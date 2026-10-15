"""
Code2Test Test Agent

LLM-powered agent for generating tests from inferred intents.
"""

import ast
import logging
import asyncio
import os
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

from pydantic_ai import Agent
from pydantic import BaseModel, Field

from code2test.core.models import (
    Intent,
    TestCase,
    TestFile,
    TestStatus,
    TestFramework,
)
from code2test.agents.errors import raise_if_fatal

logger = logging.getLogger(__name__)


class GeneratedTest(BaseModel):
    """A single generated test from LLM."""
    name: str
    description: str
    test_code: str
    tests_behavior: str


class TestGenerationResult(BaseModel):
    """Result from test generation."""

    __test__ = False  # not a pytest test class
    tests: List[GeneratedTest]
    imports: List[str] = Field(default_factory=list)
    fixtures: List[str] = Field(default_factory=list)


TEST_SYSTEM_PROMPT = """You are an expert test engineer specializing in writing comprehensive, readable tests.
Your task is to generate tests that validate the INTENDED behavior of code, not just what it currently does.

Guidelines:
- Focus on testing the behavioral contract described in the intent
- Include positive tests (expected behavior works)
- Include negative tests (error handling, edge cases)
- Use descriptive test names that explain what is being tested
- Keep tests focused - one assertion concept per test
- Generate fixtures when setup is complex
- Use the appropriate test framework syntax

For pytest, use:
- Function-based tests with `test_` prefix
- `pytest.raises` for exception testing
- Fixtures for shared setup
- Parameterized tests for similar scenarios"""


PYTEST_GENERATION_PROMPT = """Generate pytest tests for the following component based on its inferred intent:

**Component:** {name}
**Intent:** {intent}
**Confidence:** {confidence:.0%}

**Import it with:** `{import_line}`

**Imports at the top of its module (use them to import the types it works with):**
```python
{module_imports}
```

**Signature:**
```python
{signature}
```

**Source Code:**
```python
{source_code}
```

Generate comprehensive tests that validate this intent. Include:
1. A test for the primary happy path
2. Tests for edge cases mentioned in the intent
3. Tests for error conditions
4. Any necessary fixtures

Rules:
- Each test must be a complete, self-contained pytest function whose name starts with `test_`.
- Put every import the tests need (including the import above) in `imports`, one statement per entry.
- Only use the public behavior visible in the source; do not invent attributes or helpers.
- Do not mock the component under test itself.

Return tests using pytest syntax with clear docstrings explaining what each test validates."""


FIX_TESTS_PROMPT = """These generated pytest tests for `{name}` fail. Fix them.

**Intent:** {intent}

**Import it with:** `{import_line}`

**Source Code:**
```python
{source_code}
```

**Current imports:**
```python
{imports}
```

**Current fixtures (shared by all tests in the file):**
```python
{fixtures}
```

**Failing tests and their failure output:**
{failures}

For each failing test, return a corrected version with the SAME name. A test should
assert what the source code actually does when that matches the intent. If you believe
the source code has a genuine bug (it contradicts the intent), keep the assertion of the
intended behavior unchanged.

`imports` REPLACES the file's current imports: return the complete list every test in the
file needs, and leave out any import that is failing (e.g. ModuleNotFoundError).
`fixtures` likewise REPLACES the current fixtures: return them all, corrected if they are
the cause of the failure (e.g. a syntax error outside the test functions)."""


def test_function_name(code: str, fallback: str) -> str:
    """The name of the first test function the code defines (what pytest reports)."""
    match = re.search(r"^\s*(?:async\s+)?def\s+(test\w*)\s*\(", clean_code(code), re.M)
    return match.group(1) if match else fallback


def clean_code(code: str) -> str:
    """
    Undo double-escaping some models apply to code in JSON output.

    Code returned as one line with literal ``\\n`` sequences doesn't compile;
    when unescaping newlines/quotes makes it compile, use the unescaped version.
    """
    if "\n" in code.strip() or "\\n" not in code:
        return code
    try:
        compile(code, "<test>", "exec")
        return code
    except SyntaxError:
        pass
    unescaped = code.replace("\\n", "\n").replace("\\t", "    ").replace('\\"', '"').replace("\\'", "'")
    try:
        compile(unescaped, "<test>", "exec")
        return unescaped
    except SyntaxError:
        return code


class TestAgent:
    """
    LLM agent for test generation.
    
    Generates tests based on inferred intents using the specified test framework.
    """

    __test__ = False  # not a pytest test class
    
    def __init__(
        self,
        model: str = "openai:gpt-4o-mini",
        repo_path: Optional[str] = None,
        output_dir: str = "tests",
    ):
        """
        Initialize test agent.
        
        Args:
            model: LLM model to use for generation
            repo_path: Repository root, used to make source paths relative
            output_dir: Directory (relative to repo root) where tests are written
        """
        self.model = model
        self.repo_path = repo_path
        self.output_dir = output_dir or "tests"
        self._agent = None
    
    def _get_agent(self) -> Agent:
        """Get or create the pydantic-ai agent."""
        if self._agent is None:
            self._agent = Agent(
                self.model,
                system_prompt=TEST_SYSTEM_PROMPT,
            )
        return self._agent
    
    async def generate_unit_tests(
        self,
        component: Dict[str, Any],
        intent: Intent,
        framework: TestFramework = TestFramework.PYTEST
    ) -> TestFile:
        """
        Generate unit tests for a component.
        
        Args:
            component: Component data from AST analysis
            intent: Inferred intent for the component
            framework: Test framework to use
            
        Returns:
            TestFile with generated test cases
        """
        if framework != TestFramework.PYTEST:
            logger.warning(f"Framework {framework} not fully supported, using pytest patterns")
        
        prompt = PYTEST_GENERATION_PROMPT.format(
            name=component.get("name", "unknown"),
            intent=intent.intent_text,
            confidence=intent.confidence,
            signature=component.get("signature") or "",
            source_code=(component.get("source_code") or "")[:6000],  # Limit size
            import_line=self.import_line_for(component) or "(not importable: test via its module)",
            module_imports=self.module_imports_for(component) or "# none",
        )
        
        try:
            agent = self._get_agent()
            
            # Simple retry loop for 429s without tenacity dependency
            max_retries = 3
            backoff = 2.0
            for attempt in range(max_retries):
                try:
                    result = await agent.run(prompt, output_type=TestGenerationResult)
                    break 
                except Exception as e:
                    # Check for rate limit
                    is_rate_limit = "429" in str(e)
                    if hasattr(e, "status_code") and e.status_code == 429:
                        is_rate_limit = True

                    if is_rate_limit and attempt < max_retries - 1:
                        wait = backoff * (2 ** attempt)
                        logger.warning(f"Rate limited (429), retrying in {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        raise e
            
            # Convert to TestCase objects
            test_cases = []
            for gen_test in result.output.tests:
                test_cases.append(TestCase(
                    name=test_function_name(gen_test.test_code, gen_test.name),
                    intent_text=gen_test.tests_behavior,
                    test_code=clean_code(gen_test.test_code),
                    status=TestStatus.PENDING,
                ))
            
            # Build test file path
            component_path = component.get("file_path", "unknown.py")
            test_path = self._generate_test_path(component_path, component)
            
            return TestFile(
                path=test_path,
                component_id=component.get("id", component.get("name", "unknown")),
                component_path=component_path,
                test_cases=test_cases,
                framework=framework,
                imports=self._ensure_import(result.output.imports, component),
                fixtures=[clean_code(f) for f in result.output.fixtures],
                created_at=datetime.now(),
            )
            
        except Exception as e:
            raise_if_fatal(e)
            logger.error(f"Test generation failed: {e}")
            # Return empty test file
            return TestFile(
                path=self._generate_test_path(component.get("file_path", "unknown.py"), component),
                component_id=component.get("id", component.get("name", "unknown")),
                component_path=component.get("file_path", ""),
                test_cases=[],
                framework=framework,
            )
    
    async def generate_integration_tests(
        self,
        module: Dict[str, Any],
        child_components: List[Dict[str, Any]],
        intents: Dict[str, Intent],
        framework: TestFramework = TestFramework.PYTEST
    ) -> TestFile:
        """
        Generate integration tests for a module.
        
        Args:
            module: Module data
            child_components: Child components in the module
            intents: Intents for child components
            framework: Test framework
            
        Returns:
            TestFile with integration tests
        """
        # Build context about the module's components
        component_summaries = []
        for comp in child_components[:10]:  # Limit for context window
            comp_id = comp.get("id", comp.get("name"))
            intent = intents.get(comp_id)
            if intent:
                component_summaries.append(f"- {comp.get('name')}: {intent.intent_text}")
        
        prompt = f"""Generate integration tests for the following module:

**Module:** {module.get("name", "unknown")}
**Path:** {module.get("path", "")}

**Components and their intents:**
{chr(10).join(component_summaries)}

Generate integration tests that verify:
1. Components work together correctly
2. Data flows properly between components
3. Error handling across component boundaries

Use pytest syntax with appropriate fixtures."""

        try:
            agent = self._get_agent()
            
            # Simple retry loop for 429s
            max_retries = 3
            backoff = 2.0
            for attempt in range(max_retries):
                try:
                    result = await agent.run(prompt, output_type=TestGenerationResult)
                    break
                except Exception as e:
                    is_rate_limit = "429" in str(e) or (hasattr(e, "status_code") and e.status_code == 429)
                    if is_rate_limit and attempt < max_retries - 1:
                        wait = backoff * (2 ** attempt)
                        logger.warning(f"Rate limited (429), retrying in {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        raise e
            
            test_cases = [
                TestCase(
                    name=test_function_name(gen_test.test_code, gen_test.name),
                    intent_text=gen_test.tests_behavior,
                    test_code=clean_code(gen_test.test_code),
                    status=TestStatus.PENDING,
                )
                for gen_test in result.output.tests
            ]
            
            module_path = module.get("path", "unknown")
            test_path = os.path.join(self.output_dir, "integration", f"test_{module.get('name', 'module')}.py")
            
            return TestFile(
                path=test_path,
                component_id=f"module:{module.get('name', 'unknown')}",
                component_path=module_path,
                test_cases=test_cases,
                framework=framework,
                imports=result.output.imports,
                fixtures=result.output.fixtures,
            )
            
        except Exception as e:
            raise_if_fatal(e)
            logger.error(f"Integration test generation failed: {e}")
            return TestFile(
                path=os.path.join(self.output_dir, "integration", f"test_{module.get('name', 'module')}.py"),
                component_id=f"module:{module.get('name', 'unknown')}",
                component_path=module.get("path", ""),
                test_cases=[],
                framework=framework,
            )
    
    def module_path_for(self, component: Dict[str, Any]) -> Optional[str]:
        """Dotted module path for a component's source file, e.g. src/pkg/mod.py -> pkg.mod."""
        rel = component.get("relative_path") or component.get("file_path") or ""
        if self.repo_path and os.path.isabs(rel):
            try:
                rel = os.path.relpath(rel, self.repo_path)
            except ValueError:
                return None
        if not rel.endswith(".py"):
            return None
        parts = rel[:-3].replace(os.sep, "/").split("/")
        if parts and parts[0] == "src":
            parts = parts[1:]
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts or not all(p.isidentifier() for p in parts):
            return None
        return ".".join(parts)

    def import_line_for(self, component: Dict[str, Any]) -> Optional[str]:
        """Import statement for the component under test."""
        module = self.module_path_for(component)
        name = str(component.get("name") or "").split(".")[0]
        if not module or not name.isidentifier():
            return None
        return f"from {module} import {name}"

    def module_imports_for(self, component: Dict[str, Any]) -> str:
        """Top-level import statements of the component's source file, made absolute."""
        path = component.get("file_path") or ""
        if self.repo_path and path and not os.path.isabs(path):
            path = os.path.join(self.repo_path, path)
        try:
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except (OSError, SyntaxError, ValueError):
            return ""

        package = (self.module_path_for(component) or "").split(".")
        if not str(path).endswith("__init__.py"):
            package = package[:-1]

        lines = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                lines.append(ast.unparse(node))
            elif isinstance(node, ast.ImportFrom):
                if node.level:  # resolve relative imports so tests can use them
                    base = package[: len(package) - node.level + 1] if node.level <= len(package) else []
                    module = ".".join(base + ([node.module] if node.module else []))
                    names = ", ".join(a.name + (f" as {a.asname}" if a.asname else "") for a in node.names)
                    lines.append(f"from {module} import {names}" if module else ast.unparse(node))
                else:
                    lines.append(ast.unparse(node))
        return "\n".join(lines[:40])

    def _ensure_import(self, imports: List[str], component: Dict[str, Any]) -> List[str]:
        """Make sure the component under test is imported."""
        imports = [clean_code(i).strip() for i in imports if i and i.strip()]
        line = self.import_line_for(component)
        module = self.module_path_for(component)
        if line and not any(module and module in i for i in imports):
            imports.insert(0, line)
        if not any(i in ("import pytest",) or i.startswith("import pytest") for i in imports):
            imports.insert(0, "import pytest")
        return imports

    async def fix_tests(
        self,
        test_file: TestFile,
        failing: List[TestCase],
        component: Dict[str, Any],
        intent: Intent,
    ) -> TestFile:
        """
        Ask the model to repair failing tests, using their failure output.

        Returns the test file with failing tests replaced by their fixed versions
        (tests the model did not return are kept unchanged).
        """
        failures = "\n\n".join(
            f"### {tc.name}\n```python\n{tc.test_code}\n```\nFailure:\n```\n{(tc.failure_message or 'unknown')[:1500]}\n```"
            for tc in failing
        )
        prompt = FIX_TESTS_PROMPT.format(
            name=component.get("name", "unknown"),
            intent=intent.intent_text,
            import_line=self.import_line_for(component) or "(unknown)",
            source_code=(component.get("source_code") or "")[:6000],
            imports="\n".join(test_file.imports),
            fixtures="\n\n".join(test_file.fixtures) or "# none",
            failures=failures,
        )
        try:
            result = await self._get_agent().run(prompt, output_type=TestGenerationResult)
        except Exception as e:
            raise_if_fatal(e)
            logger.error(f"Test repair failed: {e}")
            return test_file

        fixed = {test_function_name(t.test_code, t.name): t for t in result.output.tests}
        new_cases = []
        for tc in test_file.test_cases:
            if tc.name in fixed:
                new_cases.append(TestCase(
                    name=tc.name,
                    intent_text=tc.intent_text,
                    test_code=clean_code(fixed[tc.name].test_code),
                    status=TestStatus.PENDING,
                ))
            else:
                new_cases.append(tc)

        return test_file.model_copy(update={
            "test_cases": new_cases,
            "imports": self._ensure_import(
                list(dict.fromkeys(result.output.imports or test_file.imports)), component
            ),
            "fixtures": [clean_code(f) for f in (result.output.fixtures or test_file.fixtures)],
        })

    def _generate_test_path(self, source_path: str, component: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate test file path from source path.

        src/pkg/file.py + component "pkg.file.Foo" -> <output_dir>/pkg/test_file_foo.py.
        Each component gets its own file so several components in one source
        file don't overwrite each other.

        Args:
            source_path: Path to source file (absolute or relative to repo root)
            component: Component data, used to make the file name unique

        Returns:
            Path for test file, relative to the repo root
        """
        if self.repo_path and os.path.isabs(source_path):
            try:
                source_path = os.path.relpath(source_path, self.repo_path)
            except ValueError:
                pass
        source_path = source_path.lstrip(os.sep)

        dirname = os.path.dirname(source_path)
        name = os.path.splitext(os.path.basename(source_path))[0]
        if name == "__init__":  # pkg/__init__.py -> tests/pkg/test_<component>.py
            name = ""

        # Handle common patterns
        if dirname == "src" or dirname.startswith("src" + os.sep):
            dirname = dirname[4:]  # Remove src/ prefix

        if name.startswith("test_"):
            name = name[5:]

        comp_name = ""
        if component:
            comp_name = str(component.get("name") or component.get("id") or "").split(".")[-1]
            comp_name = re.sub(r"\W+", "_", comp_name).strip("_").lower()

        if not name:
            basename = f"test_{comp_name or 'init'}.py"
        elif comp_name and comp_name != name.lower():
            basename = f"test_{name}_{comp_name}.py"
        else:
            basename = f"test_{name}.py"

        return os.path.join(self.output_dir, dirname, basename)

    def format_test_preview(self, test_file: TestFile) -> str:
        """
        Format test file for user preview.
        
        Args:
            test_file: Generated test file
            
        Returns:
            Formatted preview string
        """
        lines = [
            f"Generated {len(test_file.test_cases)} tests:",
        ]
        
        for tc in test_file.test_cases:
            status_icon = "○"  # pending
            lines.append(f"  {status_icon} {tc.name}")
        
        return "\n".join(lines)

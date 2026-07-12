"""
Code2Test Test Agent

LLM-powered agent for generating tests from inferred intents.
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from pydantic import BaseModel, Field

from code2test.core.models import (
    Intent,
    TestCase,
    TestFile,
    TestStatus,
    TestFramework,
)
from code2test.providers import Provider, get_provider
from code2test.config import Config

logger = logging.getLogger(__name__)


class GeneratedTest(BaseModel):
    """A single generated test from LLM."""
    name: str
    description: str
    test_code: str
    tests_behavior: str


class TestGenerationResult(BaseModel):
    """Result from test generation."""
    tests: list  # list[GeneratedTest]
    imports: list = Field(default_factory=list)
    fixtures: list = Field(default_factory=list)


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

Return tests using pytest syntax with clear docstrings explaining what each test validates."""


class TestAgent:
    """
    LLM agent for test generation.
    
    Generates tests based on inferred intents using the specified test framework.
    """
    
    def __init__(
        self,
        model: str = "stub",
        provider: Provider | None = None,
    ) -> None:
        """Initialize test agent.

        Args:
            model: Used to construct a default Provider when none is
                supplied. Defaults to "stub" so v1.0 has a sensible
                offline default.
            provider: A pre-built Provider. Preferred over `model`.
        """
        self.model = model
        if provider is None:
            if model in ("stub", "openai", "pydantic-ai"):
                cfg = Config(provider=model)
            else:
                cfg = Config(provider="stub")
            self._provider = get_provider(cfg)
        else:
            self._provider = provider
        self._agent = None  # legacy shim; harmless

    def _get_agent(self):
        """Deprecated. Returns self._provider for legacy callers."""
        return self._provider
    
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
            signature=component.get("signature", ""),
            source_code=component.get("source_code", "")[:3000],  # Limit size
        )
        
        try:
            # The provider seam: one call, one schema, one result.
            result = self._provider.apredict(
                TEST_SYSTEM_PROMPT, prompt, TestGenerationResult,
            )

            # Convert to TestCase objects. Defensive: a stub or partial
            # provider may yield fewer fields than the full schema.
            raw_tests = result.tests or []
            test_cases = []
            for gen_test in raw_tests:
                test_cases.append(TestCase(
                    name=gen_test.name,
                    intent_text=gen_test.tests_behavior,
                    test_code=gen_test.test_code,
                    status=TestStatus.PENDING,
                ))

            # Build test file path
            component_path = component.get("file_path", "unknown.py")
            test_path = self._generate_test_path(component_path)

            return TestFile(
                path=test_path,
                component_id=component.get("id", component.get("name", "unknown")),
                component_path=component_path,
                test_cases=test_cases,
                framework=framework,
                imports=result.imports or [],
                fixtures=result.fixtures or [],
                created_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Test generation failed: {e}")
            # Return empty test file
            return TestFile(
                path=self._generate_test_path(component.get("file_path", "unknown.py")),
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
            # The provider seam: same shape as generate_unit_tests.
            result = self._provider.apredict(
                TEST_SYSTEM_PROMPT, prompt, TestGenerationResult,
            )

            raw_tests = result.tests or []
            test_cases = [
                TestCase(
                    name=gen_test.name,
                    intent_text=gen_test.tests_behavior,
                    test_code=gen_test.test_code,
                    status=TestStatus.PENDING,
                )
                for gen_test in raw_tests
            ]

            module_path = module.get("path", "unknown")
            test_path = f"tests/integration/test_{module.get('name', 'module')}.py"

            return TestFile(
                path=test_path,
                component_id=f"module:{module.get('name', 'unknown')}",
                component_path=module_path,
                test_cases=test_cases,
                framework=framework,
                imports=result.imports or [],
                fixtures=result.fixtures or [],
            )

        except Exception as e:
            logger.error(f"Integration test generation failed: {e}")
            return TestFile(
                path=f"tests/integration/test_{module.get('name', 'module')}.py",
                component_id=f"module:{module.get('name', 'unknown')}",
                component_path=module.get("path", ""),
                test_cases=[],
                framework=framework,
            )
    
    def _generate_test_path(self, source_path: str) -> str:
        """
        Generate test file path from source path.
        
        Args:
            source_path: Path to source file
            
        Returns:
            Path for test file
        """
        # Convert src/module/file.py -> tests/module/test_file.py
        import os
        
        dirname = os.path.dirname(source_path)
        basename = os.path.basename(source_path)
        
        # Handle common patterns
        if dirname.startswith("src/"):
            dirname = dirname[4:]  # Remove src/ prefix
        
        # Add test_ prefix to filename
        if not basename.startswith("test_"):
            name, ext = os.path.splitext(basename)
            basename = f"test_{name}{ext}"
        
        return os.path.join("tests", dirname, basename) if dirname else os.path.join("tests", basename)
    
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

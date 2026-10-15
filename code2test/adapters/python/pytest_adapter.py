"""
Code2Test Pytest Adapter

Adapter for pytest test file generation and execution.
"""

import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from code2test.core.models import TestFile


# Default pytest imports
DEFAULT_IMPORTS = [
    "import pytest",
]


class PytestAdapter:
    """
    Adapter for pytest test generation and execution.

    Handles:
    - Test file content generation
    - pytest execution
    - Result parsing
    """

    def __init__(self, repo_path: str):
        """
        Initialize pytest adapter.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = Path(repo_path)
        from code2test.core.templates import TemplateManager

        self.template_manager = TemplateManager()

    def generate_test_file_content(self, test_file: TestFile, intent_text: str = "") -> str:
        """
        Generate pytest test file content.

        Args:
            test_file: TestFile with test cases
            intent_text: Intent description for docstring

        Returns:
            Complete test file content
        """
        # Collect imports
        imports = list(DEFAULT_IMPORTS)
        imports.extend(test_file.imports)

        # Add import for the component under test
        component_import = self._generate_import_statement(test_file.component_path)
        if component_import:
            imports.append(component_import)

        # Prepare context for template
        # We need to structure the data exactly as the template expects

        # Parse test cases to extract setup/action/assertions if possible
        # Currently TestCase model stores raw 'test_code'.
        # The template expects a structured object.
        # For this refactor, we will assume 'test_code' contains the full body
        # and pass it as 'action' or structured if parsed.
        # However, to fully utilize templates, we should ideally change how TestAgent generates tests.
        # But to be minimally invasive now, we can wrap the existing code or parse it.

        # Simpler approach matching current model:
        # We will modify the template or the context to handle the existing 'test_code' string.
        # Actually, let's adapt the context to match the template we wrote.

        tests_data = []
        for tc in test_file.test_cases:
            # If test_code is already full python code, we might struggle to split it.
            # But the Template expects setup/action/assertions blocks.
            # If we don't have them split, we can just pass everything in 'action' for now.
            tests_data.append(
                {
                    "name": tc.name,
                    "intent": tc.intent_text,
                    "fixtures": [],  # We don't track per-test fixtures yet in this model explicitly
                    "setup": "",
                    "action": tc.test_code,  # Passing full code body here
                    "assertions": "",
                }
            )

        # Render
        return self.template_manager.render(
            "python/pytest/test_file.j2",
            {
                "component_path": test_file.component_path,
                "intent": intent_text or "See individual test docstrings",
                "imports": imports,
                "fixtures": [
                    {"name": f"fixture_{i}", "docstring": "Generated fixture", "body": f}
                    for i, f in enumerate(test_file.fixtures)
                ],
                "tests": tests_data,
            },
        )

    def _generate_import_statement(self, component_path: str) -> Optional[str]:
        """
        Generate import statement for the component under test.

        Args:
            component_path: Path to the source file

        Returns:
            Import statement or None
        """
        if not component_path:
            return None

        # Convert file path to module path
        # e.g., src/auth/token.py -> src.auth.token
        path = Path(component_path)

        if path.suffix != ".py":
            return None

        # Remove .py extension
        module_path = str(path.with_suffix(""))

        # Replace path separators with dots
        module_path = module_path.replace(os.sep, ".").replace("/", ".")

        # Remove leading dots
        module_path = module_path.lstrip(".")

        return f"from {module_path} import *"

    def run_tests(self, test_path: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Execute pytest and return results.

        Args:
            test_path: Path to test file or directory
            timeout: Timeout in seconds

        Returns:
            Dictionary with test results
        """
        from code2test.core.verifier import TestVerifier

        run = TestVerifier(str(self.repo_path), timeout=timeout).run_pytest(
            self.repo_path / test_path
        )
        summary = {
            "passed": len(run.names("passed")),
            "failed": len(run.names("failed")),
            "skipped": len(run.names("skipped")),
        }
        summary["total"] = sum(summary.values())
        result = {
            "success": run.ok,
            "exit_code": run.returncode,
            "tests": [
                {"nodeid": f"{c.classname}::{c.name}", "outcome": c.outcome, "message": c.message}
                for c in run.cases
            ],
            "summary": summary,
            "stdout": run.stdout,
            "stderr": run.stderr,
        }
        if run.collection_error:
            result["error"] = run.collection_error
        return result

    def generate_fixture(self, name: str, setup_code: str, scope: str = "function") -> str:
        """
        Generate a pytest fixture.

        Args:
            name: Fixture name
            setup_code: Setup code for the fixture
            scope: Fixture scope (function, class, module, session)

        Returns:
            Fixture code
        """
        return f'''@pytest.fixture(scope="{scope}")
def {name}():
    """Fixture for {name}."""
{self._indent(setup_code, 4)}'''

    def generate_parametrized_test(
        self, test_name: str, parameters: List[Dict[str, Any]], test_body: str
    ) -> str:
        """
        Generate a parametrized test.

        Args:
            test_name: Name of the test
            parameters: List of parameter dictionaries
            test_body: Test body code

        Returns:
            Parametrized test code
        """
        if not parameters:
            return f'''def {test_name}():
    """Test with no parameters."""
{self._indent(test_body, 4)}'''

        # Build parameter string
        param_names = list(parameters[0].keys())
        param_values = [tuple(p[k] for k in param_names) for p in parameters]

        param_str = ", ".join(param_names)
        values_str = ", ".join(str(v) for v in param_values)

        return f'''@pytest.mark.parametrize("{param_str}", [{values_str}])
def {test_name}({param_str}):
    """Parametrized test for {test_name}."""
{self._indent(test_body, 4)}'''

    def _indent(self, code: str, spaces: int) -> str:
        """Indent code by specified number of spaces."""
        indent = " " * spaces
        lines = code.split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)

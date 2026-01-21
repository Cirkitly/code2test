"""
Code2Test Jest Adapter

Adapter for Jest test file generation and execution.
"""

import os
import subprocess
import json
import tempfile
from typing import Dict, List, Any, Optional
from pathlib import Path

from code2test.core.models import TestFile, TestCase, TestStatus


# Default Jest imports
DEFAULT_IMPORTS = [
    # Assuming ES modules or adjust for CommonJS as needed
    # For now, we'll assume the user might want explicitly imported jest globals or rely on global scope
    # "import { describe, expect, test, beforeEach } from '@jest/globals';",
]


class JestAdapter:
    """
    Adapter for Jest test generation and execution.
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        from code2test.core.templates import TemplateManager
        self.template_manager = TemplateManager()
    
    def generate_test_file_content(
        self,
        test_file: TestFile,
        intent_text: str = ""
    ) -> str:
        """
        Generate Jest test file content.
        """
        # Collect imports
        imports = list(DEFAULT_IMPORTS)
        imports.extend(test_file.imports)
        
        # Add import for the component under test
        component_import = self._generate_import_statement(test_file.component_path)
        if component_import:
            imports.append(component_import)
        
        # Prepare context
        component_name = Path(test_file.component_path).stem
        
        tests_data = []
        for tc in test_file.test_cases:
            tests_data.append({
                "intent": tc.intent_text,
                "setup": "",
                "action": tc.test_code,
                "assertions": ""
            })

        return self.template_manager.render(
            "javascript/jest/test_file.j2",
            {
                "component_name": component_name,
                "imports": imports,
                "mocks": test_file.fixtures, # Treating fixtures as mocks/setup code for JS
                "tests": tests_data
            }
        )
    
    def _generate_import_statement(self, component_path: str) -> Optional[str]:
        """
        Generate import statement for the component under test.
        """
        if not component_path:
            return None
            
        path = Path(component_path)
        
        # Determine relative path from test file (assuming tests parallel src)
        # This is a simplification; handling imports in JS is complex
        # For now, return a placeholder or simple require/import
        file_name = path.stem
        # Assuming we are in a 'tests' dir and importing from 'src'
        # import { Module } from '../src/path/to/module';
        
        return f"import * as {file_name} from '../{component_path}';" # Optimized guess
    
    def run_tests(
        self,
        test_path: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Execute Jest and return results.
        """
        full_path = self.repo_path / test_path
        
        # Create temp file for JSON results
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_path = f.name
            
        try:
            # Command: npx jest <file> --json --outputFile=<json_path>
            cmd = [
                "npx", "jest",
                str(full_path),
                "--json",
                f"--outputFile={json_path}"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return self._parse_result(json_path, result, timeout)
            
        except subprocess.TimeoutExpired:
            return self._error_result(f"Timeout after {timeout} seconds")
        except Exception as e:
             return self._error_result(str(e))
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)

    def _parse_result(self, json_path: str, result: subprocess.CompletedProcess, timeout: int) -> Dict[str, Any]:
        tests_results = []
        summary = {"passed": 0, "failed": 0, "skipped": 0, "total": 0}

        if os.path.exists(json_path):
            try:
                with open(json_path) as f:
                    report = json.load(f)
                
                # Jest JSON format extraction
                # report['testResults'][0]['assertionResults']
                for suite in report.get("testResults", []):
                    for assertion in suite.get("assertionResults", []):
                        status = assertion.get("status") # passed, failed, pending
                        title = assertion.get("title")
                        
                        summary["total"] += 1
                        if status == "passed":
                            summary["passed"] += 1
                        elif status == "failed":
                            summary["failed"] += 1
                        elif status == "pending": # skipped
                            summary["skipped"] += 1
                            
                        tests_results.append({
                            "nodeid": title,
                            "outcome": status,
                            "duration": 0, # Could extract if needed
                            "call": {}
                        })
            except Exception:
                pass

        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "tests": tests_results,
            "summary": summary,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        return {
            "success": False,
            "exit_code": -1,
            "error": error_msg,
            "tests": [],
            "summary": {"passed": 0, "failed": 0, "skipped": 0, "total": 0},
        }

    def generate_mock(self, name: str, mock_code: str) -> str:
        """Generate a Jest mock."""
        return f"const {name} = jest.fn({mock_code});"

    def _indent(self, code: str, spaces: int) -> str:
        indent = " " * spaces
        lines = code.split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)

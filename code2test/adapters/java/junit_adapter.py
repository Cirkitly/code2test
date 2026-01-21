"""
Code2Test JUnit Adapter

Adapter for JUnit 5 test file generation and execution.
"""

import os
import subprocess
import re
from typing import Dict, List, Any, Optional
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from code2test.core.models import TestFile, TestCase, TestStatus


TEST_FILE_TEMPLATE = '''package {package_name};

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
{imports}

/**
 * Tests for {component_name}
 * Intent: {intent}
 */
class {test_class_name} {{

{fixtures}

{test_cases}
}}
'''

class JUnitAdapter:
    """
    Adapter for JUnit test generation and execution.
    """
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
    
    def generate_test_file_content(
        self,
        test_file: TestFile,
        intent_text: str = ""
    ) -> str:
        """
        Generate JUnit test file content.
        """
        # Parse package from component path (basic heuristic)
        # src/main/java/com/example/MyClass.java -> com.example
        package_name = self._infer_package(test_file.component_path)
        
        component_name = Path(test_file.component_path).stem
        test_class_name = f"{component_name}Test"
        
        imports_str = "\n".join(test_file.imports)
        
        fixtures_str = "\n".join(test_file.fixtures) if test_file.fixtures else ""
        
        test_cases_str = "\n\n".join(self._indent(tc.test_code, 4) for tc in test_file.test_cases)
        
        return TEST_FILE_TEMPLATE.format(
            package_name=package_name,
            component_name=component_name,
            test_class_name=test_class_name,
            intent=intent_text,
            imports=imports_str,
            fixtures=self._indent(fixtures_str, 4),
            test_cases=test_cases_str
        )

    def _infer_package(self, path_str: str) -> str:
        """Infer java package from path."""
        # Look for src/main/java or similar
        parts = Path(path_str).parts
        try:
            if "java" in parts:
                idx = parts.index("java")
                return ".".join(parts[idx+1:-1])
        except ValueError:
            pass
        return "com.example.generated" # Fallback

    def run_tests(
        self,
        test_path: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Execute JUnit tests.
        Assumption: using Maven or Gradle.
        """
        # We need to map the file path to a test class name for the runner
        # tests/com/example/MyTest.java -> com.example.MyTest
        
        test_class = self._path_to_classname(test_path)
        
        cmd = []
        if (self.repo_path / "pom.xml").exists():
            cmd = ["mvn", "test", f"-Dtest={test_class}"]
        elif (self.repo_path / "build.gradle").exists():
            cmd = ["./gradlew", "test", "--tests", test_class]
        else:
            return self._error_result("No build system detected (pom.xml or build.gradle needed)")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            # Parsing Maven/Gradle output is hard. 
            # Better to parse the XML report usually generated in target/surefire-reports
            return self._parse_results(test_class, result)
            
        except subprocess.TimeoutExpired:
            return self._error_result("Timeout")
        except Exception as e:
            return self._error_result(str(e))

    def _path_to_classname(self, path_str: str) -> str:
        # Simplistic mapping
        path = Path(path_str)
        name = path.stem
        # Try to find package parts
        # This implementation assumes the standard maven layout structure
        parts = list(path.parent.parts)
        if "java" in parts:
            idx = parts.index("java")
            package_parts = parts[idx+1:]
            return ".".join(package_parts + [name])
        return name

    def _parse_results(self, test_class: str, result: subprocess.CompletedProcess) -> Dict[str, Any]:
        # Try to find XML report
        # Maven: target/surefire-reports/TEST-<class>.xml
        # Gradle: build/test-results/test/TEST-<class>.xml
        
        xml_path = None
        for base in ["target/surefire-reports", "build/test-results/test"]:
            p = self.repo_path / base / f"TEST-{test_class}.xml"
            if p.exists():
                xml_path = p
                break
        
        if xml_path and xml_path.exists():
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                # <testsuite tests="X" failures="Y" skipped="Z" ...>
                summary = {
                    "total": int(root.attrib.get("tests", 0)),
                    "failed": int(root.attrib.get("failures", 0)) + int(root.attrib.get("errors", 0)),
                    "skipped": int(root.attrib.get("skipped", 0)),
                    "passed": 0
                }
                summary["passed"] = summary["total"] - summary["failed"] - summary["skipped"]
                
                tests = []
                for tc in root.findall("testcase"):
                    outcome = "passed"
                    if tc.find("failure") is not None or tc.find("error") is not None:
                        outcome = "failed"
                    elif tc.find("skipped") is not None:
                        outcome = "skipped"
                        
                    tests.append({
                        "nodeid": tc.attrib.get("name"),
                        "outcome": outcome,
                        "duration": float(tc.attrib.get("time", 0))
                    })
                
                return {
                    "success": summary["failed"] == 0,
                    "exit_code": result.returncode,
                    "tests": tests,
                    "summary": summary,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            except Exception:
                pass
        
        # Fallback if no XML
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "tests": [],
            "summary": {"passed":0, "failed":0, "skipped":0, "total":0}, # Unknown
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    def _error_result(self, msg: str) -> Dict[str, Any]:
         return {
            "success": False,
            "exit_code": -1,
            "error": msg,
            "tests": [],
            "summary": {"passed": 0, "failed": 0, "skipped": 0, "total": 0},
        }

    def _indent(self, code: str, spaces: int) -> str:
        indent = " " * spaces
        lines = code.split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)

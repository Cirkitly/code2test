"""
Code2Test Test Registry

Tracks generated tests per component.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from code2test.core.models import TestFile, TestCase, TestStatus, TestFramework


class TestRegistry:
    """Tracks generated tests per component."""
    
    def __init__(self, db_path: str):
        """
        Initialize test registry.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    component_id TEXT NOT NULL,
                    component_path TEXT NOT NULL,
                    framework TEXT NOT NULL,
                    test_cases TEXT NOT NULL,
                    imports TEXT NOT NULL,
                    fixtures TEXT NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_test_files_component 
                ON test_files(component_id)
            """)
            conn.commit()
    
    def register_test(self, test_file: TestFile) -> int:
        """
        Register a generated test file.
        
        Args:
            test_file: TestFile to register
            
        Returns:
            ID of the registered test file
        """
        # Serialize test cases
        test_cases_json = json.dumps([tc.model_dump() for tc in test_file.test_cases])
        imports_json = json.dumps(test_file.imports)
        fixtures_json = json.dumps(test_file.fixtures)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO test_files 
                (path, component_id, component_path, framework, test_cases, 
                 imports, fixtures, verified, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                test_file.path,
                test_file.component_id,
                test_file.component_path,
                test_file.framework.value,
                test_cases_json,
                imports_json,
                fixtures_json,
                1 if test_file.verified else 0,
                test_file.created_at.isoformat(),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_test_file(self, path: str) -> Optional[TestFile]:
        """
        Get test file by path.
        
        Args:
            path: Path to the test file
            
        Returns:
            TestFile if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM test_files WHERE path = ?",
                (path,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return self._row_to_test_file(row)
    
    def get_tests_for_component(self, component_id: str) -> List[TestFile]:
        """
        Get all tests for a component.
        
        Args:
            component_id: Component identifier
            
        Returns:
            List of TestFile objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM test_files WHERE component_id = ?",
                (component_id,)
            )
            return [self._row_to_test_file(row) for row in cursor.fetchall()]
    
    def mark_verified(self, test_file_path: str) -> bool:
        """
        Mark a test file as verified.
        
        Args:
            test_file_path: Path to the test file
            
        Returns:
            True if updated, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE test_files SET verified = 1 WHERE path = ?",
                (test_file_path,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_unverified_tests(self) -> List[TestFile]:
        """
        Get all unverified test files.
        
        Returns:
            List of unverified TestFile objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM test_files WHERE verified = 0"
            )
            return [self._row_to_test_file(row) for row in cursor.fetchall()]
    
    def get_all_tests(self) -> List[TestFile]:
        """
        Get all registered test files.
        
        Returns:
            List of all TestFile objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM test_files ORDER BY component_path"
            )
            return [self._row_to_test_file(row) for row in cursor.fetchall()]
    
    def delete_test(self, path: str) -> bool:
        """
        Delete a test file record.
        
        Args:
            path: Path to the test file
            
        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM test_files WHERE path = ?",
                (path,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def _row_to_test_file(self, row: sqlite3.Row) -> TestFile:
        """Convert database row to TestFile model."""
        test_cases_data = json.loads(row["test_cases"])
        test_cases = []
        for tc_data in test_cases_data:
            # Handle enum conversion
            if "status" in tc_data and isinstance(tc_data["status"], str):
                tc_data["status"] = TestStatus(tc_data["status"])
            test_cases.append(TestCase(**tc_data))
        
        return TestFile(
            path=row["path"],
            component_id=row["component_id"],
            component_path=row["component_path"],
            framework=TestFramework(row["framework"]),
            test_cases=test_cases,
            imports=json.loads(row["imports"]),
            fixtures=json.loads(row["fixtures"]),
            verified=bool(row["verified"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total_files = conn.execute(
                "SELECT COUNT(*) FROM test_files"
            ).fetchone()[0]
            verified = conn.execute(
                "SELECT COUNT(*) FROM test_files WHERE verified = 1"
            ).fetchone()[0]
            
            # Count total test cases
            cursor = conn.execute("SELECT test_cases FROM test_files")
            total_tests = 0
            for row in cursor.fetchall():
                test_cases = json.loads(row[0])
                total_tests += len(test_cases)
            
            return {
                "total_test_files": total_files,
                "verified_files": verified,
                "unverified_files": total_files - verified,
                "total_test_cases": total_tests,
            }

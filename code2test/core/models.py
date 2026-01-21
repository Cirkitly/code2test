"""
Code2Test Core Models

Data models for intent-first test generation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class IntentEvidence(BaseModel):
    """Evidence supporting an inferred intent."""
    
    docstring: Optional[str] = None
    signature: Optional[str] = None
    type_hints: Optional[str] = None
    naming_signals: List[str] = Field(default_factory=list)
    call_sites: List[str] = Field(default_factory=list)
    dependency_intents: List[str] = Field(default_factory=list)
    
    def get_summary(self) -> str:
        """Get a summary of all evidence."""
        parts = []
        if self.docstring:
            parts.append(f"Docstring: {self.docstring[:100]}...")
        if self.signature:
            parts.append(f"Signature: {self.signature}")
        if self.naming_signals:
            parts.append(f"Naming: {', '.join(self.naming_signals)}")
        return " | ".join(parts) if parts else "No evidence"


class Intent(BaseModel):
    """Inferred behavioral intent for a code component."""
    
    component_id: str
    component_path: str
    intent_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: IntentEvidence = Field(default_factory=IntentEvidence)
    user_edited: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    def needs_clarification(self, threshold: float = 0.6) -> bool:
        """Check if intent confidence is below threshold."""
        return self.confidence < threshold
    
    def update_intent(self, new_text: str, user_edited: bool = True) -> None:
        """Update intent text and mark as user-edited."""
        self.intent_text = new_text
        self.user_edited = user_edited
        self.updated_at = datetime.now()
        if user_edited:
            self.confidence = 0.95  # User-edited intents are high confidence


class DiagnosisCause(str, Enum):
    """Possible causes of test failure."""
    
    TEST_WRONG = "TEST_WRONG"  # The test incorrectly interprets the intent
    CODE_BUG = "CODE_BUG"      # The code doesn't match the stated intent
    INTENT_WRONG = "INTENT_WRONG"  # The inferred intent is incorrect


class Diagnosis(BaseModel):
    """Diagnosis of a test failure."""
    
    test_name: str
    cause: DiagnosisCause
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str
    suggested_fix: Optional[str] = None
    stack_trace: Optional[str] = None
    
    def get_action_prompt(self) -> str:
        """Get the user action prompt based on diagnosis cause."""
        if self.cause == DiagnosisCause.TEST_WRONG:
            return "[f] Fix test  [k] Keep (xfail)  [s] Skip"
        elif self.cause == DiagnosisCause.CODE_BUG:
            return "[b] Flag as bug  [f] Fix test anyway  [s] Skip"
        else:  # INTENT_WRONG
            return "[i] Edit intent  [f] Fix test  [s] Skip"


class TestStatus(str, Enum):
    """Status of a test case."""
    
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    XFAIL = "xfail"  # Expected failure


class TestCase(BaseModel):
    """A single test case."""
    
    name: str
    intent_text: str
    test_code: str
    status: TestStatus = TestStatus.PENDING
    failure_message: Optional[str] = None
    diagnosis: Optional[Diagnosis] = None
    
    def mark_passed(self) -> None:
        """Mark test as passed."""
        self.status = TestStatus.PASSED
        self.failure_message = None
    
    def mark_failed(self, message: str) -> None:
        """Mark test as failed with message."""
        self.status = TestStatus.FAILED
        self.failure_message = message
    
    def mark_xfail(self, reason: str) -> None:
        """Mark test as expected failure."""
        self.status = TestStatus.XFAIL
        self.failure_message = reason


class TestFramework(str, Enum):
    """Supported test frameworks."""
    
    PYTEST = "pytest"
    UNITTEST = "unittest"
    JEST = "jest"
    MOCHA = "mocha"
    VITEST = "vitest"
    JUNIT = "junit"
    TESTNG = "testng"


class TestFile(BaseModel):
    """A generated test file."""
    
    path: str
    component_id: str
    component_path: str
    test_cases: List[TestCase] = Field(default_factory=list)
    framework: TestFramework = TestFramework.PYTEST
    imports: List[str] = Field(default_factory=list)
    fixtures: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    verified: bool = False
    
    @property
    def total_tests(self) -> int:
        """Get total number of test cases."""
        return len(self.test_cases)
    
    @property
    def passed_count(self) -> int:
        """Get count of passed tests."""
        return sum(1 for tc in self.test_cases if tc.status == TestStatus.PASSED)
    
    @property
    def failed_count(self) -> int:
        """Get count of failed tests."""
        return sum(1 for tc in self.test_cases if tc.status == TestStatus.FAILED)
    
    def get_full_content(self) -> str:
        """Generate full test file content."""
        lines = []
        
        # Imports
        for imp in self.imports:
            lines.append(imp)
        lines.append("")
        
        # Fixtures
        for fixture in self.fixtures:
            lines.append(fixture)
            lines.append("")
        
        # Test cases
        for tc in self.test_cases:
            lines.append(tc.test_code)
            lines.append("")
        
        return "\n".join(lines)


class VerificationResult(BaseModel):
    """Result of running verification on a test file."""
    
    test_file_path: str
    all_passed: bool
    passed: List[str] = Field(default_factory=list)
    failed: List[str] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)
    diagnoses: List[Diagnosis] = Field(default_factory=list)
    execution_time: float = 0.0
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    
    @property
    def total_tests(self) -> int:
        """Get total number of tests."""
        return len(self.passed) + len(self.failed) + len(self.skipped)
    
    @property
    def pass_rate(self) -> float:
        """Get pass rate as percentage."""
        if self.total_tests == 0:
            return 0.0
        return (len(self.passed) / self.total_tests) * 100


class TestSuite(BaseModel):
    """A collection of generated test files for a module."""
    
    module_path: str
    test_files: List[TestFile] = Field(default_factory=list)
    intents: Dict[str, Intent] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def total_tests(self) -> int:
        """Get total number of tests across all files."""
        return sum(tf.total_tests for tf in self.test_files)
    
    @property
    def total_passed(self) -> int:
        """Get total passed tests."""
        return sum(tf.passed_count for tf in self.test_files)
    
    @property
    def coverage_summary(self) -> Dict[str, Any]:
        """Get coverage summary."""
        return {
            "total_components": len(self.intents),
            "total_test_files": len(self.test_files),
            "total_tests": self.total_tests,
            "passed": self.total_passed,
            "components_with_tests": len(self.test_files),
        }


class GenerationConfig(BaseModel):
    """Configuration for test generation."""
    
    confidence_threshold: float = 0.6
    auto_accept: bool = False
    dry_run: bool = False
    max_tests_per_component: int = 10
    include_edge_cases: bool = True
    include_fixtures: bool = True
    output_dir: Optional[str] = None
    framework: TestFramework = TestFramework.PYTEST

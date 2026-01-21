"""
Code2Test Diagnosis Agent

LLM-powered agent for analyzing test failures and determining root cause.
"""

import logging
from typing import Dict, Any, Optional

from pydantic_ai import Agent
from pydantic import BaseModel

from code2test.core.models import (
    Intent,
    TestCase,
    Diagnosis,
    DiagnosisCause,
)

logger = logging.getLogger(__name__)


class DiagnosisResult(BaseModel):
    """Result from failure diagnosis."""
    cause: str  # TEST_WRONG, CODE_BUG, or INTENT_WRONG
    confidence: float
    explanation: str
    suggested_fix: Optional[str] = None


DIAGNOSIS_SYSTEM_PROMPT = """You are an expert debugger and test analyst.
Your task is to analyze test failures and determine the root cause.

There are THREE possible causes:
1. TEST_WRONG - The test incorrectly implements the stated intent. The test needs to be fixed.
2. CODE_BUG - The code doesn't match the intended behavior. This is a potential bug in the source code.
3. INTENT_WRONG - The inferred intent doesn't match what the code actually does. The intent needs revision.

Analyze the failure carefully:
- Compare the test assertions with the stated intent
- Compare the actual behavior with the expected behavior
- Consider if the intent description matches the code's purpose

Provide a clear confidence score (0.0-1.0) for your diagnosis."""


DIAGNOSIS_PROMPT_TEMPLATE = """Analyze this test failure:

**Test Name:** {test_name}
**Test Code:**
```python
{test_code}
```

**Stated Intent:** {intent}

**Component Under Test:**
```python
{source_code}
```

**Failure Output:**
```
{failure_output}
```

**Expected:** {expected}
**Actual:** {actual}

Determine the root cause:
1. Is the TEST wrongly implementing the intent?
2. Is the CODE buggy and not matching the intent?
3. Is the INTENT incorrectly describing what the code does?

Provide your diagnosis with:
- cause: TEST_WRONG, CODE_BUG, or INTENT_WRONG
- confidence: 0.0-1.0
- explanation: Why you believe this is the cause
- suggested_fix: How to fix the issue (optional)"""


class DiagnosisAgent:
    """
    LLM agent for test failure diagnosis.
    
    Analyzes why tests fail and categorizes the root cause.
    """
    
    def __init__(self, model: str = "openai:gpt-4o-mini"):
        """
        Initialize diagnosis agent.
        
        Args:
            model: LLM model to use
        """
        self.model = model
        self._agent = None
    
    def _get_agent(self) -> Agent:
        """Get or create the pydantic-ai agent."""
        if self._agent is None:
            self._agent = Agent(
                self.model,
                system_prompt=DIAGNOSIS_SYSTEM_PROMPT,
                result_type=DiagnosisResult,
            )
        return self._agent
    
    async def diagnose_failure(
        self,
        test_case: TestCase,
        failure_output: str,
        component: Dict[str, Any],
        intent: Intent
    ) -> Diagnosis:
        """
        Diagnose why a test failed.
        
        Args:
            test_case: The failing test case
            failure_output: stdout/stderr from test execution
            component: The component under test
            intent: The inferred intent
            
        Returns:
            Diagnosis with cause, confidence, and suggested fix
        """
        # Parse expected/actual from failure output
        expected, actual = self._parse_assertion_error(failure_output)
        
        prompt = DIAGNOSIS_PROMPT_TEMPLATE.format(
            test_name=test_case.name,
            test_code=test_case.test_code,
            intent=intent.intent_text,
            source_code=component.get("source_code", "")[:2000],
            failure_output=failure_output[:1000],  # Limit size
            expected=expected or "Unknown",
            actual=actual or "Unknown",
        )
        
        try:
            agent = self._get_agent()
            result = await agent.run(prompt)
            
            # Map string cause to enum
            cause_map = {
                "TEST_WRONG": DiagnosisCause.TEST_WRONG,
                "CODE_BUG": DiagnosisCause.CODE_BUG,
                "INTENT_WRONG": DiagnosisCause.INTENT_WRONG,
            }
            cause = cause_map.get(result.data.cause, DiagnosisCause.TEST_WRONG)
            
            return Diagnosis(
                test_name=test_case.name,
                cause=cause,
                confidence=result.data.confidence,
                explanation=result.data.explanation,
                suggested_fix=result.data.suggested_fix,
                stack_trace=failure_output[:500] if failure_output else None,
            )
            
        except Exception as e:
            logger.error(f"Diagnosis failed: {e}")
            # Return fallback diagnosis
            return Diagnosis(
                test_name=test_case.name,
                cause=DiagnosisCause.TEST_WRONG,
                confidence=0.5,
                explanation=f"Unable to diagnose: {str(e)}",
                suggested_fix=None,
                stack_trace=failure_output[:500] if failure_output else None,
            )
    
    def _parse_assertion_error(self, output: str) -> tuple[Optional[str], Optional[str]]:
        """
        Parse expected and actual values from assertion error.
        
        Args:
            output: Test failure output
            
        Returns:
            Tuple of (expected, actual) or (None, None)
        """
        import re
        
        # Common patterns
        patterns = [
            # pytest AssertionError
            r"assert\s+(.+?)\s*==\s*(.+)",
            # Expected vs Got
            r"Expected:\s*(.+?)[\n\r]+\s*Got:\s*(.+)",
            r"expected:\s*(.+?)[\n\r]+\s*actual:\s*(.+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1).strip(), match.group(2).strip()
        
        return None, None
    
    def format_diagnosis_panel(self, diagnosis: Diagnosis) -> str:
        """
        Format diagnosis for CLI display.
        
        Args:
            diagnosis: The diagnosis to format
            
        Returns:
            Formatted string for display
        """
        cause_labels = {
            DiagnosisCause.TEST_WRONG: "Test incorrectly implements intent",
            DiagnosisCause.CODE_BUG: "Potential bug in source code",
            DiagnosisCause.INTENT_WRONG: "Intent doesn't match code behavior",
        }
        
        lines = [
            f"╭─ Diagnosis ─{'─' * 50}╮",
            f"│ {diagnosis.explanation[:60]}",
            f"│",
            f"│ Likely cause: {diagnosis.cause.value} ({diagnosis.confidence:.0%})",
            f"╰─{'─' * 62}╯",
        ]
        
        return "\n".join(lines)

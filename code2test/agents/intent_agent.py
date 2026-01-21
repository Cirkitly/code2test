"""
Code2Test Intent Agent

LLM-powered agent for intent inference when static analysis signals are weak.
"""

import logging
from typing import Dict, List, Any, Optional

from pydantic_ai import Agent
from pydantic import BaseModel

from code2test.core.models import Intent, IntentEvidence

logger = logging.getLogger(__name__)


class IntentInferenceResult(BaseModel):
    """Result from LLM intent inference."""
    intent_text: str
    confidence: float
    reasoning: str
    unclear_aspects: List[str] = []


INTENT_SYSTEM_PROMPT = """You are an expert code analyst specializing in understanding code behavior.
Your task is to infer the intended behavior of code components based on:
- Source code
- Function signatures and type hints
- Naming conventions
- Context from dependencies and callers

Be specific about what the code SHOULD do, not just what it currently does.
Focus on the behavioral contract - inputs, outputs, side effects, and error handling.
If the intent is unclear, list the unclear aspects that need clarification."""


INTENT_USER_PROMPT_TEMPLATE = """Analyze this code component and infer its intended behavior:

**Component Name:** {name}
**Type:** {component_type}
**File:** {file_path}

**Signature:**
```
{signature}
```

**Source Code:**
```{language}
{source_code}
```

**Existing Documentation:**
{docstring}

**Called By:**
{call_sites}

**Dependencies:**
{dependencies}

Based on all available signals, describe:
1. The primary purpose of this component
2. Expected inputs and their constraints
3. Expected outputs and return values
4. Any side effects or state changes
5. Error conditions that should be handled

Provide your analysis as a clear, concise intent statement."""


class IntentAgent:
    """
    LLM agent for intent inference.
    
    Used when static analysis cannot determine intent with high confidence.
    """
    
    def __init__(self, model: str = "openai:gpt-4o-mini"):
        """
        Initialize intent agent.
        
        Args:
            model: LLM model to use for inference
        """
        self.model = model
        self._agent = None
    
    def _get_agent(self) -> Agent:
        """Get or create the pydantic-ai agent."""
        if self._agent is None:
            self._agent = Agent(
                self.model,
                system_prompt=INTENT_SYSTEM_PROMPT,
                result_type=IntentInferenceResult,
            )
        return self._agent
    
    async def infer_intent(
        self,
        component: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Intent:
        """
        Use LLM to infer intent when static signals are weak.
        
        Args:
            component: Component data from AST analysis
            context: Additional context (dependencies, callers, etc.)
            
        Returns:
            Inferred Intent with confidence score
        """
        if context is None:
            context = {}
        
        # Format prompt
        prompt = INTENT_USER_PROMPT_TEMPLATE.format(
            name=component.get("name", "unknown"),
            component_type=component.get("type", "function"),
            file_path=component.get("file_path", ""),
            signature=component.get("signature", ""),
            language=component.get("language", "python"),
            source_code=component.get("source_code", "")[:2000],  # Limit size
            docstring=component.get("docstring", "None provided"),
            call_sites=", ".join(component.get("called_by", [])[:5]) or "None",
            dependencies=", ".join(context.get("dependencies", [])[:5]) or "None",
        )
        
        try:
            agent = self._get_agent()
            result = await agent.run(prompt)
            
            # Build evidence
            evidence = IntentEvidence(
                docstring=component.get("docstring"),
                signature=component.get("signature"),
                type_hints=component.get("signature") if "->" in component.get("signature", "") else None,
                naming_signals=[],
                call_sites=component.get("called_by", [])[:5],
                dependency_intents=[],
            )
            
            return Intent(
                component_id=component.get("id", component.get("name", "unknown")),
                component_path=component.get("file_path", ""),
                intent_text=result.data.intent_text,
                confidence=result.data.confidence,
                evidence=evidence,
            )
            
        except Exception as e:
            logger.error(f"Intent inference failed: {e}")
            # Return low-confidence fallback
            return Intent(
                component_id=component.get("id", component.get("name", "unknown")),
                component_path=component.get("file_path", ""),
                intent_text=f"Function '{component.get('name', 'unknown')}' - intent unclear",
                confidence=0.3,
                evidence=IntentEvidence(),
            )
    
    def get_clarification_prompt(
        self,
        component: Dict[str, Any],
        partial_intent: Intent
    ) -> str:
        """
        Generate a user-facing prompt requesting clarification.
        
        Args:
            component: Component data
            partial_intent: The low-confidence intent
            
        Returns:
            Formatted clarification prompt
        """
        name = component.get("name", "unknown")
        
        prompt_parts = [
            f"⚠ Low confidence intent ({partial_intent.confidence:.0%}) for {name}()",
            "",
            f'Inferred: "{partial_intent.intent_text}"',
            "",
            "Please describe the intended behavior:",
        ]
        
        return "\n".join(prompt_parts)
    
    async def refine_intent(
        self,
        intent: Intent,
        user_feedback: str,
        component: Dict[str, Any]
    ) -> Intent:
        """
        Refine intent based on user feedback.
        
        Args:
            intent: Original low-confidence intent
            user_feedback: User's description of intended behavior
            component: Component data
            
        Returns:
            Updated Intent with higher confidence
        """
        # User-provided intents get high confidence
        refined_intent = Intent(
            component_id=intent.component_id,
            component_path=intent.component_path,
            intent_text=user_feedback.strip(),
            confidence=0.95,
            evidence=intent.evidence,
            user_edited=True,
        )
        
        return refined_intent

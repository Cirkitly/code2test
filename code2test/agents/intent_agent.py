"""Code2Test Intent Agent (M1A.3 refactor).

LLM-powered agent for intent inference when static analysis signals are
weak. v1.0 refactor: the agent no longer constructs pydantic_ai.Agent
directly. It receives a Provider through __init__ and calls
provider.apredict(system, user, schema) for the actual inference.

Backward compatibility: __init__ still accepts a `model: str` argument.
When given, it constructs a default provider via get_provider(). Tests
and existing call sites that pass `model="openai:gpt-4o-mini"` continue
to work — but the call will fail at predict() time in v1.0 with a
NotImplementedError from PydanticAIProvider, which is the intended
"real LLM not wired" signal.
"""

import logging
from typing import Dict, Any, Optional

from pydantic import BaseModel

from code2test.core.models import Intent, IntentEvidence
from code2test.providers import Provider, get_provider
from code2test.config import Config

logger = logging.getLogger(__name__)


class IntentInferenceResult(BaseModel):
    """Result from LLM intent inference."""
    intent_text: str
    confidence: float
    reasoning: str
    unclear_aspects: list = []


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
    """LLM agent for intent inference.

    Used when static analysis cannot determine intent with high
    confidence. In v1.0 the agent goes through the provider seam; if
    provider='stub' is configured, the response is deterministic and
    safe to run without API keys.
    """

    def __init__(
        self,
        model: str = "stub",
        provider: Provider | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            model: Used only when no provider is supplied; we construct
                a default provider from a Config whose provider/model
                carry across. Defaults to "stub" so v1.0 has a sensible
                offline default.
            provider: A pre-built Provider. Preferred over `model` for
                callers that already have a configured provider (the
                test-generation generator builds one and shares it).
        """
        self.model = model
        if provider is None:
            cfg = Config(provider=model) if model in ("stub", "openai", "pydantic-ai") else Config(provider="stub")
            self._provider = get_provider(cfg)
        else:
            self._provider = provider
        self._agent = None  # legacy shim for old callers reading `.model` or `._agent`; harmless

    def _get_agent(self):
        """Deprecated. Returns self._provider for backward compat with
        very old callers that introspected ._agent. Prefer the seam."""
        return self._provider

    async def infer_intent(
        self,
        component: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Intent:
        """Use LLM to infer intent when static signals are weak.

        Args:
            component: Component data from AST analysis
            context: Additional context (dependencies, callers, etc.)

        Returns:
            Inferred Intent with confidence score
        """
        if context is None:
            context = {}

        user = INTENT_USER_PROMPT_TEMPLATE.format(
            name=component.get("name", "unknown"),
            component_type=component.get("type", "function"),
            file_path=component.get("file_path", ""),
            signature=component.get("signature", ""),
            language=component.get("language", "python"),
            source_code=component.get("source_code", "")[:2000],
            docstring=component.get("docstring", "None provided"),
            call_sites=", ".join(component.get("called_by", [])[:5]) or "None",
            dependencies=", ".join(context.get("dependencies", [])[:5]) or "None",
        )

        try:
            # The provider seam: one call, one schema, one result.
            # `apredict` is synchronous in v1.0 (it delegates to predict);
            # we keep the name as a placeholder for v1.1's async backend.
            result = self._provider.apredict(
                INTENT_SYSTEM_PROMPT, user, IntentInferenceResult,
            )

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
                intent_text=result.intent_text,
                confidence=result.confidence,
                evidence=evidence,
            )

        except Exception as e:
            logger.error(f"Intent inference failed: {e}")
            # Return low-confidence fallback so the pipeline can continue.
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
        partial_intent: Intent,
    ) -> str:
        """Generate a user-facing prompt requesting clarification."""
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
        component: Dict[str, Any],
    ) -> Intent:
        """Refine intent based on user feedback."""
        return Intent(
            component_id=intent.component_id,
            component_path=intent.component_path,
            intent_text=user_feedback.strip(),
            confidence=0.95,
            evidence=intent.evidence,
            user_edited=True,
        )

"""
Code2Test Generator

Main orchestrator for the test generation pipeline.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

from code2test.core.models import (
    Intent,
    TestFile,
    TestSuite,
    TestStatus,
    TestFramework,
    VerificationResult,
    GenerationConfig,
)
from code2test.core.intent import IntentExtractor
from code2test.core.verifier import TestVerifier
from code2test.storage.intent_db import IntentDatabase
from code2test.storage.test_registry import TestRegistry
from code2test.agents.intent_agent import IntentAgent
from code2test.agents.test_agent import TestAgent
from code2test.agents.diagnosis_agent import DiagnosisAgent
from code2test.events import (
    IntentExtracted,
    TestsGenerated,
    VerificationCompleted,
    DiagnosisTriggered,
    RewriteAttempted,
    new_run_id,
    null_sink,
)
from code2test.providers.base import Provider

# The rewrite loop lives in its own module; the generator orchestrates.
from code2test.agents.rewrite_coordinator import RewriteCoordinator

logger = logging.getLogger(__name__)


class TestGenerator:
    """
    Main test generation orchestrator.

    Coordinates the three-phase pipeline:
    1. Intent extraction
    2. Test generation
    3. Verification and refinement

    Events are emitted into a sink; the production default is a null sink.
    The benchmark collector (code2testbench/) injects a real sink that
    accumulates AcceptanceReport. code2test itself never imports
    AcceptanceReport — that is the M1B.2 architectural invariant.
    """

    def __init__(
        self,
        repo_path: str,
        db_path: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
        sink=None,
    ):
        """
        Initialize test generator.

        Args:
            repo_path: Path to the repository root
            db_path: Path to database for persistence
            config: Generation configuration
            sink: Object with `emit(event)` accepting GeneratorEvent
                  subclasses. Defaults to null_sink so the generator is
                  unaware of any benchmark machinery.
        """
        self.repo_path = Path(repo_path)
        self.config = config or GenerationConfig()
        # Sink for events; production default is null_sink.
        self._sink = sink if sink is not None else null_sink()
        # Provider shared by all three agents; lazily built on first access
        # through the `provider` property so we don't pay SDK-import cost
        # on a TestGenerator that never makes an LLM call.
        self._provider: Optional[Provider] = None
        # Phase 3 stores the most recent VerificationResult per
        # component here so phase 4 can pass it to the rewrite
        # coordinator without re-running the verifier.
        self._last_verification: Dict[str, Any] = {}
        # The rewrite coordinator is constructed lazily so its
        # dependencies (the agents) are available. We hold a
        # reference once built and reuse across phase-4 calls within
        # one run, so the per-component idempotency set is consistent.
        self._rewrite_coordinator: Optional[RewriteCoordinator] = None
        # run_id is created on first generate_tests_for_module call and reused
        # across phases so a sink can correlate events for the same generation.
        self._run_id: Optional[str] = None

        # Set up database path
        if db_path is None:
            db_path = str(self.repo_path / ".code2test" / "code2test.db")

        # Initialize components
        self.intent_extractor = IntentExtractor(self.config.confidence_threshold)
        self.intent_db = IntentDatabase(db_path)
        self.test_registry = TestRegistry(db_path)
        self.verifier = TestVerifier(str(repo_path))

        # LLM agents (lazy init)
        self._intent_agent: Optional[IntentAgent] = None
        self._test_agent: Optional[TestAgent] = None
        self._diagnosis_agent: Optional[DiagnosisAgent] = None

        # Callbacks for interactive mode
        self.on_intent_extracted: Optional[Callable[[Intent], None]] = None
        self.on_test_generated: Optional[Callable[[TestFile], None]] = None
        self.on_verification_complete: Optional[Callable[[VerificationResult], None]] = None

    def _publish(self, event) -> None:
        """Single point of emission; null sink absorbs in production."""
        try:
            self._sink.emit(event)
        except Exception as exc:  # noqa: BLE001
            # A misbehaving sink must NEVER break generation. Log and move on.
            logger.warning("event sink raised %r; suppressed", exc)
    
    @property
    def provider(self):
        """Single Provider shared by all three agents.

        Built lazily because some v1.0 callers (e.g. the legacy CLI
        path with an old Config) instantiate TestGenerator without ever
        making an LLM call; deferring the openai SDK import until
        actually needed keeps those paths cheap.

        v1.1 adds the seam-awareness: previously, the lazy agent
        constructors received only ``model=self.config.model`` and
        silently produced StubProvider agents regardless of
        ``Config.provider``. We now construct one Provider that honors
        the configured provider/base_url/api_key and inject it into
        every agent.
        """
        if self._provider is None:
            from code2test.config import Config
            from code2test.providers import get_provider
            cfg = Config(
                provider=getattr(self.config, "provider", "stub"),
                model=self.config.model,
                base_url=getattr(self.config, "base_url", ""),
                api_key=getattr(self.config, "api_key", ""),
            )
            self._provider = get_provider(cfg)
        return self._provider

    @property
    def intent_agent(self) -> IntentAgent:
        if self._intent_agent is None:
            self._intent_agent = IntentAgent(provider=self.provider)
        return self._intent_agent

    @property
    def test_agent(self) -> TestAgent:
        if self._test_agent is None:
            def _on_generation_record(event) -> None:
                # The test_agent forwards per-LLM-call instrumentation
                # here. We publish it into the same sink that
                # IntentExtracted / TestsGenerated / etc. flow through,
                # so the benchmark's collector sees every event.
                self._publish(event)
            self._test_agent = TestAgent(
                provider=self.provider,
                on_generation_record=_on_generation_record,
            )
        return self._test_agent

    @property
    def diagnosis_agent(self) -> DiagnosisAgent:
        if self._diagnosis_agent is None:
            self._diagnosis_agent = DiagnosisAgent(provider=self.provider)
        return self._diagnosis_agent

    @property
    def rewrite_coordinator(self) -> RewriteCoordinator:
        """Lazily-built rewrite coordinator.

        Built on first access. Reused across the lifetime of this
        TestGenerator, so the per-component idempotency set carries
        across phase-4 calls within one run.

        When ``self.config.enable_rewrite`` is False the generator
        never calls into this property, so the coordinator's
        dependencies are never constructed. Phase 4 gates on the
        flag and is a no-op otherwise.
        """
        if self._rewrite_coordinator is None:
            self._rewrite_coordinator = RewriteCoordinator(
                test_agent=self.test_agent,
                intent_agent=self.intent_agent,
                verifier=self.verifier,
                diagnosis_agent=self.diagnosis_agent,
            )
        return self._rewrite_coordinator

    async def generate_tests_for_module(
        self,
        module_path: str,
        components: Dict[str, Dict[str, Any]],
    ) -> TestSuite:
        """
        Generate tests for a module with verification loop.
        
        Args:
            module_path: Path to the module
            components: Component data from AST analysis
            
        Returns:
            TestSuite with all generated tests
        """
        logger.info(f"Generating tests for module: {module_path}")

        # Initialize run_id so all phases carry the same identifier.
        if self._run_id is None:
            self._run_id = new_run_id()

        # Phase 1: Extract intents
        intents = await self._extract_intents_phase(components)
        
        # Phase 2: Generate tests
        test_files = await self._generate_tests_phase(components, intents)

        # Phase 3: Verify and refine (if not dry-run)
        if not self.config.dry_run:
            test_files = await self._verify_and_refine_phase(test_files, components, intents)

        # Phase 4: Repair loop (when enabled). Only runs after phase 3
        # because we need verification_results to drive strategy
        # selection. When disabled, this is a no-op; v1.0 behavior
        # is preserved unchanged.
        if not self.config.dry_run and getattr(
            self.config, "enable_rewrite", False
        ):
            test_files = await self._rewrite_phase(
                test_files, components, intents,
            )

        # Build test suite
        suite = TestSuite(
            module_path=module_path,
            test_files=test_files,
            intents={k: v for k, v in intents.items()},
        )
        
        logger.info(f"Generated {suite.total_tests} tests across {len(test_files)} files")
        
        return suite
    
    async def _extract_intents_phase(
        self,
        components: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Intent]:
        """
        Phase 1: Extract intents for all components.
        
        Args:
            components: Component data
            
        Returns:
            Dictionary mapping component IDs to intents
        """
        logger.info("Phase 1: Extracting intents...")
        intents: Dict[str, Intent] = {}
        
        # Process in dependency order (leaves first)
        for comp_id, component in components.items():
            # Check if intent already exists
            existing = self.intent_db.get_intent(comp_id)
            if existing and existing.user_edited:
                intents[comp_id] = existing
                continue
            
            # Get dependency intents for context
            dep_intents = {
                dep: intents.get(dep)
                for dep in component.get("dependencies", [])
                if dep in intents
            }
            
            # Extract using static analysis first
            intent = self.intent_extractor.extract_intent(component, dep_intents)
            
            # If low confidence and not auto-accept, use LLM
            if intent.needs_clarification(self.config.confidence_threshold):
                if not self.config.auto_accept:
                    # Use LLM for better inference
                    try:
                        intent = await self.intent_agent.infer_intent(component, {
                            "dependencies": list(dep_intents.keys())
                        })
                    except Exception as e:
                        logger.warning(f"LLM intent inference failed: {e}")
            
            intents[comp_id] = intent
            self.intent_db.save_intent(intent)

            # Emit IntentExtracted. accepted=True when the intent clears the
            # configured confidence threshold (downstream tests will run).
            accepted = intent.confidence >= self.config.confidence_threshold
            self._publish(IntentExtracted(
                run_id=self._run_id or new_run_id(),
                component_id=comp_id,
                confidence=intent.confidence,
                accepted=accepted,
            ))

            if self.on_intent_extracted:
                self.on_intent_extracted(intent)
        
        logger.info(f"Extracted {len(intents)} intents")
        return intents
    
    async def _generate_tests_phase(
        self,
        components: Dict[str, Dict[str, Any]],
        intents: Dict[str, Intent],
    ) -> List[TestFile]:
        """
        Phase 2: Generate tests hierarchically.
        
        Args:
            components: Component data
            intents: Extracted intents
            
        Returns:
            List of generated test files
        """
        logger.info("Phase 2: Generating tests...")
        test_files: List[TestFile] = []
        
        logger.info("Phase 2: Generating tests...")
        test_files: List[TestFile] = []
        
        # Concurrency limit
        semaphore = asyncio.Semaphore(5)
        
        async def process_component(comp_id: str, component: Dict[str, Any]) -> Optional[TestFile]:
            async with semaphore:
                intent = intents.get(comp_id)
                if not intent:
                    return None
                
                # Incremental check: if verified test exists and intent hasn't changed, skip
                # This is a basic check. Ideally we'd compare timestamps or hashes.
                existing_test_files = self.test_registry.get_tests_for_component(comp_id)
                if existing_test_files:
                     # For now, if we have any existing test, simpler logic:
                     # If verified, skip.
                     # If auto-mode and verified, definitely skip.
                     is_verified = any(t.verified for t in existing_test_files)
                     if is_verified and self.config.auto_accept:
                         logger.info(f"Skipping {comp_id} (already verified)")
                         return None

                # Skip low-confidence intents in auto mode
                if self.config.auto_accept and intent.confidence < self.config.confidence_threshold:
                    logger.info(f"Skipping {comp_id} (low confidence: {intent.confidence:.0%})")
                    return None
                
                try:
                    test_file = await self.test_agent.generate_unit_tests(
                        component,
                        intent,
                        self.config.framework,
                    )

                    if test_file.test_cases:
                        self.test_registry.register_test(test_file)
                        # Emit TestsGenerated. M1B.2 invariant: production
                        # default sink absorbs; benchmark collector emits.
                        self._publish(TestsGenerated(
                            run_id=self._run_id or new_run_id(),
                            component_id=comp_id,
                            test_file_path=test_file.path,
                            test_count=len(test_file.test_cases),
                        ))
                        if self.on_test_generated:
                            self.on_test_generated(test_file)
                        return test_file
                            
                except Exception as e:
                    logger.error(f"Test generation failed for {comp_id}: {e}")
                    return None
                    
        # Create tasks
        tasks = [
            process_component(cid, comp) 
            for cid, comp in components.items()
        ]
        
        # Run tasks
        results = await asyncio.gather(*tasks)
        test_files = [r for r in results if r is not None]
        
        logger.info(f"Generated {len(test_files)} test files")
        return test_files
    
    async def _verify_and_refine_phase(
        self,
        test_files: List[TestFile],
        components: Dict[str, Dict[str, Any]],
        intents: Dict[str, Intent],
    ) -> List[TestFile]:
        """
        Phase 3: Verify and refine tests.
        
        Args:
            test_files: Generated test files
            components: Component data
            intents: Extracted intents
            
        Returns:
            Refined test files
        """
        logger.info("Phase 3: Verifying tests...")
        
        for test_file in test_files:
            # Validate syntax first
            valid, error = self.verifier.validate_syntax(test_file)
            if not valid:
                logger.warning(f"Syntax error in {test_file.path}: {error}")
                continue
            
            # Run tests
            result = self.verifier.run_tests(test_file)

            if self.on_verification_complete:
                self.on_verification_complete(result)

            # Emit VerificationCompleted. Pass/fail counts come from
            # the verifier result; failure_ids is the tuple of failed
            # test names for downstream diagnosis correlation.
            self._publish(VerificationCompleted(
                run_id=self._run_id or new_run_id(),
                component_id=test_file.component_id,
                passed=len(result.passed),
                failed=len(result.failed),
                failure_ids=tuple(result.failed),
            ))
            # Stash the verification result so phase 4 can pass it
            # to the rewrite coordinator without re-running the
            # verifier. We capture per-component_id; the rewrite
            # coordinator reads this when it's called.
            self._last_verification[test_file.component_id] = result

            # Diagnose failures
            if not result.all_passed:
                for tc in test_file.test_cases:
                    if tc.status == TestStatus.FAILED:
                        component = components.get(test_file.component_id, {})
                        intent = intents.get(test_file.component_id)

                        if intent:
                            try:
                                diagnosis = await self.diagnosis_agent.diagnose_failure(
                                    tc,
                                    tc.failure_message or "",
                                    component,
                                    intent,
                                )
                                tc.diagnosis = diagnosis
                                # Emit DiagnosisTriggered after the agent
                                # successfully classifies the failure.
                                self._publish(DiagnosisTriggered(
                                    run_id=self._run_id or new_run_id(),
                                    component_id=test_file.component_id,
                                    failure_id=tc.name,
                                    cause=diagnosis.cause.value if hasattr(diagnosis.cause, "value") else str(diagnosis.cause),
                                    diagnosis_confidence=diagnosis.confidence,
                                ))
                            except Exception as e:
                                logger.error(f"Diagnosis failed: {e}")
            
            # Mark verified
            if result.all_passed:
                test_file.verified = True
                self.test_registry.mark_verified(test_file.path)

        return test_files

    async def _rewrite_phase(
        self,
        test_files: List[TestFile],
        components: Dict[str, Dict[str, Any]],
        intents: Dict[str, Intent],
    ) -> List[TestFile]:
        """Phase 4: repair loop.

        For each test_file that failed verification, ask the rewrite
        coordinator for one repair attempt. On success the candidate
        replaces the original in the returned list. The coordinator
        enforces the per-component invariant (one attempt per
        component per run).

        After all rewrites are attempted, the full suite is
        re-verified exactly once to confirm no regressions in
        non-rewritten components. This is what catches a rewrite
        that traded one test for another.

        Telemetry: every rewrite attempt emits a RewriteAttempted
        event with three timing fields (verification_before_seconds,
        rewrite_elapsed, verification_after_seconds) plus
        strategy, failure_classification, success, tests_before,
        tests_after.
        """
        # The architecture is:
        #   VerificationCompleted (phase 3)
        #       |
        #   rewrite_coordinator (per failing component)
        #       |
        #   VerificationCompleted (phase 4 final re-run)
        run_id = self._run_id or new_run_id()
        rewrites_attempted: List[Any] = []
        rewrite_indices: Dict[str, int] = {}

        for index, test_file in enumerate(test_files):
            if test_file.verified:
                continue
            verification_result = self._last_verification.get(
                test_file.component_id
            )
            if verification_result is None:
                # No verification record; nothing to drive a rewrite.
                continue
            if getattr(verification_result, "all_passed", True):
                # Nothing to fix; phase 3 already marked verified.
                continue

            component = components.get(test_file.component_id, {})
            intent = intents.get(test_file.component_id)
            if intent is None:
                continue

            outcome = await self.rewrite_coordinator.attempt_rewrite(
                run_id=run_id,
                component_id=test_file.component_id,
                original_test_file=test_file,
                component=component,
                intent=intent,
                verification_result=verification_result,
                test_cases=test_file.test_cases,
                framework=test_file.framework,
            )
            rewrites_attempted.append(outcome)
            rewrite_indices[test_file.component_id] = index

            # Emit the event. Six fields populated by the coordinator;
            # we add component_id, failure_id (we use the first failed
            # test name), and the run_id.
            failed_ids = list(getattr(verification_result, "failed", []))
            first_failure_id = failed_ids[0] if failed_ids else "unknown"
            self._publish(RewriteAttempted(
                run_id=run_id,
                component_id=test_file.component_id,
                failure_id=first_failure_id,
                strategy=outcome.strategy.value,
                failure_classification=outcome.failure_classification,
                success=outcome.success,
                elapsed_seconds=outcome.rewrite_elapsed,
            ))

            # Transactional commit: replace the test_file with the
            # candidate only on success.
            if outcome.success and outcome.new_test_file is not None:
                test_files[index] = outcome.new_test_file

        # Full-suite re-run after every successful rewrite to detect
        # silent regressions. One re-run, not per-rewrite, because
        # the verifier's per-test-file write semantics means a
        # rewrite of one component doesn't overwrite another
        # component's on-disk tests.
        #
        # IMPORTANT: this re-run does NOT emit VerificationCompleted
        # events. The metric counters (diagnosis_trigger_rate,
        # rewrite_attempt_rate) are computed from phase-3 events
        # only. Phase-4 VerificationCompleted events would inflate
        # the failure-count denominators and make the metrics look
        # worse than they are. The re-run's job is to update
        # test_registry state, not the metrics.
        if any(o.success for o in rewrites_attempted):
            for test_file in test_files:
                if test_file.verified:
                    continue
                valid, _ = self.verifier.validate_syntax(test_file)
                if not valid:
                    continue
                result = self.verifier.run_tests(test_file)
                if result.all_passed:
                    test_file.verified = True
                    self.test_registry.mark_verified(test_file.path)
                else:
                    test_file.verified = False

        return test_files

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        intent_stats = self.intent_db.get_stats()
        test_stats = self.test_registry.get_stats()
        
        return {
            **intent_stats,
            **test_stats,
        }

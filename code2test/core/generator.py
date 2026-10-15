"""
Code2Test Generator

Main orchestrator for the test generation pipeline.
"""

import logging
import asyncio
import os
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
    DiagnosisCause,
)
from code2test.core.intent import IntentExtractor
from code2test.core.verifier import TestVerifier
from code2test.storage.intent_db import IntentDatabase
from code2test.storage.test_registry import TestRegistry
from code2test.agents.intent_agent import IntentAgent
from code2test.agents.test_agent import TestAgent
from code2test.agents.diagnosis_agent import DiagnosisAgent
from code2test.agents.errors import raise_if_fatal

logger = logging.getLogger(__name__)


class TestGenerator:
    """
    Main test generation orchestrator.
    
    Coordinates the three-phase pipeline:
    1. Intent extraction
    2. Test generation
    3. Verification and refinement
    """

    __test__ = False  # not a pytest test class
    
    def __init__(
        self,
        repo_path: str,
        db_path: Optional[str] = None,
        config: Optional[GenerationConfig] = None,
    ):
        """
        Initialize test generator.
        
        Args:
            repo_path: Path to the repository root
            db_path: Path to database for persistence
            config: Generation configuration
        """
        self.repo_path = Path(repo_path)
        self.config = config or GenerationConfig()
        
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
    
    @property
    def intent_agent(self) -> IntentAgent:
        if self._intent_agent is None:
            self._intent_agent = IntentAgent(model=self.config.model)
        return self._intent_agent
    
    @property
    def test_agent(self) -> TestAgent:
        if self._test_agent is None:
            self._test_agent = TestAgent(
                model=self.config.model,
                repo_path=str(self.repo_path),
                output_dir=self.config.output_dir or "tests",
            )
        return self._test_agent
    
    @property
    def diagnosis_agent(self) -> DiagnosisAgent:
        if self._diagnosis_agent is None:
            self._diagnosis_agent = DiagnosisAgent(model=self.config.model)
        return self._diagnosis_agent
    
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
        
        # Phase 1: Extract intents
        intents = await self._extract_intents_phase(components)
        
        # Phase 2: Generate tests
        test_files = await self._generate_tests_phase(components, intents)
        
        # Phase 3: Verify and refine (if not dry-run)
        if not self.config.dry_run:
            test_files = await self._verify_and_refine_phase(test_files, components, intents)
        
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
        
        # Static analysis first, in dependency order (leaves first)
        for comp_id, component in components.items():
            # Keep intents the user has edited
            existing = self.intent_db.get_intent(comp_id)
            if existing and existing.user_edited:
                intents[comp_id] = existing
                continue

            dep_intents = {
                dep: intents.get(dep)
                for dep in component.get("dependencies", [])
                if dep in intents
            }
            intents[comp_id] = self.intent_extractor.extract_intent(component, dep_intents)

        # Ask the LLM about components static analysis isn't sure about
        semaphore = asyncio.Semaphore(5)

        async def refine(comp_id: str) -> None:
            intent = intents[comp_id]
            if intent.user_edited or not intent.needs_clarification(self.config.confidence_threshold):
                return
            component = components[comp_id]
            async with semaphore:
                try:
                    inferred = await self.intent_agent.infer_intent(component, {
                        "dependencies": component.get("dependencies", []),
                    })
                except Exception as e:
                    raise_if_fatal(e)
                    logger.warning(f"LLM intent inference failed for {comp_id}: {e}")
                    return
            if inferred.confidence > intent.confidence:
                intents[comp_id] = inferred

        await asyncio.gather(*(refine(cid) for cid in intents))

        for intent in intents.values():
            self.intent_db.save_intent(intent)
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
                        if self.on_test_generated:
                            self.on_test_generated(test_file)
                        return test_file
                            
                except Exception as e:
                    raise_if_fatal(e)
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

        # Each verification is a pytest subprocess: run one per CPU
        semaphore = asyncio.Semaphore(max(2, os.cpu_count() or 2))

        async def verify(test_file: TestFile) -> Optional[TestFile]:
            async with semaphore:
                return await self.verify_and_fix(
                    test_file,
                    components.get(test_file.component_id, {}),
                    intents.get(test_file.component_id),
                )

        results = await asyncio.gather(*(verify(tf) for tf in test_files))
        return [tf for tf in results if tf is not None]

    async def _run_verifier(self, test_file: TestFile) -> VerificationResult:
        """Run the verifier (blocking subprocess) without stalling the event loop."""
        # Syntax errors in individual tests: report them per test instead of running pytest
        valid, error = self.verifier.validate_syntax(test_file)
        if not valid:
            bad = []
            for tc in test_file.test_cases:
                try:
                    compile(tc.test_code, tc.name, "exec")
                except SyntaxError as e:
                    tc.mark_failed(f"SyntaxError at line {e.lineno}: {e.msg}")
                    bad.append(tc.name)
            if not bad:  # the imports/fixtures are broken: every test is affected
                for tc in test_file.test_cases:
                    tc.mark_failed(error or "SyntaxError")
                bad = [tc.name for tc in test_file.test_cases]
            return VerificationResult(test_file_path=test_file.path, all_passed=False, failed=bad)
        return await asyncio.to_thread(self.verifier.run_tests, test_file)

    async def verify_and_fix(
        self,
        test_file: TestFile,
        component: Dict[str, Any],
        intent: Optional[Intent],
    ) -> Optional[TestFile]:
        """
        Run a generated test file and repair it until it passes.

        1. Run the tests.
        2. Send failing tests back to the model with their failure output (up to
           ``config.max_fix_attempts`` rounds).
        3. Tests that still fail are diagnosed: likely bugs in the code under test are
           kept as ``xfail`` with the reason, everything else is dropped. This keeps
           the written suite green while still surfacing suspected bugs.

        Returns the final test file, or None if no tests survived (file removed).
        """
        result = await self._run_verifier(test_file)

        for attempt in range(self.config.max_fix_attempts):
            failing = [tc for tc in test_file.test_cases if tc.status == TestStatus.FAILED]
            if result.all_passed or not failing or intent is None:
                break
            logger.info(f"Repairing {len(failing)} failing test(s) in {test_file.path} (attempt {attempt + 1})")
            test_file = await self.test_agent.fix_tests(test_file, failing, component, intent)
            result = await self._run_verifier(test_file)

        if self.on_verification_complete:
            self.on_verification_complete(result)

        failing = [tc for tc in test_file.test_cases if tc.status == TestStatus.FAILED]
        if failing:
            kept = []
            failing_names = {tc.name for tc in failing}
            for tc in test_file.test_cases:
                if tc.name not in failing_names:
                    kept.append(tc)
                    continue
                diagnosis = None
                if intent is not None:
                    try:
                        diagnosis = await self.diagnosis_agent.diagnose_failure(
                            tc, tc.failure_message or "", component, intent
                        )
                    except Exception as e:
                        raise_if_fatal(e)
                        logger.error(f"Diagnosis failed: {e}")
                tc.diagnosis = diagnosis
                if diagnosis and diagnosis.cause == DiagnosisCause.CODE_BUG:
                    reason = f"code2test: possible bug - {diagnosis.explanation}"[:300]
                    tc.test_code = f"@pytest.mark.xfail(reason={reason!r}, strict=False)\n{tc.test_code}"
                    kept.append(tc)
                    logger.warning(f"{test_file.path}::{tc.name} kept as xfail: {diagnosis.explanation}")
                else:
                    logger.info(f"Dropping failing test {test_file.path}::{tc.name}")

            test_file = test_file.model_copy(update={"test_cases": kept})
            if not kept:
                path = self.repo_path / test_file.path
                if path.exists():
                    path.unlink()
                self.test_registry.delete_test(test_file.path)
                logger.warning(f"No passing tests for {test_file.component_id}; removed {test_file.path}")
                return None
            if not any(i.startswith("import pytest") for i in test_file.imports):
                test_file.imports.insert(0, "import pytest")
            result = await self._run_verifier(test_file)

        test_file.verified = result.all_passed
        self.test_registry.register_test(test_file)
        if test_file.verified:
            self.test_registry.mark_verified(test_file.path)
        return test_file

    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        intent_stats = self.intent_db.get_stats()
        test_stats = self.test_registry.get_stats()
        
        return {
            **intent_stats,
            **test_stats,
        }

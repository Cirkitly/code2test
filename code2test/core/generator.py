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

logger = logging.getLogger(__name__)


class TestGenerator:
    """
    Main test generation orchestrator.
    
    Coordinates the three-phase pipeline:
    1. Intent extraction
    2. Test generation
    3. Verification and refinement
    """
    
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
            self._test_agent = TestAgent(model=self.config.model)
        return self._test_agent
    
    @property
    def diagnosis_agent(self) -> DiagnosisAgent:
        if self._diagnosis_agent is None:
            self._diagnosis_agent = DiagnosisAgent()
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
                            except Exception as e:
                                logger.error(f"Diagnosis failed: {e}")
            
            # Mark verified
            if result.all_passed:
                test_file.verified = True
                self.test_registry.mark_verified(test_file.path)
        
        return test_files
    
    def get_stats(self) -> Dict[str, Any]:
        """Get generation statistics."""
        intent_stats = self.intent_db.get_stats()
        test_stats = self.test_registry.get_stats()
        
        return {
            **intent_stats,
            **test_stats,
        }

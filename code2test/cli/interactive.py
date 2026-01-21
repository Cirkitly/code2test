"""
Code2Test Interactive CLI Module

Claude Code-style interactive prompts for test generation.
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

import click
from rich.console import Console
from rich.prompt import Prompt, Confirm

from code2test.core.models import (
    Intent,
    TestCase,
    TestFile,
    Diagnosis,
    DiagnosisCause,
    VerificationResult,
)
from code2test.cli.display import DisplayManager


class UserAction(str, Enum):
    """User actions for interactive prompts."""
    ACCEPT = "accept"
    SKIP = "skip"
    EDIT = "edit"
    RUN = "run"
    FIX = "fix"
    FLAG_BUG = "flag_bug"
    EDIT_INTENT = "edit_intent"
    KEEP_XFAIL = "keep_xfail"


class InteractiveSession:
    """
    Manages interactive test generation session.
    
    Provides Claude Code-style prompts for user decision making.
    """
    
    def __init__(self, display: Optional[DisplayManager] = None):
        """
        Initialize interactive session.
        
        Args:
            display: Display manager for output
        """
        self.display = display or DisplayManager()
        self.console = Console()
    
    def present_intent(
        self,
        intent: Intent,
        component_name: str = ""
    ) -> UserAction:
        """
        Present inferred intent and get user action.
        
        Args:
            intent: Inferred intent
            component_name: Name of the component
            
        Returns:
            User's chosen action
        """
        self.display.show_intent(intent, component_name)
        
        if intent.needs_clarification():
            self.display.warning(f"Low confidence ({intent.confidence:.0%})")
        
        choices = "[y] Accept  [n] Skip  [e] Edit intent"
        self.display.show_prompt("", choices)
        
        choice = Prompt.ask(
            ">",
            choices=["y", "n", "e"],
            default="y" if intent.confidence >= 0.8 else "n"
        )
        
        if choice == "y":
            return UserAction.ACCEPT
        elif choice == "e":
            return UserAction.EDIT_INTENT
        else:
            return UserAction.SKIP
    
    def present_tests(
        self,
        test_file: TestFile,
        intent: Intent
    ) -> UserAction:
        """
        Present generated tests and get user action.
        
        Args:
            test_file: Generated test file
            intent: Associated intent
            
        Returns:
            User's chosen action
        """
        self.display.show_test_preview(test_file)
        
        choices = "[y] Accept  [n] Skip  [e] Edit  [r] Run first  [i] Edit intent"
        self.display.show_prompt("", choices)
        
        choice = Prompt.ask(
            ">",
            choices=["y", "n", "e", "r", "i"],
            default="r"
        )
        
        if choice == "y":
            return UserAction.ACCEPT
        elif choice == "r":
            return UserAction.RUN
        elif choice == "e":
            return UserAction.EDIT
        elif choice == "i":
            return UserAction.EDIT_INTENT
        else:
            return UserAction.SKIP
    
    def present_verification_result(
        self,
        result: VerificationResult,
        test_file: TestFile
    ) -> UserAction:
        """
        Present verification results and get user action.
        
        Args:
            result: Verification result
            test_file: The test file
            
        Returns:
            User's chosen action
        """
        self.display.show_verification_result(result)
        
        if result.all_passed:
            save = Confirm.ask(f"Save to {test_file.path}?", default=True)
            return UserAction.ACCEPT if save else UserAction.SKIP
        else:
            self.display.warning("Some tests failed. Review diagnoses below.")
            return UserAction.RUN  # Indicates need for diagnosis
    
    def present_diagnosis(
        self,
        diagnosis: Diagnosis,
        test_case: TestCase
    ) -> UserAction:
        """
        Present failure diagnosis and get user action.
        
        Args:
            diagnosis: Failure diagnosis
            test_case: The failing test case
            
        Returns:
            User's chosen action
        """
        self.console.print()
        self.console.print(f"✗ {test_case.name} [red]FAILED[/red]")
        
        if test_case.failure_message:
            self.console.print(f"  [dim]{test_case.failure_message[:100]}...[/dim]")
        
        self.display.show_diagnosis_panel(diagnosis)
        
        # Show appropriate choices based on diagnosis
        if diagnosis.cause == DiagnosisCause.TEST_WRONG:
            choices = "[f] Fix test  [k] Keep (xfail)  [s] Skip"
            valid_choices = ["f", "k", "s"]
        elif diagnosis.cause == DiagnosisCause.CODE_BUG:
            choices = "[b] Flag as bug  [f] Fix test anyway  [s] Skip"
            valid_choices = ["b", "f", "s"]
        else:  # INTENT_WRONG
            choices = "[i] Edit intent  [f] Fix test  [s] Skip"
            valid_choices = ["i", "f", "s"]
        
        self.display.show_prompt("", choices)
        
        choice = Prompt.ask(">", choices=valid_choices, default="s")
        
        if choice == "f":
            return UserAction.FIX
        elif choice == "b":
            return UserAction.FLAG_BUG
        elif choice == "i":
            return UserAction.EDIT_INTENT
        elif choice == "k":
            return UserAction.KEEP_XFAIL
        else:
            return UserAction.SKIP
    
    def request_intent_clarification(
        self,
        intent: Intent,
        questions: List[str]
    ) -> str:
        """
        Request user clarification for low-confidence intent.
        
        Args:
            intent: The low-confidence intent
            questions: Clarification questions
            
        Returns:
            User's description of intended behavior
        """
        self.console.print()
        self.display.warning(
            f"Low confidence intent ({intent.confidence:.0%}) for {intent.component_id}"
        )
        self.console.print()
        self.console.print(f'Current: [dim]"{intent.intent_text}"[/dim]')
        self.console.print()
        
        if questions:
            self.console.print("Unclear aspects:")
            for q in questions:
                self.console.print(f"  • {q}")
            self.console.print()
        
        user_input = Prompt.ask("Please describe the intended behavior")
        
        return user_input.strip()
    
    def edit_intent(self, intent: Intent) -> str:
        """
        Allow user to edit intent text.
        
        Args:
            intent: Current intent
            
        Returns:
            Updated intent text
        """
        self.console.print()
        self.console.print(f'Current intent: [dim]"{intent.intent_text}"[/dim]')
        self.console.print()
        
        new_intent = Prompt.ask(
            "New intent (or Enter to keep)",
            default=intent.intent_text
        )
        
        return new_intent.strip()
    
    def confirm_save(self, path: str) -> bool:
        """
        Confirm saving to a path.
        
        Args:
            path: File path
            
        Returns:
            True if user confirms
        """
        return Confirm.ask(f"Save to [cyan]{path}[/cyan]?", default=True)
    
    def confirm_batch(
        self,
        count: int,
        action: str = "generate tests for"
    ) -> bool:
        """
        Confirm batch operation.
        
        Args:
            count: Number of items
            action: Action description
            
        Returns:
            True if user confirms
        """
        return Confirm.ask(
            f"[yellow]About to {action} {count} components. Continue?[/yellow]",
            default=True
        )


def run_interactive_generation(
    generator,
    components: Dict[str, Any],
    auto_accept: bool = False
) -> None:
    """
    Run interactive test generation session.
    
    Args:
        generator: TestGenerator instance
        components: Components to generate tests for
        auto_accept: Auto-accept high confidence results
    """
    session = InteractiveSession()
    display = session.display
    
    # Confirm batch operation
    if not session.confirm_batch(len(components)):
        display.info("Generation cancelled.")
        return
    
    async def run():
        skipped = 0
        generated = 0
        
        for comp_id, component in components.items():
            # Extract intent
            intent = generator.intent_extractor.extract_intent(component, {})
            
            # Present intent
            if not auto_accept or intent.needs_clarification():
                action = session.present_intent(intent, component.get("name", ""))
                
                if action == UserAction.SKIP:
                    skipped += 1
                    continue
                elif action == UserAction.EDIT_INTENT:
                    new_text = session.edit_intent(intent)
                    intent.update_intent(new_text)
            
            # Generate tests
            test_file = await generator.test_agent.generate_unit_tests(
                component, intent
            )
            
            if not test_file.test_cases:
                display.warning(f"No tests generated for {comp_id}")
                continue
            
            # Present tests
            if not auto_accept:
                action = session.present_tests(test_file, intent)
                
                if action == UserAction.SKIP:
                    skipped += 1
                    continue
                elif action == UserAction.RUN:
                    # Run verification
                    result = generator.verifier.run_tests(test_file)
                    action = session.present_verification_result(result, test_file)
                    
                    if action != UserAction.ACCEPT:
                        # Handle failures
                        for tc in test_file.test_cases:
                            if tc.diagnosis:
                                session.present_diagnosis(tc.diagnosis, tc)
            
            # Save test file
            if session.confirm_save(test_file.path):
                generator.verifier.write_test_file(test_file)
                generator.test_registry.register_test(test_file)
                generated += 1
                display.success(f"Saved {test_file.path}")
        
        # Show summary
        display.show_summary_table({
            "total_intents": len(components),
            "total_test_files": generated,
            "skipped": skipped,
        })
    
    asyncio.run(run())

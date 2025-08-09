import argparse
import asyncio
import os
import json
import yaml
from pathlib import Path
from dotenv import load_dotenv
import tempfile

load_dotenv()

from offline_flow import create_offline_flow
from online_flow import create_planning_flow
# --- START OF FIX ---
# Import the node classes directly so we can instantiate them
from nodes.generation_nodes import GenerateSingleTestNode, HealNode
from nodes.verification_nodes import VerifySingleTestNode, FinalizeAndOrganizeNode
from online_flow import LoadContextNode 
# --- END OF FIX ---


KG_FILE_PATH = "knowledge_graph.json"
STATE_FILE_PATH = "test_execution_state.yaml"
MAX_HEAL_ATTEMPTS = 2 # Allow the agent to try fixing a test twice before giving up

def validate_environment():
    print("Validating environment configuration...")
    provider = os.getenv("LLM_PROVIDER", "azure")
    required_vars = ["EMBEDDING_MODEL"]
    if provider == 'azure':
        required_vars.extend(["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"])
    elif provider == 'ollama':
        required_vars.extend(["OLLAMA_MODEL", "OLLAMA_URL"])
    else:
        print(f"FATAL ERROR: Unsupported LLM_PROVIDER '{provider}'. Must be 'azure' or 'ollama'.")
        return False

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"\nFATAL ERROR: Missing required environment variables: {missing_vars}\n")
        return False
    print(f"✅ Environment validated successfully for LLM_PROVIDER='{provider}'.")
    return True


async def main():
    if not validate_environment():
        exit(1)

    parser = argparse.ArgumentParser(description="AI Software Foundry - Test Generator")
    parser.add_argument("--repo-path", required=True, help="Path to the code repository to analyze.")
    parser.add_argument("--run-phase", choices=['offline', 'online'], required=True, help="Which phase to run.")
    args = parser.parse_args()

    shared = {
        "repo_path": args.repo_path,
        "source_files_content": {},
        "generated_files": {},
    }

    if args.run_phase == 'offline':
        print("\n--- Starting Phase 1: Offline Indexing ---")
        offline_flow = create_offline_flow()
        offline_flow.set_params({"repo_path": args.repo_path})
        await offline_flow.run_async(shared)

        if shared.get("knowledge_graph_data"):
            with open(KG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(shared["knowledge_graph_data"], f, indent=2)
            print(f"Knowledge Graph saved to {KG_FILE_PATH}")
        else:
            print("Warning: Knowledge graph was not created or is empty.")
        print("--- Offline Indexing Complete ---")

    elif args.run_phase == 'online':
        if not os.path.exists(KG_FILE_PATH):
            print(f"Error: Knowledge Graph file '{KG_FILE_PATH}' not found. Please run the 'offline' phase first.")
            return

        print("\n--- Starting Phase 2: Online Test Generation (Incremental Mode) ---")

        with tempfile.TemporaryDirectory() as sandbox_path:
            print(f"Created persistent sandbox for this run at: {sandbox_path}")

            if os.path.exists(STATE_FILE_PATH):
                print(f"Found existing state file at '{STATE_FILE_PATH}'. Resuming...")
                with open(STATE_FILE_PATH, 'r', encoding='utf-8') as f:
                    test_plan = yaml.safe_load(f)
            else:
                print("No state file found. Generating a new test plan...")
                planning_flow = create_planning_flow()
                planning_flow.set_params({"knowledge_graph_path": KG_FILE_PATH})
                await planning_flow.run_async(shared)
                test_plan = shared.get("test_plan")

            if not test_plan or "test_cases" not in test_plan:
                print("Error: Test plan is invalid or empty. Exiting.")
                return

            # Load project context once at the beginning
            if "project_analysis" not in shared:
                load_context_node = LoadContextNode()
                load_context_node.set_params({"knowledge_graph_path": KG_FILE_PATH})
                load_context_node.run(shared)

            test_cases = test_plan["test_cases"]
            total_cases = len(test_cases)
            print(f"Loaded {total_cases} test cases to process.")

            # Create single instances of nodes to be reused
            generate_node = GenerateSingleTestNode()
            generate_node.set_params({"repo_path": args.repo_path})
            
            verify_node = VerifySingleTestNode()
            verify_node.set_params({"sandbox_path": sandbox_path})
            
            heal_node = HealNode()
            heal_node.set_params({"max_retries": 1})

            for i, test_case in enumerate(test_cases):
                print("-" * 50)
                print(f"Processing case {i+1}/{total_cases}: {test_case['id']} (Priority: {test_case.get('priority', 'N/A')})")

                if test_case.get("status") == "PASSED":
                    print("Status is already PASSED. Skipping.")
                    continue

                # Step 1: Generate the test code ONCE.
                if not test_case.get("generated", False):
                    shared["current_test_case"] = test_case
                    await generate_node.run_async(shared)
                    test_case["generated"] = True 
                
                # Step 2: Initial Verification
                shared["current_test_case"] = test_case
                verify_result = await verify_node.run_async(shared)
                
                is_passed = (verify_result == "success")

                # Step 3: Enter the Healing Loop if initial verification fails
                heal_attempts = test_case.get("heal_attempts", 0)
                while not is_passed and heal_attempts < MAX_HEAL_ATTEMPTS:
                    print(f"Entering healing attempt {heal_attempts + 1}/{MAX_HEAL_ATTEMPTS}...")
                    
                    heal_result = await heal_node.run_async(shared)

                    if heal_result == "patched":
                        verify_result = await verify_node.run_async(shared)
                        is_passed = (verify_result == "success")
                    else:
                        print("Agent determined the issue is unpatchable.")
                        break

                    heal_attempts += 1
                    test_case["heal_attempts"] = heal_attempts
                
                # Step 4: Final Status Update
                if is_passed:
                    test_case["status"] = "PASSED"
                else:
                    print(f"Max heal attempts reached for {test_case['id']}. Marking as FAILED.")
                    test_case["status"] = "FAILED_UNFIXABLE"
                    result = shared.get("current_test_case_result", {})
                    test_case["last_error"] = result.get("stderr", "Unknown error")

                with open(STATE_FILE_PATH, 'w', encoding='utf-8') as f:
                    yaml.dump(test_plan, f, indent=2, default_flow_style=False, sort_keys=False)
                print(f"Saved progress to {STATE_FILE_PATH}. Current Status: {test_case['status']}")

            print("\n--- All test cases processed. Finalizing... ---")
            
            finalize_node = FinalizeAndOrganizeNode()
            finalize_node.set_params({"repo_path": args.repo_path})
            finalize_node.run(shared)

        print("--- Online Generation Complete ---")
        print("All test cases processed. Final state saved to:", STATE_FILE_PATH)

if __name__ == "__main__":
    asyncio.run(main())
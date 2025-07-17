import argparse
import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from offline_flow import create_offline_flow
from online_flow import create_online_flow

KG_FILE_PATH = "knowledge_graph.json"

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

    shared = {"repo_path": args.repo_path}

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

        print("\n--- Starting Phase 2: Online Test Generation ---")
        online_flow = create_online_flow()
        # FIX: Pass the repo_path and KG path as params. The flow handles loading.
        online_flow.set_params({
            "repo_path": args.repo_path,
            "knowledge_graph_path": KG_FILE_PATH,
            "project_analysis": shared.get("project_analysis", {}) # Pass analysis data
        })
        await online_flow.run_async(shared)
        print("--- Online Generation Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
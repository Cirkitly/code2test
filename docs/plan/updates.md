## AI Software Foundry: Development Checklist

### Phase 1: Foundational Architecture & Offline Indexing

This phase focuses on understanding the codebase and building our long-term memory.

-   [x] **Setup & Configuration (`main.py`, `.env`)**
    -   [x] Create CLI entry point with `argparse`.
    -   [x] Implement robust environment validation (`validate_environment`).
    -   [x] Support multiple LLM providers (`LLM_PROVIDER`).
    -   [x] Support separate, local embedding models (`EMBEDDING_MODEL`).

-   [x] **Utilities (`utils/`)**
    -   [x] **LLM Wrapper (`call_llm.py`, `async_call_llm.py`):** Create a robust, provider-agnostic LLM utility with logging and caching. Wrap it for async use.
    -   [x] **Code Discovery (`code_utils.py`):** Implement functions to find all source files and extract code units (functions/classes).
    -   [x] **Knowledge Graph (`knowledge_graph.py`):**
        -   [x] Implement `get_embedding` using the local Ollama model.
        -   [x] Implement FAISS index initialization and in-memory metadata storage.
        -   [x] Implement `add_to_index` and `query_index` functions.
        -   [x] Implement `get_knowledge_graph_data_for_saving` to persist the KG state.
    -   [x] **Sandbox Executor (`sandbox_executor.py`):** Implement a utility to safely run `pytest` in a temporary, isolated environment.

-   [x] **Offline Workflow (`offline_flow.py`, `nodes/analysis_nodes.py`)**
    -   [x] **`DiscoverProjectNode`:** Successfully scans the repository and identifies source files.
    -   [x] **`GenerateSummariesNode`:** Correctly iterates through all code units in parallel, calls the LLM for summaries, and collects the results.
    -   [x] **`BuildKnowledgeGraphNode`:** Correctly embeds all summaries in parallel using the local embedding model and populates the FAISS index.
    -   [x] **Flow Orchestration:** All offline nodes are connected and execute in the correct sequence.
    -   [x] **State Persistence:** The completed Knowledge Graph and project analysis data are successfully saved to `knowledge_graph.json`.

---

### Phase 2: Online Generation & Self-Healing Loop

This phase focuses on using the Knowledge Graph to autonomously generate and verify a test suite.

-   [x] **Online Workflow Setup (`online_flow.py`)**
    -   [x] **`LoadContextNode`:** Successfully loads `project_analysis` from the saved `knowledge_graph.json` into the `shared` store at the start of the flow.
    -   [x] **State Passing:** Corrected the logic to pass data between nodes via the `shared` store, not `params`.

-   [ ] **Test Planning & Generation (`nodes/generation_nodes.py`)**
    -   [x] **`PlanTestsNode`:**
        -   [x] Successfully reads `project_analysis` from the `shared` store.
        -   [ ] **[To Do/Verify]** Confirm that the LLM prompt consistently produces a valid YAML test plan for different codebases.
    -   [ ] **`GenerateUnitTestsNode`:**
        -   [ ] **[To Do/Verify]** Confirm that the RAG query (`query_index`) effectively retrieves relevant context for each module.
        -   [ ] **[To Do/Verify]** Confirm that the LLM prompt consistently generates valid, runnable `pytest` code.
        -   [ ] **[To Do/Verify]** Implement `GenerateMocksNode` if complex mocking is required (currently a placeholder in the plan).
    -   [ ] **`GenerateIntegrationTestsNode`:**
        -   [ ] **[To Do]** Implement this node. It should read the `integration_test_tasks` from the test plan, query the KG for context on all `modules_involved`, and generate a test file that verifies their interaction.

-   [ ] **Verification & Healing Loop (`nodes/verification_nodes.py`, `nodes/generation_nodes.py`)**
    -   [x] **`VerifyTestsNode`:**
        -   [x] Successfully prepares files for the sandbox.
        -   [x] Executes `pytest` via the `sandbox_executor`.
        -   [x] Correctly identifies `success` and `failure` states.
    -   [ ] **`HealNode`:**
        -   [ ] **[To Do/Verify]** Confirm that the RAG query effectively retrieves relevant context based on `stderr` from a failed test.
        -   [ ] **[To Do/Verify]** Confirm that the LLM can generate a valid code patch in the correct `diff` format.
        -   [ ] **[To Do]** Implement the logic to **apply the patch** in-memory to the files in `shared["generated_files"]` or the source code before looping back to the `VerifyTestsNode`. *This is a critical missing piece.*

-   [ ] **Finalization (`nodes/verification_nodes.py`)**
    -   [x] **`FinalizeAndOrganizeNode`:** The logic to write files to the disk is implemented.
    -   [ ] **[To Do/Verify]** Confirm that this node correctly writes all files from `shared["generated_files"]` to the user's repository in their intended relative paths.

---

### Summary of Current Status & Next Steps

-   **DONE:** The entire **Offline Indexing** pipeline is complete and functional. The application can successfully learn a codebase and create a persistent Knowledge Graph.
-   **IN PROGRESS:** The **Online Generation** pipeline is architecturally sound, but its core intelligent components (`PlanTests`, `GenerateUnitTests`, `HealNode`) need to be thoroughly tested and validated for reliability.
-   **CRITICAL NEXT STEP:** Implement the in-memory **patch application logic** within the `HealNode`. Without this, the "healing" part of the loop is just a simulation. After the `HealNode` generates a patch, it needs to modify the code in the `shared` store before the next `VerifyTestsNode` run.

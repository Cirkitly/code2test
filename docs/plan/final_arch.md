### **Implementation Phases: From Core Engine to Ultimate Architecture**

| Phase | Title | Core Focus | Key `final_arch.md` Components | Pocket Flow Pattern |
| :--- | :--- | :--- | :--- | :--- |
| **Phase 1** | The Core Generate & Verify Engine | Statefully generate and run individual tests, recording pass/fail status. | `Smart Test Checklist`, `Incremental Execution Engine` | `Workflow`, `Batch` |
| **Phase 2** | The Surgical Healing Loop | Autonomously diagnose and fix failing tests with minimal, targeted patches. | `Surgical Healing System`, `Patch Database` | `Agent` |
| **Phase 3** | The Multi-Modal Intelligence Engine | Incorporate specifications (user stories, API contracts) to generate behavior-driven tests. | `Multi-Source Truth`, `Fact Extractor`, `Cross-Validator` | `RAG` |
| **Phase 4** | Full Orchestration & Enterprise Readiness | Add multi-tool routing, quality gates, human oversight, and cross-project learning. | `Smart Orchestration`, `Best-in-Class Tools`, `Learning Engine` | `Async`, `Multi-Agent` |

---

### **Phase 1: The Core Generate & Verify Engine (The MVP)**

**Goal:** To build the fundamental "spine" of the system. This phase focuses on creating a stateful, incremental process that can generate a checklist of tests and execute them one by one, reliably tracking their `PASSED` or `FAILED` status.

**Actions:**

1.  **Evolve `PlanTestsNode` to create the `Smart Test Checklist`**:
    *   Modify the LLM prompt in your `PlanTestsNode` to output a detailed YAML structure for `test_cases`, including `id`, `description`, `module_path`, and a `status` field initialized to `PENDING`. This YAML file is the physical artifact of the `Smart Test Checklist`.

2.  **Refactor `main.py` into a Stateful Orchestrator**:
    *   Change the `online` phase from running a single `Flow` to a stateful loop.
    *   **Step A:** Run a preliminary `Flow` to generate the `Smart Test Checklist` and save it to `test_execution_state.yaml`.
    *   **Step B:** Start a `for` loop that iterates through each `test_case` in the checklist.
    *   **Step C:** Inside the loop, run a new, smaller `Flow` dedicated to processing just *one* test case. This flow will use the `Incremental Execution Engine` logic.
    *   **Step D:** After each test case is processed, update its `status` in the checklist and save the `test_execution_state.yaml` file, making the entire process resilient and resumable.

3.  **Implement the `Incremental Execution Engine`**:
    *   Create granular nodes for single-test operations:
        *   **`GenerateSingleTestNode`**: Takes a `test_case` object and generates only the code for that one function, appending it to the correct in-memory test file.
        *   **`VerifySingleTestNode`**: Executes `pytest -k "test_case_id"`. This is the core of "run only failed tests" (or in this case, "run only one test at a time"). It isolates failures and provides precise error context.

**Deliverable at End of Phase 1:** A system that can generate a complete test suite plan, execute it test-by-test, and accurately report which tests passed and which failed in a persistent state file. The healing loop is not yet implemented, but the system now knows exactly *what* needs healing.

---

### **Phase 2: The Surgical Healing Loop**

**Goal:** To bring the agent to life by implementing the core "secret sauce": the ability to autonomously diagnose and fix its own broken tests. This phase directly builds the `Surgical Healing System`.

**Actions:**

1.  **Create the `Healing Flow`**:
    *   In your `main.py` orchestrator, when `VerifySingleTestNode` fails, trigger a new `healing_flow` (a dedicated `Flow`).

2.  **Implement the `ErrorAnalyzer` Node**:
    *   This `Node` receives the precise, focused `stderr` from `VerifySingleTestNode`.
    *   Its `exec()` method prompts an LLM to categorize the error (`IMPORT_ERROR`, `ASSERTION_FAILURE`, `MOCK_ERROR`) and identify the root cause. This analysis is stored in the `Shared Store`.

3.  **Implement the `SurgicalHealer` Node**:
    *   This `Node` takes the output from the `ErrorAnalyzer`.
    *   It performs a RAG query against the Knowledge Graph using the error context to find relevant source code and test patterns.
    *   It prompts the LLM to generate a minimal patch in `diff` format, constrained to change as few lines as possible.

4.  **Implement the `PatchDatabase`**:
    *   After a patch is successfully applied and verified, add a final `Node` to the healing loop called `UpdatePatchDatabase`.
    *   This node writes the mapping of `{error_category, code_context} -> {successful_patch}` into your `test_execution_state.yaml` or a separate `patch_db.json`. This is the foundation of the `LearningEngine`.

**Deliverable at End of Phase 2:** A self-correcting system. When a generated test fails, the agent can diagnose the failure, generate a targeted fix, apply it, and re-verify, turning a `FAILED` status into `PASSED`.

---

### **Phase 3: The Multi-Modal Intelligence Engine**

**Goal:** To elevate the system from a code-based generator to a specification-driven one. This phase focuses on incorporating business requirements and technical specs to produce more meaningful tests.

**Actions:**

1.  **Expand the `Offline Flow` (Fact Extraction)**:
    *   Create a new `FactExtractorNode` (or a set of them) as a `BatchNode` at the beginning of your `offline_flow`.
    *   This node will parse different `Multi-Source Truth` inputs: `.md` files for user stories, OpenAPI/YAML files for API specs, and type definition files.
    *   It will extract structured "facts" (e.g., "User story X requires function Y to return Z") and add them to the Knowledge Graph with a special `spec` tag.

2.  **Implement the `CrossValidator` Node**:
    *   Add this `Node` to the offline flow after fact extraction.
    *   It queries the Knowledge Graph for both `code` facts and `spec` facts.
    *   It identifies and flags mismatches:
        *   **Coverage Gaps**: A spec exists but no code implements it.
        *   **Contradictions**: The code's behavior (e.g., exceptions raised) does not match the API spec.

3.  **Upgrade the `StrategyOrchestrator` (Planner)**:
    *   Enhance the prompt in your `PlanTestsNode`. It should now use the output of the `CrossValidator`.
    *   The test plan should now explicitly prioritize tests for `Coverage Gaps` and `Contradictions`, ensuring the most critical, business-relevant tests are generated first.

**Deliverable at End of Phase 3:** The system generates tests that validate intended behavior, not just existing code. It can now write a failing test for a feature that hasn't been implemented yet, effectively guiding development in a TDD-like manner.

---

### **Phase 4: Full Orchestration & Enterprise Readiness**

**Goal:** To complete the vision by adding advanced routing, quality control, human oversight, and cross-project learning, making the system robust and ready for team deployment.

**Actions:**

1.  **Implement the `Multi-Tool Smart Router`**:
    *   Refactor the `GenerateSingleTestNode` from Phase 1. Instead of having one generation method, its `exec()` method will become a router.
    *   Based on context (e.g., `test_case.description`), it will select a generation strategy (a specific utility function wrapper for `Copilot`, `Hypothesis`, etc.).

2.  **Implement the `Multi-Layer Quality Gate`**:
    *   After a test is generated but before it's finalized (`PASSED`), insert a `QualityGateNode`.
    *   This `Node` runs additional checks using external tools (e.g., calls a `StaticAnalysis` or `MutationTest` utility).
    *   Its `post()` method returns an action: `quality_passed` or `quality_failed`.

3.  **Implement the `Human-in-the-Loop Controller`**:
    *   Use an `AsyncNode` to handle escalations.
    *   If the `SurgicalHealer` has a low confidence score or `QualityGateNode` fails, the `Flow` transitions to a `WaitForHumanInputNode`.
    *   This `AsyncNode` can print the issue to the console and wait for a user to type "approve," "reject," or "retry," creating a simple but effective human-in-the-loop workflow.

**Deliverable at End of Phase 4:** The complete "Ultimate Test Generation Architecture." A highly intelligent, adaptable, and robust system that orchestrates best-in-class tools, validates its own work, learns from its mistakes, and collaborates with human developers when necessary.
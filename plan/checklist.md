### **AI Software Foundry: Master Development Checklist & Strategic Roadmap**

### **Phase I: The Foundational Agent (The "Solo Developer")**

**Goal:** To build a single, robust agent that can methodically plan, generate, verify, and heal a test suite for an entire repository. This agent proves the core mechanics of the system are sound.

| Component | Item | Purpose | Status |
| :--- | :--- | :--- | :--- |
| **Core Utilities** | LLM Wrappers | To abstract away the specific LLM provider (Azure/Ollama) and centralize logging, caching, and error handling. | `✅ Complete` |
| | Knowledge Graph | To create a searchable, long-term memory of the codebase, solving the context window limitation of LLMs. | `✅ Complete` |
| | Code Discovery | To accurately identify all relevant source files for analysis, forming the basis of the agent's understanding. | `✅ Complete` |
| | Sandbox Executor | To provide a secure, isolated, and persistent environment for running generated code, crucial for safety and reliability. | `✅ Complete` |
| **Offline Workflow** | Code Indexing & Summarization | To process the entire codebase once, creating the rich data needed for the Knowledge Graph. | `✅ Complete` |
| **Online Workflow** | Planning & Test Generation | To use the Knowledge Graph to create a strategic test plan and generate the initial test code. | `✅ Complete` |
| | Verification & Healing Loop | To create the core autonomous loop (`Verify -> Heal -> Verify`) that allows the agent to be self-correcting. | `✅ Complete` |
| | Intelligent Diagnosis | To enable the `HealNode` to parse complex error reports (`stdout`/`stderr`) and identify the most likely root cause. | `✅ Complete` |
| | Advanced Patching | To empower the `HealNode` to apply patches that not only modify but also **create** new files (`__init__.py`). | `✅ Complete` |

---

#### **Phase I Status: 99% Complete. Final Blocker Identified.**

The agent is now fully built and its reasoning loop is working perfectly. However, it is stuck in a logical infinite loop.

-   **The Symptom:** The agent correctly diagnoses a packaging issue, creates a patch for `tests/__init__.py`, applies it, and upon re-running, faces the exact same set of `ModuleNotFoundError`s.
-   **The Root Cause (The "Project Contract"):** The target repository is not a valid, installable Python package. It lacks both a master dependency list and a `setup.py` file to define its own structure. **The AI cannot fix a broken environment; it can only operate within a valid one.**
-   **Our Final Task for Phase I:** We must upgrade our system to enforce this "Project Contract," making it capable of handling any standard Python project.

#### **Action Plan for Phase I Completion:**

| Item | Action Required | Definition of Done | Status |
| :--- | :--- | :--- | :--- |
| **1.1: Upgrade Sandbox** | Modify `utils/sandbox_executor.py` to find any `setup.py` in the project root and run `pip install -e .`. | The sandbox now automatically installs the project itself and its declared dependencies, solving all `ModuleNotFoundError`s related to project structure and missing packages. | `[ ] To-Do` |
| **1.2: Prepare Target Repo** | Manually create a `setup.py` file in the root of the `/tmp/PocketFlow` directory. | The target repository is now a valid, installable package that fulfills the agent's operational contract. | `[ ] To-Do` |

**The "Definition of Done" for Phase I:** The agent successfully breaks the infinite loop. The `pytest` collection errors vanish, and the agent begins making meaningful progress by finding and attempting to heal the *first real, logical test failure* (`AssertionError`, etc.).

---

### **Phase II: The "TDD Agent" with Cognitive Checklist**

**Goal:** To implement your "cognitive checklist" idea, refactoring the agent into an efficient Test-Driven Development practitioner that is significantly faster, more accurate, and more resilient.

| Item | Action Required | Purpose | Status |
| :--- | :--- | :--- | :--- |
| **2.1: Propose Test Cases** | Create a new `ProposeTestCasesNode`. | **The LLM builds the checklist.** The agent will now ask the LLM to first propose a list of specific test cases (e.g., test edge cases, valid inputs) for a given file before writing any code. | `[ ] To-Do` |
| **2.2: Implement TDD Loop** | Refactor `main.py` into a "Task Board Orchestrator". | To manage the state of each test case from the checklist (`pending`, `passed`, `failed`). This enables parallel execution and isolates failures. | `[ ] To-Do` |
| **2.3: Create Granular Agents** | Create new, specialized nodes (`Generate/Verify/HealSingleTestFunctionNode`). | To operate on one checklist item at a time. The Heal node will receive tiny, focused error reports, making its patches incredibly accurate. | `[ ] To-Do` |

**Key Benefits of Phase II:** Massive increase in speed (per-test verification), fault isolation (one failure doesn't stop others), and superior healing accuracy.

---

### **Phase III: The "AI Team" - Expanding Capabilities**

**Goal:** To build a team of specialized agents that can perform tasks beyond just unit testing, fulfilling the vision in the `README.md`.

-   `[ ] The Integration Tester Agent`
-   `[ ] The "Fix My Code" Agent (Autonomous Source Healing)`
-   `[ ] The Refactoring Agent`
-   `[ ] The Documentation Agent`

---

### **Phase IV: The "AI Teammate" - Full SDLC Integration**

**Goal:** To transform the tool from a command-line application into a true AI teammate integrated into the development lifecycle.

-   `[ ] Git-Awareness (Incremental Indexing & Testing)`
-   `[ ] GitHub API Integration (Reporting via PR Comments)`

---

### **Phase V: The "Enterprise-Grade Foundry" - Production Architecture**

**Goal:** To prepare the system for massive scale and resilience.

-   `[ ] Migrate Knowledge Graph to a dedicated Vector Database (e.g., ChromaDB, Weaviate).`
-   `[ ] Implement Stateful, Resumable Flows (e.g., with Redis).`
-   `[ ] Evolve into a Micro-Agent Architecture (Docker, Message Queues).`

---

**Our immediate and only next step is to execute the Action Plan for Phase I Completion.** Let's do this.
### Architecture Diagram

```mermaid
graph TD
    %% === STYLES ===
    classDef process fill:#e6f2ff,stroke:#b3d9ff,stroke-width:2px;
    classDef datastore fill:#e6ffe6,stroke:#b3ffb3,stroke-width:2px;
    classDef external fill:#fff0e6,stroke:#ffccb3,stroke-width:2px;
    classDef finaloutput fill:#d6d6c2,stroke:#b8b894,stroke-width:2px;
    classDef decision fill:#f2f2f2,stroke:#cccccc,stroke-width:2px;

    %% === ACTORS & EXTERNAL SERVICES ===
    subgraph Core Components
        direction LR
        LLM["Generation & Reasoning LLM"]:::external
        Embedding["Embedding Service"]:::external
        Sandbox["Execution Sandbox"]:::external
        Repo["Code Repository (File System)"]:::datastore
    end

    CLI["User via CLI (main.py)"]

    %% === PHASE 1: OFFLINE INDEXING ===
    subgraph Phase 1: Offline Indexing
        direction TB
        Discover[DiscoverProjectNode]:::process
        Summarize[GenerateSummariesNode]:::process
        BuildKG[BuildKnowledgeGraphNode]:::process
        KG_File[("knowledge_graph.json")]:::datastore

        Discover -- "Reads Files From" --> Repo
        Discover -- "File & Module List" --> Summarize
        Summarize -- "Calls for Summaries" --> LLM
        Summarize -- "Code Summaries" --> BuildKG
        BuildKG -- "Calls for Embeddings" --> Embedding
        BuildKG -- "Builds FAISS Index" --> BuildKG
        BuildKG -- "Saves Final State" --> KG_File
    end

    %% === PHASE 2: ONLINE GENERATION & HEALING ===
    subgraph Phase 2: Online Test Generation
        direction TB
        LoadContext[LoadContextNode]:::process
        Plan[PlanTestsNode]:::process
        Generate[GenerateUnitTestsNode]:::process
        Verify[VerifyTestsNode]:::process
        Heal[HealNode]:::process
        Finalize[FinalizeAndOrganizeNode]:::process
        FinalFiles[("Verified Test Files")]:::finaloutput

        LoadContext -- "Loads" --> KG_File
        LoadContext -- "Project Context" --> Plan
        Plan -- "Calls for Strategic Plan" --> LLM
        Plan -- "Test Plan (YAML)" --> Generate
        Generate -- "Queries for Context (RAG)" --> KG_File
        Generate -- "Calls for Test Code" --> LLM
        Generate -- "In-Memory Test Files" --> Verify

        Verify -- "Writes Source & Test Files" --> Sandbox
        Sandbox -- "pytest stdout/stderr" --> Verify
        Verify -- "Result" --> VerifyBranch{Verification Result?}:::decision

        VerifyBranch -- "Failure" --> Heal
        Heal -- "Queries KG with Error (RAG)" --> KG_File
        Heal -- "Calls for Patch" --> LLM
        Heal -- "Applies Patch In-Memory" --> HealBranch{Heal Attempt}:::decision
        HealBranch -- "Patched, Retry Verification" --> Verify
        HealBranch -- "Unpatchable" --> Finalize

        VerifyBranch -- "Success" --> Finalize
        Finalize -- "Writes Final Files To" --> Repo
        Repo -- "Receives" --> FinalFiles
    end

    %% === MAIN FLOW CONNECTIONS ===
    CLI -- "Starts Offline Flow" --> Discover
    CLI -- "Starts Online Flow" --> LoadContext
```

### How to Read the Diagram

1.  **Phase 1: Offline Indexing (Top-Left)**: This workflow is run once to learn about the codebase.
    *   It starts by **discovering** source files.
    *   It then **summarizes** each function/class using an LLM.
    *   Finally, it **builds the knowledge graph** by creating vector embeddings of the summaries and saves the result to `knowledge_graph.json`.

2.  **Phase 2: Online Test Generation (Top-Right)**: This workflow uses the knowledge graph to autonomously generate and fix tests.
    *   It **loads** the context from the `knowledge_graph.json` file.
    *   The **`PlanTestsNode`** creates a high-level strategy.
    *   The **`GenerateUnitTestsNode`** uses Retrieval-Augmented Generation (RAG) to query the knowledge graph for relevant context and prompts the LLM to write test code.
    *   The **`VerifyTestsNode`** runs the generated code in a secure **Sandbox**.
    *   **The Healing Loop**:
        *   If verification **fails**, the **`HealNode`** is activated. It uses the error message to query the knowledge graph for context, generates a patch, and applies it in-memory.
        *   The flow then loops back to the **`VerifyTestsNode`** to try again with the patched code.
        *   If verification **succeeds**, the flow proceeds to the final step.
    *   The **`FinalizeAndOrganizeNode`** takes the successfully verified (and potentially patched) test files and writes them to the disk.
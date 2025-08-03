### Architecture Diagram

```mermaid
graph TD
    %% === STYLES ===
    classDef process fill:#e6f2ff,stroke:#b3d9ff,stroke-width:2px;
    classDef datastore fill:#e6ffe6,stroke:#b3ffb3,stroke-width:2px;
    classDef external fill:#fff0e6,stroke:#ffccb3,stroke-width:2px;
    classDef finaloutput fill:#d6d6c2,stroke:#b8b894,stroke-width:2px;
    classDef decision fill:#f2f2f2,stroke:#cccccc,stroke-width:2px;
    classDef cache fill:#f0e6ff,stroke:#d9b3ff,stroke-width:2px;
    classDef monitor fill:#ffe6f0,stroke:#ffb3d9,stroke-width:2px;

    %% === EXTERNAL SERVICES ===
    subgraph External Services
        direction LR
        LLM["Generation & Reasoning LLM<br/>(with fallback models)"]:::external
        Embedding["Embedding Service<br/>(with caching)"]:::external
        VectorDB["Vector Database<br/>(Pinecone/Weaviate)"]:::external
        MessageQueue["Message Queue<br/>(Redis/RabbitMQ)"]:::external
    end

    %% === STORAGE LAYER ===
    subgraph Storage Layer
        direction LR
        Repo["Code Repository<br/>(Git Integration)"]:::datastore
        MetaDB["Metadata Store<br/>(PostgreSQL)"]:::datastore
        Cache["Distributed Cache<br/>(Redis)"]:::cache
        ArtifactStore["Artifact Store<br/>(S3/GCS)"]:::datastore
    end

    %% === MONITORING & OBSERVABILITY ===
    subgraph Observability
        direction LR
        Metrics["Metrics & Analytics<br/>(Prometheus/DataDog)"]:::monitor
        Logging["Structured Logging<br/>(ELK/Splunk)"]:::monitor
        Tracing["Distributed Tracing<br/>(Jaeger/Zipkin)"]:::monitor
    end

    CLI["CLI Interface<br/>(with config management)"]

    %% === PHASE 1: ENHANCED INDEXING ===
    subgraph Phase 1: Intelligent Indexing Pipeline
        direction TB
        
        subgraph Ingestion Layer
            FileWatcher["File Change Watcher<br/>(inotify/polling)"]:::process
            Parser["Multi-Language Parser<br/>(Tree-sitter based)"]:::process
            ChangeDetector["Incremental Change Detection"]:::process
        end
        
        subgraph Analysis Layer
            DependencyAnalyzer["Dependency Graph Builder"]:::process
            ComplexityAnalyzer["Code Complexity Analyzer"]:::process
            PatternExtractor["Design Pattern Extractor"]:::process
            TestabilityScorer["Testability Scorer"]:::process
        end
        
        subgraph Knowledge Management
            Chunker["Intelligent Code Chunker"]:::process
            Summarizer["Multi-Level Summarizer<br/>(function/class/module)"]:::process
            EmbeddingGenerator["Batch Embedding Generator"]:::process
            KGBuilder["Knowledge Graph Builder<br/>(with relationships)"]:::process
        end
        
        KnowledgeBase[("Enhanced Knowledge Base<br/>• Vector embeddings<br/>• Dependency graphs<br/>• Test coverage maps<br/>• Code metrics")]:::datastore
    end

    %% === PHASE 2: ENHANCED GENERATION ===
    subgraph Phase 2: Adaptive Test Generation System
        direction TB
        
        subgraph Planning & Strategy
            ContextLoader["Smart Context Loader<br/>(with relevance scoring)"]:::process
            TestPlanner["Strategic Test Planner<br/>(coverage-driven)"]:::process
            PriorityRanker["Test Priority Ranker"]:::process
        end
        
        subgraph Generation Engine
            TemplateEngine["Test Template Engine"]:::process
            CodeGenerator["Multi-Strategy Generator<br/>• Unit tests<br/>• Integration tests<br/>• Edge case tests<br/>• Performance tests"]:::process
            QualityChecker["Code Quality Checker<br/>(linting, best practices)"]:::process
        end
        
        subgraph Verification & Healing
            SandboxManager["Containerized Sandbox Manager<br/>(Docker/containerd)"]:::process
            TestRunner["Parallel Test Runner<br/>(pytest/unittest)"]:::process
            ErrorAnalyzer["AI-Powered Error Analyzer"]:::process
            AutoHealer["Multi-Strategy Auto-Healer<br/>• Syntax fixes<br/>• Import resolution<br/>• Mock injection<br/>• Test data generation"]:::process
            CoverageAnalyzer["Coverage Gap Analyzer"]:::process
        end
        
        subgraph Output Management
            TestOrganizer["Test Suite Organizer"]:::process
            DocumentationGen["Test Documentation Generator"]:::process
            ReportGenerator["Quality Report Generator"]:::process
        end
        
        FinalTestSuite[("Comprehensive Test Suite<br/>• Organized by module<br/>• With documentation<br/>• Quality reports<br/>• Coverage metrics")]:::finaloutput
    end

    %% === CONNECTIONS - PHASE 1 ===
    CLI --> FileWatcher
    FileWatcher --> Repo
    FileWatcher --> Parser
    Parser --> ChangeDetector
    ChangeDetector --> Cache
    ChangeDetector --> DependencyAnalyzer
    
    DependencyAnalyzer --> ComplexityAnalyzer
    ComplexityAnalyzer --> PatternExtractor
    PatternExtractor --> TestabilityScorer
    TestabilityScorer --> Chunker
    
    Chunker --> Summarizer
    Summarizer --> LLM
    Summarizer --> EmbeddingGenerator
    EmbeddingGenerator --> Embedding
    EmbeddingGenerator --> KGBuilder
    KGBuilder --> VectorDB
    KGBuilder --> KnowledgeBase
    
    %% === CONNECTIONS - PHASE 2 ===
    CLI --> ContextLoader
    ContextLoader --> KnowledgeBase
    ContextLoader --> VectorDB
    ContextLoader --> TestPlanner
    TestPlanner --> LLM
    TestPlanner --> PriorityRanker
    PriorityRanker --> TemplateEngine
    
    TemplateEngine --> CodeGenerator
    CodeGenerator --> LLM
    CodeGenerator --> QualityChecker
    QualityChecker --> SandboxManager
    SandboxManager --> TestRunner
    
    TestRunner --> ErrorAnalyzer
    ErrorAnalyzer --> AutoHealer
    AutoHealer --> LLM
    AutoHealer --> VectorDB
    
    %% Healing Loop
    AutoHealer --> TestRunner
    TestRunner --> CoverageAnalyzer
    CoverageAnalyzer --> TestOrganizer
    
    TestOrganizer --> DocumentationGen
    DocumentationGen --> ReportGenerator
    ReportGenerator --> FinalTestSuite
    FinalTestSuite --> Repo
    
    %% === ASYNC & CACHING CONNECTIONS ===
    MessageQueue -.->|"Async Processing"| EmbeddingGenerator
    Cache -.->|"Fast Retrieval"| ContextLoader
    Cache -.->|"Cached Results"| Summarizer
    
    %% === MONITORING CONNECTIONS ===
    Metrics -.->|"Performance Metrics"| Phase1
    Metrics -.->|"Success Rates"| Phase2
    Logging -.->|"Error Tracking"| AutoHealer
    Tracing -.->|"Request Tracing"| CodeGenerator
    
    %% === METADATA TRACKING ===
    MetaDB -.->|"Version Tracking"| KnowledgeBase
    MetaDB -.->|"Test History"| FinalTestSuite
    ArtifactStore -.->|"Large Artifacts"| KnowledgeBase
```
## **Major Enhancements**

### **1. Scalability & Performance**
- **Distributed Vector Database**: Replaced file-based storage with proper vector DB (Pinecone/Weaviate)
- **Caching Layer**: Added Redis for frequent queries and intermediate results
- **Message Queues**: Async processing for heavy operations like embedding generation
- **Containerized Sandboxes**: Better isolation and resource management

### **2. Intelligence & Context Awareness**
- **Incremental Updates**: Only reprocess changed files instead of full rebuilds
- **Multi-Level Analysis**: Dependency graphs, complexity metrics, testability scoring
- **Smart Context Loading**: Relevance scoring for better RAG retrieval
- **Coverage-Driven Planning**: Strategic test generation based on coverage gaps

### **3. Reliability & Error Handling**
- **Multi-Strategy Healing**: Different healing approaches for different error types
- **Fallback Models**: LLM redundancy for reliability
- **Quality Gates**: Code quality checks before execution
- **Parallel Processing**: Better resource utilization

### **4. Observability & Monitoring**
- **Structured Logging**: Better debugging and audit trails
- **Metrics Collection**: Performance and success rate monitoring
- **Distributed Tracing**: End-to-end request tracking
- **Quality Reports**: Comprehensive test suite analytics

### **5. Production Readiness**
- **Proper Data Persistence**: PostgreSQL for metadata, S3/GCS for artifacts
- **Git Integration**: Version control awareness
- **Configuration Management**: Environment-specific settings
- **Documentation Generation**: Self-documenting test suites

## **Key Architectural Principles**

1. **Separation of Concerns**: Clear boundaries between ingestion, analysis, generation, and verification
2. **Async Processing**: Non-blocking operations for better UX
3. **Caching Strategy**: Multiple cache layers for different access patterns
4. **Fault Tolerance**: Graceful degradation and recovery mechanisms
5. **Extensibility**: Plugin architecture for different languages and test frameworks

This architecture is much more suitable for production use and can handle enterprise-scale codebases while maintaining the core AI-driven test generation capabilities.
# Code2Test Implementation Tasks

## Project Overview
Transform CodeWiki (documentation generator) into Code2Test (test generator) using intent-first hierarchical test generation with human-in-the-loop verification.

---

## Phase 1: Foundation (Weeks 1-2)

### 1.1 Rename & Rebrand
- [x] Rename package from `codewiki` to `code2test` throughout codebase
- [x] Update `pyproject.toml` with new name, description, and version
- [x] Update CLI entry point from `codewiki` to `code2test`
- [ ] Update README.md with Code2Test branding

### 1.2 Core Data Models
- [x] Create `code2test/core/models.py` with:
  - [x] `Intent` model (component, intent_text, confidence, evidence)
  - [x] `TestCase` model (name, intent, assertions, status)
  - [x] `TestFile` model (path, test_cases, component)
  - [x] `Diagnosis` model (cause, confidence, suggested_fix)
  - [x] `VerificationResult` model (passed, failures, diagnosis)

### 1.3 Intent Storage System
- [x] Create `code2test/storage/intent_db.py`:
  - [x] SQLite integration for intent persistence
  - [x] Intent CRUD operations
  - [x] Low-confidence intent filtering
- [x] Create `code2test/storage/test_registry.py`:
  - [x] Track generated tests per component
  - [x] Verification status tracking

### 1.4 CLI Scaffold Enhancements
- [x] Add new commands to `code2test/cli/commands/`:
  - [x] `generate.py` - Interactive test generation (exists, remains as legacy/alias)
  - [x] `test.py` - Main interactive test generation command
  - [x] `verify.py` - Test verification and diagnosis
  - [x] `intent.py` - View/edit inferred intents
  - [x] `report.py` - Coverage and quality reports
- [x] Update `main.py` with new command groups

---

## Phase 2: Core Engine (Weeks 3-5)

### 2.1 Intent Extraction System
- [x] Create `code2test/core/intent.py`:
  - [x] Intent extraction from docstrings
  - [x] Intent inference from function signatures/type hints
  - [x] Naming convention analysis (e.g., `validate_*`, `is_*`)
  - [x] Call site analysis from dependency graph
  - [x] Dependency intent aggregation
  - [x] Confidence scoring algorithm

### 2.2 Test Generation Agents
- [x] Create `code2test/agents/intent_agent.py`:
  - [x] LLM-powered intent inference
  - [x] Multi-signal confidence scoring
  - [x] User clarification prompting for low-confidence
- [x] Create `code2test/agents/test_agent.py`:
  - [x] Unit test generation from intent
  - [x] Integration test generation from module structure
  - [x] Test fixture suggestion

### 2.3 Verification System
- [x] Create `code2test/core/verifier.py`:
  - [x] Test execution orchestration
  - [x] Result parsing and aggregation
  - [x] Failure categorization
- [x] Create `code2test/agents/diagnosis_agent.py`:
  - [x] Failure root cause analysis
  - [x] Diagnosis classification (TEST_WRONG, CODE_BUG, INTENT_WRONG)
  - [x] Fix suggestion generation

### 2.4 Generator Orchestration
- [x] Create `code2test/core/generator.py`:
  - [x] Hierarchical generation flow orchestration
  - [x] Intent extraction phase coordination
  - [x] Test generation phase coordination
  - [x] Verification loop management

---

## Phase 3: Interactive CLI (Weeks 6-7)

### 3.1 Rich Terminal UI
- [x] Create `code2test/cli/interactive.py`:
  - [x] Intent confidence display with color coding
  - [x] Test preview rendering
  - [x] Verification result formatting
  - [x] Diagnosis panel with recommendations
- [x] Create `code2test/cli/display.py`:
  - [x] Progress indicators for generation
  - [x] Rich tables for test summaries
  - [x] Tree view for hierarchical test structure

### 3.2 User Interaction Flows
- [x] Implement accept/skip/edit/run test flow
- [x] Implement intent editing mode
- [x] Implement diagnosis response flow (fix/flag bug/keep/skip)
- [x] Implement batch confirmation mode

### 3.3 Low Confidence Handling
- [x] Interactive intent clarification prompts
- [x] Intent editing with live confidence recalculation
- [x] User-provided intent override

---

## Phase 4: Multi-Language Support (Weeks 8-10)

### 4.1 Test Framework Adapters
- [x] Create `code2test/adapters/python/pytest_adapter.py`:
  - [x] pytest test file generation
  - [x] Fixture generation
  - [x] Test execution and result parsing
- [x] Create `code2test/adapters/javascript/jest_adapter.py`:
  - [x] Jest test file generation
  - [x] Mock generation
  - [x] Test execution and result parsing
- [x] Create `code2test/adapters/java/junit_adapter.py`:
  - [x] JUnit 5 test file generation
  - [x] Test execution and result parsing

### 4.2 Language-Specific Intent Extraction
- [x] Refactor IntentExtractor for pluggable strategies
- [x] Implement Python analyzer
- [x] Implement JavaScript/TypeScript analyzer
- [x] Implement Java analyzer

### 4.3 Template System
- [x] Create test file templates per language/framework
- [x] Create fixture/mock templates
- [x] Create assertion pattern library

---

## Phase 5: Enterprise Features (Weeks 11-12)

### 5.1 CI/CD Integration
- [ ] Implement `--auto` mode for non-interactive generation
- [ ] Implement confidence threshold filtering
- [ ] Create GitHub Actions workflow example
- [ ] Create GitLab CI example

### 5.2 Reporting System
- [ ] Create `code2test/reporting/`:
  - [ ] HTML report generation
  - [ ] JSON export for integrations
  - [ ] Markdown summary generation
  - [ ] Coverage analysis (behavioral vs line)

### 5.3 Batch Processing
- [ ] Parallel module processing
- [ ] Progress persistence and resumption
- [ ] Incremental test generation (changed files only)

---

## Current Implementation Status

### ✅ Completed
- Core Models & Storage
- Intent Extraction Engine (Polylingual)
- LLM Agents (Intent, Test, Diagnosis)
- Verification System
- CLI (Refactored & Interactive)
- Adapters (Pytest, Jest, JUnit)
- Template System (Templates, Fixtures, Assertions)

### 🆕 Planned
- CI/CD Integration
- Advanced Reporting

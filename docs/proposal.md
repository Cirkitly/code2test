# CODE2TEST

## Intelligent Test Generation for Legacy Codebases

---

**Product Proposal & Technical Specification**  
Version 1.0 | January 2026  
*Building on FSoft AI4Code's CodeWiki Framework*

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Technical Architecture](#3-technical-architecture)
4. [User Experience](#4-user-experience)
5. [Implementation Plan](#5-implementation-plan)
6. [Market & Business Model](#6-market--business-model)
7. [Evaluation Framework](#7-evaluation-framework)
8. [Risks & Mitigations](#8-risks--mitigations)
9. [Conclusion & Next Steps](#9-conclusion--next-steps)

---

## 1. Executive Summary

### The Problem

Enterprise codebases contain millions of lines of untested code. Manual test writing is slow, expensive, and inconsistent. Existing AI tools generate tests that pass but don't capture true intent.

### The Solution

**Code2Test** is an open-source CLI tool that automatically generates comprehensive test suites for codebases lacking tests. Unlike existing solutions that simply generate tests that pass, Code2Test employs **intent-first generation**: it first infers what code *should* do, then generates tests that validate that behavior.

Built on top of FSoft AI4Code's CodeWiki framework, Code2Test adapts the proven hierarchical decomposition and agent-based architecture for test generation instead of documentation. The result is a tool that understands your codebase at the architectural level and generates tests that capture true system behavior.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Reduction in test writing time** | 70% |
| **Languages supported at launch** | 7 |
| **LOC scalability proven** | 1M+ |

### Key Value Propositions

- **Intent-First Testing**: Generates tests based on inferred behavior, not just code coverage
- **Human-in-the-Loop Verification**: Claude Code-style interactive CLI for confident test acceptance
- **Hierarchical Generation**: System tests constrain integration tests constrain unit tests
- **Self-Diagnosing**: When tests fail, determines if the test, code, or inferred intent is wrong
- **Enterprise Scale**: Handles repositories from 10K to 1M+ lines of code

---

## 2. Problem Statement

### 2.1 The Testing Debt Crisis

Modern enterprises face a critical challenge: millions of lines of production code with minimal or no test coverage. Studies indicate that developers spend approximately **58% of their working time on program comprehension activities**, with untested code being significantly harder to understand and maintain.

The cost of this testing debt is substantial:

- Bug fixing in production costs **10-25x more** than catching issues during development
- Untested code creates fear of refactoring, leading to architectural decay
- Onboarding new developers takes **2-3x longer** on untested codebases
- Regulatory compliance (SOX, HIPAA, PCI-DSS) increasingly requires test evidence

### 2.2 Why Existing Solutions Fall Short

| Approach | Method | Limitation | Result |
|----------|--------|------------|--------|
| **Copilot/Cursor** | Single-file context | No architectural awareness | Fragmented, inconsistent tests |
| **Pynguin** | Symbolic execution | No semantic understanding | Tests paths, not behavior |
| **EvoSuite** | Search-based generation | Generates tests that pass | Not tests that *should* pass |
| **Code2Test** | Intent-first hierarchical | Full repo context + verification | **Tests that capture true intent** |

### 2.3 The Core Insight

> **Intent vs. Implementation**
> 
> The fundamental problem with existing test generators is they create tests that verify what code *does*, not what code *should do*. When generating tests for untested code, we must first infer intent, then test against that intent. This is the only way to catch bugs, not just document existing behavior.

---

## 3. Technical Architecture

### 3.1 Foundation: CodeWiki Framework

Code2Test builds directly on FSoft AI4Code's CodeWiki framework, which provides a proven foundation for repository-scale code analysis. CodeWiki achieved **68.79% quality scores** on documentation generation across 7 programming languages, outperforming both open-source and commercial alternatives.

We adapt CodeWiki's three-phase architecture:

| CodeWiki Phase | Code2Test Adaptation | New Capability |
|----------------|---------------------|----------------|
| Repository Analysis | Same: AST parsing, dependency graph construction | **+ Intent extraction layer** |
| Recursive Generation | Docs agents → Test agents | **+ Verification loop** |
| Hierarchical Assembly | Bottom-up synthesis | **+ Integration test generation** |

### 3.2 Three-Phase Pipeline

#### Phase 1: Analysis & Intent Extraction

The first phase constructs a complete understanding of the codebase structure and infers behavioral intent for each component.

**Core capabilities:**
- **Dependency Graph Construction**: Tree-sitter parsers extract ASTs across 7 languages, identifying function calls, class inheritance, attribute access, and module imports
- **Entry Point Identification**: Topological sorting identifies main functions, API endpoints, CLI handlers, and public interfaces
- **Intent Extraction (New)**: Multi-signal analysis infers what each component *should do*, with confidence scoring

**Intent signals include:**
- Docstrings and inline comments
- Function signatures and type hints
- Naming conventions (e.g., `validate_email` suggests validation behavior)
- Call site analysis (how is this function used?)
- Dependency intents (what do called functions do?)

#### Phase 2: Hierarchical Test Generation

Tests are generated in a hierarchical structure where higher-level tests constrain lower-level tests:

1. **System Tests**: Generated from entry points, capture end-to-end user scenarios
2. **Integration Tests**: Generated for module boundaries, verify component interactions
3. **Unit Tests**: Generated for leaf functions, test individual behaviors

Each test agent has access to the complete module tree, enabling cross-module understanding. Dynamic delegation handles modules that exceed context limits by spawning sub-agents.

#### Phase 3: Verification & Refinement

This phase is Code2Test's core innovation. After generating tests, we run them and diagnose any failures:

- **Test Wrong**: The generated test incorrectly interprets the inferred intent
- **Code Bug**: The code doesn't match the stated intent (potential bug discovered)
- **Intent Wrong**: The inferred intent doesn't match actual code behavior

The verification loop iterates until all tests pass and intents are validated, with human approval at each step.

### 3.3 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CODE2TEST PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

PHASE 1: ANALYSIS & INTENT EXTRACTION
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Codebase    │────▶│  Tree-sitter │────▶│  Dependency  │────▶│   Intent     │
│  (no tests)  │     │  AST Parse   │     │  Graph G     │     │   Vector DB  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
PHASE 2: HIERARCHICAL TEST GENERATION                                 │
                     ┌────────────────────────────────────────────────┘
                     │
                     ▼
         ┌─────────────────────────────────────────────────────────────┐
         │                    MODULE TREE                               │
         │  ┌─────────────────────────────────────────────────────┐   │
         │  │              System Tests (Entry Points)              │   │
         │  └─────────────────────────────────────────────────────┘   │
         │                          │                                  │
         │         ┌────────────────┼────────────────┐                │
         │         ▼                ▼                ▼                │
         │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
         │  │ Integration │  │ Integration │  │ Integration │        │
         │  │   Tests     │  │   Tests     │  │   Tests     │        │
         │  └─────────────┘  └─────────────┘  └─────────────┘        │
         │        │                │                │                 │
         │    ┌───┴───┐        ┌───┴───┐        ┌───┴───┐            │
         │    ▼       ▼        ▼       ▼        ▼       ▼            │
         │ ┌─────┐ ┌─────┐  ┌─────┐ ┌─────┐  ┌─────┐ ┌─────┐        │
         │ │Unit │ │Unit │  │Unit │ │Unit │  │Unit │ │Unit │        │
         │ │Test │ │Test │  │Test │ │Test │  │Test │ │Test │        │
         │ └─────┘ └─────┘  └─────┘ └─────┘  └─────┘ └─────┘        │
         └─────────────────────────────────────────────────────────────┘
                                    │
PHASE 3: VERIFICATION LOOP          │
                                    ▼
         ┌─────────────────────────────────────────────────────────────┐
         │                                                             │
         │   ┌──────────┐     ┌──────────┐     ┌──────────────────┐   │
         │   │ Run Test │────▶│  PASS?   │─YES─▶│ Intent Validated │   │
         │   └──────────┘     └──────────┘     └──────────────────┘   │
         │                         │                                   │
         │                         NO                                  │
         │                         ▼                                   │
         │                  ┌─────────────┐                            │
         │                  │  Diagnose   │                            │
         │                  │ ┌─────────┐ │                            │
         │                  │ │Test wrong│ │                            │
         │                  │ │Code bug  │ │                            │
         │                  │ │Intent bad│ │                            │
         │                  │ └─────────┘ │                            │
         │                  └─────────────┘                            │
         │                         │                                   │
         │        ┌────────────────┼────────────────┐                  │
         │        ▼                ▼                ▼                  │
         │ ┌────────────┐  ┌────────────┐  ┌────────────────────┐     │
         │ │  Revise    │  │  Flag Bug  │  │    ASK USER        │     │
         │ │   Test     │  │  in Code   │  │ (low confidence)   │     │
         │ └────────────┘  └────────────┘  └────────────────────┘     │
         │        │                │                │                  │
         │        └────────────────┴────────────────┘                  │
         │                         │                                   │
         │                         ▼                                   │
         │                  ┌─────────────┐                            │
         │                  │   Update    │                            │
         │                  │  Intent DB  │◀─────────────────────┐     │
         │                  └─────────────┘                      │     │
         │                         │                             │     │
         └─────────────────────────┴─────────────────────────────┘     │
                                                                       │
                              ┌────────────────────────────────────────┘
                              ▼
                     ┌──────────────────┐
                     │  GENERATED TEST  │
                     │     SUITE        │
                     └──────────────────┘
```

---

## 4. User Experience

### 4.1 CLI Interface Design

Code2Test uses a **Claude Code-inspired interactive CLI** that prioritizes developer confidence. The interface presents generated tests with full context and asks for explicit approval before writing any files.

### 4.2 Example Session

```
$ code2test generate src/auth/

Analyzing module: auth (4 functions)

▶ validate_token(token: str) -> bool
  Intent (92% confidence):
  "Validates JWT token, returns True if valid and not expired"

  Generated 4 tests:
  ├─ test_valid_token_returns_true
  ├─ test_expired_token_returns_false
  ├─ test_malformed_token_returns_false
  └─ test_empty_token_returns_false

[y] Accept  [n] Skip  [e] Edit  [r] Run first  [i] Edit intent
> r

Running tests...
✓ test_valid_token_returns_true      PASSED
✓ test_expired_token_returns_false   PASSED
✓ test_malformed_token_returns_false PASSED
✓ test_empty_token_returns_false     PASSED

All tests passed. Save to tests/auth/test_token.py? [y/n]
```

### 4.3 Verification UX for Failed Tests

When tests fail, Code2Test presents a diagnosis and asks the developer to decide:

```
✗ test_none_token_raises  FAILED
  Expected: TypeError
  Got: returns False (no exception)

╭─ Diagnosis ──────────────────────────────────────────────────╮
│ The function handles None gracefully (returns False) rather │
│ than raising. This appears to be intentional defensive      │
│ coding based on the try/except block in the implementation. │
│                                                              │
│ Likely cause: TEST_WRONG (confidence: 87%)                  │
╰──────────────────────────────────────────────────────────────╯

[f] Fix test  [b] Flag as bug  [k] Keep (xfail)  [s] Skip
```

### 4.4 Low Confidence Intent Handling

When intent confidence is below threshold (default: 60%), Code2Test asks the developer to clarify before generating tests:

```
⚠ Low confidence intent (41%) for process_transaction()

Inferred: "Processes a financial transaction"

Unclear aspects:
  • Does it validate the transaction first?
  • Does it handle rollback on failure?
  • What happens with insufficient funds?

Please describe the intended behavior:
> It should validate first, if valid return new token with extended expiry. 
> If invalid or expired, raise InvalidTokenError. Old token stays valid.

Updated intent (confidence: 0.95):
"Validates token, if valid returns new token with extended expiry. 
 Raises InvalidTokenError if invalid/expired. Does not revoke old token."

Generating tests...
```

### 4.5 Batch Mode for CI/CD

```bash
# Non-interactive mode for CI pipelines
$ code2test generate --auto --confidence 0.8 --output-dir tests/generated/

Processing 127 functions...
├─ Generated: 98 (77.2%)
├─ Skipped (low confidence): 23 (18.1%)
├─ Failed verification: 6 (4.7%)
└─ Report: tests/generated/code2test-report.html
```

---

## 5. Implementation Plan

### 5.1 Project Timeline

| Phase | Duration | Deliverables | Success Criteria |
|-------|----------|--------------|------------------|
| **1. Foundation** | Weeks 1-2 | Fork CodeWiki, CLI scaffold, basic intent extraction | Parse 3 test repos successfully |
| **2. Core Engine** | Weeks 3-5 | Test generation agents, verification loop, diagnosis system | Generate passing tests for 70% of functions |
| **3. Interactive CLI** | Weeks 6-7 | Rich terminal UI, verification UX, intent editing | Complete user flow end-to-end |
| **4. Multi-language** | Weeks 8-10 | Support for 7 languages, test framework adapters | All CodeWiki languages supported |
| **5. Enterprise** | Weeks 11-12 | CI/CD integration, batch mode, reporting | GitHub Actions workflow ready |

### 5.2 Technical Dependencies

- **CodeWiki Framework**: Fork from github.com/FSoft-AI4Code/CodeWiki
- **Tree-sitter**: AST parsing for Python, JavaScript, TypeScript, Java, C, C++, C#
- **LLM Integration**: Claude API (primary), with architecture supporting local models
- **Vector Database**: ChromaDB for intent storage and similarity search
- **CLI Framework**: Rich + prompt_toolkit for interactive terminal UI
- **Test Runners**: pytest, Jest, JUnit, GoogleTest adapters

### 5.3 Repository Structure

```
code2test/
├── cli/                        # Interactive CLI interface
│   ├── main.py                 # Entry point, argument parsing
│   ├── interactive.py          # Claude Code-style prompts
│   └── display.py              # Rich terminal rendering
├── core/                       # Core analysis engine
│   ├── analyzer.py             # CodeWiki analysis (forked)
│   ├── intent.py               # Intent extraction (NEW)
│   ├── generator.py            # Test generation orchestration
│   └── verifier.py             # Test execution & diagnosis
├── agents/                     # LLM-powered agents
│   ├── intent_agent.py         # Infers intent from code
│   ├── test_agent.py           # Generates tests from intent
│   ├── diagnosis_agent.py      # Analyzes test failures
│   └── delegation.py           # Dynamic sub-agent spawning
├── adapters/                   # Language & framework adapters
│   ├── python/                 # pytest adapter
│   ├── javascript/             # Jest adapter
│   └── java/                   # JUnit adapter
└── storage/                    # Persistence layer
    ├── intent_db.py            # Vector DB for intents
    └── test_registry.py        # Generated test tracking
```

### 5.4 Core Algorithm: Intent-Aware Test Generation

```python
# Pseudocode for the core generation loop

def generate_tests_for_module(module: Module) -> TestSuite:
    # Phase 1: Extract intents
    intents = {}
    for component in topological_sort(module.components):
        dep_intents = {d: intents[d] for d in component.dependencies if d in intents}
        intent = extract_intent(component, dep_intents)
        intents[component.id] = intent
        
        if intent.confidence < CONFIDENCE_THRESHOLD:
            intent = request_user_clarification(component, intent)
            intents[component.id] = intent
    
    # Phase 2: Generate tests hierarchically
    test_suite = TestSuite()
    
    # Unit tests (leaves first)
    for leaf in module.leaf_components:
        tests = generate_unit_tests(leaf, intents[leaf.id])
        test_suite.add(tests)
    
    # Integration tests (parents)
    for parent in module.parent_components:
        child_tests = [test_suite.get(c) for c in parent.children]
        tests = generate_integration_tests(parent, intents[parent.id], child_tests)
        test_suite.add(tests)
    
    # Phase 3: Verify and refine
    for test_file in test_suite:
        result = run_tests(test_file)
        
        if not result.all_passed:
            for failure in result.failures:
                diagnosis = diagnose_failure(failure, test_file.component, intents)
                
                if diagnosis.cause == "TEST_WRONG":
                    action = prompt_user_fix_test(failure, diagnosis)
                elif diagnosis.cause == "CODE_BUG":
                    action = prompt_user_flag_bug(failure, diagnosis)
                elif diagnosis.cause == "INTENT_WRONG":
                    action = prompt_user_revise_intent(failure, diagnosis)
                
                if action == "fix":
                    test_file = apply_fix(test_file, diagnosis.suggested_fix)
                elif action == "revise_intent":
                    intents[test_file.component.id] = get_revised_intent()
                    test_file = regenerate_tests(test_file.component, intents)
    
    return test_suite
```

---

## 6. Market & Business Model

### 6.1 Target Market

Code2Test targets three primary market segments:

**Segment 1: Enterprise Legacy Modernization**
Large enterprises with millions of lines of legacy code seeking to add test coverage before modernization or refactoring efforts. These organizations typically have regulatory compliance requirements (SOX, HIPAA) that mandate test evidence.

**Segment 2: Growing Engineering Teams**
Mid-stage startups and scale-ups that built quickly without tests and now need to add coverage as the team grows. These teams need to onboard new developers safely and reduce bug rates.

**Segment 3: Open Source Maintainers**
Open source project maintainers who want to improve code quality and contributor experience but lack bandwidth for comprehensive test writing.

### 6.2 Competitive Landscape

| Competitor | Strength | Weakness | Code2Test Advantage |
|------------|----------|----------|---------------------|
| **Copilot** | IDE integration, ease of use | Single-file context only | Repository-wide understanding |
| **Codium/Qodo** | Test-focused, good UX | No verification loop | Self-diagnosing failures |
| **Diffblue Cover** | Enterprise proven | Java only, expensive | 7 languages, open source |
| **EvoSuite** | High coverage | Tests what IS, not what SHOULD BE | Intent-first generation |

### 6.3 Business Model Options

**Open Core Model:**
- **Open Source**: CLI tool, core engine, community language support
- **Commercial**: Enterprise features (SSO, audit logs, batch processing, priority support)

**Managed Service:**
- Hosted version with integrated LLM costs
- GitHub App for automatic PR test generation
- Team collaboration features

### 6.4 Pricing Strategy (Commercial Tier)

| Tier | Price | Features |
|------|-------|----------|
| **Community** | Free | CLI tool, 3 languages, local LLM only |
| **Pro** | $29/user/mo | All languages, Claude API integration, CI/CD mode |
| **Enterprise** | Custom | SSO, audit logs, dedicated support, on-prem deployment |

---

## 7. Evaluation Framework

### 7.1 Quality Metrics

Adapting CodeWiki's evaluation methodology, we define three primary metrics for test quality:

**Intent Alignment Score (IAS)**
Measures how well generated tests capture the inferred intent. Evaluated by comparing test assertions against intent statements using semantic similarity.

**Behavioral Coverage (BC)**
Goes beyond line coverage to measure how many distinct behaviors are tested. Calculated by analyzing test scenarios against inferred behavioral intents.

**Diagnostic Accuracy (DA)**
Measures how often the verification system correctly identifies the cause of test failures (test wrong vs. code bug vs. intent wrong).

### 7.2 Benchmark Suite

We will create **Code2TestBench**, adapting CodeWikiBench's methodology:

- 10 open-source repositories with existing high-quality test suites (hidden during generation)
- Comparison of generated tests against human-written tests
- Mutation testing to evaluate test effectiveness
- Human evaluation of test readability and maintainability

### 7.3 Success Criteria for MVP

| Metric | Target | Stretch |
|--------|--------|---------|
| Functions with generated tests (acceptance rate) | 70% | 85% |
| Generated tests that pass on first run | 80% | 90% |
| Diagnostic accuracy on failures | 75% | 85% |
| Intent confidence correlation with test quality | r > 0.6 | r > 0.8 |
| Time to generate tests vs. manual writing | 5x faster | 10x faster |

### 7.4 Benchmark Repositories

| Repository | Language | LOC | Domain | Why Selected |
|------------|----------|-----|--------|--------------|
| flask | Python | 15K | Web framework | Well-tested, clear patterns |
| requests | Python | 12K | HTTP client | Excellent docs, clear intent |
| lodash | JavaScript | 25K | Utilities | Pure functions, testable |
| express | JavaScript | 8K | Web framework | Async patterns |
| spring-petclinic | Java | 10K | Sample app | Enterprise patterns |

---

## 8. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **Intent inference inaccuracy** | Wrong tests that pass but don't catch bugs | Medium | Confidence scoring + human verification for low-confidence intents |
| **LLM cost at scale** | High API costs for large repos | High | Caching, local model support, incremental processing |
| **Systems language complexity** | Poor results on C/C++ (as seen in CodeWiki) | High | Focus MVP on Python/JS/TS, add specialized parsers later |
| **Test maintenance burden** | Generated tests become tech debt | Medium | Generate readable tests with clear intent comments |
| **Flaky test generation** | Tests that pass/fail inconsistently | Medium | Run tests multiple times before acceptance, flag non-deterministic code |
| **Context window limits** | Large files exceed LLM capacity | Medium | Dynamic delegation (inherited from CodeWiki) |
| **Adoption resistance** | Developers distrust AI-generated tests | Medium | High-quality UX, conservative defaults, transparency |

---

## 9. Conclusion & Next Steps

### Summary

Code2Test represents a significant advancement in automated test generation by combining CodeWiki's proven hierarchical analysis with intent-first generation and human-in-the-loop verification. The tool addresses a critical industry need: adding test coverage to legacy codebases that were built without tests.

### Key Differentiators

- **Intent-first approach** ensures tests catch bugs, not just document existing behavior
- **Hierarchical generation** creates coherent test suites from system to unit level
- **Self-diagnosing verification loop** reduces false positives and developer frustration
- **Claude Code-style UX** builds developer confidence in generated tests
- **Open source foundation** enables community contribution and enterprise customization

### Immediate Next Steps

1. Fork CodeWiki repository and set up development environment
2. Implement basic CLI scaffold with Rich terminal UI
3. Build intent extraction module for Python
4. Create test generation agent with pytest output
5. Implement verification loop with diagnosis capabilities
6. Validate on 3 open-source Python repositories

---

## Appendix A: CLI Command Reference

```bash
# Initialize Code2Test on a repository
code2test init [path]
  --language    Force language detection
  --framework   Specify test framework (pytest, jest, junit)

# Generate tests interactively
code2test generate [path]
  --auto        Accept all high-confidence tests automatically
  --confidence  Minimum confidence threshold (default: 0.6)
  --dry-run     Show what would be generated without writing

# Run verification on generated tests
code2test verify [path]
  --diagnose    Analyze and explain any failures
  --fix         Attempt to auto-fix failed tests

# View/edit inferred intents
code2test intent [component]
  --edit        Open intent in editor
  --export      Export all intents to JSON

# Generate coverage report
code2test report
  --format      Output format (html, json, markdown)
  --output      Output file path
```

---

## Appendix B: Intent Extraction Signals

| Signal | Weight | Source | Example |
|--------|--------|--------|---------|
| Docstring | +0.30 | AST parsing | `"""Validates user email"""` |
| Type hints | +0.20 | Signature analysis | `def validate(x: str) -> bool` |
| Function name | +0.15 | Naming heuristics | `validate_email_format()` |
| Call sites | +0.20 | Dependency graph | Called in `register_user()` |
| Dependency intents | +0.15 | Transitive analysis | Calls `hash_password()` |
| Magic numbers | -0.10 | Body analysis | `if x > 42: return True` |
| Complex control flow | -0.15 | Cyclomatic complexity | Nested conditionals > 3 |

**Confidence Calculation:**
```
confidence = 0.5 (base)
           + docstring_signal
           + type_hint_signal
           + naming_signal
           + call_site_signal
           + dependency_signal
           - magic_number_penalty
           - complexity_penalty
```

---

## Appendix C: Supported Languages & Frameworks

| Language | Test Framework | Parser | MVP Priority |
|----------|----------------|--------|--------------|
| Python | pytest, unittest | tree-sitter-python | P0 - Launch |
| JavaScript | Jest, Mocha, Vitest | tree-sitter-javascript | P0 - Launch |
| TypeScript | Jest, Vitest | tree-sitter-typescript | P0 - Launch |
| Java | JUnit 5, TestNG | tree-sitter-java | P1 - Phase 2 |
| C# | xUnit, NUnit, MSTest | tree-sitter-c-sharp | P1 - Phase 2 |
| C | Unity, Check, CTest | tree-sitter-c | P2 - Phase 3 |
| C++ | GoogleTest, Catch2 | tree-sitter-cpp | P2 - Phase 3 |

---

## Appendix D: Sample Generated Test

**Source Code:**
```python
# auth/token.py
def validate_token(token: str) -> bool:
    """
    Validates a JWT token.
    
    Returns True if the token is valid and not expired.
    Returns False for invalid, expired, or malformed tokens.
    """
    if not token:
        return False
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("exp", 0) > datetime.now().timestamp()
    except jwt.InvalidTokenError:
        return False
```

**Extracted Intent:**
```json
{
  "component": "auth.token.validate_token",
  "intent": "Validates a JWT token, returning True if valid and not expired, False otherwise",
  "confidence": 0.92,
  "evidence": {
    "docstring": "Validates a JWT token. Returns True if valid and not expired.",
    "signature": "(token: str) -> bool",
    "calls": ["jwt.decode", "datetime.now"],
    "naming": "validate_* suggests validation returning boolean"
  }
}
```

**Generated Test:**
```python
# tests/auth/test_token.py
"""
Tests for auth.token.validate_token

Intent: Validates a JWT token, returning True if valid and not expired, False otherwise
Generated by Code2Test v1.0
"""
import pytest
from datetime import datetime, timedelta
from auth.token import validate_token
from tests.fixtures import create_test_token


class TestValidateToken:
    """Tests for validate_token based on inferred intent."""
    
    def test_valid_token_returns_true(self):
        """Valid, non-expired token should return True."""
        token = create_test_token(expires_in=timedelta(hours=1))
        assert validate_token(token) is True
    
    def test_expired_token_returns_false(self):
        """Expired token should return False."""
        token = create_test_token(expires_in=timedelta(hours=-1))
        assert validate_token(token) is False
    
    def test_malformed_token_returns_false(self):
        """Malformed token string should return False."""
        assert validate_token("not.a.valid.jwt.token") is False
    
    def test_empty_string_returns_false(self):
        """Empty string should return False."""
        assert validate_token("") is False
    
    def test_none_returns_false(self):
        """None input should return False (defensive handling)."""
        # Note: Function handles None gracefully rather than raising
        assert validate_token(None) is False
```

---

## Appendix E: Comparison with CodeWiki Results

CodeWiki achieved the following results across 7 repositories:

| Repository | Language | LOC | CodeWiki Score | Code2Test Target |
|------------|----------|-----|----------------|------------------|
| OpenHands | Python | 230K | 82.45% | 80%+ test acceptance |
| svelte | JavaScript | 125K | 71.96% | 70%+ test acceptance |
| puppeteer | TypeScript | 136K | 83.00% | 80%+ test acceptance |
| ml-agents | C# | 86K | 79.78% | 75%+ test acceptance |
| logstash | Java | 117K | 57.90% | 60%+ test acceptance |
| wazuh | C | 1.4M | 64.17% | 50%+ test acceptance |
| electron | C++ | 184K | 42.30% | 40%+ test acceptance |

**Key Insight:** Code2Test targets similar acceptance rates to CodeWiki's documentation quality scores, with the understanding that test generation may be slightly harder than documentation due to the need for executable correctness.

---

## Contact & Resources

**GitHub Repository:** github.com/[TBD]/code2test

**Built On:** [FSoft AI4Code CodeWiki](https://github.com/FSoft-AI4Code/CodeWiki)

**Reference Paper:** CodeWiki: Evaluating AI's Ability to Generate Holistic Documentation for Large-Scale Codebases (arXiv:2510.24428)

---

*Code2Test is designed for immediate implementation, building on the proven CodeWiki foundation. The 12-week roadmap delivers a production-ready tool that addresses real enterprise needs.*

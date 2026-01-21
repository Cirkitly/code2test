<h1 align="center">Code2Test: Intent-Driven Test Generation Agent</h1>

<p align="center">
  <strong>Hierarchical Test Generation</strong> • <strong>Multi-Language Support</strong> • <strong>Human-in-the-Loop Verification</strong>
</p>

# Code2Test

Code2Test is an advanced AI agent that automatically generates, verifies, and maintains test suites for large-scale codebases. Unlike simple test generators that look at isolated functions, Code2Test understands the *intent* of your components, their role in the system architecture, and their dependencies.

It employs a hierarchical approach, extracting high-level intents from your codebase, generating corresponding tests, and running them in a verification loop to ensure correctness.

## 🚀 Key Features

*   **Intent-First Generation**: Extracts "intent" from docstrings, naming conventions, and dependencies to generate meaningful tests, not just coverage padding.
*   **Hierarchical Understanding**: Analyzes your dependency graph to understand how components interact, enabling integration test suggestions.
*   **Human-in-the-Loop**: Interactive CLI allows you to review inferred intents, edit generated tests, and guide the agent before committing.
*   **Self-Healing Verification**: If a generated test fails, the agent analyzes the error, determines if it's a test bug or a code bug, and attempts to fix the test automatically.
*   **Multi-Language Support**:
    *   🐍 **Python** (pytest) - *Fully Supported*
    *   ☕ **Java** (JUnit 5) - *Beta*
    *   🟨 **JavaScript/TypeScript** (Jest) - *Beta*
*   **CI/CD Ready**: Includes `--auto` mode for headless execution in CI pipelines, with support for Github Actions and GitLab CI.
*   **Comprehensive Reporting**: Generates HTML and JSON reports detailing test coverage, verification status, and confidence levels.

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/cirkitly/code2test.git
cd code2test

# Install dependencies
pip install .

# Verify installation
code2test --help
```

## 🛠️ Usage

### 1. Interactive Test Generation
The default mode. The agent scans your code, presents inferred intents, and asks for confirmation before generating tests.

```bash
# Generate tests for the current directory
code2test test .

# Generate tests for a specific module
code2test test src/core/auth.py
```

### 2. CI/CD / Automated Mode
Run without user interaction. Useful for CI pipelines or nightly builds.

```bash
# Run in auto mode with a confidence threshold
code2test test --auto --confidence 0.8 --exit-code src/
```

*   `--auto`: Skip interactive prompts.
*   `--confidence 0.8`: Only generate tests for intents with >80% confidence.
*   `--exit-code`: Fail the build (exit 1) if any verification step fails.

### 3. Reporting
Generate detailed reports after a test run.

```bash
code2test test --auto --report html .
```
This creates `reports/report.html` with a visual summary of the run.

## 🏗️ Architecture

Code2Test operates in five phases:

1.  **Foundation**: Parses the codebase to build a Dependency Graph.
2.  **Intent Extraction**: Uses static analysis + LLMs to infer *what* a component should do.
3.  **Test Generation**: Uses language-specific agents to write idiomatic test code (Pytest, Jest, JUnit).
4.  **Verification**: Executes the generated tests immediately.
5.  **Diagnosis & Repair**: If tests fail, a diagnosis agent analyzes the traceback to fix the test or flag the code.

## 🤝 Contributing

Contributions are welcome! Please check out the [implementation plan](docs/implementation_plan.md) to see what's next.

## 📄 License

MIT License

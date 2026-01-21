# Code2Test Quickstart Guide

This guide will help you get started with **Code2Test** to automatically generate comprehensive test suites for your legacy codebase.

## Prerequisites

- Python 3.9 or higher
- An OpenAI-compatible API Key (e.g., OpenAI, Anthropic, OpenRouter) set as `OPENAI_API_KEY` environment variable.

## 1. Installation

Clone the repository and install the package:

```bash
git clone https://github.com/cirkitly/code2test.git
cd code2test
pip install .
```

Verify the installation:

```bash
code2test --version
```

## 2. Initialization

Navigate to your project root (the code you want to test) and initialize Code2Test:

```bash
cd /path/to/your/project
code2test init
```

This command will:
1.  Detect your primary language (Python, JavaScript/TypeScript, or Java).
2.  Create a `.code2test/config.json` file with default settings.

## 3. Generating Tests (Interactive Mode)

The most common way to use Code2Test is the interactive mode. It guides you through the process of verifying inferred intents before writing any code.

```bash
# Generate tests for the entire current directory
code2test test .

# Or for a specific file/module
code2test test src/utils/string_utils.py
```

**What happens next?**
1.  **Analysis**: Code2Test scans your code and dependencies.
2.  **Intent Proposal**: It shows you what it thinks each function *should* do.
3.  **Review**: You can `[y]es` to accept, `[e]dit` the intent, or `[s]kip`.
4.  **Generation**: Once accepted, it generates the test file.
5.  **Verification**: It immediately runs the test.
6.  **Refinement**: If the test fails, it tries to fix it automatically (or asks you).

## 4. Automated Mode (CI/CD)

For Continuous Integration pipelines, use the `--auto` flag. This runs without user prompts, skipping items with low confidence.

```bash
code2test test --auto --confidence 0.8 --exit-code src/
```

-   `--auto`: Non-interactive mode.
-   `--confidence 0.8`: Skip functions where intent confidence is < 80%.
-   `--exit-code`: Return a non-zero exit code if verification fails (breaks the build).

## 5. Generating Reports

You can generate HTML or JSON reports to visualize test coverage and verification status.

```bash
code2test test --auto --report html src/
```

Open `reports/report.html` in your browser to see the results.

## 6. Viewing & Editing Intents

Code2Test remembers what it learned about your code. You can view or refine these "intents" later.

```bash
# Show stored intents
code2test intent show

# Edit a specific intent (useful if code changes behavior)
code2test intent edit src.utils.string_utils.to_camel_case
```

## Next Steps

- Check out [Architecture Guide](architecture.md) for a deep dive into how it works.
- Customize `.code2test/config.json` to change prompt templates or model parameters.

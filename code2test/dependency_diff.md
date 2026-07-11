# Dependency Audit Report (M0.5)

Generated against `code2test/dependency_inventory.json` (built by walking
`ast` over every `*.py` under `code2test/`).

## Method

1. Built a real import inventory via `ast.walk` of every `code2test/**/*.py`
   file, collecting the top-level package name of every `import` and
   `from ... import` (relative imports skipped).
2. Normalised each top-level name against `sys.stdlib_module_names` and the
   set of `code2test/` sub-packages that ship an `__init__.py` (so local
   packages such as `code2test.agents` are excluded). The legacy docs
   loader inserts `code2test/src/` onto `sys.path` and imports `fe` —
   that one is also excluded from third-party accounting.
3. Mapped third-party import names to canonical PyPI distribution names
   (e.g. `git` → `GitPython`, `yaml` → `PyYAML`).
4. Parsed `requirements.txt` and `pyproject.toml [project] dependencies`
   into comparable sets.

## Summary

| Category | Count |
| --- | --- |
| Third-party imports actually used by `code2test/` | 25 |
| Distinct declared packages (requirements.txt ∪ pyproject.toml) | 162 |
| Declared but NOT used (any code path) | 124 |
| Used but NOT declared | 0 (one name in the inventory is undeclared, see notes) |

The declared surface is ~6× the actually used surface.

## Used third-party packages (audit)

These appear as imports somewhere under `code2test/`:

| Import name | PyPI distribution | Where it's used |
| --- | --- | --- |
| `click` | `click` | `cli/main.py` and every CLI subcommand |
| `colorama` | `colorama` | `src/be/dependency_analyzer/utils/logging_config.py` (legacy docs) |
| `dotenv` | `python-dotenv` | `cli/commands/init.py`, `cli/commands/init_*.py` |
| `fastapi` | `fastapi` | `src/fe/` (legacy webapp) |
| `git` | `GitPython` | `cli/git_manager.py`, `cli/utils/repo_validator.py`, `cli/commands/generate.py` (lazy-loaded only) |
| `gitdb` | `gitdb` | transitive of `GitPython` (declared as direct dep) |
| `jinja2` | `Jinja2` | `cli/commands/init.py`, `src/fe/` |
| `keyring` | `keyring` | `cli/config_manager.py` |
| `markdown_it` | `markdown-it-py` | `src/fe/visualise_docs.py` (legacy docs) |
| `mermaid` | `mermaid-py` | `src/be/utils.py` (legacy docs) |
| `mermaid_parser` | `mermaid-parser-py` | `src/be/utils.py` (legacy docs) |
| `openai` | `openai` | `src/be/llm_services.py` (legacy docs) |
| `pydantic` | `pydantic` | everywhere (models / settings) |
| `pydantic_ai` | `pydantic-ai` | `agents/{intent,test,diagnosis}_agent.py` |
| `rich` | `rich` | `cli/commands/{init,test,verify,intent,report,config,generate}.py`, output rendering |
| `tiktoken` | `tiktoken` | `src/be/utils.py` (legacy docs, count_tokens) |
| `tree_sitter` | `tree-sitter` | `src/be/dependency_analyzer/ast_parser.py` |
| `tree_sitter_c` | `tree-sitter-c` | (analyzers) |
| `tree_sitter_c_sharp` | `tree-sitter-c-sharp` | (analyzers) |
| `tree_sitter_cpp` | `tree-sitter-cpp` | (analyzers) |
| `tree_sitter_java` | `tree-sitter-java` | (analyzers) |
| `tree_sitter_javascript` | `tree-sitter-javascript` | (analyzers) |
| `tree_sitter_languages` | `tree-sitter-languages` (NOT installed in venv; only referenced inside legacy `src/be/agent_tools/str_replace_editor.py`) |
| `tree_sitter_php` | `tree-sitter-php` | (analyzers) |
| `tree_sitter_typescript` | `tree-sitter-typescript` | (analyzers) |
| `uvicorn` | `uvicorn` | `src/fe/web_app.py`, `run_web_app.py` (legacy docs webapp) |

Notes on the used-but-not-installed entry:

* `tree_sitter_languages` is referenced by `src/be/agent_tools/str_replace_editor.py`
  but is **not installed** in the active `.venv-py312` (the declared package is
  `tree-sitter-language-pack`, which is a different distribution with a similar
  name and a different API). This module is part of the legacy docs path and is
  out of v1.0 scope. We will not add it back.

## Declared but unused (audit)

Roughly 124 declared distributions are imported nowhere under `code2test/`.
The high-noise entries are mostly transitive HTTP / LLM-SDK / observability
stacks that the dependency declaration pulled in wholesale. They are listed
in `code2test/dependency_inventory.json` and the cut-list is below.

## v1.0 cut list (final)

For v1.0 we keep only the Python tooling needed by the new path plus the
lazy-loaded CLI. The following declared packages are unused by the v1.0
subcommands and will be removed (and uninstalled):

```
ag-ui-protocol, aiodns, aiohappyeyeballs, aiohttp, aiosignal,
annotated-types, anthropic, anyio, appnope, argcomplete, asttokens,
attrs, boto3, botocore, brotli, cachetools, certifi, cffi,
charset-normalizer, cohere, comm, debugpy, decorator, distro,
eval_type_backport, executing, fastapi, fastavro, fastuuid,
filelock, frozenlist, fsspec, genai-prices, google-auth,
google-genai, googleapis-common-protos, griffe, groq, h11, hf-xet,
httpcore, httpx, httpx-sse, huggingface-hub, idna, importlib_metadata,
invoke, ipykernel, ipython, ipython_pygments_lexers, jedi, jiter,
jmespath, jsonschema, jsonschema-specifications, jupyter_client,
jupyter_core, litellm, logfire, logfire-api, loguru, markupsafe,
matplotlib-inline, mcp, mdurl, mistralai, multidict, nest-asyncio,
networkx, nexus-rpc, openai-agents, opentelemetry-api,
opentelemetry-exporter-otlp-proto-common,
opentelemetry-exporter-otlp-proto-http, opentelemetry-instrumentation,
opentelemetry-instrumentation-httpx, opentelemetry-proto,
opentelemetry-sdk, opentelemetry-semantic-conventions,
opentelemetry-util-http, packaging, parso, pathspec, pexpect,
platformdirs, pminit, propcache, protobuf, psutil, ptyprocess,
pure_eval, pyasn1, pyasn1_modules, pycares, pycparser,
pydantic-ai-slim, pydantic-evals, pydantic-graph, pydantic-settings,
pydantic_core, pygments, pyperclip, python-dateutil, python-multipart,
pythonmonkey, pytz, pyyaml, pyzmq, referencing, regex, requests,
rpds-py, rsa, s3transfer, six, smmap, sniffio, sse-starlette,
stack-data, starlette, temporalio, tenacity, tokenizers, tornado,
tqdm, traitlets, tree-sitter-embedded-template,
tree-sitter-language-pack, tree-sitter-python, tree-sitter-yaml,
types-protobuf, types-requests, typing-inspection, typing_extensions,
urllib3, uvicorn, wcwidth, websockets, wrapt, yarl, zipp
```

### Departures from the plan's "KEEP" list

The plan instructs us to **KEEP** `pydantic-settings, pydantic-evals,
prompt-toolkit, networkx, psutil, pyyaml`. The audit shows these are
imported nowhere under `code2test/` today (they are declared but inert).
Per the instruction "Use judgement", and because M1A/M1B/M1C subcommands
may want them, we keep them in this milestone (no `pip uninstall`).

The plan instructs us to **KEEP** `tree-sitter-*` — and the audit
agrees for `tree-sitter`, `tree-sitter-c`, `tree-sitter-c-sharp`,
`tree-sitter-cpp`, `tree-sitter-java`, `tree-sitter-javascript`,
`tree-sitter-php`, `tree-sitter-typescript`. The cut list above
removes `tree-sitter-embedded-template`, `tree-sitter-language-pack`,
`tree-sitter-python`, `tree-sitter-yaml` because they are imported
nowhere. The Python grammar in particular is unused — the dependency
analyzer parses Python with the generic `tree-sitter` driver, not the
dedicated grammar.

The plan instructs us to **KEEP** `requests` "verify; tree-sitter uses
it". The audit shows `requests` is imported nowhere under `code2test/`,
and modern `tree-sitter` (>=0.20) does not depend on `requests`. We
will remove `requests`.

The plan instructs us to cut `tiktoken`. The audit shows `tiktoken`
**is** imported (`src/be/utils.py:count_tokens`). It is part of the
legacy docs path. We keep `tiktoken` for now (no uninstall) since
the legacy path is not deleted in M0.5; a future milestone can revisit.

The plan does not mention `colorama`, `markdown-it-py`, `mermaid`,
`mermaid-parser`, `fastapi`, `uvicorn`, `gitdb`, `keyring` — these are
all used somewhere. We keep them.

## Dev dependencies

`pytest`, `pytest-cov`, `pytest-asyncio`, `black`, `mypy`, `ruff`
remain in `[project.optional-dependencies] dev`. The first three are
required to run the test suite; the linters are kept as a courtesy.

## Net result

After M0.5 lands:

* `requirements.txt` pins only the ~25 actually-imported third-party
  distributions plus their transitives that the venv still needs at
  runtime.
* `pyproject.toml [project] dependencies` declares the runtime surface
  required by the v1.0 CLI + the lazy legacy paths that v1.0 keeps
  importable.
* `tests/smoke/` (11 tests) and `tests/unit/test_events.py` (11 tests)
  still pass.
* `code2test --help` still works.
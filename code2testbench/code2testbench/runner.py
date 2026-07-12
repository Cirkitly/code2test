"""benchmark runner CLI.

`python -m code2testbench.runner --provider stub`
`python -m code2testbench.runner --provider openai --model gpt-4o-mini`

Reads code2testbench/corpus/manifest.json, runs the code2test pipeline
against each (repo, component) pair, captures the event stream, and emits:

  * code2testbench/latest_report.json  (array of AcceptanceReport)

The harness is intentionally thin: it does NOT own the test-generation
machinery. The pipeline (TestGenerator, agents, verifier) lives in
code2test/; the corpus and the acceptance interpretation live here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Optional


PACKAGE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACKAGE_DIR))


def _build_config(provider_name: str, model: str, threshold: float):
    """Construct a code2test.config.Config from CLI args."""
    from code2test.config import Config
    base_url = os.environ.get("OPENAI_BASE_URL", os.environ.get("OPENAI_API_BASE", ""))
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CODE2TEST_API_KEY") or ""
    if provider_name == "openai" and not api_key:
        raise SystemExit(
            "ERROR: --provider openai was selected but OPENAI_API_KEY is not set. "
            "Export it before invoking the harness, e.g.\n"
            "    export OPENAI_API_KEY=sk-...\n"
            "    python -m code2testbench.runner --provider openai --model MiniMax-M3"
        )
    return Config(
        provider=provider_name,
        model=model,
        base_url=base_url,
        api_key=api_key,
        confidence_threshold=threshold,
        auto_accept=True,
    )


def _run_one_repo(repo_path: Path, components_dir: Path, config, sink):
    """Run the generator against `components_dir`; events flow to sink.

    v1.0 simplification: we run a single TestGenerator.generate_tests_for_module
    call on a synthetic component dictionary. Real AST-based discovery is
    M1D.5's concern; here we limit scope to wiring.

    NOTE: this is a thin harness. Real component discovery remains a v1.1
    task once the corpus vendoring lands.
    """
    from code2test.core.generator import TestGenerator
    from code2test.core.models import GenerationConfig, TestFramework

    repo = Path(repo_path)
    name = repo.name

    # Build components dict from *.py functions in components_dir.
    components: dict = {}
    if components_dir.is_dir():
        for fp in sorted(components_dir.glob("*.py")):
            key = fp.stem
            components[key] = {
                "id": key,
                "name": key,
                "file_path": str(fp),
                "docstring": f"Function {key}",
                "signature": f"def {key}() -> None",
                "type_hints": "",
                "language": "python",
                "source_code": fp.read_text(),
                "called_by": [],
                "dependencies": [],
                "cyclomatic_complexity": 1,
            }

    if not components:
        return None

    gen_config = GenerationConfig(
        confidence_threshold=config.confidence_threshold,
        auto_accept=config.auto_accept,
        dry_run=False,  # we want verification
        framework=TestFramework.PYTEST,
        # v1.1: forward provider credentials to the generator so its
        # lazily-built agent trio wires the right provider, not the
        # silent-default StubProvider.
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        api_key=config.api_key,
    )
    gen = TestGenerator(
        repo_path=str(repo_path),
        config=gen_config,
        sink=sink,
    )
    suite = asyncio.run(gen.generate_tests_for_module(name, components))
    return suite


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="code2testbench")
    parser.add_argument("--provider", default="stub", choices=["stub", "openai"])
    parser.add_argument("--model", default="")
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--out", default="latest_report.json",
                        help="Where to write the JSON report.")
    parser.add_argument("--manifest", default="",
                        help="Path to corpus manifest; default uses corpus/manifest.json")
    args = parser.parse_args(argv)

    here = Path(__file__).resolve().parent.parent
    manifest_path = Path(args.manifest) if args.manifest else here / "corpus" / "manifest.json"

    if not manifest_path.exists():
        print(f"manifest not found at {manifest_path}", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text())

    # Build a Config and a single EventCollector shared across all repos.
    from code2testbench.collector import EventCollector
    from code2testbench.report import AcceptanceReport

    config = _build_config(args.provider, args.model or "stub-model",
                           args.confidence)
    sink = EventCollector()

    for repo in manifest.get("repos", []):
        repo_path = here / repo["path"]
        comp_dir = repo_path / (repo.get("components_dir") or "code")
        if not comp_dir.is_dir():
            comp_dir = repo_path
        try:
            _run_one_repo(repo_path, comp_dir, config, sink)
        except Exception as exc:  # noqa: BLE001
            print(f"[harness] repo {repo.get('name')} failed: {exc}",
                  file=sys.stderr)

    report = sink.report()
    out = here / args.out
    out.write_text(json.dumps({
        "schema_version": 1,
        "provider": args.provider,
        "model": args.model,
        "confidence": args.confidence,
        **report.to_dict(),
        "_num_components": sum(1 for _ in sink.events
                              if _.__class__.__name__ == "IntentExtracted"),
    }, indent=2))

    print(f"wrote {out}")
    print(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

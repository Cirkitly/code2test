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


def _run_one_repo(repo_path: Path, components_dir: Path, config, sink, enable_rewrite: bool = False):
    """Run the generator against `components_dir`; events flow to sink.

    v1.0 simplification: we run a single TestGenerator.generate_tests_for_module
    call on a synthetic component dictionary. Real AST-based discovery is
    M1D.5's concern; here we limit scope to wiring.

    NOTE: this is a thin harness. Real component discovery remains a v1.1
    task once the corpus vendoring lands.

    v1.1: ``enable_rewrite`` gates the phase-4 rewrite loop. Off by
    default; v1.0 behavior is preserved unchanged.
    """
    from code2test.core.generator import TestGenerator
    from code2test.core.models import GenerationConfig, TestFramework

    repo = Path(repo_path)
    name = repo.name

    # Build components dict from *.py functions in components_dir.
    # We skip test_*.py files because the verifier writes them
    # into components_dir; without this filter a subsequent harness
    # run would see the previously-generated tests as a fresh
    # "component" to test. Architecture invariant: harness input
    # is source code, harness output is test files, never
    # re-ingest.
    components: dict = {}
    if components_dir.is_dir():
        for fp in sorted(components_dir.glob("*.py")):
            if fp.name.startswith("test_"):
                continue
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
        # v1.1: forward the rewrite flag so phase 4 runs when
        # the operator asked for it. Default False preserves v1.0.
        enable_rewrite=enable_rewrite,
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
    parser.add_argument("--enable-rewrite", action="store_true",
                        help="Phase 4: enable the rewrite loop. Off by default; "
                             "the v1.0 behavior is preserved unchanged.")
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
            _run_one_repo(repo_path, comp_dir, config, sink, args.enable_rewrite)
        except Exception as exc:  # noqa: BLE001
            print(f"[harness] repo {repo.get('name')} failed: {exc}",
                  file=sys.stderr)

    report = sink.report()
    out = here / args.out
    # Schema_version bumped to 2 in v1.1.4: events list is now
    # included so the variance script can partition the failure
    # space without re-running the harness.
    out.write_text(json.dumps({
        "schema_version": 2,
        "provider": args.provider,
        "model": args.model,
        "confidence": args.confidence,
        **report.to_dict(),
        "_num_components": sum(1 for _ in sink.events
                              if _.__class__.__name__ == "IntentExtracted"),
        "_events": _serialize_events(sink),
    }, indent=2, default=str))

    print(f"wrote {out}")
    print(json.dumps(report.to_dict(), indent=2))
    return 0


def _serialize_events(sink) -> list:
    """Convert the collector's raw events to JSON-serializable dicts.

    Used by the recorded JSON so the variance script can partition
    the failure space without re-running the harness. Each event
    becomes a dict with __dict__-style fields plus the class
    name as a discriminator (so the script knows what type it is).
    """
    out = []
    for ev in sink.events:
        d = {"_type": type(ev).__name__}
        # dataclass instances expose fields via __dataclass_fields__.
        if hasattr(ev, "__dataclass_fields__"):
            for k in ev.__dataclass_fields__:
                d[k] = getattr(ev, k)
        else:
            d["_repr"] = repr(ev)
        out.append(d)
    return out


if __name__ == "__main__":
    sys.exit(main())

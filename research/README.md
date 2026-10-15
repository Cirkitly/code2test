# Research

This directory holds the paper on Code2Test, the scripts that produced its results, and the raw
data behind every measured number.

**Paper:** *Code2Test: Intent-First, Execution-Verified Test Generation for Legacy Python Code*
([PDF](paper/main.pdf)).

The paper is written as a tool and experience report. It evaluates Code2Test on two open-source
libraries (inflection 0.5.1 and TinyDB 4.8.2) with two MiniMax models, and it states which parts of
the design have precedents in prior work.

## Contents

| Path | Contents |
| --- | --- |
| `paper/main.tex` | Paper source |
| `paper/results.tex` | Measured results as LaTeX macros (generated; do not edit) |
| `paper/abstract.txt` | Plain-text abstract for the arXiv form (generated) |
| `paper/references.bib` | Bibliography |
| `paper/figures/pipeline.tex` | Figure 1 (TikZ) |
| `paper/Makefile` | Builds the PDF and the arXiv bundle |
| `scripts/run_experiments.sh` | Re-runs all experiments: four configurations, two runs each |
| `scripts/collect_results.py` | Turns run directories into `data/` and `paper/results.tex` |
| `data/results.csv` | One row per run with every reported measure (column `run`: 1 or 2) |
| `data/runs/<subject>-<model>/` | First runs (main results). Per run: generated test suite, inferred intents, run metrics, benchmark output, verification log |
| `data/second-runs/<subject>-<model>/` | A second run of each configuration, in the same form |
| `data/development/` | Earlier runs cited only as evidence of run-to-run variance |

## Building the paper

Requires a TeX distribution with `latexmk`, `pdflatex` and BibTeX (TeX Live works).

```bash
make -C research/paper          # paper/main.pdf
make -C research/paper arxiv    # paper/arxiv.tar.gz for submission
```

## Reproducing the results

Requires Code2Test installed in the active Python environment and a MiniMax API key.

```bash
pip install -e .
export OPENAI_API_KEY=...       # MiniMax key
bash research/scripts/run_experiments.sh /path/to/workdir
make -C research/paper
```

The script downloads both libraries from PyPI, removes their own tests, and runs
`code2test test --auto`, `code2test verify` and `code2test benchmark` for each library and model,
twice: once for the main results and once more to show run-to-run variation. It then runs
`collect_results.py`, which rewrites `data/` and `paper/results.tex`. Model output is
not deterministic, so a new run gives different numbers; the paper's text describes the specific
runs in `data/runs/` and `data/second-runs/`.

A full reproduction makes several hundred model calls. Each set of four runs executes in
parallel; in our first runs, the slowest (TinyDB with M3) spent 815 seconds generating tests
before its benchmark started.

## Submitting to arXiv

1. Check the author block in `paper/main.tex`. It names Utkarsh Maurya and links the repository;
   add an affiliation and a contact address if wanted, and rebuild.
2. Run `make -C research/paper arxiv`. The bundle contains `main.tex`, `results.tex`,
   `figures/pipeline.tex` and the generated `main.bbl`, because arXiv does not run BibTeX.
3. At <https://arxiv.org/submit>, upload `paper/arxiv.tar.gz`. Suggested primary category:
   `cs.SE` (Software Engineering); optional cross-list: `cs.LG`.
4. Paste the title and the contents of `paper/abstract.txt` into the metadata form. The abstract is
   within arXiv's 1,920-character limit.
5. Choose a license. CC BY 4.0 is a common choice for papers whose code is MIT-licensed.
6. Check arXiv's generated PDF before announcing.

#!/usr/bin/env bash
# Reproduce the experiments in the paper.
#
# Requires: code2test installed (pip install -e .), and a MiniMax API key:
#   export OPENAI_API_KEY=...            # MiniMax key
#   bash research/scripts/run_experiments.sh [WORK_DIR]
#
# For each subject (inflection 0.5.1, TinyDB 4.8.2) and model (MiniMax-M3.1-Flash-Preview,
# MiniMax-M3), it downloads the sdist from PyPI, removes the library's own tests, and runs
# `code2test test --auto`, `code2test verify` and `code2test benchmark`. It then collects
# the results into research/data/ and research/paper/results.tex.
set -euo pipefail

WORK="${1:-$(mktemp -d)}"
RESEARCH="$(cd "$(dirname "$0")/.." && pwd)"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-https://api.minimax.io/v1}"
export PYDANTIC_AI_NO_BANNER=1
: "${OPENAI_API_KEY:?set OPENAI_API_KEY to a MiniMax API key}"

declare -A MODELS=(
  [flash]="openai-chat:MiniMax-M3.1-Flash-Preview"
  [m3]="openai-chat:MiniMax-M3"
)

mkdir -p "$WORK/subjects"
cd "$WORK/subjects"
pip download -q --no-deps --no-binary :all: inflection==0.5.1 tinydb==4.8.2 -d .
tar xzf inflection-0.5.1.tar.gz && rm -f inflection-0.5.1/test_inflection.py
tar xzf tinydb-4.8.2.tar.gz && rm -rf tinydb-4.8.2/tests

run() {
  local subject=$1 source=$2 model=$3
  local dir="$WORK/runs/$subject-$model"
  rm -rf "$dir" && mkdir -p "$dir/home"
  cp -r "$WORK/subjects/$source" "$dir/project"
  cd "$dir/project"
  export HOME="$dir/home" CODE2TEST_MODEL="${MODELS[$model]}"
  local start; start=$(date +%s)
  code2test test --auto . > "$dir/test.log" 2>&1
  echo $(( $(date +%s) - start )) > "$dir/seconds.txt"
  code2test verify tests/ > "$dir/verify.log" 2>&1 || true
  code2test benchmark --mutants 80 --diagnoses 15 . > "$dir/benchmark.log" 2>&1
  echo "done: $subject-$model ($(cat "$dir/seconds.txt") s)"
}

for model in flash m3; do
  run inflection inflection-0.5.1 "$model" &
  run tinydb tinydb-4.8.2 "$model" &
done
wait

python "$RESEARCH/scripts/collect_results.py" "$WORK/runs"
echo "Results in $RESEARCH/data; rebuild the paper with: make -C $RESEARCH/paper"

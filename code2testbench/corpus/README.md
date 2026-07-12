# code2testbench SLO

This document is the source of truth for the four acceptance numbers that
the bench reports. Adjusting these is a v1.x commitment; once v1.0 ships,
moving the floor is a breaking change.

| Number                       | v1.0 minimum | v1.0 stretch | v1.1 target |
|------------------------------|--------------|--------------|-------------|
| Initial acceptance rate      | ≥40%         | ≥60%         | ≥70%        |
| Diagnosis trigger rate       | ≥20%         | ≥40%         | n/a         |
| Rewrite attempt rate         | ≥15%         | ≥35%         | n/a         |
| Final acceptance rate        | ≥55%         | ≥75%         | ≥80%        |
| Net improvement              | ≥+10pp       | ≥+20pp       | ≥+30pp      |

## Why v1.0 numbers are lower than proposal targets

The proposal's MVP targets (70%, 80%, 75%) are aspirational and were the
target Code2Test was meant to **eventually meet**. v1.0 ships a frozen,
measurable baseline, not yet at that target — but with a corpus and a
harness that allow us to move toward it incrementally.

Reporting a 25% acceptance rate as "70%" because the proposal said so
would be dishonest. Reporting 25% as 25% gives us a starting point we
can improve from. That is the deal v1.0 makes with the user.

## What moves the numbers

* Initial acceptance rate is gated by IntentExtracted.accepted — better
  intent extraction (or a better confidence threshold calibration)
  moves this directly.
* Diagnosis trigger rate is gated by how often VerificationCompleted
  surfaces a failure that the diagnosis agent sees. Fix loops in the
  classifier push this up.
* Rewrite attempt rate needs the loop closed end to end. Often a
  diagnosed failure doesn't lead to a rewrite because the rewrite path
  isn't implemented; this is the first thing to fix in v1.1.
* Final acceptance rate is the user-facing "did it work" number.

## Reading the report

`code2testbench/latest_report.json` contains a single record with the
four numbers, plus a `_num_components` field for sanity (how many
components the pipeline actually saw). NaN values mean "no data" — the
run didn't engage; that's a real signal worth investigating.

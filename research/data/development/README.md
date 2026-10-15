# Development runs

Results from runs made while Code2Test was still being fixed, with earlier versions of the tool
and MiniMax `MiniMax-M3.1-Flash-Preview`. They are not part of the main results. The paper cites
them only as evidence of run-to-run variance (Threats to validity).

| Run | Mutants killed | Scoring |
| --- | --- | --- |
| `inflection-flash` | 80 of 80 | each mutant against the mutated component's own tests |
| `tinydb-flash-1` | 63 of 80 | same |
| `tinydb-flash-2` | 51 of 80 | same |

`inflection-flash/test_irregular.py` is that run's test file for `_irregular`: 33 tests, several of
which check irregular words through `pluralize` and `singularize`. The final Flash run wrote one
test for `_irregular`, which checks only how many rules it inserts.

The mutant samples differ from the final runs, because the mutation operators changed in between
(type annotations were excluded).

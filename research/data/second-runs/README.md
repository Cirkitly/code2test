# Second runs

A second, independent run of each configuration, made after the first runs in `../runs/`.
The paper compares the two in Section 5.5 and Table 3.

- **Same pipeline.** These runs used a later version of Code2Test that removed code inherited
  from CodeWiki which the pipeline does not use. Under that version, the first runs' test suites
  reproduced their verification results, mutants killed and surviving mutants exactly.
- **Times are not comparable.** The runs shared a 4-CPU machine with other jobs (the regression
  check of the first runs' suites, and the tool's own test suite), so `seconds` in `../results.csv` overstates their
  generation time. Run alone, inflection with Flash took 252 s for 307 tests.
- **A real defect.** `inflection-m3/tests/inflection/test_singularize.py` contains the one test
  any run kept as an expected failure: `singularize("campuses")` returns `"campuse"` in
  inflection 0.5.1.

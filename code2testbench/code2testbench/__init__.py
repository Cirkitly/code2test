"""code2testbench — benchmark harness for code2test.

This package is intentionally separate from code2test/ because:

  1. tests answer "does it work?"
     benchmarks answer "how good is it?"
  2. evaluation infrastructure is distinct from product code
  3. code2test can be released without dragging benchmark corpus

Public surface:
  * report.AcceptanceReport   — the four-number SLO result
  * collector.EventCollector  — subscribes to code2test.events
  * collector.collect_into_run — context-manager wrapper
  * runner.main               — CLI: `python -m code2testbench.runner`
"""

from code2testbench.report import AcceptanceReport
from code2testbench.collector import EventCollector

__version__ = "1.0.0"
__all__ = ["AcceptanceReport", "EventCollector", "__version__"]

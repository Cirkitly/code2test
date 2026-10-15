"""
HTML Reporting Module.
"""

import datetime
from typing import Any, Dict, Optional

from jinja2 import DictLoader, Environment

from code2test.core.models import Intent, TestSuite

STYLE = """
    <style>
        body { font-family: sans-serif; margin: 2rem; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { padding: 1rem; background: #f8f9fa; border-radius: 4px; border: 1px solid #dee2e6; }
        .card h3 { margin: 0 0 0.5rem 0; color: #666; font-size: 0.9rem; text-transform: uppercase; }
        .card .value { font-size: 1.5rem; font-weight: bold; color: #333; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { text-align: left; padding: 0.75rem; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; color: #666; font-weight: 600; }
        .status-passed { color: green; font-weight: bold; }
        .status-failed { color: red; font-weight: bold; }
        .status-verified { color: #0d6efd; font-weight: bold; }
        .badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
        .badge-success { background: #d1e7dd; color: #0f5132; }
        .badge-danger { background: #f8d7da; color: #842029; }
        .badge-warning { background: #fff3cd; color: #664d03; }
        .note { color: #666; font-size: 0.9rem; }
        details summary { cursor: pointer; }
    </style>
"""

# Behavioral coverage and diagnostic accuracy (code2test.core.quality.quality_report)
QUALITY_SECTION = """
        <h2>Test Quality</h2>
        {% set b = quality.benchmark %}
        <div class="summary">
            <div class="card">
                <h3>Behaviors Tested</h3>
                <div class="value">{{ quality.summary.behaviors_tested }}</div>
            </div>
            <div class="card">
                <h3>Mutation Score</h3>
                <div class="value">{% if b.mutation_score is not none %}{{ "%.0f"|format(b.mutation_score * 100) }}%{% else %}n/a{% endif %}</div>
            </div>
            <div class="card">
                <h3>Diagnostic Accuracy</h3>
                <div class="value">{% if b.diagnosis_accuracy is not none %}{{ "%.0f"|format(b.diagnosis_accuracy * 100) }}%{% else %}n/a{% endif %}</div>
            </div>
        </div>
        <p class="note">
            Behaviors tested: distinct behaviors checked by passing tests, as stated for each generated test.
            Mutation score: share of injected single-site behavior changes the generated suite detects.
            Diagnostic accuracy: share of failures with a known cause that the diagnosis agent classified correctly.
            {% if not b.available %}
            Mutation score and diagnostic accuracy come from <code>code2test benchmark</code>, which has not been run.
            {% else %}
            From the <code>code2test benchmark</code> run of {{ b.created_at or "an unknown date" }}.
            {% if b.stale %}<strong>That run predates the last <code>code2test test</code> run, so it measured an earlier suite.</strong>{% endif %}
            {% endif %}
        </p>
        <table>
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Intent</th>
                    <th>Passing tests</th>
                    <th>Behaviors tested</th>
                    <th>Mutants killed</th>
                </tr>
            </thead>
            <tbody>
                {% for c in quality.components %}
                <tr>
                    <td>{{ c.component }}</td>
                    <td>{{ c.intent or "" }}</td>
                    <td>{{ c.tests_passing }}{% if c.tests_xfail %} (+{{ c.tests_xfail }} xfail){% endif %}</td>
                    <td>
                        {% if c.behaviors_tested %}
                        <details><summary>{{ c.behaviors_tested|length }}</summary>
                            <ul>{% for item in c.behaviors_tested %}<li>{{ item }}</li>{% endfor %}</ul>
                        </details>
                        {% else %}0{% endif %}
                    </td>
                    <td>{% if c.mutants %}{{ c.mutants_killed }}/{{ c.mutants }} ({{ "%.0f"|format(c.mutation_score * 100) }}%){% else %}n/a{% endif %}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
"""

COVERAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Code2Test Coverage Report</title>
    {% include "style" %}
</head>
<body>
    <div class="container">
        <h1>Code2Test Coverage Report</h1>
        <p>Generated on: {{ timestamp }}</p>
        {% include "quality" %}
    </div>
</body>
</html>
"""

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Code2Test Report - {{ suite.module_path }}</title>
    {% include "style" %}
</head>
<body>
    <div class="container">
        <h1>Code2Test Generation Report</h1>
        <p>Generated on: {{ timestamp }}</p>
        
        <div class="summary">
            <div class="card">
                <h3>Total Tests</h3>
                <div class="value">{{ suite.total_tests }}</div>
            </div>
            <div class="card">
                <h3>Files Generated</h3>
                <div class="value">{{ suite.test_files|length }}</div>
            </div>
            <div class="card">
                <h3>Verified Files</h3>
                <div class="value">{{ verified_count }}</div>
            </div>
            <div class="card">
                <h3>Success Rate</h3>
                <div class="value">{{ "%.1f"|format(success_rate) }}%</div>
            </div>
        </div>
        {% if quality %}{% include "quality" %}{% endif %}
        
        <h2>Test Files</h2>
        <table>
            <thead>
                <tr>
                    <th>File Path</th>
                    <th>Component</th>
                    <th>Tests</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for file in suite.test_files %}
                <tr>
                    <td>{{ file.path }}</td>
                    <td>{{ file.component_id }}</td>
                    <td>{{ file.test_cases|length }}</td>
                    <td>
                        {% if file.verified %}
                        <span class="badge badge-success">Verified</span>
                        {% else %}
                        <span class="badge badge-warning">Unverified</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <h2>Intents Detected</h2>
        <table>
            <thead>
                <tr>
                    <th>Component</th>
                    <th>Confidence</th>
                    <th>Intent Summary</th>
                </tr>
            </thead>
            <tbody>
                {% for id, intent in intents.items() %}
                <tr>
                    <td>{{ id }}</td>
                    <td>
                        <div style="width: 100px; background: #eee; height: 10px; border-radius: 5px; overflow: hidden;">
                            <div style="width: {{ intent.confidence * 100 }}%; background: {% if intent.confidence > 0.8 %}green{% elif intent.confidence > 0.5 %}orange{% else %}red{% endif %}; height: 100%;"></div>
                        </div>
                        {{ "%.0f"|format(intent.confidence * 100) }}%
                    </td>
                    <td>{{ intent.intent_text[:100] }}{% if intent.intent_text|length > 100 %}...{% endif %}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""


class HTMLReportGenerator:
    """Generates HTML reports for test generation results."""

    TEMPLATE = TEMPLATE

    def _env(self) -> Environment:
        loader = DictLoader(
            {
                "style": STYLE,
                "quality": QUALITY_SECTION,
                "report": self.TEMPLATE,
                "coverage": COVERAGE_TEMPLATE,
            }
        )
        return Environment(loader=loader, autoescape=True)

    def generate_report(
        self,
        test_suite: TestSuite,
        intents: Dict[str, Intent],
        output_path: str,
        quality: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate comprehensive HTML report.

        Args:
            test_suite: The generated test suite
            intents: Dictionary of detected intents
            output_path: Path to write the HTML report to
            quality: Behavioral coverage and diagnostic accuracy (code2test.core.quality.quality_report)

        Returns:
            The generated HTML content
        """
        verified_count = sum(1 for f in test_suite.test_files if f.verified)
        total_files = len(test_suite.test_files)
        success_rate = (verified_count / total_files * 100) if total_files > 0 else 0

        html_content = (
            self._env()
            .get_template("report")
            .render(
                suite=test_suite,
                intents=intents,
                quality=quality,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                verified_count=verified_count,
                success_rate=success_rate,
            )
        )

        with open(output_path, "w") as f:
            f.write(html_content)

        return html_content

    def generate_quality_report(self, quality: Dict[str, Any], output_path: str) -> str:
        """Write a standalone page with behavioral coverage and diagnostic accuracy."""
        html_content = (
            self._env()
            .get_template("coverage")
            .render(
                quality=quality,
                timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        with open(output_path, "w") as f:
            f.write(html_content)
        return html_content

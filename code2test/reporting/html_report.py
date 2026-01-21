"""
HTML Reporting Module.
"""
import os
import datetime
from typing import Dict, Any, List
from jinja2 import Environment, BaseLoader

from code2test.core.models import TestSuite, Intent

class HTMLReportGenerator:
    """Generates HTML reports for test generation results."""
    
    TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Code2Test Report - {{ suite.module_path }}</title>
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
    </style>
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

    def generate_report(self, test_suite: TestSuite, intents: Dict[str, Intent], output_path: str) -> str:
        """
        Generate comprehensive HTML report.
        
        Args:
            test_suite: The generated test suite
            intents: Dictionary of detected intents
            output_path: Path to write the HTML report to
            
        Returns:
            The generated HTML content
        """
        env = Environment(loader=BaseLoader())
        template = env.from_string(self.TEMPLATE)
        
        verified_count = sum(1 for f in test_suite.test_files if f.verified)
        total_files = len(test_suite.test_files)
        success_rate = (verified_count / total_files * 100) if total_files > 0 else 0
        
        html_content = template.render(
            suite=test_suite,
            intents=intents,
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            verified_count=verified_count,
            success_rate=success_rate
        )
        
        with open(output_path, 'w') as f:
            f.write(html_content)
            
        return html_content

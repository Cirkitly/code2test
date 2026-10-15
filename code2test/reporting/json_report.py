"""
JSON Reporting Module.
"""
import json
import datetime
from typing import Any, Dict, Optional

from code2test.core.models import TestSuite, Intent

class JSONReportGenerator:
    """Generates JSON reports for machine consumption."""
    
    def generate_report(self, test_suite: TestSuite, intents: Dict[str, Intent], output_path: str,
                        quality: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate JSON report data.
        
        Args:
            test_suite: The generated test suite
            intents: Dictionary of intents
            output_path: Path to write the JSON report to
            quality: Behavioral coverage and diagnostic accuracy (code2test.core.quality.quality_report)
            
        Returns:
            The report dictionary
        """
        verified_count = sum(1 for f in test_suite.test_files if f.verified)
        
        report_data = {
            "metadata": {
                "timestamp": datetime.datetime.now().isoformat(),
                "tool": "code2test",
                "version": "0.1.0"
            },
            "summary": {
                "module_path": test_suite.module_path,
                "total_tests": test_suite.total_tests,
                "total_files": len(test_suite.test_files),
                "verified_files": verified_count,
                "success_rate":  (verified_count / len(test_suite.test_files)) if test_suite.test_files else 0
            },
            "files": [
                {
                    "path": f.path,
                    "component_id": f.component_id,
                    "test_count": len(f.test_cases),
                    "verified": f.verified,
                    "test_cases": [
                        {
                            "name": tc.name,
                            "status": tc.status
                        } for tc in f.test_cases
                    ]
                } for f in test_suite.test_files
            ],
            "intents": {
                comp_id: {
                    "text": intent.intent_text,
                    "confidence": intent.confidence,
                    "user_edited": intent.user_edited
                } for comp_id, intent in intents.items()
            },
            "quality": quality,
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        return report_data

    def generate_quality_report(self, quality: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """Write behavioral coverage and diagnostic accuracy as JSON."""
        report_data = {
            "metadata": {"timestamp": datetime.datetime.now().isoformat(), "tool": "code2test", "version": "0.1.0"},
            **quality,
        }
        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2)
        return report_data

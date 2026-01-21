"""
Template manager for Code2Test.
"""

import os
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

class TemplateManager:
    """Manages Jinja2 templates for test generation."""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize template manager.
        
        Args:
            templates_dir: Custom path to templates directory. 
                           Defaults to built-in templates.
        """
        if templates_dir is None:
            # Assume templates are relative to this file's package
            # code2test/core/templates.py -> code2test/templates/
            base_dir = os.path.dirname(os.path.dirname(__file__))
            templates_dir = os.path.join(base_dir, "templates")
            
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Render a template with context.
        
        Args:
            template_path: Path to template relative to templates root 
                           (e.g., 'python/pytest/test_file.j2')
            context: Variables to pass to template
            
        Returns:
            Rendered string
        """
        template = self.env.get_template(template_path)
        return template.render(**context)

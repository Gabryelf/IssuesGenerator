from typing import Dict, List, Optional
from backend.src.models.schemas import IssueTemplate, TemplateField


class TemplateService:
    """Service for managing issue templates"""

    # Predefined templates library
    PREDEFINED_TEMPLATES = {
        "bug_report": {
            "name": "bug_report",
            "title": "Bug Report: ",
            "description": "Standard bug report template",
            "body": """## 🐛 Bug Description

**What happened?**
[Clear and concise description of the bug]

**Steps to Reproduce**
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected Behavior**
[What you expected to happen]

**Actual Behavior**
[What actually happened]

**Screenshots/Logs**
            

**Environment**
- OS: [e.g., Windows 10, macOS 11.0]
- Browser: [e.g., Chrome 90, Safari 14]
- Version: [e.g., 1.2.3]

**Additional Context**
[Add any other context about the problem here]""",
            "fields": [
                {
                    "name": "bug_description",
                    "label": "Bug Description",
                    "type": "textarea",
                    "placeholder": "Describe the bug in detail",
                    "required": True
                },
                {
                    "name": "environment",
                    "label": "Environment",
                    "type": "text",
                    "placeholder": "Windows 10, Chrome 90",
                    "required": False
                }
            ],
            "labels": ["bug", "needs-triage"],
            "is_public": True
        },

        "feature_request": {
            "name": "feature_request",
            "title": "Feature Request: ",
            "description": "Template for requesting new features",
            "body": """## 🚀 Feature Request

**Feature Description**
[Clear and concise description of the feature]

**Problem Statement**
[What problem does this feature solve?]

**Proposed Solution**
[How should this feature work?]

**Alternatives Considered**
[Any alternative solutions or features considered]

**Use Cases**
1. [Use case 1]
2. [Use case 2]
3. [Use case 3]

**Additional Context**
[Add any other context, mockups, or references here]""",
            "fields": [
                {
                    "name": "feature_description",
                    "label": "Feature Description",
                    "type": "textarea",
                    "required": True
                },
                {
                    "name": "use_cases",
                    "label": "Use Cases",
                    "type": "textarea",
                    "placeholder": "List the main use cases",
                    "required": False
                }
            ],
            "labels": ["enhancement", "feature-request"],
            "is_public": True
        },

        "documentation": {
            "name": "documentation",
            "title": "Documentation: ",
            "description": "Documentation improvement request",
            "body": """## 📚 Documentation Update

**Section to Update**
[Which part of documentation needs updating?]

**Current Documentation Issue**
[What's wrong with the current documentation?]

**Suggested Changes**
[Proposed documentation changes]

**Related Files/Sections**
- [File/Section 1]
- [File/Section 2]

**Additional Notes**
[Any additional information or references]""",
            "fields": [],
            "labels": ["documentation"],
            "is_public": True
        },

        "security": {
            "name": "security",
            "title": "Security Issue: ",
            "description": "Template for reporting security vulnerabilities",
            "body": """## 🔒 Security Vulnerability Report

**IMPORTANT: This issue will be created as private**

**Vulnerability Description**
[Description of the security issue]

**Affected Components**
- [Component 1]
- [Component 2]

**Steps to Exploit**
1. [Step 1]
2. [Step 2]

**Potential Impact**
[What could an attacker achieve?]

**Suggested Fix**
[How to fix the vulnerability]

**References**
[Any references or CVEs]""",
            "fields": [],
            "labels": ["security", "critical"],
            "is_public": False
        },

        "code_review": {
            "name": "code_review",
            "title": "Code Review: ",
            "description": "Request for code review",
            "body": """## 👀 Code Review Request

**PR/Commit Reference**
[Link to PR or commit hash]

**Changes Overview**
[Brief overview of changes]

**Areas of Concern**
- [Area 1]
- [Area 2]

**Testing Done**
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

**Review Checklist**
- [ ] Code follows style guidelines
- [ ] No obvious bugs
- [ ] Performance considered
- [ ] Security implications reviewed""",
            "fields": [],
            "labels": ["code-review"],
            "is_public": True
        }
    }

    @classmethod
    def get_predefined_templates(cls) -> Dict[str, IssueTemplate]:
        """Get all predefined templates as IssueTemplate objects"""
        templates = {}
        for name, template_data in cls.PREDEFINED_TEMPLATES.items():
            # Convert dict to IssueTemplate with proper field conversion
            template_data_copy = template_data.copy()

            # Convert fields dicts to TemplateField objects
            if template_data_copy.get("fields"):
                template_data_copy["fields"] = [
                    TemplateField(**field) for field in template_data_copy["fields"]
                ]

            templates[name] = IssueTemplate(**template_data_copy)
        return templates

    @classmethod
    def get_template(cls, template_name: str) -> Optional[IssueTemplate]:
        """Get specific template by name"""
        templates = cls.get_predefined_templates()
        return templates.get(template_name)

    @classmethod
    def populate_template(
            cls,
            template_name: str,
            data: Dict[str, str]
    ) -> Optional[str]:
        """Populate template with user data"""
        template = cls.get_template(template_name)
        if not template:
            return None

        body = template.body

        # Replace placeholders with user data
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            body = body.replace(placeholder, value)

        return body

    @classmethod
    def get_template_fields(cls, template_name: str) -> List[Dict]:
        """Get fields for a template as dictionaries"""
        template = cls.get_template(template_name)
        if template and template.fields:
            return [field.dict() for field in template.fields]
        return []

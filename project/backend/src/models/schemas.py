from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


# TemplateField должен быть Pydantic моделью
class TemplateField(BaseModel):
    name: str
    label: str
    type: str = "text"  # text, textarea, select, checkbox
    required: bool = True
    options: Optional[List[str]] = None
    placeholder: Optional[str] = ""
    default_value: Optional[str] = ""


# Issue related schemas
class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    template_name: Optional[str] = None
    labels: Optional[List[str]] = []
    assignees: Optional[List[str]] = []


class GitHubIssueRequest(BaseModel):
    title: str
    body: str
    token: str
    username: str
    repo_name: str
    labels: Optional[List[str]] = []
    assignees: Optional[List[str]] = []


# Repository schemas
class RepositoryConnection(BaseModel):
    username: str
    repo_name: str
    token: str
    save_to_redis: bool = True
    metadata: Optional[Dict] = {}


class RepositoryInfo(BaseModel):
    username: str
    repo_name: str
    last_used: Optional[datetime] = None
    metadata: Optional[Dict] = {}


# Template schemas
class IssueTemplate(BaseModel):
    name: str
    title: str
    body: str
    description: Optional[str] = ""
    fields: Optional[List[TemplateField]] = []  # Изменено с Dict на TemplateField
    is_public: bool = False
    labels: Optional[List[str]] = []


# Response schemas
class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None


class IssueResponse(StandardResponse):
    issue_url: Optional[str] = None


class RepositoriesResponse(StandardResponse):
    repositories: List[RepositoryInfo]


class TemplatesResponse(StandardResponse):
    templates: List[IssueTemplate]
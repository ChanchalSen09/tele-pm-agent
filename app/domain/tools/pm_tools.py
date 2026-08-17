"""Pydantic Function & Tool Schemas for Gemini Structured Tool Use."""

from typing import Literal

from pydantic import BaseModel, Field


class CreateTaskArgs(BaseModel):
    """Arguments for creating a project task."""

    title: str = Field(description="Short title or description of the task")
    assignee: str | None = Field(
        default=None, description="Username or first name of the assignee"
    )
    priority: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        default="HIGH", description="Priority level of the task"
    )
    due_date: str | None = Field(
        default=None, description="Optional due date in YYYY-MM-DD format"
    )


class UpdateTaskStatusArgs(BaseModel):
    """Arguments for updating a task's progress status."""

    task_id: str = Field(description="Task UUID or 8-character prefix")
    new_status: Literal["TODO", "IN_PROGRESS", "BLOCKED", "DONE"] = Field(
        description="Target status for the task"
    )


class GetTaskBoardArgs(BaseModel):
    """Arguments for fetching active project tasks."""

    status_filter: Literal["ALL", "TODO", "IN_PROGRESS", "BLOCKED", "DONE"] = Field(
        default="ALL", description="Filter tasks by status"
    )


class GetSprintSummaryArgs(BaseModel):
    """Arguments for generating sprint progress summary report."""

    include_completed: bool = Field(
        default=True, description="Include completed tasks in report"
    )

from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models.task import Priority, Status


class TaskBase(BaseModel):
    title: str = Field(..., examples=["Example task"])
    description: str | None = Field(None, examples=["Detailed description of the task"])
    priority: Priority = Field(..., examples=[Priority.MEDIUM])


class TaskCreate(TaskBase):
    """Schema for creating a new task"""

    pass


class TaskRead(BaseModel):
    """Schema for reading task data"""

    id: int
    title: str
    description: str | None
    priority: Priority
    status: Status
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: str | None = None
    error: str | None = None

    class Config:
        from_attributes = True


class TaskStatus(BaseModel):
    """Schema for task status only"""

    status: Status

    class Config:
        from_attributes = True

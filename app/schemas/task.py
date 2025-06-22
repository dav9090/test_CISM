from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.db.models.task import Priority, Status


class TaskBase(BaseModel):
    title: str = Field(..., example="Example task")
    description: Optional[str] = Field(None, example="Detailed description of the task")
    priority: Priority = Field(..., example=Priority.MEDIUM)


class TaskCreate(TaskBase):
    """Схема для создания новой задачи"""

    pass


class TaskRead(TaskBase):
    """Схема для чтения задачи"""

    id: str
    status: Status
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None

    class Config:
        orm_mode = True


class TaskStatus(BaseModel):
    """Схема для запроса только статуса задачи"""

    status: Status

    class Config:
        orm_mode = True

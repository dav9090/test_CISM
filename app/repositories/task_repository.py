from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.models.task import Status
from app.db.models.task import Task as TaskModel
from app.schemas.task import TaskCreate


class TaskRepository:
    """Repository for task database operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, task_data: TaskCreate) -> TaskModel:
        """Create a new task"""
        from datetime import datetime

        task = TaskModel(
            **task_data.model_dump(), status=Status.NEW, created_at=datetime.utcnow()
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Optional[TaskModel]:
        """Get task by ID"""
        return await self.db.get(TaskModel, task_id)

    async def get_all(
        self,
        status: Optional[Status] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TaskModel]:
        """Get tasks with optional filtering and pagination"""
        stmt = select(TaskModel).offset(skip).limit(limit)

        if status:
            stmt = stmt.where(TaskModel.status == status)
        if priority:
            stmt = stmt.where(TaskModel.priority == priority)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, task_id: int, status: Status) -> Optional[TaskModel]:
        """Update task status"""
        task = await self.get_by_id(task_id)
        if task:
            task.status = status
            await self.db.commit()
            await self.db.refresh(task)
        return task

    async def cancel_task(self, task_id: int) -> Optional[TaskModel]:
        """Cancel a task if it can be cancelled"""
        task = await self.get_by_id(task_id)
        if task and task.status not in {
            Status.COMPLETED,
            Status.FAILED,
            Status.CANCELLED,
        }:
            task.status = Status.CANCELLED
            await self.db.commit()
            await self.db.refresh(task)
            return task
        return None

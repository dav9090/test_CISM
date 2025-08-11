from collections.abc import Sequence
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.db.models.task import Status
from app.db.session import get_db
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskRead, TaskStatus
from app.services.task_processor import get_task_processor

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"],
    responses={
        HTTP_404_NOT_FOUND: {"description": "Task not found"},
        HTTP_400_BAD_REQUEST: {"description": "Invalid request or operation"},
    },
)


@router.post(
    "",
    response_model=TaskRead,
    status_code=HTTP_201_CREATED,
    summary="Create a new task",
    description="Create a task with title, description and priority. "
    "The task is persisted with status NEW and enqueued for background processing.",
    response_description="The created task with its assigned ID and status",
)
async def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    """
    Create a new task and enqueue it for processing.

    - **title**: task title
    - **description**: detailed description
    - **priority**: task priority (LOW, MEDIUM, HIGH)
    """
    repository = TaskRepository(db)
    task = await repository.create(payload)

    # Enqueue task for background processing
    processor = get_task_processor()
    background_tasks.add_task(processor.enqueue, str(task.id))

    return task


@router.get(
    "",
    response_model=list[TaskRead],
    summary="List tasks",
    description="Retrieve tasks with optional filtering by status or priority, "
    "and pagination (skip/limit).",
    response_description="List of tasks",
)
async def list_tasks(
    status: Optional[Status] = Query(None, description="Filter by task status"),
    priority: Optional[str] = Query(None, description="Filter by task priority"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, gt=0, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db),
) -> Sequence[TaskRead]:
    """
    Return list of tasks filtered by status and/or priority.
    """
    repository = TaskRepository(db)
    return await repository.get_all(
        status=status, priority=priority, skip=skip, limit=limit
    )


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Get task details",
    description="Retrieve detailed information of a specific task by its ID.",
    response_description="Task details",
)
async def get_task(
    task_id: int = Path(..., description="Unique identifier of the task"),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    """
    Get complete task information.
    """
    repository = TaskRepository(db)
    task = await repository.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

    return task


@router.delete(
    "/{task_id}",
    response_model=TaskStatus,
    summary="Cancel a task",
    description="Cancel a pending or in-progress task. "
    "Tasks in COMPLETED, FAILED or already CANCELLED cannot be cancelled.",
    response_description="New task status",
)
async def cancel_task(
    task_id: int = Path(..., description="Unique identifier of the task to cancel"),
    db: AsyncSession = Depends(get_db),
) -> TaskStatus:
    """
    Cancel a task if it's not yet completed.
    """
    repository = TaskRepository(db)
    task = await repository.cancel_task(task_id)

    if not task:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail="Cannot cancel task"
        )

    return TaskStatus(status=task.status)


@router.get(
    "/{task_id}/status",
    response_model=TaskStatus,
    summary="Get task status",
    description="Retrieve the current status of a task without loading all its "
    "details.",
    response_description="Current status of the task",
)
async def get_task_status(
    task_id: int = Path(..., description="Unique identifier of the task"),
    db: AsyncSession = Depends(get_db),
) -> TaskStatus:
    """
    Return only the task status.
    """
    repository = TaskRepository(db)
    task = await repository.get_by_id(task_id)

    if not task:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

    return TaskStatus(status=task.status)

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.db.models.task import Task as TaskModel, Status
from app.schemas.task import TaskCreate, TaskRead, TaskStatus
from app.services.task_processor import get_task_processor

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"],
    responses={
        404: {"description": "Task not found"},
        400: {"description": "Invalid request or operation"},
    },
)


@router.post(
    "",
    response_model=TaskRead,
    status_code=201,
    summary="Create a new task",
    description="Create a task with title, description and priority. "
    "The task is persisted with status NEW and enqueued for background processing.",
    response_description="The created task with its assigned ID and status",
)
async def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Создаёт новую задачу и ставит её в очередь на обработку.

    - **title**: заголовок задачи
    - **description**: подробное описание
    - **priority**: приоритет задачи (LOW, MEDIUM, HIGH)
    """
    # 1) Сохраняем задачу в БД
    task = TaskModel(**payload.dict(), status=Status.NEW)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 2) Ставим задачу в очередь фоном, передаём только ID
    processor = get_task_processor()
    background_tasks.add_task(processor.enqueue, str(task.id))

    return task


@router.get(
    "",
    response_model=List[TaskRead],
    summary="List tasks",
    description="Retrieve tasks with optional filtering by status or priority, "
    "and pagination (skip/limit).",
    response_description="Список задач",
)
async def list_tasks(
    status: Optional[Status] = Query(None, description="Filter by task status"),
    priority: Optional[str] = Query(None, description="Filter by task priority"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, gt=0, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает список задач, отфильтрованных по статусу и/или приоритету.
    """
    stmt = select(TaskModel).offset(skip).limit(limit)
    if status:
        stmt = stmt.where(TaskModel.status == status)
    if priority:
        stmt = stmt.where(TaskModel.priority == priority)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Get task details",
    description="Retrieve detailed information of a specific task by its ID.",
    response_description="Детали задачи",
)
async def get_task(
    task_id: str = Path(..., description="Unique identifier of the task"),
    db: AsyncSession = Depends(get_db),
):
    """
    Получает полную информацию по задаче.
    """
    try:
        pk = int(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    task = await db.get(TaskModel, pk)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskRead.from_orm(task)


@router.delete(
    "/{task_id}",
    response_model=TaskStatus,
    summary="Cancel a task",
    description="Cancel a pending or in-progress task. "
    "Tasks in COMPLETED, FAILED or already CANCELLED cannot be cancelled.",
    response_description="Новый статус задачи",
)
async def cancel_task(
    task_id: str = Path(..., description="Unique identifier of the task to cancel"),
    db: AsyncSession = Depends(get_db),
):
    """
    Отменяет задачу, если она ещё не выполнена.
    """
    try:
        pk = int(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    task = await db.get(TaskModel, pk)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in {Status.COMPLETED, Status.FAILED, Status.CANCELLED}:
        raise HTTPException(status_code=400, detail="Cannot cancel")
    task.status = Status.CANCELLED
    await db.commit()
    return TaskStatus(status=task.status)


@router.get(
    "/{task_id}/status",
    response_model=TaskStatus,
    summary="Get task status",
    description="Retrieve the current status of a task without loading all its details.",
    response_description="Current status of the task",
)
async def get_task_status(
    task_id: str = Path(..., description="Unique identifier of the task"),
    db: AsyncSession = Depends(get_db),
):
    """
    Возвращает только статус задачи.
    """
    try:
        pk = int(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    task = await db.get(TaskModel, pk)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatus(status=task.status)

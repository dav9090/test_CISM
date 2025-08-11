import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models.task import Priority, Status
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate


@pytest_asyncio.fixture
async def test_db():
    """Создаем тестовую in-memory базу данных"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async with AsyncSessionLocal() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
def repository(test_db):
    """Создаем репозиторий с тестовой БД"""
    return TaskRepository(test_db)


@pytest.mark.asyncio
async def test_create_task(repository):
    """Тест создания задачи"""
    task_data = TaskCreate(
        title="Test Task", description="Test Description", priority=Priority.HIGH
    )

    task = await repository.create(task_data)

    assert task.title == "Test Task"
    assert task.description == "Test Description"
    assert task.priority == Priority.HIGH
    assert task.status == Status.NEW
    assert task.id is not None


@pytest.mark.asyncio
async def test_get_by_id(repository):
    """Тест получения задачи по ID"""
    # Создаем задачу
    task_data = TaskCreate(
        title="Test Task", description="Test Description", priority=Priority.MEDIUM
    )
    created_task = await repository.create(task_data)

    # Получаем по ID
    retrieved_task = await repository.get_by_id(created_task.id)

    assert retrieved_task is not None
    assert retrieved_task.id == created_task.id
    assert retrieved_task.title == created_task.title


@pytest.mark.asyncio
async def test_get_all_with_filtering(repository):
    """Тест получения списка задач с фильтрацией"""
    # Создаем несколько задач
    await repository.create(
        TaskCreate(title="High Priority", description="High", priority=Priority.HIGH)
    )
    await repository.create(
        TaskCreate(title="Low Priority", description="Low", priority=Priority.LOW)
    )

    # Получаем все задачи
    all_tasks = await repository.get_all()
    assert len(all_tasks) >= 2

    # Фильтруем по приоритету
    high_tasks = await repository.get_all(priority="HIGH")
    assert all(task.priority == Priority.HIGH for task in high_tasks)


@pytest.mark.asyncio
async def test_cancel_task(repository):
    """Тест отмены задачи"""
    # Создаем задачу
    task_data = TaskCreate(
        title="To Cancel", description="Will be cancelled", priority=Priority.LOW
    )
    task = await repository.create(task_data)

    # Отменяем задачу
    cancelled_task = await repository.cancel_task(task.id)

    assert cancelled_task is not None
    assert cancelled_task.status == Status.CANCELLED


@pytest.mark.asyncio
async def test_cancel_completed_task(repository):
    """Тест отмены уже завершенной задачи"""
    # Создаем задачу
    task_data = TaskCreate(
        title="Completed Task",
        description="Already completed",
        priority=Priority.MEDIUM,
    )
    task = await repository.create(task_data)

    # Меняем статус на COMPLETED
    await repository.update_status(task.id, Status.COMPLETED)

    # Пытаемся отменить
    cancelled_task = await repository.cancel_task(task.id)

    # Должно вернуть None, так как задача уже завершена
    assert cancelled_task is None

import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskRead, TaskStatus
from app.db.models.task import Priority, Status
from app.services.task_processor import TaskProcessor, get_task_processor


def test_task_create_schema_valid():
    payload = {"title": "Test", "description": "Desc", "priority": "HIGH"}
    task = TaskCreate(**payload)
    assert task.title == "Test"
    assert task.description == "Desc"
    assert task.priority == Priority.HIGH


def test_task_create_schema_missing_fields():
    with pytest.raises(ValidationError):
        # не хватает description и priority
        TaskCreate(title="Test")


def test_task_read_from_orm():
    # создаём «сырой» объект с атрибутами
    class Dummy:
        id = "123"
        title = "Test"
        description = "Desc"
        priority = Priority.LOW
        status = Status.NEW
        created_at = "2025-06-20T10:00:00"
        started_at = None
        completed_at = None
        result = None
        error = None

    dummy = Dummy()
    task = TaskRead.from_orm(dummy)
    assert task.id == "123"
    assert task.status == Status.NEW
    assert task.priority == Priority.LOW


def test_task_status_schema_valid_and_invalid():
    st = TaskStatus(status="IN_PROGRESS")
    assert st.status == Status.IN_PROGRESS

    with pytest.raises(ValidationError):
        TaskStatus(status="NOT_A_STATUS")


def test_get_task_processor_singleton():
    p1 = get_task_processor()
    p2 = get_task_processor()
    assert isinstance(p1, TaskProcessor)
    # должно быть один и тот же экземпляр
    assert p1 is p2

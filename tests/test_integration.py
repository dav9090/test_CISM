import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.api.v1.endpoints.tasks as tasks_module
import app.db.session as session_module
from app.db.base import Base
from app.db.models.task import Status
from app.db.models.task import Task as TaskModel
from app.main import app
from app.worker import handle_message


class DummyProcessor:
    async def enqueue(self, task_id: str):
        # вместо реального RabbitMQ просто «мокаем» вызов
        return


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """
    Сессия-скоуп фикстура для asyncio-loop,
    которую pytest-asyncio сможет зарезолвить.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def prepare_test_db(monkeypatch):
    # in-memory SQLite
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        # создаём все таблицы
        await conn.run_sync(Base.metadata.create_all)

    # фабрика сессий
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    # подменяем подключение к БД на наш in-memory
    monkeypatch.setattr(session_module, "get_db", override_get_db)
    # подменяем TaskProcessor на DummyProcessor
    monkeypatch.setattr(tasks_module, "get_task_processor", lambda: DummyProcessor())

    yield

    # после всех тестов удаляем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_create_and_get_task(client: AsyncClient):
    payload = {
        "title": "Integration Test",
        "description": "Checking create",
        "priority": "MEDIUM",
    }
    # создаём
    resp = await client.post("/api/v1/tasks", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    task_id = data["id"]

    # получаем по ID
    resp2 = await client.get(f"/api/v1/tasks/{task_id}")
    assert resp2.status_code == 200
    detail = resp2.json()
    assert detail["title"] == payload["title"]
    assert detail["status"] == "NEW"

    # статус через отдельный эндпоинт
    resp3 = await client.get(f"/api/v1/tasks/{task_id}/status")
    assert resp3.status_code == 200
    assert resp3.json()["status"] == "NEW"


@pytest.mark.asyncio
async def test_list_and_filter_tasks(client: AsyncClient):
    # создаём две задачи разного приоритета
    await client.post(
        "/api/v1/tasks", json={"title": "LowPr", "description": "", "priority": "LOW"}
    )
    await client.post(
        "/api/v1/tasks", json={"title": "HighPr", "description": "", "priority": "HIGH"}
    )

    # без фильтрации
    resp = await client.get("/api/v1/tasks")
    assert resp.status_code == 200
    lst = resp.json()
    assert isinstance(lst, list)
    assert len(lst) >= 2

    # фильтрация по HIGH
    resp2 = await client.get("/api/v1/tasks", params={"priority": "HIGH"})
    assert resp2.status_code == 200
    filtered = resp2.json()
    assert all(item["priority"] == "HIGH" for item in filtered)


@pytest.mark.asyncio
async def test_cancel_task_and_not_found(client: AsyncClient):
    # создаём задачу
    resp = await client.post(
        "/api/v1/tasks",
        json={"title": "ToCancel", "description": "", "priority": "LOW"},
    )
    tid = resp.json()["id"]

    # отменяем
    resp2 = await client.delete(f"/api/v1/tasks/{tid}")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "CANCELLED"

    # повторная отмена — ошибка 4xx
    resp3 = await client.delete(f"/api/v1/tasks/{tid}")
    assert 400 <= resp3.status_code < 500

    # несуществующий ID — все эндпоинты 404
    fake = 99999  # используем int вместо UUID
    assert (await client.get(f"/api/v1/tasks/{fake}")).status_code == 404
    assert (await client.get(f"/api/v1/tasks/{fake}/status")).status_code == 404
    assert (await client.delete(f"/api/v1/tasks/{fake}")).status_code == 404


@pytest.mark.asyncio
async def test_handle_message(monkeypatch):
    # 1. В памяти заводим sqlite и создаём таблицы
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Переопределяем глобальную фабрику сессий, которую берёт worker
    TestSession = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr("app.worker.AsyncSessionLocal", TestSession)

    # 3. Добавляем в БД тестовую задачу
    async with TestSession() as session:
        t = TaskModel(title="T", description="", priority="LOW")
        session.add(t)
        await session.commit()
        task_id = t.id

    # 4. Эмулируем aio_pika.IncomingMessage с телом b"{task_id}"
    class DummyMessage:
        def __init__(self, body: bytes):
            self.body = body

        # контекст-менеджер .process()
        def process(self):
            class Ctx:
                async def __aenter__(self_inner):
                    return self_inner

                async def __aexit__(self_inner, exc_type, exc, tb):
                    pass

            return Ctx()

    msg = DummyMessage(body=str(task_id).encode())

    # 5. Вызываем нашу функцию и ждём, пока она отработает
    start = datetime.now(timezone.utc)
    await handle_message(msg)
    duration = (datetime.now(timezone.utc) - start).total_seconds()

    # 6. Проверяем, что она действительно ждёт хотя бы 2 секунды
    assert duration >= 2

    # 7. И проверяем, что в БД статус и поля проставились
    async with TestSession() as session:
        task = await session.get(TaskModel, task_id)
        assert task.status == Status.COMPLETED
        assert task.result == "Processed successfully"
        assert task.started_at is not None
        assert task.finished_at is not None

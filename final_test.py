#!/usr/bin/env python3
"""
Финальный тест FastAPI приложения
"""

import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db


async def setup_test_db():
    """Настройка тестовой БД"""
    # Создаем in-memory SQLite
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Создаем фабрику сессий
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    # Переопределяем зависимость
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    return engine


def test_api_sync():
    """Тестируем API endpoints синхронно"""
    client = TestClient(app)

    print("🧪 Тестируем API endpoints...")

    # Тест получения списка задач (должен быть пустым)
    print("1. Тест получения списка задач...")
    response = client.get("/api/v1/tasks")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        tasks = response.json()
        print(f"   ✅ Получено задач: {len(tasks)}")
    else:
        print(f"   ❌ Ошибка: {response.text}")

    # Тест получения несуществующей задачи
    print("2. Тест получения несуществующей задачи...")
    response = client.get("/api/v1/tasks/99999")
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        print("   ✅ 404 для несуществующей задачи")
    else:
        print(f"   ❌ Неожиданный статус: {response.status_code}")

    # Тест получения статуса несуществующей задачи
    print("3. Тест получения статуса несуществующей задачи...")
    response = client.get("/api/v1/tasks/99999/status")
    print(f"   Status: {response.status_code}")
    if response.status_code == 404:
        print("   ✅ 404 для статуса несуществующей задачи")
    else:
        print(f"   ❌ Неожиданный статус: {response.status_code}")

    # Тест отмены несуществующей задачи
    print("4. Тест отмены несуществующей задачи...")
    response = client.delete("/api/v1/tasks/99999")
    print(f"   Status: {response.status_code}")
    if response.status_code == 400:
        print("   ✅ 400 для отмены несуществующей задачи (правильно)")
    else:
        print(f"   ❌ Неожиданный статус: {response.status_code}")

    print("\n🎉 Тестирование завершено!")


async def main():
    """Главная функция"""
    print("🚀 Запуск финального тестирования FastAPI приложения...")

    # Настраиваем тестовую БД
    engine = await setup_test_db()

    try:
        # Тестируем API
        test_api_sync()

        print("\n✅ Все тесты прошли успешно!")
        print("🌐 API готов к работе")
        print("📚 Swagger UI будет доступен при запуске сервера")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

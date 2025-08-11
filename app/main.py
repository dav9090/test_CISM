import structlog
import uvicorn
from fastapi import FastAPI

from app.api.v1.endpoints.tasks import router as tasks_router
from app.core.logging import init_logging
from app.services.task_processor import get_task_processor

logger = structlog.get_logger()
# Инициализация логирования
init_logging()

app = FastAPI(
    title="Async Task Service",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Подключаем роуты
app.include_router(tasks_router)


@app.on_event("startup")
async def on_startup() -> None:
    try:
        await get_task_processor().initialize()
    except Exception as e:
        # В тестах сюда придёт DummyProcessor, а реальное подключение не дойдёт до этого блока
        logger.warning(
            "Не удалось подключиться к RabbitMQ, работаем без очереди", error=str(e)
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        # например, можно выставить log_level из настроек
        log_level="info",
    )

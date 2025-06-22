import asyncio
from datetime import datetime, timezone

import structlog
from aio_pika import connect_robust, IncomingMessage, ExchangeType
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.models.task import Task as TaskModel, Status

# Настраиваем structlog для JSON-логов
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

# Фабрика сессий, инициализируется в main()
AsyncSessionLocal: async_sessionmaker[AsyncSession] = None  # type: ignore[arg-type]


async def handle_message(message: IncomingMessage) -> None:
    async with message.process():
        body = message.body.decode()
        try:
            task_id = int(body)
        except ValueError:
            logger.error("Invalid task id received", task_id=body)
            return

        logger.info("Received task", task_id=task_id)

        if AsyncSessionLocal is None:
            logger.error("Session factory not initialized")
            return

        async with AsyncSessionLocal() as session:
            task = await session.get(TaskModel, task_id)
            if not task:
                logger.error("Task not found in DB", task_id=task_id)
                return

            if task.status in (Status.CANCELLED, Status.COMPLETED, Status.FAILED):
                logger.info(
                    "Skipping task with final status",
                    task_id=task_id,
                    status=task.status.value,
                )
                return

            try:
                # Переводим в IN_PROGRESS
                task.status = Status.IN_PROGRESS
                task.started_at = datetime.now(timezone.utc)
                await session.commit()

                # Бизнес-логика (например, sleep 2 сек)
                await asyncio.sleep(2)

                # Завершаем успешно
                task.finished_at = datetime.now(timezone.utc)
                task.result = "Processed successfully"
                task.status = Status.COMPLETED
                await session.commit()

                logger.info("Task processed", task_id=task_id)

            except Exception as exc:
                await session.rollback()
                task.error = str(exc)
                task.status = Status.FAILED
                await session.commit()
                logger.error(
                    "Task processing failed",
                    task_id=task_id,
                    error=task.error,
                )


async def main() -> None:
    # 1) Создаём движок и таблицы (если их ещё нет)
    engine = create_async_engine(
        settings.DATABASE_URL,
        future=True,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2) Фабрика сессий
    global AsyncSessionLocal
    AsyncSessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    # 3) Подключаемся к RabbitMQ
    connection = await connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()

    # 4) Объявляем exchange и очередь
    exchange = await channel.declare_exchange(
        name=settings.TASKS_EXCHANGE,
        type=ExchangeType.DIRECT,
        durable=True,
    )
    queue = await channel.declare_queue(
        name=settings.TASKS_QUEUE,
        durable=True,
    )
    await queue.bind(
        exchange=exchange,
        routing_key=settings.TASKS_ROUTING_KEY,
    )

    # 5) Стартуем потребление
    await queue.consume(handle_message)  # type: ignore[arg-type]
    logger.info("Worker started, awaiting messages")

    # 6) Ждём сигнала остановки
    try:
        await asyncio.Future()
    finally:
        await connection.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")

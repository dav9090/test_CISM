import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode
from app.core.config import settings
from typing import Optional


class TaskProcessor:
    _instance: Optional["TaskProcessor"] = None

    def __init__(self):
        # Флаг, чтобы инициализация сработала только один раз
        self._initialized = False
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None

    async def initialize(self) -> None:
        """Асинхронная инициализация подключения к RabbitMQ."""
        if self._initialized:
            return

        # Подключаемся к RabbitMQ (robust—с автоматическим восстановлением)
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        # Объявляем direct-exchange
        self.exchange = await self.channel.declare_exchange(
            name=settings.TASKS_EXCHANGE, type=ExchangeType.DIRECT, durable=True
        )
        # Объявляем очередь и привязываем её к exchange
        self.queue = await self.channel.declare_queue(
            name=settings.TASKS_QUEUE, durable=True
        )
        await self.queue.bind(
            exchange=self.exchange, routing_key=settings.TASKS_ROUTING_KEY
        )

        self._initialized = True

    async def enqueue(self, task_id: str) -> None:
        """Публикация новой задачи в очередь."""
        await self.initialize()
        msg = Message(
            body=task_id.encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
        )
        await self.exchange.publish(
            message=msg,
            routing_key=settings.TASKS_ROUTING_KEY,
        )

    async def close(self) -> None:
        """Закрытие соединения при завершении работы приложения."""
        if self.connection:
            await self.connection.close()
            self._initialized = False


def get_task_processor() -> TaskProcessor:
    """Синглтон-провайдер для TaskProcessor."""
    if TaskProcessor._instance is None:
        TaskProcessor._instance = TaskProcessor()
    return TaskProcessor._instance

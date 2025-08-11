import os

from pydantic import BaseModel


class Settings(BaseModel):
    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    # RabbitMQ
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_URL: str
    TASKS_EXCHANGE: str = "tasks"
    TASKS_QUEUE: str = "tasks_queue"
    TASKS_ROUTING_KEY: str = "task_key"
    SECRET_KEY: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаем настройки из переменных окружения
settings = Settings(
    POSTGRES_USER=os.getenv("POSTGRES_USER", "postgres"),
    POSTGRES_PASSWORD=os.getenv("POSTGRES_PASSWORD", "password"),
    POSTGRES_DB=os.getenv("POSTGRES_DB", "task_service"),
    DATABASE_URL=os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:password@localhost:5432/task_service",
    ),
    RABBITMQ_USER=os.getenv("RABBITMQ_USER", "user"),
    RABBITMQ_PASSWORD=os.getenv("RABBITMQ_PASSWORD", "password"),
    RABBITMQ_HOST=os.getenv("RABBITMQ_HOST", "localhost"),
    RABBITMQ_PORT=int(os.getenv("RABBITMQ_PORT", "5672")),
    RABBITMQ_URL=os.getenv("RABBITMQ_URL", "amqp://user:password@localhost:5672/"),
    SECRET_KEY=os.getenv("SECRET_KEY", "your-secret-key-here"),
)

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings

# 1) Создаём асинхронный движок
engine = create_async_engine(
    settings.DATABASE_URL,
    future=True,
    echo=False,
)

# 2) Фабрика сессий
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# 3) Депенденси для FastAPI
async def get_db():
    """
    Зависимость FastAPI, которая выдаёт асинхронную сессию и
    автоматически её закрывает после выхода из контекста.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Всё автоматом закрывается по выходу из async with
            pass

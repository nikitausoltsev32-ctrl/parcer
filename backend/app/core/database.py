import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

_ssl_ctx = ssl.create_default_context()
if not settings.database_ssl_verify:
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = ssl.CERT_NONE

_db_url = settings.database_url.split("?")[0]

engine = create_async_engine(
    _db_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": _ssl_ctx, "statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

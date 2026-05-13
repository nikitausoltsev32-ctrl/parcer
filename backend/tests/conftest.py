import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.database import Base, get_db

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def disable_external_email(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.transactional_smtp_host", "")


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.core.rate_limit import limiter

    try:
        limiter._storage.reset()
    except Exception:
        pass


@pytest.fixture
async def test_engine():
    engine = create_async_engine(TEST_DB, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    Session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest.fixture
async def client(db_session):
    from app.main import app

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

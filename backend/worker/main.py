from arq.connections import RedisSettings

from app.core.config import settings


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    functions = []
    cron_jobs = []

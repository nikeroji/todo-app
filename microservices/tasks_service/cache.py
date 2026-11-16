import json
import os

from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry


CACHE_KEY = "tasks:list:v1"
CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
    retry=Retry(NoBackoff(), 0),
)


def get_cached_tasks() -> list[dict] | None:
    try:
        cached = redis_client.get(CACHE_KEY)

        if cached is None:
            return None

        tasks = json.loads(cached)

        if not isinstance(tasks, list):
            raise ValueError("В кэше ожидается список задач")

        return tasks

    except (RedisError, ValueError) as error:
        print(f"[cache] Ошибка чтения: {error}", flush=True)
        return None


def cache_tasks(tasks: list[dict]) -> None:
    try:
        redis_client.set(
            CACHE_KEY,
            json.dumps(tasks, ensure_ascii=False),
            ex=CACHE_TTL,
        )

    except RedisError as error:
        print(f"[cache] Ошибка записи: {error}", flush=True)


def invalidate_tasks_cache() -> None:
    try:
        redis_client.delete(CACHE_KEY)
        print("[cache] Кэш списка задач сброшен", flush=True)

    except RedisError as error:
        print(f"[cache] Ошибка сброса: {error}", flush=True)

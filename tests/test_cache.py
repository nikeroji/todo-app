import json
from unittest.mock import Mock

import pytest
from redis.exceptions import ConnectionError

from microservices.tasks_service import cache


@pytest.fixture
def redis_mock(monkeypatch):
    client = Mock()
    monkeypatch.setattr(cache, "redis_client", client)
    return client


@pytest.mark.parametrize(
    "tasks",
    [
        [],
        [{"id": 1, "title": "Тестовая задача"}],
    ],
)
def test_cached_list_is_returned(redis_mock, tasks):
    redis_mock.get.return_value = json.dumps(
        tasks,
        ensure_ascii=False,
    )

    assert cache.get_cached_tasks() == tasks


@pytest.mark.parametrize(
    "stored_value",
    [
        None,
        "broken JSON",
        '{"unexpected": true}',
    ],
)
def test_missing_or_invalid_cache_is_miss(redis_mock, stored_value):
    redis_mock.get.return_value = stored_value

    assert cache.get_cached_tasks() is None


def test_unavailable_redis_is_miss(redis_mock):
    redis_mock.get.side_effect = ConnectionError("Redis недоступен")

    assert cache.get_cached_tasks() is None


def test_cache_write_preserves_data_and_ttl(redis_mock, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_TTL", 60)

    tasks = [
        {
            "id": 1,
            "title": "Проверить кэширование",
            "due_date": "2026-11-20",
        }
    ]

    cache.cache_tasks(tasks)

    redis_mock.set.assert_called_once()

    key, value = redis_mock.set.call_args.args
    options = redis_mock.set.call_args.kwargs

    assert key == "tasks:list:v1"
    assert json.loads(value) == tasks
    assert options["ex"] == 60


def test_unavailable_redis_does_not_break_cache_write(redis_mock):
    redis_mock.set.side_effect = ConnectionError("Redis недоступен")

    cache.cache_tasks([{"id": 1, "title": "Тестовая задача"}])

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pika


def publish_task_created(task_id: int, title: str) -> None:
    event = {
        "event_id": str(uuid4()),
        "event": "task_created",
        "task_id": task_id,
        "title": title,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }

    credentials = pika.PlainCredentials(
        username=os.environ["RABBITMQ_USER"],
        password=os.environ["RABBITMQ_PASSWORD"],
    )

    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=credentials,
        heartbeat=60,
        socket_timeout=5,
        stack_timeout=15,
        blocked_connection_timeout=5,
        connection_attempts=3,
        retry_delay=1,
    )

    queue_name = os.getenv("RABBITMQ_QUEUE", "notifications")
    connection = pika.BlockingConnection(parameters)

    try:
        channel = connection.channel()

        channel.queue_declare(
            queue=queue_name,
            durable=True,
        )

        channel.confirm_delivery()

        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=json.dumps(event, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                content_encoding="utf-8",
                delivery_mode=2,
                message_id=event["event_id"],
                type=event["event"],
            ),
            mandatory=True,
        )

        print(
            f"[publisher] Событие {event['event_id']} "
            f"для задачи #{task_id} принято RabbitMQ",
            flush=True,
        )

    finally:
        if connection.is_open:
            connection.close()

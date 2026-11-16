import json
import os
import time

import pika


def process_notification(channel, method, properties, body):
    try:
        event = json.loads(body.decode("utf-8"))

        if not isinstance(event, dict):
            raise ValueError("Сообщение должно быть JSON-объектом")

        if event.get("event") != "task_created":
            raise ValueError("Неизвестный тип события")

        task_id = event["task_id"]
        title = event["title"]
        event_id = event["event_id"]

    except (ValueError, KeyError, UnicodeDecodeError) as error:
        print(
            f"[notification] Некорректное сообщение: {error}",
            flush=True,
        )
        channel.basic_reject(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )
        return

    print(
        f"[notification] Получено событие {event_id}: "
        f"задача #{task_id} — {title}",
        flush=True,
    )

    # Имитируем операцию отправки уведомления.
    time.sleep(2)

    print(
        f"[notification] Имитация отправки завершена: "
        f"задача #{task_id}, событие {event_id}",
        flush=True,
    )

    channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
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
        connection_attempts=5,
        retry_delay=3,
    )

    queue_name = os.getenv("RABBITMQ_QUEUE", "notifications")
    connection = pika.BlockingConnection(parameters)

    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_qos(prefetch_count=1)

        channel.basic_consume(
            queue=queue_name,
            on_message_callback=process_notification,
            auto_ack=False,
        )

        print(
            f"[notification] Ожидание сообщений в очереди {queue_name}",
            flush=True,
        )

        channel.start_consuming()

    except KeyboardInterrupt:
        print("[notification] Остановка сервиса", flush=True)

    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()

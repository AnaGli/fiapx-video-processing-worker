import json

import pika

from app.core.config import settings


class RabbitMQConnection:
    def __init__(self):
        self.credentials = pika.PlainCredentials(
            settings.RABBITMQ_USERNAME,
            settings.RABBITMQ_PASSWORD,
        )

        self.parameters = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=self.credentials,
        )

    def connect(self):
        return pika.BlockingConnection(self.parameters)


class RabbitMQConsumer:
    def __init__(self):
        self.connection = RabbitMQConnection()

    def consume(self, callback) -> None:
        connection = self.connection.connect()

        try:
            channel = connection.channel()

            channel.queue_declare(
                queue=settings.RABBITMQ_INPUT_QUEUE,
                durable=True,
                passive=True,
            )

            channel.basic_qos(prefetch_count=1)

            channel.basic_consume(
                queue=settings.RABBITMQ_INPUT_QUEUE,
                on_message_callback=callback,
                auto_ack=False,
            )

            channel.start_consuming()

        finally:
            connection.close()


class RabbitMQPublisher:
    def __init__(self):
        self.connection = RabbitMQConnection()

    def publish(
        self,
        message: dict,
        queue: str,
    ) -> None:

        connection = self.connection.connect()

        if connection is None:
            raise RuntimeError("RabbitMQ connection returned None")

        channel = connection.channel()

        if channel is None:
            raise RuntimeError("RabbitMQ channel returned None")

        try:
            channel.basic_publish(
                exchange="",
                routing_key=queue,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )

        finally:
            connection.close()

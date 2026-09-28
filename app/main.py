import json
import logging

from app.core.config import settings
from app.messaging.rabbitmq import RabbitMQConsumer
from app.services.processing_service import ProcessingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def handle_message(
    channel,
    method,
    properties,
    body,
) -> None:
    logger.info("Received video processing request")

    try:
        service = ProcessingService()

        service.process(body)

        channel.basic_ack(delivery_tag=method.delivery_tag)

        logger.info("Video processing request completed")

    except Exception:
        logger.exception("Video processing request failed")

        channel.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )


def main():
    logger.info("Starting Video Processing Worker")

    consumer = RabbitMQConsumer()

    logger.info("Listening on queue: %s", settings.RABBITMQ_INPUT_QUEUE)

    consumer.consume(
        callback=handle_message,
    )


if __name__ == "__main__":
    main()

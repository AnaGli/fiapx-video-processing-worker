import json
from unittest.mock import Mock, patch

import pika
import pytest

from app.messaging.rabbitmq import (
    RabbitMQConnection,
    RabbitMQConsumer,
    RabbitMQPublisher,
)


@patch("app.messaging.rabbitmq.pika.BlockingConnection")
def test_connection_connect(mock_blocking_connection):
    connection = Mock()
    mock_blocking_connection.return_value = connection

    rabbitmq = RabbitMQConnection()

    result = rabbitmq.connect()

    assert result == connection
    mock_blocking_connection.assert_called_once_with(rabbitmq.parameters)


@patch("app.messaging.rabbitmq.RabbitMQConnection")
def test_consumer(mock_connection_class):
    connection = Mock()
    channel = Mock()

    connection.channel.return_value = channel
    mock_connection_class.return_value.connect.return_value = connection

    callback = Mock()

    consumer = RabbitMQConsumer()
    consumer.consume(callback)

    channel.queue_declare.assert_called_once()
    channel.basic_qos.assert_called_once_with(prefetch_count=1)
    channel.basic_consume.assert_called_once()
    channel.start_consuming.assert_called_once()
    connection.close.assert_called_once()


@patch("app.messaging.rabbitmq.RabbitMQConnection")
def test_publisher(mock_connection_class):
    connection = Mock()
    channel = Mock()

    connection.channel.return_value = channel
    mock_connection_class.return_value.connect.return_value = connection

    publisher = RabbitMQPublisher()

    message = {
        "video_id": "123",
        "status": "COMPLETED",
    }

    publisher.publish(
        message=message,
        queue="video-processing-completed",
    )

    channel.basic_publish.assert_called_once()

    call_kwargs = channel.basic_publish.call_args.kwargs

    assert call_kwargs["exchange"] == ""
    assert call_kwargs["routing_key"] == "video-processing-completed"
    assert json.loads(call_kwargs["body"]) == message
    assert isinstance(call_kwargs["properties"], pika.BasicProperties)
    assert call_kwargs["properties"].delivery_mode == 2
    assert call_kwargs["properties"].content_type == "application/json"

    connection.close.assert_called_once()


@patch("app.messaging.rabbitmq.RabbitMQConnection")
def test_publisher_raises_when_connection_is_none(mock_connection_class):
    mock_connection_class.return_value.connect.return_value = None

    publisher = RabbitMQPublisher()

    with pytest.raises(
        RuntimeError,
        match="RabbitMQ connection returned None",
    ):
        publisher.publish(
            message={"test": "value"},
            queue="test-queue",
        )


@patch("app.messaging.rabbitmq.RabbitMQConnection")
def test_publisher_raises_when_channel_is_none(mock_connection_class):
    connection = Mock()
    connection.channel.return_value = None

    mock_connection_class.return_value.connect.return_value = connection

    publisher = RabbitMQPublisher()

    with pytest.raises(
        RuntimeError,
        match="RabbitMQ channel returned None",
    ):
        publisher.publish(
            message={"test": "value"},
            queue="test-queue",
        )

    connection.close.assert_not_called()

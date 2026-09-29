import json
from unittest.mock import Mock, patch
from uuid import uuid4

from app.models.processing_job import ProcessingStatus
from app.services.processing_service import ProcessingService


@patch("app.services.processing_service.RabbitMQPublisher")
@patch("app.services.processing_service.StorageService")
@patch("app.services.processing_service.VideoProcessor")
@patch("app.services.processing_service.ProcessingJobRepository")
@patch("app.services.processing_service.SessionLocal")
def test_process_success(
    mock_session_local,
    mock_repository_class,
    mock_video_processor_class,
    mock_storage_class,
    mock_publisher_class,
    tmp_path,
):
    video_id = uuid4()
    user_id = uuid4()

    event = {
        "event_type": "VideoProcessingRequested",
        "video_id": str(video_id),
        "user_id": str(user_id),
        "input_object_key": f"videos/{video_id}/input/video.mp4",
    }

    db = Mock()
    mock_session_local.return_value = db

    repository = Mock()
    job = Mock()
    repository.create.return_value = job
    mock_repository_class.return_value = repository

    video_processor = Mock()
    video_processor.process.return_value = 10
    mock_video_processor_class.return_value = video_processor

    storage = Mock()
    mock_storage_class.return_value = storage

    publisher = Mock()
    mock_publisher_class.return_value = publisher

    service = ProcessingService()

    service.process(json.dumps(event).encode())

    repository.create.assert_called_once_with(
        video_id=video_id,
        user_id=user_id,
        input_object_key=event["input_object_key"],
    )

    repository.update_status.assert_any_call(
        job=job,
        status=ProcessingStatus.PROCESSING,
    )

    storage.download.assert_called_once()

    video_processor.process.assert_called_once()

    storage.upload.assert_called_once_with(
        object_key=f"videos/{video_id}/output/frames.zip",
        source=video_processor.process.call_args.kwargs["output_path"],
    )

    repository.update_status.assert_any_call(
        job=job,
        status=ProcessingStatus.COMPLETED,
        output_object_key=f"videos/{video_id}/output/frames.zip",
        frame_count=10,
    )

    publisher.publish.assert_called_once()

    db.close.assert_called_once()

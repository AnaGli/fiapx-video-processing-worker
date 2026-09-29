from unittest.mock import Mock
from uuid import uuid4

from app.models.processing_job import ProcessingJob, ProcessingStatus
from app.repositories.processing_job_repository import ProcessingJobRepository


def test_create():
    db = Mock()
    repository = ProcessingJobRepository(db)

    video_id = uuid4()
    user_id = uuid4()

    job = repository.create(
        video_id=video_id,
        user_id=user_id,
        input_object_key="videos/123/input/video.mp4",
    )

    assert isinstance(job, ProcessingJob)
    assert job.video_id == video_id
    assert job.user_id == user_id
    assert job.input_object_key == "videos/123/input/video.mp4"
    assert job.status == ProcessingStatus.QUEUED

    db.add.assert_called_once_with(job)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(job)


def test_update_status():
    db = Mock()
    repository = ProcessingJobRepository(db)

    job = ProcessingJob(
        video_id=uuid4(),
        user_id=uuid4(),
        input_object_key="videos/123/input/video.mp4",
        status=ProcessingStatus.QUEUED,
    )

    result = repository.update_status(
        job=job,
        status=ProcessingStatus.COMPLETED,
        output_object_key="videos/123/output/frames.zip",
        frame_count=150,
    )

    assert result == job
    assert job.status == ProcessingStatus.COMPLETED
    assert job.output_object_key == "videos/123/output/frames.zip"
    assert job.frame_count == 150

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(job)


def test_update_status_with_error():
    db = Mock()
    repository = ProcessingJobRepository(db)

    job = ProcessingJob(
        video_id=uuid4(),
        user_id=uuid4(),
        input_object_key="videos/123/input/video.mp4",
        status=ProcessingStatus.PROCESSING,
    )

    result = repository.update_status(
        job=job,
        status=ProcessingStatus.FAILED,
        error_message="FFmpeg failed",
    )

    assert result == job
    assert job.status == ProcessingStatus.FAILED
    assert job.error_message == "FFmpeg failed"

    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(job)


def test_find_by_video_id():
    db = Mock()
    repository = ProcessingJobRepository(db)

    video_id = uuid4()
    job = Mock()

    query = db.query.return_value
    filtered_query = query.filter.return_value
    filtered_query.first.return_value = job

    result = repository.find_by_video_id(video_id)

    assert result == job

    db.query.assert_called_once_with(ProcessingJob)
    query.filter.assert_called_once()
    filtered_query.first.assert_called_once()

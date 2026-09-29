import json
import logging
import tempfile
from pathlib import Path
from uuid import UUID

from app.core.config import settings
from app.dependencies.database import SessionLocal
from app.messaging.events import (
    VideoProcessingCompleted,
    VideoProcessingFailed,
    VideoProcessingRequested,
)
from app.messaging.rabbitmq import RabbitMQPublisher
from app.models.processing_job import ProcessingStatus
from app.repositories.processing_job_repository import ProcessingJobRepository
from app.services.storage_service import StorageService
from app.services.video_processor import VideoProcessor


logger = logging.getLogger(__name__)


class ProcessingService:
    def __init__(self):
        self.video_processor = VideoProcessor()
        self.storage_service = StorageService()
        self.publisher = RabbitMQPublisher()

    def process(self, body: bytes) -> None:
        event = VideoProcessingRequested.model_validate(
            json.loads(body)
        )

        logger.info(
            "Processing video %s",
            event.video_id,
        )

        db = SessionLocal()

        try:
            repository = ProcessingJobRepository(db)

            # Create processing job
            job = repository.create(
                video_id=event.video_id,
                user_id=event.user_id,
                input_object_key=event.input_object_key,
            )

            repository.update_status(
                job=job,
                status=ProcessingStatus.PROCESSING,
            )

            # Temporary workspace for this processing
            with tempfile.TemporaryDirectory(
                prefix=f"video-{event.video_id}-"
            ) as temp_dir:

                temp_directory = Path(temp_dir)

                input_path = (
                    temp_directory
                    / "input"
                    / Path(event.input_object_key).name
                )

                output_path = (
                    temp_directory
                    / "output"
                    / "frames.zip"
                )

                # Download original video from S3
                logger.info(
                    "Downloading input video %s",
                    event.input_object_key,
                )

                self.storage_service.download(
                    object_key=event.input_object_key,
                    destination=input_path,
                )

                # Process video and generate ZIP
                logger.info(
                    "Starting video processing for %s",
                    event.video_id,
                )

                frame_count = self.video_processor.process(
                    input_path=input_path,
                    output_path=output_path,
                )

                # Upload generated ZIP to S3
                output_object_key = (
                    f"videos/{event.video_id}/output/frames.zip"
                )

                logger.info(
                    "Uploading processed video output %s",
                    output_object_key,
                )

                self.storage_service.upload(
                    object_key=output_object_key,
                    source=output_path,
                )

            # Update processing job
            repository.update_status(
                job=job,
                status=ProcessingStatus.COMPLETED,
                output_object_key=output_object_key,
                frame_count=frame_count,
            )

            # Publish completion event
            completed_event = VideoProcessingCompleted(
                video_id=event.video_id,
                user_id=event.user_id,
                output_object_key=output_object_key,
                frame_count=frame_count,
            )

            self.publisher.publish(
                message=completed_event.model_dump(mode="json"),
                queue=settings.RABBITMQ_COMPLETED_QUEUE,
            )

            logger.info(
                "Video %s processed successfully: %s frames",
                event.video_id,
                frame_count,
            )

        except Exception as exc:
            logger.exception(
                "Error processing video %s",
                event.video_id,
            )

            self._handle_failure(
                db=db,
                video_id=event.video_id,
                user_id=event.user_id,
                error_message=str(exc),
            )

        finally:
            db.close()

    def _handle_failure(
        self,
        db,
        video_id: UUID,
        user_id: UUID,
        error_message: str,
    ) -> None:
        repository = ProcessingJobRepository(db)

        job = repository.find_by_video_id(video_id)

        if job is not None:
            repository.update_status(
                job=job,
                status=ProcessingStatus.FAILED,
                error_message=error_message,
            )

        # Publish failure event
        failed_event = VideoProcessingFailed(
            video_id=video_id,
            user_id=user_id,
            error_message=error_message,
        )

        self.publisher.publish(
            message=failed_event.model_dump(mode="json"),
            queue=settings.RABBITMQ_FAILED_QUEUE,
        )

        logger.error(
            "Video %s marked as FAILED: %s",
            video_id,
            error_message,
        )
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.processing_job import (
    ProcessingJob,
    ProcessingStatus,
)


class ProcessingJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        video_id: UUID,
        user_id: UUID,
        input_object_key: str,
    ) -> ProcessingJob:
        job = ProcessingJob(
            video_id=video_id,
            user_id=user_id,
            input_object_key=input_object_key,
            status=ProcessingStatus.QUEUED,
        )

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return job

    def update_status(
        self,
        job: ProcessingJob,
        status: ProcessingStatus,
        output_object_key: str | None = None,
        frame_count: int | None = None,
        error_message: str | None = None,
    ) -> ProcessingJob:
        job.status = status

        if output_object_key is not None:
            job.output_object_key = output_object_key

        if frame_count is not None:
            job.frame_count = frame_count

        if error_message is not None:
            job.error_message = error_message

        self.db.commit()
        self.db.refresh(job)

        return job

    def find_by_video_id(
        self,
        video_id: UUID,
    ) -> ProcessingJob | None:
        return (
            self.db.query(ProcessingJob)
            .filter(
                ProcessingJob.video_id == video_id
            )
            .first()
        )
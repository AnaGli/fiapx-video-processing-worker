from uuid import UUID

from pydantic import BaseModel


class VideoProcessingRequested(BaseModel):
    event_type: str = "VideoProcessingRequested"
    video_id: UUID
    user_id: UUID
    input_object_key: str


class VideoProcessingCompleted(BaseModel):
    event_type: str = "VideoProcessingCompleted"
    video_id: UUID
    user_id: UUID
    output_object_key: str
    frame_count: int


class VideoProcessingFailed(BaseModel):
    event_type: str = "VideoProcessingFailed"
    video_id: UUID
    user_id: UUID
    error_message: str
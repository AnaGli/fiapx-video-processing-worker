# FIAP X - Video Processing Worker

Worker responsible for asynchronous video processing.

## Responsibilities

- Consume `VideoProcessingRequested` from RabbitMQ.
- Process videos using FFmpeg.
- Extract video frames.
- Generate a `.zip` containing the frames.
- Persist processing information in its own PostgreSQL database.
- Publish `VideoProcessingCompleted`.
- Publish `VideoProcessingFailed` when processing fails.

## Architecture

```text
Video Management API
        |
        | VideoProcessingRequested
        v
     RabbitMQ
        |
        v
Video Processing Worker
        |
        +---- PostgreSQL Worker
        |
        +---- FFmpeg
        |
        +---- Shared storage
        |
        +---- RabbitMQ
                 |
                 +---- VideoProcessingCompleted
                 |
                 +---- VideoProcessingFailed
# fiapx-video-processing-worker

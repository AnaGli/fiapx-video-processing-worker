from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Video Processing Worker"
    APP_VERSION: str = "1.0.0"

    DATABASE_URL: str

    RABBITMQ_HOST: str = "host.docker.internal"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USERNAME: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    RABBITMQ_INPUT_QUEUE: str = "video-processing"
    RABBITMQ_COMPLETED_QUEUE: str = "video-processing-completed"
    RABBITMQ_FAILED_QUEUE: str = "video-processing-failed"

    S3_ENDPOINT_URL: str = "http://host.docker.internal:4566"
    S3_ACCESS_KEY_ID: str = "test"
    S3_SECRET_ACCESS_KEY: str = "test"
    S3_REGION: str = "us-east-1"
    S3_BUCKET: str = "videos"

    STORAGE_PATH: str = "/tmp/video-processing"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

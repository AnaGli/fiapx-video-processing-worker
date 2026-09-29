import boto3

from pathlib import Path


from app.core.config import settings


class StorageService:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        )

    def download(
        self,
        object_key: str,
        destination: Path,
    ) -> Path:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.client.download_file(
            settings.S3_BUCKET,
            object_key,
            str(destination),
        )

        return destination

    def upload(
        self,
        object_key: str,
        source: Path,
        content_type: str = "application/zip",
    ) -> str:
        self.client.upload_file(
            str(source),
            settings.S3_BUCKET,
            object_key,
            ExtraArgs={
                "ContentType": content_type,
            },
        )

        return object_key

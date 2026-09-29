from pathlib import Path
from unittest.mock import Mock, patch

from app.services.storage_service import StorageService


@patch("app.services.storage_service.boto3.client")
def test_download(mock_boto_client, tmp_path):
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    service = StorageService()

    destination = tmp_path / "input" / "video.mp4"

    result = service.download(
        object_key=Path("videos/123/input/video.mp4"),
        destination=destination,
    )

    assert result == destination
    assert destination.parent.exists()

    mock_client.download_file.assert_called_once()


@patch("app.services.storage_service.boto3.client")
def test_upload(mock_boto_client, tmp_path):
    mock_client = Mock()
    mock_boto_client.return_value = mock_client

    service = StorageService()

    source = tmp_path / "frames.zip"
    source.write_bytes(b"fake zip")

    result = service.upload(
        object_key="videos/123/output/frames.zip",
        source=source,
    )

    assert result == "videos/123/output/frames.zip"

    mock_client.upload_file.assert_called_once()

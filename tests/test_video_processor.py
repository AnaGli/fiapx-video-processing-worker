from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.services.video_processor import VideoProcessor


def test_process_fails_when_input_video_does_not_exist(tmp_path):
    processor = VideoProcessor()

    input_path = tmp_path / "missing.mp4"
    output_path = tmp_path / "output" / "frames.zip"

    with pytest.raises(
        FileNotFoundError,
        match="Input video not found",
    ):
        processor.process(
            input_path=input_path,
            output_path=output_path,
        )


@patch("app.services.video_processor.subprocess.run")
def test_process_fails_when_ffmpeg_returns_error(
    mock_run,
    tmp_path,
):
    processor = VideoProcessor()

    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "output" / "frames.zip"

    input_path.write_bytes(b"fake video")

    mock_run.return_value = Mock(
        returncode=1,
        stderr="Invalid data found when processing input",
    )

    with pytest.raises(
        RuntimeError,
        match="FFmpeg failed",
    ):
        processor.process(
            input_path=input_path,
            output_path=output_path,
        )

    mock_run.assert_called_once()


@patch("app.services.video_processor.subprocess.run")
def test_process_fails_when_ffmpeg_generates_no_frames(
    mock_run,
    tmp_path,
):
    processor = VideoProcessor()

    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "output" / "frames.zip"

    input_path.write_bytes(b"fake video")

    mock_run.return_value = Mock(
        returncode=0,
        stderr="",
    )

    with pytest.raises(
        RuntimeError,
        match="no frames were generated",
    ):
        processor.process(
            input_path=input_path,
            output_path=output_path,
        )

    mock_run.assert_called_once()


@patch("app.services.video_processor.subprocess.run")
def test_process_creates_zip_with_frames(
    mock_run,
    tmp_path,
):
    processor = VideoProcessor()

    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "output" / "frames.zip"

    input_path.write_bytes(b"fake video")

    def fake_ffmpeg(*args, **kwargs):
        command = args[0]

        frame_pattern = Path(command[-1])
        frames_directory = frame_pattern.parent

        frames_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        (frames_directory / "frame_000001.jpg").write_bytes(b"frame 1")
        (frames_directory / "frame_000002.jpg").write_bytes(b"frame 2")

        return Mock(
            returncode=0,
            stderr="",
        )

    mock_run.side_effect = fake_ffmpeg

    frame_count = processor.process(
        input_path=input_path,
        output_path=output_path,
    )

    assert frame_count == 2
    assert output_path.exists()

    import zipfile

    with zipfile.ZipFile(output_path) as archive:
        assert sorted(archive.namelist()) == [
            "frame_000001.jpg",
            "frame_000002.jpg",
        ]

    mock_run.assert_called_once()

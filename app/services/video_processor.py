import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


class VideoProcessor:
    def process(
        self,
        input_path: Path,
        output_path: Path,
    ) -> int:
        if not input_path.exists():
            raise FileNotFoundError(
                f"Input video not found: {input_path}"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.TemporaryDirectory(
            prefix="video-processing-"
        ) as temp_dir:
            frames_directory = (
                Path(temp_dir) / "frames"
            )

            frames_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            frame_pattern = (
                frames_directory / "frame_%06d.jpg"
            )

            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                str(frame_pattern),
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg failed: {result.stderr}"
                )

            frames = sorted(
                frames_directory.glob("frame_*.jpg")
            )

            if not frames:
                raise RuntimeError(
                    "FFmpeg completed but no frames were generated"
                )

            with zipfile.ZipFile(
                output_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                for frame in frames:
                    archive.write(
                        frame,
                        arcname=frame.name,
                    )

            return len(frames)
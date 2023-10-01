#!/usr/bin/env python3

import argparse
import subprocess
from pathlib import Path
import sys
import datetime
import dataclasses
import shutil
import tempfile


@dataclasses.dataclass
class Recording:
    path: Path
    timestamp: datetime.datetime


def render_group(recordings: list[Recording], output_dir: Path):
    output_name = recordings[0].timestamp.strftime("%Y%m%d_%H%M.mkv")
    output_path = (output_dir / output_name).resolve()

    input = "\n".join(f"file '{r.path.resolve()}'" for r in recordings)
    # Could not figure out how to get ffmpeg to take the list of files via stdin so this will do
    with tempfile.NamedTemporaryFile("w") as f:
        f.write(input)
        f.flush()
        subprocess.run(
            [
                "ffmpeg",
                "-f",
                "concat", # Lossless concatenation
                "-safe",
                "0",
                "-i",
                f.name,
                "-c",
                "copy", # Use existing video/audio codec
                "-y", # Overwrite files without asking
                str(output_path),
            ],
            check=True,
            input=input.encode(),
        )


def combine(record_dir: Path, output_dir: Path) -> None:
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found")

    if not record_dir.exists() or not record_dir.is_dir():
        sys.exit(f"Camera recording directory not found or invalid: {record_dir}")
    try:
        output_dir.mkdir(exist_ok=True)
    except FileExistsError:
        sys.exit(f"Not a directory: {output_dir}")

    mp4_paths = record_dir.rglob("??.mp4")

    # Parse timestamps
    recordings: list[Recording] = []
    for mp4_path in mp4_paths:
        year = int(mp4_path.parts[-3][0:4])
        month = int(mp4_path.parts[-3][4:6])
        day = int(mp4_path.parts[-3][6:8])
        hour = int(mp4_path.parts[-2])
        min = int(mp4_path.parts[-1][: -len(".mp4")])
        timestamp = datetime.datetime(year, month, day, hour, min)
        recordings.append(Recording(mp4_path, timestamp))
    recordings = sorted(recordings, key=lambda r: r.timestamp)

    # Group and render recordings
    if len(recordings) == 0:
        return
    grouped_recordings: list[Recording] = [recordings[0]]
    timedelta_threshold = datetime.timedelta(minutes=1, seconds=30)
    for recording in recordings[1:]:
        if (
            recording.timestamp - grouped_recordings[-1].timestamp
        ) < timedelta_threshold:
            # Part of same group
            grouped_recordings.append(recording)
        else:
            # Start of new group - render old one, start new group
            render_group(grouped_recordings, output_dir)
            grouped_recordings = [recording]
    render_group(grouped_recordings, output_dir)


def main():
    parser = argparse.ArgumentParser(
        "wyzechunk",
        description="Combine 1min video fragments recorded by Wyze V3 cameras into full videos",
    )
    parser.add_argument(
        "recordings_dir",
        help='Path to folder containing Wyze recordings (usually called "record")',
    )
    parser.add_argument("-o", "--output-dir", help="Path to output combined videos to")
    args = parser.parse_args()

    record_dir = Path(args.recordings_dir)
    if args.output_dir is None:
        output_dir = Path.cwd()
    else:
        output_dir = Path(args.output_dir)
    combine(record_dir, output_dir)


if __name__ == "__main__":
    main()
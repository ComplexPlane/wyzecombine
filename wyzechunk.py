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
    start_name, end_name = (
        t.strftime("%Y%m%d_%H%M")
        for t in [recordings[0].timestamp, recordings[-1].timestamp]
    )
    output_name = f"{start_name}_to_{end_name}.mkv"
    tmp_output_name = f"{start_name}_to_{end_name}.tmp.mkv"
    output_path = (output_dir / output_name).resolve()
    tmp_output_path = (output_dir / tmp_output_name).resolve()

    if output_path.exists():
        return

    # Could not figure out how to get ffmpeg to take the list of files via stdin so this will do
    input = "\n".join(f"file '{r.path.resolve()}'" for r in recordings)
    with tempfile.NamedTemporaryFile() as input_tmpfile:
        input_tmpfile.write(input.encode())
        input_tmpfile.flush()
        subprocess.run(
            [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                input_tmpfile.name,
                "-c",
                "copy",  # Use existing video/audio codec
                "-y",  # Overwrite files without asking
                str(tmp_output_path),
            ],
            check=True,
        )

    shutil.move(tmp_output_path, output_path)


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
    TIMEDELTA_THRESHOLD = datetime.timedelta(minutes=1, seconds=30)
    for recording in recordings[1:]:
        delta = recording.timestamp - grouped_recordings[-1].timestamp
        if delta < TIMEDELTA_THRESHOLD:
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

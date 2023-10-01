# wyzecombine

Combine 1min video fragments recorded by Wyze V3 cameras into full videos.

## Features

- One full video is produced for each continuous span of 1min chunks
- Will not rerender the same videos which have already been outputted

## Example

`./wyzecombine.py /Volumes/mycamera/record --output-dir ~/Downloads/wyzecam-combined/`
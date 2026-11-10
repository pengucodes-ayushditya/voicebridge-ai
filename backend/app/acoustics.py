"""Observable audio diagnostics; no emotion or employee-performance inference."""

import json
import re
import subprocess
from pathlib import Path


def measure(path: Path):
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=sample_rate,channels",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    info = json.loads(probe.stdout)
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "silencedetect=noise=-35dB:d=0.4,volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    text = result.stderr
    if not info.get("streams") or not info.get("format", {}).get("duration"):
        raise ValueError("No non-empty decodable audio stream")
    duration = float(info["format"]["duration"])
    spans = []
    start = None
    for match in re.finditer(r"silence_(start|end): ([0-9.]+)", text):
        if match[1] == "start":
            start = float(match[2])
        elif start is not None:
            spans.append(
                {
                    "start_ms": round(start * 1000),
                    "end_ms": round(float(match[2]) * 1000),
                }
            )
            start = None
    if start is not None:
        spans.append(
            {"start_ms": round(start * 1000), "end_ms": round(duration * 1000)}
        )
    volume = re.search(r"mean_volume: ([-0-9.inf]+) dB", text)
    value = float(volume[1]) if volume and volume[1] != "-inf" else None
    return {
        "duration_seconds": round(duration, 3),
        "sample_rate": info["streams"][0].get("sample_rate"),
        "channels": info["streams"][0].get("channels"),
        "mean_volume_dbfs": value,
        "silence_threshold_dbfs": -35,
        "minimum_silence_seconds": 0.4,
        "silence_spans": spans,
        "caveat": "Measured audio energy and low-energy spans only. Silence can reflect turn boundaries, recording conditions or pauses; it does not establish hesitation, confidence, emotion or causation.",
    }

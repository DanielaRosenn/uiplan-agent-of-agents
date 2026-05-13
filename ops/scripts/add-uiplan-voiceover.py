#!/usr/bin/env python3
"""Generate Edge TTS narration from the UiPlan SRT and attach it to the video."""

from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

import edge_tts

try:
    from moviepy import AudioFileClip, CompositeAudioClip, VideoFileClip
except ImportError:  # moviepy v1 fallback
    from moviepy.editor import AudioFileClip, CompositeAudioClip, VideoFileClip


DEFAULT_VOICE = "en-US-JennyNeural"
DEFAULT_RATE = -8


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"SRT is empty: {path}")

    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", raw)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if len(lines) < 3:
            continue
        index = int(lines[0])
        start_text, end_text = [part.strip() for part in lines[1].split("-->")]
        text = " ".join(lines[2:])
        cues.append(Cue(index=index, start=parse_time(start_text), end=parse_time(end_text), text=text))

    if not cues:
        raise ValueError(f"No cues found in SRT: {path}")
    return cues


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000
    )


def format_rate(rate: int) -> str:
    sign = "+" if rate >= 0 else ""
    return f"{sign}{rate}%"


async def generate_tts(text: str, voice: str, output: Path, rate: int) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=format_rate(rate))
    await communicate.save(str(output))


def initial_rate(cue: Cue, base_rate: int) -> int:
    duration = max(cue.end - cue.start, 1)
    words = len(re.findall(r"\w+", cue.text))
    required_words_per_second = words / duration
    # Keep narration in a clear explainer range. Only speed up slightly for
    # dense cues, and otherwise keep the requested slower baseline.
    rate = int(max(base_rate, min(12, ((required_words_per_second / 2.15) - 1) * 100)))
    return rate


async def generate_cue_audio(cues: list[Cue], voice: str, work_dir: Path, rate: int) -> list[Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for cue in cues:
        output = work_dir / f"cue-{cue.index:03d}.mp3"
        await generate_tts(cue.text, voice, output, initial_rate(cue, rate))
        outputs.append(output)
    return outputs


def with_duration(clip, duration: float):
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def with_start(clip, start: float):
    if hasattr(clip, "with_start"):
        return clip.with_start(start)
    return clip.set_start(start)


def build_video_with_voice(
    video_path: Path,
    cue_audio_paths: list[Path],
    cues: list[Cue],
    output_video: Path,
    output_voiceover: Path,
    volume: float,
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    video = VideoFileClip(str(video_path))
    audio_clips = []

    try:
        for cue, audio_path in zip(cues, cue_audio_paths, strict=True):
            clip = AudioFileClip(str(audio_path))
            if volume != 1:
                if hasattr(clip, "with_volume_scaled"):
                    clip = clip.with_volume_scaled(volume)
                else:
                    clip = clip.volumex(volume)
            audio_clips.append(with_start(clip, cue.start))

        composite = CompositeAudioClip(audio_clips)
        composite = with_duration(composite, video.duration)
        composite.write_audiofile(str(output_voiceover), fps=44100, bitrate="192k", logger=None)

        if hasattr(video, "with_audio"):
            final = video.with_audio(composite)
        else:
            final = video.set_audio(composite)

        final.write_videofile(
            str(output_video),
            codec="libx264",
            audio_codec="aac",
            audio_bitrate="192k",
            logger=None,
        )
    finally:
        video.close()
        for clip in audio_clips:
            try:
                clip.close()
            except Exception:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--srt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--voiceover", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--rate", default=DEFAULT_RATE, type=int)
    parser.add_argument("--volume", default=1.0, type=float)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    cues = parse_srt(args.srt)
    cue_audio_paths = await generate_cue_audio(cues, args.voice, args.work_dir, args.rate)
    build_video_with_voice(
        video_path=args.video,
        cue_audio_paths=cue_audio_paths,
        cues=cues,
        output_video=args.output,
        output_voiceover=args.voiceover,
        volume=args.volume,
    )
    print(f"voice: {args.voice}")
    print(f"base_rate: {format_rate(args.rate)}")
    print(f"voiceover: {args.voiceover}")
    print(f"video: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())

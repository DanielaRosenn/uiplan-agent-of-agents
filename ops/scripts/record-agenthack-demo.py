#!/usr/bin/env python3
"""
Build the AgentHack demo video from timeline subtitles + voiceover.

This script creates a 1280x720 narrated MP4 using:
- docs/submission/agenthack-demo.captions.srt (timing + captions)
- docs/submission/demo-script.md (scene narrative source)
- optional scene images under docs/submission/screenshots/

Output files:
- docs/submission/agenthack-demo.mp4
- docs/submission/agenthack-demo.voiceover.mp3
- docs/submission/agenthack-demo.captions.srt (reused)
"""

from __future__ import annotations

import argparse
import asyncio
import re
from dataclasses import dataclass
from pathlib import Path

import edge_tts
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    concatenate_videoclips,
)

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover - pillow optional in some environments
    Image = None
    ImageDraw = None
    ImageFont = None


WIDTH = 1280
HEIGHT = 720
VOICE = "en-US-JennyNeural"
FPS = 24


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return max(self.end - self.start, 0.1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output MP4 path (defaults to docs/submission/agenthack-demo.mp4).",
    )
    return parser.parse_args()


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8").strip()
    blocks = re.split(r"\n\s*\n", raw)
    cues: list[Cue] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) < 3:
            continue
        idx = int(lines[0])
        start_txt, end_txt = [part.strip() for part in lines[1].split("-->")]
        text = " ".join(lines[2:])
        cues.append(
            Cue(
                index=idx,
                start=parse_srt_time(start_txt),
                end=parse_srt_time(end_txt),
                text=text,
            )
        )
    if not cues:
        raise ValueError(f"No cues parsed from {path}")
    return cues


def parse_srt_time(value: str) -> float:
    hh, mm, ss_ms = value.split(":")
    ss, ms = ss_ms.split(",")
    return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000


def scene_image_for_cue(repo_root: Path, cue: Cue) -> Path | None:
    screenshot_dir = repo_root / "docs" / "submission" / "screenshots"
    if screenshot_dir.exists():
        candidate = screenshot_dir / f"screenshot-{cue.index:02d}.png"
        if candidate.exists():
            return candidate
    fallback_map = {
        1: repo_root / "docs" / "submission" / "thumbnail.png",
        6: repo_root / "docs" / "submission" / "architecture-diagram.png",
        9: repo_root / "docs" / "submission" / "thumbnail.png",
    }
    fallback = fallback_map.get(cue.index)
    if fallback and fallback.exists():
        return fallback
    return None


def make_placeholder_image(path: Path, title: str, subtitle: str) -> Path:
    if Image is None:
        raise RuntimeError("Pillow is required to generate placeholder frames.")
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(20, 32, 61))
    draw = ImageDraw.Draw(img)
    title_font = ImageFont.load_default()
    body_font = ImageFont.load_default()

    draw.rectangle([(24, 24), (WIDTH - 24, HEIGHT - 24)], outline=(250, 70, 22), width=3)
    draw.text((60, 80), "UiPlan: Agent-of-Agents", fill=(250, 250, 250), font=title_font)
    draw.text((60, 130), title, fill=(250, 70, 22), font=title_font)

    wrapped = wrap_text(subtitle, 92)
    y = 200
    for line in wrapped:
        draw.text((60, y), line, fill=(240, 240, 240), font=body_font)
        y += 20

    img.save(path)
    return path


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        cand = " ".join(current + [word]).strip()
        if len(cand) <= max_chars:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def build_visual_track(repo_root: Path, cues: list[Cue], temp_dir: Path) -> VideoClip:
    clips = []
    for cue in cues:
        img = scene_image_for_cue(repo_root, cue)
        if img is None:
            img = make_placeholder_image(
                temp_dir / f"scene-{cue.index:02d}.png",
                f"Scene {cue.index}",
                cue.text,
            )

        clip = ImageClip(str(img)).resized((WIDTH, HEIGHT)).with_duration(cue.duration)
        clips.append(clip)

    base = concatenate_videoclips(clips, method="compose")

    if Image is None:
        return base

    caption_overlays = []
    running_start = 0.0
    for cue in cues:
        overlay_path = make_caption_overlay(temp_dir / f"caption-{cue.index:02d}.png", cue.text)
        overlay = (
            ImageClip(str(overlay_path))
            .with_duration(cue.duration)
            .with_start(running_start)
            .with_position(("center", HEIGHT - 150))
        )
        caption_overlays.append(overlay)
        running_start += cue.duration

    return CompositeVideoClip([base, *caption_overlays], size=(WIDTH, HEIGHT))


def make_caption_overlay(path: Path, text: str) -> Path:
    assert Image is not None and ImageDraw is not None and ImageFont is not None
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (WIDTH - 80, 120), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(0, 0), (WIDTH - 80, 120)], radius=16, fill=(8, 17, 44, 210))
    font = ImageFont.load_default()
    y = 18
    for line in wrap_text(text, 92)[:4]:
        draw.text((24, y), line, fill=(255, 255, 255, 255), font=font)
        y += 22
    img.save(path)
    return path


def speaking_rate_for_cue(cue: Cue) -> int:
    words = len(re.findall(r"\w+", cue.text))
    target_wps = max(words / cue.duration, 1.5)
    # Tune around ~2.2 words/sec baseline for clear narration.
    computed = int(((target_wps / 2.2) - 1.0) * 100)
    return max(-15, min(computed, 22))


async def generate_voice_tracks(cues: list[Cue], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for cue in cues:
        rate = speaking_rate_for_cue(cue)
        out = out_dir / f"cue-{cue.index:02d}.mp3"
        communicator = edge_tts.Communicate(text=cue.text, voice=VOICE, rate=f"{rate:+d}%")
        await communicator.save(str(out))
        outputs.append(out)
    return outputs


def build_voiceover(cues: list[Cue], cue_paths: list[Path], out_mp3: Path) -> AudioFileClip:
    audio_clips = []
    running_start = 0.0
    for cue, cue_path in zip(cues, cue_paths, strict=True):
        clip = AudioFileClip(str(cue_path))
        if clip.duration > cue.duration + 0.1:
            clip = clip.subclipped(0, cue.duration)
        audio_clips.append(clip.with_start(running_start))
        running_start += cue.duration
    mixed = CompositeAudioClip(audio_clips).with_duration(sum(c.duration for c in cues))
    mixed.write_audiofile(str(out_mp3), fps=44100, bitrate="192k", logger=None)
    for clip in audio_clips:
        clip.close()
    return AudioFileClip(str(out_mp3))


async def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()

    submission_dir = repo_root / "docs" / "submission"
    srt_path = submission_dir / "agenthack-demo.captions.srt"
    out_video = args.output or (submission_dir / "agenthack-demo.mp4")
    out_audio = submission_dir / "agenthack-demo.voiceover.mp3"
    temp_dir = submission_dir / ".video-temp"
    cues_dir = temp_dir / "voice-cues"

    cues = parse_srt(srt_path)
    visual = build_visual_track(repo_root, cues, temp_dir)
    cue_audio_paths = await generate_voice_tracks(cues, cues_dir)
    voiceover = build_voiceover(cues, cue_audio_paths, out_audio)
    final = visual.with_audio(voiceover)

    out_video.parent.mkdir(parents=True, exist_ok=True)
    final.write_videofile(
        str(out_video),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        logger=None,
    )
    final.close()
    voiceover.close()
    visual.close()

    print(f"video: {out_video}")
    print(f"voiceover: {out_audio}")
    print(f"captions: {srt_path}")


if __name__ == "__main__":
    asyncio.run(main())

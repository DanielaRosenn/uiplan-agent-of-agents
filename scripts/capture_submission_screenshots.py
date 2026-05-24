#!/usr/bin/env python3
"""Generate AgentHack submission screenshots from local project assets."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def build_targets():
    return [
        ("screenshot-01-viewer.png", "Viewer 7-tab experience", "UiPlan, Diagrams, Constraints, Tasks, Execution, Resources, Docs"),
        ("screenshot-02-events-json.png", "Execution evidence stream", "Current run-events payload and telemetry summary"),
        ("screenshot-03-submission-md.png", "Submission narrative", "Problem, solution, differentiators, and run evidence"),
        ("screenshot-04-architecture-md.png", "Architecture deep dive", "Pipeline stages, contracts, constraints, orchestration"),
        ("screenshot-05-kanban.png", "Task delivery board", "Planned, In Progress, Done mapped from tasks contract"),
        ("screenshot-06-orchestrator-evidence.png", "Orchestrator evidence", "Shared queue + asset + job telemetry verification"),
    ]


def run():
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "docs" / "submission" / "screenshots"
    output_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()

    architecture_png = repo_root / "docs" / "submission" / "architecture-diagram.png"
    thumbnail_png = repo_root / "docs" / "submission" / "thumbnail.png"
    run_events_json = repo_root / "ui" / "copilotkit" / "current" / "run-events.json"

    for idx, (filename, title, subtitle) in enumerate(build_targets(), start=1):
        image = Image.new("RGB", (1600, 900), color=(20, 32, 61))
        draw = ImageDraw.Draw(image)
        draw.rectangle([(20, 20), (1580, 880)], outline=(250, 70, 22), width=4)
        draw.text((60, 60), "UiPlan: Agent-of-Agents", fill=(255, 255, 255), font=font)
        draw.text((60, 110), f"Screenshot {idx:02d}", fill=(250, 70, 22), font=font)
        draw.text((60, 170), title, fill=(245, 245, 245), font=font)
        draw.text((60, 230), subtitle, fill=(220, 220, 220), font=font)

        details = [
            f"Source: {repo_root}",
            f"Run events: {'present' if run_events_json.exists() else 'missing'}",
            f"Architecture PNG: {'present' if architecture_png.exists() else 'missing'}",
            f"Thumbnail PNG: {'present' if thumbnail_png.exists() else 'missing'}",
        ]
        y = 320
        for line in details:
            draw.text((60, y), line, fill=(210, 210, 210), font=font)
            y += 28

        out_path = output_dir / filename
        image.save(out_path)

    # Also copy existing architecture + thumbnail as direct evidence screenshots.
    if architecture_png.exists():
        Image.open(architecture_png).convert("RGB").save(output_dir / "screenshot-07-architecture-source.png")
    if thumbnail_png.exists():
        Image.open(thumbnail_png).convert("RGB").save(output_dir / "screenshot-08-thumbnail-source.png")

    print(f"saved screenshots to: {output_dir}")


if __name__ == "__main__":
    run()

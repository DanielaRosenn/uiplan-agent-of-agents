# AgentHack Submission Checklist (Execution Status)

## Completed

- [x] Baseline cleanup + submission commit created
- [x] Video generation script created: `ops/scripts/record-agenthack-demo.py`
- [x] Narrated demo generated:
  - `docs/submission/agenthack-demo.mp4`
  - `docs/submission/agenthack-demo.voiceover.mp3`
  - `docs/submission/agenthack-demo.captions.srt`
- [x] Video technical verification completed:
  - duration: `150.05s`
  - audio attached: `true`
  - voiceover duration: `150.05s`
- [x] `.gitignore` updated for orchestrator output exception:
  - `!agents/builder-orchestrator/out/enterpriseincidentagentbuilder-20260524163750/**`
- [x] License added: `LICENSE` (MIT)
- [x] Devpost content drafted: `docs/submission/DEVPOST.md`
- [x] Submission screenshots generated:
  - `docs/submission/screenshots/screenshot-01-viewer.png`
  - `docs/submission/screenshots/screenshot-02-events-json.png`
  - `docs/submission/screenshots/screenshot-03-submission-md.png`
  - `docs/submission/screenshots/screenshot-04-architecture-md.png`
  - `docs/submission/screenshots/screenshot-05-kanban.png`
  - `docs/submission/screenshots/screenshot-06-orchestrator-evidence.png`
  - `docs/submission/screenshots/screenshot-07-architecture-source.png`
  - `docs/submission/screenshots/screenshot-08-thumbnail-source.png`
- [x] README verification completed (all AgentHack links present)
- [x] Local reproduction test passed:
  - `enterpriseincidentagentbuilder-20260524173312 completed`
- [x] Viewer payload check completed:
  - `ui/copilotkit/viewer.html` contains all expected tab labels
  - `ui/copilotkit/current/run-events.json` is readable
- [x] Public repository created and pushed:
  - `https://github.com/DanielaRosenn/uiplan-agent-of-agents`
  - branch push: `dev -> main`

## Remaining External Step

- [ ] Upload video to YouTube/Vimeo and collect shareable URL
  - Deferred by user for now (local MP4 retained in repo)

## Ready-to-run Unblock Commands

If you need to republish from a new machine/account:

```bash
gh auth logout
gh auth login
gh repo create DanielaRosenn/uiplan-agent-of-agents --public --description "Agent-of-Agents: LangGraph orchestrator that turns a business brief into a full UiPath automation delivery package"
git remote add submission https://github.com/DanielaRosenn/uiplan-agent-of-agents.git
git push submission dev:main
```

Video upload:

1. Upload `docs/submission/agenthack-demo.mp4` to YouTube or Vimeo (unlisted/public).
2. Upload captions from `docs/submission/agenthack-demo.captions.srt`.
3. Paste the video URL into `docs/submission/DEVPOST.md`.

## Final URLs (to fill once unblocked)

- GitHub: `https://github.com/DanielaRosenn/uiplan-agent-of-agents`
- Video: `<youtube-or-vimeo-url>`
- Devpost page: `<devpost-project-url>`

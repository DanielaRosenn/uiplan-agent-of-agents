# Installation

Full setup for UiPath Claude Code. The [README.md](../README.md) Quickstart is the three-command version; this doc is everything else.

## Prerequisites

| Requirement | Why |
|---|---|
| Python 3.11+ | Runtime |
| Node.js 18+ | Required by `@uipath/cli` |
| UiPath Studio Desktop **26.2+** | Required for `uip rpa --use-studio` validation commands |
| AWS account with Bedrock access | LLM backend (Anthropic Claude via Bedrock) |
| Git with submodule support | Official UiPath skills ship as a submodule |

## 1. Clone and install

```bash
git clone <your-repo-url>
cd uipath-builder-agent
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -e ".[dev]"
git submodule update --init --recursive
```

## 2. UiPath CLI (required for validation)

```bash
npm install -g @uipath/cli
npm install -g @uipath/rpa-tool @uipath/common @uipath/solutionpackager-tool-core commander
```

Studio must be running for IPC-backed commands (`--use-studio`).

Authenticate against Automation Cloud:

```bash
uipath auth --cloud --tenant <YourTenant>
```

## 3. AWS Bedrock

```bash
aws sts get-caller-identity
```

If this fails, configure credentials (AWS SSO, `aws configure`, or environment variables). Optional overrides:

```bash
# PowerShell
$env:AWS_REGION = "us-east-1"
$env:UIPATH_CLAUDE_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"
```

## 4. Project environment

Copy `.env.example` to `.env` in the directory you will run `uipath-claude chat` from:

```bash
cp .env.example .env
```

Variables starting with `UIPATH_` in `.env` override the same names from the shell environment, so project settings win. Key variables documented in [USER_GUIDE.md](USER_GUIDE.md).

## 5. Cursor integration (optional)

The UiPath skills work directly in Cursor without the CLI runtime:

```powershell
# Windows
.\ops\scripts\setup-cursor.ps1
```

```bash
# macOS/Linux
./ops/scripts/setup-cursor.sh
```

This creates `.cursor/skills/` linking to the UiPath skills. Open the repo in Cursor; skills load automatically. Full guide: [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md).

## 6. Verify

```bash
uipath-claude chat
# type: /status
# type: /skills
# exit with: exit
```

You should see a tenant, tool profile, and a list of available skills with origins (`user`, `project`, `extensions`, `uipath-submodule`).

## Troubleshooting

- **`uipath CLI not found on PATH`** — install `@uipath/cli` globally with npm and reopen the shell.
- **`Studio not running` during validation** — start UiPath Studio Desktop; `--use-studio` commands require an IPC-reachable Studio instance.
- **Bedrock `AccessDeniedException`** — your role lacks `bedrock:InvokeModel`. Request access to `anthropic.claude-3-sonnet-20240229-v1:0` in the AWS Bedrock console for your region.
- **NuGet restore lock/permission errors** — run `/repair-restore` inside chat for deterministic recovery steps.

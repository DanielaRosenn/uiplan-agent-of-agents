# Zip email smart invoice routing (fixture intent)

Build an **Automation Cloud UiPath Solution** (not Flow-first) for Finance zip-email routing.

- **Dispatcher** (`ZipEmail.Dispatcher`): scheduled Graph/mail read every ~30 minutes, creates
  **Orchestrator** items on **`ZipEmailIntakeQueue`**.
- **Analyzer host** (`ZipEmail.AnalyzerRunner`): **XAML-first** Sequence or Flowchart process that
  dequeues intake work, snapshots audit payloads, invokes the **`ZipEmail.AnalyzerAgent`** Python
  LangGraph **per item** (`uv run uipath run agent`), then updates intake and
  **`ZipEmailHumanReviewQueue`** when needed. The agent is the **semantic engine only**.
- **Human review** (`ZipEmail.HumanReviewHandler`): **Long Running Workflow** for Action Center /
  human wait paths.
- **Queues**: `ZipEmailIntakeQueue`, `ZipEmailHumanReviewQueue` are the integration contract.

**SME gaps** (must not invent): full regional mailbox list, IL mailbox list, Zip mode, audit store,
review channel, trigger details — use `[SME REVIEW]` until confirmed.

**Verification**: test-first, `uipcli` restore/analyze/test/pack, smoke run, robot logs with
**correlation id** and expected phase **LogMessage** markers.

# Coded vs low-code agents

UiPath supports two agent shapes:

- **Coded** (Python). Frameworks: LangGraph, LlamaIndex, OpenAI Agents SDK. Full control, version-controllable, runs anywhere `uip agent run` works.
- **Low-code** (`agent.json`). Authored in Agent Builder UI; runtime is provided by UiPath. Best for structured tool-calling agents with declarative inputs/outputs.

## When to choose which

| Need | Choose |
|---|---|
| Custom Python deps, multi-step graphs, fine-grained control | Coded (LangGraph) |
| Document-heavy retrieval | Coded (LlamaIndex) |
| Drop-in OpenAI Agents semantics | Coded (OpenAI Agents) |
| Fastest path, no Python, business-user-editable | Low-code |

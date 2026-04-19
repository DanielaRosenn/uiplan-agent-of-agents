# LangGraph project layout

```
my-agent/
  pyproject.toml
  agent/
    __init__.py
    graph.py        # build_graph() returns a compiled LangGraph
    state.py        # TypedDict state
    nodes/
      classify.py
      respond.py
  evals/
    regression.json
```

`uip agent run` imports `agent.graph:build_graph` by convention.

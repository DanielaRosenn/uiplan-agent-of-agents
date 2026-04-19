# Minimal LangGraph example

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class State(TypedDict):
    question: str
    answer: str

def respond(state: State) -> State:
    return {**state, "answer": f"You asked: {state['question']}"}

def build_graph():
    g = StateGraph(State)
    g.add_node("respond", respond)
    g.set_entry_point("respond")
    g.add_edge("respond", END)
    return g.compile()
```

Run:

```bash
uip agent run --input '{"question":"hello"}'
```

# Adding tools to a LangGraph agent

Use `langchain_core.tools.tool` to declare callable tools, then bind to the model in a node.

```python
from langchain_core.tools import tool

@tool
def get_invoice(invoice_id: str) -> dict:
    """Fetch invoice details by id."""
    return {"id": invoice_id, "amount": 42.0}
```

For UiPath integrations, prefer Integration Service connectors via `uip platform is` and call them through a tool wrapper.

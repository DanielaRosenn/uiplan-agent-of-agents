# LlamaIndex RAG agent

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.agent import ReActAgent
from llama_index.core.tools import QueryEngineTool

def build_agent():
    docs = SimpleDirectoryReader('docs').load_data()
    index = VectorStoreIndex.from_documents(docs)
    qe = index.as_query_engine()
    tool = QueryEngineTool.from_defaults(qe, name='docs', description='Search internal docs.')
    return ReActAgent.from_tools([tool])
```

`uip agent run` will look for `agent:build_agent`.

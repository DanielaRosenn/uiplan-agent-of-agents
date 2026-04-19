# Persisting the LlamaIndex index

Avoid rebuilding on every run.

```python
from llama_index.core import StorageContext, load_index_from_storage

try:
    storage = StorageContext.from_defaults(persist_dir='./.idx')
    index = load_index_from_storage(storage)
except FileNotFoundError:
    index = VectorStoreIndex.from_documents(docs)
    index.storage_context.persist('./.idx')
```

For production, persist into Data Fabric attachments or a managed vector DB rather than local disk.

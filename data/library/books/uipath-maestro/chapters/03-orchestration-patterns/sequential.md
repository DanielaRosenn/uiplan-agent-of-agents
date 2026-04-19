# Sequential pattern

Linear chain of action nodes. Use when each step depends on the previous output. Output of node N is available at `$.<node-id>` in node N+1.

```
start -> fetch -> classify -> respond -> end
```

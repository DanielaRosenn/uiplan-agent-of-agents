# Agent lifecycle

```
setup -> auth -> build -> run -> evaluate -> deploy -> sync
```

1. **Setup**: `uip agent new <name> --framework <fw>`
2. **Auth**: `uip auth login`
3. **Build**: install deps; for low-code, edit `agent.json`
4. **Run**: `uip agent run --input '<json>'`
5. **Evaluate**: `uip agent eval evals/regression.json`
6. **Deploy**: `uip agent deploy --folder Production`
7. **Sync**: pull updates from Studio Web with `uip codedapp pull` (low-code) or git for coded

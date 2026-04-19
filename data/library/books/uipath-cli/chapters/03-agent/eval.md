# uip agent eval

Run an evaluation set against the agent and emit scores.

## Synopsis

```bash
uip agent eval <eval-set.json> [--report <file>]
```

## Examples

```bash
uip agent eval evals/regression.json --report out/scores.html
```

## Notes

Evaluation sets are JSON arrays of `{input, expected, scorers[]}`. Built-in scorers: `exact`, `contains`, `llm-judge`, `regex`.

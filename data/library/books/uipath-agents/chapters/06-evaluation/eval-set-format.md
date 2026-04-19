# Eval set format

```json
[
  {
    "name": "basic_billing",
    "input": {"question": "refund my last invoice"},
    "expected": {"category": "billing"},
    "scorers": ["exact:category"]
  },
  {
    "name": "polite_tone",
    "input": {"question": "angry message..."},
    "scorers": ["llm-judge:Response is polite and apologetic."]
  }
]
```

Run: `uip agent eval evals/regression.json --report out/scores.html`

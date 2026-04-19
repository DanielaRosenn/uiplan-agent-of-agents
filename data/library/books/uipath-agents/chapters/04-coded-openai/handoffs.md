# Handoffs and tools

```python
from agents import Agent, function_tool

@function_tool
def lookup_account(email: str) -> dict:
    return {'email': email, 'plan': 'pro'}

billing = Agent(name='Billing', instructions='Resolve billing questions.', tools=[lookup_account])
support = Agent(name='Support', instructions='Resolve support tickets.')

triager = Agent(
    name='Triager',
    instructions='Route to billing or support.',
    handoffs=[billing, support],
)
```

# OpenAI Agents SDK — basic agent

```python
from agents import Agent, Runner

agent = Agent(
    name='Triager',
    instructions='Classify the user request into: billing, support, sales.',
)

def build_agent():
    return agent

# uip agent run wraps Runner.run_sync(agent, input)
```

"""FastAPI sub-routers for the UiPlan Studio API.

Each router groups a coherent slice of the surface area:

- :mod:`bundle` - bundle load/save (legacy direct-write path).
- :mod:`diagram` - diagram load/save.
- :mod:`generation` - section/diagram preview + apply, approval packages.
- :mod:`review` - review run + lifecycle readiness.
- :mod:`context` - context sources + library context.
- :mod:`copilotkit` - CopilotKit runtime info + GraphQL-ish dispatcher.

``app/main.py`` mounts these routers and owns the ``/health`` endpoint plus
the FastAPI app instance / CORS / submodule wiring.
"""

# Test Fixtures for Skills

This directory contains test fixture skills used for unit and integration tests.

## Structure

```
skills/
  user/
    my-user-skill/SKILL.md     # Simulates ~/.cursor/skills/
  extensions/
    team-workflow/SKILL.md     # Simulates extensions/skills/
  uipath-mock/
    uipath-rpa/SKILL.md        # Mocks skills/skills/ (UiPath submodule)
```

## Usage

These fixtures are used to test:

1. **Priority resolution**: User skills override extensions, extensions override UiPath submodule
2. **Provenance tracking**: Each skill should get the correct origin based on its source
3. **Manifest generation**: Skills should be grouped correctly by origin in manifests

## Important

- Do not modify these fixtures without updating corresponding tests
- These fixtures are minimal and stable to prevent test flakiness
- Real skills from the UiPath submodule are not used in tests to ensure isolation

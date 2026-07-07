# Conflict Resolution

Where you want to suggest changes that disagree with architectural documents, an instructions file or other prompt, ASK.

Never use the current codebase as a source, only documentation, instructions or prompts. We assume that the code is something that might need fixing.

- List and describe the conflicts and ask which source to follow in each case.
  - If this skill is being ignored stop
  - If this skill is being followed, update the other sources so they agree

Format:

```
CONFLICT: <TITLE> - <DESCRIPTION>
- The Hex Arg Skill: <WHAT THIS SKILL SAYS YOU SHOULD DO>
- <SOURCE 2>: <SOURCE 2 SPECIFICATION>
- <SOURCE 3>: <SOURCE 3 SPECIFICATION>
...
- <SOURCE N>: <SOURCE N SPECIFICATION>

IMPACT: <IMPACT OF NOT USING HEX ARG SKILL>
```

Example:

```
CONFLICT: Use Case Uses ORM/API Models - Application logic is coupled to SQLModel + response DTOs.

- The Hex Arg Skill: Use cases depend on ports and use domain/simple types, not framework types.
- `/.github/copilot-instructions.md`: Resource models combine SQLModel tables + API schemas in `app/models/.../index.py` and routes may delegate directly to session.

IMPACT: Lower portability and testability: DB/API model changes ripple into use cases, and core logic is harder to isolate from infrastructure.
```

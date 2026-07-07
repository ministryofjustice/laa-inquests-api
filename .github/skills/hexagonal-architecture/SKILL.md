---
name: hexagonal-architecture
description: Core rules for developing code with hexagonal architecture. Use this whenever writing, reviewing, or refactoring any codebase that follows hexagonal architecture or making any recommendations about hexagonal architecture. References the other hex-arch skills for specifics.
---

# Hexagonal Architecture

Apply hexagonal architecture principles whenever writing new code or modifying existing code in a project that says it should use hexagonal architecture in its agent file or architecture docs.

## Structure

The architecture is divided into the following layers. Consult the dedicated skill for each when working on that layer:

- **Domain** — core business objects and logic (`domain` skill)
- **Use Cases** — application logic that orchestrates the domain (`use-cases` skill)
- **Ports** — interfaces that define boundaries between layers (`ports` skill)
- **Inbound Adapters** — drive the application from the outside world (`inbound-adapters` skill)
- **Outbound Adapters** — allow the application to reach the outside world (`outbound-adapters` skill)

YOU MUST look at the specific skill WHENEVER making judgements about how a layer should work.
ONLY load the skill when you need it.

## Dependency Rule

Dependencies always point **inward**:

```
Inbound Adapters → Use Cases → Domain
Outbound Adapters ← (implement) Ports ← Use Cases
```

The domain and use cases must never depend on adapters or infrastructure or even know about them.

THE MOST IMPORTANT THING is that the application layer (usecases and domain) MUST NOT know about the outside world. It is less important that the domain and usecases have a neat separation.

## Refactoring Boundary

- When adding or changing a feature, **only refactor code directly in the path of that change**.
- Do not reorganise unrelated files or layers speculatively.
- If existing code violates these rules and is in the path of your change, perform minimal changes to bring it into compliance. Otherwise, leave it alone and note the deviation when you provide a summary back to the user.

## Conflicting advice

In the event that you want to make a change or give advice that conflicts with the codebase IN ANY WAY, refer to [conflict_resolution.md](references/conflict_resolution.md).

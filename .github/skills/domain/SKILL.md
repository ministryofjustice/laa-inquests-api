---
name: domain
description: Rules for writing domain objects in hexagonal architecture. Use this when creating or modifying or reviewing entities, value objects, aggregates, or domain services.
---

# Domain

The domain is the innermost layer. It contains the business concepts and rules of the application.

## What belongs here

- **Entities** — objects with identity that change over time.
- **Value Objects** — immutable objects defined entirely by their attributes.
- **Aggregates** — clusters of entities and value objects with a single root that enforces consistency.
- **Domain Events** — records of something meaningful that happened within the domain.

## Rules

- Contain business rules and invariants.
- Have zero dependencies on frameworks, infrastructure, or other layers. E.g. a domain object should never be implemented in a way that relates to an ORM or database
- Never import from use cases, ports, or adapters.
- Enforce their own consistency — invalid state should be impossible to represent.

## Anti-patterns to avoid

- Placing validation or business rules in use cases or adapters instead of here. (But be loose on this if the repo doesn't have a solid domain layer).
- Importing ORM annotations, HTTP types, or framework code.
- Anaemic domain objects that are just data bags with no behaviour.

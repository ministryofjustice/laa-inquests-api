---
name: use-cases
description: Rules for writing use cases in hexagonal architecture. Use this when creating or modifying or reviewing a use case / application service class or function.
---

# Use Cases

A use case orchestrates the domain to fulfil a single user-facing or system-facing intention.

## Responsibilities

Use cases implement a single task a user is trying to do, and implementing the business rules around it. They should implement a WHOLE task and NOTHING BUT the task. The name of the usecase should reflect what a user is trying to do, not what the system does.

To do this they:

- Retrieve domain objects via outbound ports.
- Call domain logic on those objects.
- Persist changes via outbound ports.
- Return a result to the caller (inbound adapter).

## Rules

- One use case = one intention. Keep them narrow.
- Contain no business rules — those belong in the domain. (But be loose on this if the repo doesn't have a solid domain layer).
- Contain no infrastructure concerns (HTTP, SQL, queues, etc.) — those belong in adapters.
- Depend only on ports (interfaces), never on concrete adapter implementations.
- Accept and return simple value objects or domain types — not framework-specific types.

## Anti-patterns to avoid

- Putting validation logic that belongs in the domain inside a use case. (But be loose on this if the repo doesn't have a solid domain layer).
- Directly instantiating infrastructure clients or repositories. There should be no instantiation of anything accept domain objects.
- Handling multiple unrelated intentions in one class/function.

## Testing

Should be tested with unit tests that mock out all of the adapters that are used, so only the use case and domain objects are real objects.

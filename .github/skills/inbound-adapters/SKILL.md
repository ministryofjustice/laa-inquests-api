---
name: inbound-adapters
description: Rules for writing inbound adapters (also called presenters, controllers, or primary adapters) in hexagonal architecture. Use this when creating or modifying or reviewing any code that receives input from the outside world (HTTP handlers, CLI commands, queue consumers, event listeners, etc.).
---

# Inbound Adapters

An inbound adapter translates an external trigger (HTTP request, CLI invocation, message, etc.) into a call to a use case.

It is particularly important to keep these small as they are expensive to test.

## Responsibilities

- Parse and validate the incoming request/message format.
- Map the input to the data structure the use case expects.
- Call the appropriate use case.
- Map the use case result back to the external response format (status code, response body, exit code, etc.).

## Rules

- Contain no business logic — delegate everything to the use case.
- Contain no domain logic — do not manipulate domain objects directly.
- Depend on use cases through their input/output types, not on the domain or ports.
- Keep framework-specific code (annotations, decorators, routing) confined to this layer.
- Should instantiate the tree of objects. No instantiation of adapters, use-cases or their dependencies should happen anywhere else.

## Anti-patterns to avoid

- Performing business decisions (conditionals based on business rules) inside a handler/controller.
- Performing business rule validation in the inbound adapter.
- Calling outbound adapters or repositories directly, bypassing the use case.
- Leaking framework types (request/response objects or web sessions) into use cases or the domain.

## Testing

Should be tested with:

- Unit tests that mock out the use cases, where this can be done easily.
- End to End/Feature tests that create the whole app and run against it.

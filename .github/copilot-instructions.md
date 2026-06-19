# GitHub Copilot Instructions — laa-inquests-api

## 1. Before Starting Any Feature

1. **Ask for the Jira ticket ID** (`IDDS-XXX`) if not provided.
2. **Clarify any ambiguous requirements** before writing code.
3. **Run the tests** to confirm a clean baseline: `pytest`.
4. **Find the nearest analogous existing feature** (e.g. the `applications` router and its models) and follow the same pattern exactly.

## 2. Workflow

- **Start by writing E2E tests.** Wait for approval before continuing.
- **Then develop one unit test at a time.** Write the test, make it pass with minimum code, wait for approval before the next.
- **Run tests after every change.** New tests must fail first, then pass after implementation. Fix code, not tests, if refactoring breaks them.
- **NEVER install a new dependency.** Stop and recommend a dependency for the user to add to the appropriate `requirements/source/*.in` file.
- **All code MUST match the architecture** — keep business logic out of routers. Routers handle HTTP only.
- **If a database schema change is required**, e.g. any time a model is changed, create an Alembic migration: `alembic revision --autogenerate -m "description"`.
- **When finished**, run all checks and update documentation.

### Checks before completing any task

```bash
ruff check .          # Linting
ruff format --check . # Formatting
pytest                # All tests
```

### When editing existing files

- Make surgical changes only. Do not refactor unrelated code.
- Do not change test assertions without understanding why they were written that way.
- Fix linting failures — do not suppress rules unless unavoidable and justified.

If these instructions do not cover a specific case, stop and ask.

## 3. Architecture Rules

This project is a **FastAPI REST API** using **SQLModel** (SQLAlchemy + Pydantic) for ORM and schema validation.

- **`app/main.py`** — app factory (`create_app()`). Register routers here, nothing else.
- **`app/routers/`** — `APIRouter` instances. HTTP request/response handling only. No business logic.
- **`app/models/[resource]/`** — SQLModel table models, and Pydantic `Create`/`Update`/`Response` schemas.
- **`app/db/`** — database session factory and Alembic migrations.
- **`app/config/`** — typed config objects. Never access `os.environ` directly in application code.
- **`app/auth/`** — JWT authentication logic.

### Adding a new endpoint

1. Define table model(s) and `Create`/`Response` Pydantic schemas in `app/models/[resource]/index.py`.
2. Add an `APIRouter` in `app/routers/[resource].py` with route handlers that delegate directly to the session.
3. Register the new router in `app/main.py`.
4. Generate an Alembic migration if the schema changed.
5. Write E2E tests in `tests/e2e/[resource]/test_[operation].py`.
6. Write unit tests in `tests/unit/` if there is logic to test in isolation.

## 4. Coding Conventions

- Python 3.12 throughout. Use type hints everywhere.
- Use `snake_case` for all identifiers; `PascalCase` for classes; `UPPER_SNAKE_CASE` for constants.
- Never access `os.environ` directly — use the typed config object in `app/config/`.
- No `print()` in production code.
- SQLModel table models use `snake_case` field names. Pydantic schemas use `alias_generator=to_camel` for JSON serialisation.
- Use `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)` on all request/response models.
- Raise `HTTPException` with appropriate status codes for API errors. Do not let unhandled exceptions propagate.
- Enums for constrained string fields — define them in `app/models/[resource]/enums.py`.

### Naming

| Thing                      | Convention         | Example                              |
| -------------------------- | ------------------ | ------------------------------------ |
| Files / folders            | `snake_case`       | `applications.py`, `application/`   |
| Classes (models, schemas)  | `PascalCase`       | `ApplicationResponse`, `ClientBase` |
| Constants / enum values    | `UPPER_SNAKE_CASE` | `FULL_REPRESENTATION`, `PENDING`    |
| Functions / variables      | `snake_case`       | `create_application`, `laa_reference` |
| URL paths                  | `kebab-case`       | `/applications/{laa_reference}`     |
| Test files                 | `test_[name].py`   | `test_create_application.py`        |
| Model base classes         | `[Resource]Base`   | `ClientBase`, `ApplicationBase`     |
| Request schemas            | `[Resource]Create` / `[Resource]Update` | `ApplicationCreate`, `MeritsDecisionUpdateRefuse` |
| Response schemas           | `[Resource]Response` | `ApplicationResponse`             |

## 5. Testing Standards

This project uses **pytest** with FastAPI's **`TestClient`** (backed by an in-memory SQLite database).

### Fixtures (`tests/conftest.py`)

- `session` — in-memory SQLite session with seed data. Never modify this fixture without understanding all tests that depend on it.
- `client` — `TestClient` with the `session` dependency overridden.
- `auth_token` / `auth_token_disabled_user` — JWT tokens for use in `Authorization: Bearer` headers.

Always use these fixtures. Do not create ad-hoc `TestClient` instances in tests.

### E2E Tests (`tests/e2e/`)

Mirror the router structure: one file per operation (e.g. `test_create_application.py`).

Each endpoint must cover:

- The happy path (correct status code and response body shape)
- Error paths (404, 422, 401/403 as appropriate)
- Authentication — always pass a valid `auth_token` header

Test function names read as sentences:
```python
def test_201_create_application_response_contains_expected_base_properties(client, auth_token):
```

### Unit Tests (`tests/unit/`)

- Isolate logic that is not purely HTTP (e.g. timestamp helpers, validators).
- Mirror the `app/` structure.
- Use plain `assert` statements.

## 6. Exploration

Always output exploration and plans as a markdown file in the session folder, not in the repo.

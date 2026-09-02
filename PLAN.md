# Plan: RBAC framework mapping Entra App Roles to permissions

Ticket: IDDS-411

## Decisions

- Module location: `app/auth/rbac.py` (single file, in the currently-empty `app/auth/` dir) — NOT a top-level `app/rbac/` package, to match this repo's hexagonal architecture (HTTP-layer auth dependencies live alongside `app/routers/dependencies/entra_auth.py`).
- Role source: reuse existing `AuthenticatedUser.scopes` (already merges JWT `scp` + `roles` claims) via the existing `verify_entra_token` dependency in `app/routers/dependencies/entra_auth.py`. No new raw-payload dependency (there is no `app/core/jwt.py` / `get_current_token_payload` in this repo).
- Existing 25 scope-protected routes (`verify_entra_provider_token`, `verify_entra_caseworker_token`, etc.) stay untouched. Full migration to permissions is a future task.
- Only one route migrates now: `POST /applications/upload-coroners-letter` in `app/routers/applications.py`, replacing `Depends(verify_entra_provider_token)` with `Depends(require_permission(Permission.CORONERS_LETTER_UPLOAD))`.

## Steps

1. Create `app/auth/rbac.py` containing:
   - `Permission(str, Enum)`: `APPLICATION_READ = "application:read"`, `APPLICATION_CREATE = "application:create"`, `CLAIM_READ = "claim:read"`, `CLAIM_CREATE = "claim:create"`, `CORONERS_LETTER_UPLOAD = "coroners-letter:upload"`.
   - `ROLE_PERMISSIONS_MAP: dict[str, set[Permission]]` mapping `"Provider.ApplicationUser"` -> `{APPLICATION_READ, APPLICATION_CREATE, CORONERS_LETTER_UPLOAD}` and `"Provider.ClaimsUser"` -> `{CLAIM_READ, CLAIM_CREATE}`.
   - `get_current_user_permissions(user: AuthenticatedUser = Depends(verify_entra_token)) -> set[Permission]`: iterates `user.scopes`, looks up each in `ROLE_PERMISSIONS_MAP` (unmapped/unknown roles contribute nothing), unions results.
   - `require_permission(required_permission: Permission)` factory returning a dependency callable that depends on `get_current_user_permissions` and raises `HTTPException(403, detail=f"Forbidden: Missing required permission '{required_permission.value}'")` if not present.
   - Imports `verify_entra_token` from `app.routers.dependencies`, `AuthenticatedUser` from `app.ports.entra_auth_port`.

2. Wire the example route (*depends on 1*): in `app/routers/applications.py`, on `upload_coroners_letter` (~line 617), replace `_: None = Depends(verify_entra_provider_token)` with `_: None = Depends(require_permission(Permission.CORONERS_LETTER_UPLOAD))`. Update imports (drop `verify_entra_provider_token` if unused elsewhere in file — check first; add `from app.auth.rbac import Permission, require_permission`).

3. Unit tests (*depends on 1*) in new `tests/unit/auth/test_rbac.py` (mirrors `app/auth/` structure per testing standards):
   - `get_current_user_permissions` resolves permissions correctly for a known role, for multiple roles (union), for an unmapped/unknown role (empty set), and for no roles.
   - `require_permission` dependency: allows through when permission present; raises `HTTPException(403, ...)` with the expected detail message when missing.
   - Call the dependency functions directly (construct `AuthenticatedUser` instances / call `get_current_user_permissions(user=...)`), not through `TestClient`.

4. E2E tests (*depends on 2*) in `tests/e2e/application/test_upload_coroners_letter.py` (extend existing file), using per-test `api.dependency_overrides` rather than modifying the shared `entra_auth_client`/`session` fixtures:
   - 201 when token's role is `Provider.ApplicationUser` (has `CORONERS_LETTER_UPLOAD`).
   - 403 when token's role is `Provider.ClaimsUser` (valid role, but missing `CORONERS_LETTER_UPLOAD` permission).
   - 403 when token's role is unmapped/unknown (e.g. `"Some.UnknownRole"`).
   - A dedicated test overriding `api.dependency_overrides[get_current_user_permissions]` directly (per the explicit testing requirement) to mock permissions without real JWTs, using the `client` fixture (auth bypass) plus overriding to return `set()` vs `{Permission.CORONERS_LETTER_UPLOAD}`.

5. Run `ruff check .`, `ruff format --check .`, `pytest` and fix any failures.

## Relevant files

- `app/auth/rbac.py` — new file (all RBAC logic: enum, mapping, dependencies).
- `app/routers/applications.py` — swap dependency on `upload_coroners_letter` route (~line 613-661).
- `app/routers/dependencies/entra_auth.py` — reused as-is, source of `verify_entra_token` and `AuthenticatedUser`.
- `tests/unit/auth/test_rbac.py` — new unit tests.
- `tests/e2e/application/test_upload_coroners_letter.py` — extended with RBAC e2e tests.

## Scope boundaries

- Included: new `app/auth/rbac.py` module, one route migration (`upload_coroners_letter`), unit + e2e tests, dependency-override testing support.
- Excluded: migrating the other 24 existing scope-protected routes (future task), no `app/core/jwt.py`, no top-level `app/rbac/` package, no changes to `EntraAuthAdapter` / `EntraAuthPort` / JWT decoding itself.

## Verification

1. `pytest tests/unit/auth/test_rbac.py tests/e2e/application/test_upload_coroners_letter.py -v`
2. Full suite: `pytest`
3. `ruff check .` and `ruff format --check .`
4. Manual: confirm `/applications/upload-coroners-letter` still 401s with no token, and now 403s for a valid token lacking `Provider.ApplicationUser` / `CORONERS_LETTER_UPLOAD`.

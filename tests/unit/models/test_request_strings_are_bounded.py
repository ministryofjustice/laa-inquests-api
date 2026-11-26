"""Guard: no string a client can send to the API is unbounded.

Reads the generated OpenAPI schema, so it covers every request body (including nested
models and multipart forms) and every path, query and header parameter. A new field that
is a plain `str` fails here until it uses a validated type from
`app.models.validated_types` or is added to ALLOWED_UNBOUNDED with a reason.
"""

from app import api

# A string with one of these formats cannot be unbounded.
_BOUNDING_FORMATS = {"uuid", "date", "date-time", "time", "duration", "binary", "email"}

# Strings the schema cannot show a bound for. Each needs a reason, and the test fails if
# an entry stops being unbounded so this list cannot go stale.
ALLOWED_UNBOUNDED: dict[str, str] = {
    "Body_upload_claim_evidence_claims_evidence_post.file": (
        "Binary upload, not text. No application-level size cap exists; see the note in "
        "the commit or PR about checking the ingress limit."
    ),
    "Body_upload_coroners_letter_applications_upload_coroners_letter_post.file": (
        "Binary upload, not text. No application-level size cap exists; see the note in "
        "the commit or PR about checking the ingress limit."
    ),
    "POST /notifications/callback header authorization": (
        "The bearer token Notify sends. Its length is Notify's, and the server limits "
        "header size. It is compared in constant time."
    ),
}


def _string_leaves(schema, components, path):
    """Yield (path, schema) for every string the schema accepts, following references."""
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        yield from _string_leaves(components[name], components, name)
        return
    for keyword in ("allOf", "anyOf", "oneOf"):
        if keyword in schema:
            branches = schema[keyword]
            if any(branch.get("type") in ("number", "integer") for branch in branches):
                return
            for branch in branches:
                yield from _string_leaves(branch, components, path)
            return
    kind = schema.get("type")
    if kind == "object":
        for name, sub_schema in schema.get("properties", {}).items():
            yield from _string_leaves(sub_schema, components, f"{path}.{name}")
    elif kind == "array":
        yield from _string_leaves(schema.get("items", {}), components, path)
    elif kind == "string":
        yield path, schema


def _is_bounded(schema) -> bool:
    return (
        "maxLength" in schema
        or "enum" in schema
        or "const" in schema
        or schema.get("format") in _BOUNDING_FORMATS
    )


def _request_strings():
    openapi = api.openapi()
    components = openapi.get("components", {}).get("schemas", {})
    for url, operations in openapi["paths"].items():
        for method, operation in operations.items():
            body = operation.get("requestBody", {}).get("content", {})
            for media_type in body.values():
                yield from _string_leaves(media_type["schema"], components, "body")
            for parameter in operation.get("parameters", []):
                yield from _string_leaves(
                    parameter["schema"],
                    components,
                    f"{method.upper()} {url} {parameter['in']} {parameter['name']}",
                )


def _unbounded_strings() -> set[str]:
    return {path for path, schema in _request_strings() if not _is_bounded(schema)}


def test_finds_request_strings_so_the_guard_cannot_pass_by_checking_nothing():
    assert len(list(_request_strings())) > 50


def test_the_guard_flags_a_plain_string_and_accepts_bounded_ones():
    components = {
        "Example": {
            "type": "object",
            "properties": {
                "plain": {"type": "string"},
                "capped": {"type": "string", "maxLength": 5},
                "choice": {"type": "string", "enum": ["a"]},
                "when": {"type": "string", "format": "date"},
                "amount": {"anyOf": [{"type": "number"}, {"type": "string"}]},
                "nested": {"$ref": "#/components/schemas/Inner"},
            },
        },
        "Inner": {"type": "object", "properties": {"loose": {"type": "string"}}},
    }

    leaves = _string_leaves(
        {"$ref": "#/components/schemas/Example"}, components, "body"
    )
    unbounded = {path for path, schema in leaves if not _is_bounded(schema)}

    assert unbounded == {"Example.plain", "Inner.loose"}


def test_every_request_string_is_bounded_or_explicitly_allowed():
    unbounded = _unbounded_strings() - ALLOWED_UNBOUNDED.keys()

    assert not unbounded, (
        "Unbounded request strings (use a validated type from "
        f"app.models.validated_types, or allow-list with a reason): {sorted(unbounded)}"
    )


def test_the_allow_list_only_contains_strings_that_are_still_unbounded():
    stale = ALLOWED_UNBOUNDED.keys() - _unbounded_strings()

    assert not stale, (
        f"Remove from ALLOWED_UNBOUNDED, now bounded or gone: {sorted(stale)}"
    )

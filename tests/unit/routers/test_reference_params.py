import pytest

from app import api

REFERENCE_PARAMS = {"laa_reference", "claim_reference", "firm_id"}


def _reference_params():
    for path, operations in api.openapi()["paths"].items():
        for method, operation in operations.items():
            for parameter in operation.get("parameters", []):
                if parameter["name"] in REFERENCE_PARAMS:
                    yield pytest.param(
                        parameter,
                        id=f"{method.upper()} {path} {parameter['name']}",
                    )


def test_finds_the_reference_params_so_the_checks_below_cannot_pass_by_checking_nothing():
    assert len(list(_reference_params())) >= 18


@pytest.mark.parametrize("parameter", _reference_params())
def test_every_reference_param_has_a_length_cap(parameter):
    assert "maxLength" in parameter["schema"]


@pytest.mark.parametrize(
    "parameter",
    [p for p in _reference_params() if p.values[0]["in"] == "path"],
)
def test_every_reference_path_param_is_shape_checked(parameter):
    assert "pattern" in parameter["schema"]

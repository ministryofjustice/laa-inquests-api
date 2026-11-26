import pytest
from pydantic import ValidationError

from app.models.application.enums import PublicBodyId
from app.models.application.index import PublicBodyCreate


@pytest.mark.parametrize("public_body", list(PublicBodyId), ids=lambda pb: pb.name)
def test_accepts_every_known_public_body_exactly_as_the_ui_sends_it(public_body):
    request = PublicBodyCreate.model_validate({"publicBodyId": public_body.value})

    assert request.public_body_id is public_body


@pytest.mark.parametrize(
    "value", ["Not A Body", "attorney general's office", " Cabinet Office", "", None]
)
def test_rejects_anything_that_is_not_a_known_public_body(value):
    with pytest.raises(ValidationError):
        PublicBodyCreate.model_validate({"publicBodyId": value})

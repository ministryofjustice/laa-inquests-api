from unittest.mock import MagicMock
from fastapi import HTTPException

import pytest

from app.routers.applications import patch_merits_decision
from app.use_cases.exceptions import ProceedingsNotFoundError
from tests.unit.use_cases.test_create_application_use_case import _make_request


def test_patch_mertirs_decision_raises_404_when_no_proceedings_found():
    use_case = MagicMock()
    use_case.execute.side_effect = ProceedingsNotFoundError()

    with pytest.raises(HTTPException) as exception:
        patch_merits_decision("1", _make_request("REFUSED"), use_case=use_case)

    assert exception.value.status_code == 404
    assert exception.value.detail == "No proceedings found for application"

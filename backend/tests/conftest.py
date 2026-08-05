from __future__ import annotations

import pytest

from api.app import app
from api.deps import require_owner
from security.session import OWNER_ID


@pytest.fixture(autouse=True)
def authenticate_global_test_app():
    """Existing API tests run as the single owner unless they build their own app."""
    app.dependency_overrides[require_owner] = lambda: OWNER_ID
    yield
    app.dependency_overrides.pop(require_owner, None)


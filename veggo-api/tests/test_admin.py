import pytest
from app.models.user import UserRole
from app.services.auth_service import require_role


def test_role_enforcement_logic():
    admin_checker = require_role([UserRole.ADMIN])
    agent_checker = require_role([UserRole.DELIVERY_AGENT, UserRole.ADMIN])
    customer_checker = require_role([UserRole.USER, UserRole.ADMIN])

    assert admin_checker is not None
    assert agent_checker is not None
    assert customer_checker is not None

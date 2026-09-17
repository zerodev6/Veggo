import pytest
from app.models.order import OrderStatus
from app.services.delivery_service import calculate_haversine_distance
from app.utils.validators import validate_order_status_transition


def test_order_status_progression():
    # Valid customer and standard pipeline transitions
    assert validate_order_status_transition(OrderStatus.PLACED, OrderStatus.CONFIRMED) is True
    assert validate_order_status_transition(OrderStatus.CONFIRMED, OrderStatus.PREPARING) is True
    assert validate_order_status_transition(OrderStatus.PREPARING, OrderStatus.READY_FOR_PICKUP) is True
    assert validate_order_status_transition(OrderStatus.READY_FOR_PICKUP, OrderStatus.OUT_FOR_DELIVERY) is True
    assert validate_order_status_transition(OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED) is True

    # Customer cancellation allowed when PLACED or CONFIRMED
    assert validate_order_status_transition(OrderStatus.PLACED, OrderStatus.CANCELLED) is True
    assert validate_order_status_transition(OrderStatus.CONFIRMED, OrderStatus.CANCELLED) is True

    # Invalid backwards transition prevented
    assert validate_order_status_transition(OrderStatus.DELIVERED, OrderStatus.PREPARING, is_admin=False) is False


def test_haversine_delivery_distance():
    # Nuwara Eliya center to Hakgala (approx 9-10 km)
    dist = calculate_haversine_distance(6.9497, 80.7891, 6.9272, 80.8202)
    assert 3.0 <= dist <= 6.0

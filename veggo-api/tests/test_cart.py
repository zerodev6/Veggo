import pytest
from app.services.pricing_service import pricing_service


def test_cart_item_subtotal_calculation():
    items = [
        {"unit_type": "WEIGHT", "price_per_kg": 450.0, "price_per_piece": None, "quantity": 750, "unit": "g"},
        {"unit_type": "WEIGHT", "price_per_kg": 380.0, "price_per_piece": None, "quantity": 500, "unit": "g"},
        {"unit_type": "PACK", "price_per_kg": None, "price_per_piece": 420.0, "quantity": 2, "unit": "pack"},
    ]

    total = 0.0
    for it in items:
        _, line = pricing_service.calculate_line_item_price(
            it["unit_type"], it["price_per_kg"], it["price_per_piece"], it["quantity"], it["unit"]
        )
        total += line

    # 337.50 (carrots) + 190.00 (leeks) + 840.00 (eggs) = 1367.50
    assert total == 1367.50

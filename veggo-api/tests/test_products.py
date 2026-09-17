import pytest
from app.services.pricing_service import pricing_service


def test_custom_weight_pricing_calculation():
    # 750g of carrots @ Rs. 450/kg
    base, line_total = pricing_service.calculate_line_item_price(
        unit_type="WEIGHT",
        price_per_kg=450.0,
        price_per_piece=None,
        quantity=750,
        unit="g"
    )
    assert base == 450.0
    assert line_total == 337.50  # 450 / 1000 * 750 = 337.50

    # 100g of carrots @ Rs. 450/kg
    _, line_100g = pricing_service.calculate_line_item_price(
        unit_type="WEIGHT",
        price_per_kg=450.0,
        price_per_piece=None,
        quantity=100,
        unit="g"
    )
    assert line_100g == 45.00

    # 1.5kg of carrots @ Rs. 450/kg
    _, line_15kg = pricing_service.calculate_line_item_price(
        unit_type="WEIGHT",
        price_per_kg=450.0,
        price_per_piece=None,
        quantity=1.5,
        unit="kg"
    )
    assert line_15kg == 675.00


def test_piece_and_pack_pricing():
    # 3 packs of eggs @ Rs. 420/pack
    base, total = pricing_service.calculate_line_item_price(
        unit_type="PACK",
        price_per_kg=None,
        price_per_piece=420.0,
        quantity=3,
        unit="pack"
    )
    assert base == 420.0
    assert total == 1260.00

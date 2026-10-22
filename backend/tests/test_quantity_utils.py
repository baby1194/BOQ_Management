from utils.quantity_utils import round_quantity


def test_round_quantity_two_decimals():
    assert round_quantity(4.596) == 4.6
    assert round_quantity(16.443) == 16.44
    assert round_quantity(4.6) == 4.6


def test_round_quantity_half_up():
    assert round_quantity(1.125) == 1.13
    assert round_quantity(1.124) == 1.12
    assert round_quantity("1.125") == 1.13

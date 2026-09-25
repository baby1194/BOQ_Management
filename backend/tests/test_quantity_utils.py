from utils.quantity_utils import round_quantity


def test_round_quantity_two_decimals():
    assert round_quantity(4.596) == 4.6
    assert round_quantity(16.443) == 16.44
    assert round_quantity(4.6) == 4.6

import math

from utils.quantity_utils import boq_has_non_zero_psq, round_quantity


def test_round_quantity_two_decimals():
    assert round_quantity(4.596) == 4.6
    assert round_quantity(16.443) == 16.44
    assert round_quantity(4.6) == 4.6


def test_round_quantity_half_up():
    assert round_quantity(1.125) == 1.13
    assert round_quantity(1.124) == 1.12
    assert round_quantity("1.125") == 1.13
    # 0.835 must become 0.84. Python's own round() prints it as 0.83.
    assert round_quantity(0.835) == 0.84
    assert round(0.835, 2) == 0.83
    # The float just under 0.835 is what Excel stores for a cell that shows 0.835.
    assert round_quantity(math.nextafter(0.835, 0)) == 0.84
    assert round_quantity(-0.835) == -0.84
    # 0.8345 is the low edge of a cell Excel shows as 0.835.
    assert round_quantity(0.8345) == 0.84
    assert round_quantity("0.8345") == 0.84
    assert round_quantity(0.8344) == 0.83


def test_equal_printed_quantities_are_not_a_psq_difference():
    # 1.005 and 1.006 both print as 1.01. Database rounding splits them.
    assert boq_has_non_zero_psq(1.005, 1.006) is False
    assert boq_has_non_zero_psq(7.224, 7.221) is False
    assert boq_has_non_zero_psq(7.22, 7.22) is False
    assert boq_has_non_zero_psq(0.004, 0) is False


def test_a_real_psq_difference_stays():
    assert boq_has_non_zero_psq(7.23, 7.22) is True
    assert boq_has_non_zero_psq(7.226, 7.22) is True

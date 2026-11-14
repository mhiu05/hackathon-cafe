import pytest

from .test_live_smoke import assert_prices_grounded, strip_budget_echo


def test_budget_echo_is_not_a_menu_price():
    text = "Một vài lựa chọn dưới 50.000đ:\n- Cà phê đen — 35.000đ"
    assert_prices_grounded(strip_budget_echo(text, 50000), {35000})


def test_fabricated_item_at_budget_is_still_rejected():
    text = "Dưới 50.000đ:\n- Món bịa — 50.000đ"
    with pytest.raises(AssertionError, match="Ungrounded price"):
        assert_prices_grounded(strip_budget_echo(text, 50000), {35000})

"""Tests for agents/_budget_manager.py."""
import pytest
from agents._budget_manager import BudgetManager
from agents.base_agent import BudgetExceeded


class TestBudgetManagerInit:
    def test_initial_state(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=5.0)
        assert bm.session_cost == 0.0
        assert bm.session_calls == 0
        assert bm.is_paused is False

    def test_no_limit(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=None)
        assert bm.budget_limit_usd is None


class TestBudgetManagerCheck:
    def test_no_limit_never_raises(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=None)
        bm.session_cost = 9999.0
        bm.check()  # should not raise

    def test_under_limit_ok(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=10.0)
        bm.session_cost = 5.0
        bm.check()  # should not raise

    def test_exact_limit_raises(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=5.0)
        bm.session_cost = 5.0
        with pytest.raises(BudgetExceeded):
            bm.check()

    def test_over_limit_raises(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=5.0)
        bm.session_cost = 6.0
        with pytest.raises(BudgetExceeded):
            bm.check()

    def test_over_limit_sets_is_paused(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=5.0)
        bm.session_cost = 6.0
        with pytest.raises(BudgetExceeded):
            bm.check()
        assert bm.is_paused is True

    def test_error_message_contains_agent_name(self):
        bm = BudgetManager("MyAgent", budget_limit_usd=1.0)
        bm.session_cost = 2.0
        with pytest.raises(BudgetExceeded, match="MyAgent"):
            bm.check()


class TestBudgetManagerReset:
    def test_reset_clears_cost_and_calls(self):
        bm = BudgetManager("TestAgent", budget_limit_usd=10.0)
        bm.session_cost = 3.0
        bm.session_calls = 7
        bm.is_paused = True
        bm.reset()
        assert bm.session_cost == 0.0
        assert bm.session_calls == 0
        assert bm.is_paused is False

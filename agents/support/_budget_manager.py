"""Budget guard for agent sessions."""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BudgetManager:
    def __init__(self, agent_name: str, budget_limit_usd: Optional[float]) -> None:
        self.agent_name = agent_name
        self.budget_limit_usd = budget_limit_usd
        self.session_cost: float = 0.0
        self.session_calls: int = 0
        self.is_paused: bool = False

    def check(self) -> None:
        from agents.base_agent import BudgetExceeded
        if self.budget_limit_usd and self.session_cost >= self.budget_limit_usd:
            self.is_paused = True
            logger.error(
                "[%s] BUDGET EXCEEDED: $%.4f / $%.2f — PAUSING",
                self.agent_name, self.session_cost, self.budget_limit_usd,
            )
            raise BudgetExceeded(
                f"Agent {self.agent_name} paused: cost ${self.session_cost:.4f} "
                f"exceeds limit ${self.budget_limit_usd:.2f}"
            )

    def reset(self) -> None:
        self.session_cost = 0.0
        self.session_calls = 0
        self.is_paused = False

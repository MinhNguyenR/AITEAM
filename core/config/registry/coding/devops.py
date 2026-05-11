from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "DEVOPS": {
        "model": "deepseek/deepseek-v4-pro",
        "role": "DevOps",
        "reason": "Thiết kế hạ tầng IaC, quản lý Kubernetes và quy trình CI/CD.",
        "tier": "DEVOPS",
        "priority": 3,
        "max_tokens": 4096,
        "temperature": 0.2,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
}

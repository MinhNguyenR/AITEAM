from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "FAST_TEST_AGENT": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "QA Engineer A",
        "reason": "Viết và chạy unit test nhanh, bao phủ happy path và edge case cơ bản.",
        "tier": "QA",
        "priority": 2,
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
    },
    "DEEP_TEST_AGENT": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "QA Engineer B",
        "reason": "Viết integration test, test bảo mật và kiểm tra các luồng nghiệp vụ phức tạp.",
        "tier": "QA",
        "priority": 2,
        "max_tokens": 4096,
        "temperature": 0.7,
        "top_p": 1.0,
    },
}

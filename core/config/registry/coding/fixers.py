from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "FIX_WORKER_A": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "Bug Fixer A",
        "reason": "Sửa bug nhanh, tập trung vào lỗi cú pháp, runtime error và logic đơn giản.",
        "tier": "FIX",
        "priority": 3,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
    },
    "FIX_WORKER_B": {
        "model": "deepseek/deepseek-v3.2",
        "role": "Bug Fixer B",
        "reason": "Sửa bug trung bình: logic sai, race condition và lỗi tích hợp giữa các module.",
        "tier": "FIX",
        "priority": 4,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
    },
    "FIX_WORKER_C": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Bug Fixer C",
        "reason": "Sửa bug phức tạp: memory leak, concurrency và lỗi hiệu năng hệ thống.",
        "tier": "FIX",
        "priority": 4,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
    },
    "ADVANCED_FIX_WORKER_A": {
        "model": "xiaomi/mimo-v2.5-pro",
        "role": "Deep Fixer A",
        "reason": "Debug nâng cao: phân tích stack trace, profiling và điều tra lỗi khó tái hiện.",
        "tier": "FIX",
        "priority": 4,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
    },
    "ADVANCED_FIX_WORKER_B": {
        "model": "moonshotai/kimi-k2.6",
        "role": "Deep Fixer B",
        "reason": "Debug chuyên sâu với reasoning dài, xử lý lỗi kiến trúc và tối ưu hóa hệ thống.",
        "tier": "FIX",
        "priority": 4,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
    },
}

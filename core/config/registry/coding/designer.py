REGISTRY = {
    'DESIGNER': {
        'model': 'qwen/qwen3.6-plus',
        'role': 'Designer',
        'reason': 'Thiet ke UX/UI, luong trai nghiem, visual system, layout, component states va su nhat quan san pham.',
        'tier': 'DESIGN',
        'priority': 2,
        'max_tokens': 120000,
        'temperature': 0.7,
        'top_p': 1.0,
        'cache_enabled': True,
        'cache_ttl_seconds': 300,
        'reasoning': {'effort': 'medium', 'exclude': False, 'enabled': True, 'summary': 'detailed'},
    },
}
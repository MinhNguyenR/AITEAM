"""Tests for Ambassador static tier classification methods — no API calls needed."""
import pytest
from agents.ambassador import Ambassador


class TestClassifyTierFallback:
    """Full matrix of _classify_tier_fallback across 4 tiers."""

    # --- HARD ---
    @pytest.mark.parametrize("prompt", [
        "Write a CUDA kernel for matrix multiplication",
        "Optimize GPU memory for RTX 5080",
        "Implement a multi-GPU NCCL all-reduce",
        "Low-level assembly for warp divergence",
        "threadIdx blockIdx __global__ kernel launch",
    ])
    def test_hard_tier(self, prompt):
        assert Ambassador._classify_tier_fallback(prompt) == "HARD"

    # --- EXPERT ---
    @pytest.mark.parametrize("prompt", [
        "Design a distributed microservice architecture",
        "Prove the theorem for convergence of gradient descent",
        "Multi-agent orchestration pipeline for enterprise",
        "Thiết kế hệ thống phân tán với kiến trúc microservice",
        "Derive the backpropagation equations for LSTM",
    ])
    def test_expert_tier(self, prompt):
        assert Ambassador._classify_tier_fallback(prompt) == "EXPERT"

    # --- MEDIUM ---
    @pytest.mark.parametrize("prompt", [
        "Write a FastAPI endpoint with PostgreSQL",
        "Create a LangChain chatbot with RAG retrieval",
        "Implement a machine learning training loop",
        "Build a REST API with Django and ORM",
        "Viết hàm Python để phân loại văn bản",
    ])
    def test_medium_tier(self, prompt):
        assert Ambassador._classify_tier_fallback(prompt) == "MEDIUM"

    # --- LOW ---
    @pytest.mark.parametrize("prompt", [
        "What is a decorator in Python?",
        "Why does Python use indentation?",
        "What is the purpose of a variable?",
        "Vì sao Python lại phổ biến?",
        "Định nghĩa của thuật toán là gì?",
    ])
    def test_low_tier(self, prompt):
        assert Ambassador._classify_tier_fallback(prompt) == "LOW"

    def test_default_medium_for_ambiguous(self):
        assert Ambassador._classify_tier_fallback("hello world test") == "MEDIUM"


class TestDetectLanguage:
    def test_detects_cuda(self):
        assert Ambassador._detect_language("__global__ kernel threadIdx") == "cuda"

    def test_detects_python(self):
        assert Ambassador._detect_language("def my_function(): import os") == "python"

    def test_detects_cpp(self):
        assert Ambassador._detect_language("#include <vector> std::vector") == "cpp"

    def test_detects_javascript(self):
        assert Ambassador._detect_language("const x = 5; console.log(x)") == "javascript"

    def test_detects_rust(self):
        assert Ambassador._detect_language("fn main() { let mut x = 5; }") == "rust"

    def test_natural_fallback(self):
        assert Ambassador._detect_language("explain machine learning concepts") == "natural"


class TestExtractVram:
    def test_extracts_gb(self):
        assert Ambassador._extract_vram("Need 16GB VRAM for this model") == "16GB"

    def test_extracts_mb(self):
        assert Ambassador._extract_vram("Use 512MB memory") == "512MB"

    def test_no_vram_returns_none(self):
        assert Ambassador._extract_vram("no memory info here") is None

    def test_decimal_gb(self):
        assert Ambassador._extract_vram("requires 8.5GB") == "8.5GB"


class TestApplyTierUpgradeRules:
    def test_cuda_always_becomes_hard(self):
        result = Ambassador._apply_tier_upgrade_rules("LOW", is_cuda=True, complexity=0.1, is_hardware_bound=False)
        assert result == "HARD"

    def test_high_complexity_non_hw_becomes_expert(self):
        result = Ambassador._apply_tier_upgrade_rules("MEDIUM", is_cuda=False, complexity=0.9, is_hardware_bound=False)
        assert result == "EXPERT"

    def test_high_complexity_hw_stays_medium(self):
        result = Ambassador._apply_tier_upgrade_rules("MEDIUM", is_cuda=False, complexity=0.9, is_hardware_bound=True)
        assert result == "MEDIUM"

    def test_low_complexity_stays(self):
        result = Ambassador._apply_tier_upgrade_rules("LOW", is_cuda=False, complexity=0.3, is_hardware_bound=False)
        assert result == "LOW"

    def test_cuda_overrides_hardware_bound(self):
        result = Ambassador._apply_tier_upgrade_rules("MEDIUM", is_cuda=True, complexity=0.5, is_hardware_bound=True)
        assert result == "HARD"

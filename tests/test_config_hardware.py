"""Tests for core/config/hardware.py — GPU/RAM detection and hardware string."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

from core.config.hardware import build_hardware_string, detect_gpu_info, detect_total_ram_gb


class TestBuildHardwareString:
    def test_cuda_device(self):
        result = build_hardware_string("Linux", "5.15", "x86_64", 16.0, "cuda", "RTX 3090", 24.0)
        assert "GPU: RTX 3090" in result
        assert "24.0GB VRAM" in result
        assert "Linux 5.15" in result
        assert "16.0GB RAM" in result

    def test_cpu_only(self):
        result = build_hardware_string("Windows", "11", "AMD64", 32.0, "cpu", "CPU (No GPU detected)", 0.0)
        assert "GPU: None (CPU mode)" in result
        assert "32.0GB RAM" in result
        assert "Windows 11" in result

    def test_format_structure(self):
        result = build_hardware_string("Darwin", "21.0", "arm64", 8.0, "cpu", "CPU", 0.0)
        parts = result.split("|")
        assert len(parts) == 4


class TestDetectGpuInfo:
    def test_torch_cuda_available(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "RTX 4090"
        mock_props = MagicMock()
        mock_props.total_memory = 24 * (1024 ** 3)
        mock_torch.cuda.get_device_properties.return_value = mock_props
        with patch.dict(sys.modules, {"torch": mock_torch}):
            device, name, vram = detect_gpu_info()
        assert device == "cuda"
        assert "RTX" in name
        assert vram > 0

    def test_torch_not_available_falls_through(self):
        with patch.dict(sys.modules, {"torch": None}), \
             patch.dict(sys.modules, {"GPUtil": None}):
            with patch("subprocess.run", side_effect=FileNotFoundError("nvidia-smi not found")):
                device, name, vram = detect_gpu_info()
        assert device == "cpu"
        assert vram == 0.0

    def test_torch_cuda_not_available(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        with patch.dict(sys.modules, {"torch": mock_torch, "GPUtil": None}):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                device, name, vram = detect_gpu_info()
        assert device == "cpu"

    def test_gputil_fallback(self):
        mock_gpu = MagicMock()
        mock_gpu.name = "GTX 1080"
        mock_gpu.memoryTotal = 8192  # MB
        mock_gputil = MagicMock()
        mock_gputil.getGPUs.return_value = [mock_gpu]
        with patch.dict(sys.modules, {"torch": None, "GPUtil": mock_gputil}):
            device, name, vram = detect_gpu_info()
        assert device == "cuda"
        assert "1080" in name
        assert abs(vram - 8.0) < 0.1

    def test_nvidia_smi_fallback(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "RTX 3080, 10240\n"
        with patch.dict(sys.modules, {"torch": None, "GPUtil": None}):
            with patch("subprocess.run", return_value=mock_result):
                device, name, vram = detect_gpu_info()
        assert device == "cuda"
        assert "3080" in name

    def test_nvidia_smi_timeout(self):
        import subprocess
        with patch.dict(sys.modules, {"torch": None, "GPUtil": None}):
            with patch("subprocess.run", side_effect=TimeoutError("timeout")):
                device, name, vram = detect_gpu_info()
        assert device == "cpu"

    def test_returns_cpu_fallback_when_all_fail(self):
        with patch.dict(sys.modules, {"torch": None, "GPUtil": None}):
            with patch("subprocess.run", side_effect=OSError("no nvidia")):
                device, name, vram = detect_gpu_info()
        assert device == "cpu"
        assert vram == 0.0


class TestDetectTotalRamGb:
    def test_psutil_path(self):
        mock_psutil = MagicMock()
        mock_psutil.virtual_memory.return_value.total = 16 * (1024 ** 3)
        with patch.dict(sys.modules, {"psutil": mock_psutil}):
            result = detect_total_ram_gb()
        assert abs(result - 16.0) < 0.1

    def test_fallback_when_psutil_missing(self):
        with patch.dict(sys.modules, {"psutil": None}):
            # On any platform, this should not raise
            result = detect_total_ram_gb()
        assert isinstance(result, float)
        assert result >= 0.0

    def test_returns_float_on_any_platform(self):
        # No mocking — just verify it returns a float without raising
        result = detect_total_ram_gb()
        assert isinstance(result, float)
        assert result >= 0.0

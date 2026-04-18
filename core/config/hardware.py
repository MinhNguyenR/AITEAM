from __future__ import annotations

import os
import platform
from typing import Tuple


def detect_gpu_info() -> Tuple[str, str, float]:
    try:
        import torch

        if torch.cuda.is_available():
            return (
                "cuda",
                torch.cuda.get_device_name(0),
                torch.cuda.get_device_properties(0).total_memory / (1024**3),
            )
    except ImportError:
        pass

    try:
        import GPUtil

        gpus = GPUtil.getGPUs()
        if gpus:
            gpu = gpus[0]
            return ("cuda", gpu.name, gpu.memoryTotal / 1024)
    except ImportError:
        pass

    try:
        import subprocess

        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines:
                parts = lines[0].split(",")
                return ("cuda", parts[0].strip(), float(parts[1].strip()) / 1024)
    except (FileNotFoundError, OSError, ValueError, IndexError, TimeoutError):
        pass

    return ("cpu", "CPU (No GPU detected)", 0.0)


def detect_total_ram_gb() -> float:
    try:
        import psutil

        return psutil.virtual_memory().total / (1024**3)
    except ImportError:
        pass

    try:
        if platform.system() == "Windows":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            c_ulonglong = ctypes.c_ulonglong

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", c_ulonglong),
                    ("ullAvailPhys", c_ulonglong),
                    ("ullTotalPageFile", c_ulonglong),
                    ("ullAvailPageFile", c_ulonglong),
                    ("ullTotalVirtual", c_ulonglong),
                    ("ullAvailVirtual", c_ulonglong),
                    ("ullAvailExtendedVirtual", c_ulonglong),
                ]

            memory_status = MEMORYSTATUSEX()
            memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
            return memory_status.ullTotalPhys / (1024**3)

        pages = os.sysconf("SC_PAGE_SIZE")
        page_count = os.sysconf("SC_PHYS_PAGES")
        return (pages * page_count) / (1024**3)
    except (AttributeError, OSError, ValueError, TypeError):
        return 0.0


def build_hardware_string(
    system_name: str,
    release: str,
    machine: str,
    total_ram_gb: float,
    device: str,
    gpu_name: str,
    total_vram_gb: float,
) -> str:
    os_str = f"{system_name} {release}"
    cpu_str = machine
    ram_str = f"{total_ram_gb:.1f}GB RAM"
    if device == "cuda":
        gpu_str = f"GPU: {gpu_name} ({total_vram_gb:.1f}GB VRAM)"
    else:
        gpu_str = "GPU: None (CPU mode)"
    return f"{os_str} | CPU: {cpu_str} | {ram_str} | {gpu_str}"

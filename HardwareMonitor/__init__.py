"""
HardwareMonitor - Python wrapper for LibreHardwareMonitorLib.dll

通过 pythonnet (clr) 加载 LibreHardwareMonitorLib.dll，
将 .NET 类型暴露为 Python 可用的 Hardware 子模块。
"""

import clr
import os
import sys

# 优先使用旧版 DLL（兼容 .NET Framework/8），新版 .NET 10 DLL 需要 .NET 10 运行时
_DLL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "LibreHardwareMonitor")
_DLL_PATH = os.path.join(_DLL_DIR, "LibreHardwareMonitorLib.dll")

if not os.path.exists(_DLL_PATH):
    _DLL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "LibreHardwareMonitor.NET.10")
    _DLL_PATH = os.path.join(_DLL_DIR, "LibreHardwareMonitorLib.dll")

if not os.path.exists(_DLL_PATH):
    raise FileNotFoundError(
        "找不到 LibreHardwareMonitorLib.dll，请确保 LibreHardwareMonitor 或 "
        "LibreHardwareMonitor.NET.10 目录存在于程序目录下"
    )

# 将 DLL 所在目录加入搜索路径，以便加载依赖
sys.path.insert(0, _DLL_DIR)

# 加载主 DLL
clr.AddReference("LibreHardwareMonitorLib")

# 导入 .NET 命名空间下的 Hardware 子模块
from LibreHardwareMonitor import Hardware

# 同时预加载常用类型，方便代码中使用
from LibreHardwareMonitor.Hardware import (
    Computer,
    IComputer,
    ISensor,
    IHardware,
    IParameter,
    IVisitor,
    SensorType,
)

__all__ = [
    "Hardware",
    "Computer",
    "IComputer",
    "ISensor",
    "IHardware",
    "IParameter",
    "IVisitor",
    "SensorType",
]

#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import glob
import json  # 用于保存json格式配置
import copy  # 用于深拷贝独立配置
import shutil  # 用于配置文件迁移
import os  # 用于读取文件
import queue  # geezmo: 流水线同步和交换数据用
import sys
import threading  # 引入多线程支持
import time  # 引入延时库
import traceback
from datetime import datetime  # 用于获取当前时间

# ================= PySide6 (Qt) UI 库 =================
# 主界面已从 Tkinter 迁移到 PySide6（Qt 6.11）。业务逻辑层（串口/渲染/配置/API）全部复用。
from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject, QPoint, QEvent
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap, QColor, QFont, QCloseEvent, QPalette
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QLabel, QPushButton, QComboBox, QCheckBox, QRadioButton,
    QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit, QPlainTextEdit,
    QGroupBox, QFrame, QScrollArea, QFileDialog, QColorDialog, QSlider,
    QMessageBox, QDialog, QDialogButtonBox, QSizePolicy, QSplitter, QToolButton, QMenu,
    QStackedWidget, QListWidget, QListWidgetItem, QStyleFactory,
)

import cv2
import numpy as np  # 使用numpy加速数据处理
import psutil  # 引入psutil获取设备信息（需要额外安装）
import pystray
import serial  # 引入串口库（需要额外安装）
import serial.tools.list_ports
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk  # 引入PIL库进行图像处理
from PyCameraList import camera_device
from mss import mss  # 用于桌面截图的备用方案

isWindows = True if os.name == "nt" else False

if isWindows:
    from ctypes import windll
    import win32con
    import win32gui
    import win32process
    import win32ui

    # 使用高dpi缩放适配高分屏。
    # 必须在 QApplication 创建前把进程 DPI awareness 精确设为 Qt6 默认的
    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2（(HANDLE)-4）。否则 Qt 初始化时
    # 无法覆盖已设置的 awareness（Windows 只允许设置一次），会打印
    # "SetProcessDpiAwarenessContext() failed: 拒绝访问" 警告（无害，但碍眼）。
    try:  # win 10 1607+（SetProcessDpiAwarenessContext 可用）
        from ctypes import wintypes
        windll.user32.SetProcessDpiAwarenessContext.argtypes = [wintypes.HANDLE]
        windll.user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        windll.user32.SetProcessDpiAwarenessContext(wintypes.HANDLE(-4))
    except Exception:  # win 10 1606 及更早，回退到旧接口
        try:
            windll.shcore.SetProcessDpiAwareness(1)  # 0：不使用缩放 1：所有屏幕 2：当前屏幕
        except Exception:  # win 8.0 or less
            try:
                windll.user32.SetProcessDPIAware()
            except Exception:
                pass
    try:
        scale_factor = windll.shcore.GetScaleFactorForDevice(0)
        system_dpi = windll.user32.GetDpiForSystem()
    except:
        scale_factor = 100
        system_dpi = 96.0

    try:
        # 取消命令行窗口快速编辑模式，防止鼠标误触导致阻塞
        windll.kernel32.SetConsoleMode(windll.kernel32.GetStdHandle(-10), 128)
    except:
        pass
    try:
        if not windll.shell32.IsUserAnAdmin():  # 测试是否是以管理员权限启动
            print("WARN：需要以管理员权限启动本程序，否则部分指标将无法获取")
            # windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
            # sys.exit(0)
    except Exception:
        pass
else:  # linux
    # 命令行或后台启动需要加DISPLAY
    os.environ["DISPLAY"] = ":0.0"

# 颜色对应的RGB565编码
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
WHITE = 0xFFFF
BLACK = 0x0000
YELLOW = 0xFFE0
GRAY0 = 0xEF7D
GRAY1 = 0x8410
GRAY2 = 0x4208

# ==================== 程序元数据 ====================
PROGRAM_TITLE = "USB副屏工具"
PROGRAM_SUBTITLE = ""
PROGRAM_VERSION = "5.1.1"
PROGRAM_AUTHOR = "杜玛"
PROGRAM_GITHUB = "https://github.com/duma520/MSU2_MINI_V2"
PROGRAM_LICENSE = "MIT"
PROGRAM_BUILD_DATE = "2026-08-17"

# 整合自以下开源项目（均为MIT协议）
PROGRAM_SOURCE_PROJECTS = [
    {
        "name": "just-fun-for-MSU2_MINI",
        "author": "dimangopie",
        "url": "https://github.com/dimangopie/just-fun-for-MSU2_MINI",
        "license": "MIT",
    },
    {
        "name": "msu2_mini",
        "author": "dchg43",
        "url": "https://github.com/dchg43/msu2_mini",
        "license": "MIT",
    },
]

# 版本更新说明
PROGRAM_CHANGELOG = """
v5.1.1 (2026-08-17)
- 修复：显示墙设置无法自动保存/恢复——原写入全局配置会被多屏渲染线程切换导致落错文件，现改为独立配置文件 config/MSU2_MINI_wall.json（原子写入），下次启动自动恢复

v5.1.0 (2026-08-17)
- 新增「电视墙」标签页（第一层：中控 | 电视墙 | 关于）
- 第一层原「主控」标签更名「中控」，避免与第三层「主控」子页同名混淆
- 电视墙包含「显示墙」与「显示墙设置」：显示墙按设置的行×列网格实时显示所有小屏预览；显示墙设置根据已连接屏幕数量动态提供快速布局（横向/纵向排布），布局可保存

v5.0.0 (2026-08-16)
- 重大重构：主界面由 Tkinter 迁移到 PySide6 (Qt 6.11)，界面更现代、布局更规范；业务逻辑层（串口/渲染/配置/API）全部复用
- 新界面结构：顶部为「主控 | 关于」两个标签；主控页内按屏幕分标签（屏幕1/屏幕2…）；每块屏标签内再嵌套「主控 | 设置 | 设备信息」三个子页，每屏一套独立控件
- 主控子页：页面/方向选择 + 自定义显示（占位）+ 每屏实时预览；烧写区与信息框为程序级共享（主控页外层）
- 注：设置页 / 设备信息页当前为占位页，内容将在后续版本逐步填充；原 Tkinter 版保留为 MSU2_MINI_V2.py 可回退

v4.8.0 (2026-08-16)
- 新增：主控页改为「每屏一个标签页」（多屏时），每块屏一套独立主控控件（颜色/页面/方向/FPS/动图间隔/相机/镜像窗口/实时预览等），彻底隔离各屏状态
- 新增：设置页与设备信息页顶部也增加「每屏一个标签」，切换标签即切换当前配置屏；主控标签、设置标签、设备信息标签、顶部设备下拉框四处双向联动
- 各屏主控控件值绑定本屏配置，保存时锁定本屏，从结构上杜绝多屏「串台」（屏幕2显示成屏幕1页面等）
- 设置页/设备信息页内容共享一套控件，切换标签时刷新为该屏配置（避免每屏复制整套设置控件造成界面臃肿），配合每屏独立配置实现逻辑隔离

v4.7.1 (2026-08-16)
- 修复：切换屏幕时 API 服务器被反复重启（端口/令牌控件刷新误触发重启），现仅同步配置、不重启服务器，日志不再重复且切换不再卡顿
- 修复：切换设备时批量刷新控件不再重复写盘，消除切换卡顿；刷新操作锁定到 UI 当前选中屏，避免后台渲染线程切换全局配置导致界面串错
- 修复：多屏页面串扰（如 屏幕1流量监控 → 切到屏幕2后屏幕2也变成流量监控）；渲染按各屏自己的运行时页面显示，切换设备时页面同步不再经过全局配置对象
- 修复：切换设备后相机下拉框/屏幕镜像窗口下拉框不再残留上一屏幕的值（找不到时显示为空）

v4.7.0 (2026-08-16)
- 修复：设备连接后设置页/主控页控件自动同步为设备已保存的配置（此前强制投屏等设置可能显示为默认值，造成"设置没保存"的错觉）
- 修复：退出程序时等待配置写盘完成再结束，避免修改后立刻关闭导致设置未写入文件
- 优化：摄像头列表改为后台枚举（启动不再卡顿）；摄像头/窗口下拉框点击后台刷新；「检测屏幕」与设备信息「刷新」改为后台线程执行串口读取，界面不卡顿

v4.6.4 (2026-08-16)
- 新增「屏幕序号检测」：触发后所有副屏同时显示各自屏号（屏幕1/屏幕2…），显示时长后自动恢复原画面（如 热搜）
- 触发方式：设置 → API接入 的「检测屏幕」按钮、网页控制台「🔢 屏幕序号检测」按钮、API /api/screen/id 及统一命令 screen_id
- 显示时长可在「设置 → API接入」配置（1~300秒，默认5秒），检测期间不改变页面状态，结束自动返回原页面

v4.6.3 (2026-08-16)
- 新增「强制投屏」：设置 → API接入 可勾选，未选择「API投屏」页也可投屏（任何页面都会被投屏覆盖）
- 强制投屏停止后自动返回投屏前的页面（如 热搜），无需手动切页；按设备保存，多屏各自独立
- /api/config 与 /api/config/set 白名单新增 api_overlay 字段；文档与 OpenAPI 说明同步更新

v4.6.2 (2026-08-16)
- API 新增信息/查询接口：/api/health 健康检查、/api/version 版本、/api/protocols 列出全部接入协议与地址（自动发现）、/api/status 综合运行状态、/api/config 读取配置、/api/screenshot 获取当前屏画面（PNG+RGB888）
- API 新增控制/配置接口：/api/page/next、/api/page/prev 翻页；/api/key 模拟按键；/api/orientation 设置LCD方向；/api/marquee 跑马灯投屏；/api/config/set 白名单改配置（40+字段，立即保存）；/api/device/select 切换活跃屏；/api/device/refresh 刷新设备；/api/notify 状态栏通知；/api/quit 退出程序（需force）
- 全部新命令同步加入统一命令 type 分发，TCP/UDP/WebSocket/命名管道/热文件夹/stdin 等所有协议均可用；OpenAPI 增至 31 个端点，文档同步

v4.6.1 (2026-08-16)
- 新增多种本地接入协议：TCP Socket（JSON行，端口+1）、UDP（JSON报，端口+2）、热文件夹（程序目录 hotfolder/ 放入图片/文本即投屏）、Windows命名管道、Unix Domain Socket、ZeroMQ（端口+3，需pyzmq）、stdin/stdout管道、SSE事件流（/api/events）
- 统一命令执行器：所有协议命令格式与 HTTP/WebSocket 完全一致（type 为 screen/text/clear/slideshow/stop/page/mirror，支持 device 指定目标屏）
- 设置页「API接入」显示全部协议地址；网页控制台文档、/docs 说明、OpenAPI 描述同步更新

v4.6.0 (2026-08-16)
- 新增「API投屏」页面与本地 API 服务器（HTTP + WebSocket，默认 127.0.0.1:8632），供其他程序自定义投屏内容
- 投屏接口：整帧图像（image/rgb888/pixels/原始字节流）、文本、清屏、切页、窗口投屏；可配置端口与访问令牌
- 提供 OpenAPI 3.0 JSON 规范（/api/openapi.json），启动自动生成 api_openapi.json，并自动校验端点与文档同步
- 网页投屏控制台（分页标签：投屏/选择程序/文档）：文本、图片（单张/多图轮播+间隔）、选择程序窗口投屏、停止投屏
- 多屏投屏：各接口支持 device 参数指定目标屏，每屏独立显示；新增 /api/devices 列出多屏
- 图片投屏显示方式：自适应(contain)/拉伸(stretch)/填充(cover)

v4.5.10 (2026-08-15)
- 配色方案改为独立标签页（设置 → 配色方案），放在「监控显示」之前，入口更显眼
- 配色方案交互升级：选择方案只提供候选色板，不再自动套用；每个颜色位置后新增「色块下拉」，可直接看到并挑选该方案的颜色
- 支持混合配色：不同位置可分别从不同方案的色板选色，点「存为新方案」把当前组合一键保存为自定义方案

v4.5.9 (2026-08-15)
- 新增「配色方案」系统：内置 260+ 个色系（马卡龙/莫兰迪/美拉德/赛博朋克/侘寂/大地/孟菲斯/极简/复古/霓虹/传统国色/艺术流派/色彩理论等）
- 配色方案管理：新增「监控显示 → 配色方案」子页，实时预览色块，可新增/编辑/删除自定义方案（按设备保存）
- 一键套用：网络流量、磁盘读写（经典模式/网速样式）、仪表盘设置区新增「配色方案」下拉，选择后按顺序套用到各颜色

v4.5.8 (2026-08-15)
- 磁盘读写设置改成分页标签管理（经典模式/经典2样式/网速样式），避免界面过高，切换显示模式自动跳转对应标签
- 经典2样式颜色改为跟随网络流量页面当前配色（经典=通用文字颜色+默认柱色；自定义=独立配色），无需单独配置

v4.5.7 (2026-08-15)
- 网络流量监控：上传/下载文字颜色、柱状图颜色全部可自定义
- 网络流量监控：新增「经典/自定义」显示模式（经典=原样式，自定义=独立配色）
- 磁盘读写：新增「经典2」样式，布局与字体大小和网络流量一致（读/写标签），颜色可自定义
- 磁盘读写：网速样式新增独立的读/写数值颜色设置，所有文字与柱状图颜色均可自定义
- 修复：启动/切换设备后，页面、显示方向下拉框自动恢复为该设备上次的选择
- 设置「按页面」导航记住上次选择的页面，重启后恢复

v4.5.6 (2026-08-14)
- 新增「设备信息」标签页：USB连接信息 / 固件版本 / SFR寄存器 / Flash芯片与分区 / 本机系统信息
- 修复中文字体显示：simhei.ttf 自动回退到 resource/，跑马灯/时钟等中文不再变方块
- 跑马灯字体固定为黑体(移除字体选择，避免字体路径失效)，字号/颜色/速度/文本仍可调
- 编译脚本加入 winsdk(播放音乐) 与 device_protocol.json

v4.5.4 (2026-08-14)
- 热搜独立设置：独立分页(每页条数/抓取总条数/字体/翻页间隔/自动刷新)
- 热搜字体自动适配屏幕大小(按最长文本缩小字号，最小8)；长文本滚动字幕，滚动速度可调
- 热搜/跑马灯居中布局；字体/尺寸/速度等调整后小屏实时同步生效
- 文字跑马灯新增滚动速度设置(marquee_speed)
- 所有设置更改后实时生效：天气城市/行情交易对/延迟目标改动后立即刷新数据并重绘，不再等待缓存刷新

v4.5.1 (2026-08-13)
- 多屏独立配置：每个屏幕按 USB 序列号(serial_number)独立保存设置(MSU2_MINI_<serial>.json)
- 多设备 SN 相同时按 COM 端口区分保存；SN 为空也按端口区分
- 兜底方案：配置文件唯一性强制校验(绝不共用文件) + 原子写入(临时文件+替换，防崩溃损坏)
- 配置文件集中保存到程序目录 config/ 子目录，旧配置自动迁移(保留根目录原件备份)
- 修复多屏只识别1个：daemon端口遍历时实时更新连接状态，各屏独立创建/独立线程
- 修复多屏页面/方向/设置联动：所有UI操作锁定到当前选中设备，互不干扰
- 传感器自由选择：硬件详情/仪表盘可勾选/指定任意 LibreHardwareMonitor 传感器
- 传感器按 HardwareType 类型枚举区分 CPU/GPU，无数据时显示 --(非0误导)
- 设备掉线自动重连(清除known_com_ports)、LCD指令失败容错重试、重连复用设备
- 串口写超时容错重试；清理 isSet() 弃用警告
- 修复多屏下网络速率/硬件详情等页面首次渲染崩溃

v4.3.1 (2026-08-13)
- 新增多线程处理：窗口枚举后台加载+缓存、UI消息线程安全、避免启动与运行时卡顿
- 新增大量显示页面：文字跑马灯、磁盘速率、网络延迟、进程TOP、番茄钟、纪念日、待办、世界时钟、农历、仪表盘、硬件详情、天气、行情、热搜、电池、音乐
- 自定义显示：新增矩形/线条/圆/动图命令，图形化编辑器+模板预设库+模板导入导出
- 镜像增强：局部放大（跟随鼠标）、设置页多标签页管理
- 通用增强：崩溃日志、命令行参数(--page/--com)、开机自启动、配置导入导出、自动翻页、息屏待机、按键自定义、自动更新检查、多语言(页面/方向名称中英)
- 修复屏幕镜像倾斜（RGB565打包uint16溢出、PAGE_ID清空）等问题

v3.1.4 (2026-08-13)
- 修复启动时屏幕镜像首帧倾斜的问题：设备标记"已连接"的时机过早，
  导致截图线程与LCD检测/ADC阈值读取/方向重置并发交错，现已推迟到全部初始化完成之后
- 修复窗口最小化时"窗口不可见"日志刷屏，改为每5秒最多打印一次
- 修复PrintWindow/DC初始化失败(窗口正在关闭、句柄失效)未回退到mss截图，
  导致"object is not a PyCDC"异常刷屏的问题
- 统一截图线程为幂等启动，消除UI与daemon重复启动线程的竞态
- 移除USB描述符诊断中误导性的"设备指纹"判断输出

v3.1.3 (2026-08-13)
- 修复ADC心跳读取失败误判断开导致帧写入被截断→画面倾斜的问题
- SER_Read改为定时等待，给设备渲染完成留出响应时间
- 限制按键ADC轮询频率，避免与屏幕镜像帧发送争抢串口带宽
- 串口写入前复查端口状态，防止并发关闭导致写入失败
- 修复退出时线程未结束就关闭串口的竞态(消除退出时的误报)

v3.1.2 (2026-08-13)
- 修复频繁切换页面/窗口/方向后小屏画面倾斜(斜切)的问题
- 串口大块数据改为分块写入并逐块校验完整性，避免单次write超时导致命令流截断
- 大块数据发送后排空USB适配器缓冲，避免下一条命令与末尾字节交错
- 切换时彻底重置截图流水线(清空队列+丢弃在途帧)，只发送最新帧
- LCD方向重置清屏改用设备实际分辨率(修复240x240等设备清错区域)

v2.0.0 (2026-08-11)
- 正式发布USB小屏幕助手v2.0.0版本
- 整合 dimangopie/just-fun-for-MSU2_MINI (MIT) 与 dchg43/msu2_mini (MIT)
- 支持动图、时钟、相册、屏幕镜像、相机视频、系统监控、网络监控等功能
- 支持自定义显示内容（MiniMark模板引擎）
- 支持LCD屏幕分辨率自动检测
- 支持托盘图标隐藏
- 采用MIT开源协议发布
"""

def get_program_info():
    """获取程序完整信息字符串"""
    return (
        f"{PROGRAM_TITLE} v{PROGRAM_VERSION}\n"
        f"{PROGRAM_SUBTITLE}\n"
        f"作者: {PROGRAM_AUTHOR}\n"
        f"项目地址: {PROGRAM_GITHUB}\n"
        f"许可证: {PROGRAM_LICENSE}\n"
        f"构建日期: {PROGRAM_BUILD_DATE}"
    )

def get_about_lines():
    """获取关于页面的文本行（用于LCD屏幕显示）"""
    lines = [
        f"{PROGRAM_TITLE} v{PROGRAM_VERSION}",
        f"{PROGRAM_AUTHOR}  {PROGRAM_LICENSE}",
        PROGRAM_GITHUB.replace("https://github.com/", ""),
        "",
        "整合自(MIT):",
    ]
    for proj in PROGRAM_SOURCE_PROJECTS:
        lines.append(f"{proj['author']}/{proj['name']}")
    return lines


# ==================== 内联 MiniMark 模块 ====================
# 原文件: MSU2_MINI_MG_minimark.py

# Font cache
_font_cache = {}
# Image cache
_image_cache = {}
# GIF cache（保持打开状态以便 seek 选帧）
_gif_cache = {}


# 优先尝试启动路径，也就是资源文件可以在启动路径修改
def _get_resource(relative_path):
    base_path = os.path.dirname(os.path.realpath(sys.argv[0]))  # 启动路径
    path = os.path.normpath(os.path.join(base_path, relative_path))
    if os.path.isfile(path):
        return path
    # 找不到时，若路径不带 resource/ 前缀，自动回退到 resource/ 子目录查找
    # （例如 ./simhei.ttf -> resource/simhei.ttf），兼容打包后资源集中存放
    rel = relative_path.replace("\\", "/").lstrip("./")
    if rel and not rel.lower().startswith("resource/"):
        candidate = os.path.normpath(os.path.join(base_path, "resource", rel))
        if os.path.isfile(candidate):
            return candidate
    base_path = getattr(sys, "_MEIPASS", None)  # pyinstaller打包后的路径
    if base_path is None:
        base_path = os.path.dirname(__file__)  # py文件路径
    return os.path.normpath(os.path.join(base_path, relative_path))


def _load_font(font_name, font_size):
    key = (font_name, font_size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(_get_resource(font_name), font_size)
        except (OSError, ValueError) as e:
            try:
                _font_cache[key] = ImageFont.truetype(_get_resource("./simhei.ttf"), font_size)
            except (OSError, ValueError) as e2:
                print("Warning: font %s load failed, %s:%s" % (key, type(e2), e2))
                _font_cache[key] = ImageFont.load_default(font_size)
    return _font_cache[key]


def _load_image(image_path):
    if image_path not in _image_cache:
        image = None
        try:
            image = Image.open(_get_resource(image_path))
            _image_cache[image_path] = image.convert("RGBA")
        except FileNotFoundError as e:
            print("Warning: image %s load failed: %s" % (image_path, e))
            image_default = "default"
            if image_default not in _image_cache:
                _image_cache[image_default] = Image.new("RGBA", (16, 16), (255, 0, 255))
            return _image_cache[image_default]
        finally:
            if image is not None:
                image.close()
    return _image_cache[image_path]


class MiniMark:
    """MiniMark 模块命名空间，提供 load_font 和 load_image 静态方法"""

    @staticmethod
    def load_font(font_name, font_size):
        return _load_font(font_name, font_size)

    @staticmethod
    def load_image(image_path):
        return _load_image(image_path)


class MiniMarkParser:
    """MiniMark 解析器，原 MSU2_MINI_MG_minimark.py"""

    def __init__(self):
        self.anchor = None
        self.color = None
        self.font = None
        self.position = None
        self.reset_state()

    def reset_state(self):
        self.position = (0, 0)
        self.font = _load_font("./simhei.ttf", 20)
        self.color = (0, 0, 0)
        self.anchor = "la"

    def parse_line(self, line, draw, img, record_dict=None, frame_time=None):
        parts = line.split()
        if len(parts) == 0:
            return
        command = parts[0]

        if command == 'a':
            self.anchor = parts[1]

        elif command == 'p':
            text = ' '.join(parts[1:])
            draw.text(self.position, text, fill=self.color, font=self.font, anchor=self.anchor)
            text_width = round(draw.textlength(text, font=self.font))
            if "l" in self.anchor:
                self.position = (self.position[0] + text_width, self.position[1])
            if "r" in self.anchor:
                self.position = (self.position[0] - text_width, self.position[1])

        elif command == 'm':
            x, y = map(int, parts[1:3])
            self.position = (x, y)

        elif command == 't':
            dx, dy = map(int, parts[1:3])
            self.position = (self.position[0] + dx, self.position[1] + dy)

        elif command == 'f':
            if len(parts) > 3:
                font_name = line[line.index(parts[0]) + 1:line.rindex(parts[-1])].strip()
                font_size = int(parts[-1])
            else:
                font_name = parts[1]
                font_size = int(parts[2])
            self.font = _load_font(font_name, font_size)

        elif command == 'c':
            hex_color = parts[1].lstrip('#')
            self.color = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        elif command == 'i':
            if len(parts) > 2:
                image_path = line[line.index(parts[0]) + 1:].strip()
            else:
                image_path = parts[1]
            image = _load_image(image_path)
            img.paste(image, self.position, image)

        elif command == 'r':
            x1, y1, x2, y2 = map(int, parts[1:5])
            draw.rectangle([x1, y1, x2, y2], fill=self.color)

        elif command == 'l':
            x1, y1, x2, y2 = map(int, parts[1:5])
            draw.line([x1, y1, x2, y2], fill=self.color, width=1)

        elif command == 'o':
            x, y, r = map(int, parts[1:4])
            draw.ellipse([x - r, y - r, x + r, y + r], fill=self.color)

        elif command == 'g':
            # 动图：根据当前时间选帧（默认约10帧/秒）
            image_path = line[line.index(parts[0]) + 1:].strip() if len(parts) > 1 else ""
            if image_path:
                path = _get_resource(image_path)
                if path not in _gif_cache:
                    try:
                        _gif_cache[path] = Image.open(path)
                    except Exception as e:
                        print("gif load failed: %s" % e)
                        _gif_cache[path] = None
                gif = _gif_cache[path]
                if gif is not None:
                    try:
                        n = max(1, gif.n_frames)
                        idx = int(frame_time * 10) % n if frame_time is not None else 0
                        gif.seek(idx)
                        frame = gif.convert("RGBA")
                        img.paste(frame, self.position, frame)
                    except Exception as e:
                        print("gif frame error: %s" % e)

        elif command == 'v' and record_dict is not None:
            key = parts[1]
            pairs = record_dict.get(key, None)
            if pairs is None:
                text = "<%s>" % key
            elif len(parts) <= 2:
                text = pairs[0]
            elif pairs[1] is None:
                text = "<%s>" % key
            else:
                formatting = parts[2]
                text = formatting.format(pairs[1])
            draw.text(self.position, text, fill=self.color, font=self.font, anchor=self.anchor)
            text_width = round(draw.textlength(text, font=self.font))
            if "l" in self.anchor:
                self.position = (self.position[0] + text_width, self.position[1])
            if "r" in self.anchor:
                self.position = (self.position[0] - text_width, self.position[1])

    def parse(self, size, lines, record_dict=None, frame_time=None):
        img = Image.new("RGBA", size, color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for line in lines:
            self.parse_line(line, draw, img, record_dict, frame_time)
        return img


# ==================== 内联 ContinuousCapture 模块 ====================
# 原文件: ContinuousCapture.py

class ContinuousCapture:
    def __init__(self, hwnd=None):
        """
        初始化连续截图器
        """
        self.print_mode = 0b11  # 用于设置截屏时是否包含标题栏和工具栏，包含0b10，不包含0b11
        self.hwnd = hwnd

        # 获取窗口尺寸
        self.width, self.height = self.getRect()
        self.dpi_width, self.dpi_height = self.width, self.height

        # 设备上下文和位图对象（将在setup_resources中初始化）
        self.hwndDC = None
        self.mfcDC = None
        self.saveDC = None
        self.saveBitMap = None

        if self.hwnd:
            # 仅在提供了有效窗口句柄时才初始化GDI资源
            self.setup_resources()

    def set_hwnd(self, hwnd):
        if self.hwnd != hwnd:
            self.cleanup_resources()
            self.hwnd = hwnd
            self.width, self.height = self.getRect()
            self.setup_resources()

    def setup_resources(self):
        """ 初始化截图所需的资源 """
        self.dpi_width, self.dpi_height = self.getDpiRect()

        # 获取窗口设备上下文
        self.hwndDC = win32gui.GetWindowDC(self.hwnd)
        self.mfcDC = win32ui.CreateDCFromHandle(self.hwndDC)
        self.saveDC = self.mfcDC.CreateCompatibleDC()

        # 创建位图对象
        self.saveBitMap = win32ui.CreateBitmap()
        self.saveBitMap.CreateCompatibleBitmap(self.mfcDC, self.dpi_width, self.dpi_height)

        # 将位图选入设备上下文
        self.saveDC.SelectObject(self.saveBitMap)

    def getRect(self):
        if not self.hwnd:
            return 0, 0
        if self.print_mode == 0b10:
            # 0b10：获取窗口位置和大小，包含标题栏和工具栏
            get_rect = win32gui.GetWindowRect(self.hwnd)
        else:
            # 0b11：获取窗口大小，不包含标题栏和工具栏
            get_rect = win32gui.GetClientRect(self.hwnd)
        width = get_rect[2] - get_rect[0]
        height = get_rect[3] - get_rect[1]
        return width, height

    def getDpiRect(self):
        """ 根据dpi获取窗口实际大小 """
        if self.hwnd == win32gui.GetDesktopWindow():
            try:
                hdc = win32gui.GetDC(self.hwnd)
                app_width = win32ui.GetDeviceCaps(hdc, win32con.HORZRES)
                sys_width = win32ui.GetDeviceCaps(hdc, win32con.DESKTOPHORZRES)
                dpi = sys_width / app_width
            except:
                dpi = 1.0
            finally:
                win32gui.ReleaseDC(self.hwnd, hdc)
        else:
            app_dpi = windll.user32.GetDpiForWindow(self.hwnd)
            dpi = app_dpi / system_dpi
        return int(self.width * dpi), int(self.height * dpi)

    @staticmethod
    def find_window_by_title(window_title):
        """根据窗口标题查找窗口句柄"""
        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd) and window_title in win32gui.GetWindowText(hwnd):
                hwnds.append(hwnd)
                return False
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds[0] if hwnds else None

    def capture_window(self):
        """截取单个窗口"""
        new_width, new_height = self.getRect()
        if new_width != self.width or new_height != self.height:
            self.cleanup_resources()
            self.width = new_width
            self.height = new_height
            self.setup_resources()

        # 后台窗口使用PrintWindow代替BitBlt解决部分窗口黑屏问题
        windll.user32.PrintWindow(self.hwnd, self.saveDC.GetSafeHdc(), self.print_mode)

        bmpinfo = self.saveBitMap.GetInfo()
        bmpstr = self.saveBitMap.GetBitmapBits(True)
        # 返回DPI缩放后的实际位图尺寸，确保下游数据长度计算正确
        return bmpstr, bmpinfo['bmWidth'], bmpinfo['bmHeight']

    def get_actual_size(self):
        """获取DPI缩放后的实际位图尺寸（用于下游校验数据长度）"""
        return self.dpi_width, self.dpi_height

    def capture_screen(self):
        """截取整个屏幕（BitBlt方式，桌面专用备选）"""
        new_width, new_height = self.getRect()
        if new_width != self.width or new_height != self.height:
            self.cleanup_resources()
            self.width = new_width
            self.height = new_height
            self.setup_resources()

        try:
            self.saveDC.BitBlt((0, 0), (self.dpi_width, self.dpi_height), self.mfcDC, (0, 0), win32con.SRCCOPY)
        except:
            pass

        bmpinfo = self.saveBitMap.GetInfo()
        bmpstr = self.saveBitMap.GetBitmapBits(True)
        return bmpstr, bmpinfo['bmWidth'], bmpinfo['bmHeight']

    def cleanup_resources(self):
        """清理资源"""
        try:
            if self.saveBitMap:
                win32gui.DeleteObject(self.saveBitMap.GetHandle())
                self.saveBitMap = None
            if self.saveDC:
                self.saveDC.DeleteDC()
                self.saveDC = None
            if self.mfcDC:
                self.mfcDC.DeleteDC()
                self.mfcDC = None
            if self.hwndDC:
                win32gui.ReleaseDC(self.hwnd, self.hwndDC)
                self.hwndDC = None
        except:
            pass


SHOW_WIDTH = 160  # 画布宽度
SHOW_HEIGHT = 80  # 画布高度

# 小屏幕分辨率变量（可通过自动检测更新）
LCD_MAX_X = SHOW_WIDTH   # LCD最大宽度
LCD_MAX_Y = SHOW_HEIGHT  # LCD最大高度

GIF_PAGE_ID = 0
PCTIME_PAGE_ID = 1
PHOTO_PAGE_ID = 2
SCREEN_PAGE_ID = 3
CAMERA_VIDEO_ID = 4
STATE_PAGE_ID = 5
NETSPEED_PAGE_ID = 6
CUSTOM1_PAGE_ID = 7
CUSTOM2_PAGE_ID = 8
ABOUT_PAGE_ID = 9
MARQUEE_PAGE_ID = 10  # 文字跑马灯
DISKIO_PAGE_ID = 11   # 磁盘读写速率
PING_PAGE_ID = 12     # 网络延迟
PROC_PAGE_ID = 13     # 进程占用TOP
TIMER_PAGE_ID = 14    # 番茄钟/倒计时
MEMO_PAGE_ID = 15     # 纪念日
TODO_PAGE_ID = 16     # 待办事项
WORLDCLOCK_PAGE_ID = 17  # 世界时钟
LUNAR_PAGE_ID = 18    # 农历日期
GAUGE_PAGE_ID = 19    # 仪表盘
HWDETAIL_PAGE_ID = 20  # 硬件详情
WEATHER_PAGE_ID = 21   # 天气
CRYPTO_PAGE_ID = 22    # 行情
HOTSEARCH_PAGE_ID = 23  # 热搜
BATTERY_PAGE_ID = 24   # 电池
MUSIC_PAGE_ID = 25     # 音乐
API_PAGE_ID = 26       # API 投屏
PAGE_ID = {
    GIF_PAGE_ID: "动图",
    PCTIME_PAGE_ID: "时间",
    PHOTO_PAGE_ID: "单个相册图片",
    SCREEN_PAGE_ID: "屏幕镜像",
    STATE_PAGE_ID: "电脑CPU/内存/磁盘/电池使用率监控",
    NETSPEED_PAGE_ID: "网络流量监控",
    ABOUT_PAGE_ID: "关于",
    MARQUEE_PAGE_ID: "文字跑马灯",
    DISKIO_PAGE_ID: "磁盘读写速率",
    PING_PAGE_ID: "网络延迟",
    PROC_PAGE_ID: "进程占用TOP",
    TIMER_PAGE_ID: "番茄钟",
    MEMO_PAGE_ID: "纪念日",
    TODO_PAGE_ID: "待办事项",
    WORLDCLOCK_PAGE_ID: "世界时钟",
    LUNAR_PAGE_ID: "农历日期",
    GAUGE_PAGE_ID: "仪表盘",
    HWDETAIL_PAGE_ID: "硬件详情",
    WEATHER_PAGE_ID: "天气",
    CRYPTO_PAGE_ID: "行情",
    HOTSEARCH_PAGE_ID: "热搜",
    BATTERY_PAGE_ID: "电池",
    MUSIC_PAGE_ID: "音乐",
    API_PAGE_ID: "API投屏",
}

# 多语言：页面名称中英映射
PAGE_ID_CN = dict(PAGE_ID)
PAGE_ID_CN.update({
    CAMERA_VIDEO_ID: "相机视频",
    CUSTOM1_PAGE_ID: "自定义显示两项图表",
    CUSTOM2_PAGE_ID: "自定义显示多项数值",
})
PAGE_ID_EN = {
    GIF_PAGE_ID: "GIF",
    PCTIME_PAGE_ID: "Clock",
    PHOTO_PAGE_ID: "Photo",
    SCREEN_PAGE_ID: "Screen Mirror",
    CAMERA_VIDEO_ID: "Camera",
    STATE_PAGE_ID: "System Monitor",
    NETSPEED_PAGE_ID: "Network",
    CUSTOM1_PAGE_ID: "Custom Chart",
    CUSTOM2_PAGE_ID: "Custom Values",
    ABOUT_PAGE_ID: "About",
    MARQUEE_PAGE_ID: "Marquee",
    DISKIO_PAGE_ID: "Disk IO",
    PING_PAGE_ID: "Ping",
    PROC_PAGE_ID: "Process TOP",
    TIMER_PAGE_ID: "Pomodoro",
    MEMO_PAGE_ID: "Anniversary",
    TODO_PAGE_ID: "To-Do",
    WORLDCLOCK_PAGE_ID: "World Clock",
    LUNAR_PAGE_ID: "Lunar",
    GAUGE_PAGE_ID: "Gauge",
    HWDETAIL_PAGE_ID: "Hardware",
    WEATHER_PAGE_ID: "Weather",
    CRYPTO_PAGE_ID: "Crypto",
    HOTSEARCH_PAGE_ID: "Hot Search",
    BATTERY_PAGE_ID: "Battery",
    MUSIC_PAGE_ID: "Music",
    API_PAGE_ID: "API Screen",
}

LCD_STATE_MESSAGE = [
    "正向 (0°)",
    "反向 (180°)",
    "水平镜像",
    "垂直镜像",
    "顺时针90°",
    "逆时针90°",
    "水平镜像+90°",
    "垂直镜像+90°",
]
LCD_STATE_MESSAGE_CN = list(LCD_STATE_MESSAGE)
LCD_STATE_MESSAGE_EN = [
    "Normal (0°)",
    "Reverse (180°)",
    "H-Mirror",
    "V-Mirror",
    "CW 90°",
    "CCW 90°",
    "H-Mirror+90°",
    "V-Mirror+90°",
]

IMAGE_FILE_TYPES = [
    ("Image file", "*.jpg"),
    ("Image file", "*.jpeg"),
    ("Image file", "*.png"),
    ("Image file", "*.bmp"),
    ("Image file", "*.ico"),
    ("Image file", "*.webp"),
    ("Image file", "*.jfif"),
    ("Image file", "*.jpe"),
    ("Image file", "*.tiff"),
    ("Image file", "*.tif"),
    ("Image file", "*.dib"),
    ("Image file", "*.pcx"),
    ("Image file", "*.tga"),
    ("Image file", "*.dds"),
    ("Image file", "*.psd"),
    # ("Image file", "*.pcl"), # 不支持
    # ("Image file", "*.svg"), # 不支持
    # ("Image file", "*.eps"), # 不支持
    # ("Image file", "*.jxr"), # 不支持
    # ("Image file", "*.heic"),  # 不支持
    # ("Image file", "*.heif"), # 不支持
    # ("Image file", "*.heics"), # 不支持
    # ("Image file", "*.heifs"), # 不支持
    # ("Image file", "*.avci"), # 不确定
    # ("Image file", "*.avcs"), # 不确定
    # ("Image file", "*.avif"), # 不支持
    # ("Image file", "*.avifs"), # 不确定
    # ("Image file", "*.wdp") # 不支持
]

# ==================== 多设备支持基础设施 ====================
# 当前活跃设备上下文（线程本地存储），串口/LCD函数自动使用当前线程绑定的设备
_device_context = threading.local()
# 所有已连接设备的字典 {device_id: ScreenDevice}
all_devices = {}
# 主设备（单屏模式下的默认设备，向后兼容）
_primary_device = None


def get_current_device():
    """获取当前线程活跃的ScreenDevice，无则返回主设备"""
    dev = getattr(_device_context, 'device', None)
    if dev is not None:
        return dev
    return _primary_device


def set_current_device(device):
    """设置当前线程活跃的ScreenDevice"""
    _device_context.device = device


class ScreenDevice:
    """单个USB副屏设备的完整上下文（状态、串口、线程、配置）"""
    def __init__(self, index, com_port):
        self.index = index              # 设备序号 0, 1, 2...
        self.com_port = com_port        # COM端口号，如 "COM15"
        self.device_name = f"屏幕{index + 1}" if index > 0 else "屏幕1"
        
        # --- 串口 ---
        self.ser = None
        self.SER_lock = threading.Lock()
        
        # --- 设备状态 ---
        self.device_state = 0           # 0=未连接, 1=已连接
        self.state_change = 1           # 状态变化标志
        self.lcd_change_now = 0         # 当前LCD方向
        self.force_lcd_reset = False    # 强制LCD方向重置
        self.last_lcd_watchdog_time = 0 # LCD看门狗计时
        
        # --- 状态机 ---
        self.state_machine = SCREEN_PAGE_ID  # 当前页面
        self.serial_busy = False  # 帧/页面渲染串口发送中标志（供按键线程避让，防命令流交错导致画面倾斜）
        
        # --- 截图流水线 ---
        self.screen_shot_queue = queue.Queue(2)
        self.screen_process_queue = queue.Queue(2)
        self.screen_shot_thread = None
        self.screen_process_thread = None
        self.mg_screen_thread_running = True
        self.screen_frame_generation = 0
        self.default_capture = None     # ContinuousCapture实例
        self.screenshot_last_limit_time = 0
        self.wait_time = 0.0
        self.row_np_zero = None
        self.column_np_zero = None
        
        # --- 渲染状态 ---
        self.color_use = RED
        self.gif_num = 0
        self.second_pass = 0
        self.gif_wait_time = 0.0
        self.last_refresh_time = 0
        self.sleep_event = threading.Event()
        
        # --- 防烧屏 ---
        self.burn_offset_x = 0
        self.burn_offset_y = 0
        self.burn_offset_time = 0
        
        # --- 网络/自定义/磁盘图表数据 ---
        self.netspeed_last_refresh_snetio = None
        self.netspeed_plot_data = None
        self.custom_plot_data = None
        self.diskio_plot_data = None
        self.last_data_half = (0, 0)
        
        # --- MSN设备信息 ---
        self.msn_device = None
        self.msn_data = None
        self.ADC_det = 0
        self.adc_fail_count = 0  # ADC读取连续失败计数

        # --- 设备硬件/固件信息（连接时采集缓存，供“设备信息”标签页展示） ---
        self.usb_info = {}           # USB描述符信息（端口/VID/PID/SN/制造商/产品/位置等）
        self.firmware_version = 0    # 固件版本（握手 \x00MSN+版本号 解析）
        
        # --- 自定义渲染锁 ---
        self.custom_render_lock = threading.Lock()
        self.last_preview_rgb = None   # 最近一帧预览图像（per-device）
        self._preview_lock = threading.Lock()  # 预览读写锁

        # --- 独立配置（按 serial_number 唯一识别码保存） ---
        self.serial_number = ""   # USB设备序列号（唯一识别码）
        self.config = None        # 本屏独立配置对象
        self.config_file = None   # 本屏配置文件路径
        
        # --- LCD分辨率 ---
        self.LCD_MAX_X = SHOW_WIDTH
        self.LCD_MAX_Y = SHOW_HEIGHT
    
    def init_arrays(self):
        """初始化numpy零数组（依赖LCD尺寸）"""
        if self.row_np_zero is None:
            self.row_np_zero = np.zeros([1, self.LCD_MAX_X, 3], dtype=np.uint8)
            self.column_np_zero = np.zeros([self.LCD_MAX_Y, 1, 3], dtype=np.uint8)
        if self.netspeed_plot_data is None:
            self.netspeed_plot_data = {"sent": [0] * (self.LCD_MAX_X // 2),
                                       "recv": [0] * (self.LCD_MAX_X // 2)}
        if self.diskio_plot_data is None:
            self.diskio_plot_data = {"read": [0] * (self.LCD_MAX_X // 2),
                                     "write": [0] * (self.LCD_MAX_X // 2)}
        if self.netspeed_last_refresh_snetio is None:
            try:
                self.netspeed_last_refresh_snetio = psutil.net_io_counters()
            except Exception:
                self.netspeed_last_refresh_snetio = None
            self.custom_plot_data = {"sent": [0] * (self.LCD_MAX_X // 2),
                                     "recv": [0] * (self.LCD_MAX_X // 2)}

    def set_device_state(self, state):
        """设置设备连接状态"""
        if self.device_state != state:
            self.device_state = state
            if state == 0 and self.ser is not None and self.ser.is_open:
                try:
                    self.ser.close()
                except:
                    pass
    
    def start_threads(self):
        """启动截图和daemon线程（幂等：线程已在运行时不会重复启动）"""
        self.mg_screen_thread_running = True
        if self.screen_shot_thread is None or not self.screen_shot_thread.is_alive():
            self.screen_shot_thread = threading.Thread(
                target=screen_shot_task, args=(self,), daemon=True)
            self.screen_shot_thread.start()
        if self.screen_process_thread is None or not self.screen_process_thread.is_alive():
            self.screen_process_thread = threading.Thread(
                target=screen_process_task, args=(self,), daemon=True)
            self.screen_process_thread.start()
    
    def stop_threads(self):
        """停止所有线程"""
        self.mg_screen_thread_running = False
        self.sleep_event.set()

    def cleanup(self):
        """清理LCD并关闭串口"""
        try:
            if self.device_state == 1:
                print(f'{self.device_name}: 正在清除LCD屏幕...')
                set_current_device(self)
                LCD_Color_set(0, 0, self.LCD_MAX_X, self.LCD_MAX_Y, BLACK)
                time.sleep(0.1)
        except:
            pass
        finally:
            if self.ser is not None and self.ser.is_open:
                print(f'{self.device_name}: {self.ser.name} close')
                self.ser.close()


def _init_single_device():
    """初始化主设备（单屏兼容模式）"""
    global _primary_device
    if _primary_device is None:
        _primary_device = ScreenDevice(0, "")
        all_devices[0] = _primary_device


def get_all_cameras():
    all_camera_devices = {"": None}  # 考虑隐私，默认不打开相机，所以这里放一个空的作为默认值
    try:
        camera_devices = camera_device.list_video_devices()
        for camera_id, camera_name in camera_devices:
            if camera_name in all_camera_devices.keys():
                all_camera_devices["%s%s" % (camera_name, camera_id)] = camera_id
            else:
                all_camera_devices[camera_name] = camera_id
    except Exception as e:
        print(e)
    return all_camera_devices


_windows_cache = {"data": None, "time": 0.0}  # 窗口列表缓存，2秒内复用，避免反复枚举造成卡顿


def get_all_windows():
    global desktop_hwnd
    now_cache = time.monotonic()
    if _windows_cache["data"] is not None and now_cache - _windows_cache["time"] < 2.0:
        return _windows_cache["data"]

    def get_process_name(hwnd):
        try:
            _, procpid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(procpid).name()
        except:
            return hwnd

    def add_dict(dicts, hwnd, title, parent):
        if len(title) > 100:
            title = title[:100] + ' …'
        # key需要包含hwnd，否则可能因key重复被覆盖
        dicts["[%s] - %s (%s)" % (get_process_name(hwnd), title, hwnd)] = (hwnd, parent)

    def children(hwnd, parent_hwnd, param):
        window_class = win32gui.GetClassName(hwnd)
        window_title = win32gui.GetWindowText(hwnd)
        if window_class == "TrayClockWClass":  # 系统时钟
            # or window_title == "Game Bar":  # Xbox Game Bar
            add_dict(param, hwnd, window_title, parent_hwnd)
        return True

    def get_children_windows(parent, parent_hwnd):
        hwndChildList = dict()
        win32gui.EnumChildWindows(
            parent, lambda hwnd, param: children(hwnd, parent_hwnd, param), hwndChildList)
        return hwndChildList

    def get_all_hwnd(hwnd, hwnd_title):
        if win32gui.IsWindowVisible(hwnd):
            window_class = win32gui.GetClassName(hwnd)
            window_title = win32gui.GetWindowText(hwnd)
            if window_title:  # 普通窗口
                # and window_class != "Windows.UI.Core.CoreWindow"
                # and window_class != "Internet Explorer_Hidden"
                parent = win32gui.GetParent(hwnd)
                add_dict(hwnd_title, hwnd, window_title, parent)
            elif window_class == "Shell_TrayWnd":  # 任务栏
                hwnd_title.update(get_children_windows(hwnd, 0))
        return True

    hwnd_titles = dict()
    try:
        # 添加桌面
        desktop_hwnd = win32gui.GetDesktopWindow()
        hwnd_titles["[%s] - 桌面" % desktop_hwnd] = (desktop_hwnd, 0)

        # 遍历其他所有窗口
        win32gui.EnumWindows(get_all_hwnd, hwnd_titles)

        # 添加各个显示器屏幕（多屏支持）
        try:
            with mss() as sct:
                for i, monitor in enumerate(sct.monitors):
                    if i == 0:
                        continue  # 跳过完整桌面（已添加）
                    monitor_key = "屏幕 %d - %dx%d" % (i, monitor['width'], monitor['height'])
                    hwnd_titles[monitor_key] = (-i, 0)  # 负值表示显示器编号
        except Exception:
            pass

        # 添加特殊窗口
        # hwnd_titles.update(get_children_windows(desktop_hwnd, desktop_hwnd))
    except Exception as e:
        print(e)
        hwnd_titles = {"": (0, 0)}

    _windows_cache["data"] = hwnd_titles
    _windows_cache["time"] = time.monotonic()
    return hwnd_titles


class Win32_Image:
    def __init__(self, rgb=None, bgra=None, size=(0, 0)):
        self.rgb = rgb
        self.bgra = bgra
        self.size = size


default_capture = None
mss_sct = None  # 旧全局（向后兼容），实际使用device.mss_sct
printwindow_fail_count = 0  # PrintWindow连续失败计数
printwindow_fail_hwnd = 0   # 当前失败对应的窗口句柄
MSS_FALLBACK_THRESHOLD = 3  # 连续失败N次后切换到mss区域截图
MIN_WINDOW_SIZE = 10        # 窗口最小尺寸（像素），小于此值不尝试PrintWindow
last_invisible_print_time = 0  # "窗口不可见"日志节流时间戳


def _mss_fallback_screenshot(hWnd=None):
    """使用mss截取桌面（或指定窗口区域）作为回退方案"""
    # mss GDI句柄是线程本地的，每次调用创建新实例(轻量)
    sct = mss()
    if hWnd and hWnd != desktop_hwnd:
        try:
            rect = win32gui.GetWindowRect(hWnd)
            left, top, right, bottom = rect
            w, h = right - left, bottom - top
            if w >= MIN_WINDOW_SIZE and h >= MIN_WINDOW_SIZE:
                monitor = {"left": left, "top": top, "width": w, "height": h, "mon": 0}
                sct_img = sct.grab(monitor)
                return Win32_Image(rgb=sct_img.rgb, size=(sct_img.width, sct_img.height))
        except Exception:
            pass
    monitor = sct.monitors[0]
    sct_img = sct.grab(monitor)
    return Win32_Image(rgb=sct_img.rgb, size=(sct_img.width, sct_img.height))


def get_window_image(hWnd=None):
    global desktop_hwnd
    global printwindow_fail_count, printwindow_fail_hwnd
    global last_invisible_print_time

    if hWnd is not None and hWnd < 0:
        monitor_index = -hWnd
        sct = mss()  # mss GDI句柄是线程本地的
        if monitor_index < len(sct.monitors):
            monitor = sct.monitors[monitor_index]
            sct_img = sct.grab(monitor)
            return Win32_Image(rgb=sct_img.rgb, size=(sct_img.width, sct_img.height))
        hWnd = desktop_hwnd
        set_select_hwnd(hWnd)

    while not win32gui.IsWindow(hWnd):  # 只需要窗口在，不需要可见，比如最小化或者隐藏到任务栏
        hWnd = get_parent(hWnd)
        if hWnd == 0:
            hWnd = desktop_hwnd
        set_select_hwnd(hWnd)

    # 桌面截图：使用 mss，比 BitBlt 更可靠，解决桌面黑屏问题
    if hWnd == desktop_hwnd:
        printwindow_fail_count = 0  # 重置失败计数
        return _mss_fallback_screenshot()

    # 普通窗口：先检查窗口尺寸是否合理
    try:
        rect = win32gui.GetClientRect(hWnd)
        client_w = rect[2] - rect[0]
        client_h = rect[3] - rect[1]
    except Exception:
        client_w, client_h = 0, 0
    if client_w < MIN_WINDOW_SIZE or client_h < MIN_WINDOW_SIZE:
        # 窗口太小（如最小化或0x0），PrintWindow会产生垃圾数据
        # client为0时不传hWnd，直接全桌面截图，避免截到无效的窗口装饰框
        if client_w == 0 or client_h == 0:
            # 节流打印，避免每帧刷屏淹没其他日志
            if time.monotonic() - last_invisible_print_time > 5:
                print("get_window_image: 窗口不可见 (%dx%d), 回退全桌面截图" % (client_w, client_h))
                last_invisible_print_time = time.monotonic()
            printwindow_fail_count = 0
            return _mss_fallback_screenshot()
        else:
            print("get_window_image: 窗口过小 (%dx%d), 使用mss区域截图" % (client_w, client_h))
            printwindow_fail_count = 0
            return _mss_fallback_screenshot(hWnd)

    # 连续失败检测：同一窗口连续失败超过阈值，切换到mss区域截图
    if (printwindow_fail_count >= MSS_FALLBACK_THRESHOLD
            and printwindow_fail_hwnd == hWnd):
        return _mss_fallback_screenshot(hWnd)

    # 普通窗口截图：使用 ContinuousCapture (PrintWindow API)
    dev = get_current_device()
    if dev is None:
        return _mss_fallback_screenshot()
    try:
        if not dev.default_capture:
            dev.default_capture = ContinuousCapture()
        dev.default_capture.set_hwnd(hWnd)
        bmpstr, width, height = dev.default_capture.capture_window()
    except Exception as e:
        # PrintWindow/DC初始化失败(如窗口正在关闭、DC句柄失效)，回退到mss截图
        print("get_window_image: PrintWindow失败, 回退mss截图: %s" % e)
        dev.default_capture = None  # 重置，下次重建GDI资源
        _record_printwindow_fail(hWnd)
        return _mss_fallback_screenshot(hWnd)
    # 防御：位图尺寸有效性校验
    if width <= 0 or height <= 0:
        print("get_window_image: 位图尺寸无效 (%d, %d), 回退到mss截图" % (width, height))
        _record_printwindow_fail(hWnd)
        return _mss_fallback_screenshot(hWnd)
    # 防御：位图数据长度校验
    expected_bmp_len = width * height * 4
    if len(bmpstr) != expected_bmp_len:
        print("get_window_image: 位图数据长度不匹配 expected=%d actual=%d, 回退到mss截图"
              % (expected_bmp_len, len(bmpstr)))
        _record_printwindow_fail(hWnd)
        return _mss_fallback_screenshot(hWnd)
    # PrintWindow成功，重置失败计数
    printwindow_fail_count = 0
    printwindow_fail_hwnd = 0
    # 优先使用capture_window返回的实际位图尺寸，避免DPI缓存不一致导致画面斜切
    dpi_w, dpi_h = dev.default_capture.get_actual_size()
    if width != dpi_w or height != dpi_h:
        dev.default_capture.dpi_width = width
        dev.default_capture.dpi_height = height
    return Win32_Image(bgra=bmpstr, size=(width, height))


def _record_printwindow_fail(hWnd):
    """记录PrintWindow失败，用于连续失败检测和退避"""
    global printwindow_fail_count, printwindow_fail_hwnd
    if printwindow_fail_hwnd == hWnd:
        printwindow_fail_count += 1
    else:
        printwindow_fail_count = 1
        printwindow_fail_hwnd = hWnd
    if printwindow_fail_count >= MSS_FALLBACK_THRESHOLD:
        print("get_window_image: PrintWindow连续失败%d次, hwnd=%d, 切换到mss区域截图"
              % (printwindow_fail_count, hWnd))


_ui_msg_queue = queue.Queue()  # UI消息队列：工作线程→主线程的文本消息
_ui_root = None  # 主窗口引用，用于after调度


def insert_text_message(text, cleanNext=True, item=None):
    global Text1
    if text:
        print(text)
    if item is None:
        if Text1 is None:
            return
        item = Text1
    # 线程安全：Tk控件只能在主线程操作。非主线程调用时入队，由主线程的after轮询执行，
    # 避免工作线程直接操作UI造成卡顿或崩溃。
    if threading.current_thread() is not threading.main_thread():
        try:
            _ui_msg_queue.put((text, cleanNext, item))
        except Exception:
            pass
        return
    _do_insert_text_message(text, cleanNext, item)


def _do_insert_text_message(text, cleanNext=True, item=None):
    global Text1, cleanNextTime
    if item is None:
        item = Text1
    if item == Text1:
        clean = False
        if cleanNextTime:
            clean = True
            if not cleanNext:
                cleanNextTime = False
        elif cleanNext:
            cleanNextTime = True
        if not cleanNextTime and text:
            text = text + '\n'
    else:
        clean = True

    try:
        if isinstance(item, QTextEdit):
            item.setReadOnly(False)
            if clean:
                item.clear()  # 清除文本框
            item.insertPlainText(text)
            item.setReadOnly(True)
            sb = item.verticalScrollBar()
            sb.setValue(sb.maximum())
        else:  # QLineEdit（烧写路径框）
            item.setText(text)
    except Exception as e:
        print(e)


def _process_ui_msg_queue():
    """主线程定时轮询UI消息队列，把工作线程的消息安全地更新到界面"""
    global _ui_root
    try:
        while True:
            text, cleanNext, item = _ui_msg_queue.get_nowait()
            _do_insert_text_message(text, cleanNext, item)
    except queue.Empty:
        pass
    except Exception:
        pass
    if _ui_root is not None:
        try:
            QTimer.singleShot(100, _process_ui_msg_queue)
        except Exception:
            pass


def convertImageFileToRGB(file_path):
    if not os.path.exists(file_path):  # 检查文件是否存在
        insert_text_message("文件不存在：%s" % file_path, cleanNext=False)
        return bytearray()  # 如果文件不存在，直接返回，不执行后续代码

    im1 = None
    try:
        im1 = Image.open(file_path)
        return convertImageToRGB(im1)
    except Exception as e:
        errstr = "图片\"%s\"打开失败：%s" % (file_path, e)
        insert_text_message(errstr, cleanNext=False)
        return bytearray()
    finally:
        if im1 is not None:
            im1.close()


def convertImageToRGB(image):
    # 处理图片旋转
    ImageOps.exif_transpose(image, in_place=True)
    # 转换为RGB格式
    if image.mode != "RGB":
        image = image.convert("RGB")  # 转换为RGB格式。虽然转换再缩放会降低效率，但是能够提升缩小后的图片质量
    # 缩放到160*80，同时长宽比例修改为2:1
    if image.width > (image.height * 2):  # 图片长宽比例超过2:1
        im2 = image.resize((SHOW_HEIGHT * image.width // image.height, SHOW_HEIGHT), Image.Resampling.LANCZOS)
        # 定义需要裁剪的空间
        box = ((im2.width - SHOW_WIDTH) // 2, 0, (im2.width + SHOW_WIDTH) // 2, SHOW_HEIGHT)
        im2 = im2.crop(box)
    else:
        im2 = image.resize((SHOW_WIDTH, SHOW_WIDTH * image.height // image.width), Image.Resampling.LANCZOS)
        # 定义需要裁剪的空间
        box = (0, (im2.height - SHOW_HEIGHT) // 2, SHOW_WIDTH, (im2.height + SHOW_HEIGHT) // 2)
        im2 = im2.crop(box)
    # im2 = im2.convert("RGB")  # 转换为RGB格式

    # 转换为RGB565
    img_data = bytearray()
    for y in range(0, SHOW_HEIGHT):  # 逐字解析编码
        for x in range(0, SHOW_WIDTH):  # 逐字解析编码
            r, g, b = im2.getpixel((x, y))
            img_data.append(((r >> 3) << 3) | (g >> 5))
            img_data.append((((g % 32) >> 2) << 5) | (b >> 3))
    return img_data


# 按键功能定义
def Get_Photo_Path(index):  # 获取文件路径
    global Label3, Label4, Label5, Label6
    parent = _ui_root
    img_filter = "图片文件 (*.jpg *.jpeg *.png *.bmp *.ico *.webp *.jfif *.jpe *.gif)"
    if index == 1:
        photo_path, _ = QFileDialog.getOpenFileName(parent, "选择文件", "", "Bin file (*.bin)")
        insert_text_message(photo_path, item=Label3)
    elif index == 2:
        photo_path, _ = QFileDialog.getOpenFileName(parent, "选择文件", "", img_filter)
        insert_text_message(photo_path, item=Label4)
    elif index == 3:
        photo_path, _ = QFileDialog.getOpenFileName(parent, "选择文件", "", img_filter)
        insert_text_message(photo_path, item=Label5)
    elif index == 4:
        photo_path, _ = QFileDialog.getOpenFileName(parent, "选择文件", "", img_filter)
        insert_text_message(photo_path, item=Label6)


def Start_Write_Photo_Path(index):  # 写入文件
    global Device_State
    if Device_State == 0:
        insert_text_message("设备未连接，烧录失败")
        return
    if index == 1:
        target = Write_Photo_Path1
    elif index == 2:
        target = Write_Photo_Path2
    elif index == 3:
        target = Write_Photo_Path3
    elif index == 4:
        target = Write_Photo_Path4
    threading.Thread(target=target, daemon=True).start()


def Write_Photo_Path1():  # 写入文件
    global write_path_index, sleep_event
    ctx = _cur_main_ctx()
    le = ctx.get('label3') if ctx else None
    photo_path = le.text().strip() if le else ""
    if not photo_path:
        insert_text_message("闪存固件未选择")
        return
    insert_text_message("准备烧写Flash固件…", cleanNext=False)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 1


def Write_Photo_Path2():  # 写入文件
    global config_obj, write_path_index, Img_data_use, sleep_event
    ctx = _cur_main_ctx()
    le = ctx.get('label4') if ctx else None
    photo_path = le.text().strip() if le else ""
    if not photo_path:
        insert_text_message("背景图像未选择")
        return

    insert_text_message("图像格式转换…", cleanNext=False)
    Img_data_use = convertImageFileToRGB(photo_path)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 2


def Write_Photo_Path3():  # 写入文件
    global config_obj, write_path_index, Img_data_use, sleep_event
    ctx = _cur_main_ctx()
    le = ctx.get('label5') if ctx else None
    photo_path = le.text().strip() if le else ""
    if not photo_path:
        insert_text_message("相册图像未选择")
        return

    insert_text_message("图像格式转换…", cleanNext=False)
    Img_data_use = convertImageFileToRGB(photo_path)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 3


def Write_Photo_Path4():  # 写入文件
    global config_obj, write_path_index, Img_data_use, sleep_event
    ctx = _cur_main_ctx()
    le = ctx.get('label6') if ctx else None
    photo_path = le.text().strip() if le else ""
    if not photo_path:
        insert_text_message("动图文件未选择")
        return

    Img_data_use = bytearray()
    insert_text_message("动图格式转换中…", cleanNext=False)
    Path_use1 = photo_path
    try:
        index = Path_use1.rindex(".")
    except ValueError as e:
        insert_text_message("动图名称不符合要求！%s" % e)
        return  # 如果文件名不符合要求，直接返回
    path_file_type = Path_use1[index:]

    u_time = time.time()

    if path_file_type.lower() == ".gif":
        try:
            gif = Image.open(Path_use1)
            if not "duration" in gif.info:
                insert_text_message("非动图文件：%s" % Path_use1)
                return
            if gif.n_frames > 1000:
                insert_text_message("动图过大，无能为力")
                return

            durations = []
            longs = 0
            for i in range(0, gif.n_frames):
                gif.seek(i)
                if "duration" in gif.info:
                    duration = gif.info["duration"]
                    if duration <= 0:
                        duration = 100  # 默认0.1s
                durations.append(duration)
                longs += duration

            realduration = longs / 36.0
            _ctx_main = _cur_main_ctx()
            _iv_box = _ctx_main.get('interval_var') if _ctx_main else None
            if realduration >= 10:
                duration_string = "%.4f" % (realduration / 1000.0)
                massage = "建议动图间隔：%s" % duration_string
                if _iv_box is not None:
                    _iv_box.set(duration_string)
            else:
                massage = "动图太短，不建议使用此动图"
                if _iv_box is not None:
                    _iv_box.set("0.1")
            insert_text_message(massage, cleanNext=False)

            gifseek = 0
            curtime = 0
            giftime = durations[gifseek]
            for i in range(0, 36):  # 依次转换36张图片
                while giftime < int(curtime):
                    gifseek += 1
                    giftime += durations[gifseek]
                curtime += realduration

                gif.seek(gifseek)
                converted = gif
                # 如果长度小于宽度，则旋转90度
                # if converted.width < converted.height:
                #     converted = converted.transpose(Image.Transpose.ROTATE_270)
                converted = convertImageToRGB(converted)
                if len(converted) == 0:
                    insert_text_message("转换失败")
                    return  # 转换失败，取消写入
                Img_data_use.extend(converted)
        except Exception as e:
            insert_text_message("图片\"%s\"打开失败：%s" % (Path_use1, e))
            print(traceback.format_exc())
            return
        finally:
            gif.close()
    else:
        Path_use = Path_use1[:index - 1]
        file_path = "%s35%s" % (Path_use, path_file_type)
        if not os.path.exists(file_path):
            Path_use = Path_use1[:index - 2]
            file_path = "%s35%s" % (Path_use, path_file_type)
            if not os.path.exists(file_path):
                file_path = None

        if file_path:  # 文件名是 A0、A1、…… A35 排列
            for i in range(0, 36):  # 依次转换36张图片
                file_path = "%s%d%s" % (Path_use, i, path_file_type)
                converted = convertImageFileToRGB(file_path)
                if len(converted) == 0:
                    insert_text_message("转换失败")
                    return  # 转换失败，取消写入
                Img_data_use.extend(converted)
        else:  # 不是规则命名，只按文件类型查找文件
            file_path = os.path.join(os.path.dirname(Path_use1), "*%s" % path_file_type)
            files = []
            try:
                files = glob.glob(file_path)  # 按类型列出所有文件
            except Exception as e:
                insert_text_message("转换失败: %s" % e)
                return  # 转换失败，取消写入
            if len(files) < 36:
                insert_text_message("转换失败，图片不够36张")
                return  # 转换失败，取消写入
            for i in range(0, 36):  # 依次转换36张图片
                converted = convertImageFileToRGB(files[i])
                if len(converted) == 0:
                    insert_text_message("转换失败")
                    return  # 转换失败，取消写入
                Img_data_use.extend(converted)

    insert_text_message("转换完成，耗时%.1f秒" % (time.time() - u_time), cleanNext=False)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 4


def state_change_set(message=None, save=True):
    device = get_current_device()
    if device is None:
        return
    device.state_change = 1
    device.force_lcd_reset = True  # 切页时强制重置LCD方向
    # 彻底重置：清空截图流水线队列，递增帧代际，丢弃所有在途帧。
    # 防止频繁切换时，旧帧数据被发送到新页面，造成命令流错位/画面倾斜
    clear_queue(device.screen_shot_queue)
    clear_queue(device.screen_process_queue)
    device.screen_frame_generation += 1
    device.sleep_event.set()
    device.burn_offset_x = 0
    device.burn_offset_y = 0
    device.burn_offset_time = 0
    if save:
        save_config()
    if message is not None:
        insert_text_message(message)


def state_change_clear():
    device = get_current_device()
    if device is None:
        return
    device.state_change = 0
    device.sleep_event.clear()


def Page_UP():  # 上一页
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    # 基于当前设备自己的配置切换页面：daemon渲染线程会在多设备间切换全局config_obj，
    # 若直接用全局会改到别的设备的配置，导致两个屏一起切换
    set_active_device_config(dev)
    keys = list(PAGE_ID.keys())
    if not keys:
        return
    try:
        index = keys.index(config_obj.state_machine)
        if index >= len(keys) - 1:
            index = 0
        else:
            index = index + 1
    except:
        index = 0
    config_obj.state_machine = keys[index]
    if dev:
        dev.state_machine = config_obj.state_machine
    if config_obj.state_machine == CAMERA_VIDEO_ID and dev:
        clear_queue(dev.screen_shot_queue)
        clear_queue(dev.screen_process_queue)
    state_change_set(PAGE_ID[config_obj.state_machine])
    sync_page_combobox()


def Page_Down():  # 下一页
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    # 基于当前设备自己的配置切换页面（避免多屏联动）
    set_active_device_config(dev)
    keys = list(PAGE_ID.keys())
    if not keys:
        return
    try:
        index = keys.index(config_obj.state_machine)
        if index == 0:
            index = len(keys) - 1
        else:
            index = index - 1
    except:
        index = 0
    config_obj.state_machine = keys[index]
    if dev:
        dev.state_machine = config_obj.state_machine
    if config_obj.state_machine == SCREEN_PAGE_ID and dev:
        clear_queue(dev.screen_shot_queue)
        clear_queue(dev.screen_process_queue)
    state_change_set(PAGE_ID[config_obj.state_machine])
    sync_page_combobox()


def do_key_action(action):
    """执行按键自定义映射的动作（供manage_task按键线程调用）"""
    global config_obj
    if action == "下翻页":
        Page_UP()
    elif action == "上翻页":
        Page_Down()
    elif action == "切换方向":
        LCD_Change()
    # "无" 或其他未知值：不执行任何动作


def toggle_timer():
    """番茄钟：开始/暂停"""
    global timer_running, timer_last_tick
    timer_running = not timer_running
    timer_last_tick = time.monotonic()


def reset_timer():
    """番茄钟：重置"""
    global config_obj, timer_remaining, timer_running, timer_last_tick
    timer_remaining = max(1, int(config_obj.timer_minutes)) * 60
    timer_running = True
    timer_last_tick = time.monotonic()


# ===== 每屏主控控件上下文（模块级）：主控页多标签后，每块屏一套主控控件，这里记录各屏上下文 =====
_main_ctxs = {}            # dev_id -> 该屏主控控件上下文
_active_main_dev_id = None  # 当前显示的主控标签对应的设备id


def _cur_main_ctx():
    """返回当前主控标签对应的控件上下文（无则 None）"""
    return _main_ctxs.get(_active_main_dev_id)


def sync_page_combobox():
    """同步页面下拉列表的显示值（基于当前设备配置）"""
    global config_obj
    ctx = _cur_main_ctx()
    cb = ctx.get('page_combobox') if ctx else None
    if cb is not None:
        try:
            dev = get_current_device()
            cfg = dev.config if dev is not None and dev.config is not None else config_obj
            page_name = PAGE_ID.get(cfg.state_machine, "")
            cb.blockSignals(True)
            # 仅当下拉项集合变化(如切换语言)才重建 items；否则只更新选中项。
            # 避免 clear+addItems 频繁重置，关闭用户正在打开的下拉框导致无法选择。
            expected = list(PAGE_ID.values())
            if [cb.itemText(i) for i in range(cb.count())] != expected:
                cb.clear()
                cb.addItems(expected)
            if page_name and cb.currentText() != page_name:
                cb.setCurrentText(page_name)
            cb.blockSignals(False)
        except Exception:
            pass


def on_page_combobox_select(index=-1):
    """用户通过下拉列表选择页面（仅作用于当前选中设备）"""
    global config_obj
    dev = get_current_device()
    ctx = _cur_main_ctx()
    cb = ctx.get('page_combobox') if ctx else None
    if cb is None:
        return
    selected_name = cb.currentText()
    for pid, pname in PAGE_ID.items():
        if pname == selected_name:
            # 基于当前设备自己的配置切换（避免多屏联动）
            set_active_device_config(dev)
            if config_obj.state_machine != pid:
                config_obj.state_machine = pid
                if dev:
                    dev.state_machine = pid
                if dev and (pid == CAMERA_VIDEO_ID or pid == SCREEN_PAGE_ID):
                    clear_queue(dev.screen_shot_queue)
                    clear_queue(dev.screen_process_queue)
                state_change_set(pname)
            break


def LCD_Change():  # 切换显示方向（循环）
    global config_obj
    dev = get_current_device()
    if dev is None or dev.device_state == 0:
        insert_text_message("设备未连接，切换失败")
        return
    # 基于当前设备自己的配置切换方向（避免多屏联动）
    set_active_device_config(dev)
    config_obj.lcd_change = (config_obj.lcd_change + 1) % len(LCD_STATE_MESSAGE)
    state_change_set(LCD_STATE_MESSAGE[config_obj.lcd_change])
    sync_lcd_combobox()


def set_lcd_direction(index):
    """直接设置显示方向（基于当前设备配置）"""
    global config_obj
    dev = get_current_device()
    if dev is None or dev.device_state == 0:
        insert_text_message("设备未连接，切换失败")
        return
    set_active_device_config(dev)
    if config_obj.lcd_change != index:
        config_obj.lcd_change = index
        state_change_set(LCD_STATE_MESSAGE[config_obj.lcd_change])


def sync_lcd_combobox():
    """同步显示方向下拉列表（基于当前设备配置）"""
    global config_obj
    ctx = _cur_main_ctx()
    cb = ctx.get('lcd_direction_combobox') if ctx else None
    if cb is not None:
        try:
            dev = get_current_device()
            cfg = dev.config if dev is not None and dev.config is not None else config_obj
            cb.setCurrentText(LCD_STATE_MESSAGE[cfg.lcd_change])
        except Exception:
            pass


def apply_language():
    """切换界面语言（页面名称与方向名称）"""
    global config_obj
    try:
        if config_obj.language == "English":
            PAGE_ID.clear()
            PAGE_ID.update(PAGE_ID_EN)
            LCD_STATE_MESSAGE[:] = LCD_STATE_MESSAGE_EN
        else:
            PAGE_ID.clear()
            PAGE_ID.update(PAGE_ID_CN)
            LCD_STATE_MESSAGE[:] = LCD_STATE_MESSAGE_CN
    except Exception:
        pass
    sync_page_combobox()
    ctx = _cur_main_ctx()
    cb = ctx.get('lcd_direction_combobox') if ctx else None
    if cb is not None:
        try:
            cb.blockSignals(True)
            cb.clear()
            cb.addItems(list(LCD_STATE_MESSAGE))
            cb.blockSignals(False)
        except Exception:
            pass
    sync_lcd_combobox()


def on_lcd_direction_select(index=-1):
    """用户通过下拉列表选择显示方向"""
    global config_obj
    ctx = _cur_main_ctx()
    cb = ctx.get('lcd_direction_combobox') if ctx else None
    if cb is None:
        return
    selected = cb.currentText()
    try:
        index = LCD_STATE_MESSAGE.index(selected)
        set_lcd_direction(index)
    except ValueError:
        pass


# 由于设备不支持多线程访问，请不要直接使用SER_Write，应使用SER_rw方法
def SER_Write(Data_U0):
    device = get_current_device()
    if device is None:
        raise IOError("设备未连接")
    ser = device.ser
    if ser is None or not ser.is_open:
        raise IOError("串口未打开")
    # 尝试发出指令,有两种无法正确发送命令的情况：1.设备被移除,发送出错；2.设备处于MSN连接状态，对于电脑发送的指令响应迟缓
    ser.reset_input_buffer()  # 清空输入缓存
    # 注意：不要reset_output_buffer()！USB串口适配器内部还有缓冲，
    # flush()返回后适配器可能仍在发送最后几个字节，reset_output_buffer()
    # 会中途打断传输导致硬件收到截断的命令流，造成解析错位→画面倾斜。
    data_len = len(Data_U0)
    # 大块数据分块写入：单次write大块数据可能触发write_timeout导致部分写入
    # （命令流截断→硬件解析错位→画面倾斜）。分块写入每块都校验完整性。
    CHUNK_SIZE = 1024
    if data_len <= CHUNK_SIZE:
        written = ser.write(Data_U0)
        if written != data_len:
            print("SER_Write: 写入不完整 expected=%d actual=%d" % (data_len, written))
            raise IOError("串口写入不完整")
    else:
        total = 0
        while total < data_len:
            # 写入前再次确认串口仍打开，避免其他线程关闭串口后写入失败
            if not ser.is_open:
                raise IOError("串口已关闭")
            end = min(total + CHUNK_SIZE, data_len)
            chunk = Data_U0[total:end]
            written = ser.write(chunk)
            if written != len(chunk):
                print("SER_Write: 分块写入不完整 chunk=%d actual=%d (已写%d/%d)"
                      % (len(chunk), written, total, data_len))
                raise IOError("串口分块写入不完整")
            total += written
    ser.flush()
    # 大块数据发送后短暂排空：USB适配器flush()返回后可能仍在发送末尾字节，
    # 紧接着的下一条命令会与末尾字节在适配器内部交错，造成硬件解析错位→倾斜
    if data_len > CHUNK_SIZE:
        time.sleep(0.1)


# 由于设备不支持多线程访问，请不要直接使用SER_Read，应使用SER_rw方法
def SER_Read():
    device = get_current_device()
    if device is None or device.ser is None or not device.ser.is_open:
        return 0
    ser = device.ser
    # 在限定时长内等待响应首字节：避免忙等(过快误判超时)或无限阻塞。
    # 设备在渲染帧期间可能短暂无响应，稍作等待即可恢复。
    deadline = time.monotonic() + 0.5
    recv = bytearray()
    try:
        while len(recv) == 0:
            if time.monotonic() >= deadline:
                print("SER_Read timeout")
                return 0
            n = ser.in_waiting
            if n > 0:
                recv.extend(ser.read(n))
                break
            time.sleep(0.005)
    except Exception:
        # 底层瞬时错误(如串口被并发关闭/句柄异常)视为无响应返回0，
        # 不抛异常到 SER_rw 的 except，避免误判掉线触发反复重连。
        return 0
    # 响应可能分片到达：短暂等待并收集剩余字节
    time.sleep(0.01)
    try:
        if ser.in_waiting > 0:
            recv.extend(ser.read(ser.in_waiting))
    except Exception:
        pass
    return recv


def SER_rw(data, read=True, size=0):
    device = get_current_device()
    ser = device.ser
    SER_lock = device.SER_lock

    result = bytearray()
    SER_lock.acquire()
    try:
        if not ser.is_open:
            print("设备未连接，取消串口读写")
            return result

        try:
            SER_Write(data)  # 发出指令
        except Exception as e:
            # 写失败可能只是设备瞬时繁忙（如正在渲染帧/命令流拥塞），
            # 等待后重试一次，避免一次瞬时故障就误判掉线、断开设备重连。
            print("串口写入异常(%s)，等待后重试一次…" % e)
            time.sleep(0.1)
            if not ser.is_open:
                raise
            SER_Write(data)
        if not read:
            return result
        while True:
            recv = SER_Read()
            if recv == 0:
                return result
            result.extend(recv)
            if len(result) >= size:
                return result
    except Exception as e:  # 出现异常
        # 不 ser.close()/set_device_state(0)：瞬时异常(超时/底层竞争)会误判掉线，
        # 导致 daemon 反复重连→屏幕重新初始化→闪烁。真正拔线由 Read_ADC_CH 连续失败(10次)检测。
        print("串口读写异常，%s" % e)
    finally:
        SER_lock.release()
    return result


def Read_M_u8(add):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(0 * 32)  # 识别为8bit SFR读
    hex_use.append(add // 256)  # 高地址
    hex_use.append(add % 256)  # 低地址
    hex_use.append(0)  # 数值

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 5:
        return recv[5]
    else:
        print("Read_M_u8 failed: %s" % recv)
        set_device_state(0)
        return 0


def Read_M_u16(add):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(1 * 32)  # 识别为16bit SFR读
    hex_use.append(add % 256)  # 地址
    hex_use.append(0)  # 高位数值
    hex_use.append(0)  # 低位数值

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 5:
        return recv[4] * 256 + recv[5]
    else:
        print("Read_M_u16 failed: %s" % recv)
        set_device_state(0)
        return 0


def Write_M_u8(add, data_w):  # 修改主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(4 * 32)  # 识别为16bit SFR写
    hex_use.append(add // 256)  # 高地址
    hex_use.append(add % 256)  # 低地址
    hex_use.append(data_w % 256)  # 数值

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 0:
        return 1
    else:
        print("Write_M_u8 failed: %s" % recv)
        set_device_state(0)
        return 0


def Write_M_u16(add, data_w):  # 修改主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(1 * 32)  # 识别为16bit SFR写
    hex_use.append(add % 256)  # 地址
    hex_use.append(data_w // 256)  # 高位数值
    hex_use.append(data_w % 256)  # 低位数值

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 0:
        return 1
    else:
        print("Write_M_u16 failed: %s" % recv)
        set_device_state(0)
        return 0


def Read_ADC_CH(ch):  # 读取主机ADC寄存器数值（ADC通道）
    device = get_current_device()
    hex_use = bytearray()
    hex_use.append(8)  # 读取ADC
    hex_use.append(ch)  # 通道
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 5 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        if device is not None:
            device.adc_fail_count = 0
        return recv[4] * 256 + recv[5]
    else:
        # 单次读取失败(如设备正忙于渲染帧)不应立即断开，
        # 否则会在帧写入中途关闭串口，导致命令流截断→画面倾斜。
        # 连续多次失败才判定为真正断开。
        fail_count = (getattr(device, 'adc_fail_count', 0) + 1) if device is not None else 1
        if device is not None:
            device.adc_fail_count = fail_count
        if fail_count >= 10:
            print("Read_ADC_CH 连续失败%d次，触发重连" % fail_count)
            set_device_state(0)
            if device is not None:
                device.adc_fail_count = 0
        elif fail_count == 1:
            print("Read_ADC_CH failed (第1次，忽略): %s" % recv)
        return 0


# SFR格式：data_name data_unit data_family data_data
def Read_M_SFR_Data(add):  # 从u8区域获取SFR描述
    SFR_data = bytearray()
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        SFR_data.append(Read_M_u8(add + i))  # 读取编码数据
    data_type = 0  # 根据是否为0进行类型循环统计
    data_len = 0
    data_use = bytearray()
    data_name = b""
    data_unit = b""
    data_family = b""
    data_data = b""
    My_MSN_Data = []
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        if data_type < 3:
            if SFR_data[i] != 0:  # 未检测到0
                data_use.append(SFR_data[i])  # 将非0数据合并到一块
                continue
            if len(data_use) == 0:  # 没有接收到数据时就接收到00
                break  # 检测到0后收集的数据为空，判断为结束
            if data_type == 0:
                data_name = data_use  # 名称
                data_use = bytearray()
                data_type = 1
            elif data_type == 1:
                data_unit = data_use  # 单位
                data_use = bytearray()
                data_type = 2
            else:  # data_type == 2
                data_family = data_use  # 类型
                data_use = bytearray()
                data_type = 3
                data_len = ord(data_family) // 32
                if data_len == 0:  # u8 data 2B add
                    data_len = 2
                elif data_len == 1:  # u16 data 1B add
                    data_len = 1
                elif data_len == 2:  # u32 data 2B add
                    data_len = 2
                elif data_len == 3:  # u8 Text XB data
                    data_len = data_family[0] % 32  # 计算数据长度
                else:
                    print("data_len error: %d" % data_len)
        else:  # data_type == 3
            if data_len > 0:  # 正式的有效数据
                data_use.append(SFR_data[i])  # 将非0数据合并到一块
                data_len = data_len - 1
            if data_len == 0:  # 将后续数据收集完整，注意这儿不能用elif
                data_data = data_use
                # 对数据进行登记
                My_MSN_Data.append(MSN_Data(data_name, data_unit, data_family, data_data))

                data_type = 0  # 重置类型
                data_use = bytearray()  # 获取完成，重置数组
    return My_MSN_Data


def Print_MSN_Data(My_MSN_Data):
    type_list = ["u8_SFR地址", "u16_SFR地址", "u32_SFR地址", "字符串  ", "u8数组数据"]
    num = len(My_MSN_Data)
    print("MSN数据总数为：%d" % num)
    # 进行数据解析
    for i in range(0, num):  # 将数据全部打印出来
        data_str = "序号：%-5d名称：%-15s单位：%-20s类型：%-12s长度：%-5d地址：%-5s" % (
            i, My_MSN_Data[i].name.decode("utf-8"), My_MSN_Data[i].unit, type_list[ord(My_MSN_Data[i].family) // 32],
            ord(My_MSN_Data[i].family) % 32, int.from_bytes(My_MSN_Data[i].data, byteorder="big"))
        print(data_str)


def Read_MSN_Data(My_MSN_Data):  # 读取MSN_data中的数据
    print("MSN_data:")
    for i in range(0, len(My_MSN_Data)):  # 将数据查找一遍
        use_data = []  # 创建一个空列表
        data_type = ord(My_MSN_Data[i].family) // 32
        if data_type == 0:  # 数据类型为u8地址(16bit)
            sfr_add = int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1])
            for n in range(0, ord(My_MSN_Data[i].family) % 32):
                use_data.append(Read_M_u8(sfr_add + n))
        elif data_type == 1:  # 数据类型为u16地址(8bit)
            use_data.append(Read_M_u16(int(My_MSN_Data[i].data[0])))
        elif data_type == 2:  # 数据类型为u32地址(16bit)
            sfr_add = int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1])
            for n in range(0, ord(My_MSN_Data[i].family) % 32):
                use_data.append(Read_M_u8(sfr_add + n))
        elif data_type == 3:  # 数据类型为u8字符串
            use_data.append(My_MSN_Data[i].data)
        elif data_type == 4:  # 数据类型为u8数组
            use_data.append(My_MSN_Data[i].data)
        else:
            print("data_type error in Read_MSN_Data: %d" % data_type)
        print("%-10s = %s" % (My_MSN_Data[i].name.decode("utf-8"), use_data))


def Write_MSN_Data(My_MSN_Data, name_use, data_w):  # 在MSN_data写入数据
    for i in range(0, len(My_MSN_Data)):  # 将数据查找一遍
        if My_MSN_Data[i].name != name_use:
            continue
        data_type = int(My_MSN_Data[i].family) // 32
        if data_type == 0:  # 数据类型为u8地址(16bit)
            Write_M_u8(int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1]), data_w)
            print("\"%s\"写入%s完成" % (name_use, str(data_w)))
            return 1
        elif data_type == 1:  # 数据类型为u16地址(8bit)
            Write_M_u16(int(My_MSN_Data[i].data[0]), data_w)
            print("\"%s\"写入%s完成" % (name_use, str(data_w)))
            return 1
        else:
            print("data_type error in Write_MSN_Data: %d" % data_type)
    print("\"%s\"不存在，请检查名称是否正确" % name_use)
    return 0


def Write_Flash_Page(Page_add, data_w, Page_num):  # 往Flash指定页写入256B数据
    # 先把数据传输完成
    hex_use = bytearray()
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use.append(4)  # 多次写入Flash
        hex_use.append(i)  # 低位地址
        hex_use.append(data_w[i * 4 + 0])  # Data0
        hex_use.append(data_w[i * 4 + 1])  # Data1
        hex_use.append(data_w[i * 4 + 2])  # Data2
        hex_use.append(data_w[i * 4 + 3])  # Data3
    hex_use.append(3)  # 对Flash操作
    hex_use.append(1)  # 写Flash
    hex_use.append(Page_add // 65536)  # Data0
    hex_use.append((Page_add % 65536) // 256)  # Data1
    hex_use.append(Page_add % 256)  # Data2
    hex_use.append(Page_num % 256)  # Data3

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 0:
        return 1
    else:
        print("Write_Flash_Page failed: %s" % recv)
        set_device_state(0)
        return 0


# 未经过擦除，直接往Flash指定页写入256B数据
def Write_Flash_Page_fast(Page_add, data_w, Page_num):
    # 先把数据传输完成
    hex_use = bytearray()
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use.append(4)  # 多次写入Flash
        hex_use.append(i)  # 低位地址
        hex_use.append(data_w[i * 4 + 0])  # Data0
        hex_use.append(data_w[i * 4 + 1])  # Data1
        hex_use.append(data_w[i * 4 + 2])  # Data2
        hex_use.append(data_w[i * 4 + 3])  # Data3
    hex_use.append(3)  # 对Flash操作
    hex_use.append(3)  # 经过擦除，写Flash
    hex_use.append(Page_add // 65536)  # Data0
    hex_use.append((Page_add % 65536) // 256)  # Data1
    hex_use.append(Page_add % 256)  # Data2
    hex_use.append(Page_num)  # Data3

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 0:
        return 1
    else:
        print("Write_Flash_Page_fast failed: %s" % recv)
        set_device_state(0)
        return 0


def Erase_Flash_page(add, size):  # 清空指定区域的内存
    hex_use = bytearray()
    hex_use.append(3)  # 对Flash操作
    hex_use.append(2)  # 清空指定区域的内存
    hex_use.append((add % 65536) // 256)  # Data1
    hex_use.append(add % 256)  # Data2
    hex_use.append((size % 65536) // 256)  # Data1
    hex_use.append(size % 256)  # Data2

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 0:
        return 1
    else:
        print("Erase_Flash_page failed: %s" % recv)
        set_device_state(0)
        return 0


def Read_Flash_byte(add):  # 读取指定地址的数值
    hex_use = bytearray()
    hex_use.append(3)  # 对Flash操作
    hex_use.append(0)  # 读Flash
    hex_use.append(add // 65536)  # Data0
    hex_use.append((add % 65536) // 256)  # Data1
    hex_use.append(add % 256)  # Data2
    hex_use.append(0)  # Data3

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 5:
        return recv[5]
    else:
        print("Read_Flash_byte failed: %s" % recv)
        set_device_state(0)
        return 0


# 闪存芯片P25D80具有1024KB的存储空间，以256B为一页，共4096页，使用0~4095作为页地址
# 闪存上存储的数据信息如下：
# for i in range(1, 37):  # 36张动图数据，160*80分辨率彩色图片，每张占用100个Page，共3600页
#     Write_Flash_Photo_fast(100 * (i - 1), str(i))
# Write_Flash_Photo_fast(3600, "Demo1")  # 240*240单色图片，占用29个Page
# Write_Flash_Photo_fast(3629, "N48X66P")  # 48*66分辨率数码管图像，占用22个Page
# Write_Flash_ZK(3651, "ASC64")  # 时钟字体，32*64分辨率ASCII表格，占用128个Page
# Write_Flash_Photo_fast(3779, "logo")  # 240*102单色LOGO,占用12个Page
# Write_Flash_Photo_fast(3791, "J1")  # 240*240单色图片，占用29个Page
# Write_Flash_Photo_fast(3820, "MLOGO")  # 160*68单色图片，占用6个Page
# Write_Flash_Photo_fast(3826, "CLK_BG")  # 时钟背景图像，160*80彩色图片，占用100个Page
# Write_Flash_Photo_fast(3926, "PH1")  # 相册图像，160*80彩色图片，占用100个Page
# Write_Flash_Photo_fast(4026, "N24X33P")  # 状态显示页面字体，24*33分辨率数码管图像，占用12个Page
# Write_Flash_Photo_fast(4038, "MP1")  # 状态显示页面背景，160*80单色图片，占用7个Page
def Write_Flash_Photo_fast(Page_add, filepath):  # 往Flash里面写入Bin格式的照片
    binfile = None
    try:  # 尝试打开bin文件
        Fsize = os.path.getsize(filepath)
        if Fsize == 0:
            insert_text_message("未读到数据，取消烧录。")
            return 0
        binfile = open(filepath, "rb")  # 以只读方式打开

        insert_text_message("找到\"%s\"文件，大小%dB，烧录中…" % (filepath, Fsize), cleanNext=False)
        u_time = time.time()
        Page_Count = Fsize // 256
        Data_Remain = Fsize % 256
        # 进行擦除
        if Data_Remain != 0:
            Erase_Flash_page(Page_add, Page_Count + 1)  # 清空指定区域的内存
        else:
            Erase_Flash_page(Page_add, Page_Count)  # 清空指定区域的内存

        for i in range(0, Page_Count):  # 每次写入一个Page
            Fdata = binfile.read(256)
            Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
        if Data_Remain != 0:  # 还存在没写完的数据
            Fdata = bytearray(binfile.read(Data_Remain))  # 将剩下的数据读完
            for i in range(Data_Remain, 256):
                Fdata.append(0xFF)  # 不足位置补充0xFF
            Write_Flash_Page_fast(Page_add + Page_Count, Fdata, 1)  # (page,数据，大小)
        u_time = time.time() - u_time
        insert_text_message("烧写完成，耗时%.1f秒" % u_time)
        return 1
    except Exception as e:  # 出现异常
        insert_text_message("文件路径或格式出错\"%s\"，%s" % (filepath, e))
        return 0
    finally:
        if binfile is not None:
            binfile.close()


def Write_Flash_hex_fast(Page_add, img_use):  # 往Flash里面写入hex数据
    Fsize = len(img_use)
    if Fsize == 0:
        insert_text_message("未读到数据，取消烧录。")
        return 0
    insert_text_message("大小%dB，烧录中…" % Fsize, cleanNext=False)
    u_time = time.time()
    Page_Count = Fsize // 256
    Data_Remain = Fsize % 256
    # 进行擦除
    if Data_Remain != 0:
        Erase_Flash_page(Page_add, Page_Count + 1)  # 清空指定区域的内存
    else:
        Erase_Flash_page(Page_add, Page_Count)  # 清空指定区域的内存

    for i in range(0, Page_Count):  # 每次写入一个Page
        Fdata = img_use[i * 256:(i + 1) * 256]  # 取256字节
        Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if Data_Remain != 0:  # 还存在没写完的数据
        Fdata = bytearray(img_use[Page_Count * 256:])  # 将剩下的数据读完
        for i in range(Data_Remain, 256):
            Fdata.append(0xFF)  # 不足位置补充0xFF
        Write_Flash_Page_fast(Page_add + Page_Count, Fdata, 1)  # (page,数据，大小)
    insert_text_message("烧写完成，耗时%.1f秒" % (time.time() - u_time))
    return 1


def Write_Flash_ZK(Page_add, ZK_name):  # 往Flash里面写入Bin格式的字库
    filepath = "%s.bin" % ZK_name  # 合成文件名称
    binfile = None
    try:  # 尝试打开bin文件
        Fsize = os.path.getsize(filepath) - 6  # 字库文件的最后六个字节不是点阵信息
        if Fsize <= 0:
            insert_text_message("未读到数据，取消烧录。")
            return 0
        binfile = open(filepath, "rb")  # 以只读方式打开
        insert_text_message("找到\"%s\"文件，大小：%dB" % (filepath, Fsize), cleanNext=False)

        Page_Count = Fsize // 256
        Data_Remain = Fsize % 256
        # 进行擦除
        # if Data_Remain != 0:
        #     Erase_Flash_page(Page_add, Page_Count + 1)  # 清空指定区域的内存
        # else:
        #     Erase_Flash_page(Page_add, Page_Count)  # 清空指定区域的内存

        for i in range(0, Page_Count):  # 每次写入一个Page
            Fdata = binfile.read(256)
            Write_Flash_Page(Page_add + i, Fdata, 1)  # (page,数据，大小)
        if Data_Remain != 0:  # 还存在没写完的数据
            Fdata = bytearray(binfile.read(Data_Remain))  # 将剩下的数据读完
            for i in range(Data_Remain, 256):
                Fdata.append(0xFF)  # 不足位置补充0xFF
            Write_Flash_Page(Page_add + Page_Count, Fdata, 1)  # (page,数据，大小)
        insert_text_message("%s 烧写完成" % filepath)
        return 1
    except Exception as e:  # 出现异常
        insert_text_message("找不到文件\"%s\"，%s" % (filepath, e))
        print(traceback.format_exc())
        return 0
    finally:
        if binfile is not None:
            binfile.close()


def LCD_Set_XY(LCD_D0, LCD_D1):  # 设置起始位置
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(0)  # 设置起始位置
    hex_use.append(LCD_D0 // 256)  # Data0
    hex_use.append(LCD_D0 % 256)  # Data1
    hex_use.append(LCD_D1 // 256)  # Data2
    hex_use.append(LCD_D1 % 256)  # Data3
    return hex_use


def LCD_Set_Size(LCD_D0, LCD_D1):  # 设置大小
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(1)  # 设置大小
    hex_use.append(LCD_D0 // 256)  # Data0
    hex_use.append(LCD_D0 % 256)  # Data1
    hex_use.append(LCD_D1 // 256)  # Data2
    hex_use.append(LCD_D1 % 256)  # Data3
    return hex_use


def LCD_Set_Color(LCD_D0, LCD_D1):  # 设置颜色（FC,BC）
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(2)  # 设置颜色
    hex_use.append(LCD_D0 // 256)  # Data0
    hex_use.append(LCD_D0 % 256)  # Data1
    hex_use.append(LCD_D1 // 256)  # Data2
    hex_use.append(LCD_D1 % 256)  # Data3
    SER_rw(hex_use, read=False)  # 发出指令


def LCD_Photo(Page_Add):
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(0)  # 显示彩色图片
    hex_use.append(Page_Add // 256)
    hex_use.append(Page_Add % 256)
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_Photo failed: %s" % recv)
        set_device_state(0)
        return 0


# 防烧屏全局变量
burn_offset_x = 0
burn_offset_y = 0
burn_offset_time = 0
BURN_OFFSETS = [(0, 0), (2, 0), (0, 1), (1, 0), (2, 2), (0, 0), (1, 2), (2, 1), (1, 1)]
BURN_INTERVAL = 30  # 每30秒移动一次

def update_burn_offset():
    """更新防烧屏偏移量（每30秒循环移动1像素）"""
    global config_obj
    dev = get_current_device()
    if dev is None: return
    if not config_obj or config_obj.anti_burn == 0:
        dev.burn_offset_x = 0
        dev.burn_offset_y = 0
        return
    now = time.monotonic()
    if now - dev.burn_offset_time > BURN_INTERVAL:
        dev.burn_offset_time = now
        idx = int(now // BURN_INTERVAL) % len(BURN_OFFSETS)
        dev.burn_offset_x, dev.burn_offset_y = BURN_OFFSETS[idx]

def LCD_ADD(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size):
    # 防烧屏：微调显示位置
    update_burn_offset()
    dev = get_current_device()
    if dev is None: return 0
    x = max(0, LCD_X + dev.burn_offset_x)
    y = max(0, LCD_Y + dev.burn_offset_y)
    hex_use = LCD_Set_XY(x, y)
    hex_use.extend(LCD_Set_Size(LCD_X_Size, LCD_Y_Size))
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(7)  # 载入地址
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)

    recv = bytearray()
    for attempt in range(2):  # 容错：一次失败可能是设备瞬时繁忙，重试一次
        recv = SER_rw(hex_use)  # 发出指令
        if len(recv) > 1 and recv[0] == 2 and recv[1] == 3:
            return 1
        time.sleep(0.02)
    print("LCD_ADD failed: %s" % recv)
    set_device_state(0)
    return 0


def LCD_State(LCD_S):
    hex_use = bytearray()
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(10)  # 载入地址
    hex_use.append(LCD_S)
    hex_use.append(0)
    hex_use.append(0)

    recv = bytearray()
    for attempt in range(2):  # 容错：一次失败可能只是设备瞬时繁忙/复位握手残留，重试一次
        recv = SER_rw(hex_use)  # 发出指令
        if len(recv) > 5 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
            # 切换方向后屏幕会变白，用设备实际分辨率清屏（而非固定160x80）
            dev = get_current_device()
            w = dev.LCD_MAX_X if dev is not None else SHOW_WIDTH
            h = dev.LCD_MAX_Y if dev is not None else SHOW_HEIGHT
            LCD_Color_set(0, 0, w, h, (0, 0, 0))
            # print("LCD towards change to: %s" % LCD_S)
            return 1
        time.sleep(0.1)
    print("LCD towards change failed: %s" % recv)
    set_device_state(0)
    return 0


def LCD_DATA(data_w, size):  # 往LCD写入指定大小的数据
    # 先把数据传输完成
    hex_use = bytearray()
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use.append(4)  # 多次写入Flash
        hex_use.append(i)  # 低位地址
        hex_use.append(data_w[i * 4 + 0])  # Data0
        hex_use.append(data_w[i * 4 + 1])  # Data1
        hex_use.append(data_w[i * 4 + 2])  # Data2
        hex_use.append(data_w[i * 4 + 3])  # Data3
    hex_use.append(2)  # 对Flash操作
    hex_use.append(3)  # 经过擦除，写Flash
    hex_use.append(8)  # Data0
    hex_use.append(size // 256)  # Data1
    hex_use.append(size % 256)  # Data2
    hex_use.append(0)  # Data3
    SER_rw(hex_use, read=False)  # 发出指令


# 往Flash里面写入Bin格式的照片
def Write_LCD_Photo_fast(x_star, y_star, x_size, y_size, Photo_name):
    filepath = "%s.bin" % Photo_name  # 合成文件名称
    binfile = None
    try:  # 尝试打开bin文件
        Fsize = os.path.getsize(filepath)
        if Fsize == 0:
            insert_text_message("未读到数据，取消烧录。")
            return 0
        binfile = open(filepath, "rb")  # 以只读方式打开

        insert_text_message("找到\"%s\"文件，大小：%dB" % (filepath, Fsize), cleanNext=False)
        u_time = time.time()
        # 进行地址写入
        LCD_ADD(x_star, y_star, x_size, y_size)
        for i in range(0, Fsize // 256):  # 每次写入一个Page
            Fdata = binfile.read(256)
            LCD_DATA(Fdata, 256)  # (page,数据，大小)
        if Fsize % 256 != 0:  # 还存在没写完的数据
            Fdata = bytearray(binfile.read(Fsize % 256))  # 将剩下的数据读完
            for i in range(Fsize % 256, 256):
                Fdata.append(0xFF)  # 不足位置补充0xFF
            LCD_DATA(Fdata, Fsize % 256)  # (page,数据，大小)
        u_time = time.time() - u_time
        insert_text_message("%s 显示完成，耗时%.1f秒" % (filepath, u_time))
        return 1
    except Exception as e:  # 出现异常
        insert_text_message("找不到文件\"%s\"，%s" % (filepath, e))
        print(traceback.format_exc())
        return 0
    finally:
        if binfile is not None:
            binfile.close()


# 往Flash里面写入Bin格式的照片
def Write_LCD_Photo_fast1(x_star, y_star, x_size, y_size, Photo_name):
    filepath = "%s.bin" % Photo_name  # 合成文件名称
    binfile = None
    try:  # 尝试打开bin文件
        Fsize = os.path.getsize(filepath)
        if Fsize == 0:
            insert_text_message("未读到数据，取消烧录。")
            return 0
        binfile = open(filepath, "rb")  # 以只读方式打开

        insert_text_message("找到\"%s\"文件，大小：%dB" % (filepath, Fsize), cleanNext=False)
        u_time = time.time()
        # 进行地址写入
        LCD_ADD(x_star, y_star, x_size, y_size)
        hex_use = bytearray()
        for j in range(0, Fsize // 256):  # 每次写入一个Page
            data_w = binfile.read(256)
            # 先把数据格式转换好
            for i in range(0, 64):  # 256字节数据分为64个指令
                hex_use.append(4)
                hex_use.append(i)
                hex_use.append(data_w[i * 4 + 0])
                hex_use.append(data_w[i * 4 + 1])
                hex_use.append(data_w[i * 4 + 2])
                hex_use.append(data_w[i * 4 + 3])
            hex_use.append(2)
            hex_use.append(3)
            hex_use.append(8)
            hex_use.append(1)
            hex_use.append(0)
            hex_use.append(0)
        if Fsize % 256 != 0:  # 还存在没写完的数据
            data_w = bytearray(binfile.read(Fsize % 256))  # 将剩下的数据读完
            for i in range(Fsize % 256, 256):
                data_w.append(0xFF)  # 不足位置补充0xFF
            for i in range(0, 64):  # 256字节数据分为64个指令
                hex_use.append(4)
                hex_use.append(i)
                hex_use.append(data_w[i * 4 + 0])
                hex_use.append(data_w[i * 4 + 1])
                hex_use.append(data_w[i * 4 + 2])
                hex_use.append(data_w[i * 4 + 3])
            hex_use.append(2)
            hex_use.append(3)
            hex_use.append(8)
            hex_use.append(0)
            hex_use.append(Fsize % 256)
            hex_use.append(0)
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(9)
        hex_use.append(0)
        hex_use.append(0)
        hex_use.append(0)
        SER_rw(hex_use, read=False)  # 发出指令
        u_time = time.time() - u_time
        insert_text_message("%s 显示完成，耗时%.1f秒" % (filepath, u_time))
        return 1
    except Exception as e:  # 出现异常
        insert_text_message("找不到文件\"%s\"，%s" % (filepath, e))
        print(traceback.format_exc())
        return 0
    finally:
        if binfile is not None:
            binfile.close()


# 往Flash里面写入Bin格式的照片
def Write_LCD_Screen_fast(x_star, y_star, x_size, y_size, Photo_data):
    LCD_ADD(x_star, y_star, x_size, y_size)
    Photo_data_use = Photo_data
    hex_use = bytearray()
    for j in range(0, x_size * y_size * 2 // 256):  # 每次写入一个Page
        data_w = Photo_data_use[:256]
        Photo_data_use = Photo_data_use[256:]
        cmp_use = []
        for i in range(0, 64):  # 256字节数据分为64个指令
            cmp_use.append(
                data_w[i * 4 + 0] * 256 * 256 * 256
                + data_w[i * 4 + 1] * 256 * 256
                + data_w[i * 4 + 2] * 256
                + data_w[i * 4 + 3]
            )
        result = max(set(cmp_use), key=cmp_use.count)  # 统计出现最多的数据
        hex_use.append(2)
        hex_use.append(4)
        color_ram = result
        hex_use.append(color_ram // (256 * 256 * 256))
        color_ram = color_ram % (256 * 256 * 256)
        hex_use.append(color_ram // (256 * 256))
        color_ram = color_ram % (256 * 256)
        hex_use.append(color_ram // 256)
        hex_use.append(color_ram % 256)
        # 先把数据格式转换好
        for i in range(0, 64):  # 256字节数据分为64个指令
            if (data_w[i * 4 + 0] * 256 * 256 * 256
                + data_w[i * 4 + 1] * 256 * 256
                + data_w[i * 4 + 2] * 256
                + data_w[i * 4 + 3]
            ) != result:
                hex_use.append(4)
                hex_use.append(i)
                hex_use.append(data_w[i * 4 + 0])
                hex_use.append(data_w[i * 4 + 1])
                hex_use.append(data_w[i * 4 + 2])
                hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if (x_size * y_size * 2) % 256 != 0:  # 还存在没写完的数据
        data_w = bytearray(Photo_data_use)  # 将剩下的数据读完
        for i in range(x_size * y_size * 2 % 256, 256):
            data_w.append(0xFF)  # 不足位置补充0xFF
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(x_size * y_size * 2 % 256)
        hex_use.append(0)
    SER_rw(hex_use, read=False)  # 发出指令


# 往Flash里面写入Bin格式的照片，对发送的数据进行编码分析,缩短数据指令
def Write_LCD_Screen_fast1(x_star, y_star, x_size, y_size, Photo_data):
    LCD_ADD(x_star, y_star, x_size, y_size)
    Photo_data_use = Photo_data
    hex_use = bytearray()
    for j in range(0, x_size * y_size * 2 // 256):  # 每次写入一个Page
        data_w = Photo_data_use[:256]
        Photo_data_use = Photo_data_use[256:]
        # 先把数据格式转换好
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if (x_size * y_size * 2) % 256 != 0:  # 还存在没写完的数据
        data_w = bytearray(Photo_data_use)  # 将剩下的数据读完
        for i in range(x_size * y_size * 2 % 256, 256):
            data_w.append(0xFF)  # 不足位置补充0xFF
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 4 + 0])
            hex_use.append(data_w[i * 4 + 1])
            hex_use.append(data_w[i * 4 + 2])
            hex_use.append(data_w[i * 4 + 3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(x_size * y_size * 2 % 256)
        hex_use.append(0)
    # 等待传输完成
    hex_use.append(2)
    hex_use.append(3)
    hex_use.append(9)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    SER_rw(hex_use, read=False)  # 发出指令


def LCD_Photo_wb(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    hex_use.extend(LCD_Set_Size(LCD_X_Size, LCD_Y_Size))
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(1)  # 显示单色图片
    hex_use.append(Page_Add // 256)
    hex_use.append(Page_Add % 256)
    hex_use.append(0)
    return hex_use


def LCD_ASCII_32X64(LCD_X, LCD_Y, Txt, Num_Page):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(2)  # 显示ASCII
    hex_use.append(ord(Txt))
    hex_use.append(Num_Page // 256)
    hex_use.append(Num_Page % 256)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == 2 and recv[1] == 3:
        return 1
    else:
        print("LCD_ASCII_32X64 failed: %s" % recv)
        set_device_state(0)  # 接收出错
        return 0


def LCD_GB2312_16X16(LCD_X, LCD_Y, Txt):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    Txt_Data = Txt.encode("gb2312")
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(3)  # 显示彩色图片
    hex_use.append(Txt_Data[0])
    hex_use.append(Txt_Data[1])
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == 2 and recv[1] == 3:
        return 1
    else:
        print("LCD_GB2312_16X16 failed: %s" % recv)
        set_device_state(0)  # 接收出错
        return 0


def LCD_Photo_wb_MIX(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    hex_use.extend(LCD_Set_Size(LCD_X_Size, LCD_Y_Size))
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(4)  # 显示单色图片
    hex_use.append(Page_Add // 256)
    hex_use.append(Page_Add % 256)
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == 2 and recv[1] == 3:
        return 1
    else:
        print("LCD_Photo_wb_MIX failed: %s" % recv)
        set_device_state(0)  # 接收出错
        return 0


def LCD_ASCII_32X64_MIX(LCD_X, LCD_Y, Txt, Num_Page):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(5)  # 显示ASCII
    hex_use.append(ord(Txt))
    hex_use.append(Num_Page // 256)
    hex_use.append(Num_Page % 256)

    return hex_use


def LCD_GB2312_16X16_MIX(LCD_X, LCD_Y, Txt):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    Txt_Data = Txt.encode("gb2312")
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(6)  # 显示彩色图片
    hex_use.append(Txt_Data[0])
    hex_use.append(Txt_Data[1])
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == 2 and recv[1] == 3:
        return 1
    else:
        print("LCD_GB2312_16X16_MIX failed: %s" % recv)
        set_device_state(0)  # 接收出错
        return 0


# 对指定区域进行颜色填充
def LCD_Color_set(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, F_Color):
    rgb565 = ((F_Color[0] & 0xF8) << 8) | ((F_Color[1] & 0xFC) << 3) | ((F_Color[2] & 0xF8) >> 3)
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    hex_use.extend(LCD_Set_Size(LCD_X_Size, LCD_Y_Size))
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(11)  # 显示彩色图片
    hex_use.append(rgb565 // 256)
    hex_use.append(rgb565 % 256)
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == 2 and recv[1] == 3:
        return 1
    else:
        print("LCD_Color_set failed: %s" % recv)
        set_device_state(0)  # 接收出错
        return 0


def show_gif():  # 显示GIF动图
    global config_obj
    dev = get_current_device()
    if dev is None: return
    current_monoto_time = time.monotonic()
    if dev.state_change == 1:
        state_change_clear()
        dev.gif_wait_time = 0
        dev.last_refresh_time = current_monoto_time
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    if dev.gif_num > 35:
        dev.gif_num = 0

    LCD_Photo(dev.gif_num * 100)

    if config_obj.second_times != 0:
        if dev.second_pass < config_obj.second_times:
            dev.second_pass += 1
            dev.sleep_event.wait(1)
            return
        else:
            dev.second_pass = 0

    dev.gif_num = dev.gif_num + 1
    elapse_time = current_monoto_time - dev.last_refresh_time
    dev.last_refresh_time = current_monoto_time
    if elapse_time - config_obj.second_times > config_obj.photo_interval_var + 5:
        dev.gif_wait_time = config_obj.photo_interval_var
    else:
        dev.gif_wait_time += config_obj.photo_interval_var - elapse_time + config_obj.second_times
    if dev.gif_wait_time > 0:
        dev.sleep_event.wait(dev.gif_wait_time)


def show_PC_state(FC, BC):  # 显示PC状态
    dev = get_current_device()
    if dev is None: return
    current_monoto_time = time.monotonic()
    photo_add = 4038
    num_add = 4026
    if dev.state_change == 1:
        state_change_clear()
        dev.wait_time = 0
        dev.last_refresh_time = current_monoto_time
        LCD_Set_Color(FC, BC)
        hex_use = LCD_Photo_wb(0, 0, SHOW_WIDTH, SHOW_HEIGHT, photo_add)  # 放置背景
        recv = SER_rw(hex_use)  # 发出指令
        if len(recv) == 0 or recv[0] != 2 or recv[1] != 3:
            print("show_PC_state failed: %s" % recv)
            set_device_state(0)  # 接收出错

    # CPU
    CPU = round(psutil.cpu_percent(interval=0.5))
    # mem
    mem = psutil.virtual_memory()
    RAM = round(mem.percent)

    # battery
    battery = psutil.sensors_battery()
    if battery is None:
        BAT = 100
    else:
        BAT = round(battery.percent)

    # 获取所有分区磁盘使用率
    # disk_partitions = psutil.disk_partitions()
    # usage_total = 0
    # usage_used = 0
    # for partition in disk_partitions:
    #     try:
    #         usage = psutil.disk_usage(partition.mountpoint)
    #         usage_total += usage.total
    #         usage_used += usage.used
    #     except PermissionError:
    #         # 跳过无权访问的分区
    #         pass
    # if usage_total == 0:
    #     FRQ = 100
    # else:
    #     FRQ = round(usage_used * 100 / usage_total)

    # 获取软件启动所在分区使用率
    disk_info = psutil.disk_usage("/")
    FRQ = round(disk_info.percent)

    # # 磁盘IO
    # FRQ = 0
    # disk_io_counter_cur = psutil.disk_io_counters()
    # disk_used = (disk_io_counter_cur.read_bytes + disk_io_counter_cur.write_bytes
    #              - disk_io_counter.read_bytes - disk_io_counter.write_bytes)
    # if disk_used > 0:
    #     FRQ = round(disk_used / (1024 * 1024))  # MB
    # disk_io_counter = disk_io_counter_cur
    # # 网络IO
    # BAT = 0
    # net_io_counter_cur = psutil.net_io_counters()
    # net_used = (net_io_counter_cur.bytes_sent + net_io_counter_cur.bytes_recv
    #             - net_io_counter.bytes_sent - net_io_counter.bytes_recv)
    # if net_used > 0:
    #     BAT = round(net_used / (1024 * 1024 / 8))  # Mb
    # net_io_counter = net_io_counter_cur

    hex_use = bytearray()

    if CPU >= 100:
        hex_use.extend(LCD_Photo_wb(24, 0, 8, 33, 10 + num_add))
        CPU = CPU % 100
    else:
        hex_use.extend(LCD_Photo_wb(24, 0, 8, 33, 11 + num_add))
    hex_use.extend(LCD_Photo_wb(32, 0, 24, 33, (CPU // 10) + num_add))
    hex_use.extend(LCD_Photo_wb(56, 0, 24, 33, (CPU % 10) + num_add))
    if RAM >= 100:
        hex_use.extend(LCD_Photo_wb(104, 0, 8, 33, 10 + num_add))
        RAM = RAM % 100
    else:
        hex_use.extend(LCD_Photo_wb(104, 0, 8, 33, 11 + num_add))
    hex_use.extend(LCD_Photo_wb(112, 0, 24, 33, (RAM // 10) + num_add))
    hex_use.extend(LCD_Photo_wb(136, 0, 24, 33, (RAM % 10) + num_add))
    if BAT >= 100:
        hex_use.extend(LCD_Photo_wb(104, 47, 8, 33, 10 + num_add))
        BAT = BAT % 100
    else:
        hex_use.extend(LCD_Photo_wb(104, 47, 8, 33, 11 + num_add))
    hex_use.extend(LCD_Photo_wb(112, 47, 24, 33, (BAT // 10) + num_add))
    hex_use.extend(LCD_Photo_wb(136, 47, 24, 33, (BAT % 10) + num_add))
    if FRQ >= 100:
        hex_use.extend(LCD_Photo_wb(24, 47, 8, 33, 10 + num_add))
        FRQ = FRQ % 100
    else:
        hex_use.extend(LCD_Photo_wb(24, 47, 8, 33, 11 + num_add))
    hex_use.extend(LCD_Photo_wb(32, 47, 24, 33, (FRQ // 10) + num_add))
    hex_use.extend(LCD_Photo_wb(56, 47, 24, 33, (FRQ % 10) + num_add))
    recv = SER_rw(hex_use, size=6 * 12)  # 发出指令
    if len(recv) == 0 or recv[0] != 2 or recv[1] != 3:
        print("show_PC_state failed: %s" % recv)
        set_device_state(0)  # 接收出错

    # 实时预览：软件渲染系统状态
    if config_obj:
        rgb_tuple = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
        _update_preview_state(CPU, RAM, BAT, FRQ, rgb_tuple)

    seconds_elapsed = current_monoto_time - dev.last_refresh_time
    dev.last_refresh_time = current_monoto_time
    dev.wait_time += 1 - seconds_elapsed
    if dev.wait_time > 0:
        dev.sleep_event.wait(dev.wait_time)


def show_Photo():  # 显示照片
    dev = get_current_device()
    if dev is None: return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    LCD_Photo(3926)  # 放置背景
    dev.sleep_event.wait(1)  # 1秒刷新一次


def _update_preview_clock(hour, minute, color_tuple):
    """软件渲染时钟预览图像"""
    global _preview_rgb
    if not config_obj or not config_obj.preview_enabled:
        return
    try:
        img = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        time_str = "%02d:%02d" % (hour, minute)
        font = _load_font("./simhei.ttf", 36)
        bbox = draw.textbbox((0, 0), time_str, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (SHOW_WIDTH - tw) // 2
        y = (SHOW_HEIGHT - th) // 2
        draw.text((x, y), time_str, fill=color_tuple, font=font)
        dev = get_current_device()
        if dev:
            with dev._preview_lock:
                dev.last_preview_rgb = np.asarray(img, dtype=np.uint8)
                _preview_rgb = dev.last_preview_rgb
    except Exception:
        pass


def _update_preview_state(cpu, ram, bat, frq, color_tuple):
    """软件渲染系统状态预览图像"""
    global _preview_rgb
    if not config_obj or not config_obj.preview_enabled:
        return
    try:
        img = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = _load_font("./simhei.ttf", 16)
        lines = [
            "CPU %3d%%  MEM %3d%%" % (cpu, ram),
            "BAT %3d%%  DSK %3d%%" % (bat, frq),
        ]
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            x = (SHOW_WIDTH - tw) // 2
            y = SHOW_HEIGHT // 4 + i * (SHOW_HEIGHT // 2)
            draw.text((x, y), line, fill=color_tuple, font=font)
        dev = get_current_device()
        if dev:
            with dev._preview_lock:
                dev.last_preview_rgb = np.asarray(img, dtype=np.uint8)
                _preview_rgb = dev.last_preview_rgb
    except Exception:
        pass


def show_PC_time(FC):
    """显示24小时制 HH:MM 大字时间（32x64字体，满屏）"""
    dev = get_current_device()
    if dev is None: return
    num_add = 3651  # ASC64 大字库
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        LCD_Set_Color(FC, BLACK)
        LCD_Color_set(0, 0, SHOW_WIDTH, SHOW_HEIGHT, (0, 0, 0))

    current_time = datetime.now()
    time_h = int(current_time.hour)
    time_m = int(current_time.minute)

    # 4位大数字 HH:MM, 居中满屏: 4×32+16(间隔)=144, 偏移8居中
    LCD_ASCII_32X64(8, 8, chr((time_h // 10) + 48), num_add)
    LCD_ASCII_32X64(40, 8, chr((time_h % 10) + 48), num_add)
    LCD_ASCII_32X64(88, 8, chr((time_m // 10) + 48), num_add)
    LCD_ASCII_32X64(120, 8, chr((time_m % 10) + 48), num_add)

    # 实时预览：软件渲染时钟
    _update_preview_clock(time_h, time_m, FC)

    if time_m != 59:
        dev.sleep_event.wait(1)
    else:
        dev.sleep_event.wait(1 - current_time.microsecond / 1000000.0)


def digit_to_ints(di):
    return [(di >> 24) & 0xFF, (di >> 16) & 0xFF, (di >> 8) & 0xFF, di & 0xFF]


def Screen_Date_Process(Photo_data):  # 对数据进行转换处理
    total_data_size = len(Photo_data)  # SHOW_WIDTH * SHOW_HEIGHT ?
    # 防御：校验输入数据长度与LCD分辨率匹配
    expected_pixels = LCD_MAX_X * LCD_MAX_Y
    if total_data_size != expected_pixels:
        print("Screen_Date_Process: 数据长度异常 actual=%d expected=%d (LCD %dx%d), 返回空数据"
              % (total_data_size, expected_pixels, LCD_MAX_X, LCD_MAX_Y))
        return bytearray()
    data_per_page = 128
    data_page1 = 0
    data_page2 = 0
    hex_use = bytearray()
    for j in range(0, total_data_size // data_per_page):  # 每次写入一个Page
        data_page1 = data_page2
        data_page2 += data_per_page
        data_w = Photo_data[data_page1: data_page2]
        # 将相邻两个 RGB565 像素打包为一个 32 位值（高16位=偶数像素，低16位=奇数像素）。
        # 必须先提升为 uint32 再左移：uint16 << 16 会溢出归零，
        # 导致偶数像素颜色全部丢失，画面出现栅栏/斜切（小屏倾斜而预览正常）。
        cmp_use = (data_w[::2].astype(np.uint32) << 16) | data_w[1::2].astype(np.uint32)

        # 找最频繁的颜色作为背景色填充整个区域
        u, c = np.unique(cmp_use, return_counts=True)
        result = u[c.argmax()]
        hex_use.extend([2, 4])
        hex_use.extend(digit_to_ints(result))

        # 填充与背景色不同的像素
        for i, cmp_value in enumerate(cmp_use):
            if cmp_value != result:
                hex_use.extend([4, i])
                hex_use.extend(digit_to_ints(cmp_value))

        # Append footer
        hex_use.extend([2, 3, 8, 1, 0, 0])

    remaining_data_size = total_data_size % data_per_page
    if remaining_data_size != 0:  # 还存在没写完的数据
        data_w = Photo_data[-remaining_data_size:]  # 取最后的没有写的
        # 补全128个 uint16
        data_w = np.append(data_w, np.full(data_per_page - remaining_data_size, 0xFF, dtype=np.uint32))
        # 同上：提升为 uint32，避免 uint16 左移溢出导致偶数像素丢失
        cmp_use = (data_w[::2].astype(np.uint32) << 16) | data_w[1::2].astype(np.uint32)
        for i, cmp_value in enumerate(cmp_use):
            hex_use.extend([4, i])
            hex_use.extend(digit_to_ints(cmp_value))
        hex_use.extend([2, 3, 8, 0, remaining_data_size * 2, 0])
    return hex_use


# in: [[[255 255 255]]], type: np.asarray((((r, g, b),),)), out: [[rgb565_int]]
def rgb888_to_rgb565(rgb888_array):
    # 防御：校验输入维度
    if rgb888_array.ndim != 3 or rgb888_array.shape[2] != 3:
        raise ValueError("rgb888_to_rgb565: 输入必须为 (H, W, 3) 形状, 实际为 %s" % str(rgb888_array.shape))
    # 防御：校验尺寸与LCD匹配
    if rgb888_array.shape[0] != LCD_MAX_Y or rgb888_array.shape[1] != LCD_MAX_X:
        raise ValueError("rgb888_to_rgb565: 图像尺寸 (%d, %d) 与LCD (%d, %d) 不匹配"
                         % (rgb888_array.shape[0], rgb888_array.shape[1], LCD_MAX_Y, LCD_MAX_X))
    # 防御：确保dtype至少为uint16，防止uint8位移溢出（uint8 << 8 = 0）
    if rgb888_array.dtype == np.uint8:
        rgb888_array = rgb888_array.astype(np.uint16)
    # Convert RGB888 to RGB565
    r = (rgb888_array[:, :, 0] & 0xF8) << 8  # 5 bits for red
    g = (rgb888_array[:, :, 1] & 0xFC) << 3  # 6 bits for green
    b = (rgb888_array[:, :, 2] & 0xF8) >> 3  # 5 bits for blue

    # r = r.astype(np.uint16)
    # g = g.astype(np.uint16)
    # b = b.astype(np.uint16)

    # Combine into RGB565 format
    rgb565 = r | g | b

    # Convert to a 16-bit unsigned integer array
    # return rgb565.astype(np.uint16)
    return rgb565


# in: rgb565_int, out: rgb_tuple(r, g, b)
def rgb565_to_rgb888(rgb565_int):
    return (rgb565_int >> 8) & 0xF8, (rgb565_int >> 3) & 0xFC, (rgb565_int << 3) & 0xF8


def shrink_image_block_average(image, shrink_factor):
    """
    图像每一块多次采样，最后平均

    Parameters:
    image (numpy.ndarray): The input image as a 2D (grayscale) or 3D (color) numpy array.
    shrink_factor (float): The factor by which the image dimensions are reduced.

    Returns:
    numpy.ndarray: The shrunk image.
    """

    # 使用精确整数运算计算目标尺寸，彻底避免浮点精度问题
    # 例如 1080 / (1080/80) 可能得到 79.9999，直接使用比例关系更可靠
    if image.shape[0] / shrink_factor >= image.shape[1] / shrink_factor:
        # 高度方向比例更大，以行数为准
        target_rows = int(image.shape[0] / shrink_factor + 0.5)
        target_cols = int(image.shape[1] * target_rows / image.shape[0] + 0.5)
    else:
        target_cols = int(image.shape[1] / shrink_factor + 0.5)
        target_rows = int(image.shape[0] * target_cols / image.shape[1] + 0.5)
    new_shape = (max(1, target_rows), max(1, target_cols))

    shrunk_parts = []
    # 4倍多重采样
    for rand in [(0.0, 0.0), (0.25, 0.5), (0.5, 0.25), (0.75, 0.75)]:
        start = (shrink_factor * rand[0], shrink_factor * rand[1])
        stop = (start[0] + image.shape[0] - 1, start[1] + image.shape[1] - 1)
        row_indices = np.round(np.linspace(start[0], stop[0] - shrink_factor, new_shape[0])).astype(np.uint32)
        col_indices = np.round(np.linspace(start[1], stop[1] - shrink_factor, new_shape[1])).astype(np.uint32)

        # Handle color and grayscale images
        if image.ndim == 3:
            shrunk_image = image[np.ix_(row_indices, col_indices, np.arange(image.shape[2]))]
        else:
            shrunk_image = image[np.ix_(row_indices, col_indices)]
        shrunk_parts.append(shrunk_image)

    result = np.mean(shrunk_parts, axis=0, dtype=np.uint32)
    # 防御：若结果维度与目标不一致（极端浮点情况），强制修正
    if result.shape[0] != new_shape[0] or result.shape[1] != new_shape[1]:
        print("shrink_image_block_average: 维度修正 %s -> (%d, %d)" % (str(result.shape), new_shape[0], new_shape[1]))
        if result.ndim == 3:
            # 使用cv2.resize进行精确尺寸修正
            result = cv2.resize(result.astype(np.uint8), (new_shape[1], new_shape[0]),
                               interpolation=cv2.INTER_LINEAR).astype(np.uint32)
        else:
            result = cv2.resize(result.astype(np.uint8), (new_shape[1], new_shape[0]),
                               interpolation=cv2.INTER_LINEAR).astype(np.uint32)
    return result

    # 下面的算法可以用（每块所有像素平均），但是慢，所以用上面的简单算法，取少数几个点
    # # Calculate integer block size for averaging
    # block_size = int(np.floor(shrink_factor))
    #
    # # Calculate the shape after block averaging
    # new_shape = (image.shape[0] // block_size, image.shape[1] // block_size)
    #
    # # Perform block averaging
    # if image.ndim == 3:  # Color image
    #     averaged_image = (image.reshape(new_shape[0], block_size, new_shape[1], block_size, image.shape[2])
    #                       .mean(axis=(1, 3), dtype=np.uint32))
    # else:  # Grayscale image
    #     averaged_image = (image.reshape(new_shape[0], block_size, new_shape[1], block_size)
    #                       .mean(axis=(1, 3), dtype=np.uint32))
    #
    # # Nearest neighbor interpolation to handle fractional part
    # final_shape = (round(image.shape[0] / shrink_factor), round(image.shape[1] / shrink_factor))
    #
    # row_indices = np.round(np.linspace(0, averaged_image.shape[0] - 1, final_shape[0])).astype(np.uint32)
    # col_indices = np.round(np.linspace(0, averaged_image.shape[1] - 1, final_shape[1])).astype(np.uint32)
    #
    # # Handle color and grayscale images
    # if image.ndim == 3:
    #     shrunk_image = averaged_image[np.ix_(row_indices, col_indices, np.arange(image.shape[2]))].astype(np.uint8)
    # else:
    #     shrunk_image = averaged_image[np.ix_(row_indices, col_indices)].astype(np.uint8)
    # return shrunk_image


def set_select_hwnd(hwnd):
    global config_obj
    config_obj.select_window_hwnd = hwnd
    save_config()
    # 递增帧代际，使正在处理中的旧窗口帧被丢弃
    dev = get_current_device()
    if dev is not None:
        dev.screen_frame_generation += 1
        clear_queue(dev.screen_shot_queue)  # 清空缓存，防止显示旧的窗口
        clear_queue(dev.screen_process_queue)  # 清空缓存，防止显示旧的窗口
    desc = get_hwnd_desc(hwnd)
    if not desc:
        desc = hwnd
    ctx = _cur_main_ctx()
    wcb = ctx.get('windows_combobox') if ctx else None
    if wcb is not None:
        wcb.setCurrentText(desc)


def clear_queue(queue):
    for _ in range(queue.qsize()):
        queue.get()


def screen_shot_task(device=None):
    global config_obj, all_cameras, desktop_hwnd
    if device is None:
        device = get_current_device()
    set_current_device(device)
    dev = device
    # mss GDI句柄是线程本地的，每个线程必须独立创建mss实例
    _thread_mss = mss()
    if not isWindows:
        monitor = _thread_mss.monitors[0]
        cropped_monitor = monitor
        cropped_monitor["mon"] = 0

    dev.wait_time = 0
    dev.screenshot_last_limit_time = time.monotonic()
    print("Start screenshot")
    while dev.mg_screen_thread_running:
        # 多屏隔离：每次迭代取本设备最新配置（设备重连替换 dev.config 后也能及时用上）
        cfg = dev.config if dev.config is not None else config_obj
        if dev.device_state != 1 or (cfg.state_machine != SCREEN_PAGE_ID
                                 and cfg.state_machine != CAMERA_VIDEO_ID):
            if not dev.screen_shot_queue.empty():
                time.sleep(0.5)
                clear_queue(dev.screen_shot_queue)
            time.sleep(0.5)
            continue
        if dev.screen_shot_queue.full():
            time.sleep(1.0 / cfg.fps_var)

        try:
            if cfg.state_machine == CAMERA_VIDEO_ID:
                camera_id = all_cameras.get(cfg.camera_var)
                if camera_id is None:
                    rgb888 = get_draw_text("请选择相机…")
                    image = Win32_Image(rgb=rgb888, size=(dev.LCD_MAX_X, dev.LCD_MAX_Y))
                    dev.screen_shot_queue.put((image, {"width": dev.LCD_MAX_X, "height": dev.LCD_MAX_Y}), timeout=1)
                    time.sleep(0.5)
                    continue

                rgb888 = get_draw_text("打开中…")
                image = Win32_Image(rgb=rgb888, size=(dev.LCD_MAX_X, dev.LCD_MAX_Y))
                dev.screen_shot_queue.put((image, {"width": dev.LCD_MAX_X, "height": dev.LCD_MAX_Y}), timeout=1)
                camera_name = cfg.camera_var
                cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                try:
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, dev.LCD_MAX_X)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, dev.LCD_MAX_Y)
                        # cap.set(cv2.CAP_PROP_FPS, config_obj.fps_var)  # 这个程序中相机fps无效
                        # cap.set(cv2.CAP_PROP_EXPOSURE, 4)  # 曝光度调节
                        # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 缓冲帧数量大小
                        # cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 是否将图像转为RGB，取值0/1
                        # cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))  # 设置视频编码为MJPG
                        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        last_time = time.monotonic()
                        while (dev.mg_screen_thread_running and dev.device_state == 1
                               and cfg.state_machine == CAMERA_VIDEO_ID
                               and camera_name == cfg.camera_var):
                            cap_hue = cap.get(cv2.CAP_PROP_HUE)
                            if cap_hue == 13:
                                time.sleep(1)
                                raise Exception("get CAP_PROP_HUE failed")
                            if dev.screen_shot_queue.full():
                                time.sleep(1.0 / cfg.fps_var)
                            suc, frame = cap.read()
                            if not suc:
                                raise Exception("cap.read() failed")
                            current_time = time.monotonic()
                            if current_time - last_time > 5.0:
                                raise Exception("cap.read() timeout")
                            last_time = current_time
                            image = Win32_Image(rgb=frame[:, :, [2, 1, 0]], size=(width, height))
                            try:
                                dev.screen_shot_queue.put((image, {"width": width, "height": height}), timeout=1)
                            except queue.Full:
                                time.sleep(1.0 / cfg.fps_var)
                                continue
                            fps_control(dev)
                    else:
                        raise Exception("capture open failed")
                finally:
                    cap.release()
            elif isWindows:
                if cfg.zoom_enable:
                    # 放大镜模式：截取鼠标周围区域并放大显示
                    try:
                        import win32api
                        x, y = win32api.GetCursorPos()
                    except Exception:
                        x, y = 0, 0
                    scale = max(1, int(cfg.zoom_scale))
                    w = max(8, dev.LCD_MAX_X // scale)
                    h = max(8, dev.LCD_MAX_Y // scale)
                    left = max(0, x - w // 2)
                    top = max(0, y - h // 2)
                    mon = {"left": left, "top": top, "width": w, "height": h}
                    try:
                        grab = _thread_mss.grab(mon)
                        bgra = np.frombuffer(grab.rgb, dtype=np.uint8).reshape((h, w, 4))
                        rgb = bgra[:, :, [2, 1, 0]]
                        image = Win32_Image(rgb=rgb, size=(w, h))
                        dev.screen_shot_queue.put((image, {"width": w, "height": h}), timeout=1)
                    except Exception:
                        pass
                else:
                    sct_img = get_window_image(cfg.select_window_hwnd)
                    dev.screen_shot_queue.put((sct_img, {"width": sct_img.size[0], "height": sct_img.size[1]}), timeout=1)
            else:
                sct_img = _thread_mss.grab(cropped_monitor)
                dev.screen_shot_queue.put((sct_img, cropped_monitor), timeout=1)
        except queue.Full:
            time.sleep(1.0 / cfg.fps_var)
            continue
        except Exception as e:
            print("获取图像失败 %s" % traceback.format_exc())
            image = Win32_Image(rgb=bytes(6), size=(2, 1))
            dev.screen_shot_queue.put((image, {"width": 2, "height": 1}), timeout=1)
            time.sleep(0.5)
            continue

        fps_control(dev)

    # stop
    print("Stop screenshot")


def fps_control(device=None):
    if device is None:
        device = get_current_device()
    dev = device
    # 多屏隔离：fps 用本设备配置，避免全局 config_obj 被 daemon 切换导致节奏错乱
    fps = max(1, getattr(dev.config if dev.config is not None else config_obj, "fps_var", 30))
    current_monoto_time = time.monotonic()
    elapse_time = current_monoto_time - dev.screenshot_last_limit_time
    if elapse_time > 5:
        dev.wait_time = 0
        elapse_time = 1.0 / fps

    dev.screenshot_last_limit_time = current_monoto_time
    dev.wait_time += 1.0 / fps - elapse_time
    if dev.wait_time > 0:
        dev.sleep_event.wait(dev.wait_time)
    elif dev.wait_time < -5:
        dev.wait_time = 0


# geezmo: 流水线 第二步 处理图像
def screen_process_task(device=None):
    global config_obj
    if device is None:
        device = get_current_device()
    dev = device
    set_current_device(device)
    print("Start screen process")
    while dev.mg_screen_thread_running:
        # 多屏隔离：每次迭代取本设备最新配置（设备重连替换 dev.config 后也能及时用上）
        cfg = dev.config if dev.config is not None else config_obj
        if dev.device_state != 1 or (cfg.state_machine != SCREEN_PAGE_ID
                                 and cfg.state_machine != CAMERA_VIDEO_ID):
            if not dev.screen_process_queue.empty():
                time.sleep(0.5)
                clear_queue(dev.screen_process_queue)
            time.sleep(0.5)
            continue

        try:
            if dev.screen_process_queue.full():
                time.sleep(1.0 / cfg.fps_var)

            frame_gen = dev.screen_frame_generation

            sct_img, monitor = dev.screen_shot_queue.get(timeout=2)
            if sct_img.rgb is None:
                # win32gui截图 (PrintWindow API)
                bgra = sct_img.bgra
                img_w, img_h = sct_img.size
                # 防御：尺寸有效性校验
                if img_w <= 0 or img_h <= 0:
                    print("screen_process_task: 截图尺寸无效 (%d, %d), 跳过此帧" % (img_w, img_h))
                    continue
                expected_len = img_h * img_w * 4
                actual_len = len(bgra)
                remain = expected_len - actual_len

                if remain == 0:
                    # 正常窗口：数据长度完全匹配
                    bgra = np.frombuffer(bgra, dtype=np.uint8).reshape((img_h, img_w, 4))
                    rgb = bgra[:, :, [2, 1, 0]]
                elif remain > 0:
                    # 数据不足（如最小化窗口），用0填充缺失部分
                    bgra += bytes(remain)
                    bgra = np.frombuffer(bgra, dtype=np.uint8).reshape((img_h, img_w, 4))
                    rgb = bgra[:, :, [2, 1, 0]]
                else:
                    # 数据多于预期（DPI缩放不一致、或非标准窗口框架）
                    # 从实际数据量反推真实行数，而不是用 sct_img.size
                    bytes_per_row = actual_len // img_h
                    if bytes_per_row > 0 and bytes_per_row % 4 == 0:
                        real_w = bytes_per_row // 4
                        # 截取到完整行
                        bgra = bgra[:img_h * bytes_per_row]
                        bgra = np.frombuffer(bgra, dtype=np.uint8).reshape((img_h, real_w, 4))
                        # 裁剪到期望宽度（取中间部分）
                        if real_w > img_w:
                            offset = (real_w - img_w) // 2
                            bgra = bgra[:, offset:offset + img_w, :]
                        elif real_w < img_w:
                            # 宽度不足，右侧补零
                            pad_w = img_w - real_w
                            bgra = np.pad(bgra, ((0, 0), (0, pad_w), (0, 0)), mode='constant')
                        rgb = bgra[:, :, [2, 1, 0]]
                    else:
                        # 无法可靠解析，跳过这一帧
                        print("screen_process_task: 无法解析窗口截图, expected=%d, actual=%d, size=%dx%d"
                              % (expected_len, actual_len, img_w, img_h))
                        continue
                # 防御：验证RGB图像维度正确 (H, W, 3)
                if rgb.ndim != 3 or rgb.shape[2] != 3:
                    print("screen_process_task: RGB转换后维度异常 shape=%s, 跳过此帧" % str(rgb.shape))
                    continue
            else:
                rgb = sct_img.rgb  # 相机视频
                if type(rgb) == bytes:  # sct.grab截图
                    # 防御：尺寸有效性校验
                    if sct_img.size[0] <= 0 or sct_img.size[1] <= 0:
                        print("screen_process_task: mss截图尺寸无效 %s, 跳过此帧" % str(sct_img.size))
                        continue
                    rgb = np.frombuffer(rgb, dtype=np.uint8).reshape((sct_img.size[1], sct_img.size[0], 3))
                # 防御：验证RGB图像维度正确
                if rgb.ndim != 3 or rgb.shape[2] != 3:
                    print("screen_process_task: 视频帧维度异常 shape=%s, 跳过此帧" % str(rgb.shape))
                    continue

            # 是否需要旋转90度
            # if sct_img.size[1] > sct_img.size[0]:
            #     rgb = np.rot90(rgb, 1)

            # 防御：校验rgb维度与monitor一致，防止队列中数据不一致导致后续计算错误
            if rgb.shape[0] != monitor["height"] or rgb.shape[1] != monitor["width"]:
                print("screen_process_task: rgb/monitor尺寸不一致 rgb=%dx%d monitor=%dx%d, 跳过此帧"
                      % (rgb.shape[0], rgb.shape[1], monitor["height"], monitor["width"]))
                continue

            # 压缩图像到LCD屏幕尺寸，不足的填充
            width = monitor["width"]
            heightx2 = monitor["height"] * 2
            if cfg.shrink_type == 1:
                # 方法1：裁剪以 填充屏幕
                if width > heightx2:  # 图片长宽比例超过2:1
                    im1 = shrink_image_block_average(rgb, rgb.shape[0] / LCD_MAX_Y)
                    # 防御：若缩略后宽度不足，回退到填充模式
                    if im1.shape[1] < LCD_MAX_X:
                        print("screen_process_task: crop路径宽度不足 %d < %d, 回退pad模式" % (im1.shape[1], LCD_MAX_X))
                        im1 = shrink_image_block_average(rgb, rgb.shape[1] / LCD_MAX_X)
                        total = LCD_MAX_Y - im1.shape[0]
                        if total > 0:
                            np_fill_zero = row_np_zero.repeat(total // 2, axis=0)
                            if total % 2:
                                im1 = np.row_stack((np_fill_zero, im1, np_fill_zero, row_np_zero))
                            else:
                                im1 = np.row_stack((np_fill_zero, im1, np_fill_zero))
                    else:
                        offset = max(0, (im1.shape[1] - LCD_MAX_X) // 2)
                        im1 = im1[:, offset: LCD_MAX_X + offset]
                else:  # 纵向裁剪
                    im1 = shrink_image_block_average(rgb, rgb.shape[1] / LCD_MAX_X)
                    # 防御：若缩略后高度不足，回退到填充模式
                    if im1.shape[0] < LCD_MAX_Y:
                        print("screen_process_task: crop路径高度不足 %d < %d, 回退pad模式" % (im1.shape[0], LCD_MAX_Y))
                        im1 = shrink_image_block_average(rgb, rgb.shape[0] / LCD_MAX_Y)
                        total = LCD_MAX_X - im1.shape[1]
                        if total > 0:
                            np_fill_zero = column_np_zero.repeat(total // 2, axis=1)
                            if total % 2:
                                im1 = np.column_stack((np_fill_zero, im1, np_fill_zero, column_np_zero))
                            else:
                                im1 = np.column_stack((np_fill_zero, im1, np_fill_zero))
                    else:
                        offset = max(0, (im1.shape[0] - LCD_MAX_Y) // 2)
                        im1 = im1[offset: LCD_MAX_Y + offset, :]
            else:
                # 方法2：填充空白以 适应屏幕
                if width > heightx2:  # 图片长宽比例超过2:1
                    im1 = shrink_image_block_average(rgb, rgb.shape[1] / LCD_MAX_X)
                    total = LCD_MAX_Y - len(im1)
                    np_fill_zero = row_np_zero.repeat(total // 2, axis=0)
                    if total % 2:
                        im1 = np.row_stack((np_fill_zero, im1, np_fill_zero, row_np_zero))
                    else:
                        im1 = np.row_stack((np_fill_zero, im1, np_fill_zero))
                elif width == heightx2:  # 纵向充满
                    im1 = shrink_image_block_average(rgb, rgb.shape[0] / LCD_MAX_Y)
                else:
                    im1 = shrink_image_block_average(rgb, rgb.shape[0] / LCD_MAX_Y)
                    total = LCD_MAX_X - len(im1[0])
                    np_fill_zero = column_np_zero.repeat(total // 2, axis=1)
                    if total % 2:
                        im1 = np.column_stack((np_fill_zero, im1, np_fill_zero, column_np_zero))
                    else:
                        im1 = np.column_stack((np_fill_zero, im1, np_fill_zero))

            # 维度校验：防止因浮点精度或尺寸计算错误导致画面倾斜/斜切
            if im1.shape[0] != LCD_MAX_Y or im1.shape[1] != LCD_MAX_X:
                print("screen_process_task: 图像维度异常 (%d, %d), 期望 (%d, %d), 跳过此帧"
                      % (im1.shape[0], im1.shape[1], LCD_MAX_Y, LCD_MAX_X))
                continue

            # 防御：将图像转为uint16以确保rgb888_to_rgb565中位移操作不会溢出
            # （uint8的<<8会溢出归零，uint16/uint32安全）
            im1 = im1.astype(np.uint16)

            # 实时预览：保存屏幕镜像图像供UI刷新（per-device）
            if cfg and cfg.preview_enabled:
                with dev._preview_lock:
                    dev.last_preview_rgb = im1.astype(np.uint8).copy()
                    _preview_rgb = dev.last_preview_rgb  # 全局兼容

            # 转化为可直接写入小屏幕的格式
            rgb565 = rgb888_to_rgb565(im1)
            # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
            hexstream = Screen_Date_Process(rgb565.flatten())

            # 防御：校验hexstream合理性（不应为空，也不应异常巨大）
            if len(hexstream) == 0:
                print("screen_process_task: hexstream为空, 跳过此帧")
                continue
            if len(hexstream) > LCD_MAX_X * LCD_MAX_Y * 6 + 256:
                print("screen_process_task: hexstream过大 %d bytes, 跳过此帧" % len(hexstream))
                continue

            # 防御：帧代际校验——处理期间若窗口已切换，丢弃此帧
            if frame_gen != dev.screen_frame_generation:
                continue

            dev.screen_process_queue.put(hexstream, timeout=1)
        except (queue.Empty, queue.Full):
            continue
        except Exception as e:
            print("screen_process_task error: %s" % traceback.format_exc())
            time.sleep(0.2)

    # stop
    print("Stop screen process")


# 重启截图线程
def screenshot_panic(clean_queue=True):
    dev = get_current_device()
    if dev is None: return
    dev.mg_screen_thread_running = False
    old_shot = dev.screen_shot_thread
    old_process = dev.screen_process_thread
    dev.screen_shot_thread = threading.Thread(target=screen_shot_task, args=(dev,), daemon=True)
    dev.screen_process_thread = threading.Thread(target=screen_process_task, args=(dev,), daemon=True)

    if clean_queue:
        clear_queue(dev.screen_shot_queue)
        clear_queue(dev.screen_process_queue)
    if old_shot and old_shot.is_alive():
        old_shot.join()
    if old_process and old_process.is_alive():
        old_process.join()

    dev.mg_screen_thread_running = True
    dev.screen_shot_thread.start()
    dev.screen_process_thread.start()


def show_PC_Screen():  # 显示屏幕镜像 / 相机视频
    dev = get_current_device()
    if dev is None: return
    # 串口渲染事务标志：LCD_ADD与帧数据之间/帧发送期间阻止按键ADC插入，防命令流交错导致画面倾斜
    dev.serial_busy = True
    try:
        if dev.state_change == 1:
            state_change_clear()
            # 切换后彻底重置：清空处理队列，丢弃切换前生成的旧帧
            clear_queue(dev.screen_process_queue)
            if not LCD_ADD(0, 0, dev.LCD_MAX_X, dev.LCD_MAX_Y):
                print("show_PC_Screen: LCD_ADD失败, 触发LCD方向重置")
                dev.force_lcd_reset = True
                return

        try:
            hexstream = dev.screen_process_queue.get(timeout=0.3)
        except queue.Empty:
            return
        # 防御：发送跟不上时丢弃堆积的旧帧，只发送最新一帧，避免延迟累积和旧帧混入
        while not dev.screen_process_queue.empty():
            try:
                hexstream = dev.screen_process_queue.get_nowait()
            except queue.Empty:
                break
        if len(hexstream) == 0:
            print("show_PC_Screen: 收到空数据，跳过发送")
            return
        try:
            SER_rw(hexstream, read=False)
        except Exception as e:
            print("show_PC_Screen: 发送失败 %s, 触发LCD方向重置" % e)
            dev.force_lcd_reset = True
            return
        # 防御：发送期间若发生切换(切页/切窗口/切方向)，立即结束本轮，
        # 由状态机下一轮统一执行LCD方向重置，避免继续发送旧页面数据造成错位
        if dev.state_change == 1 or dev.force_lcd_reset:
            return
    finally:
        dev.serial_busy = False


def sizeof_fmt(num, suffix="B", base=1024.0):
    num = abs(num)
    if num < base:
        if 0 < num < 0.5:  # 小于0.5才显示mA/mV/mW/mWh/mL
            return "%3.1fm%s" % (num * base, suffix)
        return "%3.1f%s" % (num, suffix)
    for unit in ("K", "M", "G", "T", "P", "E", "Z"):
        num /= base
        if num < base:
            return "%3.1f%s%s" % (num, unit, suffix)
    return "%3.1fY%s" % (num, suffix)


BAR_WIDTH = 2  # 每个点宽度
IMAGE_HEIGHT = SHOW_HEIGHT // 4  # 高度
last_data_half = (0, 0)


_preview_rgb = None  # 实时预览用的RGB888图像缓存 (H, W, 3) uint8
_preview_lock = threading.Lock()  # 预览图像读写锁


def _safe_send_rgb888(rgb888_array):
    """防御性安全发送：将RGB888数组编码为RGB565后发送到LCD，异常时自动恢复LCD方向"""
    global _preview_rgb
    dev = get_current_device()
    if dev is None: return
    # 实时预览：保存RGB888图像供UI刷新
    if config_obj and config_obj.preview_enabled:
        with dev._preview_lock:
            dev.last_preview_rgb = rgb888_array.astype(np.uint8).copy()
            _preview_rgb = dev.last_preview_rgb  # 全局兼容
    try:
        rgb565 = rgb888_to_rgb565(rgb888_array)
        hex_use = Screen_Date_Process(rgb565.flatten())
        if len(hex_use) == 0:
            print("_safe_send_rgb888: Screen_Date_Process返回空数据, 触发LCD方向重置")
            dev.force_lcd_reset = True
            return
        # 串口渲染事务标志：发送期间阻止按键ADC命令插入，避免命令流交错导致画面倾斜
        dev.serial_busy = True
        try:
            SER_rw(hex_use, read=False)
        finally:
            dev.serial_busy = False
    except ValueError as e:
        print("_safe_send_rgb888: 编码异常 %s, 触发LCD方向重置" % e)
        dev.force_lcd_reset = True
    except Exception as e:
        print("_safe_send_rgb888: 发送异常 %s, 触发LCD方向重置" % traceback.format_exc())
        dev.force_lcd_reset = True


# ==================== API 投屏服务器（本地 HTTP + WebSocket） ====================
# 外部程序可通过 REST API / WebSocket 接入，自定义投屏内容（图像/文本/清屏/切页/实时帧）。
# 默认仅监听 127.0.0.1:8632，可在「设置 → API接入」中配置端口与令牌。
# ⚠ 维护约定：新增/修改/删除 API 端点时，必须同步更新 _build_openapi_doc() 中的 paths 与 schemas，
#   并保证 API 文档页(_API_DOC_HTML)说明同步。启动时会自动检查端点与 JSON 文档是否一致（见 _check_openapi_sync）。
import base64 as _b64
import hashlib as _hashlib
import struct as _struct
import io as _io
import http.server
import webbrowser
from urllib.parse import urlparse, parse_qs

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

_api_frames = {}             # 多屏投屏帧：{设备名: (SHOW_HEIGHT, SHOW_WIDTH, 3) uint8}
_api_frame_lock = threading.Lock()
_api_server = None           # HTTPServer 实例
_api_ws_connections = set()  # 活跃 WebSocket 连接
_api_slideshow_stops = {}    # 多图轮播：每屏停止信号 {设备名: Event}
_api_slideshow_threads = {}  # 多图轮播：每屏线程 {设备名: Thread}


def _api_device_key(device=None):
    """把 device(ScreenDevice/设备名/index/None) 解析为帧存储键（设备名）"""
    if device is None:
        dev = get_current_device()
        if dev is not None:
            return getattr(dev, "device_name", None) or "屏幕1"
        return "屏幕1"
    if isinstance(device, str):
        return device
    if hasattr(device, "device_name") and getattr(device, "device_name", None):
        return device.device_name
    try:
        return "屏幕%d" % (int(device) + 1)
    except Exception:
        return "屏幕1"


def api_set_frame(frame, device=None):
    """写入外部投屏帧到指定屏（device 缺省=当前活跃屏）"""
    global _api_event_version
    with _api_frame_lock:
        key = _api_device_key(device)
        if frame is None:
            _api_frames.pop(key, None)
        else:
            _api_frames[key] = frame
        # SSE 帧版本号递增，通知 /api/events 订阅端有新帧
        with _api_event_lock:
            _api_event_version += 1


def api_get_frame(device=None):
    """读取指定屏的外部投屏帧（device 缺省=当前活跃屏）"""
    with _api_frame_lock:
        return _api_frames.get(_api_device_key(device))


def api_start_slideshow(frames, interval, device=None):
    """启动多图轮播投屏到指定屏（frames 为已缩放 RGB888 数组列表，interval 间隔秒）"""
    key = _api_device_key(device)
    api_stop_slideshow(device)
    stop = threading.Event()
    _api_slideshow_stops[key] = stop

    def _worker():
        n = len(frames)
        idx = 0
        while not stop.is_set():
            try:
                api_set_frame(frames[idx % n], key)
            except Exception:
                break
            idx += 1
            stop.wait(interval)

    _api_slideshow_threads[key] = threading.Thread(target=_worker, daemon=True)
    _api_slideshow_threads[key].start()


def api_stop_slideshow(device=None):
    """停止指定屏的多图轮播投屏"""
    key = _api_device_key(device)
    stop = _api_slideshow_stops.pop(key, None)
    if stop:
        stop.set()
    t = _api_slideshow_threads.pop(key, None)
    if t is not None:
        try:
            t.join(timeout=2)
        except Exception:
            pass


def _api_resolve_device(data):
    """从请求参数解析目标屏设备；返回 ScreenDevice 或 None（缺省=当前活跃屏）"""
    if not isinstance(data, dict):
        return None
    name = data.get("device", "") or ""
    if not name:
        return None
    for dev in all_devices.values():
        if getattr(dev, "device_name", "") == str(name) or str(getattr(dev, "index", -1)) == str(name):
            return dev
    return None


def _api_prepare_frame(data, width, height):
    """把外部 RGB 像素数据整形/缩放到屏幕尺寸的 RGB888 数组"""
    try:
        arr = np.asarray(data, dtype=np.uint8).reshape((int(height), int(width), 3))
    except Exception:
        return None
    img = Image.fromarray(arr).convert("RGB")
    img = img.resize((SHOW_WIDTH, SHOW_HEIGHT), Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)


def _api_resize_image(img, fit=None):
    """按显示方式把图像缩放到屏幕尺寸：
    stretch=拉伸填满(不保持比例)；contain=自适应完整显示(四周留黑边)；cover=填充裁剪(保持比例裁满)。"""
    tw, th = SHOW_WIDTH, SHOW_HEIGHT
    try:
        if fit == "stretch" or fit is None:
            return img.resize((tw, th), Image.LANCZOS)
        if fit == "cover":
            ratio = max(tw / img.width, th / img.height)
        else:  # contain
            ratio = min(tw / img.width, th / img.height)
        nw = max(1, round(img.width * ratio))
        nh = max(1, round(img.height * ratio))
        img2 = img.resize((nw, nh), Image.LANCZOS)
        if (nw, nh) == (tw, th):
            return img2
        if fit == "cover":
            x = (nw - tw) // 2
            y = (nh - th) // 2
            return img2.crop((x, y, x + tw, y + th))
        # contain：居中放到黑底画布
        canvas = Image.new("RGB", (tw, th), (0, 0, 0))
        canvas.paste(img2, ((tw - nw) // 2, (th - nh) // 2))
        return canvas
    except Exception:
        return img.resize((tw, th), Image.LANCZOS)


def _api_apply_text(data, device=None):
    """按 JSON 参数把文本渲染到投屏帧（支持字体/颜色/位置/对齐/背景色/目标屏）"""
    try:
        text = str(data.get("text", "") or "")
        if not text:
            api_set_frame(None, device)
            return
        font_size = max(8, min(72, int(data.get("font_size", 16))))
        color = data.get("color", "#ffffff")
        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        align = str(data.get("align", "left"))
        back = data.get("background", "#000000")
        img = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back)
        draw = ImageDraw.Draw(img)
        try:
            font = MiniMark.load_font("./simhei.ttf", font_size)
        except Exception:
            font = default_font
        try:
            c = (color or "#ffffff").lstrip('#')
            rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
        except Exception:
            rgb = (255, 255, 255)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if align == "center":
            x = (SHOW_WIDTH - tw) // 2
        elif align == "right":
            x = SHOW_WIDTH - tw - x
        y = max(0, min(SHOW_HEIGHT - th, y))
        draw.text((x, y), text, fill=rgb, font=font)
        api_set_frame(np.asarray(img, dtype=np.uint8), device)
    except Exception as e:
        print("API 文本渲染失败：%s" % e)


# ---------- 统一命令执行器（HTTP / WebSocket / TCP / UDP 复用） ----------
def api_apply_screen(data, device=None):
    """应用整帧图像投屏（image/rgb888/pixels 三种方式），成功返回 True"""
    width = int(data.get("width", 0) or 0)
    height = int(data.get("height", 0) or 0)
    if "image" in data:
        raw = _b64.b64decode(data["image"])
        img = Image.open(_io.BytesIO(raw)).convert("RGB")
        img = _api_resize_image(img, data.get("fit", "stretch"))
        api_set_frame(np.asarray(img, dtype=np.uint8), device)
    elif "rgb888" in data:
        raw = _b64.b64decode(data["rgb888"])
        need = SHOW_WIDTH * SHOW_HEIGHT * 3
        arr = np.frombuffer(raw[:need], dtype=np.uint8).reshape(SHOW_HEIGHT, SHOW_WIDTH, 3).copy()
        api_set_frame(arr, device)
    elif "pixels" in data and width and height:
        arr = _api_prepare_frame(data["pixels"], width, height)
        if arr is not None:
            api_set_frame(arr, device)
    else:
        return False
    return True


def api_apply_slideshow(data, device=None):
    """应用多图轮播投屏，返回响应 dict"""
    raws = data.get("images") or []
    if not isinstance(raws, list) or not raws:
        return {"ok": False, "error": "需要 images 数组（base64 图像）"}
    try:
        interval = max(0.5, float(data.get("interval", 3)))
    except Exception:
        interval = 3.0
    fit = data.get("fit", "stretch")
    frames = []
    for raw in raws:
        img = Image.open(_io.BytesIO(_b64.b64decode(raw))).convert("RGB")
        img = _api_resize_image(img, fit)
        frames.append(np.asarray(img, dtype=np.uint8))
    api_start_slideshow(frames, interval, device)
    return {"ok": True, "count": len(frames), "interval": interval}


def api_apply_stop(device=None):
    """停止指定屏投屏：停止轮播 + 清屏。强制投屏模式下保留原页面（清帧后自动恢复，如 热搜）；
    普通模式切回 API 投屏页。返回响应 dict"""
    api_stop_slideshow(device)
    api_set_frame(None, device)
    try:
        dev = device if device is not None else get_current_device()
        if dev is not None:
            set_active_device_config(dev)
            if getattr(config_obj, "api_overlay", 0):
                # 强制投屏模式：不切页，清帧后渲染循环自动回到投屏前的页面
                state_change_set(save=False)
                return {"ok": True, "page": PAGE_ID.get(config_obj.state_machine, ""), "overlay": True}
            config_obj.state_machine = API_PAGE_ID
            if dev:
                dev.state_machine = API_PAGE_ID
            state_change_set(save=False)
    except Exception:
        pass
    return {"ok": True, "page": PAGE_ID.get(API_PAGE_ID, "API投屏")}


def api_apply_page(data, device=None):
    """切换指定屏页面，返回响应 dict"""
    try:
        dev = device if device is not None else get_current_device()
        if dev is None:
            return {"ok": False, "error": "no device"}
        set_active_device_config(dev)
        name = str(data.get("page", ""))
        pid = None
        for k, v in PAGE_ID.items():
            if v == name:
                pid = k
                break
        if pid is None:
            try:
                pid = int(data.get("page", -1))
            except Exception:
                pid = -1
        if pid in PAGE_ID:
            config_obj.state_machine = pid
            if dev:
                dev.state_machine = pid
            state_change_set(save=True)
            return {"ok": True, "page": PAGE_ID.get(pid, str(pid))}
        return {"ok": False, "error": "无效页面，可用 /api/pages 查看"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_apply_mirror(data, device=None):
    """把窗口投到指定屏，返回响应 dict"""
    try:
        dev = device if device is not None else get_current_device()
        if dev is None:
            return {"ok": False, "error": "no device"}
        hwnd = int(data.get("hwnd", 0) or 0)
        if hwnd == 0:
            return {"ok": False, "error": "需要 hwnd"}
        set_active_device_config(dev)
        config_obj.select_window_hwnd = hwnd
        config_obj.state_machine = SCREEN_PAGE_ID
        if dev:
            dev.state_machine = SCREEN_PAGE_ID
            dev.screen_frame_generation += 1
            clear_queue(dev.screen_shot_queue)
            clear_queue(dev.screen_process_queue)
        state_change_set(save=True)
        return {"ok": True, "hwnd": hwnd, "page": PAGE_ID.get(SCREEN_PAGE_ID, "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------- 扩展功能命令（信息/控制/配置，HTTP 与统一命令共用） ----------
# 允许通过 /api/config/set 修改的字段白名单（安全显示/行为类，排除令牌/端口/自启等敏感项）
_API_CONFIG_WRITABLE = {
    "state_machine": "int", "lcd_change": "int",
    "page_cycle_enable": "int", "page_cycle_interval": "int", "screen_off_timeout": "int",
    "anti_burn": "int", "preview_enabled": "int", "zoom_enable": "int", "zoom_scale": "int",
    "marquee_text": "str", "marquee_font": "str", "marquee_font_size": "int",
    "marquee_color": "str", "marquee_speed": "int",
    "ping_host": "str", "timer_minutes": "int", "weather_city": "str", "crypto_symbols": "str",
    "proc_count": "int", "clock_zones": "str", "hwdetail_max": "int",
    "hotsearch_interval": "int", "hotsearch_total": "int", "hotsearch_count": "int",
    "text_color_r": "int", "text_color_g": "int", "text_color_b": "int",
    "netspeed_mode": "str", "netspeed_up_color": "str", "netspeed_down_color": "str",
    "netspeed_bar1_color": "str", "netspeed_bar2_color": "str",
    "diskio_mode": "str", "diskio_show_title": "int", "diskio_font_auto": "int",
    "diskio_font_size": "int", "diskio_title_color": "str", "diskio_read_color": "str",
    "diskio_write_color": "str", "diskio_label_color": "str", "diskio_value_auto": "int",
    "diskio_value_font_size": "int", "diskio_bar1_color": "str", "diskio_bar2_color": "str",
    "diskio_value_read_color": "str", "diskio_value_write_color": "str",
}


def api_get_health():
    """健康检查：轻量探测服务是否可用"""
    return {"ok": True, "time": time.time()}


def api_get_version():
    """版本信息"""
    return {"ok": True, "name": PROGRAM_TITLE, "version": PROGRAM_VERSION,
            "build_date": PROGRAM_BUILD_DATE, "author": PROGRAM_AUTHOR,
            "license": PROGRAM_LICENSE, "github": PROGRAM_GITHUB}


def api_get_protocols():
    """列出全部接入协议与地址（供外部程序自动发现可用接入方式）"""
    port = 8632
    try:
        port = int(getattr(config_obj, "api_port", 8632))
    except Exception:
        pass
    base_dir = ""
    try:
        base_dir = get_base_config_dir()
    except Exception:
        pass
    import socket as _sock
    has_unix = hasattr(_sock, "AF_UNIX")
    has_zmq = False
    try:
        import zmq  # noqa: F401
        has_zmq = True
    except Exception:
        pass
    protocols = [
        {"name": "HTTP REST", "type": "http", "address": "http://127.0.0.1:%d" % port,
         "enabled": True, "note": "GET 查询 / POST JSON 命令（主接口）"},
        {"name": "WebSocket", "type": "ws", "address": "ws://127.0.0.1:%d/ws" % port,
         "enabled": True, "note": "文本帧=JSON命令，二进制帧=RGB888原始帧"},
        {"name": "SSE 事件流", "type": "sse", "address": "http://127.0.0.1:%d/api/events" % port,
         "enabled": True, "note": "帧版本变化推送 event: frame"},
        {"name": "TCP Socket", "type": "tcp", "address": "127.0.0.1:%d" % (port + 1),
         "enabled": True, "note": "JSON 行协议"},
        {"name": "UDP", "type": "udp", "address": "127.0.0.1:%d" % (port + 2),
         "enabled": True, "note": "JSON 数据报"},
        {"name": "ZeroMQ", "type": "zmq", "address": "tcp://127.0.0.1:%d" % (port + 3),
         "enabled": has_zmq, "note": "REP/REQ JSON（需 pip install pyzmq）"},
        {"name": "Windows 命名管道", "type": "pipe", "address": r"\\.\pipe\MSU2_MINI_V2_api",
         "enabled": isWindows, "note": "JSON 行协议"},
        {"name": "Unix Domain Socket", "type": "unix",
         "address": os.path.join(base_dir, "api_unix.sock") if base_dir else "api_unix.sock",
         "enabled": has_unix, "note": "JSON 行协议（需系统支持 AF_UNIX）"},
        {"name": "热文件夹", "type": "hotfolder",
         "address": os.path.join(base_dir, "hotfolder") if base_dir else "hotfolder",
         "enabled": True, "note": "放入图片/文本即投屏"},
        {"name": "stdin 管道", "type": "stdin", "address": "标准输入",
         "enabled": True, "note": "管道/重定向启动时按行读 JSON 命令"},
    ]
    return {"ok": True, "port": port, "protocols": protocols}


def api_get_status():
    """综合运行状态（当前屏、各屏连接、页面、方向、投屏帧、轮播）"""
    try:
        dev = get_current_device()
        cfg = getattr(dev, "config", None) if dev is not None else None
        if cfg is None:
            cfg = config_obj
        devices = []
        for d in all_devices.values():
            c = getattr(d, "config", None)
            devices.append({
                "name": getattr(d, "device_name", "屏幕1"),
                "index": getattr(d, "index", 0),
                "connected": bool(getattr(d, "device_state", 0)),
                "page": PAGE_ID.get(getattr(c, "state_machine", 0), "") if c is not None else "",
                "direction": getattr(c, "lcd_change", 0) if c is not None else 0,
            })
        devices.sort(key=lambda x: x["index"])
        frames = {}
        with _api_frame_lock:
            for k in _api_frames:
                frames[k] = True
        return {"ok": True,
                "device": getattr(dev, "device_name", "屏幕1") if dev is not None else None,
                "connected": bool(getattr(dev, "device_state", 0)) if dev is not None else False,
                "page": PAGE_ID.get(getattr(cfg, "state_machine", 0), "") if cfg else "",
                "direction": getattr(cfg, "lcd_change", 0) if cfg else 0,
                "version": PROGRAM_VERSION,
                "devices": devices,
                "casting": frames,
                "slideshows": sorted(_api_slideshow_stops.keys())}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_get_config(device=None):
    """读取指定屏的完整配置（只读，JSON 序列化安全字段）"""
    dev = device if device is not None else get_current_device()
    if dev is None:
        return {"ok": False, "error": "no device"}
    cfg = getattr(dev, "config", None) if dev is not None else None
    if cfg is None:
        cfg = config_obj
    try:
        d = {}
        for k, v in vars(cfg).items():
            try:
                json.dumps(v)
                d[k] = v
            except Exception:
                pass
        return {"ok": True, "device": getattr(dev, "device_name", "屏幕1"), "config": d}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_get_screenshot(device=None):
    """获取指定屏当前画面：优先投屏帧，其次最近预览帧；返回 PNG 与 RGB888 的 base64"""
    dev = device if device is not None else get_current_device()
    if dev is None:
        return {"ok": False, "error": "no device"}
    frame = api_get_frame(dev)
    if frame is None:
        prev = getattr(dev, "last_preview_rgb", None)
        if prev is None:
            return {"ok": False, "error": "当前无可用画面（无投屏帧也无预览帧）"}
        frame = prev
    try:
        arr = np.asarray(frame, dtype=np.uint8)
        if arr.ndim == 3 and arr.shape[2] == 3:
            h, w = arr.shape[0], arr.shape[1]
        else:
            return {"ok": False, "error": "帧数据格式异常"}
        img = Image.fromarray(arr)
        buf = _io.BytesIO()
        img.save(buf, "PNG")
        return {"ok": True, "device": getattr(dev, "device_name", "屏幕1"),
                "width": w, "height": h,
                "png": _b64.b64encode(buf.getvalue()).decode("ascii"),
                "rgb888": _b64.b64encode(arr.tobytes()).decode("ascii")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_apply_orientation(data, device=None):
    """设置指定屏 LCD 方向：direction 为 0~N 或 next（循环切换）"""
    dev = device if device is not None else get_current_device()
    if dev is None:
        return {"ok": False, "error": "no device"}
    if getattr(dev, "device_state", 0) == 0:
        return {"ok": False, "error": "设备未连接"}
    prev = _device_context.device
    _device_context.device = dev
    try:
        set_active_device_config(dev)
        direction = data.get("direction")
        if str(direction).lower() in ("next", "rotate", "switch"):
            LCD_Change()
        else:
            try:
                idx = int(direction)
            except Exception:
                return {"ok": False, "error": "direction 需为 0~%d 或 next" % (len(LCD_STATE_MESSAGE) - 1)}
            set_lcd_direction(idx % len(LCD_STATE_MESSAGE))
        return {"ok": True, "direction": config_obj.lcd_change,
                "direction_name": LCD_STATE_MESSAGE[config_obj.lcd_change]}
    finally:
        _device_context.device = prev


def api_apply_key(data):
    """模拟按键动作：下翻页 / 上翻页 / 切换方向 / 无"""
    action = str(data.get("action", ""))
    if action in ("下翻页", "上翻页", "切换方向", "无"):
        do_key_action(action)
        return {"ok": True, "action": action}
    return {"ok": False, "error": "action 需为 下翻页/上翻页/切换方向/无"}


def api_page_next(device=None):
    """翻到下一页（当前活跃屏）"""
    dev = device if device is not None else get_current_device()
    if dev is None:
        return {"ok": False, "error": "no device"}
    prev = _device_context.device
    _device_context.device = dev
    try:
        Page_UP()
        return {"ok": True, "page": PAGE_ID.get(config_obj.state_machine, "")}
    finally:
        _device_context.device = prev


def api_page_prev(device=None):
    """翻到上一页（当前活跃屏）"""
    dev = device if device is not None else get_current_device()
    if dev is None:
        return {"ok": False, "error": "no device"}
    prev = _device_context.device
    _device_context.device = dev
    try:
        Page_Down()
        return {"ok": True, "page": PAGE_ID.get(config_obj.state_machine, "")}
    finally:
        _device_context.device = prev


def api_apply_config_set(data, device=None):
    """按白名单修改指定屏配置（字段见 _API_CONFIG_WRITABLE），立即保存生效"""
    dev = device if device is not None else get_current_device()
    if dev is None:
        return {"ok": False, "error": "no device"}
    set_active_device_config(dev)
    changed = []
    for key, val in data.items():
        if key in ("type", "cmd", "device", "action"):
            continue
        if key not in _API_CONFIG_WRITABLE:
            continue
        typ = _API_CONFIG_WRITABLE[key]
        try:
            if typ == "int":
                val = int(val)
            else:
                val = str(val)
        except Exception:
            return {"ok": False, "error": "字段 %s 的值类型错误" % key}
        if key == "state_machine":
            pid = val
            for k, v in PAGE_ID.items():
                if v == val:
                    pid = k
                    break
            if pid not in PAGE_ID:
                return {"ok": False, "error": "无效页面: %s（可用 /api/pages 查看）" % val}
            val = pid
        setattr(config_obj, key, val)
        changed.append(key)
    if changed:
        if dev:
            dev.state_machine = config_obj.state_machine
        state_change_set(save=True)
    return {"ok": True, "changed": changed}


def api_apply_marquee(data, device=None):
    """设置跑马灯文本并切到跑马灯页（text/speed/font_size/color 可选）"""
    dev = device if device is not None else get_current_device()
    if dev is None:
        return {"ok": False, "error": "no device"}
    set_active_device_config(dev)
    if "text" in data:
        config_obj.marquee_text = str(data.get("text", ""))
    if "speed" in data:
        try:
            config_obj.marquee_speed = int(data.get("speed"))
        except Exception:
            pass
    if "font_size" in data:
        try:
            config_obj.marquee_font_size = int(data.get("font_size"))
        except Exception:
            pass
    if "color" in data:
        config_obj.marquee_color = str(data.get("color"))
    config_obj.state_machine = MARQUEE_PAGE_ID
    if dev:
        dev.state_machine = MARQUEE_PAGE_ID
    state_change_set(save=True)
    return {"ok": True, "page": PAGE_ID.get(MARQUEE_PAGE_ID, "文字跑马灯")}


def api_apply_device_select(data):
    """切换当前活跃屏（多屏时改变主控/API 作用的设备）"""
    global _primary_device
    name = str(data.get("device", "") or "")
    for dev in all_devices.values():
        if dev.device_name == name:
            old = _primary_device
            if old is not None and old != dev:
                # 旧设备页面同步到其自身配置（不读全局 config_obj，避免串扰）
                if old.config is not None:
                    old.config.state_machine = old.state_machine
                else:
                    old.state_machine = config_obj.state_machine
            set_current_device(dev)
            _primary_device = dev
            set_active_device_config(dev)
            # 新设备页面同步到其自身配置（不经过全局 config_obj）
            if dev.config is not None:
                dev.config.state_machine = getattr(dev, "state_machine", SCREEN_PAGE_ID)
            state_change_set(save=False)
            return {"ok": True, "device": name}
    return {"ok": False, "error": "未找到设备: %s（可用 /api/devices 查看）" % name}


def api_apply_device_refresh():
    """刷新设备信息（返回当前设备连接快照）"""
    try:
        connected = [d for d in all_devices.values() if d.device_state == 1]
        return {"ok": True, "device_count": len(all_devices),
                "connected_count": len(connected),
                "devices": [d.device_name for d in all_devices.values()]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def api_apply_notify(data):
    """在 UI 底部状态栏显示一条通知文本（不投屏）"""
    text = str(data.get("text", "") or "")
    if not text:
        return {"ok": False, "error": "需要 text"}
    insert_text_message(text)
    return {"ok": True}


def api_apply_quit(data):
    """退出程序（需 force: true，延迟执行以便响应返回）"""
    if not data.get("force"):
        return {"ok": False, "error": "需要 force: true 才执行退出"}
    try:
        root = _ui_root
        if root is not None:
            def _do():
                try:
                    stop_api_server()
                except Exception:
                    pass
                try:
                    root.close()
                except Exception:
                    pass
            QTimer.singleShot(300, _do)
            return {"ok": True}
    except Exception:
        pass
    return {"ok": False, "error": "无法获取主窗口"}


def api_execute_command(data):
    """统一执行投屏命令 dict（供 TCP/UDP/WS 复用，与 HTTP JSON 一致）。返回响应 dict。"""
    if not isinstance(data, dict):
        return {"ok": False, "error": "需要 JSON 对象"}
    cmd = data.get("type")
    dev = _api_resolve_device(data)
    try:
        if cmd == "screen":
            if api_apply_screen(data, dev):
                return {"ok": True, "size": [SHOW_WIDTH, SHOW_HEIGHT]}
            return {"ok": False, "error": "需要 image / rgb888 / pixels 之一"}
        elif cmd == "text":
            _api_apply_text(data, dev)
            return {"ok": True}
        elif cmd == "clear":
            api_stop_slideshow(dev)
            api_set_frame(None, dev)
            return {"ok": True}
        elif cmd == "slideshow":
            return api_apply_slideshow(data, dev)
        elif cmd == "slideshow_stop":
            api_stop_slideshow(dev)
            return {"ok": True}
        elif cmd == "stop":
            return api_apply_stop(dev)
        elif cmd == "page":
            return api_apply_page(data, dev)
        elif cmd == "page_next":
            return api_page_next(dev)
        elif cmd == "page_prev":
            return api_page_prev(dev)
        elif cmd == "mirror":
            return api_apply_mirror(data, dev)
        elif cmd == "orientation":
            return api_apply_orientation(data, dev)
        elif cmd == "key":
            return api_apply_key(data)
        elif cmd == "marquee":
            return api_apply_marquee(data, dev)
        elif cmd == "config_set":
            return api_apply_config_set(data, dev)
        elif cmd == "device_select":
            return api_apply_device_select(data)
        elif cmd == "device_refresh":
            return api_apply_device_refresh()
        elif cmd == "notify":
            return api_apply_notify(data)
        elif cmd == "quit":
            return api_apply_quit(data)
        elif cmd == "health":
            return api_get_health()
        elif cmd == "version":
            return api_get_version()
        elif cmd == "protocols":
            return api_get_protocols()
        elif cmd == "status":
            return api_get_status()
        elif cmd == "config_get":
            return api_get_config(dev)
        elif cmd == "screenshot":
            return api_get_screenshot(dev)
        elif cmd == "screen_id":
            return api_trigger_screen_id(data)
        else:
            return {"ok": False, "error": "未知命令: %s" % cmd}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class ApiHandler(http.server.BaseHTTPRequestHandler):
    server_version = "MSU2MiniAPI/1.0"

    def log_message(self, fmt, *args):
        pass  # 关闭默认请求日志

    # ---------- 工具 ----------
    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except Exception:
            length = 0
        return self.rfile.read(length) if length > 0 else b""

    def _check_token(self):
        """配置了令牌时校验 X-API-Token 或 ?token=，通过返回 True"""
        try:
            token = getattr(config_obj, "api_token", "") or ""
            if not token:
                return True
            got = self.headers.get("X-API-Token", "")
            if not got:
                got = parse_qs(urlparse(self.path).query).get("token", [""])[0]
            return got == token
        except Exception:
            return False

    def _send_info(self):
        try:
            dev = get_current_device()
            info = {
                "ok": True,
                "name": "MSU2_MINI_V2",
                "version": PROGRAM_VERSION,
                "screen": {"width": SHOW_WIDTH, "height": SHOW_HEIGHT, "lcd": [LCD_MAX_X, LCD_MAX_Y]},
                "connected": dev is not None and dev.device_state == 1,
                "page": PAGE_ID.get(config_obj.state_machine, ""),
                "pages": list(PAGE_ID.values()),
            }
        except Exception as e:
            info = {"ok": False, "error": str(e)}
        self._send_json(info)

    # ---------- 帧处理 ----------
    def _apply_screen(self, data, device=None):
        """整帧投屏（复用统一逻辑）"""
        return api_apply_screen(data, device)

    # ---------- GET ----------
    def do_GET(self):
        if not self._check_token():
            self._send_json({"ok": False, "error": "invalid token"}, 401)
            return
        path = self.path.split("?", 1)[0]
        if path == "/ws":
            self._ws_handshake()
        elif path in ("/", "/api"):
            self._send_api_doc()
        elif path == "/docs":
            self._send_plain_doc()
        elif path in ("/api/openapi.json", "/api.json", "/api/openapi"):
            # 机器可读的 OpenAPI 3.0 JSON 规范，供其他程序解析对接
            self._send_json(_build_openapi_doc())
        elif path == "/api/info":
            self._send_info()
        elif path == "/api/pages":
            self._send_json({"ok": True, "pages": list(PAGE_ID.values())})
        elif path == "/api/windows":
            self._send_windows()
        elif path == "/api/devices":
            self._send_devices()
        elif path == "/api/events":
            self._sse_events()
        elif path == "/api/health":
            self._send_json(api_get_health())
        elif path == "/api/version":
            self._send_json(api_get_version())
        elif path == "/api/protocols":
            self._send_json(api_get_protocols())
        elif path == "/api/status":
            self._send_json(api_get_status())
        elif path == "/api/config":
            qs = parse_qs(urlparse(self.path).query)
            gdev = _api_resolve_device({"device": (qs.get("device") or [""])[0]})
            self._send_json(api_get_config(gdev))
        elif path == "/api/screenshot":
            qs = parse_qs(urlparse(self.path).query)
            gdev = _api_resolve_device({"device": (qs.get("device") or [""])[0]})
            self._send_json(api_get_screenshot(gdev))
        else:
            self._send_json({"ok": False, "error": "not found"}, 404)

    # ---------- POST ----------
    def do_POST(self):
        if not self._check_token():
            self._send_json({"ok": False, "error": "invalid token"}, 401)
            return
        path = self.path.split("?", 1)[0]
        if path == "/api/screen/raw":
            # 原始 RGB888 字节流（application/octet-stream），顺序为 W*H*3；目标屏用 ?device=屏幕1
            raw = self._read_body()
            need = SHOW_WIDTH * SHOW_HEIGHT * 3
            qs = parse_qs(urlparse(self.path).query)
            dev = _api_resolve_device({"device": (qs.get("device") or [""])[0]})
            if len(raw) >= need:
                arr = np.frombuffer(raw[:need], dtype=np.uint8).reshape(SHOW_HEIGHT, SHOW_WIDTH, 3).copy()
                api_set_frame(arr, dev)
                self._send_json({"ok": True})
            else:
                self._send_json({"ok": False, "error": "数据长度不足 W*H*3"}, 400)
            return
        try:
            data = json.loads(self._read_body().decode("utf-8"))
        except Exception:
            data = {}
        dev = _api_resolve_device(data)
        if path == "/api/screen":
            try:
                ok = self._apply_screen(data, dev)
            except Exception as e:
                ok = False
                self._send_json({"ok": False, "error": "图像数据解析失败：%s" % e}, 400)
                return
            if ok:
                self._send_json({"ok": True, "size": [SHOW_WIDTH, SHOW_HEIGHT]})
            else:
                self._send_json({"ok": False, "error": "需要 image / rgb888 / pixels 之一"}, 400)
        elif path == "/api/text":
            _api_apply_text(data, dev)
            self._send_json({"ok": True})
        elif path == "/api/clear":
            api_stop_slideshow(dev)
            api_set_frame(None, dev)
            self._send_json({"ok": True})
        elif path == "/api/slideshow":
            self._post_slideshow(data, dev)
        elif path == "/api/slideshow/stop":
            api_stop_slideshow(dev)
            self._send_json({"ok": True})
        elif path == "/api/stop":
            self._post_stop(dev)
        elif path == "/api/page":
            self._post_page(data, dev)
        elif path == "/api/mirror":
            self._post_mirror(data, dev)
        elif path == "/api/orientation":
            self._send_json(api_apply_orientation(data, dev))
        elif path == "/api/key":
            self._send_json(api_apply_key(data))
        elif path == "/api/page/next":
            self._send_json(api_page_next(dev))
        elif path == "/api/page/prev":
            self._send_json(api_page_prev(dev))
        elif path == "/api/config/set":
            self._send_json(api_apply_config_set(data, dev))
        elif path == "/api/device/select":
            self._send_json(api_apply_device_select(data))
        elif path == "/api/device/refresh":
            self._send_json(api_apply_device_refresh())
        elif path == "/api/marquee":
            self._send_json(api_apply_marquee(data, dev))
        elif path == "/api/notify":
            self._send_json(api_apply_notify(data))
        elif path == "/api/screen/id":
            self._send_json(api_trigger_screen_id(data))
        elif path == "/api/quit":
            self._send_json(api_apply_quit(data))
        else:
            self._send_json({"ok": False, "error": "not found"}, 404)

    def _post_page(self, data, device=None):
        """切页（复用统一逻辑）"""
        self._send_json(api_apply_page(data, device))

    # ---------- API 文档 ----------
    def _send_api_doc(self):
        """返回网页投屏控制台（带分页标签：投屏 / 选择程序 / 文档）"""
        body = _API_CONSOLE_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_plain_doc(self):
        """返回原始 API 说明文档（/docs）"""
        try:
            port = int(getattr(config_obj, "api_port", 8632))
        except Exception:
            port = 8632
        try:
            html = _API_DOC_HTML.format(port=port, size="%dx%d" % (SHOW_WIDTH, SHOW_HEIGHT),
                                        bytes_len=SHOW_WIDTH * SHOW_HEIGHT * 3,
                                        port_plus_1=port + 1, port_plus_2=port + 2, port_plus_3=port + 3)
        except Exception:
            html = "<pre>MSU2_MINI_V2 API: http://127.0.0.1:%d</pre>" % port
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse_events(self):
        """SSE 事件流：/api/events，帧版本变化时推送 event: frame（长连接）"""
        self.close_connection = False
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        last = -1
        try:
            while True:
                with _api_event_lock:
                    ver = _api_event_version
                if ver != last:
                    last = ver
                    self.wfile.write(("event: frame\ndata: %d\n\n" % ver).encode("utf-8"))
                else:
                    self.wfile.write(b": ping\n\n")  # 心跳保持连接
                self.wfile.flush()
                time.sleep(1)
        except Exception:
            pass
        finally:
            self.close_connection = True

    def _send_windows(self):
        """返回本机可投屏的窗口列表"""
        try:
            wins = get_all_windows()
            items = [{"hwnd": h, "name": n} for n, (h, _parent) in wins.items()]
            items.sort(key=lambda x: x["name"].lower())
            self._send_json({"ok": True, "windows": items})
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, 500)

    def _send_devices(self):
        """返回多屏设备列表（供选择投屏目标屏）"""
        try:
            items = []
            for dev in all_devices.values():
                cfg = getattr(dev, "config", None)
                items.append({
                    "name": getattr(dev, "device_name", "屏幕1"),
                    "index": getattr(dev, "index", 0),
                    "connected": bool(getattr(dev, "device_state", 0)),
                    "page": PAGE_ID.get(getattr(cfg, "state_machine", 0), "") if cfg is not None else "",
                })
            items.sort(key=lambda x: x["index"])
            self._send_json({"ok": True, "devices": items})
        except Exception as e:
            self._send_json({"ok": False, "error": str(e)}, 500)

    def _post_mirror(self, data, device=None):
        """窗口投屏（复用统一逻辑）"""
        self._send_json(api_apply_mirror(data, device))

    def _post_slideshow(self, data, device=None):
        """多图轮播投屏（复用统一逻辑）"""
        self._send_json(api_apply_slideshow(data, device))

    def _post_stop(self, device=None):
        """停止指定屏投屏（复用统一逻辑）"""
        self._send_json(api_apply_stop(device))

    # ---------- WebSocket ----------
    def _ws_handshake(self):
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self._send_json({"ok": False, "error": "websocket handshake failed"}, 400)
            return
        accept = _b64.b64encode(_hashlib.sha1((key + _WS_GUID).encode("ascii")).digest()).decode("ascii")
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
        self._ws_loop()

    def _ws_recv_frame(self):
        """读取一个 WS 帧，返回 (opcode, payload)；连接关闭返回 None"""
        try:
            head = self.rfile.read(2)
            if len(head) < 2:
                return None
            b0, b1 = head
            opcode = b0 & 0x0F
            length = b1 & 0x7F
            masked = b1 & 0x80
            if length == 126:
                length = _struct.unpack(">H", self.rfile.read(2))[0]
            elif length == 127:
                length = _struct.unpack(">Q", self.rfile.read(8))[0]
            mask = self.rfile.read(4) if masked else b""
            payload = self.rfile.read(length)
            if masked and len(mask) == 4:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            return opcode, payload
        except Exception:
            return None

    def _ws_loop(self):
        _api_ws_connections.add(self)
        try:
            while True:
                frame = self._ws_recv_frame()
                if frame is None:
                    break
                opcode, payload = frame
                if opcode == 0x8:  # close
                    break
                elif opcode == 0x1:  # text -> JSON 命令
                    try:
                        data = json.loads(payload.decode("utf-8", "replace"))
                    except Exception:
                        data = {}
                    cmd = data.get("type")
                    dev = _api_resolve_device(data)
                    if cmd == "screen":
                        self._apply_screen(data, dev)
                    elif cmd == "text":
                        _api_apply_text(data, dev)
                    elif cmd == "clear":
                        api_stop_slideshow(dev)
                        api_set_frame(None, dev)
                    elif cmd == "page":
                        self._post_page(data, dev)
                    elif cmd == "mirror":
                        self._post_mirror(data, dev)
                    elif cmd == "stop":
                        self._post_stop(dev)
                elif opcode == 0x2:  # binary -> 原始 RGB888 帧（W*H*3）
                    need = SHOW_WIDTH * SHOW_HEIGHT * 3
                    if len(payload) >= need:
                        arr = np.frombuffer(payload[:need], dtype=np.uint8).reshape(SHOW_HEIGHT, SHOW_WIDTH, 3).copy()
                        api_set_frame(arr)
        except Exception:
            pass
        finally:
            _api_ws_connections.discard(self)
            try:
                self.close_connection = True
                self.connection.close()
            except Exception:
                pass


def _build_openapi_doc():
    """生成 OpenAPI 3.0 规范的 API JSON 文档（机器可读，供其他程序解析对接）"""
    try:
        port = int(getattr(config_obj, "api_port", 8632))
    except Exception:
        port = 8632
    try:
        has_token = bool(getattr(config_obj, "api_token", ""))
    except Exception:
        has_token = False
    token_note = ("已启用访问令牌：请求头 X-API-Token 或查询参数 ?token="
                  if has_token else "未启用访问令牌（可在设置 → API接入 中配置）")
    need = SHOW_WIDTH * SHOW_HEIGHT * 3
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "MSU2_MINI_V2 投屏 API",
            "description": "USB 副屏工具的外部接入接口。支持 HTTP REST / WebSocket / SSE(/api/events) / TCP(JSON行,端口+1) / UDP(JSON报,端口+2) / ZeroMQ(REP,端口+3,需pyzmq) / Windows命名管道(\\\\\\.\\\\pipe\\\\MSU2_MINI_V2_api) / Unix Domain Socket(api_unix.sock) / 热文件夹 投屏。可自定义投屏内容（图像、文本、清屏、切页、多图轮播、窗口投屏、实时帧）。支持「强制投屏」：未选 API投屏 页也可投屏，结束自动返回原页面。屏幕分辨率 %dx%d。%s"
                           % (SHOW_WIDTH, SHOW_HEIGHT, token_note),
            "version": PROGRAM_VERSION,
            "license": {"name": "MIT", "url": PROGRAM_GITHUB},
        },
        "servers": [{"url": "http://127.0.0.1:%d" % port, "description": "本地 API 服务"}],
        "tags": [
            {"name": "信息", "description": "查询服务与设备信息"},
            {"name": "投屏", "description": "投屏图像 / 文本 / 清屏"},
            {"name": "控制", "description": "页面切换"},
            {"name": "实时", "description": "WebSocket 实时通道"},
        ],
        "paths": {
            "/api/info": {
                "get": {
                    "tags": ["信息"],
                    "summary": "获取服务与设备信息",
                    "responses": {
                        "200": {
                            "description": "成功",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/InfoResponse"}}},
                        }
                    },
                }
            },
            "/api/pages": {
                "get": {
                    "tags": ["信息"],
                    "summary": "获取可用页面列表",
                    "responses": {
                        "200": {
                            "description": "页面名称数组",
                            "content": {"application/json": {"schema": {
                                "type": "object",
                                "properties": {
                                    "ok": {"type": "boolean"},
                                    "pages": {"type": "array", "items": {"type": "string"}},
                                },
                            }}},
                        }
                    },
                }
            },
            "/api/screen": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "投屏整帧图像（JSON，三种方式任选）",
                    "description": "image=base64 编码的 PNG/JPG/BMP；rgb888=base64 编码的原始 RGB888 字节(W*H*3)；pixels=扁平 RGB 列表(需同时给 width/height)",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ScreenRequest"}}},
                    },
                    "responses": {
                        "200": {"description": "成功，返回屏幕尺寸"},
                        "400": {"description": "参数错误或图像解析失败"},
                    },
                }
            },
            "/api/screen/raw": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "原始 RGB888 字节流投屏（最低开销）",
                    "description": "请求体为 %d 字节原始 RGB888（按屏幕 %dx%d），Content-Type: application/octet-stream" % (need, SHOW_WIDTH, SHOW_HEIGHT),
                    "requestBody": {
                        "required": True,
                        "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}},
                    },
                    "responses": {
                        "200": {"description": "成功"},
                        "400": {"description": "数据长度不足 W*H*3"},
                    },
                }
            },
            "/api/text": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "文本投屏",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/TextRequest"}}},
                    },
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/clear": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "清空投屏帧",
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/page": {
                "post": {
                    "tags": ["控制"],
                    "summary": "切换页面（按名称或 ID）",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PageRequest"}}},
                    },
                    "responses": {
                        "200": {"description": "成功，返回当前页面"},
                        "400": {"description": "无效页面或无设备"},
                    },
                }
            },
            "/api/windows": {
                "get": {
                    "tags": ["控制"],
                    "summary": "列出本机可投屏的窗口/程序",
                    "responses": {
                        "200": {
                            "description": "窗口列表",
                            "content": {"application/json": {"schema": {
                                "type": "object",
                                "properties": {
                                    "ok": {"type": "boolean"},
                                    "windows": {
                                        "type": "array",
                                        "items": {"type": "object", "properties": {
                                            "hwnd": {"type": "integer", "description": "窗口句柄"},
                                            "name": {"type": "string", "description": "窗口/程序名称"},
                                        }},
                                    },
                                },
                            }}},
                        }
                    },
                }
            },
            "/api/devices": {
                "get": {
                    "tags": ["信息"],
                    "summary": "列出多屏设备（用于选择投屏目标屏）",
                    "responses": {
                        "200": {
                            "description": "设备列表",
                            "content": {"application/json": {"schema": {
                                "type": "object",
                                "properties": {
                                    "ok": {"type": "boolean"},
                                    "devices": {
                                        "type": "array",
                                        "items": {"type": "object", "properties": {
                                            "name": {"type": "string", "description": "屏名（如 屏幕1）"},
                                            "index": {"type": "integer", "description": "屏序号"},
                                            "connected": {"type": "boolean"},
                                            "page": {"type": "string", "description": "当前页面"},
                                        }},
                                    },
                                },
                            }}},
                        }
                    },
                }
            },
            "/api/mirror": {
                "post": {
                    "tags": ["控制"],
                    "summary": "把指定窗口(hwnd)投屏到指定屏（切换到屏幕镜像页）",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {
                            "type": "object",
                            "required": ["hwnd"],
                            "properties": {"hwnd": {"type": "integer", "description": "窗口句柄（来自 /api/windows）"}},
                        }}},
                    },
                    "responses": {
                        "200": {"description": "成功，返回 hwnd 与页面名"},
                        "400": {"description": "无设备 / 缺少 hwnd / 无效"},
                    },
                }
            },
            "/api/slideshow": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "多图轮播投屏（一次上传多张图片，按间隔自动切换）",
                    "description": "images 为 base64 编码的图像数组，interval 为切换间隔（秒，最小 0.5）。自动缩放至屏幕尺寸。",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SlideshowRequest"}}},
                    },
                    "responses": {
                        "200": {"description": "成功，返回图片数与间隔"},
                        "400": {"description": "参数错误或图像解析失败"},
                    },
                }
            },
            "/api/slideshow/stop": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "停止多图轮播（不切页）",
                    "responses": {"200": {"description": "成功"}},
                }
            },
            "/api/stop": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "停止投屏：停止轮播 + 清屏 + 回到 API 投屏页",
                    "responses": {"200": {"description": "成功，返回当前页面"}},
                }
            },
            "/ws": {
                "get": {
                    "tags": ["实时"],
                    "summary": "WebSocket 实时通道（需 WebSocket 握手升级）",
                    "description": "二进制帧 = 原始 RGB888（%d 字节）；文本帧 = JSON 命令，type 为 screen / text / clear / page，参数与对应 POST 一致。适合高频推流。" % need,
                    "responses": {"101": {"description": "Switching Protocols（WebSocket 已建立）"}},
                }
            },
            "/api/events": {
                "get": {
                    "tags": ["实时"],
                    "summary": "SSE 事件流（Server-Sent Events）",
                    "description": "长连接事件流：帧版本变化时推送 event: frame（data=版本号）；空闲时发送心跳注释行。可用于网页端实时感知投屏内容变化。",
                    "responses": {"200": {"description": "text/event-stream 事件流"}},
                }
            },
            "/api/health": {
                "get": {
                    "tags": ["信息"],
                    "summary": "健康检查（探测服务可用性）",
                    "responses": {"200": {"description": "ok + 服务器时间"}},
                }
            },
            "/api/version": {
                "get": {
                    "tags": ["信息"],
                    "summary": "获取程序版本与元数据",
                    "responses": {"200": {"description": "版本、构建日期、作者、许可证、仓库地址"}},
                }
            },
            "/api/protocols": {
                "get": {
                    "tags": ["信息"],
                    "summary": "列出全部接入协议与地址（自动发现）",
                    "responses": {"200": {"description": "HTTP/WS/SSE/TCP/UDP/ZMQ/管道/Unix/热文件夹/stdin 及其可用状态"}},
                }
            },
            "/api/status": {
                "get": {
                    "tags": ["信息"],
                    "summary": "综合运行状态（当前屏/各屏连接/页面/方向/投屏中）",
                    "responses": {"200": {"description": "设备、页面、方向、投屏状态"}},
                }
            },
            "/api/config": {
                "get": {
                    "tags": ["信息"],
                    "summary": "读取指定屏完整配置（只读，支持 ?device=屏幕1）",
                    "parameters": [{"name": "device", "in": "query", "required": False, "schema": {"type": "string"}, "description": "目标屏名称，缺省=当前活跃屏"}],
                    "responses": {"200": {"description": "配置对象"}},
                }
            },
            "/api/screenshot": {
                "get": {
                    "tags": ["信息"],
                    "summary": "获取指定屏当前画面（PNG + RGB888 的 base64，支持 ?device=屏幕1）",
                    "parameters": [{"name": "device", "in": "query", "required": False, "schema": {"type": "string"}, "description": "目标屏名称，缺省=当前活跃屏"}],
                    "responses": {"200": {"description": "宽高 + png/rgb888 base64"}},
                }
            },
            "/api/orientation": {
                "post": {
                    "tags": ["控制"],
                    "summary": "设置 LCD 显示方向",
                    "description": "direction: 0~N 直接设置，或 next 循环切换（正向/反向/镜像/旋转等）。需设备已连接。",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {
                            "direction": {"type": "string", "description": "0~N 或 next"},
                            "device": {"type": "string", "description": "目标屏名称，缺省=当前活跃屏"},
                        }}}}},
                    "responses": {"200": {"description": "设置后的方向索引与名称"}},
                }
            },
            "/api/key": {
                "post": {
                    "tags": ["控制"],
                    "summary": "模拟按键动作（下翻页 / 上翻页 / 切换方向 / 无）",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {"action": {"type": "string", "description": "下翻页/上翻页/切换方向/无"}},
                    }}}},
                    "responses": {"200": {"description": "执行结果"}},
                }
            },
            "/api/page/next": {
                "post": {
                    "tags": ["控制"],
                    "summary": "翻到下一页",
                    "requestBody": {"required": False, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {"device": {"type": "string", "description": "目标屏名称，缺省=当前活跃屏"}},
                    }}}},
                    "responses": {"200": {"description": "当前页面"}},
                }
            },
            "/api/page/prev": {
                "post": {
                    "tags": ["控制"],
                    "summary": "翻到上一页",
                    "requestBody": {"required": False, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {"device": {"type": "string", "description": "目标屏名称，缺省=当前活跃屏"}},
                    }}}},
                    "responses": {"200": {"description": "当前页面"}},
                }
            },
            "/api/config/set": {
                "post": {
                    "tags": ["控制"],
                    "summary": "按白名单修改配置并立即生效",
                    "description": "可修改字段见 _API_CONFIG_WRITABLE（页面/方向/翻页/超时/跑马灯/颜色/数据源等显示类字段），自动保存。",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {
                            "state_machine": {"type": "string", "description": "页面名称或ID"},
                            "marquee_text": {"type": "string", "description": "跑马灯文本"},
                            "device": {"type": "string", "description": "目标屏名称，缺省=当前活跃屏"},
                        },
                        "additionalProperties": True,
                    }}}},
                    "responses": {"200": {"description": "已修改字段列表"}},
                }
            },
            "/api/device/select": {
                "post": {
                    "tags": ["控制"],
                    "summary": "切换当前活跃屏（多屏时改变后续命令作用设备）",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {"device": {"type": "string", "description": "目标屏名称（如 屏幕2）"}},
                    }}}},
                    "responses": {"200": {"description": "切换结果"}},
                }
            },
            "/api/device/refresh": {
                "post": {
                    "tags": ["信息"],
                    "summary": "刷新设备信息（返回当前设备连接快照）",
                    "responses": {"200": {"description": "设备数量与列表"}},
                }
            },
            "/api/marquee": {
                "post": {
                    "tags": ["投屏"],
                    "summary": "设置跑马灯文本并切到跑马灯页（text/speed/font_size/color 可选）",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {
                            "text": {"type": "string", "description": "跑马灯文本"},
                            "speed": {"type": "integer", "description": "滚动速度"},
                            "font_size": {"type": "integer", "description": "字号"},
                            "color": {"type": "string", "description": "颜色 #rrggbb"},
                            "device": {"type": "string", "description": "目标屏名称"},
                        }}}}},
                    "responses": {"200": {"description": "页面"}},
                }
            },
            "/api/notify": {
                "post": {
                    "tags": ["控制"],
                    "summary": "在 UI 底部状态栏显示通知文本（不投屏）",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {"text": {"type": "string", "description": "通知文本"}},
                    }}}},
                    "responses": {"200": {"description": "结果"}},
                }
            },
            "/api/quit": {
                "post": {
                    "tags": ["控制"],
                    "summary": "退出程序（需 force: true，延迟执行以便响应返回）",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {"force": {"type": "boolean"}},
                    }}}},
                    "responses": {"200": {"description": "结果"}},
                }
            },
            "/api/screen/id": {
                "post": {
                    "tags": ["控制"],
                    "summary": "屏幕序号检测：所有已连接屏显示各自屏号，超时后自动恢复原页面",
                    "description": "timeout 可覆盖设置的时长（秒，1~300），缺省用「设置→API接入」中配置的时长。返回生效时长与已触发屏。",
                    "requestBody": {"required": False, "content": {"application/json": {"schema": {
                        "type": "object", "properties": {"timeout": {"type": "integer", "description": "显示时长(秒)，可覆盖设置值"}},
                    }}}},
                    "responses": {"200": {"description": "ok + timeout + devices"}},
                }
            },
        },
        "components": {
            "schemas": {
                "InfoResponse": {
                    "type": "object",
                    "properties": {
                        "ok": {"type": "boolean"},
                        "name": {"type": "string"},
                        "version": {"type": "string"},
                        "screen": {
                            "type": "object",
                            "properties": {
                                "width": {"type": "integer"},
                                "height": {"type": "integer"},
                                "lcd": {"type": "array", "items": {"type": "integer"}},
                            },
                        },
                        "connected": {"type": "boolean"},
                        "page": {"type": "string"},
                        "pages": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "ScreenRequest": {
                    "type": "object",
                    "properties": {
                        "image": {"type": "string", "format": "byte", "description": "base64 编码的 PNG/JPG/BMP 图像"},
                        "rgb888": {"type": "string", "format": "byte", "description": "base64 编码的原始 RGB888 字节（W*H*3）"},
                        "pixels": {"type": "array", "items": {"type": "integer"}, "description": "扁平 RGB 列表（需同时给 width/height）"},
                        "width": {"type": "integer", "description": "pixels 方式的图像宽度"},
                        "height": {"type": "integer", "description": "pixels 方式的图像高度"},
                        "fit": {"type": "string", "enum": ["contain", "stretch", "cover"], "default": "stretch", "description": "显示方式：contain=自适应完整、stretch=拉伸填满、cover=填充裁剪"},
                        "device": {"type": "string", "description": "目标屏名称（如 屏幕1），缺省=当前活跃屏；可用 /api/devices 查询"},
                    },
                },
                "TextRequest": {
                    "type": "object",
                    "required": ["text"],
                    "properties": {
                        "text": {"type": "string", "description": "要显示的文本"},
                        "font_size": {"type": "integer", "default": 16, "minimum": 8, "maximum": 72, "description": "字号"},
                        "color": {"type": "string", "default": "#ffffff", "description": "文本颜色 #rrggbb"},
                        "x": {"type": "integer", "default": 0, "description": "x 坐标"},
                        "y": {"type": "integer", "default": 0, "description": "y 坐标"},
                        "align": {"type": "string", "enum": ["left", "center", "right"], "default": "left", "description": "水平对齐"},
                        "background": {"type": "string", "default": "#000000", "description": "背景色 #rrggbb"},
                        "device": {"type": "string", "description": "目标屏名称（如 屏幕1），缺省=当前活跃屏"},
                    },
                },
                "PageRequest": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "string", "description": "页面名称（或整数 ID），可用 /api/pages 查询可用名称"},
                        "device": {"type": "string", "description": "目标屏名称（如 屏幕1），缺省=当前活跃屏"},
                    },
                },
                "SlideshowRequest": {
                    "type": "object",
                    "required": ["images"],
                    "properties": {
                        "images": {"type": "array", "items": {"type": "string", "format": "byte"}, "description": "base64 编码的图像数组（PNG/JPG 等）"},
                        "interval": {"type": "number", "default": 3, "minimum": 0.5, "description": "轮播间隔（秒）"},
                        "fit": {"type": "string", "enum": ["contain", "stretch", "cover"], "default": "stretch", "description": "显示方式：contain=自适应完整、stretch=拉伸填满、cover=填充裁剪"},
                        "device": {"type": "string", "description": "目标屏名称（如 屏幕1），缺省=当前活跃屏"},
                    },
                },
            }
        },
    }


_API_CONSOLE_HTML = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>MSU2_MINI_V2 · 投屏控制台</title>
<style>
body{font-family:'Microsoft YaHei',sans-serif;margin:20px;color:#222;max-width:720px}
h1{margin-bottom:6px}
.tabs{display:flex;gap:6px;border-bottom:2px solid #4a90d9;margin-bottom:14px}
.tab{padding:8px 20px;border:1px solid #ccc;border-bottom:none;background:#f0f0f0;cursor:pointer;border-radius:6px 6px 0 0}
.tab.active{background:#4a90d9;color:#fff;font-weight:bold}
.panel{display:none}
.panel.active{display:block}
.row{margin:8px 0}
label{display:inline-block;width:110px;color:#555}
input[type=text],input[type=number]{padding:4px;width:210px}
input[type=number]{width:80px}
select{padding:4px}
button{padding:6px 14px;margin-right:8px;cursor:pointer}
.msg{color:#2e86c1;margin-top:10px;white-space:pre-wrap}
table{border-collapse:collapse;width:100%;margin-top:10px}
td,th{border:1px solid #ccc;padding:6px 8px;text-align:left}
.win-btn{background:#4a90d9;color:#fff;border:none;padding:4px 12px;border-radius:4px;cursor:pointer}
.stopbtn{background:#d9534f;color:#fff;border:none;padding:6px 14px;border-radius:4px;cursor:pointer}
.tok{position:absolute;right:20px;top:20px;color:#888}
code{background:#eee;padding:1px 4px;border-radius:3px}
</style></head><body>
<h1>MSU2_MINI_V2 · 投屏控制台</h1>
<div class="tok">令牌: <input type="text" id="tok" size="16" placeholder="(可选)"></div>
<div class="row" style="margin-bottom:10px"><label>目标屏幕:</label><select id="devSel" style="width:240px"></select></div>
<div class="tabs">
  <button class="tab active" onclick="showTab('cast',this)">🎨 投屏</button>
  <button class="tab" onclick="showTab('program',this)">🖥 选择程序</button>
  <button class="tab" onclick="showTab('docs',this)">📖 文档</button>
</div>

<div id="panel-cast" class="panel active">
  <h3>文本投屏</h3>
  <div class="row"><label>文本:</label><input type="text" id="txt" placeholder="要显示的文字"></div>
  <div class="row"><label>字号:</label><input type="number" id="fs" value="16" min="8" max="72"></div>
  <div class="row"><label>颜色:</label><input type="color" id="color" value="#ffffff"> <span id="colorHex">#ffffff</span></div>
  <div class="row"><label>背景色:</label><input type="color" id="bg" value="#000000"> <span id="bgHex">#000000</span></div>
  <div class="row"><label>对齐:</label><select id="align"><option value="left">左对齐</option><option value="center">居中</option><option value="right">右对齐</option></select></div>
  <div class="row"><label>X / Y:</label><input type="number" id="x" value="0"> <input type="number" id="y" value="0"></div>
  <button onclick="sendText()">投屏文本</button>
  <hr>
  <h3>图片投屏</h3>
  <div class="row"><input type="file" id="imgfile" accept="image/*" multiple> <button onclick="sendImage()">单张投屏</button></div>
  <div class="row"><label>显示方式:</label><select id="fitSel"><option value="contain">自适应(完整)</option><option value="stretch" selected>拉伸(填满)</option><option value="cover">填充(裁剪)</option></select></div>
  <div class="row"><label>轮播间隔(秒):</label><input type="number" id="slidInt" value="3" min="0.5" step="0.5"> <button onclick="sendSlideshow()">多图轮播</button></div>
  <div class="row" style="color:#888">多图轮播：可一次选择多张图片，按间隔自动切换；点「停止投屏」结束。</div>
  <div class="row"><button onclick="doClear()">清屏</button> <button class="stopbtn" onclick="stopCast()">⏹ 停止投屏</button></div>
  <div class="row"><button onclick="doScreenId()">🔢 屏幕序号检测</button> <span style="color:#888">所有屏幕显示各自屏号，N秒后自动恢复（时长在程序设置→API接入中配置）</span></div>
  <div class="msg" id="msg-cast"></div>
</div>

<div id="panel-program" class="panel">
  <p>选择本机窗口/程序，点击「投屏」即可把该窗口内容显示到副屏。</p>
  <button onclick="loadWindows()">刷新窗口列表</button> <button class="stopbtn" onclick="stopCast()">⏹ 停止投屏</button>
  <div class="msg" id="msg-program"></div>
  <table><thead><tr><th>窗口</th><th>操作</th></tr></thead><tbody id="winlist"></tbody></table>
</div>

<div id="panel-docs" class="panel">
  <p>机器可读规范（OpenAPI 3.0）：<a href="/api/openapi.json">/api/openapi.json</a></p>
  <p><b>接入协议：</b>HTTP/WebSocket/SSE（端口N）、TCP（JSON行，N+1）、UDP（JSON报，N+2）、ZeroMQ（REP，N+3，需pyzmq）、Windows命名管道（<code>\\.\pipe\MSU2_MINI_V2_api</code>）、Unix Domain Socket（api_unix.sock）、热文件夹（程序目录 hotfolder/，放入图片/文本即投屏）。<br>
  所有协议命令格式一致（JSON，<code>type</code> 为 screen/text/clear/slideshow/slideshow_stop/stop/page/mirror，可选 <code>device</code> 指定目标屏）。</p>
  <p>常用接口：</p>
  <ul>
    <li><code>POST /api/text</code> 文本投屏</li>
    <li><code>POST /api/screen</code> 整帧图像（base64 PNG / rgb888 / pixels）</li>
    <li><code>POST /api/screen/raw</code> 原始 RGB888 字节流</li>
    <li><code>POST /api/clear</code> 清屏</li>
    <li><code>POST /api/page</code> 切页</li>
    <li><code>GET /api/windows</code> 列出可投屏窗口</li>
    <li><code>POST /api/mirror</code> 投屏指定窗口</li>
    <li><code>GET /api/devices</code> 列出多屏设备（选择目标屏）</li>
    <li><code>GET /api/protocols</code> 列出全部接入协议与地址</li>
    <li><code>GET /api/status</code> 综合运行状态</li>
    <li><code>GET /api/screenshot</code> 获取当前屏画面</li>
    <li><code>POST /api/page/next</code> / <code>/api/page/prev</code> 翻页</li>
    <li><code>POST /api/key</code> 模拟按键（下翻页/上翻页/切换方向）</li>
    <li><code>POST /api/marquee</code> 跑马灯投屏</li>
    <li><code>POST /api/device/select</code> 切换活跃屏</li>
    <li><code>GET /api/info</code> 设备信息</li>
    <li>各投屏接口均可带 <code>device</code> 参数指定目标屏</li>
  </ul>
  <p>参数详见 <a href="/api/openapi.json">JSON 规范</a>，详细说明见 <a href="/docs">说明文档</a>。</p>
</div>

<script>
var TOKEN = localStorage.getItem('api_token') || '';
function saveToken(){ TOKEN = document.getElementById('tok').value.trim(); localStorage.setItem('api_token', TOKEN); }
document.getElementById('tok').value = TOKEN;
document.getElementById('tok').onchange = saveToken;
function showTab(name, btn){
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('active');});
  btn.classList.add('active');
  document.getElementById('panel-'+name).classList.add('active');
}
function api(path, opts){
  opts = opts || {};
  opts.headers = Object.assign({'Content-Type':'application/json'}, opts.headers||{});
  if(TOKEN){ opts.headers['X-API-Token'] = TOKEN; }
  return fetch(path, opts).then(function(r){ return r.json(); });
}
function setMsg(id, text){ document.getElementById(id).textContent = text; }
function getDev(){ var s=document.getElementById('devSel'); return s ? s.value : ''; }
function getFit(){ var s=document.getElementById('fitSel'); return s ? s.value : 'stretch'; }
function loadDevices(){
  api('/api/devices').then(function(r){
    var sel = document.getElementById('devSel');
    if(!sel) return;
    if(!r.ok || !r.devices || !r.devices.length){ sel.innerHTML = '<option value="">(默认屏)</option>'; return; }
    var html = '<option value="">(默认屏)</option>';
    r.devices.forEach(function(d){
      html += '<option value="' + d.name + '">' + d.name + (d.connected ? '' : ' (未连接)') + '</option>';
    });
    sel.innerHTML = html;
  });
}
loadDevices();
document.getElementById('color').oninput = function(){ document.getElementById('colorHex').textContent = this.value; };
document.getElementById('bg').oninput = function(){ document.getElementById('bgHex').textContent = this.value; };
function sendText(){
  api('/api/text', {method:'POST', body: JSON.stringify({
    text: document.getElementById('txt').value,
    font_size: parseInt(document.getElementById('fs').value)||16,
    color: document.getElementById('color').value,
    background: document.getElementById('bg').value,
    align: document.getElementById('align').value,
    x: parseInt(document.getElementById('x').value)||0,
    y: parseInt(document.getElementById('y').value)||0,
    device: getDev()
  })}).then(function(r){ setMsg('msg-cast', r.ok ? '已投屏文本' : '失败: ' + (r.error||'')); });
}
function sendImage(){
  var f = document.getElementById('imgfile').files[0];
  if(!f){ setMsg('msg-cast', '请先选择图片'); return; }
  var rd = new FileReader();
  rd.onload = function(){
    var b64 = rd.result.split(',')[1];
    api('/api/screen', {method:'POST', body: JSON.stringify({image:b64, fit:getFit(), device:getDev()})})
      .then(function(r){ setMsg('msg-cast', r.ok ? '已投屏图片' : '失败: ' + (r.error||'')); });
  };
  rd.readAsDataURL(f);
}
function doClear(){ api('/api/clear', {method:'POST', body: JSON.stringify({device:getDev()})}).then(function(r){ setMsg('msg-cast', r.ok ? '已清屏' : '失败'); }); }
function loadWindows(){
  setMsg('msg-program', '加载中...');
  api('/api/windows').then(function(r){
    var tb = document.getElementById('winlist');
    tb.innerHTML = '';
    if(!r.ok){ setMsg('msg-program', '加载失败: ' + (r.error||'')); return; }
    var list = r.windows || [];
    setMsg('msg-program', '共 ' + list.length + ' 个窗口');
    list.forEach(function(w){
      var tr = document.createElement('tr');
      var td1 = document.createElement('td'); td1.textContent = w.name;
      var td2 = document.createElement('td');
      var btn = document.createElement('button');
      btn.className = 'win-btn'; btn.textContent = '投屏';
      btn.onclick = function(){ mirrorWindow(w.hwnd); };
      td2.appendChild(btn);
      tr.appendChild(td1); tr.appendChild(td2);
      tb.appendChild(tr);
    });
  });
}
function mirrorWindow(hwnd){
  api('/api/mirror', {method:'POST', body: JSON.stringify({hwnd:hwnd, device:getDev()})})
    .then(function(r){ setMsg('msg-program', r.ok ? '已投屏窗口: ' + r.hwnd : '失败: ' + (r.error||'')); });
}
function sendSlideshow(){
  var files = document.getElementById('imgfile').files;
  if(!files.length){ setMsg('msg-cast', '请先选择多张图片'); return; }
  var interval = parseFloat(document.getElementById('slidInt').value) || 3;
  var images = [];
  var pending = files.length;
  for(var i=0;i<files.length;i++){
    (function(file){
      var rd = new FileReader();
      rd.onload = function(){
        images.push(rd.result.split(',')[1]);
        if(--pending === 0){ startSlideshow(images, interval); }
      };
      rd.readAsDataURL(file);
    })(files[i]);
  }
}
function startSlideshow(images, interval){
  api('/api/slideshow', {method:'POST', body: JSON.stringify({images:images, interval:interval, fit:getFit(), device:getDev()})})
    .then(function(r){ setMsg('msg-cast', r.ok ? ('已开始轮播 ' + r.count + ' 张，间隔 ' + r.interval + ' 秒') : '失败: ' + (r.error||'')); });
}
function stopCast(){
  api('/api/stop', {method:'POST', body: JSON.stringify({device:getDev()})})
    .then(function(r){ setMsg('msg-cast', r.ok ? '已停止投屏（回到 ' + r.page + ' 页）' : '失败: ' + (r.error||'')); });
}
function doScreenId(){
  api('/api/screen/id', {method:'POST', body: JSON.stringify({})})
    .then(function(r){ setMsg('msg-cast', r.ok ? ('🔢 已触发屏幕序号检测，持续 ' + r.timeout + ' 秒') : '失败: ' + (r.error||'')); });
}
</script>
</body></html>"""


_API_DOC_HTML = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>MSU2_MINI_V2 API 接入文档</title>
<style>body{{font-family:'Microsoft YaHei',sans-serif;margin:24px;color:#222;max-width:900px}}
pre{{background:#f5f5f5;padding:10px;border-radius:6px;overflow:auto}}
code{{background:#eee;padding:1px 4px;border-radius:3px}}
h2{{border-bottom:2px solid #4a90d9;padding-bottom:4px}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:6px 10px}}</style></head><body>
<h1>MSU2_MINI_V2 · API 接入文档</h1>
<p>📄 机器可读 JSON 规范（OpenAPI 3.0）：<a href="/api/openapi.json">/api/openapi.json</a>（程序可按此 JSON 自动对接/生成客户端）</p>
<p>通过本地 HTTP/WebSocket API，其他程序可以自定义投屏内容（图像、文本、清屏、切页、实时帧）。
服务地址：<code>http://127.0.0.1:{port}</code>，屏幕尺寸 <code>{size}</code>。
若设置了令牌，请携带请求头 <code>X-API-Token</code> 或查询参数 <code>?token=</code>。</p>

<h2>1. 基础信息</h2>
<pre>GET /api/info    设备与屏幕信息（JSON）
GET /api/pages   可用页面列表（JSON）</pre>

<h2>2. 投屏整帧图像</h2>
<pre>POST /api/screen    JSON，三种方式任选：
  A. image  : base64 编码的 PNG/JPG/BMP 图像
  B. rgb888 : base64 编码的原始 RGB888 字节（顺序 W*H*3）
  C. pixels : 扁平 RGB 列表（需同时给 width/height）</pre>
<pre># Python 示例（投屏一张 PNG）
import base64, requests
raw = open("pic.png","rb").read()
requests.post("http://127.0.0.1:{port}/api/screen", json={{ "image": base64.b64encode(raw).decode() }})</pre>

<h2>3. 原始字节流投屏（最低开销）</h2>
<pre>POST /api/screen/raw
Content-Type: application/octet-stream
Body: {bytes_len} 字节原始 RGB888（按屏幕 {size}）</pre>

<h2>4. 文本投屏</h2>
<pre>POST /api/text
{{ "text": "你好", "font_size": 16, "color": "#ff8000",
   "x": 0, "y": 0, "align": "left", "background": "#000000" }}
align: left / center / right</pre>

<h2>5. 清屏 / 切页</h2>
<pre>POST /api/clear            清空投屏帧
POST /api/page             {{ "page": "时间" }}  或 {{ "page": 1 }}
（页面名或 ID，可用 /api/pages 查看）</pre>

<h2>6. WebSocket 实时通道（/ws）</h2>
<p>二进制帧 = 原始 RGB888（{bytes_len} 字节），文本帧 = JSON 命令
（与 POST 一致：type 为 screen/text/clear/page）。适合高频推流。</p>
<pre># Python 示例
import socket, struct
# ...（标准 WebSocket 客户端即可，如 websocket-client / websockets）</pre>

<h2>7. curl 快速测试</h2>
<pre>curl http://127.0.0.1:{port}/api/info
curl -X POST http://127.0.0.1:{port}/api/text -H "Content-Type: application/json" -d '{{"text":"hello"}}'</pre>

<h2>8. 其他接入协议</h2>
<p>除 HTTP/WebSocket 外，还支持以下本地接入方式。命令格式与 HTTP JSON 一致（type 为
screen/text/clear/slideshow/slideshow_stop/stop/page/mirror，可选 device 指定目标屏）。</p>
<pre>TCP Socket : 127.0.0.1:{port_plus_1}，每行一个 JSON 命令，返回一行 JSON 响应
UDP        : 127.0.0.1:{port_plus_2}，每条数据报一个 JSON 命令
ZeroMQ     : tcp://127.0.0.1:{port_plus_3}（REP 模式，需 pip install pyzmq）
命名管道   : \\\.\\pipe\\MSU2_MINI_V2_api（JSON 行协议，Windows）
Unix Socket: 程序目录 api_unix.sock（JSON 行协议，需系统支持 AF_UNIX）
热文件夹   : 程序目录 hotfolder/，放入图片/文本即投屏（文件名 "屏幕1_xxx.png" 指定目标屏）
stdin 管道 : 管道/重定向启动时从标准输入按行读 JSON 命令
SSE 事件流 : GET /api/events，帧版本变化推送 event: frame（data=版本号）</pre>
<pre># TCP 示例（socket 客户端）
import socket
s = socket.create_connection(("127.0.0.1", {port_plus_1}))
s.sendall(b'{{"type":"text","text":"你好"}}\n')
print(s.recv(1024).decode())</pre>

<h2>9. 信息与状态查询</h2>
<pre>GET /api/health        健康检查（探测服务可用）
GET /api/version       版本与元数据
GET /api/protocols     列出全部接入协议与地址（自动发现）
GET /api/status        综合运行状态（设备/页面/方向/投屏中）
GET /api/config        读取当前屏完整配置（?device=屏幕1）
GET /api/screenshot    获取当前屏画面（PNG + RGB888 base64，?device=屏幕1）</pre>

<h2>10. 控制与配置接口</h2>
<pre>POST /api/page/next       翻下一页
POST /api/page/prev       翻上一页
POST /api/key             {{"action":"下翻页|上翻页|切换方向|无"}}
POST /api/orientation     {{"direction": 0~7 或 "next"}} 设置 LCD 方向
POST /api/marquee         {{"text":"...","speed":2,"font_size":20,"color":"#fff"}} 切到跑马灯页
POST /api/config/set      {{"marquee_text":"...","device":"屏幕1"}} 按白名单改配置
POST /api/device/select   {{"device":"屏幕2"}} 切换活跃屏
POST /api/device/refresh  刷新设备信息
POST /api/notify          {{"text":"通知"}} UI 状态栏通知
POST /api/screen/id       {{"timeout":5}} 屏幕序号检测（所有屏显示各自屏号，超时后自动恢复原页面）
POST /api/quit            {{"force":true}} 退出程序

以上所有控制命令也可通过 TCP/UDP/WebSocket 等协议发送（type 字段同名小写：page_next/page_prev/key/orientation/marquee/config_set/device_select/device_refresh/notify/quit/screen_id/health/version/protocols/status/config_get/screenshot）</pre>

<h2>11. 强制投屏</h2>
<p>在「设置 → API接入」勾选「强制投屏」后，无需把程序切换到「API投屏」页，任何页面（时间/热搜/仪表盘等）
都会被投屏内容覆盖显示。停止投屏后自动返回投屏前的页面（如 热搜）。
该选项按设备保存；未开启时仍需手动选择「API投屏」页才能看到投屏内容。</p>
</body></html>"""


def export_api_json(path=None):
    """导出 OpenAPI JSON 文档到文件。path 为空则存到程序目录 api_openapi.json，返回保存路径。"""
    try:
        doc = _build_openapi_doc()
        if not path:
            path = os.path.join(get_base_config_dir(), "api_openapi.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        return path
    except Exception as e:
        print("导出 API JSON 文档失败：%s" % e)
        return None


def _check_openapi_sync():
    """自动检查：代码中注册的 API 端点与 OpenAPI JSON 文档(_build_openapi_doc)是否一致。
    不一致时打印警告，提醒开发者同步更新 JSON 文档。
    若方法源码无法读取（如已打包成 exe、源码被移动），会提示并跳过比对，避免误报。"""
    try:
        import inspect as _inspect
        import re as _re
        code_routes = set()
        unreadable = []
        for method in ("do_GET", "do_POST"):
            try:
                src = _inspect.getsource(getattr(ApiHandler, method))
                code_routes.update(_re.findall(r'"(/api/[a-z_/]*|/ws)"', src))
            except Exception as e:
                unreadable.append("%s(%s)" % (method, e))
        if unreadable:
            print("API 同步检查：无法读取 %s 的源码，跳过端点比对（打包运行或源码被移动时属正常现象）"
                  % "、".join(unreadable))
            return
        doc_paths = set(_build_openapi_doc().get("paths", {}).keys())
        meta = {"/api/openapi.json", "/api.json", "/api/openapi", "/api", "/docs", "/"}
        real = code_routes - meta  # 功能性端点（排除文档/元端点）
        missing = real - doc_paths      # 代码有、JSON 文档缺失 → 需补进 _build_openapi_doc()
        extra = doc_paths - code_routes  # JSON 文档有、代码已移除 → 需从 _build_openapi_doc() 删除
        if missing:
            print("⚠ API 端点与 OpenAPI JSON 文档不同步：以下端点未加入 _build_openapi_doc() 的 paths → %s"
                  % sorted(missing))
        if extra:
            print("⚠ OpenAPI JSON 文档包含已不存在的端点（建议从 _build_openapi_doc() 删除）→ %s" % sorted(extra))
    except Exception as e:
        print("API 同步检查失败：%s" % e)


_api_tcp_server = None          # TCP Socket 服务器
_api_udp_sock = None            # UDP 套接字
_api_udp_thread = None          # UDP 监听线程
_api_udp_running = threading.Event()
_api_hotfolder_running = threading.Event()
_api_hotfolder_thread = None    # 热文件夹监视线程
_api_pipe_thread = None         # Windows 命名管道服务线程
_api_unix_server = None         # Unix Domain Socket 服务器
_api_unix_thread = None         # Unix Domain Socket 监听线程
_api_zmq_sock = None            # ZeroMQ 套接字
_api_zmq_thread = None          # ZeroMQ 监听线程
_api_extra_running = threading.Event()   # 附加协议统一停止信号（Unix/ZeroMQ）
_api_event_version = 0          # SSE 帧版本号（帧写入时递增）
_api_event_lock = threading.Lock()
_screen_id_until = 0.0          # 屏幕序号检测结束时间戳（time.monotonic），<=0 表示未在检测


def start_api_tcp():
    """TCP Socket 服务器（JSON 行协议），端口 = api_port + 1"""
    global _api_tcp_server
    if _api_tcp_server is not None:
        return
    try:
        import socketserver
        base = int(getattr(config_obj, "api_port", 8632))
    except Exception:
        return

    class _TcpHandler(socketserver.StreamRequestHandler):
        def handle(self):
            while True:
                try:
                    line = self.rfile.readline()
                except Exception:
                    break
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                    resp = api_execute_command(data)
                except Exception as e:
                    resp = {"ok": False, "error": str(e)}
                try:
                    out = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
                    self.wfile.write(out)
                    self.wfile.flush()
                except Exception:
                    break

    try:
        server = socketserver.ThreadingTCPServer(("127.0.0.1", base + 1), _TcpHandler)
        server.daemon_threads = True
        _api_tcp_server = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print("API TCP 服务器已启动: 127.0.0.1:%d (JSON 行协议)" % (base + 1))
    except Exception as e:
        _api_tcp_server = None
        print("API TCP 服务器启动失败: %s" % e)


def start_api_udp():
    """UDP 服务器（JSON 数据报），端口 = api_port + 2"""
    global _api_udp_sock, _api_udp_thread
    if _api_udp_sock is not None:
        return
    try:
        import socket
        base = int(getattr(config_obj, "api_port", 8632))
    except Exception:
        return
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", base + 2))
        sock.settimeout(1.0)
        _api_udp_sock = sock
        _api_udp_running.set()

        def _loop():
            while _api_udp_running.is_set():
                try:
                    data, addr = sock.recvfrom(65536)
                except Exception:
                    continue
                try:
                    cmd = json.loads(data.decode("utf-8"))
                    resp = api_execute_command(cmd)
                except Exception as e:
                    resp = {"ok": False, "error": str(e)}
                try:
                    sock.sendto((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"), addr)
                except Exception:
                    pass

        _api_udp_thread = threading.Thread(target=_loop, daemon=True)
        _api_udp_thread.start()
        print("API UDP 服务器已启动: 127.0.0.1:%d (JSON 数据报)" % (base + 2))
    except Exception as e:
        _api_udp_sock = None
        print("API UDP 服务器启动失败: %s" % e)


def start_api_hotfolder():
    """文件/热文件夹投屏：把图片/文本放进 hotfolder 目录即投屏（零协议）"""
    global _api_hotfolder_thread
    if _api_hotfolder_thread is not None:
        return
    try:
        folder = os.path.join(get_base_config_dir(), "hotfolder")
        os.makedirs(folder, exist_ok=True)
    except Exception:
        return
    _api_hotfolder_running.set()
    seen = {}

    def _handle(folder, fname, fpath):
        try:
            # 文件名支持 "屏幕1_xxx.png" 指定目标屏
            dev = None
            stem = fname
            for d in all_devices.values():
                dn = getattr(d, "device_name", "")
                if stem.startswith(dn + "_"):
                    dev = d
                    stem = stem[len(dn) + 1:]
                    break
            ext = os.path.splitext(fname)[1].lower()
            if ext in (".txt", ".md"):
                with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read().strip()
                if text:
                    _api_apply_text({"text": text, "font_size": 16, "color": "#ffffff"}, dev)
                    print("热文件夹投屏文本: %s" % fname)
            elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
                img = Image.open(fpath).convert("RGB")
                img = _api_resize_image(img, "contain")
                api_set_frame(np.asarray(img, dtype=np.uint8), dev)
                print("热文件夹投屏图片: %s" % fname)
            try:
                os.remove(fpath)  # 处理完删除，避免重复
            except Exception:
                pass
        except Exception as e:
            print("热文件夹处理失败 %s: %s" % (fname, e))

    def _loop():
        while _api_hotfolder_running.is_set():
            try:
                for fname in os.listdir(folder):
                    fpath = os.path.join(folder, fname)
                    if not os.path.isfile(fpath):
                        continue
                    key = fname + "|" + str(os.path.getmtime(fpath))
                    if seen.get(key):
                        continue
                    seen[key] = True
                    _handle(folder, fname, fpath)
            except Exception:
                pass
            _api_hotfolder_running.wait(1)

    _api_hotfolder_thread = threading.Thread(target=_loop, daemon=True)
    _api_hotfolder_thread.start()
    print("API 热文件夹已就绪: %s（放入图片/文本即投屏）" % folder)


def start_api_pipe():
    """Windows 命名管道（pywin32）：\\\\.\\pipe\\MSU2_MINI_V2_api，JSON 行协议（与 TCP 一致）"""
    global _api_pipe_thread
    if _api_pipe_thread is not None:
        return
    if not isWindows:
        return
    try:
        import win32pipe, win32file, pywintypes, winerror
    except Exception:
        print("未安装 pywin32，跳过 Windows 命名管道接入")
        return
    pipe_name = r"\\.\pipe\MSU2_MINI_V2_api"
    _BROKEN = (getattr(winerror, "ERROR_BROKEN_PIPE", 109),
               getattr(winerror, "ERROR_PIPE_NOT_CONNECTED", 233), 0)

    def _handle_client(pipe):
        buf = b""
        while True:
            try:
                hr, data = win32file.ReadFile(pipe, 65536)
            except pywintypes.error as e:
                if getattr(e, "winerror", None) in _BROKEN:
                    break
                continue
            except Exception:
                break
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    cmd = json.loads(line.decode("utf-8"))
                    resp = api_execute_command(cmd)
                except Exception as e:
                    resp = {"ok": False, "error": str(e)}
                try:
                    win32file.WriteFile(pipe, (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
                except Exception:
                    return

    def _loop():
        while True:
            try:
                pipe = win32pipe.CreateNamedPipe(
                    pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES, 65536, 65536, 0, None)
            except Exception:
                time.sleep(1)
                continue
            try:
                win32pipe.ConnectNamedPipe(pipe, None)  # 阻塞等待客户端
            except pywintypes.error as e:
                if getattr(e, "winerror", None) != getattr(winerror, "ERROR_PIPE_CONNECTED", 535):
                    try:
                        win32pipe.DisconnectNamedPipe(pipe)
                    except Exception:
                        pass
                    continue
            except Exception:
                try:
                    win32pipe.DisconnectNamedPipe(pipe)
                except Exception:
                    pass
                continue
            try:
                _handle_client(pipe)
            except Exception:
                pass
            try:
                win32pipe.DisconnectNamedPipe(pipe)
            except Exception:
                pass

    _api_pipe_thread = threading.Thread(target=_loop, daemon=True)
    _api_pipe_thread.start()
    print("API 命名管道已就绪: %s" % pipe_name)


def start_api_unix():
    """Unix Domain Socket（零依赖，Windows 10 1803+ / Python 3.9+）：程序目录 api_unix.sock，JSON 行协议"""
    global _api_unix_server, _api_unix_thread
    if _api_unix_server is not None:
        return
    import socket as _sock
    try:
        path = os.path.join(get_base_config_dir(), "api_unix.sock")
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        server = _sock.socket(_sock.AF_UNIX, _sock.SOCK_STREAM)
        server.bind(path)
        server.listen(8)
        server.settimeout(1.0)
        _api_unix_server = server
    except Exception as e:
        print("API Unix Domain Socket 不可用（当前系统不支持 AF_UNIX）: %s" % e)
        _api_unix_server = None
        return

    def _client(conn):
        try:
            f = conn.makefile("rb")
            while True:
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                    resp = api_execute_command(data)
                except Exception as e:
                    resp = {"ok": False, "error": str(e)}
                try:
                    conn.sendall((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
                except Exception:
                    break
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _loop():
        while _api_extra_running.is_set():
            try:
                conn, _ = server.accept()
            except Exception:
                continue
            threading.Thread(target=_client, args=(conn,), daemon=True).start()

    _api_unix_thread = threading.Thread(target=_loop, daemon=True)
    _api_unix_thread.start()
    print("API Unix Domain Socket 已就绪: %s" % path)


def start_api_zmq():
    """ZeroMQ（需 pyzmq，未安装则跳过）：tcp://127.0.0.1:端口+3，REP/REQ 模式，JSON 消息"""
    global _api_zmq_sock, _api_zmq_thread
    if _api_zmq_sock is not None:
        return
    try:
        import zmq
    except Exception:
        print("未安装 pyzmq，跳过 ZeroMQ 接入（如需启用请 pip install pyzmq）")
        return
    try:
        base = int(getattr(config_obj, "api_port", 8632))
    except Exception:
        return
    try:
        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.REP)
        sock.bind("tcp://127.0.0.1:%d" % (base + 3))
        _api_zmq_sock = sock

        def _loop():
            while _api_extra_running.is_set():
                try:
                    msg = sock.recv()
                except Exception:
                    break
                try:
                    data = json.loads(msg.decode("utf-8"))
                    resp = api_execute_command(data)
                except Exception as e:
                    resp = {"ok": False, "error": str(e)}
                try:
                    sock.send(json.dumps(resp, ensure_ascii=False).encode("utf-8"))
                except Exception:
                    break

        _api_zmq_thread = threading.Thread(target=_loop, daemon=True)
        _api_zmq_thread.start()
        print("API ZeroMQ 已启动: tcp://127.0.0.1:%d (REP/REQ, JSON)" % (base + 3))
    except Exception as e:
        try:
            if _api_zmq_sock is not None:
                _api_zmq_sock.close()
        except Exception:
            pass
        _api_zmq_sock = None
        print("API ZeroMQ 启动失败: %s" % e)


def _api_stdin_loop():
    """常驻 stdin 管道：从标准输入按行读取 JSON 命令执行（echo ... | python MSU2_MINI_V2.py）"""
    while True:
        try:
            line = sys.stdin.readline()
        except Exception:
            break
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            resp = api_execute_command(data)
        except Exception as e:
            resp = {"ok": False, "error": str(e)}
        try:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception:
            break


def stop_api_extra():
    """停止 TCP / UDP / 热文件夹 / Unix Socket / ZeroMQ（命名管道为 daemon 线程随程序退出结束）"""
    global _api_tcp_server, _api_udp_sock, _api_udp_thread, _api_hotfolder_thread
    global _api_unix_server, _api_unix_thread, _api_zmq_sock, _api_zmq_thread
    if _api_tcp_server is not None:
        try:
            _api_tcp_server.shutdown()
        except Exception:
            pass
        try:
            _api_tcp_server.server_close()
        except Exception:
            pass
        _api_tcp_server = None
    _api_udp_running.clear()
    if _api_udp_sock is not None:
        try:
            _api_udp_sock.close()
        except Exception:
            pass
        _api_udp_sock = None
    if _api_udp_thread is not None:
        try:
            _api_udp_thread.join(timeout=2)
        except Exception:
            pass
        _api_udp_thread = None
    _api_hotfolder_running.clear()
    if _api_hotfolder_thread is not None:
        try:
            _api_hotfolder_thread.join(timeout=2)
        except Exception:
            pass
        _api_hotfolder_thread = None
    _api_extra_running.clear()
    if _api_unix_server is not None:
        try:
            _api_unix_server.close()
        except Exception:
            pass
        _api_unix_server = None
    if _api_unix_thread is not None:
        try:
            _api_unix_thread.join(timeout=2)
        except Exception:
            pass
        _api_unix_thread = None
    if _api_zmq_sock is not None:
        try:
            _api_zmq_sock.close()
        except Exception:
            pass
        _api_zmq_sock = None
    if _api_zmq_thread is not None:
        try:
            _api_zmq_thread.join(timeout=2)
        except Exception:
            pass
        _api_zmq_thread = None


def start_api_server():
    """启动本地全部 API 接入（HTTP + WebSocket + TCP + UDP + 热文件夹），仅监听 127.0.0.1"""
    global _api_server
    if _api_server is not None:
        return
    try:
        port = int(getattr(config_obj, "api_port", 8632))
    except Exception:
        port = 8632
    try:
        from http.server import ThreadingHTTPServer
        server = ThreadingHTTPServer(("127.0.0.1", port), ApiHandler)
        _api_server = server
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print("API 投屏服务器已启动: http://127.0.0.1:%d" % port)
        start_api_tcp()        # TCP Socket（JSON 行协议）
        start_api_udp()        # UDP（JSON 数据报）
        start_api_hotfolder()  # 文件/热文件夹投屏
        start_api_pipe()       # Windows 命名管道
        start_api_unix()       # Unix Domain Socket
        start_api_zmq()        # ZeroMQ（需 pyzmq）
        _check_openapi_sync()  # 启动时校验端点与 JSON 文档同步性
        try:
            export_api_json()  # 生成 api_openapi.json 到程序目录，便于其他程序直接读取
        except Exception:
            pass
    except Exception as e:
        _api_server = None
        print("API 投屏服务器启动失败: %s" % e)


def stop_api_server():
    """停止本地全部 API 接入（HTTP + WebSocket + TCP + UDP + 热文件夹）"""
    global _api_server
    if _api_server is not None:
        try:
            _api_server.shutdown()
        except Exception:
            pass
        try:
            _api_server.server_close()
        except Exception:
            pass
        _api_server = None
    stop_api_extra()


def _api_try_screen_id(device=None):
    """屏幕序号检测：检测期间直接发送本屏屏号帧并返回 True（跳过普通页面渲染），超时后自动恢复原页面。"""
    try:
        if _screen_id_until <= 0:
            return False
        if time.monotonic() >= _screen_id_until:
            return False
        dev = device if device is not None else get_current_device()
        if dev is None:
            return False
        name = getattr(dev, "device_name", "屏幕1")
        img = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = MiniMark.load_font("./simhei.ttf", 22)
        except Exception:
            font = default_font
        bbox = draw.textbbox((0, 0), name, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((SHOW_WIDTH - tw) // 2, (SHOW_HEIGHT - th) // 2), name,
                  fill=(255, 255, 255), font=font)
        _safe_send_rgb888(np.asarray(img, dtype=np.uint8))
        dev.sleep_event.wait(0.05)
        return True
    except Exception:
        return False


def api_trigger_screen_id(data=None):
    """触发屏幕序号检测：所有已连接屏显示各自屏号，超时后自动恢复原页面。
    data.timeout 可覆盖设置的时长（秒）。返回响应 dict"""
    global _screen_id_until
    try:
        timeout = float((data or {}).get("timeout", getattr(config_obj, "screen_id_timeout", 5) or 5))
    except Exception:
        timeout = 5.0
    timeout = max(1.0, min(timeout, 300.0))
    _screen_id_until = time.monotonic() + timeout
    # 触发所有已连接屏立即重绘（显示屏号）
    for d in all_devices.values():
        if getattr(d, "device_state", 0) == 1:
            d.state_change = 1
            d.force_lcd_reset = True
            try:
                d.sleep_event.set()
            except Exception:
                pass
    return {"ok": True, "timeout": timeout, "devices":
            [d.device_name for d in all_devices.values() if getattr(d, "device_state", 0) == 1]}


def _api_try_overlay(device=None):
    """强制投屏覆盖：开启 api_overlay 且指定屏有投屏帧时，直接发送帧并返回 True（跳过普通页面渲染）。
    投屏停止(清帧)后自动恢复原页面渲染，无需切页。"""
    try:
        if not getattr(config_obj, "api_overlay", 0):
            return False
        dev = device if device is not None else get_current_device()
        if dev is None:
            return False
        frame = api_get_frame(dev)
        if frame is None:
            return False
        if dev.state_change == 1:
            state_change_clear()
            LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        _safe_send_rgb888(frame)
        dev.sleep_event.wait(0.05)
        return True
    except Exception:
        return False


def show_api():
    """API 投屏页面：有外部帧则发送，否则显示接入提示"""
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    frame = api_get_frame()
    if frame is not None:
        _safe_send_rgb888(frame)
        dev.sleep_event.wait(0.05)
        return
    try:
        port = int(getattr(config_obj, "api_port", 8632))
    except Exception:
        port = 8632
    img = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = MiniMark.load_font("./simhei.ttf", 14)
    small = MiniMark.load_font("./simhei.ttf", 10)
    draw.text((4, 2), "API 投屏", fill=(255, 255, 255), font=font)
    draw.text((4, 22), "http://127.0.0.1:%d" % port, fill=(120, 200, 255), font=small)
    draw.text((4, 40), "等待外部程序接入...", fill=(180, 180, 180), font=small)
    rgb888 = np.asarray(img, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(1)


def _render_two_line_bars(up_label, down_label, up_value, down_value,
                          up_color, down_color, bar1_color, bar2_color,
                          plot_data, key1, key2, back_color=(0, 0, 0)):
    """通用两行速度显示（网络流量布局）：上行/下行文字 + 两条实时柱状图。
    标签、数值、颜色、柱状图数据均外部传入，供网络流量与磁盘读写经典2样式共用。"""
    global default_font
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back_color)
    draw = ImageDraw.Draw(im1)

    text = "%s %9s/s" % (up_label, sizeof_fmt(up_value))
    draw.text((0, 0), text, fill=up_color, font=default_font)
    text = "%s %9s/s" % (down_label, sizeof_fmt(down_value))
    draw.text((0, SHOW_HEIGHT // 2), text, fill=down_color, font=default_font)

    min_draw = 1
    for start_y, key, color in zip([SHOW_HEIGHT // 4 - 1, SHOW_HEIGHT - SHOW_HEIGHT // 4 - 1],
                                   [key1, key2], [bar1_color, bar2_color]):
        values = plot_data[key]
        max_value = max(min_draw, max(values))
        x0 = -BAR_WIDTH
        x1 = -1
        y1 = IMAGE_HEIGHT + start_y
        percent = IMAGE_HEIGHT / max_value
        for sent in values[-(SHOW_WIDTH // BAR_WIDTH):]:
            bar_height = percent * sent
            x0 += BAR_WIDTH
            x1 += BAR_WIDTH
            y0 = y1 - bar_height
            draw.rectangle([x0, y0, x1, y1], fill=color)

    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)


def show_netspeed(up_text_color=(255, 128, 0), down_text_color=(0, 255, 255),
                  bar1_color=(235, 139, 139), bar2_color=(146, 211, 217), back_color=(0, 0, 0)):
    global default_font
    dev = get_current_device()
    if dev is None: return
    current_monoto_time = time.monotonic()

    current_snetio = psutil.net_io_counters()
    if dev.state_change == 1 or dev.netspeed_last_refresh_snetio is None:
        state_change_clear()
        dev.wait_time = 0
        dev.last_refresh_time = current_monoto_time - 0.001
        dev.netspeed_last_refresh_snetio = current_snetio
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    seconds_elapsed = current_monoto_time - dev.last_refresh_time

    sent_per_second = (current_snetio.bytes_sent - dev.netspeed_last_refresh_snetio.bytes_sent) / seconds_elapsed
    recv_per_second = (current_snetio.bytes_recv - dev.netspeed_last_refresh_snetio.bytes_recv) / seconds_elapsed
    new_data_half = (sent_per_second // 2, recv_per_second // 2)
    sent_per_second = dev.last_data_half[0] + new_data_half[0]
    recv_per_second = dev.last_data_half[1] + new_data_half[1]
    dev.last_data_half = new_data_half
    dev.netspeed_plot_data["sent"].pop(0)
    dev.netspeed_plot_data["recv"].pop(0)
    dev.netspeed_plot_data["sent"].append(sent_per_second)
    dev.netspeed_plot_data["recv"].append(recv_per_second)

    dev.last_refresh_time = current_monoto_time
    dev.netspeed_last_refresh_snetio = current_snetio

    _render_two_line_bars("上传", "下载", sent_per_second, recv_per_second,
                          up_text_color, down_text_color, bar1_color, bar2_color,
                          dev.netspeed_plot_data, "sent", "recv", back_color)

    dev.wait_time += 1 - seconds_elapsed
    if dev.wait_time > 0:
        dev.sleep_event.wait(dev.wait_time)


# 独立线程加载，忽略错误，以免错误影响到程序的其他功能
def load_hardware_monitor():
    from HardwareMonitor import Hardware

    # see `import HardwareMonitor.Util.SensorTypeUnitFormatter`
    SensorTypeUnitFormatter = {
        Hardware.SensorType.Voltage: [sizeof_fmt, "V", 1000],
        Hardware.SensorType.Current: [sizeof_fmt, "A", 1000],
        Hardware.SensorType.Clock: [sizeof_fmt, "Hz", 1000, 1000 * 1000],
        Hardware.SensorType.Load: "{:.1f}%",
        Hardware.SensorType.Temperature: "{:.1f}°C",
        Hardware.SensorType.Fan: [sizeof_fmt, "RPM", 1000],
        Hardware.SensorType.Flow: [sizeof_fmt, "L/h", 1000],
        Hardware.SensorType.Control: "{:.1f}%",
        Hardware.SensorType.Level: "{:.1f}%",
        Hardware.SensorType.Power: [sizeof_fmt, "W", 1000],
        Hardware.SensorType.Data: [sizeof_fmt, "B", 1024, 1024 * 1024 * 1024],
        Hardware.SensorType.SmallData: [sizeof_fmt, "B", 1024, 1024 * 1024],
        Hardware.SensorType.Factor: "{:.3f}",
        Hardware.SensorType.Frequency: [sizeof_fmt, "Hz", 1000],
        Hardware.SensorType.Throughput: [sizeof_fmt, "B/s", 1024],
        Hardware.SensorType.TimeSpan: "{}",
        Hardware.SensorType.Energy: [sizeof_fmt, "Wh", 1000, 0.001],
    }

    def FormatSensor(value: float, sensortype) -> str:
        if value is None:
            return "--"
        formatStr = SensorTypeUnitFormatter.get(sensortype, "{}")
        if isinstance(formatStr, list):
            if len(formatStr) > 3:
                value *= formatStr[3]
            return formatStr[0](value, suffix=formatStr[1], base=formatStr[2])
        else:
            return formatStr.format(value)

    class UpdateVisitor(Hardware.IVisitor):
        __namespace__ = "TestHardwareMonitor"

        def __init__(self):
            self.sensors = []

        def VisitComputer(self, computer: Hardware.IComputer):
            computer.Traverse(self)

        def VisitHardware(self, hardware: Hardware.IHardware):
            hardware.Update()
            for sensor in hardware.Sensors:
                self.sensors.append([hardware, sensor])

            for subHardware in hardware.SubHardware:
                self.VisitHardware(subHardware)

        def VisitParameter(self, parameter: Hardware.IParameter):
            pass

        def VisitSensor(self, sensor: Hardware.ISensor):
            pass

    def format_sensor_name(hardware, sensor):
        return "%s: %s - %s" % (hardware.Name, sensor.SensorType, sensor.Name)

    class HardwareMonitorManager:
        def __init__(self):
            self.computer = Hardware.Computer()
            self.computer.IsBatteryEnabled = True
            self.computer.IsControllerEnabled = True
            self.computer.IsCpuEnabled = True
            self.computer.IsGpuEnabled = True
            self.computer.IsMemoryEnabled = True
            self.computer.IsMotherboardEnabled = True
            self.computer.IsNetworkEnabled = True
            self.computer.IsPsuEnabled = True
            self.computer.IsStorageEnabled = True
            self.computer.Open()

            self.visitor = UpdateVisitor()
            self.computer.Accept(self.visitor)

            self.sensors = {format_sensor_name(hardware, sensor): (hardware, sensor)
                            for hardware, sensor in self.visitor.sensors}
            # 初始全部更新一遍，否则第一次获取可能是错误的数据(没必要，加载太慢且多耗内存，并且非必现)
            # for hardware, _ in self.visitor.sensors:
            #     hardware.Update()

        def get_hardware(self, sensor_name):
            if sensor_name in self.sensors:
                hardware, _ = self.sensors[sensor_name]
                return hardware
            else:
                return None

        @staticmethod
        def update_hardwares(hardwares):
            for hardware in hardwares:
                hardware.Update()

        def get_value(self, sensor_name):
            if sensor_name in self.sensors:
                _, sensor = self.sensors[sensor_name]
                return sensor.Value
            else:
                return None

        def get_value_formatted(self, sensor_name):
            if sensor_name in self.sensors:
                _, sensor = self.sensors[sensor_name]
                return sensor.Value, FormatSensor(sensor.Value, sensor.SensorType)
            else:
                return None, "--"

        def list_sensors(self):
            """返回所有传感器：[(全名, hardware, sensor, 类型字符串, 当前值), ...]"""
            return [(name, hw, s, str(s.SensorType), s.Value)
                    for name, (hw, s) in self.sensors.items()]

    return HardwareMonitorManager


def get_draw_text(text, font_size=20, front_color=None, back_color=(0, 0, 0)):
    global config_obj

    if not front_color:
        front_color = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
    # 绘制图片
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back_color)
    draw = ImageDraw.Draw(im1)
    # 绘制文字
    font = MiniMark.load_font("./simhei.ttf", font_size)
    font_l = font.getlength(text)
    draw.text(((SHOW_WIDTH - font_l) // 2, (SHOW_HEIGHT - font_size) // 2), text, fill=front_color, font=font)

    rgb888 = np.asarray(im1, dtype=np.uint32)
    return rgb888


def draw_text(text, font_size=20, front_color=None, back_color=(0, 0, 0)):
    rgb888 = get_draw_text(text, font_size, front_color, back_color)
    _safe_send_rgb888(rgb888)


def show_custom_two_rows(text_color=(255, 128, 0), bar1_color=(235, 139, 139),
                         bar2_color=(146, 211, 217), back_color=(0, 0, 0)):
    global config_obj, hardware_monitor_manager, netspeed_font, custom_plot_data_ref
    dev = get_current_device()
    if dev is None: return
    current_monoto_time = time.monotonic()
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        draw_text("加载中…")
        dev.sleep_event.wait(0.5)
        return

    if dev.state_change == 1:
        state_change_clear()
        dev.wait_time = 0
        dev.last_refresh_time = current_monoto_time
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    # 获取 libre hardware monitor 数值
    hardwares = set()  # 因为hardware同一个周期内不能重复更新，所以这里用set去掉重复项
    for name in config_obj.custom_selected_names:
        if name == "":
            continue
        hardware = hardware_monitor_manager.get_hardware(name)
        if hardware is not None:
            hardwares.add(hardware)
    hardware_monitor_manager.update_hardwares(hardwares)

    sent, sent_text = hardware_monitor_manager.get_value_formatted(config_obj.custom_selected_names[0])
    if sent is None:
        sent = 0

    recv, recv_text = hardware_monitor_manager.get_value_formatted(config_obj.custom_selected_names[1])
    if recv is None:
        recv = 0

    dev.custom_plot_data["sent"].pop(0)
    dev.custom_plot_data["sent"].append(sent)
    dev.custom_plot_data["recv"].pop(0)
    dev.custom_plot_data["recv"].append(recv)

    seconds_elapsed = current_monoto_time - dev.last_refresh_time
    dev.last_refresh_time = current_monoto_time

    # 绘制图片

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back_color)
    draw = ImageDraw.Draw(im1)

    text = "%-6s %-s" % (config_obj.custom_selected_displayname[0][:8], sent_text)
    draw.text((0, 0), text, fill=text_color, font=netspeed_font)
    text = "%-6s %-s" % (config_obj.custom_selected_displayname[1][:8], recv_text)
    draw.text((0, SHOW_HEIGHT // 2), text, fill=text_color, font=netspeed_font)

    min_max = [0.001, 0.001]
    for start_y, key, color, minmax_it in zip([SHOW_HEIGHT // 4 - 1, SHOW_HEIGHT - SHOW_HEIGHT // 4 - 1],
                                              ["sent", "recv"], [bar1_color, bar2_color], min_max):
        sent_values = dev.custom_plot_data[key]

        min_value = min(sent_values)
        max_value = max(minmax_it, min_value * 2, max(sent_values))

        x0 = -BAR_WIDTH
        x1 = -1
        y1 = IMAGE_HEIGHT + start_y
        percent = IMAGE_HEIGHT / max_value
        for i, sent in enumerate(sent_values[-(SHOW_WIDTH // BAR_WIDTH):]):
            bar_height = percent * sent
            x0 += BAR_WIDTH
            x1 += BAR_WIDTH
            y0 = y1 - bar_height
            draw.rectangle([x0, y0, x1, y1], fill=color)

    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)

    dev.wait_time += 1 - seconds_elapsed
    if dev.wait_time > 0:
        dev.sleep_event.wait(dev.wait_time)


def get_full_custom_im(update_sensors=True):
    """渲染完全自定义页面图像。
    
    Args:
        update_sensors: True=更新硬件传感器(daemon线程LCD显示用),
                        False=跳过传感器更新(UI线程预览用,避免并发问题)
    """
    global config_obj, full_custom_error, mini_mark_parser, hardware_monitor_manager
    dev = get_current_device()
    custom_render_lock = dev.custom_render_lock if dev else threading.Lock()

    # 防御：锁保护，防止UI线程(预览)与daemon线程(LCD渲染)并发执行
    # UI线程使用非阻塞获取，获取不到直接返回占位图
    if not update_sensors:
        if not custom_render_lock.acquire(blocking=False):
            # daemon线程正在渲染，UI预览跳过本次更新
            im = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (255, 255, 255))
            return im
    else:
        custom_render_lock.acquire()
    
    try:
        full_custom_error_tmp = ""
        # 获取 libre hardware monitor 数值
        if update_sensors:
            hardwares = set()  # 因为hardware不能重复更新，所以这里用set去掉重复项
            for name in config_obj.custom_selected_names_tech:
                if name == "":
                    continue
                hardware = hardware_monitor_manager.get_hardware(name)
                if hardware is not None:
                    hardwares.add(hardware)
            hardware_monitor_manager.update_hardwares(hardwares)

        record_dict = {}
        index = 1
        for name in config_obj.custom_selected_names_tech:
            value = None
            value_formatted = "--"  # 不能为None，否则解析时可能会有异常
            if name != "":
                if update_sensors:
                    value, value_formatted = hardware_monitor_manager.get_value_formatted(name)
                else:
                    value = 0  # UI预览模式，使用占位值
                if value is None:
                    if windll.shell32.IsUserAnAdmin():
                        full_custom_error_tmp += "获取项目 \"%s\" 失败，请检查设置。\n" % name
                    else:
                        full_custom_error_tmp += "获取项目 \"%s\" 失败，请尝试以管理员身份运行本程序。\n" % name
            # 没有数据也要放入列表，因为脚本是用序号来读数据的
            record_dict[str(index)] = (value_formatted, value)
            index += 1

        # 绘制图片

        im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (255, 255, 255))  # 默认全黑

        draw = ImageDraw.Draw(im1)
        error_line = ""
        try:
            mini_mark_parser.reset_state()
            frame_time = time.monotonic()
            for line in config_obj.full_custom_template.split('\n'):
                line = line.rstrip('\r')  # possible
                error_line = line
                mini_mark_parser.parse_line(line, draw, im1, record_dict=record_dict, frame_time=frame_time)
            if full_custom_error_tmp != "":
                if full_custom_error != full_custom_error_tmp:
                    full_custom_error = full_custom_error_tmp
            elif full_custom_error != "OK":
                full_custom_error = "OK"
        except Exception as e:
            full_custom_error = "%s\nerror line: %s" % (traceback.format_exc(), error_line)
            im1.paste((255, 0, 255), (0, 0, im1.size[0], im1.size[1]))  # 异常时显示粉色
    finally:
        custom_render_lock.release()

    return im1


def show_full_custom():
    global hardware_monitor_manager
    dev = get_current_device()
    if dev is None: return
    current_monoto_time = time.monotonic()
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        draw_text("加载中…")
        dev.sleep_event.wait(0.5)
        return

    if dev.state_change == 1:
        state_change_clear()
        dev.wait_time = 0
        dev.last_refresh_time = current_monoto_time
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    seconds_elapsed = current_monoto_time - dev.last_refresh_time
    dev.last_refresh_time = current_monoto_time

    im1 = get_full_custom_im()
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)

    dev.wait_time += 1 - seconds_elapsed
    if dev.wait_time > 0:
        dev.sleep_event.wait(dev.wait_time)


# UI批量同步控件（切换设备刷新设置页/主控页）时抑制落盘，刷新完统一保存一次，
# 避免几十个控件的 trace 回调各自触发 save_config 造成切换卡顿
_ui_batch_sync = False


# now 是否立即保存
def save_config(now=False):
    global last_config_save_time, save_thread, config_event
    if _ui_batch_sync:
        return
    last_config_save_time = time.monotonic()
    if now:
        last_config_save_time -= 5
        config_event.set()  # 取消sleep, 使config_event.wait无效

    if not save_thread or not save_thread.is_alive():
        save_thread = threading.Thread(target=save_config_thread, daemon=True)
        save_thread.start()


def save_config_thread():
    global config_obj, config_file, last_config_save_time, config_event
    sleep_time = last_config_save_time - time.monotonic() + 5  # 5秒没有任何修改再保存
    while sleep_time > 0:
        if config_event.is_set():
            config_event.clear()  # 使config_event.wait生效
        config_event.wait(sleep_time)
        sleep_time = last_config_save_time - time.monotonic() + 5

    try:
        # 原子写入：先写临时文件再替换，即使写入中途程序崩溃也不会留下损坏的配置JSON
        tmp_file = config_file + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(config_obj.__dict__, f)
        os.replace(tmp_file, config_file)
    except Exception as e:
        print("写入配置失败：%s" % e)


def load_config():
    global config_file
    config_obj = sys_config()
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_obj.__dict__.update(json.load(f))
    except FileNotFoundError:
        save_config()
    except Exception as e:
        print("读取配置失败，使用默认配置：%s" % e)
    return config_obj


def get_base_config_dir():
    """程序目录"""
    return os.path.dirname(os.path.realpath(sys.argv[0]))


def get_config_dir():
    """配置保存目录：程序目录下的 config 子目录（集中存放，避免丢失/与程序文件混淆）"""
    d = os.path.join(get_base_config_dir(), "config")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def migrate_old_config():
    """把程序根目录下已有的旧配置文件迁移到 config 子目录（首次运行自动执行，保留原件）"""
    old_dir = get_base_config_dir()
    new_dir = get_config_dir()
    if os.path.normpath(old_dir) == os.path.normpath(new_dir):
        return
    try:
        for name in os.listdir(old_dir):
            if name.startswith("MSU2_MINI") and name.endswith(".json"):
                old = os.path.join(old_dir, name)
                new = os.path.join(new_dir, name)
                if os.path.exists(old) and not os.path.exists(new):
                    shutil.copy2(old, new)
                    print("配置文件已迁移: %s" % name)
    except Exception as e:
        print("配置文件迁移失败：%s" % e)


def device_config_path(serial, port=""):
    """按 serial_number 生成配置文件路径（保存在 config 子目录）。
    port 用于 SN 为空 或 多设备 SN 相同（冲突）时按端口区分，避免配置冲突。"""
    base = get_config_dir()
    if serial and port:
        # SN 冲突：SN + 端口区分（如 MSU2_MINI_<serial>_<port>.json）
        return os.path.join(base, "MSU2_MINI_%s_%s.json" % (serial, port.replace("COM", "", 1)))
    if serial:
        return os.path.join(base, "MSU2_MINI_%s.json" % serial)
    if port:
        # SN 为空：按端口区分
        return os.path.join(base, "MSU2_MINI_%s.json" % port.replace("COM", "", 1))
    return os.path.join(base, "MSU2_MINI.json")


def _serial_in_use_by_other(serial, device):
    """serial 是否已被其它已连接设备占用（用于多设备 SN 相同冲突检测）"""
    for d in all_devices.values():
        if d is device:
            continue
        if d.serial_number == serial and d.device_state == 1:
            return True
    return False


def load_device_config(device, serial=""):
    """为设备加载/创建独立配置。
    正常按 serial_number 保存；多设备 SN 相同（冲突）或 SN 为空时按端口区分，
    避免配置冲突。首次连接以当前全局配置为模板，迁移已有设置。"""
    global config_obj, config_file
    device.serial_number = serial or ""
    # 重连（已加载过配置）：保持原配置文件，避免配置归属漂移
    if device.config is not None and device.config_file:
        return device.config
    # SN冲突检测：同SN已被其它已连接设备占用 → 按端口区分保存
    port_suffix = ""
    if device.serial_number:
        if _serial_in_use_by_other(device.serial_number, device):
            port_suffix = device.com_port
    else:
        # SN 为空：若存在其它无SN设备则按端口区分，否则用默认文件
        other_empty = [d for d in all_devices.values()
                       if d is not device and not d.serial_number and d.device_state == 1]
        if other_empty and device.com_port:
            port_suffix = device.com_port
    fname = device_config_path(device.serial_number, port_suffix)
    # 兜底：确保本设备配置文件绝不与其它已连接设备共用。
    # 即使SN冲突检测因连接时序漏判，也强制按端口/索引区分，
    # 避免两个设备并发写同一配置文件导致JSON损坏或崩溃。
    for d in list(all_devices.values()):
        if d is device:
            continue
        if d.device_state == 1 and d.config_file and \
                os.path.normpath(d.config_file) == os.path.normpath(fname):
            port = device.com_port or ("DEV%d" % device.index)
            fname = device_config_path(device.serial_number, port)
            break
    cfg = sys_config()
    loaded = False
    if os.path.exists(fname):
        try:
            with open(fname, "r", encoding="utf-8") as f:
                cfg.__dict__.update(json.load(f))
            loaded = True
        except Exception as e:
            print("读取设备配置失败：%s" % e)
    if not loaded:
        # 首次连接：以当前全局配置为模板（保留用户已有设置）
        if config_obj is not None:
            try:
                cfg.__dict__.update(copy.deepcopy(config_obj.__dict__))
            except Exception:
                pass
    device.config = cfg
    device.config_file = fname
    return cfg


def set_active_device_config(device):
    """把全局配置切换为指定设备的独立配置（渲染/UI 共用）"""
    global config_obj, config_file
    if device is not None and device.config is not None:
        config_obj = device.config
        config_file = device.config_file or config_file


def _ui_set_active():
    """UI操作前把全局config_obj锁定到UI当前选中设备。
    daemon渲染线程会在屏幕间切换全局config_obj，若UI直接读写全局，
    可能把设置写到其他屏幕（设置冲突）。所有UI设置回调开头调用本函数。"""
    global config_obj, config_file
    dev = get_current_device()
    if dev is not None and dev.config is not None:
        config_obj = dev.config
        config_file = dev.config_file or config_file


def set_auto_start(enable):
    """设置/取消开机自启动（写入HKCU Run注册表项）"""
    if not isWindows:
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        if enable:
            if getattr(sys, "frozen", False):
                cmd = '"%s"' % os.path.realpath(sys.executable)
            else:
                cmd = '"%s" "%s"' % (sys.executable, os.path.realpath(sys.argv[0]))
            winreg.SetValueEx(key, "MSU2_MINI", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "MSU2_MINI")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print("设置开机自启动失败：%s" % e)
        return False


def export_config():
    """导出配置到JSON文件"""
    parent = _ui_root
    path, _ = QFileDialog.getSaveFileName(parent, "导出配置", "", "配置文件 (*.json)")
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config_obj.__dict__, f, ensure_ascii=False, indent=2)
        insert_text_message("配置已导出到：%s" % path)
    except Exception as e:
        insert_text_message("导出配置失败：%s" % e)


def import_config():
    """从JSON文件导入配置"""
    parent = _ui_root
    path, _ = QFileDialog.getOpenFileName(parent, "导入配置", "", "配置文件 (*.json)")
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config_obj.__dict__.update(data)
        save_config(True)
        sync_page_combobox()
        sync_lcd_combobox()
        insert_text_message("配置已导入")
    except Exception as e:
        insert_text_message("导入配置失败：%s" % e)


def apply_command_line_args():
    """解析命令行参数：--page 页面名称/编号, --com 串口号"""
    global config_obj, preferred_com_port
    try:
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            a = args[i].lstrip('-').lower()
            if a == "page" and i + 1 < len(args):
                val = args[i + 1]
                i += 2
                for pid, pname in PAGE_ID.items():
                    if val == pname or val == str(pid):
                        config_obj.state_machine = pid
                        break
            elif a == "com" and i + 1 < len(args):
                preferred_com_port = args[i + 1].upper()
                i += 2
            else:
                i += 1
    except Exception:
        pass


def check_update():
    """检查GitHub Release最新版本（标准库urllib，后台线程调用）"""
    try:
        import urllib.request
        import json as _json
        req = urllib.request.Request(
            "https://api.github.com/repos/duma520/MSU2_MINI_V2/releases/latest",
            headers={"User-Agent": "MSU2_MINI"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        latest = str(data.get("tag_name", "")).lstrip("v").strip()
        if latest and latest != PROGRAM_VERSION:
            insert_text_message("发现新版本 v%s（当前 v%s），请到 GitHub 下载" % (latest, PROGRAM_VERSION))
            return latest
        else:
            insert_text_message("已是最新版本 v%s" % PROGRAM_VERSION)
            return None
    except Exception as e:
        print("检查更新失败：%s" % e)
        insert_text_message("检查更新失败：%s" % e)
        return None


def not_english(strings):
    for char in strings:
        if char > '\u00ff':
            return True
    return False


def get_parent(hwnd):
    global all_windows, desktop_hwnd
    if hwnd < 0:  # 显示器标识，直接返回桌面
        return desktop_hwnd
    for key, value in all_windows.items():
        if value[0] == hwnd:
            return value[1]
    return desktop_hwnd


def get_hwnd_desc(hwnd):
    global all_windows
    if isWindows:
        if not all_windows:  # 仅当窗口列表为空（如启动占位阶段）才枚举，避免反复枚举卡顿
            all_windows = get_all_windows()
    else:
        all_windows = {"桌面": (0, 0)}

    for key, value in all_windows.items():
        if value[0] == hwnd:
            return key
    return None


# ==================== 配色方案（色系库） ====================
# 每个方案是一组颜色（#rrggbb）。"经典方案"取网络流量默认配色（3色），
# 其余为常见色系配色，颜色数量按各色系常规色板给出。用户可新增自定义方案。
BUILTIN_COLOR_SCHEMES = {
    "经典方案": ["#ff8000", "#00ffff", "#eb8b8b"],
    "马卡龙配色方案": ["#ffb3ba", "#baffc9", "#bae1ff", "#ddbaff", "#ffd6ba", "#ffffba", "#d2d2d2", "#d2b4a0", "#ff9696", "#b4f0f0"],
    "莫兰迪配色方案": ["#b8a9a1", "#a3b18a", "#8da2b3", "#c0a9b0", "#d6c4b2", "#a7b0a1", "#b5a7c4", "#9db0a3"],
    "美拉德配色方案": ["#8a5a44", "#a9744f", "#c68e5b", "#d9a86c", "#b57a4f", "#7c4a2d", "#e0b88a", "#6b3f24"],
    "多巴胺配色方案": ["#ff4d4d", "#ff9900", "#ffdd00", "#33cc33", "#00ccff", "#9966ff", "#ff66cc", "#ff3366"],
    "赛博朋克配色方案": ["#ff00e0", "#00e5ff", "#7a00ff", "#ff0055", "#00ff9d", "#ffd700", "#00bfff", "#ff7a00"],
    "孟菲斯配色方案": ["#f14d4d", "#f4a142", "#ffd94a", "#4dc3d3", "#8a5fbf", "#2bb673", "#ff8fb3", "#f7f7f7"],
    "侘寂配色方案": ["#8d8d8d", "#a8a29e", "#b5a89a", "#9c8f84", "#6f6a63", "#c2b6a8", "#d6cfc5", "#7a746d"],
    "大地色系方案": ["#6b4f3a", "#8b5e3c", "#a0522d", "#b8860b", "#cd853f", "#d2b48c", "#8a6642", "#a67c52"],
    "奶油色系方案": ["#fdf5e6", "#fff8dc", "#f5f0dc", "#f7e7ce", "#efe2cf", "#f6ead8", "#f8f0e3", "#ead9c6"],
    "燕麦色系方案": ["#e6ddc6", "#d8cfba", "#cfc4ab", "#e0d7bf", "#c9bfa6", "#d9d0b8", "#efe8d6", "#b8af98"],
    "奶茶色系方案": ["#c9a06b", "#b98a5a", "#d4b483", "#a97c50", "#e0c79a", "#8f6b42", "#cbb283", "#f0e0c0"],
    "糖果色系方案": ["#ff7eb6", "#ffd166", "#7bdff2", "#b892ff", "#ff9b85", "#a0e7e5", "#f7d6e0", "#ffb347"],
    "冰淇淋色系方案": ["#ffd1dc", "#b5ead7", "#c7ceea", "#ffe6a7", "#a2d2ff", "#fbc4ab", "#d0f4de", "#f8f9fa"],
    "蒙德里安色系方案": ["#e33e3e", "#f6d030", "#1d5bb8", "#111111", "#f5f5f5", "#9a9a9a"],
    "洛可可色系方案": ["#f6c8d8", "#d4a5c6", "#e8d5b7", "#b5c9a8", "#a8b7c9", "#f2e3c6", "#c9a9a6", "#e3c6a8"],
    "印象派色系方案": ["#e0a0c0", "#7fa8d0", "#90b8a0", "#f0d070", "#c07070", "#8a9aa0", "#d0b0e0", "#a0c8e0"],
    "波普色系方案": ["#ff2b4d", "#ffcc00", "#00b8ff", "#00e000", "#ff7a00", "#ff00cc", "#00ffff", "#f0f0f0"],
    "包豪斯色系方案": ["#e63946", "#f4a300", "#2563eb", "#111111", "#f1f1f1", "#d4a017"],
    "浮世绘色系方案": ["#2a5f8f", "#c04a3a", "#4a9aa8", "#7a5a9a", "#3a7a5a", "#e8d5a0", "#9a4a4a", "#2a3a6a"],
    "森林色系方案": ["#2d5a27", "#3f7a33", "#4a8f3f", "#5aa04a", "#7ab55f", "#1f4a1f", "#8fbf6a", "#3a6b2f"],
    "草木色系方案": ["#66a83c", "#86c442", "#a8d84a", "#bfe060", "#4a8f2d", "#d2f07a", "#5cb85c", "#8fce4a"],
    "海洋色系方案": ["#0a3d62", "#145a8a", "#1a6f9e", "#2b8fbd", "#3aa5d9", "#67c0e8", "#98d7f0", "#0f4c75"],
    "湖泊色系方案": ["#2e6b8a", "#3a7f9e", "#4a94b0", "#5aa8c4", "#6ab8d0", "#8acfe0", "#a8ddef", "#1a5a7a"],
    "暖阳色系方案": ["#ffb347", "#ffcc5c", "#ffe28a", "#ffd700", "#ff9f1c", "#f7b267", "#ffc46b", "#e8972f"],
    "日落色系方案": ["#ff4e50", "#ff9a3d", "#ffc24b", "#ff6b6b", "#f9a03f", "#e56399", "#c41e3a", "#f77622"],
    "矿石色系方案": ["#4a4a4a", "#6a6a6a", "#8a8a8a", "#a8a8a8", "#5a5a7a", "#7a5a8a", "#8a6a5a", "#6a8a8a"],
    "宝石色系方案": ["#e74c3c", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6", "#1abc9c", "#e67e22", "#34495e"],
    "金属色系方案": ["#8a8a8a", "#b8b8b8", "#d4af37", "#c0c0c0", "#a67c00", "#6a6a6a", "#e0c060", "#9a9a9a"],
    "木材色系方案": ["#8b5a2b", "#a0522d", "#cd853f", "#d2b48c", "#b8860b", "#7c4a2d", "#c49a6c", "#966f4a"],
    "中国传统色系方案": ["#c3272b", "#0a5c8a", "#e6a23c", "#3a7a5a", "#9a4a5a", "#e8d5a0", "#7a5a4a", "#4a3a6a"],
    "和风色系方案": ["#9a3a3a", "#3a5a8a", "#e8d5a0", "#5a8a6a", "#b0a0c8", "#c83a3a", "#8a6a3a", "#3a8a8a"],
    "日式色系方案": ["#e0a0a0", "#c8d0e0", "#a0c0a0", "#f0e0c0", "#d0b0b0", "#b0b8c8", "#e8e0d0", "#c0a8a0"],
    "北欧色系方案": ["#f2f2f2", "#d9d9d9", "#a8a8a8", "#4a90c4", "#e0a800", "#7a8a9a", "#5a7a5a", "#c8c8c8"],
    "斯堪的纳维亚色系方案": ["#f7f7f2", "#e5e5dc", "#c0c8c0", "#8aa8c8", "#c8a060", "#7a8a8a", "#a0b0a0", "#d0d8d0"],
    "地中海色系方案": ["#3a8ab8", "#f2d8a0", "#e86a5a", "#5aa878", "#f0b860", "#8ab8d0", "#c8e0f0", "#f8e8c0"],
    "摩洛哥色系方案": ["#c0392b", "#e67e22", "#f1c40f", "#16a085", "#8e44ad", "#d35400", "#2c3e50", "#e74c3c"],
    "北非色系方案": ["#d4a017", "#8a5a3a", "#c8a24a", "#5a7a5a", "#b86a3a", "#e8c870", "#7a4a2a", "#3a5a3a"],
    "冷色系方案": ["#1e90ff", "#00bfff", "#00ffff", "#7b68ee", "#4682b4", "#5f9ea0", "#6495ed", "#00ced1"],
    "暖色系方案": ["#ff4500", "#ff8c00", "#ffd700", "#ff6347", "#ffa07a", "#ff7f50", "#ffdab9", "#ffa500"],
    "中性色系方案": ["#808080", "#a9a9a9", "#c0c0c0", "#d3d3d3", "#696969", "#b8b8b8", "#e0e0e0", "#8b8b8b"],
    "废土色系方案": ["#6a5a3a", "#8a7a5a", "#a89a7a", "#5a4a2a", "#7a6a4a", "#b0a080", "#4a3a1a", "#96865a"],
    "蒸汽波色系方案": ["#ff6ec7", "#7873f5", "#4adede", "#f706cf", "#2de2e6", "#ff00a0", "#6a5acd", "#ff9a00"],
    "Y2K色系方案": ["#c0c0c0", "#ff66cc", "#00ccff", "#ffcc00", "#ccff00", "#ff9966", "#99ccff", "#e0e0e0"],
    "克莱因蓝色系方案": ["#002fa7", "#1a4fd0", "#3a6ee8", "#5a8ef0", "#002080", "#7aa8f8", "#001a60", "#9ac0ff"],
    # ---- 现代风格补充 ----
    "哥特色系": ["#1a1a2e", "#16213e", "#0f3460", "#533483", "#e94560", "#2d1b3d", "#5a189a", "#10002b"],
    "暗黑色系": ["#000000", "#111111", "#222222", "#333333", "#444444", "#1a1a1a", "#0a0a0a", "#2b2b2b"],
    "极简色系": ["#ffffff", "#f0f0f0", "#d9d9d9", "#bfbfbf", "#999999", "#737373", "#4d4d4d", "#262626"],
    "波西米亚色系": ["#c86b3d", "#e6a24d", "#4a7c59", "#7a5a8a", "#e0b0a0", "#2d6a5f", "#d4a373", "#6a4a3a"],
    "复古色系": ["#8b5a2b", "#a0522d", "#6b4f3a", "#c0a080", "#7a4a2a", "#d2a679", "#5a3a1a", "#966f4a"],
    "做旧色系": ["#9a8c7a", "#b0a28c", "#8a7a66", "#c2b49e", "#7a6a52", "#a89880", "#6a5a44", "#d0c2ac"],
    "褪色色系": ["#c8bfb4", "#b5aca0", "#a3988c", "#d8d0c4", "#8f8578", "#c0b8ac", "#7a7166", "#e0d8cc"],
    "怀旧色系": ["#d4b896", "#c8a882", "#b8946a", "#e0c8a0", "#a8805a", "#f0dcc0", "#96704a", "#c09070"],
    "未来主义色系": ["#00e5ff", "#7a00ff", "#e0e0ff", "#00ff9d", "#ff00e0", "#1a1aff", "#c0c0ff", "#8a2be2"],
    "太空色系": ["#0b0b2a", "#1a1a4a", "#2b2b6a", "#4a4a8a", "#6a5a9a", "#1a0a3a", "#3a2b6a", "#0a1a4a"],
    "酸性色系": ["#ccff00", "#ff00cc", "#00ffcc", "#ffcc00", "#33ff00", "#ff0066", "#00ccff", "#ff6600"],
    "迷幻色系": ["#ff00ff", "#00ffff", "#ffff00", "#ff6600", "#00ff66", "#6600ff", "#ff0066", "#66ff00"],
    "霓虹色系": ["#39ff14", "#ff1493", "#ffff32", "#32cdff", "#ff6414", "#b44dff", "#00ff9d", "#ff2d78"],
    "荧光色系": ["#ccff00", "#00ff99", "#ff00cc", "#ffff00", "#00ffff", "#ff9900", "#99ff00", "#ff00ff"],
    "镭射色系": ["#00e5ff", "#ff00e5", "#ff00ff", "#00ffea", "#e5ff00", "#00bfff", "#ff2d95", "#7df9ff"],
    "日落渐变系": ["#ff512f", "#f09819", "#ff9966", "#ff5e62", "#fa709a", "#fee140", "#f83600", "#ffd86f"],
    # ---- 艺术流派补充 ----
    "巴洛克色系": ["#8a2b2b", "#c0a060", "#2b3a5a", "#6a2b3a", "#d4b86a", "#3a2b4a", "#a08050", "#5a2b2b"],
    "文艺复兴色系": ["#7a4a2b", "#b8860b", "#2b4a7a", "#8b4513", "#cd853f", "#5a3a1a", "#daa520", "#4a2b1a"],
    "浪漫主义色系": ["#c0392b", "#8e44ad", "#2e86c1", "#e67e22", "#f7d794", "#d35400", "#6c3483", "#a93226"],
    "新古典主义色系": ["#f5f5dc", "#d4c5a9", "#8a7a5a", "#c0b090", "#5a4a2a", "#e8e0c8", "#a89878", "#6a5a3a"],
    "野兽派色系": ["#ff4500", "#ffd700", "#00bfff", "#ff00ff", "#32cd32", "#ff1493", "#1e90ff", "#ffa500"],
    "立体派色系": ["#a0522d", "#708090", "#d2b48c", "#556b2f", "#cd5c5c", "#4a4a4a", "#daa520", "#5f9ea0"],
    "超现实主义色系": ["#00ffff", "#ff69b4", "#ffd700", "#8a2be2", "#00ff7f", "#ff4500", "#00bfff", "#ff00ff"],
    "抽象表现主义色系": ["#1a1a1a", "#e0e0e0", "#d4af37", "#8b0000", "#2f4f4f", "#ffd700", "#4a4a4a", "#c0c0c0"],
    "极简主义色系": ["#ffffff", "#000000", "#808080", "#c0c0c0", "#f0f0f0", "#2f2f2f", "#d0d0d0", "#4a4a4a"],
    "维也纳分离派色系": ["#d4af37", "#111111", "#e8e0c8", "#8b0000", "#f5f5f5", "#b8860b", "#2f2f2f", "#c8a24a"],
    "新艺术运动色系": ["#4a7a5a", "#8a4a3a", "#c0a060", "#2b6a8a", "#d4a06a", "#6a3a2b", "#a8c0b0", "#8a6a3a"],
    "装饰艺术色系": ["#111111", "#d4af37", "#8b0000", "#f5f5dc", "#2f4f4f", "#c0c0c0", "#b8860b", "#3a3a3a"],
    "荷兰画派色系": ["#3a2b1a", "#8b4513", "#a0522d", "#d2b48c", "#2b2b1a", "#6b4f3a", "#c4a882", "#4a3a2a"],
    "威尼斯画派色系": ["#7a1a1a", "#c0a060", "#1a3a6a", "#8a2b3a", "#d4b86a", "#2b4a8a", "#b06040", "#4a6a9a"],
    # ---- 自然补充 ----
    "沙漠色系": ["#c2a060", "#d4b470", "#a88048", "#e8d0a0", "#b89058", "#f0e0b0", "#96703a", "#d0b880"],
    "泥土色系": ["#5a3a1a", "#6b4a2a", "#7a5a3a", "#8a6a4a", "#4a2a10", "#9a7a58", "#3a2a10", "#6a4a28"],
    "岩石色系": ["#6a6a6a", "#7a7a7a", "#8a8a8a", "#5a5a5a", "#9a9a9a", "#4a4a4a", "#a8a8a8", "#3a3a3a"],
    "苔藓色系": ["#5a7a3a", "#6a8a4a", "#4a6a2a", "#7a9a5a", "#8aa86a", "#3a5a1a", "#9ab87a", "#2b4a10"],
    "冰雪色系": ["#f0f8ff", "#e0f0ff", "#cfe8ff", "#e6f7ff", "#b8dcff", "#d0f0ff", "#f8fcff", "#a8d0f0"],
    "云雾色系": ["#e0e0e0", "#d0d0d0", "#c0c0c0", "#e8e8e8", "#b0b0b0", "#f0f0f0", "#a8a8a8", "#d8d8d8"],
    "天空色系": ["#87ceeb", "#87cefa", "#00bfff", "#4682b4", "#5f9ea0", "#1e90ff", "#a0c8f0", "#7ec8e3"],
    "星空色系": ["#0a0a2a", "#1a1a4a", "#2b2b6a", "#3a3a8a", "#4a4a9a", "#6a5a9a", "#2a1a4a", "#1a0a3a"],
    "极光色系": ["#00ff87", "#60efff", "#00ff5e", "#7dffab", "#00f5d4", "#00c9ff", "#b9fbc0", "#00e5ff"],
    "珊瑚色系": ["#ff7f50", "#ff6347", "#ff6f61", "#ff8c69", "#e07856", "#ffa07a", "#ff7f7f", "#ff937e"],
    "贝壳色系": ["#fff5ee", "#ffe4e1", "#ffdab9", "#f5deb3", "#ffeef0", "#fff0f5", "#ffe8d6", "#f8f8ff"],
    "珍珠色系": ["#f5f5f5", "#e8e8e8", "#f8f8f0", "#dcdcdc", "#f0f0e8", "#e0e0d8", "#ffffff", "#c8c8c0"],
    "琥珀色系": ["#ffbf00", "#ff8c00", "#e6a800", "#c8820a", "#f0b400", "#b8860b", "#d4a017", "#ffa700"],
    "玛瑙色系": ["#8b0000", "#a0522d", "#cd853f", "#d2691e", "#b87333", "#8b4513", "#c85a17", "#7a3b1a"],
    "翡翠色系": ["#50c878", "#2e8b57", "#3cb371", "#00a86b", "#1fa35c", "#009b6a", "#32cd32", "#00c957"],
    "孔雀色系": ["#00a4b8", "#00b5ad", "#00808a", "#1f9a8f", "#005c69", "#008a8a", "#00c4b4", "#006a6a"],
    "蝴蝶色系": ["#ff69b4", "#ffa500", "#8a2be2", "#ffd700", "#00bfff", "#ff1493", "#7a5a00", "#ff8c00"],
    "玫瑰色系": ["#ff007f", "#ff1493", "#e0115f", "#ff6f91", "#c21e56", "#ff4d6d", "#d62598", "#ff758f"],
    "薰衣草色系": ["#b57edc", "#967bb6", "#c8a2c8", "#a78bc0", "#e6e6fa", "#8a5a9a", "#d8b2d1", "#9a6bae"],
    "郁金香色系": ["#ff6b6b", "#ff9a3d", "#ffd166", "#ff8fa3", "#ff4d6d", "#f9a03f", "#e56399", "#ffb347"],
    "樱桃色系": ["#de3163", "#d2042d", "#ff073a", "#9b111e", "#e30b5c", "#ff004f", "#c40233", "#ff2a6d"],
    "柠檬色系": ["#fff700", "#faff00", "#ffe600", "#fff44f", "#eef76c", "#f7e600", "#fff200", "#e8f110"],
    "葡萄色系": ["#6b2d5c", "#7a3b6a", "#8848a0", "#8e4585", "#5e2a5e", "#9a4a8a", "#6a1a4a", "#4a1a3a"],
    "肉桂色系": ["#8b4513", "#a0522d", "#7a4a2a", "#b06030", "#cd853f", "#6a3a1a", "#d2691e", "#5a2d0c"],
    "姜黄色系": ["#ffbf00", "#e6a800", "#d4a017", "#f0a400", "#c8820a", "#ffa700", "#b8860b", "#e8a000"],
    "藏红色系": ["#e34234", "#c02a2a", "#b7410e", "#d03030", "#a02a1a", "#f05a3a", "#8a2010", "#e05030"],
    "小麦色系": ["#f5deb3", "#f0d8a8", "#e8c890", "#dfc090", "#f0e0b0", "#d4b070", "#e8d0a0", "#c8a050"],
    "大麦色系": ["#e0d0a0", "#d0c088", "#c0b070", "#d8c898", "#e8d8a8", "#b0a060", "#c8b888", "#a89858"],
    "米色系": ["#f5f5dc", "#faf0e6", "#f0e6d8", "#e8dcc8", "#f8f4e0", "#e0d4c0", "#ede8d6", "#d8ccb8"],
    # ---- 地域文化补充 ----
    "印度色系": ["#ff9933", "#138808", "#d32f2f", "#ffc400", "#b8860b", "#e64a19", "#ff7043", "#7a3b2e"],
    "东南亚色系": ["#e8a030", "#2e8b57", "#c0392b", "#f1c40f", "#8e44ad", "#16a085", "#e67e22", "#d35400"],
    "非洲大地色系": ["#8b5a2b", "#a0522d", "#cd853f", "#d2b48c", "#b8860b", "#6b4f3a", "#c4a882", "#966f4a"],
    "南美热带色系": ["#16a085", "#f1c40f", "#e74c3c", "#2ecc71", "#3498db", "#e67e22", "#9b59b6", "#1abc9c"],
    "墨西哥色系": ["#c0392b", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#e74c3c", "#8e44ad", "#d35400"],
    "希腊色系": ["#1a5aa8", "#f5f5f5", "#d4c5a9", "#e8e0c8", "#2f4f6f", "#c0b090", "#7a8a9a", "#e0d8c0"],
    "托斯卡纳色系": ["#8b5a2b", "#a0522d", "#c0a060", "#cd853f", "#d2b48c", "#7a4a2a", "#b8860b", "#6a3a1a"],
    "普罗旺斯色系": ["#967bb6", "#c8a2c8", "#b5a8c8", "#d8c8e0", "#8a5a9a", "#e8d8f0", "#a87ab8", "#c0a8d8"],
    "苏格兰色系": ["#1a2b5a", "#2b3a6a", "#3a5a8a", "#4a6a9a", "#2b2b6a", "#1a1a4a", "#5a7a9a", "#3a4a7a"],
    "爱尔兰色系": ["#169b62", "#2e8b57", "#3cb371", "#ff8833", "#228b22", "#00a86b", "#c0c040", "#32cd32"],
    "北欧维京色系": ["#2b4a6a", "#4a2b2b", "#6a5a2b", "#3a2b4a", "#1a2b3a", "#5a3a2b", "#2b6a4a", "#4a3a2b"],
    "蒙古色系": ["#c03a2b", "#2b4a6a", "#d4a017", "#4a2b1a", "#6a3a2b", "#8a5a2b", "#2b2b4a", "#b06030"],
    "藏族色系": ["#c3272b", "#f0c040", "#2b5a8a", "#e8e0c0", "#d4a017", "#8a1a1a", "#3a2b4a", "#c0a060"],
    "傣族色系": ["#e8a030", "#2e8b57", "#c0392b", "#f1c40f", "#16a085", "#e67e22", "#8e44ad", "#d35400"],
    "彝族色系": ["#a03030", "#2b4a8a", "#d4a017", "#6a2b2b", "#3a6a2b", "#8a2b5a", "#c06030", "#4a2b6a"],
    # ---- 色彩理论 ----
    "无彩色系": ["#ffffff", "#e0e0e0", "#c0c0c0", "#a0a0a0", "#808080", "#606060", "#404040", "#202020", "#000000"],
    "有彩色系": ["#ff0000", "#ff8000", "#ffff00", "#00ff00", "#00ffff", "#0080ff", "#0000ff", "#ff00ff"],
    "原色系": ["#ff0000", "#ffff00", "#0000ff"],
    "间色系": ["#ff8000", "#00ff00", "#8000ff"],
    "复色系": ["#a05030", "#3a8a5a", "#6a4a9a", "#8a6a3a", "#4a7a8a", "#a03a6a"],
    "互补色系": ["#ff0000", "#00ffff", "#00ff00", "#ff00ff", "#0000ff", "#ffff00"],
    "邻近色系": ["#ff0000", "#ff4000", "#ff8000", "#ffc000", "#ffff00"],
    "单色系": ["#1a5aa8", "#3a7ac8", "#5a9ae0", "#7ab8f0", "#9ad8ff", "#0a4a98", "#2a6ab8", "#4a8ad8"],
    "同类色系": ["#ffd0d0", "#ffb0b0", "#ff9090", "#ff7070", "#ff5050", "#ff3030", "#ff1010", "#f00000"],
    "对比色系": ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"],
    "高明度色系": ["#ffffff", "#f0f0f0", "#e0e0e0", "#d0d0d0", "#c0c0c0", "#b0b0b0", "#a0a0a0", "#909090"],
    "中明度色系": ["#808080", "#767676", "#6a6a6a", "#606060", "#585858", "#4e4e4e", "#484848", "#404040"],
    "低明度色系": ["#3a3a3a", "#303030", "#2a2a2a", "#202020", "#1a1a1a", "#101010", "#0a0a0a", "#000000"],
    "高纯度色系": ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff"],
    "中纯度色系": ["#d08060", "#60b080", "#6080d0", "#d0d060", "#d060d0", "#60d0d0"],
    "低纯度色系": ["#a09890", "#90a098", "#9090a0", "#a0a090", "#a090a0", "#90a0a0"],
    "CIE色系": ["#ff0000", "#00ff00", "#0000ff", "#ffffff", "#000000", "#ffff00", "#ff00ff", "#00ffff"],
    "孟塞尔色系": ["#c83828", "#3a9a3a", "#2b5a9a", "#e8b838", "#8a5a8a", "#6a9a6a", "#d86828", "#4a6a8a"],
    "奥斯特瓦尔德色系": ["#c03030", "#c09030", "#c0c030", "#30c030", "#30c090", "#30c0c0", "#3090c0", "#3030c0"],
    "NCS自然色彩体系": ["#c0313a", "#d8a030", "#2b8a6a", "#2b6a8a", "#5a5a8a", "#8a2b5a", "#8a6a2b", "#3a8a5a"],
    "PCCS实用配色体系": ["#e05a5a", "#e0a05a", "#e0d05a", "#8ac05a", "#5ac08a", "#5ab0d0", "#5a6ad0", "#a05ad0"],
    "RAL色系(德国劳尔)": ["#d9381e", "#e3a30a", "#4c8d3f", "#1a509a", "#6a2b5a", "#b8a030", "#3a3a3a", "#c8c8c8"],
    "潘通色系(PANTONE)": ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4", "#46f0f0", "#f032e6"],
    "DIC色系(日本)": ["#d94f3d", "#e8a03a", "#5a8a4a", "#2b5a9a", "#6a2b8a", "#b86a3a", "#4a9a8a", "#8a3a6a"],
    "CMYK色系": ["#00ffff", "#ff00ff", "#ffff00", "#ff0000", "#00ff00", "#0000ff", "#000000", "#808080"],
    "RGB色系": ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#00ffff", "#ff00ff", "#ffffff", "#000000"],
    "HSB色系": ["#ff0000", "#ff8000", "#ffff00", "#80ff00", "#00ff00", "#00ff80", "#00ffff", "#0080ff"],
    "HSL色系": ["#ff0000", "#ff8000", "#ffff00", "#80ff00", "#00ff00", "#00ff80", "#00ffff", "#0080ff"],
    "LAB色系": ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#00ffff", "#ff00ff", "#ffffff", "#808080"],
    "XYZ色系": ["#ff0000", "#00ff00", "#0000ff", "#ffffff", "#000000", "#ff00ff", "#00ffff", "#ffff00"],
    "YUV色系": ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#00ffff", "#ff00ff", "#ffffff", "#808080"],
    # ---- 风格补充 ----
    "淡粉色系": ["#ffd1dc", "#ffc0cb", "#f8c8dc", "#fddde6", "#fadadd", "#ffd9e8", "#f7c8d0", "#fce4ec"],
    "明亮色系": ["#ff5555", "#ffaa00", "#ffee00", "#55dd55", "#55ccff", "#cc55ff", "#ff66aa", "#44dddd"],
    "鲜艳色系": ["#ff0000", "#ff8800", "#ffff00", "#00ff00", "#00ddff", "#0088ff", "#8800ff", "#ff00aa"],
    "浓烈色系": ["#8b0000", "#a0522d", "#b8860b", "#006400", "#00008b", "#4b0082", "#8b008b", "#a52a2a"],
    "深重色系": ["#2f1a1a", "#2f2a1a", "#2f2f1a", "#1a2f1a", "#1a2f2f", "#1a1a2f", "#2a1a2f", "#3a2f1a"],
    "黑灰色系": ["#000000", "#1a1a1a", "#2b2b2b", "#3a3a3a", "#4a4a4a", "#5a5a5a", "#6a6a6a", "#7a7a7a"],
    "柔和色系": ["#ffd0d0", "#d0ffd0", "#d0d0ff", "#ffffd0", "#ffd0ff", "#d0ffff", "#f0e0d0", "#e0e0f0"],
    "雅致色系": ["#a8a090", "#b8a890", "#c8b8a0", "#8a8070", "#d8c8b0", "#988878", "#e0d8c8", "#b0a898"],
    "清爽色系": ["#b8e8f0", "#a8e0d0", "#c0f0e0", "#d0f0ff", "#a0e8f8", "#c8f0f8", "#90e0f0", "#e0f8ff"],
    "清凉色系": ["#7ec8e3", "#4a90c4", "#1e90ff", "#00bfff", "#5f9ea0", "#2e86c1", "#48a3d0", "#6ab8e8"],
    "温暖色系": ["#ff6a3d", "#ff9a3d", "#ffc24b", "#f7b267", "#ff7a2a", "#e8972f", "#ffb347", "#f77622"],
    "古典色系": ["#6b4f3a", "#8b5a2b", "#a0522d", "#b8860b", "#cd853f", "#d2b48c", "#8a6642", "#a67c52"],
    "自然色系": ["#5a7a3a", "#6a8a4a", "#7a9a5a", "#3a6a2b", "#8a5a3a", "#4a7a5a", "#a87a4a", "#3a5a2b"],
    "华丽色系": ["#b8860b", "#d4af37", "#8b0000", "#800080", "#c71585", "#daa520", "#2e8b57", "#dc143c"],
    "浪漫色系": ["#ff69b4", "#ff1493", "#ff6f91", "#ff8fa3", "#ff4d6d", "#e0a0b0", "#ffb3ba", "#d62598"],
    "跃动色系": ["#ff4500", "#ffcc00", "#00cc00", "#00ccff", "#ff00cc", "#cc00ff", "#ff9900", "#33cc99"],
    "沉稳色系": ["#2f4f4f", "#3a5a6a", "#4a6a7a", "#5a7a8a", "#2b3a4a", "#6a8a9a", "#1a2a3a", "#7a9aaa"],
    "宁静色系": ["#b8d4e8", "#a8c8d8", "#c8e0f0", "#d0e8f0", "#98c0d8", "#e0f0f8", "#88b8d0", "#f0f8ff"],
    "优雅色系": ["#7a6a8a", "#8a7a9a", "#9a8aaa", "#6a5a7a", "#aa9aba", "#5a4a6a", "#b8a8c8", "#4a3a5a"],
    "知性色系": ["#3a4a6a", "#4a5a7a", "#5a6a8a", "#2b3a5a", "#6a7a9a", "#1a2b4a", "#7a8aaa", "#0a1a3a"],
    "活力色系": ["#ff3b30", "#ff9500", "#ffcc00", "#4cd964", "#5ac8fa", "#007aff", "#af52de", "#ff2d55"],
    "青春色系": ["#ff6b9d", "#ff9a76", "#ffd93d", "#6bcb77", "#4d96ff", "#b983ff", "#ff8fab", "#8ecae6"],
    "成熟色系": ["#8b5a2b", "#a0522d", "#b8860b", "#cd853f", "#6b4f3a", "#d2b48c", "#8a6642", "#a67c52"],
    "摩登色系": ["#111111", "#d4af37", "#2b2b2b", "#c0c0c0", "#4a4a4a", "#f5f5f5", "#3a3a3a", "#a8a8a8"],
    "乡村色系": ["#7a4a2a", "#8b5a2b", "#a0522d", "#cd853f", "#d2b48c", "#6b4f3a", "#c4a882", "#966f4a"],
    "田园色系": ["#8bc34a", "#66bb6a", "#42a5f5", "#ffca28", "#ff7043", "#aed581", "#4db6ac", "#ffab91"],
    "海滨色系": ["#a8d8ea", "#87ceeb", "#00bfff", "#5f9ea0", "#2e86c1", "#48c9b0", "#66ccff", "#b2dfdb"],
    "山野色系": ["#2d5a27", "#3f7a33", "#4a8f3f", "#5aa04a", "#7ab55f", "#8fbf6a", "#6a4a2a", "#a08050"],
    # ---- 传统国色 ----
    "赤色系": ["#d32f2f", "#e53935", "#f44336", "#ef5350", "#c62828", "#b71c1c", "#e53935", "#fce4ec"],
    "黄色系": ["#ffd600", "#ffeb3b", "#fdd835", "#fbc02d", "#f9a825", "#f57f17", "#fff59d", "#ffee58"],
    "青色系": ["#00bcd4", "#00acc1", "#0097a7", "#00838f", "#006064", "#4dd0e1", "#80deea", "#b2ebf2"],
    "白色系": ["#ffffff", "#fafafa", "#f5f5f5", "#f0f0f0", "#eeeeee", "#e0e0e0", "#f8f8f8", "#eaeaea"],
    "黑色系": ["#000000", "#111111", "#222222", "#333333", "#1a1a1a", "#2b2b2b", "#0a0a0a", "#404040"],
    "朱红色系": ["#e0342c", "#c3272b", "#d4322c", "#f03a2e", "#a02020", "#b3261e", "#e6453d", "#f05545"],
    "胭脂色系": ["#d5326d", "#c2185b", "#ad1457", "#880e4f", "#e91e63", "#ec407a", "#f06292", "#c6286e"],
    "绯红色系": ["#b22222", "#dc143c", "#ff2400", "#e30b5c", "#c11b17", "#d21f3c", "#ff0038", "#a60000"],
    "绛红色系": ["#722f37", "#5c0a1a", "#6a0f1a", "#8a1a1a", "#4a0a0a", "#7a1a2a", "#9a2a2a", "#3a0a0a"],
    "大红系": ["#f44336", "#e53935", "#d32f2f", "#c62828", "#b71c1c", "#ef5350", "#ff1744", "#e60000"],
    "丹色系": ["#e34234", "#d94f3d", "#c0392b", "#e8503a", "#b03a2b", "#f05a40", "#a52a2a", "#cc4a3a"],
    "橙色系": ["#ff9800", "#fb8c00", "#f57c00", "#ef6c00", "#e65100", "#ffa726", "#ffb74d", "#ffe0b2"],
    "鹅黄色系": ["#fff1a8", "#ffe066", "#ffd93d", "#ffd600", "#fbc02d", "#ffe94a", "#ffe27a", "#f9c74f"],
    "柳黄色系": ["#c8d878", "#b8c858", "#a8b838", "#d0e090", "#98a828", "#e0e8a0", "#889818", "#b0c048"],
    "杏黄色系": ["#f0b860", "#e8a850", "#e09a3a", "#f8c878", "#d88a2a", "#ffcc80", "#c87a1a", "#eab879"],
    "金黄色系": ["#ffd700", "#ffc400", "#ffb300", "#ffa000", "#ff8f00", "#ff6f00", "#ffca28", "#ffab00"],
    "香槟色系": ["#f7e7ce", "#f5deb3", "#eee8aa", "#f0e0c0", "#ead8b8", "#f8f0d0", "#e0d0b0", "#f2e6c8"],
    "苍黄色系": ["#f0e0a0", "#e8d890", "#e0d080", "#f5e8b0", "#d8c870", "#f8f0c0", "#d0c060", "#e8dc98"],
    "草绿色系": ["#7cb342", "#689f38", "#558b2f", "#33691e", "#8bc34a", "#9ccc65", "#aed581", "#c5e1a5"],
    "竹青色系": ["#789262", "#8aa868", "#5a7a4a", "#98b878", "#4a6a3a", "#a8c888", "#3a5a2b", "#88a858"],
    "松绿色系": ["#00563f", "#00695c", "#00695c", "#004d40", "#00796b", "#00897b", "#1b5e20", "#2e7d32"],
    "柏绿色系": ["#005b4f", "#00695c", "#00766d", "#1a6a5a", "#2b7a6a", "#0a5a4a", "#3a8a7a", "#00504a"],
    "柳绿色系": ["#a8b878", "#98a868", "#88a858", "#b8c888", "#789848", "#c8d898", "#688838", "#a0b068"],
    "黛青色系": ["#2b4a4a", "#3a5a5a", "#4a6a6a", "#1a3a3a", "#5a7a7a", "#0a2a2a", "#6a8a8a", "#2b3a3a"],
    "黛蓝色系": ["#1a3a5a", "#2b4a6a", "#3a5a7a", "#0a2a4a", "#4a6a8a", "#1a2b4a", "#5a7a9a", "#2b3a5a"],
    "天青色系": ["#4fa3a0", "#5fb0ac", "#6fbdb8", "#3a8f8c", "#80cac4", "#2a7d7a", "#8fd5d0", "#5aa8a5"],
    "月白色系": ["#f0f4f4", "#e8eeef", "#dce8ea", "#f5f8f8", "#d0e0e4", "#fafcfc", "#c8d8dc", "#e0eaec"],
    "皎月色系": ["#eef2f8", "#e0e8f2", "#d0dcea", "#f4f6fa", "#c0d0e2", "#f8fafc", "#b8c8dc", "#e4eaf2"],
    "霁蓝色系": ["#5a7a9a", "#6a8aaa", "#7a9aba", "#4a6a8a", "#8aaaaa", "#3a5a7a", "#9abaca", "#2b4a6a"],
    "藏蓝色系": ["#0a1a3a", "#0f2b52", "#143a63", "#1a4a7a", "#2b5a8a", "#123b5a", "#1d4e8f", "#082a4a"],
    "宝蓝色系": ["#1e3a8a", "#2b4a9a", "#3a5aaa", "#4a6aba", "#2563eb", "#3b82f6", "#1d4ed8", "#1e40af"],
    "绀青色系": ["#2b4a5a", "#3a5a6a", "#4a6a7a", "#1a3a4a", "#5a7a8a", "#0a2a3a", "#6a8a9a", "#2b3a4a"],
    "藕荷色系": ["#d8b8c8", "#c8a8b8", "#e0c8d0", "#b898a8", "#f0dce0", "#a88898", "#e8d0d8", "#c0a0b0"],
    "丁香色系": ["#b5a8d8", "#c0b8e0", "#a898c8", "#d0c8e8", "#9888b8", "#e0d8f0", "#8878a8", "#c8c0e0"],
    "紫棠色系": ["#4a2b5a", "#5a3a6a", "#6a4a7a", "#3a1a4a", "#7a5a8a", "#2a0a3a", "#8a6a9a", "#4a2b6a"],
    "灰色系(百草霜)": ["#6a6a6a", "#7a7a7a", "#8a8a8a", "#5a5a5a", "#9a9a9a", "#4a4a4a", "#aaa8a8", "#3a3a3a"],
    "褐色系(茶褐/秋香)": ["#5a3a1a", "#6b4f3a", "#7a4a2a", "#8b5a2b", "#a0522d", "#96744a", "#6a4422", "#8a6a3a"],
    "墨色系": ["#1a1a1a", "#0a0a0a", "#2b2b2b", "#101010", "#333333", "#000000", "#252525", "#1e1e1e"],
    "玄色系": ["#0a0a0a", "#111111", "#1a1a1a", "#222222", "#2b2b2b", "#050505", "#151515", "#202020"],
    "缁色系": ["#3a2a2a", "#4a3a3a", "#2b1a1a", "#5a4a4a", "#1a0a0a", "#6a5a5a", "#352828", "#0a0a0a"],
    # ---- 色相环 ----
    "红色系": ["#ff0000", "#e60000", "#cc0000", "#b30000", "#ff3333", "#ff4d4d", "#ff6666", "#990000"],
    "橙红色系": ["#ff4500", "#ff3d00", "#ff3300", "#ff5722", "#e64a19", "#d84315", "#bf360c", "#ff6e40"],
    "橙黄色系": ["#ffa500", "#ff9500", "#ff8c00", "#ff9f1c", "#f7b267", "#e8982f", "#ffb347", "#ffc46b"],
    "黄绿色系": ["#adff2f", "#a4de02", "#9acd32", "#7fff00", "#b8e800", "#c0eb00", "#cddc39", "#d0e050"],
    "绿色系": ["#00ff00", "#00cc00", "#009900", "#00e500", "#32cd32", "#3cb371", "#2e8b57", "#00aa00"],
    "蓝绿色系": ["#00ffcc", "#00e5cc", "#00ccb3", "#00b3a0", "#20b2aa", "#48d1cc", "#66cdaa", "#00a8a8"],
    "蓝色系": ["#0000ff", "#0000e0", "#0000cc", "#1e90ff", "#4169e1", "#4682b4", "#6495ed", "#0000aa"],
    "蓝紫色系": ["#4b0082", "#5a009a", "#6a00b0", "#7a00c8", "#8a2be2", "#9370db", "#7b68ee", "#6a5acd"],
    "紫色系": ["#800080", "#9a009a", "#b000b0", "#c800c8", "#a020f0", "#ba55d3", "#da70d6", "#ee82ee"],
    "紫红色系": ["#c71585", "#d02090", "#da70d6", "#e0449a", "#ff1493", "#ff69b4", "#f06292", "#c2185b"],
    "粉红色系": ["#ffc0cb", "#ffb6c1", "#ff99aa", "#ff8fa3", "#ff6f91", "#ff4d6d", "#ffaab8", "#f7a8b8"],
    "棕红色系": ["#8b4513", "#a0522d", "#b7410e", "#cd5c5c", "#a52a2a", "#c0392b", "#b96a3a", "#9a3b1a"],
    "棕黄色系": ["#b8860b", "#cd853f", "#d2b48c", "#daa520", "#c8a24a", "#b8904a", "#d4a017", "#c0964a"],
    "橄榄绿色系": ["#556b2f", "#6b8e23", "#808000", "#708238", "#8a8a3a", "#9a9a3a", "#6a6a2a", "#7a8a3a"],
    "灰蓝色系": ["#5f7a8a", "#6a8a9a", "#7a9aaa", "#4a6a7a", "#8aaaba", "#3a5a6a", "#9abaca", "#2b4a5a"],
    "灰紫色系": ["#6a5a7a", "#7a6a8a", "#8a7a9a", "#5a4a6a", "#9a8aaa", "#4a3a5a", "#aa9aba", "#3a2b4a"],
    "米黄色系": ["#f5deb3", "#f0d8a8", "#ead8b8", "#f8e8c0", "#e0d0a8", "#f0e0c0", "#e8d8b0", "#dcc8a0"],
    "奶白色系": ["#fdfbf7", "#faf6ef", "#f8f4ec", "#f6f2ea", "#f4efe6", "#f2ede2", "#faf5ee", "#f5f0e6"],
    # ---- 质感 ----
    "象牙色系": ["#fffff0", "#fef6e3", "#fdf5e6", "#faf0e6", "#fff8dc", "#fdf6ec", "#fbf5e0", "#f8efd4"],
    "裸色系": ["#e0c0a8", "#d8b090", "#e8c8b0", "#d0a888", "#f0d8c0", "#c89878", "#e8d0b8", "#d8b898"],
    "肤色系": ["#f1c27d", "#f0c8a0", "#e8b890", "#f8d8b0", "#e0a880", "#dda07a", "#f4d0a8", "#ecc090"],
    "陶土色系": ["#cc7a4a", "#b86a3a", "#c87a4a", "#a85a2a", "#d88a5a", "#9a4a1a", "#e09a6a", "#b06030"],
    "水泥色系": ["#a8a8a8", "#9a9a9a", "#b0b0b0", "#8a8a8a", "#c0c0c0", "#7a7a7a", "#b8b8b8", "#9e9e9e"],
    "混凝土色系": ["#8a8a8a", "#7a7a7a", "#969696", "#6a6a6a", "#a0a0a0", "#5a5a5a", "#909090", "#4a4a4a"],
    "沥青色系": ["#2b2b2b", "#202020", "#333333", "#1a1a1a", "#3a3a3a", "#252525", "#2f2f2f", "#151515"],
    "石墨色系": ["#3a3a3a", "#4a4a4a", "#2b2b2b", "#5a5a5a", "#202020", "#6a6a6a", "#353535", "#1a1a1a"],
    "碳灰色系": ["#2f2f2f", "#3a3a3a", "#262626", "#444444", "#1e1e1e", "#4e4e4e", "#353535", "#111111"],
    "烟灰色系": ["#8a8f98", "#7a7f88", "#9a9fa8", "#6a6f78", "#aaaeb8", "#5a5f68", "#b8bcc8", "#4a4f58"],
    "银灰色系": ["#c0c0c0", "#a8a8a8", "#b8b8b8", "#d0d0d0", "#989898", "#e0e0e0", "#888888", "#c8c8c8"],
    "锡色系": ["#a8a8a8", "#989898", "#b8b8b8", "#888888", "#c0c0c0", "#787878", "#b0b0b0", "#6a6a6a"],
    "铅色系": ["#4a4a5a", "#5a5a6a", "#3a3a4a", "#6a6a7a", "#2a2a3a", "#7a7a8a", "#50505f", "#1a1a2a"],
    "铁锈色系": ["#8b4513", "#a0522d", "#b7410e", "#c0392b", "#9a3b1a", "#b87333", "#a5541a", "#8a3a1a"],
    "铜绿色系": ["#3a8a7a", "#2e8b57", "#5a9a8a", "#1a7a6a", "#6aaa9a", "#0a6a5a", "#7abaaa", "#2b7a6a"],
    "青铜色系": ["#5a6a3a", "#6a7a4a", "#7a8a5a", "#4a5a2a", "#8a9a6a", "#3a4a1a", "#9aaa7a", "#2b3a1a"],
    "古铜色系": ["#6b4f3a", "#8b5a2b", "#a0522d", "#b87333", "#966f4a", "#7a4a2a", "#c0812a", "#5a3a1a"],
    "黄铜色系": ["#b5a642", "#c0b050", "#a89838", "#d0c060", "#98882a", "#e0d070", "#88781a", "#c8b858"],
    "玫瑰金色系": ["#b76e79", "#c0808a", "#a05a66", "#d098a0", "#904a58", "#e0aab0", "#803a4a", "#c8909a"],
    "白金系": ["#e8e8e8", "#f0f0f0", "#dcdcdc", "#e0e0e8", "#d0d0d8", "#f5f5f5", "#c8c8d0", "#eaeaea"],
    "铂金色系": ["#e5e4e2", "#e8e8e8", "#dcdcd8", "#f0f0f0", "#d0d0cc", "#f8f8f8", "#c8c8c4", "#e0e0dc"],
    # ---- 分类汇总 ----
    "花卉色系": ["#ff6f91", "#ffb3ba", "#ff9a76", "#c8a2c8", "#ffd166", "#ff8fa3", "#ff4d6d", "#ffd1dc"],
    "果实色系": ["#de3163", "#ffa500", "#6b2d5c", "#ffbf00", "#ff7f50", "#8e4585", "#ff8c00", "#c8a24a"],
    "香料色系": ["#8b4513", "#ffbf00", "#e34234", "#cd853f", "#6a3a1a", "#ffa700", "#d2691e", "#b7410e"],
    "谷物色系": ["#f5deb3", "#e8c890", "#d4b070", "#f0e0b0", "#dfc090", "#c8a050", "#e8d0a0", "#b89058"],
}


def get_all_color_schemes(config_obj=None):
    """返回全部配色方案（内置 + 用户自定义），用户自定义可覆盖同名内置"""
    schemes = dict(BUILTIN_COLOR_SCHEMES)
    try:
        custom = getattr(config_obj, "custom_color_schemes", None) or {}
        schemes.update(custom)
    except Exception:
        pass
    return schemes


def parse_color_list(text):
    """把用户输入的逗号/换行分隔颜色文本解析为 #rrggbb 列表，非法项忽略"""
    out = []
    for part in str(text).replace("\n", ",").split(","):
        part = part.strip().lstrip("#")
        if len(part) == 6:
            try:
                int(part, 16)
                out.append("#" + part.lower())
            except Exception:
                pass
    return out


class sys_config(object):
    def __init__(self):
        self.text_color_r = 255  # RGB颜色
        self.text_color_g = 0
        self.text_color_b = 255
        self.state_machine = SCREEN_PAGE_ID  # 页面状态，默认屏幕镜像
        self.lcd_change = 0  # LCD显示方向
        self.photo_interval_var = 0.1  # 动图间隔，小数部分，实际间隔为 photo_interval_var + second_times
        self.second_times = 0  # 动图间隔，整数部分。设备超过5秒收不到消息就会断开连接，所以每隔1秒发送一次消息
        self.camera_var = ""  # 相机编号
        self.select_window_hwnd = 0
        self.fps_var = 5
        self.shrink_type = 1
        self.anti_burn = 1  # 防烧屏：0=关闭, 1=开启
        self.preview_enabled = 1  # 实时预览：0=关闭, 1=开启
        self.custom_selected_names = [""] * 2
        self.custom_selected_displayname = [""] * 2
        self.custom_selected_names_tech = [""] * 6
        self.custom_selected_displayname_tech = ["1. CPU", "2. GPU", "3. 内存", "4.", "5.", "6."]
        self.full_custom_template = "p Hello world"
        # --- 新增功能配置 ---
        self.auto_start = 0  # 开机自启动：0=关闭 1=开启
        self.page_cycle_enable = 0  # 自动翻页轮播：0=关闭 1=开启
        self.page_cycle_interval = 10  # 自动翻页间隔（秒）
        self.screen_off_timeout = 0  # 屏幕待机超时（秒），0=禁用
        self.key_single = "下翻页"  # 单击动作
        self.key_double = "上翻页"  # 双击动作
        self.key_long = "切换方向"  # 长按动作
        # --- 第二批新增页面配置 ---
        self.marquee_text = "欢迎使用USB副屏"  # 跑马灯文本
        self.marquee_font = "./simhei.ttf"  # 跑马灯字体
        self.marquee_font_size = 20  # 跑马灯字号
        self.marquee_color = "#ffffff"  # 跑马灯字体颜色
        self.marquee_speed = 2  # 跑马灯滚动速度（每帧像素，越大越快）
        self.ping_host = "223.5.5.5"  # ping目标
        self.timer_minutes = 25  # 番茄钟分钟数
        self.memo_items = []  # 纪念日列表，每项"名称|MM-DD"
        self.todo_items = []  # 待办列表，每项一条
        # --- 第四批新增配置 ---
        self.zoom_enable = 0  # 镜像局部放大：0=关闭 1=开启
        self.zoom_scale = 2  # 放大倍数
        # --- 第五批新增配置 ---
        self.weather_city = "Beijing"  # 天气城市（wttr.in）
        self.crypto_symbols = "BTCUSDT,ETHUSDT"  # 行情交易对（Binance）
        self.language = "中文"  # 界面语言：中文/English
        # --- 进程占用 ---
        self.proc_count = 5  # 显示进程数量（超过屏幕自动翻页）
        # --- 世界时钟（每项"名称|UTC偏移"，逗号分隔） ---
        self.clock_zones = "北京|8,伦敦|0,纽约|-5,东京|9"
        # --- 硬件详情 ---
        self.hwdetail_max = 5  # 硬件详情显示数量（超过自动翻页）
        # --- 仪表盘 ---
        self.gauge_show_cpu = 1  # 显示CPU
        self.gauge_show_mem = 1  # 显示内存
        self.gauge_show_disk = 0  # 显示磁盘
        self.gauge_cpu_color = "#ff5050"
        self.gauge_mem_color = "#50a0ff"
        self.gauge_disk_color = "#50ff50"
        self.gauge_show_cpu_temp = 0  # 显示CPU温度
        self.gauge_show_gpu = 0  # 显示GPU负载
        self.gauge_cpu_temp_color = "#ffa500"
        self.gauge_gpu_color = "#50ff50"
        self.gauge_show_gpu_temp = 0  # 显示GPU温度
        self.gauge_show_fan = 0  # 显示风扇转速
        self.gauge_show_upload = 0  # 显示上传速率
        self.gauge_show_download = 1  # 显示下载速率
        self.gauge_gpu_temp_color = "#ff00ff"
        self.gauge_fan_color = "#00ffff"
        self.gauge_upload_color = "#ff00ff"
        self.gauge_download_color = "#00ff00"
        # --- 热搜 ---
        self.hotsearch_interval = 60  # 热搜自动刷新时间(秒)
        self.hotsearch_auto_refresh = 1  # 热搜自动刷新开关
        self.hotsearch_total = 5  # 抓取热搜总条数
        self.hotsearch_count = 5  # 每页显示条数
        self.hotsearch_font_size = 14  # 热搜字体大小（手动模式）
        self.hotsearch_font_auto = 1  # 字体自动适配屏幕
        self.hotsearch_scroll_enable = 1  # 长文本自动滚动字幕
        self.hotsearch_scroll_speed = 2.0  # 滚动字幕速度
        self.hotsearch_page_interval = 3  # 翻页间隔(秒)
        # --- 硬件详情监控类型 ---
        self.hwdetail_types = "Temperature,Fan"  # 逗号分隔，可含Temperature/Fan/Voltage/Load/Power
        # --- 传感器自由选择（LibreHardwareMonitor 全部传感器可选） ---
        self.hwdetail_sensor_names = ""   # 硬件详情：逗号分隔传感器全名（空=按类型自动选择）
        self.gauge_cpu_temp_sensor = ""   # 仪表盘CPU温度传感器全名（空=自动识别）
        self.gauge_gpu_temp_sensor = ""   # 仪表盘GPU温度传感器全名
        self.gauge_gpu_load_sensor = ""   # 仪表盘GPU负载传感器全名
        self.gauge_fan_sensor = ""        # 仪表盘风扇传感器全名
        # --- 磁盘读写速率 ---
        self.diskio_mode = "经典"         # 显示模式：经典 / 经典2 / 网速样式
        self.diskio_show_title = 1        # 经典模式：显示"磁盘读写"标题
        self.diskio_font_auto = 1         # 经典模式：字号自动适配屏幕
        self.diskio_font_size = 16        # 经典模式：手动字号
        self.diskio_title_color = "#ffffff"   # 标题颜色
        self.diskio_read_color = "#ff8000"    # "读"行颜色
        self.diskio_write_color = "#00ffff"   # "写"行颜色
        self.diskio_label_color = "#ffffff"   # 网速样式：标签颜色
        self.diskio_value_auto = 1        # 网速样式：字号自动适配
        self.diskio_value_font_size = 20  # 网速样式：手动字号
        self.diskio_bar1_color = "#eb8b8b"    # 网速样式：读柱状图颜色
        self.diskio_bar2_color = "#92d3d9"    # 网速样式：写柱状图颜色
        self.diskio_value_read_color = "#ff8000"   # 网速样式：读数值颜色
        self.diskio_value_write_color = "#00ffff"  # 网速样式：写数值颜色
        # 经典2样式（仿网络流量布局）：颜色跟随网络流量页面配色，无需独立配置
        # --- 网络流量监控（上传/下载） ---
        self.netspeed_mode = "自定义"          # 显示模式：经典 / 自定义
        self.netspeed_up_color = "#ff8000"    # 网络流量：上传文字颜色
        self.netspeed_down_color = "#00ffff"  # 网络流量：下载文字颜色
        self.netspeed_bar1_color = "#eb8b8b"  # 网络流量：上传柱状图颜色
        self.netspeed_bar2_color = "#92d3d9"  # 网络流量：下载柱状图颜色
        self.guide_last_page = ""    # 设置"按页面"导航上次选择的页面
        self.custom_color_schemes = {}  # 用户自定义配色方案 {名称: [颜色hex列表]}
        # --- API 投屏接入 ---
        self.api_enable = 1        # API 投屏服务器：0=关闭 1=开启
        self.api_port = 8632       # API 服务器端口
        self.api_token = ""        # API 访问令牌（可选，空=不校验）
        self.api_overlay = 0       # 强制投屏覆盖：0=需选择API投屏页 1=任何页面可投屏(结束自动返回原页面)
        self.screen_id_timeout = 5 # 屏幕序号检测显示时长（秒）


# ==================== LCD 屏幕分辨率检测 ====================

def Detect_LCD_Size():
    """自动检测小屏幕尺寸（尝试从设备SFR读取LCD分辨率）"""
    global LCD_MAX_X, LCD_MAX_Y
    dev = get_current_device()
    if dev is None:
        return False

    lcd_w_names = [b'Lcd_X', b'LCD_X', b'LCD_W', b'MSN_LCD_W', b'LCD_Width',
                   b'LCD_X_Max', b'LCD_Max_X', b'LCD_Size_X', b'LCD_Pixel_X', b'LCD_Col']
    lcd_h_names = [b'Lcd_Y', b'LCD_Y', b'LCD_H', b'MSN_LCD_H', b'LCD_Height',
                   b'LCD_Y_Max', b'LCD_Max_Y', b'LCD_Size_Y', b'LCD_Pixel_Y', b'LCD_Row']

    detected_w = 0
    detected_h = 0

    print('--- 开始自动检测LCD屏幕分辨率 ---')

    name_map = {}
    try:
        if dev.msn_data is not None:
            data_names = [d.name.decode('utf-8', errors='replace') for d in dev.msn_data]
            print('设备SFR数据名称列表: ' + str(data_names))
            for d in dev.msn_data:
                name_map[bytes(d.name)] = d
    except (NameError, TypeError, AttributeError):
        print('设备SFR数据名称列表: 设备未连接，无法获取')

    def _read_sfr_item(entry):
        """根据 MSN_Data 条目读取对应的 SFR 值"""
        data_type = entry.family[0] // 32
        if data_type == 0:  # u8, 2B地址
            addr = entry.data[0] * 256 + entry.data[1]
            return Read_M_u8(addr)
        elif data_type == 1:  # u16, 1B地址
            addr = entry.data[0]
            return Read_M_u16(addr)
        elif data_type == 2:  # u32, 2B地址
            addr = entry.data[0] * 256 + entry.data[1]
            val = 0
            for n in range(entry.family[0] % 32):
                val = (val << 8) | Read_M_u8(addr + n)
            return val
        return None

    for name in lcd_w_names:
        try:
            entry = name_map.get(name)
            if entry is None:
                continue
            result = _read_sfr_item(entry)
            if result is not None and result != 0:
                detected_w = result
                if 0 < detected_w <= 1024:
                    print('  检测到LCD宽度: ' + str(detected_w) + ' (SFR名称: ' + str(name) + ')')
                    break
                else:
                    detected_w = 0
        except:
            pass

    for name in lcd_h_names:
        try:
            entry = name_map.get(name)
            if entry is None:
                continue
            result = _read_sfr_item(entry)
            if result is not None and result != 0:
                detected_h = result
                if 0 < detected_h <= 1024:
                    print('  检测到LCD高度: ' + str(detected_h) + ' (SFR名称: ' + str(name) + ')')
                    break
                else:
                    detected_h = 0
        except:
            pass

    # 根据版本号推断
    if detected_w == 0 or detected_h == 0:
        print('  SFR命名检测未找到LCD尺寸,尝试版本推断...')
        my_device = dev.msn_device
        if my_device is not None:
            dev_ver = my_device.version
            print('  设备版本号: MSN' + str(dev_ver).zfill(2))
            version_res_map = {
                1: (128, 64),
                2: (128, 64),
                10: (128, 64),
                20: (240, 240),
                0: (160, 80),
            }
            if dev_ver in version_res_map:
                inferred = version_res_map[dev_ver]
                if detected_w == 0:
                    detected_w = inferred[0]
                if detected_h == 0:
                    detected_h = inferred[1]
                print('  根据版本号推断分辨率: ' + str(detected_w) + 'x' + str(detected_h))

    # 应用检测结果
    if detected_w > 0 and detected_h > 0:
        LCD_MAX_X = detected_w
        LCD_MAX_Y = detected_h
        # 同步到当前设备
        dev = get_current_device()
        if dev is not None:
            dev.LCD_MAX_X = detected_w
            dev.LCD_MAX_Y = detected_h
        msg = '屏幕分辨率: ' + str(LCD_MAX_X) + 'x' + str(LCD_MAX_Y) + ' (自动检测)'
        print(msg)
        insert_text_message(msg)
        return True
    else:
        msg = '自动检测失败,使用默认值: ' + str(LCD_MAX_X) + 'x' + str(LCD_MAX_Y)
        print(msg)
        insert_text_message(msg)
        return False


def ReDetect_LCD_Size():
    """重新检测LCD分辨率（后台线程执行串口读取，避免卡住界面）"""
    insert_text_message('正在重新检测屏幕分辨率...')
    def _worker():
        try:
            Detect_LCD_Size()
        except Exception:
            pass
        dev = get_current_device()
        if dev is not None:
            dev.state_change = 1
    threading.Thread(target=_worker, daemon=True).start()


def Set_LCD_Size_Manual(*args):
    """手动设置LCD分辨率"""
    global LCD_MAX_X, LCD_MAX_Y
    dev = get_current_device()
    _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
    ctx = _cur_main_ctx()
    if ctx and ctx.get('lcd_size_var'):
        v = ctx['lcd_size_var']
        size_str = v.currentText() if isinstance(v, QComboBox) else v.get()
    else:
        size_str = "%dx%d (默认)" % (LCD_MAX_X, LCD_MAX_Y)
    size_map = {
        '160x80 (默认)': (160, 80),
        '128x64 (0.96寸OLED)': (128, 64),
        '240x240 (1.54寸)': (240, 240),
        '320x240 (2.4寸)': (320, 240),
        '240x320 (竖屏)': (240, 320),
    }
    if size_str in size_map:
        LCD_MAX_X, LCD_MAX_Y = size_map[size_str]
        if dev is not None:
            dev.LCD_MAX_X = LCD_MAX_X
            dev.LCD_MAX_Y = LCD_MAX_Y
            dev.state_change = 1
        msg = '手动设置屏幕分辨率: ' + str(LCD_MAX_X) + 'x' + str(LCD_MAX_Y)
        print(msg)
        insert_text_message(msg)


def Cleanup_LCD_On_Exit():
    """程序退出前清理所有LCD屏幕"""
    for dev in list(all_devices.values()):
        dev.cleanup()


# ==================== UI 界面 ====================

def UI_Page():  # PySide6 (Qt) 主界面
# -*- coding: UTF-8 -*-
# 临时文件：新的 PySide6 UI_Page 函数体（不含 def 行），由脚本替换进 MSU2_MINI_V2_qt.py
# 三层结构：第一层「中控|关于」→ 第二层「屏幕1|屏幕2|屏幕3…」→ 第三层「主控|设置|设备信息」
# 第三层主控页 = 原版完整主控布局（设为自动连接/烧写区/RGB颜色/填充适应/动图间隔/最大FPS/
#              自定义内容/上翻下翻/方向/页面/相机/屏幕镜像窗口/分辨率/实时预览），每屏一套

    # ======================================================================
    # PySide6 (Qt) 主界面
    # ======================================================================
    global config_obj, Text1, all_windows, all_cameras
    global Label1, Label3, Label4, Label5, Label6, PAGE_ID, _tray_icon

    config_obj = load_config()
    apply_command_line_args()  # 应用命令行参数（--page/--com）
    apply_language()  # 应用界面语言设置

    # -------- Qt 应用与主窗口 --------
    app = QApplication.instance() or QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("%s v%s - %s - %s" % (PROGRAM_TITLE, PROGRAM_VERSION, PROGRAM_SUBTITLE, PROGRAM_GITHUB))

    global _ui_root
    _ui_root = window
    QTimer.singleShot(100, _process_ui_msg_queue)

    try:
        ico_path = "resource/icon.ico" if scale_factor >= 200 else "resource/icon_small.ico"
        iconimage = MiniMark.load_image(ico_path)
        window.setWindowIcon(QIcon(ico_path))
    except Exception:
        iconimage = None

    central = QWidget()
    window.setCentralWidget(central)
    root_lay = QVBoxLayout(central)
    root_lay.setContentsMargins(8, 8, 8, 8)
    root_lay.setSpacing(6)

    # ==================== 多设备选择栏 ====================
    device_bar = QHBoxLayout()
    root_lay.addLayout(device_bar)
    device_bar.addWidget(QLabel("已连接设备:"))

    device_selector = QComboBox()
    device_selector.setMinimumWidth(110)
    device_bar.addWidget(device_selector)

    device_count_label = QLabel("(0个设备)")
    device_count_label.setStyleSheet("color:gray;")
    device_bar.addWidget(device_count_label)
    device_bar.addStretch(1)

    def refresh_device_list():
        """刷新设备列表下拉框"""
        connected = [d for d in all_devices.values() if d.device_state == 1]
        names = [d.device_name for d in connected] if connected else ["屏幕1"]
        cur = device_selector.currentText()
        device_selector.blockSignals(True)
        device_selector.clear()
        device_selector.addItems(names)
        device_selector.blockSignals(False)
        device_count_label.setText("(%d个设备)" % len(connected))
        if cur in names:
            device_selector.setCurrentText(cur)
        else:
            device_selector.setCurrentText(names[0])

    def on_device_select(index=-1):
        """切换当前活跃设备（每屏独立配置/页面）"""
        global config_obj, _primary_device
        name = device_selector.currentText()
        old = _primary_device
        for dev in all_devices.values():
            if dev.device_name == name and dev.device_state == 1:
                if old is not None and old != dev:
                    if old.config is not None:
                        old.config.state_machine = old.state_machine
                    else:
                        old.state_machine = config_obj.state_machine
                set_current_device(dev)
                _primary_device = dev
                set_active_device_config(dev)
                if dev.config is not None:
                    dev.config.state_machine = getattr(dev, "state_machine", SCREEN_PAGE_ID)
                state_change_set(save=False)
                sync_page_combobox()
                sync_lcd_combobox()
                try:
                    _select_main_tab(dev.index)
                except Exception:
                    pass
                break

    device_selector.currentIndexChanged.connect(on_device_select)

    refresh_btn = QPushButton("刷新")
    refresh_btn.setFixedWidth(60)
    refresh_btn.clicked.connect(refresh_device_list)
    device_bar.addWidget(refresh_btn)

    refresh_device_list()

    # ==================== 第一层标签：中控 | 关于 ====================
    top_nb = QTabWidget()
    root_lay.addWidget(top_nb, 1)

    # ---------- 中控页（第二层：每屏标签 + 底部共享信息框） ----------
    root = QWidget()
    top_nb.addTab(root, "  中控  ")
    root_lay2 = QVBoxLayout(root)
    root_lay2.setContentsMargins(4, 4, 4, 4)

    # 状态栏（共享）：设为自动连接 + 设备状态 + 隐藏按钮（参照老版布局）
    status_bar = QHBoxLayout()
    root_lay2.addLayout(status_bar)
    auto_cb = QCheckBox("设为自动连接")
    auto_cb.setChecked(bool(_auto_connect))

    def _toggle_auto(val):
        global _auto_connect
        _auto_connect = bool(val)
        insert_text_message("已开启自动连接（默认）" if _auto_connect else "已关闭自动连接（需手动点击\"连接\"）")

    auto_cb.toggled.connect(_toggle_auto)
    status_bar.addWidget(auto_cb)
    dev_state_lbl = QLabel("")
    dev_state_lbl.setStyleSheet("color:gray;")
    status_bar.addWidget(dev_state_lbl)
    status_bar.addStretch(1)
    hide_btn = QPushButton("隐藏")
    hide_btn.setFixedWidth(60)
    hide_btn.clicked.connect(lambda: hide_to_tray())
    status_bar.addWidget(hide_btn)

    main_notebook = QTabWidget()
    root_lay2.addWidget(main_notebook, 1)
    # 共享信息框（业务逻辑 insert_text_message 使用全局 Text1）
    info_lbl = QLabel("信息:")
    root_lay2.addWidget(info_lbl)
    Text1 = QTextEdit()
    Text1.setReadOnly(True)
    Text1.setMaximumHeight(90)
    root_lay2.addWidget(Text1)

    def apply_color_preset(event=None):
        pass

    def _show_custom_dialog():
        """自定义显示编辑窗口（PySide6）：显示多项数值 / 显示两项图表 + 模板编辑 + 实时预览"""
        global config_obj
        if hardware_monitor_manager == 1:
            insert_text_message("Libre Hardware Monitor 加载失败，自定义内容功能不可用")
            return
        elif hardware_monitor_manager is None:
            insert_text_message("Libre Hardware Monitor 正在加载，请稍候……", cleanNext=False)
            return

        dlg = QDialog(window)
        dlg.setWindowTitle("自定义显示内容")
        dlg.setMinimumSize(760, 620)
        main_lay = QVBoxLayout(dlg)
        nb = QTabWidget()
        main_lay.addWidget(nb)

        sensor_keys = []
        try:
            if hardware_monitor_manager is not None and hardware_monitor_manager != 1:
                sensor_keys = list(hardware_monitor_manager.sensors.keys())
        except Exception:
            pass

        def _save_state():
            _ui_set_active()
            save_config()

        # ========== 显示多项数值（tech） ==========
        tech = QWidget()
        nb.addTab(tech, "  显示多项数值  ")
        tl = QVBoxLayout(tech)

        grid = QGridLayout()
        tl.addLayout(grid)
        grid.addWidget(QLabel("名称"), 0, 0)
        grid.addWidget(QLabel("项目"), 0, 1)

        names_tech = list(config_obj.custom_selected_names_tech) + [""] * 6
        dnames_tech = list(config_obj.custom_selected_displayname_tech) + [""] * 6
        for i in range(6):
            ne = QLineEdit(dnames_tech[i] if i < len(dnames_tech) else "")
            ne.setFixedWidth(80)
            grid.addWidget(ne, i + 1, 0)
            sc = QComboBox()
            sc.addItems([""] + sensor_keys)
            sc.setCurrentText(names_tech[i] if i < len(names_tech) and names_tech[i] in sensor_keys else "")
            sc.setMinimumWidth(220)
            grid.addWidget(sc, i + 1, 1)

            def _save_name(ii=i, nne=ne):
                while len(config_obj.custom_selected_displayname_tech) <= ii:
                    config_obj.custom_selected_displayname_tech.append("")
                config_obj.custom_selected_displayname_tech[ii] = nne.text()
                _save_state()

            def _save_sensor(ii=i, ssc=sc):
                while len(config_obj.custom_selected_names_tech) <= ii:
                    config_obj.custom_selected_names_tech.append("")
                config_obj.custom_selected_names_tech[ii] = ssc.currentText()
                _save_state()

            ne.editingFinished.connect(_save_name)
            sc.currentIndexChanged.connect(_save_sensor)
        grid.setColumnStretch(1, 1)

        tl.addWidget(QLabel("完全自定义模板代码："))
        text_area = QPlainTextEdit()
        text_area.setPlainText(config_obj.full_custom_template)
        tl.addWidget(text_area, 1)

        # 命令插入行
        cmd_row = QHBoxLayout()
        tl.addLayout(cmd_row)
        cmd_type_list = ["p 文本", "a 锚点", "m 移动到", "t 相对移动", "f 字体", "c 颜色",
                         "i 图片", "v 数值", "r 矩形", "l 线条", "o 圆", "g 动图"]
        cmd_type_combo = QComboBox()
        cmd_type_combo.addItems(cmd_type_list)
        cmd_row.addWidget(cmd_type_combo)
        cmd_arg = QLineEdit()
        cmd_arg.setPlaceholderText("参数，如 p:文字 / c:#ff0000 / m:8 8 / v:1 {:.1f}")
        cmd_row.addWidget(cmd_arg, 1)

        def _insert_cmd():
            letter = cmd_type_combo.currentText()[0]
            arg = cmd_arg.text().strip()
            text_area.insertPlainText(letter + (" " + arg if arg else "") + "\n")
            _save_template()
            cmd_arg.clear()

        insert_btn = QPushButton("插入")
        insert_btn.clicked.connect(_insert_cmd)
        cmd_row.addWidget(insert_btn)

        # 实时预览
        preview_lbl = QLabel()
        pw = SHOW_WIDTH * 3
        ph = SHOW_HEIGHT * 3
        preview_lbl.setFixedSize(pw, ph)
        preview_lbl.setStyleSheet("background:black; border:1px solid gray;")
        preview_lbl.setScaledContents(True)
        tl.addWidget(preview_lbl, 0, Qt.AlignHCenter)

        def _update_preview():
            try:
                im = get_full_custom_im(update_sensors=False)
                qimg = QImage(im.tobytes(), im.width, im.height, im.width * 3, QImage.Format_RGB888)
                preview_lbl.setPixmap(QPixmap.fromImage(qimg))
            except Exception:
                pass

        def _save_template():
            _ui_set_active()
            config_obj.full_custom_template = text_area.toPlainText()
            save_config()
            _update_preview()

        text_area.textChanged.connect(_save_template)

        btn_row = QHBoxLayout()
        tl.addLayout(btn_row)

        def _example(n):
            if n == 1:
                t = '\n'.join([
                    "i resource/example_background.png", "c #ff3333", "f resource/Orbitron-Regular.ttf 22",
                    "m 16 16", "v 1 {:.0f}", "p %", "m 96 16", "v 2 {:.0f}", "p %",
                    "m 96 44", "v 3 {:.0f}", "p %"
                ])
            else:
                t = '\n'.join([
                    "m 8 8", "f resource/Orbitron-Bold.ttf 20", "p CPU", "t 8 0", "c #3366cc", "v 1",
                    "m 8 28", "c #000000", "f resource/Orbitron-Bold.ttf 20", "p GPU", "t 8 0", "c #3366cc", "v 2",
                    "m 8 48", "c #000000", "f resource/Orbitron-Bold.ttf 20", "p RAM", "t 8 0", "c #3366cc", "v 3"
                ])
            text_area.setPlainText(t)
            _save_template()

        ex1 = QPushButton("科技")
        ex1.clicked.connect(lambda: _example(1))
        btn_row.addWidget(ex1)
        ex2 = QPushButton("简单")
        ex2.clicked.connect(lambda: _example(2))
        btn_row.addWidget(ex2)

        def _show_error():
            _update_preview()
            print(full_custom_error.rstrip('\n'))
            if full_custom_error == "OK":
                QMessageBox.information(dlg, "提示", full_custom_error)
            else:
                QMessageBox.warning(dlg, "错误", full_custom_error)

        err_btn = QPushButton("查看模板错误")
        err_btn.clicked.connect(_show_error)
        btn_row.addWidget(err_btn)
        btn_row.addStretch(1)

        # ========== 显示两项图表（simple） ==========
        simple = QWidget()
        nb.addTab(simple, "  显示两项图表  ")
        sl = QVBoxLayout(simple)
        sgrid = QGridLayout()
        sl.addLayout(sgrid)
        sgrid.addWidget(QLabel("名称"), 0, 0)
        sgrid.addWidget(QLabel("项目"), 0, 1)

        names2 = list(config_obj.custom_selected_names) + [""] * 2
        dnames2 = list(config_obj.custom_selected_displayname) + [""] * 2
        for i in range(2):
            ne = QLineEdit(dnames2[i] if i < len(dnames2) else "")
            ne.setFixedWidth(80)
            sgrid.addWidget(ne, i + 1, 0)
            sc = QComboBox()
            sc.addItems([""] + sensor_keys)
            sc.setCurrentText(names2[i] if i < len(names2) and names2[i] in sensor_keys else "")
            sc.setMinimumWidth(220)
            sgrid.addWidget(sc, i + 1, 1)

            def _save_name2(ii=i, nne=ne):
                while len(config_obj.custom_selected_displayname) <= ii:
                    config_obj.custom_selected_displayname.append("")
                config_obj.custom_selected_displayname[ii] = nne.text()
                _save_state()

            def _save_sensor2(ii=i, ssc=sc):
                while len(config_obj.custom_selected_names) <= ii:
                    config_obj.custom_selected_names.append("")
                config_obj.custom_selected_names[ii] = ssc.currentText()
                _save_state()
                if ii == 0 and custom_plot_data is not None:
                    custom_plot_data["sent"] = [0] * (SHOW_WIDTH // 2)
                elif ii == 1 and custom_plot_data is not None:
                    custom_plot_data["recv"] = [0] * (SHOW_WIDTH // 2)

            ne.editingFinished.connect(_save_name2)
            sc.currentIndexChanged.connect(_save_sensor2)
        sgrid.setColumnStretch(1, 1)
        sl.addStretch(1)

        # ========== 图形化编辑（visual） ==========
        visual = QWidget()
        nb.addTab(visual, "  图形化编辑  ")
        vl = QVBoxLayout(visual)

        CMD_NAMES = {"p": "文本", "a": "锚点", "m": "位置", "t": "偏移", "f": "字体", "c": "颜色",
                     "i": "图片", "v": "数值", "r": "矩形", "l": "线条", "o": "圆", "g": "动图"}

        def cmd_to_line(cmd):
            letter = cmd[0]
            if letter == "raw":
                return cmd[1]
            if letter in ("p", "a", "c", "i", "g"):
                return "%s %s" % (letter, cmd[1])
            if letter in ("m", "t"):
                return "%s %s %s" % (letter, cmd[1], cmd[2])
            if letter == "f":
                return "f %s %s" % (cmd[1], cmd[2])
            if letter == "v":
                return "v %s %s" % (cmd[1], cmd[2]) if cmd[2] else "v " + cmd[1]
            if letter in ("r", "l"):
                return "%s %s %s %s %s" % (letter, cmd[1], cmd[2], cmd[3], cmd[4])
            if letter == "o":
                return "o %s %s %s" % (letter, cmd[1], cmd[2], cmd[3])
            return ""

        def cmd_to_desc(cmd):
            letter = cmd[0]
            if letter == "raw":
                return "[未识别] " + cmd[1]
            if letter == "p":
                return "文本 \"%s\"" % cmd[1]
            if letter == "a":
                return "锚点 %s" % cmd[1]
            if letter == "m":
                return "移动到 (%s, %s)" % (cmd[1], cmd[2])
            if letter == "t":
                return "相对移动 (%s, %s)" % (cmd[1], cmd[2])
            if letter == "f":
                return "字体 %s 字号%s" % (cmd[1], cmd[2])
            if letter == "c":
                return "颜色 %s" % cmd[1]
            if letter == "i":
                return "图片 %s" % cmd[1]
            if letter == "v":
                return "数值 #%s%s" % (cmd[1], (" 格式" + cmd[2]) if cmd[2] else "")
            if letter == "r":
                return "矩形 (%s,%s)-(%s,%s)" % (cmd[1], cmd[2], cmd[3], cmd[4])
            if letter == "l":
                return "线条 (%s,%s)-(%s,%s)" % (cmd[1], cmd[2], cmd[3], cmd[4])
            if letter == "o":
                return "圆 (%s,%s) r=%s" % (cmd[1], cmd[2], cmd[3])
            if letter == "g":
                return "动图 %s" % cmd[1]
            return str(cmd)

        def parse_template_to_cmds(template):
            cmds = []
            for line in template.split('\n'):
                line = line.rstrip('\r')
                parts = line.split()
                if not parts:
                    continue
                c = parts[0]
                try:
                    if c == 'p':
                        cmds.append(("p", ' '.join(parts[1:])))
                    elif c == 'a':
                        cmds.append(("a", parts[1]))
                    elif c == 'm':
                        cmds.append(("m", parts[1], parts[2]))
                    elif c == 't':
                        cmds.append(("t", parts[1], parts[2]))
                    elif c == 'c':
                        cmds.append(("c", parts[1]))
                    elif c == 'v':
                        cmds.append(("v", parts[1], parts[2] if len(parts) > 2 else ""))
                    elif c == 'f':
                        font_name = line[line.index(parts[0]) + 1:line.rindex(parts[-1])].strip()
                        cmds.append(("f", font_name, parts[-1]))
                    elif c == 'i':
                        cmds.append(("i", line[line.index(parts[0]) + 1:].strip()))
                    elif c == 'r':
                        cmds.append(("r", parts[1], parts[2], parts[3], parts[4]))
                    elif c == 'l':
                        cmds.append(("l", parts[1], parts[2], parts[3], parts[4]))
                    elif c == 'o':
                        cmds.append(("o", parts[1], parts[2], parts[3]))
                    elif c == 'g':
                        cmds.append(("g", line[line.index(parts[0]) + 1:].strip()))
                    else:
                        cmds.append(("raw", line))
                except (IndexError, ValueError):
                    cmds.append(("raw", line))
            return cmds

        visual_cmds = parse_template_to_cmds(config_obj.full_custom_template)

        tip = QLabel("双击列表项可编辑；下方按钮添加元素；右侧为实时预览。结果与“显示多项数值”页共享。")
        tip.setStyleSheet("color:gray;")
        vl.addWidget(tip)

        vis_row = QHBoxLayout()
        vl.addLayout(vis_row)
        cmd_list = QListWidget()
        cmd_list.setMinimumWidth(360)
        vis_row.addWidget(cmd_list, 1)
        vis_preview = QLabel()
        vis_preview.setFixedSize(pw, ph)
        vis_preview.setStyleSheet("background:black; border:1px solid gray;")
        vis_preview.setScaledContents(True)
        vis_row.addWidget(vis_preview)

        def refresh_cmd_list():
            cmd_list.clear()
            for cmd in visual_cmds:
                cmd_list.addItem(cmd_to_desc(cmd))

        def update_visual_preview():
            try:
                im = get_full_custom_im(update_sensors=False)
                qimg = QImage(im.tobytes(), im.width, im.height, im.width * 3, QImage.Format_RGB888)
                vis_preview.setPixmap(QPixmap.fromImage(qimg))
            except Exception:
                pass

        def rebuild_template_and_preview():
            _ui_set_active()
            config_obj.full_custom_template = "\n".join(cmd_to_line(c) for c in visual_cmds)
            save_config()
            refresh_cmd_list()
            update_visual_preview()
            text_area.setPlainText(config_obj.full_custom_template)

        def open_cmd_dialog(cmd_type, edit_index=None):
            dlg2 = QDialog(dlg)
            dlg2.setWindowTitle("添加" + CMD_NAMES.get(cmd_type, "") + ("" if edit_index is None else "（编辑）"))
            v2 = QVBoxLayout(dlg2)
            existing = None
            if edit_index is not None and 0 <= edit_index < len(visual_cmds):
                existing = visual_cmds[edit_index]
            collect = {}

            def _entry_row(label, value, width=120):
                row = QHBoxLayout()
                v2.addLayout(row)
                row.addWidget(QLabel(label))
                e = QLineEdit(value)
                e.setFixedWidth(width)
                row.addWidget(e)
                return e

            def _browse_row(callback):
                row = QHBoxLayout()
                v2.addLayout(row)
                row.addStretch(1)
                b = QPushButton("浏览…")
                b.clicked.connect(callback)
                row.addWidget(b)

            if cmd_type == "p":
                e = _entry_row("文字：", existing[1] if existing else "", 220)
                collect["data"] = lambda: ("p", e.text())
            elif cmd_type == "v":
                row = QHBoxLayout()
                v2.addLayout(row)
                row.addWidget(QLabel("数值项："))
                idx_combo = QComboBox()
                idx_combo.addItems(["1", "2", "3", "4", "5", "6"])
                idx_combo.setCurrentText(existing[1] if existing else "1")
                row.addWidget(idx_combo)
                fmt_e = _entry_row("格式(可选)：", existing[2] if existing else "", 110)
                v2.addWidget(QLabel("例：{:.1f} 保留1位小数，留空则原样显示"))
                collect["data"] = lambda: ("v", idx_combo.currentText(), fmt_e.text().strip())
            elif cmd_type in ("m", "t"):
                e1 = _entry_row("x：", existing[1] if existing else "0", 60)
                e2 = _entry_row("y：", existing[2] if existing else "0", 60)
                collect["data"] = lambda: (cmd_type, e1.text(), e2.text())
            elif cmd_type == "a":
                anchors = ["la", "ma", "ra", "ls", "ms", "rs", "lt", "mt", "rt", "lm", "mm", "rm",
                           "lb", "mb", "rb", "ld", "md", "rd", "ct"]
                row = QHBoxLayout()
                v2.addLayout(row)
                row.addWidget(QLabel("锚点："))
                a_combo = QComboBox()
                a_combo.addItems(anchors)
                a_combo.setCurrentText(existing[1] if existing else "la")
                row.addWidget(a_combo)
                v2.addWidget(QLabel("la/ra/ma=左/右/中 顶对齐，ls/rs/ms=基线，lb/rb=底部，ct=居中"))
                collect["data"] = lambda: ("a", a_combo.currentText())
            elif cmd_type == "c":
                e = _entry_row("颜色：", existing[1] if existing else "#ff0000", 110)

                def _pick_cc():
                    c = QColorDialog.getColor(QColor(e.text()), dlg2)
                    if c.isValid():
                        e.setText(c.name())

                _browse_row(_pick_cc)
                collect["data"] = lambda: ("c", e.text())
            elif cmd_type == "f":
                e = _entry_row("字体文件：", existing[1] if existing else "", 220)
                s_e = _entry_row("字号：", existing[2] if existing else "20", 60)

                def _pick_ff():
                    path, _ = QFileDialog.getOpenFileName(dlg2, "选择字体", "", "字体文件 (*.ttf *.otf)")
                    if path:
                        e.setText(path)

                _browse_row(_pick_ff)
                collect["data"] = lambda: ("f", e.text(), s_e.text())
            elif cmd_type == "i":
                e = _entry_row("图片文件：", existing[1] if existing else "", 220)

                def _pick_ii():
                    path, _ = QFileDialog.getOpenFileName(dlg2, "选择图片", "", "图片文件 (*.png *.jpg *.bmp)")
                    if path:
                        e.setText(path)

                _browse_row(_pick_ii)
                collect["data"] = lambda: ("i", e.text())
            elif cmd_type in ("r", "l"):
                es = []
                row = QHBoxLayout()
                v2.addLayout(row)
                row.addWidget(QLabel("x1 y1 x2 y2："))
                for k in range(4):
                    e = QLineEdit(existing[k + 1] if existing else "0")
                    e.setFixedWidth(50)
                    row.addWidget(e)
                    es.append(e)
                collect["data"] = lambda: (cmd_type, es[0].text(), es[1].text(), es[2].text(), es[3].text())
            elif cmd_type == "o":
                es = []
                row = QHBoxLayout()
                v2.addLayout(row)
                row.addWidget(QLabel("x y 半径："))
                for k in range(3):
                    e = QLineEdit(existing[k + 1] if existing else "0")
                    e.setFixedWidth(50)
                    row.addWidget(e)
                    es.append(e)
                collect["data"] = lambda: (cmd_type, es[0].text(), es[1].text(), es[2].text())
            elif cmd_type == "g":
                e = _entry_row("GIF文件：", existing[1] if existing else "", 220)

                def _pick_gg():
                    path, _ = QFileDialog.getOpenFileName(dlg2, "选择动图", "", "GIF (*.gif)")
                    if path:
                        e.setText(path)

                _browse_row(_pick_gg)
                collect["data"] = lambda: ("g", e.text())

            btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            v2.addWidget(btns)

            def _on_ok():
                data = collect["data"]()
                if data:
                    if edit_index is None:
                        visual_cmds.append(data)
                    else:
                        visual_cmds[edit_index] = data
                    rebuild_template_and_preview()
                dlg2.accept()

            btns.accepted.connect(_on_ok)
            btns.rejected.connect(dlg2.reject)
            dlg2.exec()

        # 添加/编辑/删除/移动按钮
        add_row = QHBoxLayout()
        vl.addLayout(add_row)
        add_row.addWidget(QLabel("添加命令:"))
        add_type = QComboBox()
        add_type.addItems([CMD_NAMES[k] + " (" + k + ")" for k in CMD_NAMES])
        add_row.addWidget(add_type)

        def _on_add():
            letter = list(CMD_NAMES.keys())[add_type.currentIndex()]
            open_cmd_dialog(letter)

        add_btn = QPushButton("添加")
        add_btn.clicked.connect(_on_add)
        add_row.addWidget(add_btn)
        add_row.addStretch(1)

        ed_row = QHBoxLayout()
        vl.addLayout(ed_row)

        def _edit_sel():
            row = cmd_list.currentRow()
            if row < 0:
                return
            cmd = visual_cmds[row]
            if cmd[0] == "raw":
                QMessageBox.information(dlg, "提示", "该行无法识别，请在“显示多项数值”页手动修改，或删除后重新添加。")
                return
            open_cmd_dialog(cmd[0], row)

        def _del_sel():
            row = cmd_list.currentRow()
            if row >= 0:
                del visual_cmds[row]
                rebuild_template_and_preview()

        def _move(delta):
            row = cmd_list.currentRow()
            if row < 0:
                return
            nrow = row + delta
            if 0 <= nrow < len(visual_cmds):
                visual_cmds[row], visual_cmds[nrow] = visual_cmds[nrow], visual_cmds[row]
                rebuild_template_and_preview()
                cmd_list.setCurrentRow(nrow)

        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(_edit_sel)
        ed_row.addWidget(edit_btn)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(_del_sel)
        ed_row.addWidget(del_btn)
        up_btn = QPushButton("上移")
        up_btn.clicked.connect(lambda: _move(-1))
        ed_row.addWidget(up_btn)
        dn_btn = QPushButton("下移")
        dn_btn.clicked.connect(lambda: _move(1))
        ed_row.addWidget(dn_btn)
        ed_row.addStretch(1)

        cmd_list.itemDoubleClicked.connect(lambda _: _edit_sel())
        refresh_cmd_list()
        update_visual_preview()

        _update_preview()
        dlg.exec()
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览
# -*- coding: UTF-8 -*-
# 临时文件：新的 _build_main_tab 函数体（完整函数定义，含 def 行），替换进 _qt_ui_page_body.py
# 布局精确复刻老版 4.7.1 主控页：左列烧写区/控制区，右列颜色/填充/间隔/FPS/相机，底部实时预览

    def _build_main_tab(parent, dev):
        """为一块屏创建第三层「主控」子页，布局参照老版 4.7.1"""
        global all_cameras, all_windows, config_obj
        if all_cameras is None:
            all_cameras = {}
        if all_windows is None:
            all_windows = {}

        outer = QVBoxLayout(parent)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        def _cfg():
            return dev.config if dev.config is not None else config_obj

        def _lock_screen():
            set_active_device_config(dev)

        # 事件过滤器：点击下拉框时刷新列表（约等于原版 ButtonPress 刷新）
        _popup_filters = []

        def _install_popup_refresh(combo, refresh):
            class _Filter(QObject):
                def eventFilter(self, obj, ev):
                    if ev.type() == QEvent.MouseButtonPress:
                        try:
                            refresh()
                        except Exception:
                            pass
                    return False
            f = _Filter(combo)
            combo.installEventFilter(f)
            _popup_filters.append(f)

        # 跨线程 UI 更新桥：后台线程经信号回主线程填充下拉框。
        # 注意：在后台线程里直接调用 QTimer.singleShot(0, _done) 不会触发
        # （定时器属于调用线程，而 worker 线程没有事件循环），导致下拉框一直为空。
        class _ComboBridge(QObject):
            camera_ready = Signal(object)
            windows_ready = Signal(object)

        _combo_bridge = _ComboBridge()
        _popup_filters.append(_combo_bridge)  # 防 GC

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        outer.addLayout(grid)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 0)
        grid.setColumnStretch(3, 0)
        grid.setColumnStretch(4, 1)
        grid.setColumnStretch(5, 1)

        # ===== 右列：文字颜色（row0-2，col3-5） =====
        color_head = QHBoxLayout()
        grid.addLayout(color_head, 0, 3)
        color_head.addWidget(QLabel("文字颜色:"))
        color_swatch = QLabel()
        color_swatch.setFixedSize(40, 20)
        color_swatch.setStyleSheet("border:1px solid gray; background:#808080;")
        color_head.addWidget(color_swatch)
        color_head.addStretch(1)

        color_frame = QWidget()
        color_lay = QVBoxLayout(color_frame)
        color_lay.setContentsMargins(0, 0, 0, 0)
        color_lay.setSpacing(2)
        sliders = {}

        def _add_slider_row(lay, label, key):
            row = QHBoxLayout()
            lay.addLayout(row)
            lbl = QLabel(label)
            lbl.setFixedWidth(16)
            row.addWidget(lbl)
            sl = QSlider(Qt.Horizontal)
            sl.setRange(0, 255)
            sl.setValue(int(getattr(_cfg(), "text_color_" + key, 128)))
            row.addWidget(sl, 1)
            vl = QLabel(str(int(getattr(_cfg(), "text_color_" + key, 128))))
            vl.setFixedWidth(30)
            vl.setAlignment(Qt.AlignCenter)
            row.addWidget(vl)
            sliders[key] = sl

            def _on_color(v, k=key, vlabel=vl):
                cc = _cfg()
                setattr(cc, "text_color_" + k, int(v))
                _lock_screen()
                save_config()
                vlabel.setText(str(int(v)))
                rr = cc.text_color_r; gg = cc.text_color_g; bb = cc.text_color_b
                color_swatch.setStyleSheet(
                    "border:1px solid gray; background:rgb(%d,%d,%d);" % (rr, gg, bb))
                if cc.state_machine in (PCTIME_PAGE_ID, STATE_PAGE_ID):
                    dev.state_change = 1

            sl.valueChanged.connect(_on_color)

        _add_slider_row(color_lay, "R", "r")
        _add_slider_row(color_lay, "G", "g")
        _add_slider_row(color_lay, "B", "b")
        grid.addWidget(color_frame, 0, 4, 3, 2)

        # ===== 预设颜色下拉（row1，col3） =====
        color_presets = {
            "⚪ 纯白": (255, 255, 255), "⚫ 纯黑": (0, 0, 0), "🔴 大红": (255, 0, 0),
            "🟢 翠绿": (0, 255, 0), "🔵 宝蓝": (0, 0, 255), "🟡 明黄": (255, 255, 0),
            "🟣 紫罗兰": (255, 0, 255), "🩵 天青": (0, 255, 255), "🟠 橙色": (255, 128, 0),
            "🩶 中灰": (128, 128, 128), "🤎 棕色": (139, 69, 19), "💗 粉色": (255, 192, 203),
            "💗 马卡龙粉": (255, 179, 186), "💚 马卡龙绿": (186, 255, 201),
            "💙 马卡龙蓝": (186, 225, 255), "💜 马卡龙紫": (221, 186, 255),
            "🧡 马卡龙橘": (255, 214, 186), "💛 马卡龙柠檬": (255, 255, 186),
            "🔴 Red 500": (244, 67, 54), "💗 Pink 300": (240, 98, 146),
            "💜 DeepPurple": (103, 58, 183), "💙 Indigo": (63, 81, 181),
            "🔵 Blue 500": (33, 150, 243), "🩵 Cyan 500": (0, 188, 212),
            "🟢 Teal 500": (0, 150, 136), "🟡 Amber 500": (255, 193, 7),
            "🟠 Orange 500": (255, 152, 0), "🤎 Brown 400": (141, 110, 99),
            "🔥 暖橙": (255, 140, 50), "🌅 夕阳橙": (255, 180, 100),
            "🌹 玫瑰红": (220, 50, 80), "🍑 蜜桃": (255, 200, 170),
            "🍊 珊瑚": (255, 127, 80), "🍓 草莓": (255, 60, 80),
            "❄ 冰蓝": (135, 206, 235), "🌊 深海蓝": (30, 80, 180),
            "🌿 薄荷绿": (152, 255, 152), "🍀 森林绿": (50, 150, 80),
            "⬛ 炭灰": (60, 60, 60), "⬜ 银白": (200, 200, 200),
            "🟤 暗金": (200, 160, 60), "💎 午夜蓝": (20, 30, 80),
            "💚 霓虹绿": (57, 255, 20), "💗 霓虹粉": (255, 20, 147),
            "💛 霓虹黄": (255, 255, 50), "💙 霓虹蓝": (50, 200, 255),
            "🧡 霓虹橙": (255, 100, 20), "💜 霓虹紫": (180, 50, 255),
        }
        color_combo = QComboBox()
        color_combo.addItems(list(color_presets.keys()))
        try:
            cur_rgb = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
            for name, rgb in color_presets.items():
                if rgb == cur_rgb:
                    color_combo.setCurrentText(name)
                    break
        except Exception:
            pass

        def _apply_color_preset():
            name = color_combo.currentText()
            rgb = color_presets.get(name)
            if rgb is None:
                return
            r, g, b = rgb
            _lock_screen()
            config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b = r, g, b
            save_config()
            color_swatch.setStyleSheet("border:1px solid gray; background:rgb(%d,%d,%d);" % (r, g, b))
            for k, sl in sliders.items():
                sl.blockSignals(True)
                sl.setValue(getattr(config_obj, "text_color_" + k))
                sl.blockSignals(False)
            if config_obj.state_machine in (PCTIME_PAGE_ID, STATE_PAGE_ID):
                dev.state_change = 1

        color_combo.currentIndexChanged.connect(lambda _: _apply_color_preset())
        grid.addWidget(color_combo, 1, 3)

        # ===== 烧写区（row1-4，col0-2） =====
        burn_labels = {1: None, 2: None, 3: None, 4: None}
        burn_items = [
            (1, "选择闪存固件", Get_Photo_Path, Start_Write_Photo_Path),
            (3, "选择相册图像", Get_Photo_Path, Start_Write_Photo_Path),
            (2, "选择背景图像", Get_Photo_Path, Start_Write_Photo_Path),
            (4, "选择动图文件", Get_Photo_Path, Start_Write_Photo_Path),
        ]
        for i, (idx, text, get_fn, write_fn) in enumerate(burn_items):
            r = i + 1
            le = QLineEdit()
            le.setReadOnly(True)
            le.setText(text)
            grid.addWidget(le, r, 0, 1, 2)
            burn_labels[idx] = le
            btn_frame = QWidget()
            bl = QHBoxLayout(btn_frame)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(2)
            b_sel = QPushButton("选择")
            b_sel.setFixedWidth(48)
            b_sel.clicked.connect(lambda _=False, ii=idx, gf=get_fn: gf(ii))
            bl.addWidget(b_sel)
            b_burn = QPushButton("烧写")
            b_burn.setFixedWidth(48)
            b_burn.clicked.connect(lambda _=False, ii=idx, wf=write_fn: wf(ii))
            bl.addWidget(b_burn)
            grid.addWidget(btn_frame, r, 2)
        Label3 = burn_labels[1]; Label5 = burn_labels[3]
        Label4 = burn_labels[2]; Label6 = burn_labels[4]

        # ===== 填充/适应（row3，col4-5） =====
        radio_fill = QRadioButton(" 填充")
        radio_fit = QRadioButton(" 适应")
        radio_fill.setChecked(_cfg().shrink_type == 1)
        radio_fit.setChecked(_cfg().shrink_type == 2)

        def _chg_shrink():
            cc = _cfg()
            val = 1 if radio_fill.isChecked() else 2
            if val != cc.shrink_type:
                cc.shrink_type = val
                _lock_screen()
                save_config()

        radio_fill.toggled.connect(_chg_shrink)
        radio_fit.toggled.connect(_chg_shrink)
        grid.addWidget(radio_fill, 3, 4)
        grid.addWidget(radio_fit, 3, 5)

        # ===== 动图间隔（row4，col4-5） =====
        grid.addWidget(QLabel("动图间隔"), 4, 4)
        interval_edit = QLineEdit(str(_cfg().photo_interval_var + _cfg().second_times))
        interval_edit.setFixedWidth(44)
        grid.addWidget(interval_edit, 4, 5)

        def _chg_interval():
            cc = _cfg()
            try:
                tmp = float(interval_edit.text())
            except ValueError:
                return
            if tmp >= 0 and cc.photo_interval_var + cc.second_times != tmp:
                cc.second_times = int(tmp)
                cc.photo_interval_var = tmp - cc.second_times
                if cc.second_times > 0 and cc.photo_interval_var < 0.2:
                    cc.photo_interval_var += 1
                    cc.second_times -= 1
                _lock_screen()
                if cc.state_machine == GIF_PAGE_ID:
                    state_change_set()
                else:
                    save_config()

        interval_edit.editingFinished.connect(_chg_interval)

        # ===== 自定义内容 + 上翻/下翻（row5，col2-3） + 最大FPS（col4-5） =====
        custom_btn = QPushButton("自定义内容")
        custom_btn.setFixedWidth(84)
        custom_btn.clicked.connect(_show_custom_dialog)
        grid.addWidget(custom_btn, 5, 2)

        page_btn = QWidget()
        pbl = QHBoxLayout(page_btn)
        pbl.setContentsMargins(0, 0, 0, 0)
        pbl.setSpacing(2)
        up_btn = QPushButton("▲上翻")
        up_btn.clicked.connect(Page_UP)
        pbl.addWidget(up_btn)
        dn_btn = QPushButton("▼下翻")
        dn_btn.clicked.connect(Page_Down)
        pbl.addWidget(dn_btn)
        grid.addWidget(page_btn, 5, 3)

        grid.addWidget(QLabel("最大 FPS"), 5, 4)
        fps_edit = QLineEdit(str(_cfg().fps_var))
        fps_edit.setFixedWidth(44)
        grid.addWidget(fps_edit, 5, 5)

        def _chg_fps():
            cc = _cfg()
            try:
                val = int(fps_edit.text())
            except ValueError:
                return
            if 0 < val != cc.fps_var:
                cc.fps_var = val
                _lock_screen()
                save_config()

        fps_edit.editingFinished.connect(_chg_fps)

        # ===== 方向/页面/相机（row6） =====
        grid.addWidget(QLabel("方向:"), 6, 2)
        lcd_direction_combobox = QComboBox()
        lcd_direction_combobox.addItems(list(LCD_STATE_MESSAGE))
        lcd_direction_combobox.setMinimumWidth(90)
        lcd_direction_combobox.activated.connect(on_lcd_direction_select)
        grid.addWidget(lcd_direction_combobox, 6, 3)

        grid.addWidget(QLabel("页面:"), 6, 0)
        page_combobox = QComboBox()
        page_combobox.addItems(list(PAGE_ID.values()))
        page_combobox.setMinimumWidth(140)
        page_combobox.activated.connect(on_page_combobox_select)
        grid.addWidget(page_combobox, 6, 1)

        grid.addWidget(QLabel("相机名称"), 6, 4)
        camera_combobox = QComboBox()
        camera_combobox.setMinimumWidth(120)
        grid.addWidget(camera_combobox, 6, 5)

        def _update_camera_list():
            def _worker():
                try:
                    cams = get_all_cameras()
                except Exception:
                    cams = all_cameras
                _combo_bridge.camera_ready.emit(cams)
            threading.Thread(target=_worker, daemon=True).start()

        def _fill_camera(cams):
            camera_combobox.blockSignals(True)
            camera_combobox.clear()
            camera_combobox.addItems(list(cams.keys()))
            cc = _cfg()
            if cc.camera_var in list(cams.keys()):
                camera_combobox.setCurrentText(cc.camera_var)
            elif cams:
                camera_combobox.setCurrentText(list(cams.keys())[0])
            camera_combobox.blockSignals(False)

        _combo_bridge.camera_ready.connect(_fill_camera)

        def _update_select_camera(idx=-1):
            cc = _cfg()
            cid = camera_combobox.currentText()
            if cid != cc.camera_var:
                cc.camera_var = cid
                _lock_screen()
                if cc.state_machine == CAMERA_VIDEO_ID and dev:
                    clear_queue(dev.screen_shot_queue)
                    clear_queue(dev.screen_process_queue)
                    state_change_set()
                else:
                    save_config()

        camera_combobox.activated.connect(_update_select_camera)
        _install_popup_refresh(camera_combobox, _update_camera_list)
        QTimer.singleShot(0, _update_camera_list)

        # ===== 屏幕镜像窗口（row7，col2-5） =====
        grid.addWidget(QLabel("屏幕镜像窗口:"), 7, 2)
        windows_combobox = QComboBox()
        windows_combobox.setMinimumWidth(150)
        grid.addWidget(windows_combobox, 7, 3, 1, 3)

        def _update_windows_list():
            def _worker():
                wins = get_all_windows() if isWindows else {}
                _combo_bridge.windows_ready.emit(wins)
            threading.Thread(target=_worker, daemon=True).start()

        def _fill_windows(wins):
            global all_windows
            # 关键：把本次枚举结果同步到全局 all_windows，保证下拉框显示、
            # get_hwnd_desc 回显、_update_select_hwnd 选择查找用同一份窗口列表。
            # 否则 all_windows 是旧快照，用户选的窗口找不到会回退成桌面(0)。
            all_windows = wins
            desc = get_hwnd_desc(_cfg().select_window_hwnd)
            windows_combobox.blockSignals(True)
            windows_combobox.clear()
            windows_combobox.addItems(sorted(wins.keys(), key=str.lower))
            if desc:
                windows_combobox.setCurrentText(desc)
            windows_combobox.blockSignals(False)

        _combo_bridge.windows_ready.connect(_fill_windows)

        def _update_select_hwnd(idx=-1):
            cc = _cfg()
            sel = windows_combobox.currentText()
            hwnd, _ = all_windows.get(sel, (0, None))
            if hwnd != cc.select_window_hwnd:
                cc.select_window_hwnd = hwnd
                _lock_screen()
                if cc.state_machine == SCREEN_PAGE_ID and dev:
                    dev.screen_frame_generation += 1
                    clear_queue(dev.screen_shot_queue)
                    clear_queue(dev.screen_process_queue)
                    state_change_set()
                else:
                    save_config()

        windows_combobox.activated.connect(_update_select_hwnd)
        _install_popup_refresh(windows_combobox, _update_windows_list)
        QTimer.singleShot(0, _update_windows_list)

        # ===== 屏幕分辨率 + 检测屏幕（row8，col2-4） =====
        grid.addWidget(QLabel("屏幕分辨率:"), 8, 2)
        lcd_size_var = QComboBox()
        lcd_size_options = ['160x80 (默认)', '128x64 (0.96寸OLED)', '240x240 (1.54寸)',
                            '320x240 (2.4寸)', '240x320 (竖屏)']
        cur_size = "%dx%d (默认)" % (LCD_MAX_X, LCD_MAX_Y)
        if cur_size not in lcd_size_options:
            lcd_size_options.insert(0, cur_size)
        lcd_size_var.addItems(lcd_size_options)
        lcd_size_var.setCurrentText(cur_size)
        lcd_size_var.currentIndexChanged.connect(lambda _=0: Set_LCD_Size_Manual())
        grid.addWidget(lcd_size_var, 8, 3)
        detect_btn = QPushButton("检测屏幕")
        detect_btn.setFixedWidth(80)
        detect_btn.clicked.connect(ReDetect_LCD_Size)
        grid.addWidget(detect_btn, 8, 4)

        # ===== 实时预览（row9-10，col0-5） =====
        grid.addWidget(QLabel("实时预览:"), 9, 0, 1, 6)
        preview_w = 480
        preview_h = int(preview_w * SHOW_HEIGHT / SHOW_WIDTH)
        preview_label = QLabel()
        preview_label.setMinimumSize(preview_w, preview_h)
        preview_label.setAutoFillBackground(True)
        preview_label.setStyleSheet("background-color:#000000; border:1px solid gray;")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setScaledContents(False)  # 手动按小屏宽高比等比缩放，避免拉伸变形
        grid.addWidget(preview_label, 10, 0, 1, 6)
        grid.setRowStretch(10, 1)

        # 每屏上下文（模块级 _main_ctxs 使用）
        ctx = {
            'dev': dev,
            'page_combobox': page_combobox,
            'lcd_direction_combobox': lcd_direction_combobox,
            'camera_combobox': camera_combobox,
            'windows_combobox': windows_combobox,
            'lcd_size_var': lcd_size_var,
            'interval_var': interval_edit,
            'fps_var': fps_edit,
            'label3': Label3, 'label4': Label4, 'label5': Label5, 'label6': Label6,
            'preview_label': preview_label,
            '_preview_img': None,
        }

        def _update_preview():
            d = ctx['dev']
            cc = d.config if d.config is not None else config_obj
            if cc.preview_enabled:
                try:
                    with d._preview_lock:
                        img = d.last_preview_rgb
                    if img is not None and img.size > 0:
                        # 直接由 numpy 构造 QImage（跳过 PIL Image.fromarray+tobytes 复制），
                        # 实测 1600x900 全尺寸约 44ms→19ms，显著降低主线程负担，避免界面卡顿"点不开"
                        h, w = img.shape[:2]
                        img_c = np.ascontiguousarray(img)
                        qimg = QImage(img_c.data, w, h, img_c.strides[0],
                                      QImage.Format_RGB888).copy()
                        pix = QPixmap.fromImage(qimg)
                        # 按小屏宽高比等比缩放显示（不再拉伸变形），
                        # 使填充/适应效果与真实屏幕一致
                        try:
                            tw = preview_label.width() if preview_label.width() > 10 else preview_w
                            th = preview_label.height() if preview_label.height() > 10 else preview_h
                            pix = pix.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        except Exception:
                            pass
                        ctx['preview_label'].setPixmap(pix)
                        ctx['_preview_img'] = pix
                except Exception:
                    pass
            QTimer.singleShot(500, _update_preview)  # 200→500ms 降频，减轻主线程负担

        ctx['_update_preview'] = _update_preview
        _update_preview()

        # 初始化当前屏的页面/方向显示
        try:
            cfg = _cfg()
            page_combobox.setCurrentText(PAGE_ID.get(cfg.state_machine, ""))
            lcd_direction_combobox.setCurrentText(LCD_STATE_MESSAGE[cfg.lcd_change % len(LCD_STATE_MESSAGE)])
        except Exception:
            pass

        _main_ctxs[dev.index] = ctx
        return ctx

    def _build_settings_tab(parent, dev):
        """为一块屏创建第三层「设置」子页（值绑定该屏配置，保存时锁定本屏）。
        包含：通用 / 自动化 / 按键 / API接入 / 数据管理。"""
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(6, 6, 6, 6)
        sb = QTabWidget()
        outer.addWidget(sb)

        def _cfg():
            return dev.config if dev.config is not None else config_obj

        def _lock():
            """把全局 config_obj 锁定到本屏配置，保证 save_config 保存本屏"""
            set_active_device_config(dev)

        # ---------- 通用 ----------
        common = QWidget()
        sb.addTab(common, "  通用  ")
        common_lay = QVBoxLayout(common)

        anti_burn_cb = QCheckBox("防烧屏（每30秒微调像素位置，延缓OLED烧屏）")
        anti_burn_cb.setChecked(bool(getattr(_cfg(), "anti_burn", 0)))

        def _chg_anti_burn():
            _lock()
            config_obj.anti_burn = 1 if anti_burn_cb.isChecked() else 0
            if config_obj.anti_burn == 0:
                dev.burn_offset_x = 0
                dev.burn_offset_y = 0
            save_config()

        anti_burn_cb.toggled.connect(_chg_anti_burn)
        common_lay.addWidget(anti_burn_cb)

        preview_cb = QCheckBox("开启实时预览（显示小屏当前内容）")
        preview_cb.setChecked(bool(getattr(_cfg(), "preview_enabled", 1)))

        def _chg_preview():
            _lock()
            config_obj.preview_enabled = 1 if preview_cb.isChecked() else 0
            save_config()

        preview_cb.toggled.connect(_chg_preview)
        common_lay.addWidget(preview_cb)

        auto_start_cb = QCheckBox("开机自启动（随Windows启动）")
        auto_start_cb.setChecked(bool(getattr(_cfg(), "auto_start", 0)))

        def _chg_auto_start():
            _lock()
            config_obj.auto_start = 1 if auto_start_cb.isChecked() else 0
            if not set_auto_start(config_obj.auto_start):
                auto_start_cb.blockSignals(True)
                auto_start_cb.setChecked(False)
                auto_start_cb.blockSignals(False)
                config_obj.auto_start = 0
            save_config()

        auto_start_cb.toggled.connect(_chg_auto_start)
        common_lay.addWidget(auto_start_cb)

        lang_row = QHBoxLayout()
        common_lay.addLayout(lang_row)
        lang_row.addWidget(QLabel("界面语言:"))
        lang_combo = QComboBox()
        lang_combo.addItems(["中文", "English"])
        lang_combo.setCurrentText(getattr(_cfg(), "language", "中文"))

        def _chg_lang(idx=-1):
            _lock()
            config_obj.language = lang_combo.currentText()
            save_config()
            apply_language()

        lang_combo.currentIndexChanged.connect(_chg_lang)
        lang_row.addWidget(lang_combo)
        lang_row.addStretch(1)
        common_lay.addStretch(1)

        # ---------- 自动化 ----------
        auto = QWidget()
        sb.addTab(auto, "  自动化  ")
        auto_lay = QVBoxLayout(auto)

        cycle_cb = QCheckBox("自动翻页轮播")
        cycle_cb.setChecked(bool(getattr(_cfg(), "page_cycle_enable", 0)))

        def _chg_cycle():
            _lock()
            config_obj.page_cycle_enable = 1 if cycle_cb.isChecked() else 0
            save_config()

        cycle_cb.toggled.connect(_chg_cycle)
        auto_lay.addWidget(cycle_cb)

        cycle_row = QHBoxLayout()
        auto_lay.addLayout(cycle_row)
        cycle_row.addWidget(QLabel("轮播间隔(秒):"))
        cycle_edit = QLineEdit(str(getattr(_cfg(), "page_cycle_interval", 10)))
        cycle_edit.setFixedWidth(60)
        cycle_row.addWidget(cycle_edit)

        def _chg_cycle_interval():
            _lock()
            try:
                config_obj.page_cycle_interval = int(cycle_edit.text())
            except ValueError:
                return
            save_config()

        cycle_edit.editingFinished.connect(_chg_cycle_interval)
        cycle_row.addStretch(1)

        off_row = QHBoxLayout()
        auto_lay.addLayout(off_row)
        off_row.addWidget(QLabel("无操作息屏超时(秒, 0=禁用):"))
        off_edit = QLineEdit(str(getattr(_cfg(), "screen_off_timeout", 0)))
        off_edit.setFixedWidth(60)
        off_row.addWidget(off_edit)

        def _chg_off():
            _lock()
            try:
                config_obj.screen_off_timeout = int(off_edit.text())
            except ValueError:
                return
            save_config()

        off_edit.editingFinished.connect(_chg_off)
        off_row.addStretch(1)
        auto_lay.addStretch(1)

        # ---------- 按键 ----------
        key = QWidget()
        sb.addTab(key, "  按键  ")
        key_lay = QVBoxLayout(key)
        key_lay.addWidget(QLabel("按键动作映射（单击 / 双击 / 长按）:"))

        def _make_key_row(text, cfg_key):
            row = QHBoxLayout()
            key_lay.addLayout(row)
            row.addWidget(QLabel(text))
            combo = QComboBox()
            combo.addItems(["下翻页", "上翻页", "切换方向", "无"])
            combo.setCurrentText(getattr(_cfg(), cfg_key, "下翻页"))

            def _chg(idx=-1, k=cfg_key):
                _lock()
                setattr(config_obj, k, combo.currentText())
                save_config()

            combo.currentIndexChanged.connect(_chg)
            row.addWidget(combo)
            row.addStretch(1)

        _make_key_row("单击:", "key_single")
        _make_key_row("双击:", "key_double")
        _make_key_row("长按:", "key_long")
        key_lay.addStretch(1)

        # ---------- 页面内容 ----------
        content_page = QWidget()
        sb.addTab(content_page, "  页面内容  ")
        _build_content_settings(content_page, dev)

        # ---------- 配色方案 ----------
        scheme_page = QWidget()
        sb.addTab(scheme_page, "  配色方案  ")
        _build_scheme_settings(scheme_page, dev)

        # ---------- 监控显示 ----------
        monitor_page = QWidget()
        sb.addTab(monitor_page, "  监控显示  ")
        _build_monitor_settings(monitor_page, dev)

        # ---------- 屏幕镜像 ----------
        mirror_page = QWidget()
        sb.addTab(mirror_page, "  屏幕镜像  ")
        _build_mirror_settings(mirror_page, dev)

        # ---------- API接入 ----------
        api = QWidget()
        sb.addTab(api, "  API接入  ")
        api_lay = QVBoxLayout(api)

        api_enable_cb = QCheckBox("启用 API 投屏服务器")
        api_enable_cb.setChecked(bool(getattr(_cfg(), "api_enable", 1)))
        api_lay.addWidget(api_enable_cb)

        api_port_row = QHBoxLayout()
        api_lay.addLayout(api_port_row)
        api_port_row.addWidget(QLabel("端口:"))
        api_port_edit = QLineEdit(str(getattr(_cfg(), "api_port", 8632)))
        api_port_edit.setFixedWidth(70)
        api_port_row.addWidget(api_port_edit)
        api_port_row.addStretch(1)

        api_token_row = QHBoxLayout()
        api_lay.addLayout(api_token_row)
        api_token_row.addWidget(QLabel("访问令牌(留空=无):"))
        api_token_edit = QLineEdit(getattr(_cfg(), "api_token", ""))
        api_token_edit.setFixedWidth(160)
        api_token_row.addWidget(api_token_edit)
        api_token_row.addStretch(1)

        overlay_cb = QCheckBox("强制投屏（未选择「API投屏」页也投屏）")
        overlay_cb.setChecked(bool(getattr(_cfg(), "api_overlay", 0)))
        api_lay.addWidget(overlay_cb)

        def _restart_api():
            _lock()
            config_obj.api_enable = 1 if api_enable_cb.isChecked() else 0
            try:
                config_obj.api_port = int(api_port_edit.text())
            except ValueError:
                config_obj.api_port = 8632
            config_obj.api_token = api_token_edit.text().strip()
            config_obj.api_overlay = 1 if overlay_cb.isChecked() else 0
            save_config()
            try:
                stop_api_server()
            except Exception:
                pass
            try:
                if config_obj.api_enable:
                    start_api_server()
                    insert_text_message("API 服务器已重启（端口 %d）" % config_obj.api_port)
                else:
                    insert_text_message("API 服务器已停止")
            except Exception as e:
                insert_text_message("API 服务器启动失败: %s" % e)

        restart_btn = QPushButton("应用并重启 API 服务器")
        restart_btn.clicked.connect(_restart_api)
        api_lay.addWidget(restart_btn)
        api_lay.addWidget(QLabel("API 端口/令牌修改后点上方按钮生效。"))
        api_lay.addStretch(1)

        # ---------- 数据管理 ----------
        data = QWidget()
        sb.addTab(data, "  数据管理  ")
        data_lay = QVBoxLayout(data)
        export_btn = QPushButton("导出配置…")
        export_btn.clicked.connect(export_config)
        data_lay.addWidget(export_btn)
        import_btn = QPushButton("导入配置…")
        import_btn.clicked.connect(import_config)
        data_lay.addWidget(import_btn)
        data_lay.addWidget(QLabel("说明：导出/导入当前屏幕的完整配置（JSON），用于备份或迁移到其他电脑。"))
        data_lay.addStretch(1)

    def _build_content_settings(parent, dev):
        """设置 → 页面内容（子子页：跑马灯 / 天气与行情 / 热搜 / 时间 / 纪念日待办）"""
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(0, 0, 0, 0)
        cb = QTabWidget()
        outer.addWidget(cb)

        def _cfg():
            return dev.config if dev.config is not None else config_obj

        def _lock():
            set_active_device_config(dev)

        # ---- 文字跑马灯 ----
        marquee = QWidget()
        cb.addTab(marquee, "  文字跑马灯  ")
        ml = QVBoxLayout(marquee)
        ml.addWidget(QLabel("跑马灯文本:"))
        marquee_text = QLineEdit(getattr(_cfg(), "marquee_text", ""))
        ml.addWidget(marquee_text)
        row = QHBoxLayout()
        ml.addLayout(row)
        row.addWidget(QLabel("字号:"))
        marquee_size = QLineEdit(str(getattr(_cfg(), "marquee_font_size", 20)))
        marquee_size.setFixedWidth(50)
        row.addWidget(marquee_size)
        row.addWidget(QLabel("滚动速度(像素/帧):"))
        marquee_speed = QLineEdit(str(getattr(_cfg(), "marquee_speed", 2)))
        marquee_speed.setFixedWidth(50)
        row.addWidget(marquee_speed)
        row.addStretch(1)
        row2 = QHBoxLayout()
        ml.addLayout(row2)
        row2.addWidget(QLabel("字体颜色:"))
        marquee_color = QLineEdit(getattr(_cfg(), "marquee_color", "#ffffff"))
        marquee_color.setFixedWidth(90)
        row2.addWidget(marquee_color)

        def _pick_marquee_color():
            c = QColorDialog.getColor(QColor(marquee_color.text()), window)
            if c.isValid():
                marquee_color.setText(c.name())
                _save_marquee()

        pick_btn = QPushButton("调色板")
        pick_btn.clicked.connect(_pick_marquee_color)
        row2.addWidget(pick_btn)
        row2.addStretch(1)

        def _save_marquee():
            _lock()
            config_obj.marquee_text = marquee_text.text() or " "
            try:
                config_obj.marquee_font_size = int(marquee_size.text())
            except ValueError:
                pass
            try:
                config_obj.marquee_speed = float(marquee_speed.text())
            except ValueError:
                pass
            config_obj.marquee_color = marquee_color.text() or "#ffffff"
            save_config()

        marquee_text.editingFinished.connect(_save_marquee)
        marquee_size.editingFinished.connect(_save_marquee)
        marquee_speed.editingFinished.connect(_save_marquee)
        marquee_color.editingFinished.connect(_save_marquee)
        ml.addStretch(1)

        # ---- 天气与行情 ----
        net = QWidget()
        cb.addTab(net, "  天气与行情  ")
        nl = QVBoxLayout(net)

        def _entry_row(label, key, width, default):
            r = QHBoxLayout()
            nl.addLayout(r)
            r.addWidget(QLabel(label))
            e = QLineEdit(str(getattr(_cfg(), key, default)))
            e.setFixedWidth(width)
            r.addWidget(e)
            r.addStretch(1)

            def _save(k=key):
                _lock()
                setattr(config_obj, k, e.text().strip())
                save_config()

            e.editingFinished.connect(_save)
            return e

        _entry_row("天气城市:", "weather_city", 16, "Beijing")
        _entry_row("行情交易对:", "crypto_symbols", 24, "BTCUSDT,ETHUSDT")
        _entry_row("延迟测试目标:", "ping_host", 16, "223.5.5.5")
        nl.addWidget(QLabel("支持中文城市名，如 北京 或 Beijing"))
        nl.addStretch(1)

        # ---- 热搜 ----
        hot = QWidget()
        cb.addTab(hot, "  热搜  ")
        hl = QVBoxLayout(hot)

        def _spin_row(label, key, default, suffix=""):
            r = QHBoxLayout()
            hl.addLayout(r)
            r.addWidget(QLabel(label))
            e = QLineEdit(str(getattr(_cfg(), key, default)))
            e.setFixedWidth(50)
            r.addWidget(e)
            if suffix:
                r.addWidget(QLabel(suffix))
            r.addStretch(1)

            def _save(k=key):
                _lock()
                try:
                    setattr(config_obj, k, int(e.text()))
                except ValueError:
                    pass
                save_config()

            e.editingFinished.connect(_save)
            return e

        def _cb_row(label, key):
            r = QHBoxLayout()
            hl.addLayout(r)
            ck = QCheckBox(label)
            ck.setChecked(bool(getattr(_cfg(), key, 0)))
            r.addWidget(ck)
            r.addStretch(1)

            def _save(k=key):
                _lock()
                setattr(config_obj, k, 1 if ck.isChecked() else 0)
                save_config()

            ck.toggled.connect(_save)
            return ck

        _spin_row("每页显示条数:", "hotsearch_count", 3)
        _spin_row("抓取总条数:", "hotsearch_total", 10, "(多于每页条数时自动翻页)")
        _cb_row("字体自动适配屏幕", "hotsearch_font_auto")
        _spin_row("手动字号:", "hotsearch_font_size", 12)
        _cb_row("长文本自动滚动字幕", "hotsearch_scroll_enable")
        _spin_row("滚动速度:", "hotsearch_scroll_speed", 2)
        _spin_row("翻页间隔(秒):", "hotsearch_page_interval", 3)
        _cb_row("自动刷新", "hotsearch_auto_refresh")
        _spin_row("刷新间隔(秒):", "hotsearch_interval", 60)
        hl.addStretch(1)

        # ---- 时间 ----
        t = QWidget()
        cb.addTab(t, "  时间  ")
        tl = QVBoxLayout(t)
        r = QHBoxLayout()
        tl.addLayout(r)
        r.addWidget(QLabel("番茄钟时长(分钟):"))
        timer_edit = QLineEdit(str(getattr(_cfg(), "timer_minutes", 25)))
        timer_edit.setFixedWidth(50)
        r.addWidget(timer_edit)
        r.addStretch(1)

        def _save_timer():
            _lock()
            try:
                config_obj.timer_minutes = int(timer_edit.text())
            except ValueError:
                pass
            save_config()

        timer_edit.editingFinished.connect(_save_timer)
        tl.addWidget(QLabel("世界时钟时区（每项：名称|UTC偏移，逗号分隔）:"))
        zones_edit = QLineEdit(getattr(_cfg(), "clock_zones", "北京|8"))
        tl.addWidget(zones_edit)

        def _save_zones():
            _lock()
            config_obj.clock_zones = zones_edit.text().strip() or "北京|8"
            save_config()

        zones_edit.editingFinished.connect(_save_zones)
        tl.addWidget(QLabel("例：北京|8,伦敦|0,纽约|-5,东京|9"))
        tl.addStretch(1)

        # ---- 纪念日/待办 ----
        lst = QWidget()
        cb.addTab(lst, "  纪念日/待办  ")
        ll = QVBoxLayout(lst)
        ll.addWidget(QLabel("纪念日（每行一项：名称|月-日，如 生日|01-01）:"))
        memo_edit = QPlainTextEdit()
        memo_edit.setPlainText("\n".join(getattr(_cfg(), "memo_items", [])))
        ll.addWidget(memo_edit)
        ll.addWidget(QLabel("待办事项（每行一项）:"))
        todo_edit = QPlainTextEdit()
        todo_edit.setPlainText("\n".join(getattr(_cfg(), "todo_items", [])))
        ll.addWidget(todo_edit)

        def _save_lists():
            _lock()
            config_obj.memo_items = [l for l in memo_edit.toPlainText().split("\n") if l.strip()]
            config_obj.todo_items = [l for l in todo_edit.toPlainText().split("\n") if l.strip()]
            save_config()

        memo_edit.textChanged.connect(_save_lists)
        todo_edit.textChanged.connect(_save_lists)

    def _build_mirror_settings(parent, dev):
        """设置 → 屏幕镜像（镜像局部放大跟随鼠标）"""
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(6, 6, 6, 6)

        def _cfg():
            return dev.config if dev.config is not None else config_obj

        def _lock():
            set_active_device_config(dev)

        zoom_cb = QCheckBox("镜像局部放大（跟随鼠标）")
        zoom_cb.setChecked(bool(getattr(_cfg(), "zoom_enable", 0)))

        def _chg_zoom():
            _lock()
            config_obj.zoom_enable = 1 if zoom_cb.isChecked() else 0
            save_config()

        zoom_cb.toggled.connect(_chg_zoom)
        outer.addWidget(zoom_cb)
        row = QHBoxLayout()
        outer.addLayout(row)
        row.addWidget(QLabel("放大倍数:"))
        zoom_edit = QLineEdit(str(getattr(_cfg(), "zoom_scale", 2)))
        zoom_edit.setFixedWidth(50)
        row.addWidget(zoom_edit)
        row.addStretch(1)

        def _save_zoom():
            _lock()
            try:
                config_obj.zoom_scale = int(zoom_edit.text())
            except ValueError:
                pass
            save_config()

        zoom_edit.editingFinished.connect(_save_zoom)
        outer.addStretch(1)

    def _build_scheme_settings(parent, dev):
        """设置 → 配色方案：方案选择 + 预览 + 新增/编辑/删除自定义方案"""
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(6, 6, 6, 6)

        def _cfg():
            return dev.config if dev.config is not None else config_obj

        def _lock():
            set_active_device_config(dev)

        outer.addWidget(QLabel("选择配色方案预览；内置方案只读，可新增/编辑/删除自定义方案："))
        row = QHBoxLayout()
        outer.addLayout(row)
        row.addWidget(QLabel("方案:"))
        scheme_combo = QComboBox()
        scheme_combo.setMinimumWidth(200)
        row.addWidget(scheme_combo)
        row.addStretch(1)

        preview = QWidget()
        preview.setFixedHeight(28)
        preview.setStyleSheet("border:1px solid gray; background:white;")
        outer.addWidget(preview)

        def _draw_preview():
            schemes = get_all_color_schemes(config_obj)
            colors = schemes.get(scheme_combo.currentText(), []) or []
            if len(colors) >= 2:
                preview.setStyleSheet(
                    "border:1px solid gray; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                    "stop:0 %s, stop:0.5 %s, stop:1 %s);" % (colors[0], colors[len(colors) // 2], colors[-1]))
            elif len(colors) == 1:
                preview.setStyleSheet("border:1px solid gray; background:%s;" % colors[0])
            else:
                preview.setStyleSheet("border:1px solid gray; background:white;")

        def _refresh_schemes():
            schemes = get_all_color_schemes(config_obj)
            names = list(schemes.keys())
            cur = scheme_combo.currentText()
            scheme_combo.blockSignals(True)
            scheme_combo.clear()
            scheme_combo.addItems(names)
            scheme_combo.blockSignals(False)
            if cur in names:
                scheme_combo.setCurrentText(cur)
            elif names:
                scheme_combo.setCurrentText(names[0])
            _draw_preview()

        scheme_combo.currentIndexChanged.connect(lambda _: _draw_preview())

        def _scheme_dialog(title, name="", colors_text=""):
            dlg = QDialog(window)
            dlg.setWindowTitle(title)
            dlg.setModal(True)
            v = QVBoxLayout(dlg)
            v.addWidget(QLabel("方案名称:"))
            name_edit = QLineEdit(name)
            v.addWidget(name_edit)
            v.addWidget(QLabel("颜色列表（#rrggbb，逗号分隔）:"))
            colors_edit = QLineEdit(colors_text)
            v.addWidget(colors_edit)
            v.addWidget(QLabel("示例：#ffb3ba,#baffc9,#bae1ff,#ddbaff,#ffd6ba,#ffffba"))
            btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            v.addWidget(btns)
            btns.accepted.connect(dlg.accept)
            btns.rejected.connect(dlg.reject)
            if dlg.exec() == QDialog.Accepted:
                return {"name": name_edit.text().strip(), "colors": colors_edit.text().strip()}
            return None

        def add_custom_scheme():
            res = _scheme_dialog("新增配色方案")
            if not res or not res.get("name"):
                return
            colors = parse_color_list(res.get("colors", ""))
            if not colors:
                insert_text_message("新增失败：颜色列表为空或格式不正确")
                return
            _lock()
            config_obj.custom_color_schemes = config_obj.custom_color_schemes or {}
            config_obj.custom_color_schemes[res["name"]] = colors
            save_config()
            scheme_combo.setCurrentText(res["name"])
            _refresh_schemes()
            insert_text_message("已保存新配色方案：%s" % res["name"])

        def edit_custom_scheme():
            name = scheme_combo.currentText()
            if name in BUILTIN_COLOR_SCHEMES:
                insert_text_message("内置方案不可编辑")
                return
            custom = getattr(config_obj, "custom_color_schemes", {}) or {}
            res = _scheme_dialog("编辑配色方案", name, ",".join(custom.get(name, [])))
            if not res or not res.get("name"):
                return
            colors = parse_color_list(res.get("colors", ""))
            if not colors:
                insert_text_message("保存失败：颜色列表为空或格式不正确")
                return
            _lock()
            config_obj.custom_color_schemes = config_obj.custom_color_schemes or {}
            if res["name"] != name and name in config_obj.custom_color_schemes:
                del config_obj.custom_color_schemes[name]
            config_obj.custom_color_schemes[res["name"]] = colors
            save_config()
            scheme_combo.setCurrentText(res["name"])
            _refresh_schemes()
            insert_text_message("已保存配色方案：%s" % res["name"])

        def del_custom_scheme():
            name = scheme_combo.currentText()
            if name in BUILTIN_COLOR_SCHEMES:
                insert_text_message("内置方案不可删除")
                return
            if QMessageBox.question(window, "删除配色方案", "确定删除「%s」？" % name) != QMessageBox.Yes:
                return
            _lock()
            config_obj.custom_color_schemes = config_obj.custom_color_schemes or {}
            config_obj.custom_color_schemes.pop(name, None)
            save_config()
            _refresh_schemes()
            insert_text_message("已删除配色方案：%s" % name)

        btn_row = QHBoxLayout()
        outer.addLayout(btn_row)
        for text, fn in (("新增方案", add_custom_scheme), ("编辑当前", edit_custom_scheme), ("删除当前", del_custom_scheme)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            btn_row.addWidget(b)
        btn_row.addWidget(QLabel("（内置方案只读）"))
        btn_row.addStretch(1)
        _refresh_schemes()

    def _build_monitor_settings(parent, dev):
        """设置 → 监控显示（进程 / 硬件详情 / 仪表盘 / 磁盘读写 / 网络流量）"""
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(0, 0, 0, 0)
        mb = QTabWidget()
        outer.addWidget(mb)

        def _cfg():
            return dev.config if dev.config is not None else config_obj

        def _lock():
            set_active_device_config(dev)

        # ---- 进程 ----
        proc = QWidget()
        mb.addTab(proc, "  进程  ")
        pl = QVBoxLayout(proc)
        r = QHBoxLayout()
        pl.addLayout(r)
        r.addWidget(QLabel("进程TOP显示数量:"))
        proc_edit = QLineEdit(str(getattr(_cfg(), "proc_count", 10)))
        proc_edit.setFixedWidth(50)
        r.addWidget(proc_edit)
        r.addStretch(1)

        def _save_proc():
            _lock()
            try:
                config_obj.proc_count = int(proc_edit.text())
            except ValueError:
                pass
            save_config()

        proc_edit.editingFinished.connect(_save_proc)
        pl.addStretch(1)

        # ---- 硬件详情 ----
        hw = QWidget()
        mb.addTab(hw, "  硬件详情  ")
        hl = QVBoxLayout(hw)
        r = QHBoxLayout()
        hl.addLayout(r)
        r.addWidget(QLabel("硬件详情显示数量:"))
        hw_edit = QLineEdit(str(getattr(_cfg(), "hwdetail_max", 10)))
        hw_edit.setFixedWidth(50)
        r.addWidget(hw_edit)
        r.addStretch(1)

        def _save_hw():
            _lock()
            try:
                config_obj.hwdetail_max = int(hw_edit.text())
            except ValueError:
                pass
            save_config()

        hw_edit.editingFinished.connect(_save_hw)
        hl.addWidget(QLabel("硬件详情监控类型:"))
        types_row = QHBoxLayout()
        hl.addLayout(types_row)
        hw_types = ("Temperature", "Fan", "Voltage", "Load", "Power")
        hw_types_state = {}
        for t in hw_types:
            ck = QCheckBox(t)
            ck.setChecked(t in (getattr(_cfg(), "hwdetail_types", "") or "").split(","))
            hw_types_state[t] = ck

            def _save_type(k=t):
                _lock()
                sel = [tt for tt, cc in hw_types_state.items() if cc.isChecked()]
                config_obj.hwdetail_types = ",".join(sel) or "Temperature"
                save_config()

            ck.toggled.connect(_save_type)
            types_row.addWidget(ck)
        types_row.addStretch(1)
        hl.addStretch(1)

        # ---- 仪表盘 ----
        gauge = QWidget()
        mb.addTab(gauge, "  仪表盘  ")
        gl = QVBoxLayout(gauge)
        gl.addWidget(QLabel("仪表盘显示项目与颜色（多于一页自动翻页）:"))
        gauge_items = [
            ("CPU", "gauge_show_cpu", "gauge_cpu_color"),
            ("内存", "gauge_show_mem", "gauge_mem_color"),
            ("磁盘", "gauge_show_disk", "gauge_disk_color"),
            ("CPU温度", "gauge_show_cpu_temp", "gauge_cpu_temp_color"),
            ("GPU", "gauge_show_gpu", "gauge_gpu_color"),
            ("GPU温度", "gauge_show_gpu_temp", "gauge_gpu_temp_color"),
            ("风扇", "gauge_show_fan", "gauge_fan_color"),
            ("上传", "gauge_show_upload", "gauge_upload_color"),
            ("下载", "gauge_show_download", "gauge_download_color"),
        ]

        def _save_gauge():
            _lock()
            for _label, show_key, color_key in gauge_items:
                setattr(config_obj, show_key, gauge_state[show_key])
                setattr(config_obj, color_key, gauge_state[color_key])
            save_config()

        gauge_state = {}
        for label, show_key, color_key in gauge_items:
            grow = QHBoxLayout()
            gl.addLayout(grow)
            ck = QCheckBox(label)
            ck.setChecked(bool(getattr(_cfg(), show_key, 0)))
            gauge_state[show_key] = 1 if ck.isChecked() else 0
            grow.addWidget(ck)
            color_edit = QLineEdit(getattr(_cfg(), color_key, "#ff8000"))
            color_edit.setFixedWidth(80)
            gauge_state[color_key] = color_edit.text()
            grow.addWidget(color_edit)

            def _pick_color(ce):
                c = QColorDialog.getColor(QColor(ce.text()), window)
                if c.isValid():
                    ce.setText(c.name())
                    _save_gauge()

            pick_btn = QPushButton("颜色")
            pick_btn.clicked.connect(lambda _=False, ce=color_edit: _pick_color(ce))
            grow.addWidget(pick_btn)
            grow.addStretch(1)

            def _on_toggled(val, k=show_key):
                gauge_state[k] = 1 if val else 0
                _save_gauge()

            def _on_color(k=color_key, ce=color_edit):
                gauge_state[k] = ce.text()
                _save_gauge()

            ck.toggled.connect(_on_toggled)
            color_edit.editingFinished.connect(_on_color)
        gl.addStretch(1)

        # ---- 磁盘读写 ----
        disk = QWidget()
        mb.addTab(disk, "  磁盘读写  ")
        dl = QVBoxLayout(disk)
        mode_row = QHBoxLayout()
        dl.addLayout(mode_row)
        mode_row.addWidget(QLabel("显示模式:"))
        disk_mode = QComboBox()
        disk_mode.addItems(["经典", "经典2", "网速样式"])
        disk_mode.setCurrentText(getattr(_cfg(), "diskio_mode", "经典"))
        mode_row.addWidget(disk_mode)
        mode_row.addWidget(QLabel("（经典2样式自动跟随网络流量配色，无需单独配置）"))
        mode_row.addStretch(1)
        dn = QTabWidget()
        dl.addWidget(dn)

        def _disk_color_row(lay, label, key):
            row = QHBoxLayout()
            lay.addLayout(row)
            row.addWidget(QLabel(label))
            e = QLineEdit(getattr(_cfg(), key, "#ffffff"))
            e.setFixedWidth(80)
            row.addWidget(e)

            def _pick(ce):
                c = QColorDialog.getColor(QColor(ce.text()), window)
                if c.isValid():
                    ce.setText(c.name())
                    _save_disk(key, ce.text())

            b = QPushButton("颜色")
            b.clicked.connect(lambda _=False, ce=e: _pick(ce))
            row.addWidget(b)
            row.addStretch(1)

            def _save(k=key, ce=e):
                _lock()
                setattr(config_obj, k, ce.text())
                save_config()

            e.editingFinished.connect(lambda k=key, ce=e: _save(k, ce))

        def _save_disk(k, v):
            _lock()
            setattr(config_obj, k, v)
            save_config()

        classic = QWidget()
        dn.addTab(classic, "  经典模式  ")
        cl = QVBoxLayout(classic)
        _disk_color_row(cl, "标题颜色:", "diskio_title_color")
        _disk_color_row(cl, "读 颜色:", "diskio_read_color")
        _disk_color_row(cl, "写 颜色:", "diskio_write_color")
        cl.addStretch(1)

        netspeed_tab = QWidget()
        dn.addTab(netspeed_tab, "  网速样式  ")
        nsl = QVBoxLayout(netspeed_tab)
        _disk_color_row(nsl, "标签颜色:", "diskio_label_color")
        _disk_color_row(nsl, "读数值颜色:", "diskio_value_read_color")
        _disk_color_row(nsl, "写数值颜色:", "diskio_value_write_color")
        _disk_color_row(nsl, "读柱颜色:", "diskio_bar1_color")
        _disk_color_row(nsl, "写柱颜色:", "diskio_bar2_color")
        nsl.addStretch(1)

        def _save_disk_mode():
            _lock()
            config_obj.diskio_mode = disk_mode.currentText()
            save_config()

        disk_mode.currentIndexChanged.connect(lambda _: _save_disk_mode())

        # ---- 网络流量 ----
        net = QWidget()
        mb.addTab(net, "  网络流量  ")
        nl = QVBoxLayout(net)
        net_mode_row = QHBoxLayout()
        nl.addLayout(net_mode_row)
        net_mode_row.addWidget(QLabel("显示模式:"))
        netspeed_mode = QComboBox()
        netspeed_mode.addItems(["经典", "自定义"])
        netspeed_mode.setCurrentText(getattr(_cfg(), "netspeed_mode", "经典"))
        net_mode_row.addWidget(netspeed_mode)
        net_mode_row.addWidget(QLabel("（经典=修改前样式，自定义=全部颜色独立）"))
        net_mode_row.addStretch(1)
        for label, key in (("上传文字颜色:", "netspeed_up_color"),
                           ("下载文字颜色:", "netspeed_down_color"),
                           ("上传柱颜色:", "netspeed_bar1_color"),
                           ("下载柱颜色:", "netspeed_bar2_color")):
            row = QHBoxLayout()
            nl.addLayout(row)
            row.addWidget(QLabel(label))
            e = QLineEdit(getattr(_cfg(), key, "#ff8000"))
            e.setFixedWidth(80)
            row.addWidget(e)

            def _pick(ce, k=key):
                c = QColorDialog.getColor(QColor(ce.text()), window)
                if c.isValid():
                    ce.setText(c.name())
                    _save_netspeed(k, ce.text())

            b = QPushButton("颜色")
            b.clicked.connect(lambda _=False, ce=e: _pick(ce))
            row.addWidget(b)
            row.addStretch(1)

            def _save(k=key, ce=e):
                _lock()
                setattr(config_obj, k, ce.text())
                save_config()

            e.editingFinished.connect(lambda k=key, ce=e: _save(k, ce))

        def _save_netspeed(k, v):
            _lock()
            setattr(config_obj, k, v)
            save_config()

        def _save_netspeed_mode():
            _lock()
            config_obj.netspeed_mode = netspeed_mode.currentText()
            save_config()

        netspeed_mode.currentIndexChanged.connect(lambda _: _save_netspeed_mode())
        nl.addStretch(1)

    def _build_hw_tab(parent, dev):
        """第三层「设备信息」子页：连接信息 / SFR寄存器 / Flash芯片 / Flash分区 / 系统信息"""
        outer = QVBoxLayout(parent)
        outer.setContentsMargins(6, 6, 6, 6)
        hw_nb = QTabWidget()
        outer.addWidget(hw_nb)

        conn_page = QWidget()
        hw_nb.addTab(conn_page, "  连接信息  ")
        sfr_page = QWidget()
        hw_nb.addTab(sfr_page, "  SFR寄存器  ")
        flash_page = QWidget()
        hw_nb.addTab(flash_page, "  Flash芯片  ")
        parts_page = QWidget()
        hw_nb.addTab(parts_page, "  Flash分区  ")
        sys_page = QWidget()
        hw_nb.addTab(sys_page, "  系统信息  ")

        def _make_form(page):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            form = QFormLayout(content)
            form.setContentsMargins(8, 8, 8, 8)
            scroll.setWidget(content)
            lay = QVBoxLayout(page)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(scroll)
            return form

        conn_form = _make_form(conn_page)
        sfr_form = _make_form(sfr_page)
        flash_form = _make_form(flash_page)
        parts_form = _make_form(parts_page)
        sys_form = _make_form(sys_page)

        def _clear_form(form):
            while form.rowCount() > 0:
                form.removeRow(0)

        def _add_row(form, label, value):
            try:
                l = QLabel(label)
                l.setStyleSheet("color:gray;")
                v = QLabel(value)
                v.setTextInteractionFlags(Qt.TextSelectableByMouse)
                form.addRow(l, v)
            except Exception:
                pass

        # Flash 布局（内置默认，与原版一致）
        _flash_default = {
            "chip": "P25D80", "capacity": "1024KB", "page_size": "256B", "total_pages": 4096,
            "allocations": {
                "gif_frames": {"start_page": 0, "pages": 3600, "count": 36, "description": "36张动图, 每张100页"},
                "demo_image": {"start_page": 3600, "pages": 29, "description": "240x240单色Demo1"},
                "digit_font_48x66": {"start_page": 3629, "pages": 22, "description": "48x66数码管字体N48X66P"},
                "clock_font_asc64": {"start_page": 3651, "pages": 128, "description": "32x64 ASCII字体ASC64"},
                "logo": {"start_page": 3779, "pages": 12, "description": "240x102单色LOGO"},
                "j1_image": {"start_page": 3791, "pages": 29, "description": "240x240单色J1"},
                "mlogo": {"start_page": 3820, "pages": 6, "description": "160x68单色MLOGO"},
                "clock_background": {"start_page": 3826, "pages": 100, "description": "160x80彩色时钟背景CLK_BG"},
                "photo_album": {"start_page": 3926, "pages": 100, "description": "160x80彩色相册图像PH1"},
                "state_font_24x33": {"start_page": 4026, "pages": 12, "description": "24x33状态页数码管字体N24X33P"},
                "state_background": {"start_page": 4038, "pages": 7, "description": "160x80状态页背景MP1"},
            },
        }

        def _load_flash_layout():
            try:
                with open(_get_resource("device_protocol.json"), "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("flash_layout") or _flash_default
            except Exception:
                return _flash_default

        _sfr_type_names = ["u8地址", "u16地址", "u32地址", "字符串", "数组"]

        def _sfr_addr_str(entry):
            try:
                data_type = entry.family[0] // 32
                length = entry.family[0] % 32
                if data_type == 0:
                    return "0x%04X(%d字节)" % (entry.data[0] * 256 + entry.data[1], length)
                elif data_type == 1:
                    return "0x%02X" % entry.data[0]
                elif data_type == 2:
                    return "0x%04X(%d字节)" % (entry.data[0] * 256 + entry.data[1], length)
            except Exception:
                pass
            return "-"

        def _read_sfr_value(entry):
            try:
                data_type = entry.family[0] // 32
                if data_type == 0:
                    return Read_M_u8(entry.data[0] * 256 + entry.data[1])
                elif data_type == 1:
                    return Read_M_u16(entry.data[0])
                elif data_type == 2:
                    addr = entry.data[0] * 256 + entry.data[1]
                    val = 0
                    for n in range(entry.family[0] % 32):
                        val = (val << 8) | Read_M_u8(addr + n)
                    return val
                elif data_type == 3:
                    return entry.data.decode("utf-8", errors="replace")
                elif data_type == 4:
                    return " ".join("%02X" % b for b in entry.data)
            except Exception:
                return None
            return None

        def refresh_hw_info():
            for form in (conn_form, sfr_form, flash_form, parts_form, sys_form):
                _clear_form(form)
            _add_row(conn_form, "读取中", "请稍候…")

            # 跨线程桥：后台线程结果经信号回主线程填充
            # （QTimer.singleShot(0,...) 在后台线程不触发，会导致设备信息一直空白）
            class _HwBridge(QObject):
                ready = Signal(object)

            _hw_bridge = _HwBridge()
            _keepalive.append(_hw_bridge)  # 防 GC

            def _collect():
                d = dev
                usb = getattr(d, "usb_info", {}) if d is not None else {}
                fw = getattr(d, "firmware_version", 0) if d is not None else 0
                connected = (d is not None and d.ser is not None and d.ser.is_open)
                sfr_rows = []
                sfr = getattr(d, "msn_data", None) if d is not None else None
                if sfr:
                    for entry in sfr:
                        try:
                            name = entry.name.decode("utf-8", errors="replace")
                        except Exception:
                            name = "?"
                        try:
                            dtype = _sfr_type_names[entry.family[0] // 32]
                        except Exception:
                            dtype = "?"
                        addr = _sfr_addr_str(entry)
                        val = _read_sfr_value(entry) if connected else None
                        val_str = "-" if val is None else str(val)
                        sfr_rows.append((name, "%s %s = %s" % (dtype, addr, val_str)))
                import platform
                sys_rows = [
                    ("操作系统", platform.platform()),
                    ("电脑名", platform.node()),
                    ("架构", platform.machine()),
                    ("CPU型号", platform.processor() or "未知"),
                ]
                try:
                    sys_rows.append(("CPU核心",
                                     "%d物理 / %d逻辑" % (psutil.cpu_count(logical=False) or 0, psutil.cpu_count(logical=True) or 0)))
                except Exception:
                    pass
                try:
                    freq = psutil.cpu_freq()
                    if freq and freq.current:
                        sys_rows.append(("CPU频率", "%.1f GHz" % (freq.current / 1000)))
                except Exception:
                    pass
                try:
                    sys_rows.append(("内存", "%.1f GB" % (psutil.virtual_memory().total / (1024 ** 3))))
                except Exception:
                    pass
                try:
                    batt = psutil.sensors_battery()
                    if batt:
                        sys_rows.append(("电池", "%d%%" % batt.percent))
                except Exception:
                    pass
                sys_rows.append(("Python", sys.version.split()[0]))
                flash = _load_flash_layout()
                return usb, fw, connected, sfr_rows, sys_rows, flash

            def _apply(result):
                try:
                    usb, fw, connected, sfr_rows, sys_rows, flash = result
                    for form in (conn_form, sfr_form, flash_form, parts_form, sys_form):
                        _clear_form(form)
                    _add_row(conn_form, "连接状态", "已连接" if connected else "未连接")
                    _add_row(conn_form, "端口", usb.get("port") or "-")
                    _add_row(conn_form, "序列号(SN)", usb.get("serial_number") or "-")
                    _add_row(conn_form, "VID", usb.get("vid") or "-")
                    _add_row(conn_form, "PID", usb.get("pid") or "-")
                    _add_row(conn_form, "制造商", usb.get("manufacturer") or "-")
                    _add_row(conn_form, "产品", usb.get("product") or "-")
                    _add_row(conn_form, "名称", usb.get("name") or "-")
                    _add_row(conn_form, "描述", usb.get("description") or "-")
                    _add_row(conn_form, "接口", usb.get("interface") or "-")
                    _add_row(conn_form, "硬件ID", usb.get("hwid") or "-")
                    _add_row(conn_form, "位置", usb.get("location") or "-")
                    _add_row(conn_form, "固件版本", ("v%d" % fw) if fw else "-")
                    if sfr_rows:
                        _add_row(sfr_form, "变量名", "类型 / 地址 / 当前值")
                        for name, row in sfr_rows:
                            _add_row(sfr_form, name, row)
                    else:
                        _add_row(sfr_form, "SFR数据", "未获取（设备未连接）")
                    _add_row(flash_form, "Flash芯片", flash.get("chip") or "-")
                    _add_row(flash_form, "容量", flash.get("capacity") or "-")
                    _add_row(flash_form, "页大小", flash.get("page_size") or "-")
                    _add_row(flash_form, "总页数", str(flash.get("total_pages") or "-"))
                    allocs = flash.get("allocations") or {}
                    if allocs:
                        for name, info in allocs.items():
                            start = info.get("start_page", "?")
                            pages = info.get("pages", "?")
                            desc = info.get("description", "")
                            _add_row(parts_form, name, "页 %s（共%s页）%s" % (start, pages, desc))
                    for label, val in sys_rows:
                        _add_row(sys_form, label, val)
                except Exception:
                    pass

            _hw_bridge.ready.connect(_apply)

            def _worker():
                try:
                    _result = _collect()
                except Exception:
                    _result = None
                if _result is not None:
                    _hw_bridge.ready.emit(_result)

            threading.Thread(target=_worker, daemon=True).start()

        btn_row = QHBoxLayout()
        outer.addLayout(btn_row)
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(80)
        refresh_btn.clicked.connect(refresh_hw_info)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(QLabel("连接信息在设备连接成功时采集；未连接或显示“-”属正常"))
        btn_row.addStretch(1)
        refresh_hw_info()

    # 防 GC 容器：后台线程回调用的跨线程桥等对象（避免被垃圾回收导致信号失效）
    _keepalive = []

    # 每屏 inner_notebook 的懒加载状态（设置/设备信息首次点开才构建，减少启动卡顿）
    _inner_notebooks = {}

    def _on_inner_tab_changed(did, nb, idx):
        """用户切换到某屏的设置/设备信息子页时，若未构建则首次构建"""
        try:
            rec = _inner_notebooks.get(did)
            if rec is None:
                return
            dev = all_devices.get(did)
            if dev is None:
                return
            if idx == 1 and not rec["settings"]:
                rec["settings"] = True
                _build_settings_tab(nb.widget(1), dev)
            elif idx == 2 and not rec["hw"]:
                rec["hw"] = True
                _build_hw_tab(nb.widget(2), dev)
        except Exception:
            pass

    def _rebuild_main_tabs():
        """根据已连接设备重建主控多标签（保留已有屏的上下文）。
        每个屏幕标签 = 第三层「主控|设置|设备信息」三页（设置/设备信息懒加载）。"""
        global _active_main_dev_id
        connected = [d for d in all_devices.values() if d.device_state == 1]
        if not connected:
            connected = [_primary_device] if _primary_device is not None else []
        # 移除已断开的设备标签
        for did in list(_main_ctxs.keys()):
            if not any(d.index == did for d in connected):
                for i in range(main_notebook.count()):
                    w = main_notebook.widget(i)
                    if w is not None and w.property("dev_index") == did:
                        main_notebook.removeTab(i)
                        break
                _main_ctxs.pop(did, None)
                _inner_notebooks.pop(did, None)
        # 为新连接设备创建标签（每屏一个外层标签，内含 主控|设置|设备信息）
        for d in connected:
            if d.index not in _main_ctxs:
                screen_tab = QWidget()
                screen_tab.setProperty("dev_index", d.index)
                lay = QVBoxLayout(screen_tab)
                lay.setContentsMargins(0, 0, 0, 0)
                inner_nb = QTabWidget()
                lay.addWidget(inner_nb)
                main_page = QWidget()
                inner_nb.addTab(main_page, "  主控  ")
                _build_main_tab(main_page, d)
                settings_page = QWidget()
                inner_nb.addTab(settings_page, "  设置  ")
                hw_page = QWidget()
                inner_nb.addTab(hw_page, "  设备信息  ")
                main_notebook.addTab(screen_tab, d.device_name)
                _inner_notebooks[d.index] = {"settings": False, "hw": False}
                inner_nb.currentChanged.connect(
                    lambda idx, nb=inner_nb, did=d.index: _on_inner_tab_changed(did, nb, idx))
        # 同步当前选中标签与活跃设备
        try:
            cur = main_notebook.currentIndex()
            items = list(_main_ctxs.keys())
            if 0 <= cur < len(items):
                _active_main_dev_id = items[cur]
        except Exception:
            pass

    def _main_tab_for_dev_index(did):
        for i in range(main_notebook.count()):
            if main_notebook.widget(i).property("dev_index") == did:
                return i
        return -1

    def _select_main_tab(did):
        """联动：切换到指定设备的主控标签"""
        global _active_main_dev_id
        idx = _main_tab_for_dev_index(did)
        if idx >= 0:
            try:
                main_notebook.setCurrentIndex(idx)
            except Exception:
                pass
            _active_main_dev_id = did

    def _on_main_tab_changed(index):
        """联动：用户点击屏幕标签时，同步活跃设备（用 tab 的 dev_index 直接映射，避免顺序错位）"""
        try:
            w = main_notebook.widget(index) if 0 <= index < main_notebook.count() else None
            if w is not None:
                did = w.property("dev_index")
                dev = next((d for d in all_devices.values()
                            if d.index == did and d.device_state == 1), None)
                if dev is not None:
                    _activate_by_name(dev.device_name)
        except Exception:
            pass

    main_notebook.currentChanged.connect(_on_main_tab_changed)
    _rebuild_main_tabs()

    # ==================== 联动 ====================
    _syncing_screen_tabs = False

    def _activate_by_name(name):
        """按设备名切换活跃屏，并同步主控标签与下拉框"""
        global _primary_device, _active_main_dev_id
        nonlocal _syncing_screen_tabs  # _syncing_screen_tabs 定义在 UI_Page 内，须用 nonlocal（原 global 会 NameError 且被吞掉）
        if _syncing_screen_tabs:
            return
        _syncing_screen_tabs = True
        try:
            for dev in all_devices.values():
                if dev.device_name == name and dev.device_state == 1:
                    old = _primary_device
                    if old is not None and old != dev:
                        if old.config is not None:
                            old.config.state_machine = old.state_machine
                        else:
                            old.state_machine = config_obj.state_machine
                    set_current_device(dev)
                    _primary_device = dev
                    set_active_device_config(dev)
                    if dev.config is not None:
                        dev.config.state_machine = getattr(dev, "state_machine", SCREEN_PAGE_ID)
                    try:
                        device_selector.blockSignals(True)
                        device_selector.setCurrentText(dev.device_name)
                        device_selector.blockSignals(False)
                    except Exception:
                        pass
                    try:
                        _select_main_tab(dev.index)
                    except Exception:
                        pass
                    return True
            return False
        finally:
            _syncing_screen_tabs = False

    # ==================== 电视墙（第一层：中控 | 电视墙 | 关于） ====================
    wall_tab = QWidget()
    top_nb.addTab(wall_tab, "  电视墙  ")
    wall_lay = QVBoxLayout(wall_tab)
    wall_lay.setContentsMargins(4, 4, 4, 4)
    wall_nb = QTabWidget()
    wall_lay.addWidget(wall_nb)

    # ---------- 显示墙页（所有小屏实时预览，按设置的行×列排布） ----------
    wall_view_page = QWidget()
    wall_nb.addTab(wall_view_page, "  显示墙  ")
    wv_lay = QVBoxLayout(wall_view_page)
    wv_lay.setContentsMargins(4, 4, 4, 4)
    wall_grid = QGridLayout()
    wall_grid.setSpacing(4)
    wv_lay.addLayout(wall_grid)

    # ---------- 显示墙设置页（根据屏幕数量选择横向/纵向布局） ----------
    wall_set_page = QWidget()
    wall_nb.addTab(wall_set_page, "  显示墙设置  ")
    ws_lay = QVBoxLayout(wall_set_page)
    ws_lay.setContentsMargins(12, 12, 12, 12)
    ws_lay.addWidget(QLabel("显示墙布局设置：根据已连接屏幕数量，选择横向/纵向排布方式"))

    wall_count_lbl = QLabel("")
    wall_count_lbl.setStyleSheet("color:gray;")
    ws_lay.addWidget(wall_count_lbl)

    quick_row = QHBoxLayout()
    ws_lay.addLayout(quick_row)
    quick_row.addWidget(QLabel("快速布局:"))
    wall_quick = QComboBox()
    wall_quick.setMinimumWidth(150)
    quick_row.addWidget(wall_quick)
    quick_row.addStretch(1)

    rc_row = QHBoxLayout()
    ws_lay.addLayout(rc_row)
    rc_row.addWidget(QLabel("纵向行数:"))
    wall_rows_sb = QSpinBox()
    wall_rows_sb.setRange(1, 8)
    wall_rows_sb.setFixedWidth(70)
    rc_row.addWidget(wall_rows_sb)
    rc_row.addSpacing(20)
    rc_row.addWidget(QLabel("横向列数:"))
    wall_cols_sb = QSpinBox()
    wall_cols_sb.setRange(1, 8)
    wall_cols_sb.setFixedWidth(70)
    rc_row.addWidget(wall_cols_sb)
    rc_row.addStretch(1)

    ws_hint = QLabel("提示：行数 × 列数 应 ≥ 已连接屏幕数，多余的格子会留空；"
                     "预览图会自动等比缩放铺满各自格子。")
    ws_hint.setWordWrap(True)
    ws_hint.setStyleSheet("color:gray;")
    ws_lay.addWidget(ws_hint)
    ws_lay.addStretch(1)

    # 电视墙运行时状态（UI_Page 局部，嵌套函数用 nonlocal 访问）
    _wall_devs = []    # 当前已连接设备（按 index 排序）
    _wall_cells = []   # [(dev, QLabel), ...] 当前格子

    def _wall_connected():
        """返回已连接设备（按 index 排序）"""
        return sorted([d for d in all_devices.values() if d.device_state == 1],
                      key=lambda x: x.index)

    def _wall_config_path():
        """电视墙布局独立配置文件（程序级，不受多屏 daemon 切换全局 config 影响）"""
        return os.path.join(get_config_dir(), "MSU2_MINI_wall.json")

    def _wall_load_config():
        """读取已保存的显示墙布局（行数, 列数），失败返回 (0, 0)"""
        try:
            with open(_wall_config_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return int(data.get("wall_rows", 0) or 0), int(data.get("wall_cols", 0) or 0)
        except Exception:
            return 0, 0

    def _wall_save():
        """保存显示墙布局到独立配置文件（原子写入，下次启动自动恢复）"""
        try:
            data = {"wall_rows": wall_rows_sb.value(), "wall_cols": wall_cols_sb.value()}
            path = _wall_config_path()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, path)
        except Exception:
            pass

    def _wall_apply_layout():
        """把已连接设备按 行数×列数 排进显示墙网格（行主序：先填满第一行）。"""
        nonlocal _wall_cells
        try:
            rows = wall_rows_sb.value()
            cols = wall_cols_sb.value()
            for i in reversed(range(wall_grid.count())):
                it = wall_grid.itemAt(i)
                w = it.widget() if it is not None else None
                if w is not None:
                    wall_grid.removeWidget(w)
                    w.deleteLater()
            _wall_cells = []
            for idx, dev in enumerate(_wall_devs):
                r, c = idx // cols, idx % cols
                cell = QLabel(dev.device_name)
                cell.setAlignment(Qt.AlignCenter)
                cell.setAutoFillBackground(True)
                cell.setStyleSheet("background-color:#101010; color:#aaaaaa; border:1px solid #444444;")
                cell.setScaledContents(False)
                wall_grid.addWidget(cell, r, c)
                _wall_cells.append((dev, cell))
            for cc in range(cols):
                wall_grid.setColumnStretch(cc, 1)
            for rr in range(rows):
                wall_grid.setRowStretch(rr, 1)
        except Exception:
            pass

    def _wall_refresh_options():
        """根据当前屏数刷新 快速布局下拉 与 行/列取值范围；布局不合法时自动修正。"""
        nonlocal _wall_devs
        try:
            n = len(_wall_devs)
            wall_count_lbl.setText("已连接屏幕数量：%d 台" % n)
            maxv = max(1, n)
            wall_rows_sb.setRange(1, maxv)
            wall_cols_sb.setRange(1, maxv)
            # 列出所有 行×列≥屏数 的组合，最接近方形者优先
            combos = [(r, c) for r in range(1, maxv + 1) for c in range(1, maxv + 1)
                      if r * c >= n]
            combos.sort(key=lambda x: (abs(x[0] - x[1]), x[0] * x[1]))
            wall_quick.blockSignals(True)
            wall_quick.clear()
            for r, c in combos:
                wall_quick.addItem("%d 行 × %d 列" % (r, c), (r, c))
            # 当前行/列是否合法（存在组合中则保留，否则用推荐值）
            cur = (wall_rows_sb.value(), wall_cols_sb.value())
            if cur not in combos and combos:
                cur = combos[0]
                wall_rows_sb.blockSignals(True)
                wall_cols_sb.blockSignals(True)
                wall_rows_sb.setValue(cur[0])
                wall_cols_sb.setValue(cur[1])
                wall_rows_sb.blockSignals(False)
                wall_cols_sb.blockSignals(False)
            # 同步下拉选择
            for i in range(wall_quick.count()):
                if wall_quick.itemData(i) == cur:
                    wall_quick.setCurrentIndex(i)
                    break
            wall_quick.blockSignals(False)
            _wall_apply_layout()
        except Exception:
            pass

    def _on_wall_quick(idx):
        """选择快速布局 → 设置行/列并应用"""
        try:
            data = wall_quick.itemData(idx)
            if data is None:
                return
            r, c = data
            wall_rows_sb.blockSignals(True)
            wall_cols_sb.blockSignals(True)
            wall_rows_sb.setValue(r)
            wall_cols_sb.setValue(c)
            wall_rows_sb.blockSignals(False)
            wall_cols_sb.blockSignals(False)
            _wall_apply_layout()
            _wall_save()
        except Exception:
            pass

    def _on_wall_rc_changed():
        """行/列手动调整：不满足 行×列≥屏数 时自动补足；否则应用并保存。"""
        try:
            rows = wall_rows_sb.value()
            cols = wall_cols_sb.value()
            n = max(1, len(_wall_devs))
            if rows * cols < n:
                need_rows = -(-n // cols)
                if need_rows != rows:
                    wall_rows_sb.blockSignals(True)
                    wall_rows_sb.setValue(need_rows)
                    wall_rows_sb.blockSignals(False)
                    rows = need_rows
                else:
                    need_cols = -(-n // rows)
                    wall_cols_sb.blockSignals(True)
                    wall_cols_sb.setValue(need_cols)
                    wall_cols_sb.blockSignals(False)
                    cols = need_cols
            # 同步下拉（存在该组合时）
            for i in range(wall_quick.count()):
                if wall_quick.itemData(i) == (rows, cols):
                    wall_quick.blockSignals(True)
                    wall_quick.setCurrentIndex(i)
                    wall_quick.blockSignals(False)
                    break
            _wall_apply_layout()
            _wall_save()
        except Exception:
            pass

    wall_quick.currentIndexChanged.connect(_on_wall_quick)
    wall_rows_sb.valueChanged.connect(lambda _v: _on_wall_rc_changed())
    wall_cols_sb.valueChanged.connect(lambda _v: _on_wall_rc_changed())

    # 初始：从独立配置文件恢复显示墙布局（若保存过）
    _wr, _wc = _wall_load_config()
    if _wr >= 1 and _wc >= 1:
        wall_rows_sb.setValue(_wr)
        wall_cols_sb.setValue(_wc)

    _wall_devs = _wall_connected()
    _wall_refresh_options()

    def _wall_tick():
        """定时刷新显示墙：检测设备集合变化 + 更新每格实时预览。"""
        nonlocal _wall_devs
        try:
            devs = _wall_connected()
            if [d.index for d in devs] != [d.index for d in _wall_devs]:
                _wall_devs = devs
                _wall_refresh_options()
            for dev, cell in list(_wall_cells):
                try:
                    if dev.device_state != 1:
                        cell.setPixmap(QPixmap())
                        cell.setText("%s\n(未连接)" % dev.device_name)
                        cell.setStyleSheet("background-color:#101010; color:#888888; border:1px solid #444444;")
                        continue
                    img = None
                    try:
                        with dev._preview_lock:
                            img = dev.last_preview_rgb
                    except Exception:
                        img = None
                    if img is not None and getattr(img, "size", 0) and img.size > 0:
                        h, w = img.shape[:2]
                        img_c = np.ascontiguousarray(img)
                        qimg = QImage(img_c.data, w, h, img_c.strides[0],
                                      QImage.Format_RGB888).copy()
                        pix = QPixmap.fromImage(qimg)
                        tw = cell.width() if cell.width() > 10 else 160
                        th = cell.height() if cell.height() > 10 else 80
                        try:
                            pix = pix.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        except Exception:
                            pass
                        cell.setPixmap(pix)
                        cell.setStyleSheet("background-color:#101010; border:1px solid #444444;")
                    else:
                        cell.setPixmap(QPixmap())
                        cell.setText("%s\n(无预览)" % dev.device_name)
                        cell.setStyleSheet("background-color:#101010; color:#888888; border:1px solid #444444;")
                except Exception:
                    pass
        except Exception:
            pass
        QTimer.singleShot(500, _wall_tick)

    QTimer.singleShot(500, _wall_tick)

    # ==================== 关于页 ====================
    about_frame = QWidget()
    top_nb.addTab(about_frame, "  关于  ")
    about_lay = QVBoxLayout(about_frame)
    about_lay.setContentsMargins(12, 12, 12, 12)
    about_text = QTextEdit()
    about_text.setReadOnly(True)
    try:
        about_text.setPlainText(get_program_info())
    except Exception:
        about_text.setPlainText("%s v%s" % (PROGRAM_TITLE, PROGRAM_VERSION))
    about_lay.addWidget(about_text)

    # ==================== 托盘 ====================
    _tray_icon = None

    def hide_to_tray():
        global _tray_icon
        try:
            iconimage = MiniMark.load_image("resource/icon.ico")

            def show_window(icon=None, item=None):
                window.showNormal()
                window.raise_()
                window.activateWindow()
                if _tray_icon is not None:
                    _tray_icon.stop()

            def quit_window(icon=None, item=None):
                window.close()

            menu = pystray.Menu(
                pystray.MenuItem("显示", show_window, default=True),
                pystray.MenuItem("退出", quit_window),
            )
            _tray_icon = pystray.Icon(PROGRAM_TITLE, iconimage, PROGRAM_TITLE, menu)
            _tray_icon.run_detached()
            window.hide()
        except Exception as e:
            insert_text_message("Failed to use pystray to hide to tray, %s" % e)

    def show_window():
        window.showNormal()
        window.raise_()
        window.activateWindow()

    def quit_window():
        window.close()

    # ==================== 关闭/退出 ====================
    def on_closing():
        stop_api_server()
        window.close()

    def closeEvent(event):
        stop_api_server()
        event.accept()

    window.closeEvent = closeEvent
    window.setMinimumSize(760, 660)
    if len(sys.argv) > 1:
        arg = sys.argv[1].lstrip('-').lower()
        if arg == "h" or arg == "hide":
            hide_to_tray()

    # 参数全部获取后再启动各后台线程（与老版 4.7.1 一致）：
    # daemon=自动扫描连接设备/渲染状态机，load=配置加载，ping=延迟检测，manager=按键检测
    if _primary_device:
        _primary_device.start_threads()
    daemon_thread.start()
    load_thread.start()
    if ping_thread is not None:
        ping_thread.start()
    manager_thread.start()

    # 定期刷新设备列表 + 恢复当前设备上次的页面/方向选择
    last_synced_device_state = None
    last_refresh_device_signature = None

    def _periodic_refresh():
        nonlocal last_synced_device_state, last_refresh_device_signature
        refresh_device_list()
        try:
            _dev = get_current_device()
            if _dev is not None:
                dev_state_lbl.setText("设备已连接: %s" % _dev.device_name if _dev.device_state == 1 else "设备未连接")
        except Exception:
            pass
        try:
            dev = get_current_device()
            if dev is not None and dev.config is not None:
                key = (dev.device_name, dev.config.state_machine, dev.config.lcd_change)
                if key != last_synced_device_state:
                    last_synced_device_state = key
                    sync_page_combobox()
                    sync_lcd_combobox()
                # 设备集合变化（新屏连接/断开）即重建主控多标签，保证一开始就显示所有屏标签
                sig = tuple(sorted((d.index, d.device_state) for d in all_devices.values()))
                if sig != last_refresh_device_signature:
                    last_refresh_device_signature = sig
                    try:
                        _rebuild_main_tabs()
                    except Exception:
                        pass
        except Exception:
            pass
        QTimer.singleShot(2000, _periodic_refresh)

    QTimer.singleShot(2000, _periodic_refresh)

    # 自动翻页轮播（主线程定时器）
    global _last_cycle_time
    _last_cycle_time = time.monotonic()

    def _auto_cycle_tick():
        global _last_cycle_time
        try:
            if config_obj.page_cycle_enable and config_obj.page_cycle_interval > 0:
                now = time.monotonic()
                if now - _last_cycle_time >= config_obj.page_cycle_interval:
                    _last_cycle_time = now
                    Page_Down()
        except Exception:
            pass
        QTimer.singleShot(1000, _auto_cycle_tick)

    QTimer.singleShot(1000, _auto_cycle_tick)

    # 启动本地 API 投屏服务器（HTTP + WebSocket）
    try:
        if getattr(config_obj, "api_enable", 1):
            start_api_server()
    except Exception as e:
        print("启动 API 服务器失败：%s" % e)

    # 进入消息循环
    window.show()
    app.exec()











class MSN_Device:
    def __init__(self, com, version):
        self.com = com  # 登记串口位置
        self.version = version  # 登记MSN版本
        self.name = "MSN"  # 登记设备名称
        # self.baud_rate = 19200  # 登记波特率（没有用到）


class MSN_Data:
    def __init__(self, name, unit, family, data):
        self.name = name
        self.unit = unit
        self.family = family
        self.data = data


# Device_State_Labelen: 0无修改，1窗口已隐藏，2窗口已恢复有修改，3窗口已隐藏有修改
def set_device_state(state):
    """全局设备状态更新（用于UI标签），实际操作当前设备"""
    global Label1, Device_State_Labelen
    device = get_current_device()
    if device is None:
        return
    device.set_device_state(state)
    
    if Device_State_Labelen == 2:
        Device_State_Labelen = 0
    if Device_State_Labelen == 0:
        try:
            if device.device_state == 1:
                Label1.config(text="设备已连接", fg="white", bg="green")
            else:
                Label1.config(text="设备未连接", fg="white", bg="red")
        except Exception as e:
            Device_State_Labelen = 2
    elif Device_State_Labelen == 1:
        Device_State_Labelen = 3


def _dump_usb_descriptor(port):
    """诊断：打印USB设备的完整描述符信息"""
    print("=" * 60)
    print("USB设备描述符诊断: %s" % port.device)
    print("  device:          %s" % port.device)
    print("  name:            %s" % port.name)
    print("  description:     %s" % port.description)
    print("  hwid:            %s" % port.hwid)
    print("  vid:             0x%04X" % (port.vid or 0))
    print("  pid:             0x%04X" % (port.pid or 0))
    print("  serial_number:   %s" % port.serial_number)
    print("  location:        %s" % port.location)
    print("  manufacturer:    %s" % port.manufacturer)
    print("  product:         %s" % port.product)
    print("  interface:       %s" % port.interface)
    print("=" * 60)


def Get_MSN_Device(port_list):  # 尝试获取MSN设备
    global config_file, config_obj
    device = get_current_device()
    if device is None:
        return
    
    if device.ser is not None and device.ser.is_open:
        device.ser.close()

    # 对串口进行监听，确保其为MSN设备
    My_MSN_Device = None
    My_MSN_Data = None
    for port in port_list:
        # 诊断：打印USB描述符
        _dump_usb_descriptor(port)
        try:  # 尝试打开串口
            # 初始化串口连接,初始使用
            device.ser = serial.Serial(port.device, 115200, timeout=5.0, write_timeout=5.0, inter_byte_timeout=0.1)
            recv = SER_Read()
            if recv == 0:
                print("未接收到设备响应，打开失败：%s" % port.device)
                device.ser.close()
                continue  # 尝试下一个端口
        except Exception as e:  # 出现异常
            print("%s 无法打开，请检查是否被其他程序占用: %s" % (port.device, e))
            if device.ser is not None and device.ser.is_open:
                device.ser.close()
            time.sleep(0.2)  # 防止频繁重试
            continue  # 尝试下一个端口
        # 逐字解析编码，收到6个字符以上数据时才进行解析
        for n in range(0, len(recv) - 5):
            # 当前字节为0时进行解析，确保为MSN设备，确保版本号为数字ASC码
            version1 = recv[n + 4] - 48
            version2 = recv[n + 5] - 48
            if recv[n: n + 4] != b'\x00MSN' or not (0 <= version1 < 10 and 0 <= version2 < 10):
                continue
            msn_version = version1 * 10 + version2
            hex_use = b"\x00MSNCN"
            recv = SER_rw(hex_use)  # 发出指令
            # 确保为MSN设备
            if recv[-6:] == hex_use:
                PAGE_ID_tmp = {
                    GIF_PAGE_ID: "动图", PCTIME_PAGE_ID: "时间",
                    PHOTO_PAGE_ID: "单个相册图片", SCREEN_PAGE_ID: "屏幕镜像",
                    CAMERA_VIDEO_ID: "相机视频", STATE_PAGE_ID: "电脑CPU/内存/磁盘/电池使用率监控",
                    NETSPEED_PAGE_ID: "网络流量监控", CUSTOM1_PAGE_ID: "自定义显示两项图表",
                    CUSTOM2_PAGE_ID: "自定义显示多项数值", ABOUT_PAGE_ID: "关于",
                }
                if config_obj.state_machine < len(PAGE_ID_tmp):
                    page_index = config_obj.state_machine
                else:
                    page_index = 0

                # 对MSN设备进行登记
                My_MSN_Device = MSN_Device(port.device, msn_version)
                device.com_port = port.device
                device.serial_number = port.serial_number or ""  # 唯一识别码
                # 采集设备硬件/固件信息（供“设备信息”标签页展示）
                device.firmware_version = msn_version
                device.usb_info = {
                    "port": port.device,
                    "name": port.name,
                    "description": port.description,
                    "vid": "0x%04X" % (port.vid or 0),
                    "pid": "0x%04X" % (port.pid or 0),
                    "serial_number": port.serial_number or "",
                    "location": port.location,
                    "manufacturer": port.manufacturer,
                    "product": port.product,
                    "interface": port.interface,
                }
                # 每屏独立配置：按 serial_number 加载/创建本屏配置并切换生效
                # （提前加载，使本屏页面/方向等配置立即生效并正确显示自身配置文件）
                load_device_config(device, device.serial_number)
                set_active_device_config(device)
                print(get_formatted_time_string(datetime.now()), end=' ')
                if port.location is None:
                    insert_text_message("连接成功：%s\n当前页面：%s\n显示方向：%s\n配置文件：%s" % (
                        port.device, PAGE_ID_tmp[page_index], LCD_STATE_MESSAGE[config_obj.lcd_change],
                        device.config_file or config_file))
                else:
                    insert_text_message("连接成功：%s@%s\n当前页面：%s\n显示方向：%s\n配置文件：%s" % (
                        port.device, port.location, PAGE_ID_tmp[page_index], LCD_STATE_MESSAGE[config_obj.lcd_change],
                        device.config_file or config_file))
                break  # 退出当前for循环
            else:
                print("设备无法连接，请检查连接是否正常：%s" % recv)

        if My_MSN_Device is None:
            print("设备校验失败：%s" % port.device)
            device.ser.close()
        else:
            break  # 连接成功即退出循环

    if My_MSN_Device is None:  # 没有找到可用的设备
        return

    device.ser.reset_input_buffer()
    device.ser.reset_output_buffer()
    My_MSN_Data = Read_M_SFR_Data(256)  # 读取u8在0x0100之后的128字节
    Print_MSN_Data(My_MSN_Data)  # 解析字节中的数据格式
    device.msn_device = My_MSN_Device
    device.msn_data = My_MSN_Data
    device.lcd_change_now = config_obj.lcd_change
    LCD_State(device.lcd_change_now)  # 配置显示方向
    device.state_change = 1  # 状态发生变化
    # 继承页面：用本设备自己的配置页面，避免 daemon 当前全局 config_obj 是别的屏
    # 导致本屏页面被错误覆盖（串台）且 _periodic_refresh 每轮检测到变化→下拉框频繁刷新
    device.state_machine = (device.config.state_machine
                            if device.config is not None else config_obj.state_machine)
    # 注意：先完成全部初始化，最后才标记设备已连接(set_device_state(1))。
    # 若过早置1，截图/处理/按键线程会立即开始并发发送帧，
    # 与下面的LCD检测、ADC阈值读取、方向重置交错，导致启动后首帧画面倾斜。
    # 自动检测LCD屏幕分辨率
    Detect_LCD_Size()
    # 初始化numpy数组（依赖LCD尺寸）
    device.init_arrays()
    # 配置按键阈值
    device.ADC_det = (Read_ADC_CH(9) + Read_ADC_CH(9) + Read_ADC_CH(9)) // 3
    device.ADC_det = device.ADC_det - 250  # 根据125的阈值判断是否被按下
    # 启动稳定化：所有初始化读取完成后，再次重置LCD方向并清屏，
    # 确保设备处于干净状态，避免启动后首帧画面倾斜
    LCD_State(device.lcd_change_now)
    time.sleep(0.1)
    # 重置看门狗计时，避免状态机首轮立即触发一次多余的方向重置
    device.last_lcd_watchdog_time = time.monotonic()
    # 最后标记设备已连接：此时设备已完全稳定，线程才开始发送帧
    set_device_state(1)


def MSN_Device_1_State_machine():  # MSN设备1的循环状态机
    global config_obj, Label3, write_path_index, Img_data_use
    device = get_current_device()
    if device is None:
        return
    # 用当前渲染设备的运行时页面渲染（多屏各自独立），
    # 避免 daemon/UI 切换全局 config_obj 时把别的屏幕的页面串到本屏
    config_obj.state_machine = device.state_machine

    if write_path_index != 0:
        if write_path_index == 1:
            ctx = _cur_main_ctx()
            le = ctx.get('label3') if ctx else None
            photo_path = le.text().strip() if le else ""
            Write_Flash_Photo_fast(0, photo_path)
        elif write_path_index == 2:
            Write_Flash_hex_fast(3826, Img_data_use)
        elif write_path_index == 3:
            Write_Flash_hex_fast(3926, Img_data_use)
        elif write_path_index == 4:
            Write_Flash_hex_fast(0, Img_data_use)
        write_path_index = 0
        state_change_set(save=False)

    # 定期看门狗：每30秒强制重置LCD方向
    now_watchdog = time.monotonic()
    if now_watchdog - device.last_lcd_watchdog_time > 15:
        device.force_lcd_reset = True
        device.last_lcd_watchdog_time = now_watchdog

    # 防御：切页/看门狗/方向不一致时，强制重置LCD方向
    if device.force_lcd_reset or device.lcd_change_now != config_obj.lcd_change:
        device.lcd_change_now = config_obj.lcd_change
        if device.device_state == 1:
            LCD_State(device.lcd_change_now)
        device.force_lcd_reset = False

    try:
        if _api_try_screen_id(device):
            pass  # 屏幕序号检测：显示本屏屏号，超时后自动恢复原页面
        elif _api_try_overlay(device):
            pass  # 强制投屏覆盖：显示外部投屏帧，跳过普通页面渲染
        elif config_obj.state_machine == PCTIME_PAGE_ID:
            show_PC_time(device.color_use)
        elif config_obj.state_machine == PHOTO_PAGE_ID:
            show_Photo()
        elif config_obj.state_machine == SCREEN_PAGE_ID or config_obj.state_machine == CAMERA_VIDEO_ID:
            show_PC_Screen()
        elif config_obj.state_machine == STATE_PAGE_ID:
            show_PC_state(device.color_use, BLACK)
        elif config_obj.state_machine == NETSPEED_PAGE_ID:
            if (config_obj.netspeed_mode or "自定义") == "经典":
                # 经典样式：上传/下载文字用通用文字颜色，柱状图用默认柱颜色
                rgb_tuple = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
                show_netspeed(up_text_color=rgb_tuple, down_text_color=rgb_tuple,
                              bar1_color=bar_colors[0], bar2_color=bar_colors[1],
                              back_color=back_color)
            else:
                up_color = _diskio_hex2rgb(config_obj.netspeed_up_color)
                down_color = _diskio_hex2rgb(config_obj.netspeed_down_color)
                net_bar1 = _diskio_hex2rgb(config_obj.netspeed_bar1_color)
                net_bar2 = _diskio_hex2rgb(config_obj.netspeed_bar2_color)
                show_netspeed(up_text_color=up_color, down_text_color=down_color,
                              bar1_color=net_bar1, bar2_color=net_bar2,
                              back_color=back_color)
        elif config_obj.state_machine == CUSTOM1_PAGE_ID:
            rgb_tuple = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
            show_custom_two_rows(text_color=rgb_tuple, bar1_color=bar_colors[0], bar2_color=bar_colors[1],
                                 back_color=back_color)
        elif config_obj.state_machine == CUSTOM2_PAGE_ID:
            show_full_custom()
        elif config_obj.state_machine == ABOUT_PAGE_ID:
            show_about()
        elif config_obj.state_machine == MARQUEE_PAGE_ID:
            show_marquee()
        elif config_obj.state_machine == DISKIO_PAGE_ID:
            show_diskio()
        elif config_obj.state_machine == PING_PAGE_ID:
            show_ping()
        elif config_obj.state_machine == PROC_PAGE_ID:
            show_proc()
        elif config_obj.state_machine == TIMER_PAGE_ID:
            show_timer()
        elif config_obj.state_machine == MEMO_PAGE_ID:
            show_memo()
        elif config_obj.state_machine == TODO_PAGE_ID:
            show_todo()
        elif config_obj.state_machine == WORLDCLOCK_PAGE_ID:
            show_worldclock()
        elif config_obj.state_machine == LUNAR_PAGE_ID:
            show_lunar()
        elif config_obj.state_machine == GAUGE_PAGE_ID:
            show_gauge()
        elif config_obj.state_machine == HWDETAIL_PAGE_ID:
            show_hwdetail()
        elif config_obj.state_machine == WEATHER_PAGE_ID:
            show_weather()
        elif config_obj.state_machine == CRYPTO_PAGE_ID:
            show_crypto()
        elif config_obj.state_machine == HOTSEARCH_PAGE_ID:
            show_hotsearch()
        elif config_obj.state_machine == BATTERY_PAGE_ID:
            show_battery()
        elif config_obj.state_machine == MUSIC_PAGE_ID:
            show_music()
        elif config_obj.state_machine == API_PAGE_ID:
            show_api()
        else:
            show_gif()
    except Exception as e:
        print("MSN_Device_1_State_machine: 页面异常 %s" % traceback.format_exc())
        device.force_lcd_reset = True
        time.sleep(0.5)


# ==================== 新增页面（第二批） ====================

# 农历数据表（1900~2100年），公开的农历算法数据
LUNAR_INFO = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5d0, 0x14573, 0x052d0, 0x0a9a8, 0x0e950, 0x06aa0,
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b5a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x055c0, 0x0ab60, 0x096d5, 0x092e0,
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,
    0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
    0x0d520,
]

LUNAR_MONTHS = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
LUNAR_DAYS = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
              "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
              "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
SHENGXIAO = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]


def lunar_leap_month(year):
    return LUNAR_INFO[year - 1900] & 0xf


def lunar_leap_days(year):
    if lunar_leap_month(year):
        return 30 if (LUNAR_INFO[year - 1900] & 0x10000) else 29
    return 0


def lunar_month_days(year, month):
    return 30 if (LUNAR_INFO[year - 1900] & (0x10000 >> month)) else 29


def lunar_year_days(year):
    total = 348
    i = 0x8000
    while i > 0x8:
        if LUNAR_INFO[year - 1900] & i:
            total += 1
        i >>= 1
    return total + lunar_leap_days(year)


def solar_to_lunar(year, month, day):
    """公历转农历，返回 (农历年, 农历月, 农历日, 是否闰月)"""
    from datetime import date
    base = date(1900, 1, 31)
    target = date(year, month, day)
    day_offset = (target - base).days
    ly = 1900
    while day_offset >= lunar_year_days(ly):
        day_offset -= lunar_year_days(ly)
        ly += 1
    leap = lunar_leap_month(ly)
    is_leap = False
    lm = 1
    while lm <= 12:
        if leap == lm:
            ld = lunar_leap_days(ly)
            if day_offset < ld:
                is_leap = True
                break
            day_offset -= ld
        mdays = lunar_month_days(ly, lm)
        if day_offset < mdays:
            break
        day_offset -= mdays
        lm += 1
    return ly, lm, day_offset + 1, is_leap


def ping_worker():
    """后台线程：定时ping目标地址，结果写入全局ping_result"""
    global ping_result, config_obj
    import re
    import subprocess
    while True:
        try:
            if config_obj is not None and config_obj.state_machine == PING_PAGE_ID:
                host = config_obj.ping_host or "223.5.5.5"
                try:
                    proc = subprocess.run(["ping", "-n", "1", "-w", "1000", host],
                                          capture_output=True, text=True, timeout=3)
                    out = (proc.stdout or "") + (proc.stderr or "")
                    m = re.search(r"(?:时间|time)[=<]\s*(\d+)\s*ms", out)
                    if m:
                        ping_result = "%s: %sms" % (host, m.group(1))
                    elif re.search(r"TTL=", out, re.IGNORECASE):
                        ping_result = "%s: 通" % host
                    else:
                        ping_result = "%s: 超时" % host
                except Exception:
                    ping_result = "%s: 失败" % host
            time.sleep(1.0)
        except Exception:
            time.sleep(1.0)


def show_marquee():
    """文字跑马灯：配置文本水平循环滚动"""
    global config_obj, marquee_offset
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    text = config_obj.marquee_text or " "
    try:
        font_size = max(8, int(config_obj.marquee_font_size))
    except Exception:
        font_size = 20
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", font_size)  # 跑马灯字体固定用黑体
    try:
        hex_color = (config_obj.marquee_color or "#ffffff").lstrip('#')
        color = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        color = (255, 255, 255)
    text_w = round(draw.textlength(text, font=font))
    total = SHOW_WIDTH + text_w + 20
    offset = int(marquee_offset % total) if total > 0 else 0
    x = SHOW_WIDTH - offset
    y = (SHOW_HEIGHT - font_size) // 2
    draw.text((x, y), text, fill=color, font=font)
    if x + text_w < SHOW_WIDTH:
        draw.text((x + text_w + 20, y), text, fill=color, font=font)
    # 滚动速度可配置（每帧像素数，越大越快）
    try:
        speed = max(0.5, float(config_obj.marquee_speed))
    except Exception:
        speed = 2
    marquee_offset += speed
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(0.05)


def _diskio_hex2rgb(h):
    """配置颜色(#rrggbb)转RGB元组，非法值回退白色"""
    try:
        h = (h or "#ffffff").lstrip('#')
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (255, 255, 255)


def _diskio_read_speed():
    """采样磁盘IO速率，返回 (读B/s, 写B/s)，异常时返回 (0,0)"""
    global diskio_last, diskio_last_time
    now = time.monotonic()
    try:
        io = psutil.disk_io_counters()
        dt = now - diskio_last_time
        if dt <= 0:
            dt = 0.001
        read_s = (io.read_bytes - diskio_last.read_bytes) / dt
        write_s = (io.write_bytes - diskio_last.write_bytes) / dt
        diskio_last = io
        diskio_last_time = now
        return max(0.0, read_s), max(0.0, write_s)
    except Exception:
        return 0.0, 0.0


def show_diskio():
    """磁盘实时读写速率（两种显示模式：经典 / 网速样式）"""
    global config_obj, diskio_last, diskio_last_time
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        diskio_last = psutil.disk_io_counters()
        diskio_last_time = time.monotonic()
        if dev.diskio_plot_data is None:
            dev.diskio_plot_data = {"read": [0] * (SHOW_WIDTH // 2), "write": [0] * (SHOW_WIDTH // 2)}
    read_s, write_s = _diskio_read_speed()

    try:
        mode = config_obj.diskio_mode or "经典"
    except Exception:
        mode = "经典"

    if mode == "网速样式":
        _show_diskio_netspeed(dev, read_s, write_s)
    elif mode == "经典2":
        _show_diskio_classic2(dev, read_s, write_s)
    else:
        _show_diskio_classic(read_s, write_s)
    dev.sleep_event.wait(0.5)


def _show_diskio_classic(read_s, write_s):
    """经典模式：标题可选 + 读/写两行，字号自适应或手动，颜色可配置"""
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    try:
        show_title = bool(config_obj.diskio_show_title)
        font_auto = bool(config_obj.diskio_font_auto)
    except Exception:
        show_title, font_auto = True, True
    # 字号：自动按行数适配，或手动
    if font_auto:
        rows = 3 if show_title else 2
        font_size = max(8, min(40, int(SHOW_HEIGHT / rows) - 3))
    else:
        try:
            font_size = max(8, min(72, int(config_obj.diskio_font_size)))
        except Exception:
            font_size = 16
    title_color = _diskio_hex2rgb(config_obj.diskio_title_color)
    read_color = _diskio_hex2rgb(config_obj.diskio_read_color)
    write_color = _diskio_hex2rgb(config_obj.diskio_write_color)

    # 组装要显示的行
    lines = []
    if show_title:
        lines.append(("磁盘读写", title_color))
    lines.append(("读 %.1f MB/s" % (read_s / 1048576.0), read_color))
    lines.append(("写 %.1f MB/s" % (write_s / 1048576.0), write_color))

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", font_size)
    # 长文本自动缩字号，保证整行放得下
    while font_size > 8:
        tw = round(draw.textlength("读 999.9 MB/s", font=font))
        if tw <= SHOW_WIDTH - 4:
            break
        font_size -= 1
        font = MiniMark.load_font("./simhei.ttf", font_size)
    line_h = font_size + 3
    start_y = max(0, (SHOW_HEIGHT - len(lines) * line_h) // 2)
    for i, (text, color) in enumerate(lines):
        draw.text((4, start_y + i * line_h), text, fill=color, font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)


def _show_diskio_netspeed(dev, read_s, write_s):
    """网速样式：读/写两行标签+数值，下方各一条实时柱状图，颜色可配置"""
    global config_obj
    # 追加柱状图采样数据
    if dev.diskio_plot_data is None:
        dev.diskio_plot_data = {"read": [0] * (SHOW_WIDTH // 2), "write": [0] * (SHOW_WIDTH // 2)}
    dev.diskio_plot_data["read"].pop(0)
    dev.diskio_plot_data["read"].append(read_s)
    dev.diskio_plot_data["write"].pop(0)
    dev.diskio_plot_data["write"].append(write_s)

    label_color = _diskio_hex2rgb(config_obj.diskio_label_color)
    read_color = _diskio_hex2rgb(config_obj.diskio_value_read_color)
    write_color = _diskio_hex2rgb(config_obj.diskio_value_write_color)
    bar1_color = _diskio_hex2rgb(config_obj.diskio_bar1_color)
    bar2_color = _diskio_hex2rgb(config_obj.diskio_bar2_color)

    # 字号：自动适配（按两行+柱状图高度）或手动
    try:
        font_auto = bool(config_obj.diskio_value_auto)
    except Exception:
        font_auto = True
    if font_auto:
        font_size = max(8, min(40, SHOW_HEIGHT // 2 - 6))
    else:
        try:
            font_size = max(8, min(72, int(config_obj.diskio_value_font_size)))
        except Exception:
            font_size = 20
    font = MiniMark.load_font("./simhei.ttf", font_size)
    while font_size > 8:
        if round(font.getlength("读 999.9 MB/s")) <= SHOW_WIDTH - 4:
            break
        font_size -= 1
        font = MiniMark.load_font("./simhei.ttf", font_size)

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    # 标签 + 数值（标签用标签色，数值用读/写色）
    for label, value, vcolor, start_y in (
            ("读", read_s, read_color, SHOW_HEIGHT // 4 - font_size // 2),
            ("写", write_s, write_color, SHOW_HEIGHT - SHOW_HEIGHT // 4 - font_size // 2)):
        value_text = "%s/s" % sizeof_fmt(value)
        lw = round(draw.textlength(label, font=font))
        draw.text((0, start_y), label, fill=label_color, font=font)
        draw.text((lw + 2, start_y), value_text, fill=vcolor, font=font)
    # 柱状图：两条（读/写）
    min_draw = 1
    for bar_y, key, color in zip([SHOW_HEIGHT // 4 - 1, SHOW_HEIGHT - SHOW_HEIGHT // 4 - 1],
                                 ["read", "write"], [bar1_color, bar2_color]):
        values = dev.diskio_plot_data[key]
        max_value = max(min_draw, max(values))
        x0 = -BAR_WIDTH
        x1 = -1
        y1 = IMAGE_HEIGHT + bar_y
        percent = IMAGE_HEIGHT / max_value
        for sent in values[-(SHOW_WIDTH // BAR_WIDTH):]:
            bar_height = percent * sent
            x0 += BAR_WIDTH
            x1 += BAR_WIDTH
            y0 = y1 - bar_height
            draw.rectangle([x0, y0, x1, y1], fill=color)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)


def _get_netspeed_colors():
    """返回网络流量页面当前使用的配色 (上行文字, 下行文字, 柱1, 柱2)。
    经典模式→通用文字颜色+默认柱色；自定义模式→网络流量独立配色。"""
    global config_obj
    if (config_obj.netspeed_mode or "自定义") == "经典":
        text = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
        return text, text, bar_colors[0], bar_colors[1]
    return (_diskio_hex2rgb(config_obj.netspeed_up_color),
            _diskio_hex2rgb(config_obj.netspeed_down_color),
            _diskio_hex2rgb(config_obj.netspeed_bar1_color),
            _diskio_hex2rgb(config_obj.netspeed_bar2_color))


def _show_diskio_classic2(dev, read_s, write_s):
    """经典2样式：完全复刻网络流量页面的字体大小、布局与配色，标签改为读/写"""
    global config_obj
    # 追加柱状图采样数据（与网速样式共享同一份 read/write 采样）
    if dev.diskio_plot_data is None:
        dev.diskio_plot_data = {"read": [0] * (SHOW_WIDTH // 2), "write": [0] * (SHOW_WIDTH // 2)}
    dev.diskio_plot_data["read"].pop(0)
    dev.diskio_plot_data["read"].append(read_s)
    dev.diskio_plot_data["write"].pop(0)
    dev.diskio_plot_data["write"].append(write_s)

    read_color, write_color, bar1_color, bar2_color = _get_netspeed_colors()
    _render_two_line_bars("读", "写", read_s, write_s,
                          read_color, write_color, bar1_color, bar2_color,
                          dev.diskio_plot_data, "read", "write")


def show_ping():
    """网络延迟（后台线程ping，此处仅读取结果）"""
    global ping_result
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    draw_text(str(ping_result), font_size=20)
    dev.sleep_event.wait(0.5)


def show_proc():
    """进程内存占用TOP（数量可配置，超过一页自动翻页）"""
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    procs = []
    for p in psutil.process_iter(['name', 'memory_info']):
        try:
            procs.append((p.info['name'] or "?", p.info['memory_info'].rss))
        except Exception:
            pass
    procs.sort(key=lambda x: x[1], reverse=True)
    count = max(1, int(config_obj.proc_count))
    procs = procs[:count]
    per_page = 5
    pages = max(1, (len(procs) + per_page - 1) // per_page)
    page = int(time.monotonic() // 3) % pages  # 每3秒翻页
    lines = procs[page * per_page:(page + 1) * per_page]
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 14)
    for i, (name, rss) in enumerate(lines):
        rank = page * per_page + i + 1
        draw.text((4, i * 15), "%d.%s %.0fM" % (rank, name[:10], rss / 1048576.0), fill=(255, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(1.0)


def show_timer():
    """番茄钟/倒计时"""
    global config_obj, timer_remaining, timer_running, timer_last_tick
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        timer_remaining = max(1, int(config_obj.timer_minutes)) * 60
        timer_running = True
        timer_last_tick = time.monotonic()
    now = time.monotonic()
    if timer_running:
        elapsed = int(now - timer_last_tick)
        if elapsed > 0:
            timer_remaining -= elapsed
            timer_last_tick += elapsed
        if timer_remaining <= 0:
            timer_remaining = 0
            timer_running = False
    m = timer_remaining // 60
    s = timer_remaining % 60
    text = ("▶ %02d:%02d" if timer_running else "⏸ %02d:%02d") % (m, s)
    draw_text(text, font_size=30)
    dev.sleep_event.wait(0.2)


def show_memo():
    """纪念日/生日倒计时"""
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    today = datetime.now()
    lines = []
    for item in config_obj.memo_items:
        parts = item.split("|")
        if len(parts) < 2:
            continue
        name, md = parts[0].strip(), parts[1].strip()
        try:
            m, d = map(int, md.split("-"))
        except Exception:
            continue
        target = datetime(today.year, m, d)
        if target < today:
            target = datetime(today.year + 1, m, d)
        days = (target - today).days
        lines.append("%s %d天" % (name[:10], days))
    if not lines:
        lines = ["暂无纪念日"]
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 16)
    for i, line in enumerate(lines[:4]):
        draw.text((4, 6 + i * 18), line, fill=(255, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(1.0)


def show_todo():
    """待办事项列表"""
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    items = [t for t in config_obj.todo_items if t.strip()]
    if not items:
        items = ["暂无待办"]
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 14)
    for i, line in enumerate(items[:5]):
        draw.text((4, i * 15), ("□ " + line[:16]), fill=(255, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(1.0)


def show_worldclock():
    """世界时钟（时区可自定义，每项名称|UTC偏移，超过一页自动翻页）"""
    global config_obj
    from datetime import timedelta
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    now_utc = datetime.utcnow()
    zones = []
    for item in (config_obj.clock_zones or "北京|8").split(","):
        parts = item.strip().split("|")
        if len(parts) == 2:
            try:
                zones.append((parts[0].strip()[:6], int(parts[1].strip())))
            except Exception:
                pass
    if not zones:
        zones = [("北京", 8)]
    per_page = 4
    pages = max(1, (len(zones) + per_page - 1) // per_page)
    page = int(time.monotonic() // 4) % pages  # 每4秒翻页
    zones_page = zones[page * per_page:(page + 1) * per_page]
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 16)
    for i, (name, offset) in enumerate(zones_page):
        t = now_utc + timedelta(hours=offset)
        draw.text((4, 4 + i * 19), "%-6s %02d:%02d" % (name, t.hour, t.minute), fill=(255, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(1.0)


def show_lunar():
    """农历日期 + 干支 + 生肖"""
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    now = datetime.now()
    ly, lm, ld, is_leap = solar_to_lunar(now.year, now.month, now.day)
    month_name = ("闰" + LUNAR_MONTHS[lm - 1]) if is_leap else LUNAR_MONTHS[lm - 1]
    gan_zhi = GAN[(ly - 4) % 10] + ZHI[(ly - 4) % 12]
    shengxiao = SHENGXIAO[(ly - 4) % 12]
    line1 = "%d-%02d-%02d" % (now.year, now.month, now.day)
    line2 = "%s年%s%s" % (gan_zhi, month_name, LUNAR_DAYS[ld - 1])
    line3 = "属%s" % shengxiao
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 18)
    draw.text((4, 4), line1, fill=(255, 255, 255), font=font)
    draw.text((4, 30), line2, fill=(255, 200, 0), font=font)
    draw.text((4, 56), line3, fill=(255, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(1.0)


_HW_CPU_KEYWORDS = ("CPU", "CORE", "RYZEN", "INTEL", "AMD", "PROCESSOR")
_HW_GPU_KEYWORDS = ("GPU", "GEFORCE", "RADEON", "RTX", "GTX", "NVIDIA", "GRAPHICS", "IRIS", "UHD")
# LibreHardwareMonitor 硬件类型枚举（直接区分硬件，无需猜名字）
_HW_CPU_TYPES = ("Cpu",)
_HW_GPU_TYPES = ("GpuNvidia", "GpuAti", "GpuIntel")


def _hw_type_name(hw):
    try:
        return str(hw.HardwareType)
    except Exception:
        return ""


def _find_sensor_value(stype, keyword=""):
    """从硬件监控管理器查找传感器值。
    stype: 传感器类型(Temperature/Load/Fan/...)
    keyword: CPU/GPU 时优先按 HardwareType 硬件类型枚举直接区分；
             匹配不到再回退到硬件名关键词；无指定类型(如 Fan)返回该类型第一个传感器。
    """
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        return None
    try:
        kw = keyword.upper()
        if kw == "CPU":
            want_types, want_names = _HW_CPU_TYPES, _HW_CPU_KEYWORDS
        elif kw == "GPU":
            want_types, want_names = _HW_GPU_TYPES, _HW_GPU_KEYWORDS
        else:
            want_types, want_names = (), (kw,) if kw else ()
        type_group = []
        name_group = []
        for name, (hw, sensor) in hardware_monitor_manager.sensors.items():
            if str(sensor.SensorType) != stype:
                continue
            if want_types and _hw_type_name(hw) in want_types:
                type_group.append((hw, sensor))
            elif want_names and any(k in hw.Name.upper() for k in want_names):
                name_group.append((hw, sensor))
            elif not want_types and not want_names:
                name_group.append((hw, sensor))
        # 优先硬件类型枚举匹配，其次名称关键词匹配
        for group in (type_group, name_group):
            if group:
                hardware_monitor_manager.update_hardwares({hw for hw, _ in group})
                for hw, s in group:
                    if s.Value is not None:
                        return s.Value
                return group[0][1].Value
    except Exception:
        pass
    return None


def _format_sensor_display(name, val):
    """把传感器全名格式化为友好显示文本：硬件名 | 类型 - 传感器名 = 值"""
    if ": " in name:
        hw_part, rest = name.split(": ", 1)
    else:
        hw_part, rest = name, name
    vtxt = "--" if val is None else ("%.1f" % val)
    return "%s | %s = %s" % (hw_part.strip(), rest, vtxt)


def _open_sensor_picker(parent, mode, title, cfg_key, type_filter=None, label_hint="", on_done=None):
    """传感器选择对话框（PySide6）。
    mode: "multi"=多选(硬件详情) / "single"=单选(仪表盘某项)
    type_filter: 传感器类型过滤（如 "Temperature"），None=全部
    on_done: 确定保存后回调（用于刷新界面显示）
    """
    global config_obj, hardware_monitor_manager
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        QMessageBox.information(parent, "提示", "硬件监控未就绪，请稍后再试。")
        return
    sensors = hardware_monitor_manager.list_sensors()
    if type_filter:
        sensors = [x for x in sensors if x[3] == type_filter]
    if not sensors:
        QMessageBox.information(
            parent, "提示",
            "未检测到%s传感器。\n主板传感器(CPU温度/风扇等)需以管理员身份运行才能读取。" % (type_filter or ""))
        return

    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumSize(480, 380)
    v = QVBoxLayout(dlg)
    if label_hint:
        hint = QLabel(label_hint)
        hint.setWordWrap(True)
        v.addWidget(hint)

    list_widget = QListWidget()
    v.addWidget(list_widget)
    list_widget.setSelectionMode(QListWidget.NoSelection)

    if mode == "multi":
        current = [n.strip() for n in (getattr(config_obj, cfg_key) or "").split(",") if n.strip()]
        checks = {}
        for name, hw, s, t, val in sensors:
            item = QListWidgetItem(_format_sensor_display(name, val))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name in current else Qt.Unchecked)
            list_widget.addItem(item)
            checks[name] = item
    else:
        current = getattr(config_obj, cfg_key) or ""
        checks = {}
        auto_item = QListWidgetItem("自动检测（推荐）")
        auto_item.setFlags(auto_item.flags() | Qt.ItemIsUserCheckable)
        auto_item.setCheckState(Qt.Checked if (not current or current == "AUTO") else Qt.Unchecked)
        list_widget.addItem(auto_item)
        checks["AUTO"] = auto_item
        for name, hw, s, t, val in sensors:
            item = QListWidgetItem(_format_sensor_display(name, val))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name == current else Qt.Unchecked)
            list_widget.addItem(item)
            checks[name] = item

    def on_ok():
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        sel = [n for n, it in checks.items() if it.checkState() == Qt.Checked]
        if mode == "multi":
            setattr(config_obj, cfg_key, ",".join(sel))
        else:
            val = sel[0] if sel else "AUTO"
            setattr(config_obj, cfg_key, "" if val == "AUTO" else val)
        save_config()
        dlg.accept()
        if on_done:
            try:
                on_done()
            except Exception:
                pass

    btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    btns.accepted.connect(on_ok)
    btns.rejected.connect(dlg.reject)
    v.addWidget(btns)
    dlg.exec()


def _resolve_gauge_sensor(cfg_key, stype, keyword=""):
    """仪表盘取值：优先使用用户指定的传感器，否则自动检测识别"""
    global config_obj, hardware_monitor_manager
    name = ""
    if cfg_key:
        try:
            name = getattr(config_obj, cfg_key) or ""
        except Exception:
            name = ""
    if name and hardware_monitor_manager is not None and hardware_monitor_manager != 1:
        if name in hardware_monitor_manager.sensors:
            hw, s = hardware_monitor_manager.sensors[name]
            try:
                hardware_monitor_manager.update_hardwares({hw})
            except Exception:
                pass
            return s.Value
    return _find_sensor_value(stype, keyword)


def show_gauge():
    """仪表盘：CPU/内存/磁盘/温度/风扇/网络速率（项目与颜色可配置，超过一页自动翻页）"""
    global config_obj, _netio_last, _netio_last_time
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    def hex2rgb(h):
        h = (h or "#ffffff").lstrip('#')
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    def get_net_speed():
        global _netio_last, _netio_last_time
        io = psutil.net_io_counters()
        now = time.monotonic()
        if _netio_last is None or _netio_last_time <= 0 or now - _netio_last_time < 0.01:
            _netio_last = io
            _netio_last_time = now
            return 0.0, 0.0
        dt = now - _netio_last_time
        up = (io.bytes_sent - _netio_last.bytes_sent) / dt / 1024.0
        down = (io.bytes_recv - _netio_last.bytes_recv) / dt / 1024.0
        _netio_last = io
        _netio_last_time = now
        return up, down

    gauges = []  # (label, value, color, kind) kind: pct/temp/fan/speed
    if config_obj.gauge_show_cpu:
        gauges.append(("CPU", psutil.cpu_percent(interval=None), hex2rgb(config_obj.gauge_cpu_color), "pct"))
    if config_obj.gauge_show_mem:
        gauges.append(("内存", psutil.virtual_memory().percent, hex2rgb(config_obj.gauge_mem_color), "pct"))
    if config_obj.gauge_show_disk:
        gauges.append(("磁盘", psutil.disk_usage('/').percent, hex2rgb(config_obj.gauge_disk_color), "pct"))
    if config_obj.gauge_show_cpu_temp:
        v = _resolve_gauge_sensor("gauge_cpu_temp_sensor", "Temperature", "CPU")
        gauges.append(("CPU温度", v, hex2rgb(config_obj.gauge_cpu_temp_color), "temp"))
    if config_obj.gauge_show_gpu_temp:
        v = _resolve_gauge_sensor("gauge_gpu_temp_sensor", "Temperature", "GPU")
        gauges.append(("GPU温度", v, hex2rgb(config_obj.gauge_gpu_temp_color), "temp"))
    if config_obj.gauge_show_gpu:
        v = _resolve_gauge_sensor("gauge_gpu_load_sensor", "Load", "GPU")
        gauges.append(("GPU", v, hex2rgb(config_obj.gauge_gpu_color), "pct"))
    if config_obj.gauge_show_fan:
        v = _resolve_gauge_sensor("gauge_fan_sensor", "Fan")
        gauges.append(("风扇", v, hex2rgb(config_obj.gauge_fan_color), "fan"))
    up, down = get_net_speed()
    if config_obj.gauge_show_upload:
        gauges.append(("上传", up, hex2rgb(config_obj.gauge_upload_color), "speed"))
    if config_obj.gauge_show_download:
        gauges.append(("下载", down, hex2rgb(config_obj.gauge_download_color), "speed"))
    if not gauges:
        gauges = [("CPU", 0, (255, 80, 80), "pct")]

    per_page = 2
    pages = max(1, (len(gauges) + per_page - 1) // per_page)
    page = int(time.monotonic() // 5) % pages  # 每5秒翻页
    gauges_page = gauges[page * per_page:(page + 1) * per_page]
    positions = [(40, 52), (120, 52)]

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)

    def draw_one(cx, cy, r, value, color, label, max_val=100, unit="%", is_pct=True):
        bbox = (cx - r, cy - r, cx + r, cy + r)
        draw.arc(bbox, start=180, end=360, fill=(60, 60, 60), width=6)
        if value is None:
            ratio = 0.0
        else:
            ratio = max(0.0, min(1.0, value / max_val if max_val > 0 else 0))
        if ratio > 0:
            angle = int(180 * ratio)
            draw.arc(bbox, start=180, end=180 + angle, fill=color, width=6)
        font = MiniMark.load_font("./simhei.ttf", 12)
        draw.text((cx - 28, cy - r - 14), label, fill=(255, 255, 255), font=font)
        font_v = MiniMark.load_font("./simhei.ttf", 14)
        if value is None:
            text = "--"
        else:
            text = "%d%%" % value if is_pct else "%.0f%s" % (value, unit)
        draw.text((cx - 18, cy + 2), text, fill=color, font=font_v)

    for i, (label, value, color, kind) in enumerate(gauges_page):
        cx, cy = positions[i]
        if kind == "pct":
            draw_one(cx, cy, 34, value, color, label, 100, "%", True)
        elif kind == "temp":
            draw_one(cx, cy, 34, value, color, label, 100, "°C", False)
        elif kind == "fan":
            draw_one(cx, cy, 34, value, color, label, 5000, "rpm", False)
        else:  # speed
            draw_one(cx, cy, 34, value, color, label, max(value * 2, 1), "K", False)

    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(0.5)


def show_hwdetail():
    """硬件详情：监控类型可配置（温度/风扇/电压/负载等），数量可配置，自动翻页"""
    global config_obj
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        draw_text("加载中…")
        dev.sleep_event.wait(0.5)
        return
    sel_names = [n.strip() for n in (config_obj.hwdetail_sensor_names or "").split(",") if n.strip()]
    items = []
    hardwares = set()
    if sel_names:
        # 用户勾选了传感器：精确显示勾选的（不受数量限制，翻页由 per_page 控制）
        for n in sel_names:
            if n in hardware_monitor_manager.sensors:
                hw, sensor = hardware_monitor_manager.sensors[n]
                items.append((n, hw, sensor, str(sensor.SensorType)))
                hardwares.add(hw)
    else:
        # 未勾选：按类型自动选择
        enabled_types = [t.strip() for t in (config_obj.hwdetail_types or "Temperature,Fan").split(",") if t.strip()]
        for name, (hw, sensor) in hardware_monitor_manager.sensors.items():
            stype = str(sensor.SensorType)
            if stype in enabled_types:
                items.append((name, hw, sensor, stype))
                hardwares.add(hw)
    hardware_monitor_manager.update_hardwares(hardwares)
    if sel_names:
        all_items = items
    else:
        max_n = max(1, int(config_obj.hwdetail_max))
        all_items = items[:max_n]

    def fmt_value(stype, val):
        if val is None:
            return "--"
        if stype == "Temperature":
            return "%.0f°C" % val
        if stype == "Fan":
            return "%.0fRPM" % val
        if stype == "Voltage":
            return "%.3fV" % val
        if stype == "Load":
            return "%.0f%%" % val
        if stype == "Power":
            return "%.1fW" % val
        if stype == "Clock":
            return "%.0fMHz" % (val / 1000000.0)
        return "%.2f" % val

    lines = []
    for n, hw, s, t in all_items:
        short = n.split(":")[-1].strip()
        lines.append("%s %s" % (short[:12], fmt_value(t, s.Value)))
    if not lines:
        lines = ["未找到传感器"]
    per_page = 5
    pages = max(1, (len(lines) + per_page - 1) // per_page)
    page = int(time.monotonic() // 4) % pages  # 每4秒翻页
    lines_page = lines[page * per_page:(page + 1) * per_page]
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 14)
    for i, line in enumerate(lines_page):
        draw.text((4, i * 15), line, fill=(255, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(1.0)


def _http_get(url, headers=None, timeout=8):
    """标准库HTTP GET，返回文本"""
    import urllib.request
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


WEATHER_DESC_MAP = {
    "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多云", "Cloudy": "多云",
    "Overcast": "阴", "Mist": "雾", "Fog": "雾", "Rain": "雨", "Light rain": "小雨",
    "Heavy rain": "大雨", "Drizzle": "毛毛雨", "Snow": "雪", "Light snow": "小雪",
    "Thunderstorm": "雷雨", "Haze": "霾",
}


def fetch_weather():
    """天气（wttr.in 免key，支持中文城市名），后台线程调用"""
    global config_obj, _weather_cache
    try:
        import json as _json
        import urllib.parse
        city = (config_obj.weather_city or "Beijing").strip()
        url = "https://wttr.in/%s?format=j1" % urllib.parse.quote(city)
        data = _json.loads(_http_get(url))
        cur = data["current_condition"][0]
        temp = cur.get("temp_C", "--")
        desc = cur.get("weatherDesc", [{}])[0].get("value", "--")
        desc = WEATHER_DESC_MAP.get(desc, desc)
        _weather_cache["data"] = "%s %s°C %s" % (city, temp, desc)
        _weather_cache["time"] = time.monotonic()
    except Exception as e:
        _weather_cache["data"] = "天气获取失败"
        _weather_cache["time"] = time.monotonic()


def _to_gate_pair(symbol):
    """把交易对转换为 Gate.io 格式（BASE_QUOTE）"""
    symbol = symbol.upper().replace("-", "_").replace("/", "_").strip()
    if "_" in symbol:
        return symbol
    for quote in ("USDT", "USDC", "BTC", "ETH", "DAI", "USD"):
        if symbol.endswith(quote) and symbol != quote:
            return symbol[:-len(quote)] + "_" + quote
    return symbol


def fetch_crypto():
    """加密货币行情（Gate.io 免key，国内可达），后台线程调用"""
    global config_obj, _crypto_cache
    try:
        import json as _json
        symbols = [s.strip() for s in (config_obj.crypto_symbols or "BTCUSDT,ETHUSDT").split(",") if s.strip()]
        lines = []
        for sym in symbols[:4]:
            pair = _to_gate_pair(sym)
            url = "https://api.gateio.ws/api/v4/spot/tickers?currency_pair=%s" % pair
            d = _json.loads(_http_get(url))
            lines.append("%s %.2f" % (sym, float(d[0]["last"])))
        _crypto_cache["data"] = lines if lines else ["未配置交易对"]
        _crypto_cache["time"] = time.monotonic()
    except Exception as e:
        _crypto_cache["data"] = ["行情获取失败"]
        _crypto_cache["time"] = time.monotonic()


def fetch_hotsearch():
    """微博热搜，后台线程调用（条数可配置）"""
    global _hot_cache, config_obj
    try:
        import json as _json
        total = 5
        try:
            total = max(1, min(30, int(config_obj.hotsearch_total)))
        except Exception:
            pass
        url = "https://weibo.com/ajax/side/hotSearch"
        data = _json.loads(_http_get(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://weibo.com/"}))
        realtime = data.get("data", {}).get("realtime", [])
        lines = []
        for item in realtime[:total]:
            word = item.get("word") or item.get("note") or item.get("word_scheme") or ""
            if word:
                lines.append(word[:16])
        _hot_cache["data"] = lines if lines else ["暂无热搜"]
        _hot_cache["time"] = time.monotonic()
    except Exception as e:
        _hot_cache["data"] = ["热搜获取失败"]
        _hot_cache["time"] = time.monotonic()


def fetch_battery():
    """电池健康度（powercfg报告），后台线程调用"""
    global _battery_cache
    try:
        import subprocess
        import tempfile
        import re
        import os
        path = os.path.join(tempfile.gettempdir(), "battery_report.xml")
        subprocess.run(["powercfg", "/batteryreport", "/output", path, "/xml"],
                       capture_output=True, timeout=15)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        design = re.search(r"<DesignCapacity>(\d+)</DesignCapacity>", content)
        full = re.search(r"<FullChargeCapacity>(\d+)</FullChargeCapacity>", content)
        if design and full:
            d = int(design.group(1))
            fv = int(full.group(1))
            health = fv * 100.0 / d if d else 0
            _battery_cache["data"] = "容量 %d/%d (%.0f%%)" % (fv, d, health)
        else:
            _battery_cache["data"] = "未检测到电池"
        _battery_cache["time"] = time.monotonic()
    except Exception as e:
        _battery_cache["data"] = "电池信息获取失败"
        _battery_cache["time"] = time.monotonic()


def fetch_music():
    """当前播放音乐（Windows媒体会话，需winsdk库），后台线程调用"""
    global _music_cache
    try:
        import ctypes
        ctypes.windll.ole32.CoInitializeEx(None, 0)
        import winsdk.windows.media.control as wmc
        sessions = wmc.GlobalSystemMediaTransportControlsSessionManager.request_async().get()
        cur = sessions.get_current_session()
        if cur is None:
            _music_cache = "无播放"
            return
        info = cur.try_get_media_properties_async().get()
        title = info.title or "未知"
        artist = info.artist or ""
        _music_cache = "%s - %s" % (title, artist)
    except ImportError:
        _music_cache = "需安装winsdk库"
    except Exception as e:
        _music_cache = "音乐获取失败"


def _refresh_cache_if_needed(cache, fetch_func, ttl=60):
    """缓存过期时在后台线程触发刷新"""
    if cache.get("data") is None or time.monotonic() - cache.get("time", 0) > ttl:
        threading.Thread(target=fetch_func, daemon=True).start()


def _refresh_page_now(page_id, cache, fetch_func):
    """设置变更后实时生效：立即刷新数据缓存；若当前设备正显示该页面则触发重绘"""
    try:
        cache["time"] = 0
        threading.Thread(target=fetch_func, daemon=True).start()
        dev = get_current_device()
        if dev is not None and dev.config is not None and dev.config.state_machine == page_id:
            dev.state_change = 1
    except Exception:
        pass


def show_weather():
    global _weather_cache
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        _weather_cache["time"] = 0  # 强制刷新
        threading.Thread(target=fetch_weather, daemon=True).start()
    _refresh_cache_if_needed(_weather_cache, fetch_weather)
    draw_text(str(_weather_cache.get("data") or "获取中…"), font_size=16)
    dev.sleep_event.wait(0.5)


def show_crypto():
    global _crypto_cache
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        _crypto_cache["time"] = 0
        threading.Thread(target=fetch_crypto, daemon=True).start()
    _refresh_cache_if_needed(_crypto_cache, fetch_crypto)
    lines = _crypto_cache.get("data") or ["获取中…"]
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 16)
    for i, line in enumerate(lines[:4]):
        draw.text((4, 4 + i * 19), line, fill=(255, 200, 0), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(0.5)


def show_hotsearch():
    """热搜：条数/字体(自动适配)/长文本滚动字幕/自动翻页/自动刷新可配置"""
    global _hot_cache, config_obj
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        _hot_cache["time"] = 0
        threading.Thread(target=fetch_hotsearch, daemon=True).start()
    # 自动刷新：开启时按间隔刷新；关闭时仅首屏抓取一次
    if config_obj.hotsearch_auto_refresh:
        try:
            ttl = max(10, int(config_obj.hotsearch_interval))
        except Exception:
            ttl = 60
        _refresh_cache_if_needed(_hot_cache, fetch_hotsearch, ttl=ttl)
    # 显示参数
    try:
        total = max(1, int(config_obj.hotsearch_total))
        count = max(1, int(config_obj.hotsearch_count))
        page_interval = max(0.5, float(config_obj.hotsearch_page_interval))
    except Exception:
        total, count, page_interval = 5, 5, 3
    try:
        font_auto = bool(config_obj.hotsearch_font_auto)
    except Exception:
        font_auto = True
    try:
        scroll_enable = bool(config_obj.hotsearch_scroll_enable)
        scroll_speed = max(0.5, float(config_obj.hotsearch_scroll_speed))
    except Exception:
        scroll_enable, scroll_speed = True, 2.0
    # 字体：自动适配屏幕（按每页条数推算字号）或手动字号
    if font_auto:
        font_size = max(8, min(40, int(SHOW_HEIGHT / max(1, count)) - 2))
    else:
        try:
            font_size = max(8, min(72, int(config_obj.hotsearch_font_size)))
        except Exception:
            font_size = 14
    lines = (_hot_cache.get("data") or ["获取中…"])[:total]
    # 每页条数不超过屏幕可容纳行数，防止字体过大/条数过多溢出
    line_h = font_size + 2
    max_fit = max(1, SHOW_HEIGHT // line_h)
    count = min(count, max_fit)
    # 自动翻页：总条数多于每页条数时按间隔轮播
    pages = max(1, (len(lines) + count - 1) // count)
    page = int(time.monotonic() // page_interval) % pages
    lines_page = lines[page * count:(page + 1) * count]
    base = page * count
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    # 自动适配：按最长文本宽度自动缩小字号，保证一页内容全部显示（无需滚动字幕）
    if font_auto:
        while font_size > 8:
            tmp_font = MiniMark.load_font("./simhei.ttf", font_size)
            longest = 0
            for i, line in enumerate(lines_page):
                w = round(draw.textlength("%d.%s" % (base + i + 1, line), font=tmp_font))
                if w > longest:
                    longest = w
            if longest <= SHOW_WIDTH - 4:
                break
            font_size -= 1
        scroll_enable = False  # 自动适配已保证全部放下，无需滚动
    font = MiniMark.load_font("./simhei.ttf", font_size)
    line_h = font_size + 2  # 字号可能已缩小，重算行高
    # 垂直居中布局：一页内容不足一屏时整体居中，避免文字偏上
    start_y = max(0, (SHOW_HEIGHT - len(lines_page) * line_h) // 2)
    for i, line in enumerate(lines_page):
        y = start_y + i * line_h
        text = "%d.%s" % (base + i + 1, line)
        tw = round(draw.textlength(text, font=font))
        if tw > SHOW_WIDTH - 4 and scroll_enable:
            # 手动字号且长文本：滚动字幕，速度可调
            total_w = tw + 20
            offset = int(time.monotonic() * scroll_speed * 10) % total_w
            x = SHOW_WIDTH - offset
            draw.text((x, y), text, fill=(255, 255, 255), font=font)
            if x + tw < SHOW_WIDTH:
                draw.text((x + tw + 20, y), text, fill=(255, 255, 255), font=font)
        else:
            # 放得下或未开启滚动：超长则截断加省略号
            if tw > SHOW_WIDTH - 4:
                while text and round(draw.textlength(text + "…", font=font)) > SHOW_WIDTH - 4:
                    text = text[:-1]
                text += "…"
            draw.text((4, y), text, fill=(255, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(0.5)


def show_battery():
    global _battery_cache
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        _battery_cache["time"] = 0
        threading.Thread(target=fetch_battery, daemon=True).start()
    _refresh_cache_if_needed(_battery_cache, fetch_battery, ttl=300)
    draw_text(str(_battery_cache.get("data") or "获取中…"), font_size=16)
    dev.sleep_event.wait(0.5)


def show_music():
    global _music_cache
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        threading.Thread(target=fetch_music, daemon=True).start()
    draw_text(str(_music_cache), font_size=16)
    dev.sleep_event.wait(1.0)


def show_about():
    """在LCD屏幕上显示关于信息"""
    global config_obj
    dev = get_current_device()
    if dev is None: return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    about_lines = get_about_lines()
    font_size = max(10, min(14, SHOW_HEIGHT // (len(about_lines) + 1)))
    line_height = font_size + 2

    back_color = (0, 0, 0)
    front_color = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back_color)
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", font_size)

    total_height = line_height * len(about_lines)
    start_y = (SHOW_HEIGHT - total_height) // 2
    for i, line in enumerate(about_lines):
        if line == "":
            start_y += line_height // 2
            continue
        try:
            text_width = round(draw.textlength(line, font=font))
        except Exception:
            text_width = font_size * len(line) // 2
        x = (SHOW_WIDTH - text_width) // 2
        y = start_y + i * line_height
        draw.text((max(0, x), y), line, fill=front_color, font=font)

    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)

    dev.sleep_event.wait(3)  # 静态页面，3秒刷新一次即可


def get_formatted_time_string(time):
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load_task():
    global hardware_monitor_manager, PAGE_ID
    try:
        HardwareMonitorManager = load_hardware_monitor()
        hardware_monitor_manager = HardwareMonitorManager()
        PAGE_ID[CUSTOM1_PAGE_ID] = PAGE_ID_EN[CUSTOM1_PAGE_ID] if config_obj.language == "English" else PAGE_ID_CN[CUSTOM1_PAGE_ID]
        PAGE_ID[CUSTOM2_PAGE_ID] = PAGE_ID_EN[CUSTOM2_PAGE_ID] if config_obj.language == "English" else PAGE_ID_CN[CUSTOM2_PAGE_ID]
        # 按页面ID排序，保持翻页顺序正确（先备份items再清空，避免clear后items为空）
        new_PAGE_ID = sorted(PAGE_ID.items(), key=lambda a: a[0])
        PAGE_ID.clear()
        PAGE_ID.update(new_PAGE_ID)
        print("Libre hardware monitor load successed")
    except Exception as e:
        hardware_monitor_manager = 1
        print("Libre hardware monitor 加载失败，%s" % traceback.format_exc())


_force_rescan_now = False  # 手动"连接"按钮置 True，daemon 下一轮立即重扫设备（默认仍自动连接）
_auto_connect = True       # "设为自动连接"开关（UI 第三层主控页勾选框），默认自动连接


def daemon_task():
    global Device_State_Labelen, screen_off, last_key_activity_time, config_obj, preferred_com_port, _force_rescan_now, _auto_connect
    last_key_activity_time = time.monotonic()  # 初始化按键活动时间，避免启动即触发息屏
    known_com_ports = set()  # 已连接的COM端口集合
    retry_times = 0
    last_scan_time = 0
    print("Start daemon")
    # 启动诊断：扫描所有WCH设备并打印USB描述符
    port_list = list(serial.tools.list_ports.comports())
    wch_ports = [x for x in port_list if x.vid == 0x1a86]
    if wch_ports:
        print("--- 检测到 %d 个WCH设备 ---" % len(wch_ports))
        for p in wch_ports:
            _dump_usb_descriptor(p)
    else:
        print("--- 未检测到WCH设备 (VID=0x1A86) ---")
    while MG_daemon_running:
        try:
            # 多设备模式：遍历所有已连接设备，各自运行状态机
            for dev_id, device in list(all_devices.items()):
                if device.device_state == 1:
                    set_current_device(device)
                    # 每屏独立配置：渲染该屏前切换为其自己的配置
                    set_active_device_config(device)
                    # 屏幕待机/息屏：超过设定时间无按键操作则息屏，按键后由manage_task唤醒
                    if config_obj.screen_off_timeout > 0:
                        if not screen_off and time.monotonic() - last_key_activity_time > config_obj.screen_off_timeout:
                            screen_off = True
                            LCD_Color_set(0, 0, device.LCD_MAX_X, device.LCD_MAX_Y, BLACK)
                        if screen_off:
                            continue  # 息屏状态下跳过页面渲染
                    MSN_Device_1_State_machine()
            
            # 检查是否有已连接设备
            has_connected = any(d.device_state == 1 for d in all_devices.values())
            if has_connected:
                if _primary_device:
                    set_current_device(_primary_device)
                    # 渲染完一轮后把全局配置切回UI当前设备（_primary），
                    # 避免UI主控/设置操作误改到其他设备的独立配置
                    set_active_device_config(_primary_device)
                # 定期重新扫描（可能有新设备插入）；手动"连接"按钮可触发立即重扫
                now = time.monotonic()
                if now - last_scan_time < 5 and not _force_rescan_now:
                    continue
                last_scan_time = now
                _force_rescan_now = False
            
            # 无设备连接或定期扫描：检测新设备
            if Device_State_Labelen == 2:
                if _primary_device:
                    set_current_device(_primary_device)
                set_device_state(_primary_device.device_state if _primary_device else 0)

            if _primary_device is None:
                _init_single_device()

            if not _auto_connect:
                # 已关闭自动连接：不扫描新设备，仅渲染已连接设备
                time.sleep(0.5)
                continue

            port_list = list(serial.tools.list_ports.comports())
            wch_port_list = [x for x in port_list if x.vid == 0x1a86]
            if preferred_com_port:
                wch_port_list.sort(key=lambda p: 0 if p.device.upper() == preferred_com_port else 1)

            # 设备断开后允许自动重连：清除已断开设备对应的端口，
            # 否则known_com_ports一直保留导致掉线后不再扫描该端口
            disconnected_ports = {d.com_port for d in all_devices.values()
                                  if d.device_state == 0 and d.com_port}
            for pk in list(known_com_ports):
                if pk in disconnected_ports:
                    known_com_ports.discard(pk)

            # 检测新设备：对每个未连接的WCH端口尝试连接
            new_device_found = False
            for port in wch_port_list:
                port_key = port.device
                if port_key in known_com_ports:
                    continue  # 已连接过的端口，跳过

                # 关键：每处理一个端口前实时更新连接状态。
                # 否则前一个端口连接成功后 has_connected 仍为 False，
                # 第二个端口会误用主设备对象覆盖第一个设备的串口（多屏只认1个）。
                has_connected = any(d.device_state == 1 for d in all_devices.values())

                # 尝试连接此端口
                if _primary_device.device_state == 0 or _primary_device.com_port != port_key:
                    # 创建临时设备用于检测
                    if not has_connected:
                        set_current_device(_primary_device)
                        Get_MSN_Device([port])
                        if _primary_device.device_state == 1:
                            known_com_ports.add(port_key)
                            _primary_device.com_port = port_key
                            # 启动截图线程
                            _primary_device.start_threads()
                            new_device_found = True
                    else:
                        # 已有设备连接，为新设备创建新的ScreenDevice
                        # 若同端口有断开设备则复用，避免设备索引漂移（屏幕1/2/3...）
                        reused = next((d for d in all_devices.values()
                                       if d.com_port == port_key and d.device_state == 0), None)
                        if reused is not None:
                            new_dev = reused
                            set_current_device(new_dev)
                            Get_MSN_Device([port])
                            if new_dev.device_state == 1:
                                known_com_ports.add(port_key)
                                new_dev.init_arrays()
                                new_dev.start_threads()
                                new_device_found = True
                                insert_text_message("设备重连: %s → %s" % (port_key, new_dev.device_name))
                        else:
                            new_idx = len(all_devices)
                            new_dev = ScreenDevice(new_idx, port_key)
                            all_devices[new_idx] = new_dev
                            set_current_device(new_dev)
                            Get_MSN_Device([port])
                            if new_dev.device_state == 1:
                                known_com_ports.add(port_key)
                                new_dev.init_arrays()
                                new_dev.start_threads()
                                new_device_found = True
                                insert_text_message("新设备连接: %s → 屏幕%d" % (port_key, new_idx + 1))
                            else:
                                del all_devices[new_idx]

            if new_device_found:
                retry_times = 0
                continue

            # 没有新设备，也没有已连接设备
            if not has_connected:
                if wch_port_list:
                    retry_times += 1
                    if retry_times >= 5:
                        if _primary_device.sleep_event.is_set():
                            _primary_device.sleep_event.clear()
                        _primary_device.sleep_event.wait(1)
                        if (retry_times % 5) != 0:
                            continue
                else:
                    if retry_times == 0:
                        print(get_formatted_time_string(datetime.now()), end=' ')
                        insert_text_message("没有找到可用的设备，请确认设备是否正确连接")
                    retry_times += 1
                    if _primary_device.sleep_event.is_set():
                        _primary_device.sleep_event.clear()
                    _primary_device.sleep_event.wait(0.5)
        except Exception as e:
            print("Exception in daemon_task, %s" % traceback.format_exc())
            if _primary_device:
                if _primary_device.sleep_event.is_set():
                    _primary_device.sleep_event.clear()
                _primary_device.sleep_event.wait(1)

    print("Stop daemon")


# 检测按键是否被按下，兼具心跳功能
# 单击：下一页
# 双击：上一页
# 长按：切换方向
def manage_task():
    global screen_off, last_key_activity_time
    dev = get_current_device()
    if dev is None:
        dev = _primary_device
    if dev is None:
        return
    ADC_det = dev.ADC_det  # 本地引用，方便函数内使用
    now = time.monotonic()
    key_on = 0
    check_limit = 2.0
    key_on_limit = 0.5
    double_key_limit = 0.7
    last_check_time = now - check_limit
    first_press_time = 0
    print("Start manager")
    while MG_daemon_running:
        if dev.device_state == 0:
            time.sleep(0.3)
            continue

        try:
            now = time.monotonic()
            # 串口渲染事务中（帧/页面发送期间）跳过按键ADC轮询，避免命令流交错导致画面倾斜
            if getattr(dev, "serial_busy", False):
                time.sleep(0.02)
                continue
            ADC_ch = Read_ADC_CH(9)
            if ADC_ch == 0:
                continue
            if ADC_ch < ADC_det:
                if Read_ADC_CH(9) > ADC_det or Read_ADC_CH(9) > ADC_det:
                    continue

                if ADC_det - ADC_ch > 900:
                    ADC_det = ADC_ch - 250
                    dev.ADC_det = ADC_det
                    print("校正按下检测阈值为：%d" % ADC_det)
                    continue

                if key_on == 0:
                    last_key_activity_time = now
                    if screen_off:
                        screen_off = False
                        state_change_set()
                    ADC_det += 150
                    key_on = 1
                    if first_press_time != 0:
                        if now - first_press_time < double_key_limit:
                            if config_obj.state_machine == TIMER_PAGE_ID:
                                reset_timer()
                            else:
                                do_key_action(config_obj.key_double)
                            first_press_time = 1
                    else:
                        first_press_time = now
                else:
                    if first_press_time != 1:
                        if first_press_time != 0:
                            if now - first_press_time > key_on_limit:
                                do_key_action(config_obj.key_long)
                                first_press_time = 1
                        else:
                            first_press_time = now
            else:
                if key_on != 0:
                    if Read_ADC_CH(9) < ADC_det or Read_ADC_CH(9) < ADC_det:
                        continue
                    ADC_det -= 150
                    dev.ADC_det = ADC_det
                    key_on = 0
                    last_check_time = now
                    if first_press_time == 1:
                        first_press_time = 0
                elif now - last_check_time > check_limit:
                    if ADC_ch - ADC_det > 40 + 250:
                        ADC_det = (ADC_det + ADC_ch - 250) // 2
                        dev.ADC_det = ADC_det
                        print("校正按键检测阈值为：%d" % ADC_det)
                    time.sleep(0.1)
                else:
                    if first_press_time != 0:
                        if now - first_press_time > double_key_limit:
                            if config_obj.state_machine == TIMER_PAGE_ID:
                                toggle_timer()
                            else:
                                do_key_action(config_obj.key_single)
                            first_press_time = 0
        except Exception as e:
            print("Exception in manage_task, %s" % traceback.format_exc())
        finally:
            # 限制ADC轮询频率，避免与屏幕镜像的帧发送争抢串口带宽
            time.sleep(0.05)

    print("Stop manager")


Img_data_use = None

cleanNextTime = False

# 以下全局已迁移到 ScreenDevice，保留声明仅为向后兼容
sleep_event = None
SER_lock = None
custom_render_lock = None
last_refresh_time = 0
gif_wait_time = 0.0
second_pass = 0
screen_shot_queue = None
screen_process_queue = None
screen_frame_generation = 0
desktop_hwnd = 0
all_windows = None
all_cameras = None
row_np_zero = None
column_np_zero = None
screenshot_test_time = 0
screenshot_test_frame = 1
screenshot_last_limit_time = 0
wait_time = 0.0
netspeed_last_refresh_snetio = None
netspeed_plot_data = None
custom_plot_data = None
diskio_plot_data = None
mini_mark_parser = None
full_custom_error = "OK"
netspeed_font_size = 20
default_font = None
netspeed_font = None

config_file = "MSU2_MINI.json"
last_config_save_time = 0  # 最后一次保存时间
save_thread = None
config_event = None
config_obj = None

# 多线程/自动化相关全局状态
preferred_com_port = ""  # --com 命令行参数指定的优先串口
screen_off = False  # 屏幕待机/息屏状态
last_key_activity_time = 0.0  # 最近一次按键活动时间
_last_cycle_time = 0.0  # 自动翻页轮播上次执行时间

# 新增页面相关全局状态
ping_result = "检测中…"  # 后台ping结果
ping_thread = None  # ping后台线程
marquee_offset = 0  # 跑马灯滚动偏移
diskio_last = None  # 磁盘IO上次采样
diskio_last_time = 0.0  # 磁盘IO上次采样时间
timer_remaining = 0  # 番茄钟剩余秒数
timer_running = True  # 番茄钟运行状态
timer_last_tick = 0.0  # 番茄钟上次计时

# 网络/耗时数据缓存
_weather_cache = {"data": None, "time": 0.0}
_crypto_cache = {"data": None, "time": 0.0}
_hot_cache = {"data": None, "time": 0.0}
_battery_cache = {"data": None, "time": 0.0}
_music_cache = "无播放"
_netio_last = None  # 仪表盘网络速率上次采样
_netio_last_time = 0.0

State_change = 1  # 旧全局（向后兼容），实际值在 ScreenDevice.state_change 中
force_lcd_reset = False  # 旧全局（向后兼容），实际值在 ScreenDevice.force_lcd_reset 中
last_lcd_watchdog_time = 0  # 旧全局（向后兼容）
gif_num = 0  # 旧全局（向后兼容）
Device_State = 0  # 旧全局（向后兼容），实际值在 ScreenDevice.device_state 中
Device_State_Labelen = 0  # UI标签状态
LCD_Change_now = 0  # 旧全局（向后兼容），实际值在 ScreenDevice.lcd_change_now 中
color_use = RED  # 旧全局（向后兼容），实际值在 ScreenDevice.color_use 中
write_path_index = 0

back_color = (0, 0, 0)
bar_colors = [(235, 139, 139), (146, 212, 217)]

Label1 = None
Label3 = None; Label4 = None; Label5 = None; Label6 = None
Text1 = None
windows_combobox = None
interval_var = None
lcd_size_var = None
ser = None  # 旧全局（向后兼容），实际值在 ScreenDevice.ser 中
ADC_det = 0  # 旧全局（向后兼容），实际值在 ScreenDevice.ADC_det 中
sub_window = None
hardware_monitor_manager = None
My_MSN_Device = None  # 旧全局（向后兼容），实际值在 ScreenDevice.msn_device 中
My_MSN_Data = None     # 旧全局（向后兼容），实际值在 ScreenDevice.msn_data 中
My_MSN_Device = None  # 当前连接的MSN设备信息
My_MSN_Data = None     # 当前设备的SFR数据描述表
page_combobox = None   # UI中页面选择下拉列表
lcd_direction_combobox = None  # UI中显示方向选择下拉列表

# print("该设备具有%d个内核和%d个逻辑处理器" % (psutil.cpu_count(logical=False), psutil.cpu_count()))
# print("该CPU主频为%.1fGHZ" % (psutil.cpu_freq().current / 1000))
# print("当前CPU占用率为%s%%" % psutil.cpu_percent())
# mem = psutil.virtual_memory()
# print("该设备具有%.0fGB的内存" % (mem.total / (1024 * 1024 * 1024)))
# print("当前内存占用率为%s%%" % mem.percent)
# battery = psutil.sensors_battery()
# if battery is not None:
#     print("电池剩余电量%d%%" % battery.percent)
# print("系统启动时间%s" % get_formatted_time_string(datetime.fromtimestamp(psutil.boot_time())))
# print("程序启动时间%s" % get_formatted_time_string(datetime.now()))

if __name__ == "__main__":
    exit_code = 0
    try:
        # 初始化主设备（单屏兼容模式）
        _init_single_device()
        primary = _primary_device
        set_current_device(primary)
        primary.init_arrays()
        primary.last_refresh_time = time.monotonic()
        primary.screenshot_last_limit_time = primary.last_refresh_time
        
        last_refresh_time = primary.last_refresh_time
        screenshot_test_time = last_refresh_time
        screenshot_last_limit_time = last_refresh_time
        
        config_event = threading.Event()
        screen_shot_queue = primary.screen_shot_queue
        screen_process_queue = primary.screen_process_queue

        # 迁移旧配置（程序根目录）到 config 子目录，再设置主配置路径
        migrate_old_config()
        config_file = os.path.normpath(os.path.join(get_config_dir(), os.path.basename(config_file)))
        config_obj = sys_config()
        mini_mark_parser = MiniMarkParser()
        default_font = MiniMark.load_font("./simhei.ttf", netspeed_font_size)
        netspeed_font = MiniMark.load_font("resource/Orbitron-Bold.ttf", netspeed_font_size - 4)

        row_np_zero = primary.row_np_zero
        column_np_zero = primary.column_np_zero
        netspeed_plot_data = primary.netspeed_plot_data
        custom_plot_data = primary.custom_plot_data
        diskio_plot_data = primary.diskio_plot_data

        MG_daemon_running = True
        primary.mg_screen_thread_running = True
        MG_screen_thread_running = True
        daemon_thread = threading.Thread(target=daemon_task, daemon=True)
        load_thread = threading.Thread(target=load_task, daemon=True)
        manager_thread = threading.Thread(target=manage_task, daemon=True)
        ping_thread = threading.Thread(target=ping_worker, daemon=True)
        primary.screen_shot_thread = threading.Thread(target=screen_shot_task, args=(primary,), daemon=True)
        primary.screen_process_thread = threading.Thread(target=screen_process_task, args=(primary,), daemon=True)

        # 附加接入：stdin 管道（当通过管道/重定向启动时，从标准输入按行读取 JSON 命令执行）
        try:
            if sys.stdin is not None and hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
                threading.Thread(target=_api_stdin_loop, daemon=True).start()
        except Exception:
            pass

        # 打开主页面
        UI_Page()
    except Exception as e:
        exit_code = 1
        message = "Error: %s" % traceback.format_exc()
        print(message)
        # 崩溃日志：记录完整堆栈到程序目录 crash_log.txt
        try:
            crash_log = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "crash_log.txt")
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write("===== %s =====\n%s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), traceback.format_exc()))
        except Exception:
            pass
        try:
            QMessageBox.critical(None, "错误", message)
        except Exception:
            pass
    finally:
        MG_screen_thread_running = False
        MG_daemon_running = False
        if _primary_device:
            _primary_device.mg_screen_thread_running = False
            _primary_device.sleep_event.set()
        # 先停止并等待所有工作线程退出，避免清理LCD时帧发送仍在进行，
        # 导致串口被并发关闭而产生“分块写入不完整”报错
        if daemon_thread.is_alive():
            daemon_thread.join(timeout=5.0)
        if manager_thread.is_alive():
            manager_thread.join(timeout=5.0)
        if _primary_device and _primary_device.screen_process_thread and _primary_device.screen_process_thread.is_alive():
            _primary_device.screen_process_thread.join(timeout=5.0)
        if _primary_device and _primary_device.screen_shot_thread and _primary_device.screen_shot_thread.is_alive():
            _primary_device.screen_shot_thread.join(timeout=5.0)
        stop_api_server()
        # 退出前清理LCD屏幕，避免残留花屏
        Cleanup_LCD_On_Exit()
        if _primary_device and _primary_device.ser is not None and _primary_device.ser.is_open:
            print("%s close" % _primary_device.ser.name)
            _primary_device.ser.close()
        # 结束时保存配置：等待写盘线程真正完成再退出，
        # 否则daemon保存线程可能随进程退出被杀，导致本次修改（如强制投屏）未写入配置文件
        save_config(True)
        if save_thread is not None and save_thread.is_alive():
            save_thread.join(timeout=5.0)
        if load_thread.is_alive():
            load_thread.join(timeout=5.0)

        sys.exit(exit_code)































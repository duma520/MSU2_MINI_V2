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
import tkinter as tk  # 引入UI库
import tkinter.filedialog  # 用于获取文件路径
import tkinter.font as tkfont
import tkinter.messagebox
import tkinter.colorchooser
import traceback
from datetime import datetime  # 用于获取当前时间
from tkinter import ttk  # geezmo: 好看的皮肤

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

    # 使用高dpi缩放适配高分屏。0：不使用缩放 1：所有屏幕 2：当前屏幕
    try:  # >= win 8.1
        windll.shcore.SetProcessDpiAwareness(1)
    except:  # win 8.0 or less
        try:
            windll.user32.SetProcessDPIAware()
        except:
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
PROGRAM_VERSION = "4.6.1"
PROGRAM_AUTHOR = "杜玛"
PROGRAM_GITHUB = "https://github.com/duma520/MSU2_MINI_V2"
PROGRAM_LICENSE = "MIT"
PROGRAM_BUILD_DATE = "2026-08-16"

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
        item.config(state=tk.NORMAL)
        if clean:
            item.delete("1.0", tk.END)  # 清除文本框
        item.insert(tk.END, text)
        item.config(state=tk.DISABLED)
        item.see(tk.END)
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
            _ui_root.after(100, _process_ui_msg_queue)
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
    if index == 1:
        photo_path = tk.filedialog.askopenfilename(
            title="选择文件", filetypes=[("Bin file", "*.bin")])
        insert_text_message(photo_path, item=Label3)
    elif index == 2:
        photo_path = tk.filedialog.askopenfilename(
            title="选择文件", filetypes=IMAGE_FILE_TYPES + [("Image file", "*.gif")])
        insert_text_message(photo_path, item=Label4)
    elif index == 3:
        photo_path = tk.filedialog.askopenfilename(
            title="选择文件", filetypes=IMAGE_FILE_TYPES + [("Image file", "*.gif")])
        insert_text_message(photo_path, item=Label5)
    elif index == 4:
        photo_path = tk.filedialog.askopenfilename(
            title="选择文件", filetypes=[("Gif file", "*.gif")] + IMAGE_FILE_TYPES)
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
    global Label3, write_path_index, sleep_event
    photo_path = Label3.get("1.0", tk.END).rstrip()
    if not photo_path:
        insert_text_message("闪存固件未选择")
        return
    insert_text_message("准备烧写Flash固件…", cleanNext=False)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 1


def Write_Photo_Path2():  # 写入文件
    global config_obj, Label4, write_path_index, Img_data_use, sleep_event
    photo_path = Label4.get("1.0", tk.END).rstrip()
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
    global config_obj, Label5, write_path_index, Img_data_use, sleep_event
    photo_path = Label5.get("1.0", tk.END).rstrip()
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
    global config_obj, Label6, interval_var, write_path_index, Img_data_use, sleep_event
    photo_path = Label6.get("1.0", tk.END).rstrip()
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
            if realduration >= 10:
                duration_string = "%.4f" % (realduration / 1000.0)
                massage = "建议动图间隔：%s" % duration_string
                interval_var.set(duration_string)
            else:
                massage = "动图太短，不建议使用此动图"
                interval_var.set("0.1")
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


def sync_page_combobox():
    """同步页面下拉列表的显示值（基于当前设备配置）"""
    global page_combobox, config_obj
    if page_combobox is not None:
        try:
            page_combobox['values'] = list(PAGE_ID.values())
            dev = get_current_device()
            cfg = dev.config if dev is not None and dev.config is not None else config_obj
            page_name = PAGE_ID.get(cfg.state_machine, "")
            page_combobox.set(page_name)
        except Exception:
            pass


def on_page_combobox_select(event):
    """用户通过下拉列表选择页面（仅作用于当前选中设备）"""
    global config_obj, page_combobox
    dev = get_current_device()
    event.widget.selection_clear()
    selected_name = page_combobox.get()
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
    global lcd_direction_combobox, config_obj
    if lcd_direction_combobox is not None:
        try:
            dev = get_current_device()
            cfg = dev.config if dev is not None and dev.config is not None else config_obj
            lcd_direction_combobox.set(LCD_STATE_MESSAGE[cfg.lcd_change])
        except Exception:
            pass


def apply_language():
    """切换界面语言（页面名称与方向名称）"""
    global config_obj, lcd_direction_combobox
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
    if lcd_direction_combobox is not None:
        try:
            lcd_direction_combobox['values'] = list(LCD_STATE_MESSAGE)
        except Exception:
            pass
    sync_lcd_combobox()


def on_lcd_direction_select(event):
    """用户通过下拉列表选择显示方向"""
    global config_obj, lcd_direction_combobox
    event.widget.selection_clear()
    selected = lcd_direction_combobox.get()
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
    while len(recv) == 0:
        if time.monotonic() >= deadline:
            print("SER_Read timeout")
            return 0
        n = ser.in_waiting
        if n > 0:
            recv.extend(ser.read(n))
            break
        time.sleep(0.005)
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
        print("串口读写异常，%s" % e)
        ser.close()
    finally:
        SER_lock.release()
    # 释放锁后再处理异常
    device.set_device_state(0)
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
    global config_obj, windows_combobox
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
    if windows_combobox is not None:
        windows_combobox.set(desc)


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
        if dev.device_state != 1 or (config_obj.state_machine != SCREEN_PAGE_ID
                                 and config_obj.state_machine != CAMERA_VIDEO_ID):
            if not dev.screen_shot_queue.empty():
                time.sleep(0.5)
                clear_queue(dev.screen_shot_queue)
            time.sleep(0.5)
            continue
        if dev.screen_shot_queue.full():
            time.sleep(1.0 / config_obj.fps_var)

        try:
            if config_obj.state_machine == CAMERA_VIDEO_ID:
                camera_id = all_cameras.get(config_obj.camera_var)
                if camera_id is None:
                    rgb888 = get_draw_text("请选择相机…")
                    image = Win32_Image(rgb=rgb888, size=(dev.LCD_MAX_X, dev.LCD_MAX_Y))
                    dev.screen_shot_queue.put((image, {"width": dev.LCD_MAX_X, "height": dev.LCD_MAX_Y}), timeout=1)
                    time.sleep(0.5)
                    continue

                rgb888 = get_draw_text("打开中…")
                image = Win32_Image(rgb=rgb888, size=(dev.LCD_MAX_X, dev.LCD_MAX_Y))
                dev.screen_shot_queue.put((image, {"width": dev.LCD_MAX_X, "height": dev.LCD_MAX_Y}), timeout=1)
                camera_name = config_obj.camera_var
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
                               and config_obj.state_machine == CAMERA_VIDEO_ID
                               and camera_name == config_obj.camera_var):
                            cap_hue = cap.get(cv2.CAP_PROP_HUE)
                            if cap_hue == 13:
                                time.sleep(1)
                                raise Exception("get CAP_PROP_HUE failed")
                            if dev.screen_shot_queue.full():
                                time.sleep(1.0 / config_obj.fps_var)
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
                                time.sleep(1.0 / config_obj.fps_var)
                                continue
                            fps_control(dev)
                    else:
                        raise Exception("capture open failed")
                finally:
                    cap.release()
            elif isWindows:
                if config_obj.zoom_enable:
                    # 放大镜模式：截取鼠标周围区域并放大显示
                    try:
                        import win32api
                        x, y = win32api.GetCursorPos()
                    except Exception:
                        x, y = 0, 0
                    scale = max(1, int(config_obj.zoom_scale))
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
                    sct_img = get_window_image(config_obj.select_window_hwnd)
                    dev.screen_shot_queue.put((sct_img, {"width": sct_img.size[0], "height": sct_img.size[1]}), timeout=1)
            else:
                sct_img = _thread_mss.grab(cropped_monitor)
                dev.screen_shot_queue.put((sct_img, cropped_monitor), timeout=1)
        except queue.Full:
            time.sleep(1.0 / config_obj.fps_var)
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
    current_monoto_time = time.monotonic()
    elapse_time = current_monoto_time - dev.screenshot_last_limit_time
    if elapse_time > 5:
        dev.wait_time = 0
        elapse_time = 1.0 / config_obj.fps_var

    dev.screenshot_last_limit_time = current_monoto_time
    dev.wait_time += 1.0 / config_obj.fps_var - elapse_time
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
        if dev.device_state != 1 or (config_obj.state_machine != SCREEN_PAGE_ID
                                 and config_obj.state_machine != CAMERA_VIDEO_ID):
            if not dev.screen_process_queue.empty():
                time.sleep(0.5)
                clear_queue(dev.screen_process_queue)
            time.sleep(0.5)
            continue

        try:
            if dev.screen_process_queue.full():
                time.sleep(1.0 / config_obj.fps_var)

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
            if config_obj.shrink_type == 1:
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
            if config_obj and config_obj.preview_enabled:
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
    """停止指定屏投屏：停止轮播 + 清屏 + 回到 API 投屏页，返回响应 dict"""
    api_stop_slideshow(device)
    api_set_frame(None, device)
    try:
        dev = device if device is not None else get_current_device()
        if dev is not None:
            set_active_device_config(dev)
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
        elif cmd == "mirror":
            return api_apply_mirror(data, dev)
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
            "description": "USB 副屏工具的外部接入接口。支持 HTTP REST / WebSocket / SSE(/api/events) / TCP(JSON行,端口+1) / UDP(JSON报,端口+2) / ZeroMQ(REP,端口+3,需pyzmq) / Windows命名管道(\\\\\\.\\\\pipe\\\\MSU2_MINI_V2_api) / Unix Domain Socket(api_unix.sock) / 热文件夹 投屏。可自定义投屏内容（图像、文本、清屏、切页、多图轮播、窗口投屏、实时帧）。屏幕分辨率 %dx%d。%s"
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
    不一致时打印警告，提醒开发者同步更新 JSON 文档。"""
    try:
        import inspect as _inspect
        import re as _re
        code_routes = set()
        for method in ("do_GET", "do_POST"):
            try:
                src = _inspect.getsource(getattr(ApiHandler, method))
                code_routes.update(_re.findall(r'"(/api/[a-z_/]*|/ws)"', src))
            except Exception:
                pass
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


# now 是否立即保存
def save_config(now=False):
    global last_config_save_time, save_thread, config_event
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
    path = tkinter.filedialog.asksaveasfilename(defaultextension=".json",
                                                filetypes=[("配置文件", "*.json")], title="导出配置")
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
    path = tkinter.filedialog.askopenfilename(filetypes=[("配置文件", "*.json")], title="导入配置")
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
    """重新检测LCD分辨率"""
    insert_text_message('正在重新检测屏幕分辨率...')
    Detect_LCD_Size()
    dev = get_current_device()
    if dev is not None:
        dev.state_change = 1


def Set_LCD_Size_Manual(*args):
    """手动设置LCD分辨率"""
    global LCD_MAX_X, LCD_MAX_Y, lcd_size_var
    dev = get_current_device()
    _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
    size_str = lcd_size_var.get()
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

def UI_Page():  # 进行图像界面显示
    global config_obj, Text1, interval_var, all_windows, all_cameras, windows_combobox
    global Label1, Label3, Label4, Label5, Label6, PAGE_ID

    config_obj = load_config()
    apply_command_line_args()  # 应用命令行参数（--page/--com）
    apply_language()  # 应用界面语言设置
    pad_scale_xy = scale_factor / 100.0
    pad_scale_xy5 = pad_scale_xy * 5

    # 创建主窗口
    window = tk.Tk()  # 实例化主窗口
    # window.tk.call('tk', 'scaling', pad_scale_xy)
    window.title(f"{PROGRAM_TITLE} v{PROGRAM_VERSION} - {PROGRAM_SUBTITLE} - {PROGRAM_GITHUB}")  # 设置标题

    # 设置主窗口引用并启动UI消息队列轮询（工作线程→主线程安全更新界面）
    global _ui_root
    _ui_root = window
    window.after(100, _process_ui_msg_queue)

    # 修改默认图标
    if scale_factor < 200:
        iconimage = MiniMark.load_image("resource/icon_small.ico")
    else:
        iconimage = MiniMark.load_image("resource/icon.ico")
    defaulticon = ImageTk.PhotoImage(iconimage)
    window.wm_iconphoto(True, defaulticon)

    # ==================== 多设备选择栏 ====================
    device_bar = ttk.Frame(window)
    device_bar.pack(side=tk.TOP, fill=tk.X, padx=pad_scale_xy5 * 2, pady=(pad_scale_xy5, 0))
    
    ttk.Label(device_bar, text="已连接设备:").pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    
    device_selector_var = tk.StringVar(window, "屏幕1")
    device_selector = ttk.Combobox(device_bar, textvariable=device_selector_var, 
                                   values=["屏幕1"], state="readonly", width=10)
    device_selector.pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    
    device_count_label = ttk.Label(device_bar, text="(0个设备)", foreground="gray")
    device_count_label.pack(side=tk.LEFT)
    
    def refresh_device_list():
        """刷新设备列表下拉框"""
        connected = [d for d in all_devices.values() if d.device_state == 1]
        names = [d.device_name for d in connected] if connected else ["屏幕1"]
        device_selector["values"] = names
        device_count_label.config(text="(%d个设备)" % len(connected))
        if device_selector_var.get() not in names:
            device_selector_var.set(names[0])
    
    def on_device_select(event=None):
        """切换当前活跃设备（每屏独立配置/页面）"""
        global config_obj, _primary_device
        name = device_selector_var.get()
        old = _primary_device
        for dev in all_devices.values():
            if dev.device_name == name and dev.device_state == 1:
                # 保存旧设备页面到其自身配置（每屏记住自己的页面）
                if old is not None and old != dev:
                    old.state_machine = config_obj.state_machine
                set_current_device(dev)
                _primary_device = dev
                # 切换为该屏独立配置（config_obj/config_file 指向本屏配置）
                set_active_device_config(dev)
                config_obj.state_machine = getattr(dev, "state_machine", SCREEN_PAGE_ID)
                state_change_set(save=False)
                sync_page_combobox()
                sync_lcd_combobox()
                # 刷新主控页/设置页控件为当前屏配置
                try:
                    _apply_main_ui_to_config()
                except Exception:
                    pass
                try:
                    _apply_settings_ui_to_config()
                except Exception:
                    pass
                # 更新镜像窗口下拉框
                desc = get_hwnd_desc(config_obj.select_window_hwnd)
                if desc:
                    windows_combobox.set(desc)
                break
    
    device_selector.bind("<<ComboboxSelected>>", on_device_select)
    
    refresh_btn = ttk.Button(device_bar, text="刷新", width=6, command=refresh_device_list)
    refresh_btn.pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
    
    # 初始刷新
    refresh_device_list()

    # 创建标签页容器（Notebook）
    notebook = ttk.Notebook(window)
    notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=pad_scale_xy5 * 2, pady=pad_scale_xy5 * 2)

    # ==================== 第一页：主控 ====================
    # 创建 Frame 容器
    root = tk.Frame(notebook, padx=pad_scale_xy5, pady=pad_scale_xy5, highlightthickness=1,
                    highlightcolor="lightgray", highlightbackground="lightgray")
    notebook.add(root, text="  主控  ")

    # ==================== 设置标签页 ====================
    settings_frame = ttk.Frame(notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    notebook.add(settings_frame, text="  设置  ")

    # 设置页内部使用子标签页，避免设置项过多导致界面过高
    settings_notebook = ttk.Notebook(settings_frame)
    settings_notebook.pack(fill=tk.BOTH, expand=True)

    # ---- 子页0：按页面（按页面查看/跳转设置，便于找到每一项设置在哪） ----
    page_guide_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(page_guide_frame, text="  按页面  ")

    page_setting_guide = {
        MARQUEE_PAGE_ID: ("文字跑马灯：文本、字体、字号、颜色", 4, (0, "content")),
        WEATHER_PAGE_ID: ("天气：设置城市（支持中文）", 4, (1, "content")),
        CRYPTO_PAGE_ID: ("行情：设置交易对", 4, (1, "content")),
        HOTSEARCH_PAGE_ID: ("热搜：设置显示条数/字体/翻页/刷新", 4, (2, "content")),
        PING_PAGE_ID: ("网络延迟：设置测试目标", 4, (1, "content")),
        TIMER_PAGE_ID: ("番茄钟：设置时长", 4, (3, "content")),
        WORLDCLOCK_PAGE_ID: ("世界时钟：设置时区", 4, (3, "content")),
        MEMO_PAGE_ID: ("纪念日：设置列表", 4, (4, "content")),
        TODO_PAGE_ID: ("待办事项：设置列表", 4, (4, "content")),
        PROC_PAGE_ID: ("进程TOP：设置显示数量", 5, (0, "monitor")),
        DISKIO_PAGE_ID: ("磁盘读写：选择显示模式、标题/字号/颜色", 5, (3, "monitor")),
        HWDETAIL_PAGE_ID: ("硬件详情：设置监控类型与数量", 5, (1, "monitor")),
        GAUGE_PAGE_ID: ("仪表盘：设置项目与颜色", 5, (2, "monitor")),
        SCREEN_PAGE_ID: ("屏幕镜像：设置放大镜", 6, None),
    }

    ttk.Label(page_guide_frame, text="选择页面，查看该页面有哪些设置并可一键前往：").pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    guide_var = tk.StringVar(page_guide_frame, value=getattr(config_obj, "guide_last_page", ""))
    guide_combobox = ttk.Combobox(page_guide_frame, textvariable=guide_var, state="readonly", width=26)
    guide_combobox.pack(anchor=tk.W, pady=pad_scale_xy5)
    guide_desc = tk.Label(page_guide_frame, text="", wraplength=320, justify=tk.LEFT, fg="gray")
    guide_desc.pack(anchor=tk.W, pady=pad_scale_xy5)

    def on_guide_select(event=None):
        name = guide_combobox.get()
        for pid, pname in PAGE_ID.items():
            if pname == name:
                # 记住本次选择（按当前设备配置保存，重启后恢复）
                _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
                config_obj.guide_last_page = name
                save_config()
                guide = page_setting_guide.get(pid)
                if guide:
                    guide_desc.config(text=guide[0])
                else:
                    guide_desc.config(text="该页面没有独立设置项，设置由主控页或设备控制。")
                break

    def goto_guide_setting():
        name = guide_combobox.get()
        for pid, pname in PAGE_ID.items():
            if pname == name:
                guide = page_setting_guide.get(pid)
                if guide:
                    try:
                        settings_notebook.select(guide[1])
                        sub = guide[2]
                        if sub:
                            sub_idx, ntype = sub
                            if ntype == "content":
                                content_notebook.select(sub_idx)
                            elif ntype == "monitor":
                                monitor_notebook.select(sub_idx)
                    except Exception:
                        pass
                break

    guide_combobox.bind("<<ComboboxSelected>>", on_guide_select)
    guide_combobox['values'] = list(PAGE_ID.values())
    ttk.Button(page_guide_frame, text="前往该设置", padding=pad_scale_xy, command=goto_guide_setting).pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(page_guide_frame, text="提示：以下标签页按功能分类。若找不到某项设置在哪，可在此按页面查找。",
              foreground="gray", wraplength=320, justify=tk.LEFT).pack(anchor=tk.W, pady=pad_scale_xy5)

    # ---- 子页1：通用 ----
    common_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(common_frame, text="  通用  ")

    def change_anti_burn(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        dev = get_current_device()
        config_obj.anti_burn = anti_burn_var.get()
        if config_obj.anti_burn == 0 and dev:
            dev.burn_offset_x = 0
            dev.burn_offset_y = 0
        save_config()

    anti_burn_var = tk.IntVar(common_frame, 0)
    anti_burn_var.set(config_obj.anti_burn)
    ttk.Checkbutton(
        common_frame, text="防烧屏（每30秒微调像素位置，延缓OLED烧屏）", variable=anti_burn_var,
        command=change_anti_burn
    ).pack(anchor=tk.W, pady=pad_scale_xy5)

    def change_preview(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.preview_enabled = preview_var.get()
        save_config()

    preview_var = tk.IntVar(common_frame, 0)
    preview_var.set(config_obj.preview_enabled)
    ttk.Checkbutton(
        common_frame, text="开启实时预览（显示小屏当前内容）", variable=preview_var,
        command=change_preview
    ).pack(anchor=tk.W, pady=pad_scale_xy5)

    def change_auto_start(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.auto_start = auto_start_var.get()
        if not set_auto_start(config_obj.auto_start):
            auto_start_var.set(0)
            config_obj.auto_start = 0
        save_config()

    auto_start_var = tk.IntVar(common_frame, 0)
    auto_start_var.set(config_obj.auto_start)
    ttk.Checkbutton(
        common_frame, text="开机自启动（随Windows启动）", variable=auto_start_var,
        command=change_auto_start
    ).pack(anchor=tk.W, pady=pad_scale_xy5)

    def change_language(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.language = language_var.get()
        save_config()
        apply_language()

    language_row = ttk.Frame(common_frame)
    language_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(language_row, text="界面语言:").pack(side=tk.LEFT)
    language_var = tk.StringVar(common_frame, config_obj.language)
    ttk.Combobox(language_row, textvariable=language_var, values=["中文", "English"], width=10, state="readonly").pack(side=tk.LEFT, padx=pad_scale_xy5)
    language_var.trace_add("write", change_language)

    # ---- 子页2：自动化 ----
    auto_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(auto_frame, text="  自动化  ")

    def change_page_cycle(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            config_obj.page_cycle_enable = page_cycle_var.get()
            config_obj.page_cycle_interval = int(page_cycle_interval_var.get())
        except Exception:
            return
        save_config()

    page_cycle_var = tk.IntVar(auto_frame, 0)
    page_cycle_var.set(config_obj.page_cycle_enable)
    ttk.Checkbutton(
        auto_frame, text="自动翻页轮播", variable=page_cycle_var,
        command=change_page_cycle
    ).pack(anchor=tk.W, pady=pad_scale_xy5)

    cycle_row = ttk.Frame(auto_frame)
    cycle_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(cycle_row, text="轮播间隔(秒):").pack(side=tk.LEFT)
    page_cycle_interval_var = tk.IntVar(auto_frame, 0)
    page_cycle_interval_var.set(config_obj.page_cycle_interval)
    page_cycle_interval_entry = ttk.Spinbox(cycle_row, from_=3, to=3600, textvariable=page_cycle_interval_var, width=8)
    page_cycle_interval_entry.pack(side=tk.LEFT, padx=pad_scale_xy5)
    page_cycle_interval_var.trace_add("write", change_page_cycle)

    def change_screen_off(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            config_obj.screen_off_timeout = int(screen_off_var.get())
        except Exception:
            return
        save_config()

    screen_off_var = tk.IntVar(auto_frame, 0)
    screen_off_var.set(config_obj.screen_off_timeout)
    screen_off_row = ttk.Frame(auto_frame)
    screen_off_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(screen_off_row, text="无操作息屏超时(秒, 0=禁用):").pack(side=tk.LEFT)
    screen_off_entry = ttk.Spinbox(screen_off_row, from_=0, to=3600, textvariable=screen_off_var, width=8)
    screen_off_entry.pack(side=tk.LEFT, padx=pad_scale_xy5)
    screen_off_var.trace_add("write", change_screen_off)

    # ---- 子页3：按键 ----
    key_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(key_frame, text="  按键  ")

    ttk.Label(key_frame, text="按键动作映射（单击 / 双击 / 长按）:").pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    key_row = ttk.Frame(key_frame)
    key_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    key_actions = ["下翻页", "上翻页", "切换方向", "无"]

    def change_key_action(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.key_single = key_single_var.get()
        config_obj.key_double = key_double_var.get()
        config_obj.key_long = key_long_var.get()
        save_config()

    key_single_var = tk.StringVar(key_frame, config_obj.key_single)
    key_double_var = tk.StringVar(key_frame, config_obj.key_double)
    key_long_var = tk.StringVar(key_frame, config_obj.key_long)
    ttk.Label(key_row, text="单击:").pack(side=tk.LEFT)
    ttk.Combobox(key_row, textvariable=key_single_var, values=key_actions, width=8, state="readonly").pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    ttk.Label(key_row, text="双击:").pack(side=tk.LEFT)
    ttk.Combobox(key_row, textvariable=key_double_var, values=key_actions, width=8, state="readonly").pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    ttk.Label(key_row, text="长按:").pack(side=tk.LEFT)
    ttk.Combobox(key_row, textvariable=key_long_var, values=key_actions, width=8, state="readonly").pack(side=tk.LEFT)
    for v in (key_single_var, key_double_var, key_long_var):
        v.trace_add("write", change_key_action)

    # ---- 子页4：页面内容 ----
    content_frame = ttk.Frame(settings_notebook)
    settings_notebook.add(content_frame, text="  页面内容  ")

    # 页面内容内部再分子标签页，避免内容过多拉高界面
    content_notebook = ttk.Notebook(content_frame)
    content_notebook.pack(fill=tk.BOTH, expand=True)

    # ==== 子子页：跑马灯 ====
    marquee_frame = ttk.Frame(content_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    content_notebook.add(marquee_frame, text="  文字跑马灯  ")

    def change_marquee(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.marquee_text = marquee_var.get() or " "
        config_obj.marquee_color = marquee_color_var.get() or "#ffffff"
        try:
            config_obj.marquee_font_size = int(marquee_font_size_var.get())
        except Exception:
            config_obj.marquee_font_size = 20
        try:
            config_obj.marquee_speed = float(marquee_speed_var.get())
        except Exception:
            config_obj.marquee_speed = 2
        save_config()
        update_marquee_preview()

    marquee_row = ttk.Frame(marquee_frame)
    marquee_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(marquee_row, text="跑马灯文本:").pack(side=tk.LEFT)
    marquee_var = tk.StringVar(marquee_frame, config_obj.marquee_text)
    ttk.Entry(marquee_row, textvariable=marquee_var, width=24).pack(side=tk.LEFT, padx=pad_scale_xy5)

    marquee_size_row = ttk.Frame(marquee_frame)
    marquee_size_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(marquee_size_row, text="字号:").pack(side=tk.LEFT)
    marquee_font_size_var = tk.IntVar(marquee_frame, 0)
    marquee_font_size_var.set(config_obj.marquee_font_size)
    ttk.Spinbox(marquee_size_row, from_=8, to=72, textvariable=marquee_font_size_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)

    marquee_speed_row = ttk.Frame(marquee_frame)
    marquee_speed_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(marquee_speed_row, text="滚动速度:").pack(side=tk.LEFT)
    marquee_speed_var = tk.DoubleVar(marquee_frame, config_obj.marquee_speed)
    ttk.Spinbox(marquee_speed_row, from_=1, to=20, increment=1, textvariable=marquee_speed_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)
    ttk.Label(marquee_speed_row, text="(像素/帧，越大越快)", foreground="gray").pack(side=tk.LEFT)

    marquee_color_row = ttk.Frame(marquee_frame)
    marquee_color_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(marquee_color_row, text="字体颜色:").pack(side=tk.LEFT)
    marquee_color_var = tk.StringVar(marquee_frame, config_obj.marquee_color)
    ttk.Entry(marquee_color_row, textvariable=marquee_color_var, width=10).pack(side=tk.LEFT, padx=pad_scale_xy5)

    def pick_marquee_color():
        color = tkinter.colorchooser.askcolor(color=marquee_color_var.get(), parent=window)
        if color and color[1]:
            marquee_color_var.set(color[1])

    ttk.Button(marquee_color_row, text="调色板", padding=pad_scale_xy, command=pick_marquee_color).pack(side=tk.LEFT)

    # 跑马灯实时预览（所见即所得）
    marquee_preview_canvas = tk.Canvas(marquee_frame, width=(SHOW_WIDTH * scale_factor // 100),
                                       height=(SHOW_HEIGHT * scale_factor // 100), bg="black", borderwidth=1,
                                       highlightbackground="gray")
    marquee_preview_canvas.pack(anchor=tk.W, pady=pad_scale_xy5)

    def update_marquee_preview(*args):
        try:
            text = marquee_var.get() or " "
            font_size = max(8, int(marquee_font_size_var.get()))
            font_path = "./simhei.ttf"  # 跑马灯字体固定用黑体
            hex_color = (marquee_color_var.get() or "#ffffff").lstrip('#')
            color = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
            draw = ImageDraw.Draw(im1)
            try:
                font = MiniMark.load_font(font_path, font_size)
            except Exception:
                font = MiniMark.load_font("./simhei.ttf", font_size)
            draw.text((0, (SHOW_HEIGHT - font_size) // 2), text, fill=color, font=font)
            im = im1.resize((SHOW_WIDTH * scale_factor // 100, SHOW_HEIGHT * scale_factor // 100),
                            Image.Resampling.LANCZOS)
            tk_im = ImageTk.PhotoImage(im)
            marquee_preview_canvas.delete("all")
            marquee_preview_canvas.create_image(0, 0, anchor=tk.NW, image=tk_im)
            marquee_preview_canvas.image = tk_im
        except Exception:
            pass

    marquee_var.trace_add("write", change_marquee)
    marquee_font_size_var.trace_add("write", change_marquee)
    marquee_color_var.trace_add("write", change_marquee)
    marquee_speed_var.trace_add("write", change_marquee)
    update_marquee_preview()

    # ==== 子子页：天气与行情 ====
    net_frame = ttk.Frame(content_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    content_notebook.add(net_frame, text="  天气与行情  ")

    def change_weather_city(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.weather_city = weather_city_var.get() or "Beijing"
        save_config()
        # 实时生效：立即刷新天气数据，若当前在天气页则重绘
        _refresh_page_now(WEATHER_PAGE_ID, _weather_cache, fetch_weather)

    weather_row = ttk.Frame(net_frame)
    weather_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(weather_row, text="天气城市:").pack(side=tk.LEFT)
    weather_city_var = tk.StringVar(net_frame, config_obj.weather_city)
    ttk.Entry(weather_row, textvariable=weather_city_var, width=14).pack(side=tk.LEFT, padx=pad_scale_xy5)
    weather_city_var.trace_add("write", change_weather_city)
    ttk.Label(net_frame, text="支持中文城市名，如 北京 或 Beijing", foreground="gray").pack(anchor=tk.W, pady=(0, pad_scale_xy5))

    def change_crypto_symbols(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.crypto_symbols = crypto_symbols_var.get() or "BTCUSDT,ETHUSDT"
        save_config()
        # 实时生效：立即刷新行情数据，若当前在行情页则重绘
        _refresh_page_now(CRYPTO_PAGE_ID, _crypto_cache, fetch_crypto)

    crypto_row = ttk.Frame(net_frame)
    crypto_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(crypto_row, text="行情交易对:").pack(side=tk.LEFT)
    crypto_symbols_var = tk.StringVar(net_frame, config_obj.crypto_symbols)
    ttk.Entry(crypto_row, textvariable=crypto_symbols_var, width=20).pack(side=tk.LEFT, padx=pad_scale_xy5)
    crypto_symbols_var.trace_add("write", change_crypto_symbols)

    def change_ping_host(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.ping_host = ping_host_var.get() or "223.5.5.5"
        save_config()
        # 实时生效：若当前设备在延迟页，触发重绘（ping后台1秒内更新）
        try:
            dev = get_current_device()
            if dev is not None and dev.config is not None and dev.config.state_machine == PING_PAGE_ID:
                dev.state_change = 1
        except Exception:
            pass

    ping_row = ttk.Frame(net_frame)
    ping_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(ping_row, text="延迟测试目标:").pack(side=tk.LEFT)
    ping_host_var = tk.StringVar(net_frame, config_obj.ping_host)
    ttk.Entry(ping_row, textvariable=ping_host_var, width=16).pack(side=tk.LEFT, padx=pad_scale_xy5)
    ping_host_var.trace_add("write", change_ping_host)

    # ==== 子子页：热搜 ====
    hot_frame = ttk.Frame(content_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    content_notebook.add(hot_frame, text="  热搜  ")

    def change_hotsearch(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            config_obj.hotsearch_count = int(hot_count_var.get())
        except Exception:
            pass
        try:
            config_obj.hotsearch_total = int(hot_total_var.get())
        except Exception:
            pass
        try:
            config_obj.hotsearch_font_auto = hot_font_auto_var.get()
        except Exception:
            pass
        try:
            config_obj.hotsearch_font_size = int(hot_font_size_var.get())
        except Exception:
            pass
        try:
            config_obj.hotsearch_scroll_enable = hot_scroll_var.get()
        except Exception:
            pass
        try:
            config_obj.hotsearch_scroll_speed = float(hot_scroll_speed_var.get())
        except Exception:
            pass
        try:
            config_obj.hotsearch_page_interval = float(hot_page_interval_var.get())
        except Exception:
            pass
        save_config()
        # 实时同步：若当前设备正显示热搜页，立即触发重绘，调整后所见即所得
        try:
            dev = get_current_device()
            if dev is not None and dev.config is not None and dev.config.state_machine == HOTSEARCH_PAGE_ID:
                dev.state_change = 1
        except Exception:
            pass

    def change_hot_auto_refresh(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.hotsearch_auto_refresh = hot_auto_refresh_var.get()
        save_config()

    def change_hot_interval(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            config_obj.hotsearch_interval = int(hotsearch_interval_var.get())
        except Exception:
            return
        save_config()

    # 每页显示条数
    hot_count_row = ttk.Frame(hot_frame)
    hot_count_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(hot_count_row, text="每页显示条数:").pack(side=tk.LEFT)
    hot_count_var = tk.IntVar(hot_frame, config_obj.hotsearch_count)
    ttk.Spinbox(hot_count_row, from_=1, to=10, textvariable=hot_count_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)

    # 抓取总条数
    hot_total_row = ttk.Frame(hot_frame)
    hot_total_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(hot_total_row, text="抓取总条数:").pack(side=tk.LEFT)
    hot_total_var = tk.IntVar(hot_frame, config_obj.hotsearch_total)
    ttk.Spinbox(hot_total_row, from_=1, to=20, textvariable=hot_total_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)
    ttk.Label(hot_total_row, text="(多于每页条数时自动翻页播放)", foreground="gray").pack(side=tk.LEFT)

    # 字体大小（自动适配屏幕开关 + 手动字号）
    hot_font_row = ttk.Frame(hot_frame)
    hot_font_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    hot_font_auto_var = tk.IntVar(hot_frame, config_obj.hotsearch_font_auto)
    ttk.Checkbutton(hot_font_row, text="字体自动适配屏幕", variable=hot_font_auto_var).pack(side=tk.LEFT)
    ttk.Label(hot_font_row, text="字号:").pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
    hot_font_size_var = tk.IntVar(hot_frame, config_obj.hotsearch_font_size)
    hot_font_size_spin = ttk.Spinbox(hot_font_row, from_=8, to=72, textvariable=hot_font_size_var, width=5)
    hot_font_size_spin.pack(side=tk.LEFT, padx=pad_scale_xy5)

    def _sync_hot_font_state(*args):
        """自动适配开启时禁用手动字号输入（避免调整无效），并实时同步预览"""
        try:
            if hot_font_auto_var.get():
                hot_font_size_spin.config(state="disabled")
            else:
                hot_font_size_spin.config(state="normal")
        except Exception:
            pass
        try:
            change_hotsearch()
        except Exception:
            pass
    hot_font_auto_var.trace_add("write", _sync_hot_font_state)

    # 长文本滚动字幕（文字太长一屏放不下时自动滚动）
    hot_scroll_row = ttk.Frame(hot_frame)
    hot_scroll_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    hot_scroll_var = tk.IntVar(hot_frame, config_obj.hotsearch_scroll_enable)
    ttk.Checkbutton(hot_scroll_row, text="长文本自动滚动字幕", variable=hot_scroll_var).pack(side=tk.LEFT)
    ttk.Label(hot_scroll_row, text="滚动速度:").pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
    hot_scroll_speed_var = tk.DoubleVar(hot_frame, config_obj.hotsearch_scroll_speed)
    ttk.Spinbox(hot_scroll_row, from_=1, to=20, increment=1, textvariable=hot_scroll_speed_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)
    ttk.Label(hot_frame,
              text="提示：开启“字体自动适配屏幕”时，字号会自动缩小到全部显示，无需滚动；滚动仅对手动字号的长文本生效。",
              foreground="gray").pack(anchor=tk.W, pady=(0, pad_scale_xy5))

    # 翻页间隔
    hot_page_row = ttk.Frame(hot_frame)
    hot_page_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(hot_page_row, text="翻页间隔(秒):").pack(side=tk.LEFT)
    hot_page_interval_var = tk.DoubleVar(hot_frame, config_obj.hotsearch_page_interval)
    ttk.Spinbox(hot_page_row, from_=1, to=60, increment=1, textvariable=hot_page_interval_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)

    # 自动刷新
    hot_refresh_row = ttk.Frame(hot_frame)
    hot_refresh_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    hot_auto_refresh_var = tk.IntVar(hot_frame, config_obj.hotsearch_auto_refresh)
    ttk.Checkbutton(hot_refresh_row, text="自动刷新", variable=hot_auto_refresh_var).pack(side=tk.LEFT)
    ttk.Label(hot_refresh_row, text="刷新间隔(秒):").pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
    hotsearch_interval_var = tk.IntVar(hot_frame, config_obj.hotsearch_interval)
    ttk.Spinbox(hot_refresh_row, from_=10, to=3600, textvariable=hotsearch_interval_var, width=6).pack(side=tk.LEFT, padx=pad_scale_xy5)

    hot_count_var.trace_add("write", change_hotsearch)
    hot_total_var.trace_add("write", change_hotsearch)
    hot_font_auto_var.trace_add("write", change_hotsearch)
    hot_font_size_var.trace_add("write", change_hotsearch)
    hot_scroll_var.trace_add("write", change_hotsearch)
    hot_scroll_speed_var.trace_add("write", change_hotsearch)
    hot_page_interval_var.trace_add("write", change_hotsearch)
    hot_auto_refresh_var.trace_add("write", change_hot_auto_refresh)
    hotsearch_interval_var.trace_add("write", change_hot_interval)
    # 初始化字号输入框状态（所有变量已定义后调用）
    _sync_hot_font_state()

    # ==== 子子页：时间 ====
    time_frame = ttk.Frame(content_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    content_notebook.add(time_frame, text="  时间  ")

    def change_timer_minutes(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            config_obj.timer_minutes = int(timer_minutes_var.get())
        except Exception:
            return
        save_config()

    timer_row = ttk.Frame(time_frame)
    timer_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(timer_row, text="番茄钟时长(分钟):").pack(side=tk.LEFT)
    timer_minutes_var = tk.IntVar(time_frame, 0)
    timer_minutes_var.set(config_obj.timer_minutes)
    ttk.Spinbox(timer_row, from_=1, to=180, textvariable=timer_minutes_var, width=6).pack(side=tk.LEFT, padx=pad_scale_xy5)
    timer_minutes_var.trace_add("write", change_timer_minutes)

    # 世界时钟时区（每项：名称|UTC偏移，逗号分隔）
    def change_clock_zones(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.clock_zones = clock_zones_var.get() or "北京|8"
        save_config()

    ttk.Label(time_frame, text="世界时钟时区（每项：名称|UTC偏移，逗号分隔）:").pack(anchor=tk.W)
    clock_zones_var = tk.StringVar(time_frame, config_obj.clock_zones)
    ttk.Entry(time_frame, textvariable=clock_zones_var, width=40).pack(anchor=tk.W, fill=tk.X, pady=pad_scale_xy5)
    clock_zones_var.trace_add("write", change_clock_zones)
    ttk.Label(time_frame, text="例：北京|8,伦敦|0,纽约|-5,东京|9", foreground="gray").pack(anchor=tk.W, pady=(0, pad_scale_xy5))

    # ==== 子子页：纪念日与待办 ====
    list_frame = ttk.Frame(content_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    content_notebook.add(list_frame, text="  纪念日/待办  ")

    # 纪念日（每行一项：名称|MM-DD）
    ttk.Label(list_frame, text="纪念日（每行一项：名称|月-日，如 生日|01-01）:").pack(anchor=tk.W)
    memo_text = tk.Text(list_frame, height=6, width=40)
    memo_text.insert(tk.END, "\n".join(config_obj.memo_items))
    memo_text.pack(anchor=tk.W, fill=tk.X, pady=pad_scale_xy5)

    # 待办事项（每行一项）
    ttk.Label(list_frame, text="待办事项（每行一项）:").pack(anchor=tk.W)
    todo_text = tk.Text(list_frame, height=6, width=40)
    todo_text.insert(tk.END, "\n".join(config_obj.todo_items))
    todo_text.pack(anchor=tk.W, fill=tk.X, pady=pad_scale_xy5)

    def save_text_config(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.memo_items = [l for l in memo_text.get("1.0", tk.END).split("\n") if l.strip()]
        config_obj.todo_items = [l for l in todo_text.get("1.0", tk.END).split("\n") if l.strip()]
        save_config()

    memo_text.bind("<KeyRelease>", save_text_config)
    todo_text.bind("<KeyRelease>", save_text_config)

    # ==================== 配色方案：通用套用组件 ====================
    _scheme_combos = []          # 收集所有"配色方案"下拉框，自定义方案变化后统一刷新
    _scheme_swatch_buttons = []  # 收集所有"色块选择按钮" [(Menubutton, var)]，方案变化后刷新候选色
    _current_scheme_colors = []  # 当前选中方案的颜色列表（作为各位置色块下拉的候选色）

    def _is_dark_hex(h):
        """判断颜色深浅，用于色块上文字选黑/白"""
        try:
            h = (h or "#ffffff").lstrip('#')
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            return (r * 299 + g * 587 + b * 114) / 1000 < 140
        except Exception:
            return False

    def _build_scheme_menu(anchor, var=None):
        """构建色块菜单：每项=当前方案的一种颜色（色块显示），点击把颜色写入 var"""
        menu = tk.Menu(anchor, tearoff=0)
        colors = _current_scheme_colors or []
        if not colors:
            menu.add_command(label="（未选择配色方案）", state="disabled")
        for c in colors:
            try:
                fg = "#ffffff" if _is_dark_hex(c) else "#000000"
                menu.add_command(label="      ", background=c, foreground=fg,
                                 command=(lambda col=c: var.set(col)) if var is not None else (lambda: None))
            except Exception:
                pass
        return menu

    def _make_swatch_button(parent, var):
        """生成色块选择按钮：点击弹出当前方案的颜色色块菜单，选择后写入 var"""
        mb = tk.Menubutton(parent, text="☰", relief="raised", width=2)
        _scheme_swatch_buttons.append((mb, var))
        mb.configure(menu=_build_scheme_menu(mb, var))
        return mb

    def _refresh_scheme_swatches():
        """方案变化后刷新所有色块按钮的候选色菜单"""
        for mb, var in _scheme_swatch_buttons:
            try:
                mb.configure(menu=_build_scheme_menu(mb, var))
            except Exception:
                pass

    def _save_current_scheme(vars_):
        """把当前各颜色位置的取值收集为新方案，弹窗命名保存（支持混搭配色）"""
        colors = []
        for v in vars_:
            c = (v.get() or "").strip()
            if not c:
                continue
            colors.append(c if c.startswith("#") else "#" + c)
        parsed = parse_color_list(",".join(colors))
        if not parsed:
            insert_text_message("保存失败：当前没有有效的颜色值")
            return
        res = _scheme_dialog("保存当前配色为新方案", colors_text=",".join(parsed))
        if not res or not res.get("name"):
            return
        _ui_set_active()
        config_obj.custom_color_schemes = config_obj.custom_color_schemes or {}
        config_obj.custom_color_schemes[res["name"]] = parsed
        save_config()
        _refresh_scheme_page()
        _refresh_scheme_combos()
        insert_text_message("已保存新配色方案：%s" % res["name"])

    def _make_scheme_row(frame, vars_):
        """配色方案选择行：选方案仅提供候选色板（各颜色行后的色块下拉可选该方案颜色），不自动套用；
        并提供"存为新方案"按钮，把当前各位置颜色组合保存为新方案。"""
        row = ttk.Frame(frame)
        row.pack(anchor=tk.W, pady=(0, pad_scale_xy5))
        ttk.Label(row, text="配色方案:").pack(side=tk.LEFT)
        var = tk.StringVar(frame, "")
        combo = ttk.Combobox(row, textvariable=var, width=18, state="readonly")
        combo.pack(side=tk.LEFT, padx=pad_scale_xy5)
        ttk.Label(row, text="选方案后，各颜色后的色块下拉可选该方案颜色", foreground="gray").pack(side=tk.LEFT)
        ttk.Button(row, text="存为新方案", padding=pad_scale_xy,
                   command=lambda: _save_current_scheme(vars_)).pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))

        def _on_select(event=None):
            schemes = get_all_color_schemes(config_obj)
            colors = schemes.get(var.get(), [])
            _current_scheme_colors[:] = colors
            _refresh_scheme_swatches()
        combo.bind("<<ComboboxSelected>>", _on_select)
        _scheme_combos.append(combo)
        combo["values"] = list(get_all_color_schemes(config_obj).keys())
        return combo

    def _refresh_scheme_combos():
        """自定义配色方案增删改后，刷新所有配色方案下拉框的选项"""
        names = list(get_all_color_schemes(config_obj).keys())
        for combo in _scheme_combos:
            combo["values"] = names

    # ---- 子页：配色方案（管理，独立标签） ----
    scheme_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(scheme_frame, text="  配色方案  ")

    ttk.Label(scheme_frame, text="选择配色方案预览；内置方案只读，可新增/编辑/删除自定义方案：").pack(anchor=tk.W, pady=(0, pad_scale_xy5))

    scheme_row = ttk.Frame(scheme_frame)
    scheme_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(scheme_row, text="方案:").pack(side=tk.LEFT)
    scheme_var = tk.StringVar(scheme_frame, "")
    scheme_combo = ttk.Combobox(scheme_row, textvariable=scheme_var, width=24, state="readonly")
    scheme_combo.pack(side=tk.LEFT, padx=pad_scale_xy5)
    scheme_canvas = tk.Canvas(scheme_frame, height=28, bg="white", highlightthickness=1)
    scheme_canvas.pack(fill=tk.X, pady=pad_scale_xy5)

    def _draw_scheme_preview(event=None):
        schemes = get_all_color_schemes(config_obj)
        colors = schemes.get(scheme_var.get(), [])
        scheme_canvas.delete("all")
        w = scheme_canvas.winfo_width()
        if w <= 1:
            w = 380
        n = max(1, len(colors))
        cw = max(1, w // n)
        for i, c in enumerate(colors):
            scheme_canvas.create_rectangle(i * cw, 0, (i + 1) * cw, 28, fill=c, outline="")

    def _refresh_scheme_page():
        schemes = get_all_color_schemes(config_obj)
        names = list(schemes.keys())
        scheme_combo["values"] = names
        if scheme_var.get() not in names:
            scheme_var.set(names[0] if names else "")
        _draw_scheme_preview()

    scheme_combo.bind("<<ComboboxSelected>>", _draw_scheme_preview)

    def _scheme_dialog(title, name="", colors_text=""):
        """配色方案编辑对话框，返回 {'name':..,'colors':..} 或 None"""
        dlg = tk.Toplevel(window)
        dlg.title(title)
        dlg.transient(window)
        dlg.grab_set()
        dlg.resizable(False, False)
        frm = ttk.Frame(dlg, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text="方案名称:").pack(anchor=tk.W)
        name_var = tk.StringVar(frm, name)
        ttk.Entry(frm, textvariable=name_var, width=30).pack(anchor=tk.W, pady=(pad_scale_xy5, 0))
        ttk.Label(frm, text="颜色列表（#rrggbb，逗号分隔）:").pack(anchor=tk.W, pady=(pad_scale_xy5, 0))
        colors_var = tk.StringVar(frm, colors_text)
        ttk.Entry(frm, textvariable=colors_var, width=44).pack(anchor=tk.W, pady=(pad_scale_xy5, 0))
        ttk.Label(frm, text="示例：#ffb3ba,#baffc9,#bae1ff,#ddbaff,#ffd6ba,#ffffba",
                  foreground="gray").pack(anchor=tk.W, pady=(pad_scale_xy5, 0))
        result = {}
        def _ok():
            result["name"] = name_var.get().strip()
            result["colors"] = colors_var.get().strip()
            dlg.destroy()
        def _cancel():
            dlg.destroy()
        btn_row = ttk.Frame(frm)
        btn_row.pack(anchor=tk.E, pady=(pad_scale_xy5, 0))
        ttk.Button(btn_row, text="确定", padding=pad_scale_xy, command=_ok).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
        ttk.Button(btn_row, text="取消", padding=pad_scale_xy, command=_cancel).pack(side=tk.LEFT)
        dlg.wait_window()
        return result if result else None

    def add_custom_scheme():
        res = _scheme_dialog("新增配色方案")
        if not res or not res.get("name"):
            return
        colors = parse_color_list(res.get("colors", ""))
        if not colors:
            insert_text_message("新增失败：颜色列表为空或格式不正确")
            return
        _ui_set_active()
        config_obj.custom_color_schemes = config_obj.custom_color_schemes or {}
        config_obj.custom_color_schemes[res["name"]] = colors
        save_config()
        scheme_var.set(res["name"])
        _refresh_scheme_page()
        _refresh_scheme_combos()

    def edit_custom_scheme():
        name = scheme_var.get()
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
        _ui_set_active()
        config_obj.custom_color_schemes = config_obj.custom_color_schemes or {}
        if res["name"] != name and name in config_obj.custom_color_schemes:
            del config_obj.custom_color_schemes[name]
        config_obj.custom_color_schemes[res["name"]] = colors
        save_config()
        scheme_var.set(res["name"])
        _refresh_scheme_page()
        _refresh_scheme_combos()

    def del_custom_scheme():
        name = scheme_var.get()
        if name in BUILTIN_COLOR_SCHEMES:
            insert_text_message("内置方案不可删除")
            return
        if not tk.messagebox.askyesno("删除配色方案", "确定删除「%s」？" % name, parent=window):
            return
        _ui_set_active()
        config_obj.custom_color_schemes = config_obj.custom_color_schemes or {}
        config_obj.custom_color_schemes.pop(name, None)
        save_config()
        _refresh_scheme_page()
        _refresh_scheme_combos()

    btn_row = ttk.Frame(scheme_frame)
    btn_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Button(btn_row, text="新增方案", padding=pad_scale_xy, command=add_custom_scheme).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    ttk.Button(btn_row, text="编辑当前", padding=pad_scale_xy, command=edit_custom_scheme).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    ttk.Button(btn_row, text="删除当前", padding=pad_scale_xy, command=del_custom_scheme).pack(side=tk.LEFT)
    ttk.Label(btn_row, text="（内置方案只读）", foreground="gray").pack(side=tk.LEFT, padx=pad_scale_xy5)
    _refresh_scheme_page()

    # ---- 子页4.5：监控显示 ----
    monitor_frame = ttk.Frame(settings_notebook)
    settings_notebook.add(monitor_frame, text="  监控显示  ")
    # 监控显示内部再分子标签页，避免内容过多拥挤（后续新增监控项也便于扩展）
    monitor_notebook = ttk.Notebook(monitor_frame)
    monitor_notebook.pack(fill=tk.BOTH, expand=True)

    # ==== 子子页：进程 ====
    proc_frame = ttk.Frame(monitor_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    monitor_notebook.add(proc_frame, text="  进程  ")

    def change_proc_count(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            config_obj.proc_count = int(proc_count_var.get())
        except Exception:
            return
        save_config()

    proc_row = ttk.Frame(proc_frame)
    proc_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(proc_row, text="进程TOP显示数量:").pack(side=tk.LEFT)
    proc_count_var = tk.IntVar(proc_frame, 0)
    proc_count_var.set(config_obj.proc_count)
    ttk.Spinbox(proc_row, from_=1, to=30, textvariable=proc_count_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)
    proc_count_var.trace_add("write", change_proc_count)

    # ==== 子子页：硬件详情 ====
    hw_frame = ttk.Frame(monitor_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    monitor_notebook.add(hw_frame, text="  硬件详情  ")

    def change_hwdetail_max(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            config_obj.hwdetail_max = int(hwdetail_max_var.get())
        except Exception:
            return
        save_config()

    hw_row = ttk.Frame(hw_frame)
    hw_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(hw_row, text="硬件详情显示数量:").pack(side=tk.LEFT)
    hwdetail_max_var = tk.IntVar(hw_frame, 0)
    hwdetail_max_var.set(config_obj.hwdetail_max)
    ttk.Spinbox(hw_row, from_=1, to=30, textvariable=hwdetail_max_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)
    hwdetail_max_var.trace_add("write", change_hwdetail_max)

    # 硬件详情监控类型（用户自选监控哪些硬件传感器类型）
    def change_hwdetail_types(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        sel = [t for t, v in hwdetail_type_vars.items() if v.get()]
        config_obj.hwdetail_types = ",".join(sel) or "Temperature"
        save_config()

    ttk.Label(hw_frame, text="硬件详情监控类型:").pack(anchor=tk.W, pady=(pad_scale_xy5, 0))
    hwdetail_type_vars = {}
    hw_type_row = ttk.Frame(hw_frame)
    hw_type_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    for t in ("Temperature", "Fan", "Voltage", "Load", "Power"):
        var = tk.IntVar(hw_frame, t in (config_obj.hwdetail_types or "").split(","))
        hwdetail_type_vars[t] = var
        ttk.Checkbutton(hw_type_row, text=t, variable=var, command=change_hwdetail_types).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))

    # 自由选择传感器（LibreHardwareMonitor 全部传感器可勾选，覆盖按类型自动选择）
    if not windll.shell32.IsUserAnAdmin():
        ttk.Label(hw_frame, text="⚠ 主板传感器(CPU温度/主板温度/风扇)需以管理员身份运行才能读取",
                  foreground="#c00000").pack(anchor=tk.W, pady=(0, pad_scale_xy5))

    sensor_sel_row = ttk.Frame(hw_frame)
    sensor_sel_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(sensor_sel_row, text="自由选择传感器:").pack(side=tk.LEFT)
    ttk.Button(sensor_sel_row, text="选择传感器…", padding=pad_scale_xy,
               command=lambda: _open_sensor_picker(
                   window, "multi", "选择硬件详情传感器", "hwdetail_sensor_names", None,
                   "勾选要显示的传感器（不勾选则按上方类型自动选择）",
                   on_done=_refresh_hw_sensor_info)
               ).pack(side=tk.LEFT, padx=pad_scale_xy5)
    hw_sensor_info_var = tk.StringVar(hw_frame, value="")
    ttk.Label(hw_frame, textvariable=hw_sensor_info_var, foreground="#808080").pack(anchor=tk.W)

    def _refresh_hw_sensor_info():
        names = [n.strip() for n in (config_obj.hwdetail_sensor_names or "").split(",") if n.strip()]
        if names:
            shown = "、".join(names[:3]) + ("…" if len(names) > 3 else "")
            hw_sensor_info_var.set("已选 %d 个：%s" % (len(names), shown))
        else:
            hw_sensor_info_var.set("未选择（按上方类型自动选择）")
    _refresh_hw_sensor_info()

    # ==== 子子页：仪表盘 ====
    gauge_frame = ttk.Frame(monitor_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    monitor_notebook.add(gauge_frame, text="  仪表盘  ")

    ttk.Label(gauge_frame, text="仪表盘显示项目与颜色（多于一页自动翻页）:").pack(anchor=tk.W, pady=(0, pad_scale_xy5))

    def change_gauge(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.gauge_show_cpu = gauge_cpu_var.get()
        config_obj.gauge_show_mem = gauge_mem_var.get()
        config_obj.gauge_show_disk = gauge_disk_var.get()
        config_obj.gauge_show_cpu_temp = gauge_cpu_temp_var.get()
        config_obj.gauge_show_gpu = gauge_gpu_var.get()
        config_obj.gauge_show_gpu_temp = gauge_gpu_temp_var.get()
        config_obj.gauge_show_fan = gauge_fan_var.get()
        config_obj.gauge_show_upload = gauge_upload_var.get()
        config_obj.gauge_show_download = gauge_download_var.get()
        config_obj.gauge_cpu_color = gauge_cpu_color_var.get()
        config_obj.gauge_mem_color = gauge_mem_color_var.get()
        config_obj.gauge_disk_color = gauge_disk_color_var.get()
        config_obj.gauge_cpu_temp_color = gauge_cpu_temp_color_var.get()
        config_obj.gauge_gpu_color = gauge_gpu_color_var.get()
        config_obj.gauge_gpu_temp_color = gauge_gpu_temp_color_var.get()
        config_obj.gauge_fan_color = gauge_fan_color_var.get()
        config_obj.gauge_upload_color = gauge_upload_color_var.get()
        config_obj.gauge_download_color = gauge_download_color_var.get()
        save_config()

    gauge_cpu_var = tk.IntVar(gauge_frame, config_obj.gauge_show_cpu)
    gauge_mem_var = tk.IntVar(gauge_frame, config_obj.gauge_show_mem)
    gauge_disk_var = tk.IntVar(gauge_frame, config_obj.gauge_show_disk)
    gauge_cpu_temp_var = tk.IntVar(gauge_frame, config_obj.gauge_show_cpu_temp)
    gauge_gpu_var = tk.IntVar(gauge_frame, config_obj.gauge_show_gpu)
    gauge_gpu_temp_var = tk.IntVar(gauge_frame, config_obj.gauge_show_gpu_temp)
    gauge_fan_var = tk.IntVar(gauge_frame, config_obj.gauge_show_fan)
    gauge_upload_var = tk.IntVar(gauge_frame, config_obj.gauge_show_upload)
    gauge_download_var = tk.IntVar(gauge_frame, config_obj.gauge_show_download)

    def _pick_gauge_color(var):
        color = tkinter.colorchooser.askcolor(color=var.get(), parent=window)
        if color and color[1]:
            var.set(color[1])

    def _make_gauge_row(label, var, color_var, sensor_key=None, sensor_filter=None):
        row = ttk.Frame(gauge_frame)
        row.pack(anchor=tk.W, pady=pad_scale_xy5)
        ttk.Checkbutton(row, text=label, variable=var, command=change_gauge).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=color_var, width=9).pack(side=tk.LEFT, padx=pad_scale_xy5)
        ttk.Button(row, text="颜色", padding=pad_scale_xy, command=lambda: _pick_gauge_color(color_var)).pack(side=tk.LEFT)
        _make_swatch_button(row, color_var).pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
        if sensor_key:
            ttk.Button(row, text="传感器", padding=pad_scale_xy,
                       command=lambda: _open_sensor_picker(
                           window, "single", "选择%s传感器" % label, sensor_key, sensor_filter,
                           "选择用于 %s 的传感器（选“自动检测”则程序自动识别）" % label)
                       ).pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
        return color_var

    gauge_cpu_color_var = _make_gauge_row("CPU", gauge_cpu_var, tk.StringVar(gauge_frame, config_obj.gauge_cpu_color))
    gauge_mem_color_var = _make_gauge_row("内存", gauge_mem_var, tk.StringVar(gauge_frame, config_obj.gauge_mem_color))
    gauge_disk_color_var = _make_gauge_row("磁盘", gauge_disk_var, tk.StringVar(gauge_frame, config_obj.gauge_disk_color))
    gauge_cpu_temp_color_var = _make_gauge_row("CPU温度", gauge_cpu_temp_var, tk.StringVar(gauge_frame, config_obj.gauge_cpu_temp_color), "gauge_cpu_temp_sensor", "Temperature")
    gauge_gpu_color_var = _make_gauge_row("GPU", gauge_gpu_var, tk.StringVar(gauge_frame, config_obj.gauge_gpu_color), "gauge_gpu_load_sensor", "Load")
    gauge_gpu_temp_color_var = _make_gauge_row("GPU温度", gauge_gpu_temp_var, tk.StringVar(gauge_frame, config_obj.gauge_gpu_temp_color), "gauge_gpu_temp_sensor", "Temperature")
    gauge_fan_color_var = _make_gauge_row("风扇", gauge_fan_var, tk.StringVar(gauge_frame, config_obj.gauge_fan_color), "gauge_fan_sensor", "Fan")
    gauge_upload_color_var = _make_gauge_row("上传", gauge_upload_var, tk.StringVar(gauge_frame, config_obj.gauge_upload_color))
    gauge_download_color_var = _make_gauge_row("下载", gauge_download_var, tk.StringVar(gauge_frame, config_obj.gauge_download_color))

    for v in (gauge_cpu_color_var, gauge_mem_color_var, gauge_disk_color_var,
              gauge_cpu_temp_color_var, gauge_gpu_color_var, gauge_gpu_temp_color_var,
              gauge_fan_color_var, gauge_upload_color_var, gauge_download_color_var):
        v.trace_add("write", change_gauge)
    _make_scheme_row(gauge_frame, [gauge_cpu_color_var, gauge_mem_color_var, gauge_disk_color_var,
                                   gauge_cpu_temp_color_var, gauge_gpu_color_var, gauge_gpu_temp_color_var,
                                   gauge_fan_color_var, gauge_upload_color_var, gauge_download_color_var])

    # ==== 子子页：磁盘读写 ====
    disk_frame = ttk.Frame(monitor_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    monitor_notebook.add(disk_frame, text="  磁盘读写  ")

    def change_diskio(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.diskio_mode = diskio_mode_var.get()
        config_obj.diskio_show_title = diskio_show_title_var.get()
        config_obj.diskio_font_auto = diskio_font_auto_var.get()
        try:
            config_obj.diskio_font_size = int(diskio_font_size_var.get())
        except Exception:
            pass
        config_obj.diskio_title_color = diskio_title_color_var.get() or "#ffffff"
        config_obj.diskio_read_color = diskio_read_color_var.get() or "#ff8000"
        config_obj.diskio_write_color = diskio_write_color_var.get() or "#00ffff"
        config_obj.diskio_label_color = diskio_label_color_var.get() or "#ffffff"
        config_obj.diskio_value_read_color = diskio_value_read_color_var.get() or "#ff8000"
        config_obj.diskio_value_write_color = diskio_value_write_color_var.get() or "#00ffff"
        config_obj.diskio_value_auto = diskio_value_auto_var.get()
        try:
            config_obj.diskio_value_font_size = int(diskio_value_font_size_var.get())
        except Exception:
            pass
        config_obj.diskio_bar1_color = diskio_bar1_color_var.get() or "#eb8b8b"
        config_obj.diskio_bar2_color = diskio_bar2_color_var.get() or "#92d3d9"
        save_config()
        _sync_diskio_ui_state()

    def _pick_diskio_color(var):
        color = tkinter.colorchooser.askcolor(color=var.get(), parent=window)
        if color and color[1]:
            var.set(color[1])

    def _make_diskio_color_row(frame, label, var):
        row = ttk.Frame(frame)
        row.pack(anchor=tk.W, pady=pad_scale_xy5)
        ttk.Label(row, text=label).pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, width=9).pack(side=tk.LEFT, padx=pad_scale_xy5)
        ttk.Button(row, text="颜色", padding=pad_scale_xy,
                   command=lambda: _pick_diskio_color(var)).pack(side=tk.LEFT)
        _make_swatch_button(row, var).pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
        return row

    # 显示模式（顶部，始终可见）
    mode_row = ttk.Frame(disk_frame)
    mode_row.pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    ttk.Label(mode_row, text="显示模式:").pack(side=tk.LEFT)
    diskio_mode_var = tk.StringVar(disk_frame, config_obj.diskio_mode)
    diskio_mode_cb = ttk.Combobox(mode_row, textvariable=diskio_mode_var,
                                  values=["经典", "经典2", "网速样式"], width=10, state="readonly")
    diskio_mode_cb.pack(side=tk.LEFT, padx=pad_scale_xy5)
    diskio_mode_var.trace_add("write", change_diskio)
    ttk.Label(mode_row, text="选中后自动跳转到对应样式标签", foreground="gray").pack(side=tk.LEFT)

    # 磁盘读写内部按样式分标签页，避免单页内容过高
    disk_notebook = ttk.Notebook(disk_frame)
    disk_notebook.pack(fill=tk.BOTH, expand=True, pady=(pad_scale_xy5, 0))

    # ---- 标签1：经典模式 ----
    classic_tab = ttk.Frame(disk_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    disk_notebook.add(classic_tab, text="  经典模式  ")

    diskio_show_title_var = tk.IntVar(classic_tab, config_obj.diskio_show_title)
    diskio_show_title_cb = ttk.Checkbutton(classic_tab, text="显示标题“磁盘读写”",
                                           variable=diskio_show_title_var, command=change_diskio)
    diskio_show_title_cb.pack(anchor=tk.W, pady=pad_scale_xy5)

    font_auto_row = ttk.Frame(classic_tab)
    font_auto_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    diskio_font_auto_var = tk.IntVar(classic_tab, config_obj.diskio_font_auto)
    diskio_font_auto_cb = ttk.Checkbutton(font_auto_row, text="字号自适应屏幕",
                                          variable=diskio_font_auto_var, command=change_diskio)
    diskio_font_auto_cb.pack(side=tk.LEFT)
    ttk.Label(font_auto_row, text="  手动字号:").pack(side=tk.LEFT)
    diskio_font_size_var = tk.IntVar(classic_tab, config_obj.diskio_font_size)
    diskio_font_size_spin = ttk.Spinbox(font_auto_row, from_=8, to=72, textvariable=diskio_font_size_var, width=5)
    diskio_font_size_spin.pack(side=tk.LEFT, padx=pad_scale_xy5)
    diskio_font_size_var.trace_add("write", change_diskio)

    diskio_title_color_var = tk.StringVar(classic_tab, config_obj.diskio_title_color)
    diskio_read_color_var = tk.StringVar(classic_tab, config_obj.diskio_read_color)
    diskio_write_color_var = tk.StringVar(classic_tab, config_obj.diskio_write_color)
    classic_color_rows = [
        _make_diskio_color_row(classic_tab, "标题颜色:", diskio_title_color_var),
        _make_diskio_color_row(classic_tab, "读 颜色:", diskio_read_color_var),
        _make_diskio_color_row(classic_tab, "写 颜色:", diskio_write_color_var),
    ]
    _make_scheme_row(classic_tab, [diskio_title_color_var, diskio_read_color_var, diskio_write_color_var])

    # ---- 标签2：经典2样式（仿网络流量布局） ----
    classic2_tab = ttk.Frame(disk_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    disk_notebook.add(classic2_tab, text="  经典2样式  ")

    ttk.Label(classic2_tab, text="与网络流量页面的字体大小、布局、颜色完全一致（标签为读/写）",
              wraplength=340, justify=tk.LEFT).pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(classic2_tab, text="颜色自动跟随「网络流量」页面的当前配色（经典=通用文字颜色+默认柱色；自定义=独立配色），无需单独配置。",
              foreground="gray", wraplength=340, justify=tk.LEFT).pack(anchor=tk.W, pady=pad_scale_xy5)

    # ---- 标签3：网速样式 ----
    netspeed_tab = ttk.Frame(disk_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    disk_notebook.add(netspeed_tab, text="  网速样式  ")

    ttk.Label(netspeed_tab, text="带实时柱状图").pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    val_font_row = ttk.Frame(netspeed_tab)
    val_font_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    diskio_value_auto_var = tk.IntVar(netspeed_tab, config_obj.diskio_value_auto)
    diskio_value_auto_cb = ttk.Checkbutton(val_font_row, text="字号自适应屏幕",
                                           variable=diskio_value_auto_var, command=change_diskio)
    diskio_value_auto_cb.pack(side=tk.LEFT)
    ttk.Label(val_font_row, text="  手动字号:").pack(side=tk.LEFT)
    diskio_value_font_size_var = tk.IntVar(netspeed_tab, config_obj.diskio_value_font_size)
    diskio_value_font_size_spin = ttk.Spinbox(val_font_row, from_=8, to=40, textvariable=diskio_value_font_size_var, width=5)
    diskio_value_font_size_spin.pack(side=tk.LEFT, padx=pad_scale_xy5)
    diskio_value_font_size_var.trace_add("write", change_diskio)

    diskio_label_color_var = tk.StringVar(netspeed_tab, config_obj.diskio_label_color)
    diskio_value_read_color_var = tk.StringVar(netspeed_tab, config_obj.diskio_value_read_color)
    diskio_value_write_color_var = tk.StringVar(netspeed_tab, config_obj.diskio_value_write_color)
    diskio_bar1_color_var = tk.StringVar(netspeed_tab, config_obj.diskio_bar1_color)
    diskio_bar2_color_var = tk.StringVar(netspeed_tab, config_obj.diskio_bar2_color)
    netspeed_color_rows = [
        _make_diskio_color_row(netspeed_tab, "标签颜色:", diskio_label_color_var),
        _make_diskio_color_row(netspeed_tab, "读数值颜色:", diskio_value_read_color_var),
        _make_diskio_color_row(netspeed_tab, "写数值颜色:", diskio_value_write_color_var),
        _make_diskio_color_row(netspeed_tab, "读柱颜色:", diskio_bar1_color_var),
        _make_diskio_color_row(netspeed_tab, "写柱颜色:", diskio_bar2_color_var),
    ]
    _make_scheme_row(netspeed_tab, [diskio_label_color_var, diskio_value_read_color_var,
                                    diskio_value_write_color_var, diskio_bar1_color_var, diskio_bar2_color_var])
    for v in (diskio_title_color_var, diskio_read_color_var, diskio_write_color_var,
              diskio_label_color_var, diskio_value_read_color_var, diskio_value_write_color_var,
              diskio_bar1_color_var, diskio_bar2_color_var):
        v.trace_add("write", change_diskio)

    def _sync_diskio_ui_state():
        """根据显示模式自动切到对应样式标签"""
        mode = diskio_mode_var.get()
        if mode == "经典2":
            disk_notebook.select(classic2_tab)
        elif mode == "网速样式":
            disk_notebook.select(netspeed_tab)
        else:
            disk_notebook.select(classic_tab)
    _sync_diskio_ui_state()

    # ==== 子子页：网络流量 ====
    net_frame = ttk.Frame(monitor_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    monitor_notebook.add(net_frame, text="  网络流量  ")

    def change_netspeed_color(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.netspeed_mode = netspeed_mode_var.get()
        config_obj.netspeed_up_color = netspeed_up_color_var.get() or "#ff8000"
        config_obj.netspeed_down_color = netspeed_down_color_var.get() or "#00ffff"
        config_obj.netspeed_bar1_color = netspeed_bar1_color_var.get() or "#eb8b8b"
        config_obj.netspeed_bar2_color = netspeed_bar2_color_var.get() or "#92d3d9"
        save_config()
        _sync_netspeed_ui_state()

    # 显示模式
    net_mode_row = ttk.Frame(net_frame)
    net_mode_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(net_mode_row, text="显示模式:").pack(side=tk.LEFT)
    netspeed_mode_var = tk.StringVar(net_frame, config_obj.netspeed_mode)
    netspeed_mode_cb = ttk.Combobox(net_mode_row, textvariable=netspeed_mode_var,
                                    values=["经典", "自定义"], width=10, state="readonly")
    netspeed_mode_cb.pack(side=tk.LEFT, padx=pad_scale_xy5)
    netspeed_mode_var.trace_add("write", change_netspeed_color)
    ttk.Label(net_mode_row, text="经典=修改前样式，自定义=全部颜色独立", foreground="gray").pack(side=tk.LEFT)

    netspeed_up_color_var = tk.StringVar(net_frame, config_obj.netspeed_up_color)
    netspeed_down_color_var = tk.StringVar(net_frame, config_obj.netspeed_down_color)
    netspeed_bar1_color_var = tk.StringVar(net_frame, config_obj.netspeed_bar1_color)
    netspeed_bar2_color_var = tk.StringVar(net_frame, config_obj.netspeed_bar2_color)
    netspeed_color_rows = [
        _make_diskio_color_row(net_frame, "上传文字颜色:", netspeed_up_color_var),
        _make_diskio_color_row(net_frame, "下载文字颜色:", netspeed_down_color_var),
        _make_diskio_color_row(net_frame, "上传柱颜色:", netspeed_bar1_color_var),
        _make_diskio_color_row(net_frame, "下载柱颜色:", netspeed_bar2_color_var),
    ]
    _make_scheme_row(net_frame, [netspeed_up_color_var, netspeed_down_color_var,
                                 netspeed_bar1_color_var, netspeed_bar2_color_var])
    for v in (netspeed_up_color_var, netspeed_down_color_var,
              netspeed_bar1_color_var, netspeed_bar2_color_var):
        v.trace_add("write", change_netspeed_color)

    def _sync_netspeed_ui_state():
        """经典模式禁用自定义颜色区，避免无关注释误导"""
        custom_state = "normal" if netspeed_mode_var.get() == "自定义" else "disabled"
        for row in netspeed_color_rows:
            for child in row.winfo_children():
                child.configure(state=custom_state)
    _sync_netspeed_ui_state()

    # ---- 子页5：屏幕镜像 ----
    mirror_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(mirror_frame, text="  屏幕镜像  ")

    def change_zoom(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.zoom_enable = zoom_enable_var.get()
        try:
            config_obj.zoom_scale = int(zoom_scale_var.get())
        except Exception:
            config_obj.zoom_scale = 2
        save_config()

    zoom_enable_var = tk.IntVar(mirror_frame, 0)
    zoom_enable_var.set(config_obj.zoom_enable)
    ttk.Checkbutton(mirror_frame, text="镜像局部放大（跟随鼠标）", variable=zoom_enable_var,
                    command=change_zoom).pack(anchor=tk.W, pady=pad_scale_xy5)
    zoom_row = ttk.Frame(mirror_frame)
    zoom_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(zoom_row, text="放大倍数:").pack(side=tk.LEFT)
    zoom_scale_var = tk.IntVar(mirror_frame, 0)
    zoom_scale_var.set(config_obj.zoom_scale)
    ttk.Spinbox(zoom_row, from_=1, to=8, textvariable=zoom_scale_var, width=5).pack(side=tk.LEFT, padx=pad_scale_xy5)
    zoom_scale_var.trace_add("write", change_zoom)

    # ==================== 设备切换联动：设置页控件刷新 ====================
    def _apply_settings_ui_to_config():
        """把当前设备配置刷新到设置页控件（切换设备时调用）"""
        global config_obj
        try:
            # ---- 按页面导航 ----
            guide_var.set(getattr(config_obj, "guide_last_page", ""))
            # ---- 通用 ----
            anti_burn_var.set(config_obj.anti_burn)
            preview_var.set(config_obj.preview_enabled)
            auto_start_var.set(config_obj.auto_start)
            language_var.set(config_obj.language)
            # ---- 自动化 ----
            page_cycle_var.set(config_obj.page_cycle_enable)
            page_cycle_interval_var.set(config_obj.page_cycle_interval)
            screen_off_var.set(config_obj.screen_off_timeout)
            # ---- 按键 ----
            key_single_var.set(config_obj.key_single)
            key_double_var.set(config_obj.key_double)
            key_long_var.set(config_obj.key_long)
            # ---- 跑马灯 ----
            marquee_var.set(config_obj.marquee_text)
            marquee_font_size_var.set(config_obj.marquee_font_size)
            marquee_color_var.set(config_obj.marquee_color)
            marquee_speed_var.set(config_obj.marquee_speed)
            try:
                update_marquee_preview()
            except Exception:
                pass
            # ---- 天气与行情 ----
            weather_city_var.set(config_obj.weather_city)
            crypto_symbols_var.set(config_obj.crypto_symbols)
            ping_host_var.set(config_obj.ping_host)
            # ---- 热搜 ----
            hot_count_var.set(config_obj.hotsearch_count)
            hot_total_var.set(config_obj.hotsearch_total)
            hot_font_auto_var.set(config_obj.hotsearch_font_auto)
            hot_font_size_var.set(config_obj.hotsearch_font_size)
            hot_scroll_var.set(config_obj.hotsearch_scroll_enable)
            hot_scroll_speed_var.set(config_obj.hotsearch_scroll_speed)
            hot_page_interval_var.set(config_obj.hotsearch_page_interval)
            hot_auto_refresh_var.set(config_obj.hotsearch_auto_refresh)
            hotsearch_interval_var.set(config_obj.hotsearch_interval)
            # ---- 时间 ----
            timer_minutes_var.set(config_obj.timer_minutes)
            clock_zones_var.set(config_obj.clock_zones)
            # ---- 纪念日/待办 ----
            memo_text.delete("1.0", tk.END)
            memo_text.insert(tk.END, "\n".join(config_obj.memo_items))
            todo_text.delete("1.0", tk.END)
            todo_text.insert(tk.END, "\n".join(config_obj.todo_items))
            # ---- 进程 ----
            proc_count_var.set(config_obj.proc_count)
            # ---- 硬件详情 ----
            hwdetail_max_var.set(config_obj.hwdetail_max)
            for t, var in hwdetail_type_vars.items():
                var.set(1 if t in (config_obj.hwdetail_types or "").split(",") else 0)
            try:
                _refresh_hw_sensor_info()
            except Exception:
                pass
            # ---- 仪表盘 ----
            gauge_cpu_var.set(config_obj.gauge_show_cpu)
            gauge_mem_var.set(config_obj.gauge_show_mem)
            gauge_disk_var.set(config_obj.gauge_show_disk)
            gauge_cpu_temp_var.set(config_obj.gauge_show_cpu_temp)
            gauge_gpu_var.set(config_obj.gauge_show_gpu)
            gauge_gpu_temp_var.set(config_obj.gauge_show_gpu_temp)
            gauge_fan_var.set(config_obj.gauge_show_fan)
            gauge_upload_var.set(config_obj.gauge_show_upload)
            gauge_download_var.set(config_obj.gauge_show_download)
            gauge_cpu_color_var.set(config_obj.gauge_cpu_color)
            gauge_mem_color_var.set(config_obj.gauge_mem_color)
            gauge_disk_color_var.set(config_obj.gauge_disk_color)
            gauge_cpu_temp_color_var.set(config_obj.gauge_cpu_temp_color)
            gauge_gpu_color_var.set(config_obj.gauge_gpu_color)
            gauge_gpu_temp_color_var.set(config_obj.gauge_gpu_temp_color)
            gauge_fan_color_var.set(config_obj.gauge_fan_color)
            gauge_upload_color_var.set(config_obj.gauge_upload_color)
            gauge_download_color_var.set(config_obj.gauge_download_color)
            # ---- 磁盘读写 ----
            diskio_mode_var.set(config_obj.diskio_mode)
            diskio_show_title_var.set(config_obj.diskio_show_title)
            diskio_font_auto_var.set(config_obj.diskio_font_auto)
            diskio_font_size_var.set(config_obj.diskio_font_size)
            diskio_title_color_var.set(config_obj.diskio_title_color)
            diskio_read_color_var.set(config_obj.diskio_read_color)
            diskio_write_color_var.set(config_obj.diskio_write_color)
            diskio_label_color_var.set(config_obj.diskio_label_color)
            diskio_value_read_color_var.set(config_obj.diskio_value_read_color)
            diskio_value_write_color_var.set(config_obj.diskio_value_write_color)
            diskio_value_auto_var.set(config_obj.diskio_value_auto)
            diskio_value_font_size_var.set(config_obj.diskio_value_font_size)
            diskio_bar1_color_var.set(config_obj.diskio_bar1_color)
            diskio_bar2_color_var.set(config_obj.diskio_bar2_color)
            _sync_diskio_ui_state()
            # ---- 网络流量 ----
            netspeed_mode_var.set(config_obj.netspeed_mode)
            netspeed_up_color_var.set(config_obj.netspeed_up_color)
            netspeed_down_color_var.set(config_obj.netspeed_down_color)
            netspeed_bar1_color_var.set(config_obj.netspeed_bar1_color)
            netspeed_bar2_color_var.set(config_obj.netspeed_bar2_color)
            _sync_netspeed_ui_state()
            # ---- 配色方案 ----
            try:
                _refresh_scheme_page()
                _refresh_scheme_combos()
            except Exception:
                pass
            # ---- API 接入 ----
            try:
                api_enable_var.set(config_obj.api_enable)
                api_port_var.set(config_obj.api_port)
                api_token_var.set(config_obj.api_token)
                _refresh_api_status()
            except Exception:
                pass
            # ---- 屏幕镜像 ----
            zoom_enable_var.set(config_obj.zoom_enable)
            zoom_scale_var.set(config_obj.zoom_scale)
        except Exception as e:
            print("刷新设置页控件失败：%s" % e)

    # ---- 子页6：API 接入 ----
    api_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(api_frame, text="  API接入  ")

    def change_api(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.api_enable = api_enable_var.get()
        try:
            config_obj.api_port = int(api_port_var.get())
        except Exception:
            pass
        config_obj.api_token = api_token_var.get().strip()
        save_config()
        try:
            stop_api_server()
            if config_obj.api_enable:
                start_api_server()
        except Exception as e:
            print("API 服务器重启失败：%s" % e)
        _refresh_api_status()

    def _refresh_api_status():
        try:
            port = int(getattr(config_obj, "api_port", 8632))
        except Exception:
            port = 8632
        if getattr(config_obj, "api_enable", 1):
            api_status_var.set("运行中：http://127.0.0.1:%d" % port)
        else:
            api_status_var.set("已关闭")
        api_ws_var.set("WebSocket：ws://127.0.0.1:%d/ws" % port)
        try:
            api_json_var.set("JSON 文档：http://127.0.0.1:%d/api/openapi.json　|　文件：%s"
                             % (port, os.path.join(get_base_config_dir(), "api_openapi.json")))
        except Exception:
            pass
        try:
            api_proto_var.set("TCP: %d ｜ UDP: %d ｜ ZMQ: %d(需pyzmq) ｜ 管道: \\\.\\pipe\\MSU2_MINI_V2_api ｜ Unix: api_unix.sock"
                              % (port + 1, port + 2, port + 3))
        except Exception:
            pass

    def open_api_doc():
        try:
            port = int(getattr(config_obj, "api_port", 8632))
        except Exception:
            port = 8632
        webbrowser.open("http://127.0.0.1:%d" % port)

    api_enable_var = tk.IntVar(api_frame, config_obj.api_enable)
    ttk.Checkbutton(api_frame, text="启用 API 投屏服务器（本地 127.0.0.1）", variable=api_enable_var,
                    command=change_api).pack(anchor=tk.W, pady=pad_scale_xy5)

    api_port_row = ttk.Frame(api_frame)
    api_port_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(api_port_row, text="端口:").pack(side=tk.LEFT)
    api_port_var = tk.IntVar(api_frame, config_obj.api_port)
    ttk.Spinbox(api_port_row, from_=1024, to=65535, textvariable=api_port_var, width=8).pack(side=tk.LEFT, padx=pad_scale_xy5)
    api_port_var.trace_add("write", change_api)
    ttk.Label(api_port_row, text="(修改后自动重启服务器生效)", foreground="gray").pack(side=tk.LEFT)

    api_token_row = ttk.Frame(api_frame)
    api_token_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(api_token_row, text="访问令牌(可选):").pack(side=tk.LEFT)
    api_token_var = tk.StringVar(api_frame, config_obj.api_token)
    ttk.Entry(api_token_row, textvariable=api_token_var, width=24).pack(side=tk.LEFT, padx=pad_scale_xy5)
    api_token_var.trace_add("write", change_api)
    ttk.Label(api_token_row, text="留空=不校验；非空时需请求头 X-API-Token 或 ?token=", foreground="gray").pack(side=tk.LEFT)

    api_status_var = tk.StringVar(api_frame, "")
    ttk.Label(api_frame, textvariable=api_status_var, foreground="#2e86c1").pack(anchor=tk.W, pady=pad_scale_xy5)
    api_ws_var = tk.StringVar(api_frame, "")
    ttk.Label(api_frame, textvariable=api_ws_var, foreground="#2e86c1").pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    api_json_var = tk.StringVar(api_frame, "")
    ttk.Label(api_frame, textvariable=api_json_var, foreground="gray").pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    api_proto_var = tk.StringVar(api_frame, "")
    ttk.Label(api_frame, textvariable=api_proto_var, foreground="gray").pack(anchor=tk.W, pady=(0, pad_scale_xy5))

    def export_api_json_ui():
        try:
            path = tkinter.filedialog.asksaveasfilename(
                defaultextension=".json", initialfile="api_openapi.json",
                filetypes=[("JSON", "*.json")], title="导出 API JSON 文档")
            if not path:
                return
            saved = export_api_json(path)
            insert_text_message("API JSON 文档已导出：%s" % (saved or path))
        except Exception as e:
            insert_text_message("导出失败：%s" % e)

    api_btn_row = ttk.Frame(api_frame)
    api_btn_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Button(api_btn_row, text="打开 API 文档", padding=pad_scale_xy, command=open_api_doc).pack(side=tk.LEFT)
    ttk.Button(api_btn_row, text="导出 JSON 文档", padding=pad_scale_xy, command=export_api_json_ui).pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
    ttk.Label(api_btn_row, text="  其他程序可通过 REST / WebSocket 接入，自定义投屏内容", foreground="gray").pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
    _refresh_api_status()

    # ---- 子页7：数据管理 ----
    data_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(data_frame, text="  数据管理  ")

    cfg_row = ttk.Frame(data_frame)
    cfg_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Button(cfg_row, text="导出配置", width=12, padding=pad_scale_xy, command=export_config).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    ttk.Button(cfg_row, text="导入配置", width=12, padding=pad_scale_xy, command=import_config).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))

    def check_update_async():
        threading.Thread(target=check_update, daemon=True).start()

    ttk.Button(cfg_row, text="检查更新", width=12, padding=pad_scale_xy, command=check_update_async).pack(side=tk.LEFT)

    # ==================== 设备信息标签页（设置与关于之间） ====================
    hw_info_frame = ttk.Frame(notebook, padding=(pad_scale_xy5 * 3, pad_scale_xy5 * 3))
    notebook.add(hw_info_frame, text="  设备信息  ")

    hw_title_label = tk.Label(hw_info_frame, text="设备硬件信息",
                              font=("TkDefaultFont", 14 * scale_factor // 100, "bold"))
    hw_title_label.pack(pady=(0, 2))
    hw_sub_label = tk.Label(hw_info_frame, text="固件 / 芯片 / USB / 本机系统信息（连接后点“刷新”）", fg="gray")
    hw_sub_label.pack(pady=(0, pad_scale_xy5))

    hw_notebook = ttk.Notebook(hw_info_frame)
    hw_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, pad_scale_xy5))

    hw_conn_frame = ttk.Frame(hw_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    hw_notebook.add(hw_conn_frame, text="  连接信息  ")
    hw_sfr_frame = ttk.Frame(hw_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    hw_notebook.add(hw_sfr_frame, text="  SFR寄存器  ")
    hw_flash_frame = ttk.Frame(hw_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    hw_notebook.add(hw_flash_frame, text="  Flash芯片  ")
    hw_parts_frame = ttk.Frame(hw_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    hw_notebook.add(hw_parts_frame, text="  Flash分区  ")
    hw_sys_frame = ttk.Frame(hw_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    hw_notebook.add(hw_sys_frame, text="  系统信息  ")

    # Flash芯片信息（优先从 device_protocol.json 读取，失败时用内置默认）
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
        """从 device_protocol.json 读取 Flash 布局，失败时返回内置默认"""
        try:
            with open(_get_resource("device_protocol.json"), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("flash_layout") or _flash_default
        except Exception:
            return _flash_default

    def _add_info_row(parent, label, value):
        row_f = ttk.Frame(parent)
        row_f.pack(fill=tk.X, pady=1)
        tk.Label(row_f, text=label, width=16, anchor=tk.E, fg="gray").pack(side=tk.LEFT, padx=(0, 6))
        tk.Label(row_f, text=value, anchor=tk.W, justify=tk.LEFT).pack(side=tk.LEFT)

    _sfr_type_names = ["u8地址", "u16地址", "u32地址", "字符串", "数组"]

    def _read_sfr_value(entry):
        """读取单个 SFR 条目的当前值（Read_M_u8/u16 内部已加串口锁，线程安全）"""
        try:
            data_type = entry.family[0] // 32
            if data_type == 0:  # u8, 2B地址
                return Read_M_u8(entry.data[0] * 256 + entry.data[1])
            elif data_type == 1:  # u16, 1B地址
                return Read_M_u16(entry.data[0])
            elif data_type == 2:  # u32, 2B地址
                addr = entry.data[0] * 256 + entry.data[1]
                val = 0
                for n in range(entry.family[0] % 32):
                    val = (val << 8) | Read_M_u8(addr + n)
                return val
            elif data_type == 3:  # 字符串
                return entry.data.decode("utf-8", errors="replace")
            elif data_type == 4:  # 数组
                return " ".join("%02X" % b for b in entry.data)
        except Exception:
            return None
        return None

    def _sfr_addr_str(entry):
        """生成 SFR 条目的地址描述字符串"""
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

    def refresh_hw_info():
        """刷新设备信息（USB连接信息/固件版本 + SFR寄存器 + Flash布局 + 本机系统信息）"""
        for f in (hw_conn_frame, hw_sfr_frame, hw_flash_frame, hw_parts_frame, hw_sys_frame):
            for w in f.winfo_children():
                w.destroy()
        dev = get_current_device()
        usb = getattr(dev, "usb_info", {}) if dev is not None else {}
        fw = getattr(dev, "firmware_version", 0) if dev is not None else 0
        connected = (dev is not None and dev.ser is not None and dev.ser.is_open)

        # ---- 子页1：连接信息（USB描述符） ----
        _add_info_row(hw_conn_frame, "连接状态", "已连接" if connected else "未连接")
        _add_info_row(hw_conn_frame, "端口", usb.get("port") or "-")
        _add_info_row(hw_conn_frame, "序列号(SN)", usb.get("serial_number") or "-")
        _add_info_row(hw_conn_frame, "VID", usb.get("vid") or "-")
        _add_info_row(hw_conn_frame, "PID", usb.get("pid") or "-")
        _add_info_row(hw_conn_frame, "制造商", usb.get("manufacturer") or "-")
        _add_info_row(hw_conn_frame, "产品", usb.get("product") or "-")
        _add_info_row(hw_conn_frame, "名称", usb.get("name") or "-")
        _add_info_row(hw_conn_frame, "描述", usb.get("description") or "-")
        _add_info_row(hw_conn_frame, "接口", usb.get("interface") or "-")
        _add_info_row(hw_conn_frame, "硬件ID", usb.get("hwid") or "-")
        _add_info_row(hw_conn_frame, "位置", usb.get("location") or "-")
        _add_info_row(hw_conn_frame, "固件版本", ("v%d" % fw) if fw else "-")

        # ---- 子页2：SFR寄存器（设备固件变量，实时读值） ----
        sfr = getattr(dev, "msn_data", None) if dev is not None else None
        if sfr:
            _add_info_row(hw_sfr_frame, "变量名", "类型 / 地址 / 当前值")
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
                _add_info_row(hw_sfr_frame, name, "%s %s = %s" % (dtype, addr, val_str))
        else:
            _add_info_row(hw_sfr_frame, "SFR数据", "未获取（设备未连接）")

        # ---- 子页3：Flash芯片 ----
        flash = _load_flash_layout()
        _add_info_row(hw_flash_frame, "Flash芯片", flash.get("chip") or "-")
        _add_info_row(hw_flash_frame, "容量", flash.get("capacity") or "-")
        _add_info_row(hw_flash_frame, "页大小", flash.get("page_size") or "-")
        _add_info_row(hw_flash_frame, "总页数", str(flash.get("total_pages") or "-"))

        # ---- 子页4：Flash分区 ----
        allocs = flash.get("allocations") or {}
        if allocs:
            for name, info in allocs.items():
                start = info.get("start_page", "?")
                pages = info.get("pages", "?")
                desc = info.get("description", "")
                _add_info_row(hw_parts_frame, name, "页 %s（共%s页）%s" % (start, pages, desc))

        # ---- 子页5：系统信息（本机） ----
        import platform
        _add_info_row(hw_sys_frame, "操作系统", platform.platform())
        _add_info_row(hw_sys_frame, "电脑名", platform.node())
        _add_info_row(hw_sys_frame, "架构", platform.machine())
        _add_info_row(hw_sys_frame, "CPU型号", platform.processor() or "未知")
        try:
            _add_info_row(hw_sys_frame, "CPU核心",
                          "%d物理 / %d逻辑" % (psutil.cpu_count(logical=False) or 0, psutil.cpu_count(logical=True) or 0))
        except Exception:
            pass
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current:
                _add_info_row(hw_sys_frame, "CPU频率", "%.1f GHz" % (freq.current / 1000))
        except Exception:
            pass
        try:
            _add_info_row(hw_sys_frame, "内存", "%.1f GB" % (psutil.virtual_memory().total / (1024 ** 3)))
        except Exception:
            pass
        try:
            batt = psutil.sensors_battery()
            if batt:
                _add_info_row(hw_sys_frame, "电池", "%d%%" % batt.percent)
        except Exception:
            pass
        _add_info_row(hw_sys_frame, "Python", sys.version.split()[0])

    hw_btn_row = ttk.Frame(hw_info_frame)
    hw_btn_row.pack(anchor=tk.W)
    ttk.Button(hw_btn_row, text="刷新", width=12, padding=pad_scale_xy, command=refresh_hw_info).pack(side=tk.LEFT)
    ttk.Label(hw_btn_row, text="连接信息在设备连接成功时采集；未连接或显示“-”属正常", foreground="gray").pack(side=tk.LEFT, padx=(pad_scale_xy5, 0))
    refresh_hw_info()

    # ==================== 关于标签页 ====================
    about_frame = ttk.Frame(notebook, padding=(pad_scale_xy5 * 3, pad_scale_xy5 * 3))
    notebook.add(about_frame, text="  关于  ")

    # --- 关于页面标题 ---
    about_title_label = tk.Label(about_frame, text=f"{PROGRAM_TITLE}",
                                  font=("TkDefaultFont", 14 * scale_factor // 100, "bold"))
    about_title_label.pack(pady=(0, 2))
    about_ver_label = tk.Label(about_frame, text=f"v{PROGRAM_VERSION}",
                                font=("TkDefaultFont", 11 * scale_factor // 100))
    about_ver_label.pack(pady=(0, 2))
    about_sub_label = tk.Label(about_frame, text=PROGRAM_SUBTITLE, fg="gray")
    about_sub_label.pack(pady=(0, pad_scale_xy5))

    ttk.Separator(about_frame, orient="horizontal").pack(fill=tk.X, pady=pad_scale_xy5)

    # --- 基本信息 ---
    info_frame = ttk.Frame(about_frame)
    info_frame.pack(fill=tk.X, pady=pad_scale_xy5)
    info_items = [
        ("作者:", PROGRAM_AUTHOR),
        ("许可证:", PROGRAM_LICENSE),
        ("构建日期:", PROGRAM_BUILD_DATE),
    ]
    for label_text, value_text in info_items:
        row_f = ttk.Frame(info_frame)
        row_f.pack(fill=tk.X, pady=1)
        tk.Label(row_f, text=label_text, width=10, anchor=tk.E, fg="gray").pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(row_f, text=value_text).pack(side=tk.LEFT)

    # --- 项目地址 ---
    url_frame = ttk.Frame(about_frame)
    url_frame.pack(fill=tk.X, pady=(0, pad_scale_xy5))
    tk.Label(url_frame, text="项目地址:", width=10, anchor=tk.E, fg="gray").pack(side=tk.LEFT, padx=(0, 5))
    tk.Label(url_frame, text=PROGRAM_GITHUB, fg="#3366cc").pack(side=tk.LEFT)

    ttk.Separator(about_frame, orient="horizontal").pack(fill=tk.X, pady=pad_scale_xy5)

    # --- 整合源项目 ---
    tk.Label(about_frame, text="整合自以下开源项目（均为MIT协议）:",
             font=("TkDefaultFont", 9 * scale_factor // 100, "bold")).pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    for proj in PROGRAM_SOURCE_PROJECTS:
        proj_line = f"  • {proj['author']}/{proj['name']}"
        tk.Label(about_frame, text=proj_line, fg="#555555").pack(anchor=tk.W)
        tk.Label(about_frame, text=f"    {proj['url']}", fg="#3366cc",
                 font=("TkDefaultFont", 8 * scale_factor // 100)).pack(anchor=tk.W)

    ttk.Separator(about_frame, orient="horizontal").pack(fill=tk.X, pady=pad_scale_xy5)

    # --- 版本更新说明 ---
    tk.Label(about_frame, text="版本更新说明:",
             font=("TkDefaultFont", 9 * scale_factor // 100, "bold")).pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    changelog_text = tk.Text(about_frame, wrap=tk.WORD, height=6, padx=pad_scale_xy5, pady=pad_scale_xy5,
                              state=tk.DISABLED, relief=tk.GROOVE, borderwidth=1)
    changelog_text.pack(fill=tk.BOTH, expand=True, pady=(0, pad_scale_xy5))
    # 手动插入文本（因为state=DISABLED）
    changelog_text.config(state=tk.NORMAL)
    changelog_text.insert(tk.END, PROGRAM_CHANGELOG.strip())
    changelog_text.config(state=tk.DISABLED)

    # root.grid_rowconfigure(0, weight=1)
    # root.grid_rowconfigure(1, weight=1)
    # root.grid_rowconfigure(2, weight=1)
    # root.grid_rowconfigure(3, weight=1)
    # root.grid_rowconfigure(4, weight=1)
    # root.grid_rowconfigure(5, weight=1)
    # root.grid_rowconfigure(6, weight=1)
    # root.grid_rowconfigure(7, weight=1)
    # root.grid_columnconfigure(0, weight=1)
    # root.grid_columnconfigure(1, weight=1)
    # root.grid_columnconfigure(2, weight=1)
    # root.grid_columnconfigure(3, weight=1)
    # root.grid_columnconfigure(4, weight=1)
    # root.grid_columnconfigure(5, weight=1)

    # 创建一个容纳帮助按钮和状态的框
    state_frame = ttk.Frame(root, padding="0")
    state_frame.grid(row=0, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW, padx=0, pady=0)
    state_frame.grid_columnconfigure(1, weight=1)  # 设置第2列自动调整宽度
    # state_frame.grid_propagate(0)  # 禁止被内部控件撑大

    # 设备连接状态标签
    Label1 = tk.Label(state_frame, text="设备未连接", fg="white", bg="red", padx=0, pady=0,
                      borderwidth=pad_scale_xy5 - 2)
    Label1.grid(row=0, column=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # 信息显示文本框
    Text1 = tk.Text(root, state=tk.DISABLED, wrap=tk.CHAR, width=22, height=6, padx=pad_scale_xy5, pady=pad_scale_xy5)
    Text1.grid(row=5, column=0, rowspan=3, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # 这些后台线程尽早启动
    daemon_thread.start()
    load_thread.start()
    if ping_thread is not None:
        ping_thread.start()

    def help_instruction():
        help_msg = '\n'.join([
            f"{PROGRAM_TITLE} v{PROGRAM_VERSION}",
            f"作者: {PROGRAM_AUTHOR}  |  许可证: {PROGRAM_LICENSE}",
            f"项目地址: {PROGRAM_GITHUB}",
            "",
            "整合自以下开源项目（均为MIT协议）:",
            f"  {PROGRAM_SOURCE_PROJECTS[0]['author']}/{PROGRAM_SOURCE_PROJECTS[0]['name']}",
            f"  {PROGRAM_SOURCE_PROJECTS[1]['author']}/{PROGRAM_SOURCE_PROJECTS[1]['name']}",
            "",
            "该工具配套USB小屏幕使用，功能主要分两部分：烧写和显示。",
            "",
            "“烧写”包括：",
            "闪存固件：包括背景图像、相册图像、动图文件、LOGO、字体图像等。",
            "\t不包括主控固件，主控固件烧写方法需联系商家",
            "背景图像：时钟背景图像，支持大部分图像格式",
            "相册图像：单个相册图像，支持大部分图像格式",
            "动图文件：支持两种烧写方式：36张图片或者gif文件",
            "\t36张图片需要自己设置“动图间隔”，设置大于1秒可作为相册",
            "\tgif文件需要是动图文件，烧写后会自动更新“动图间隔”",
            "",
            "“显示”包含如下页面，使用“上翻页”、“下翻页”切换。",
            "动图：使用“动图间隔”调整播放速度，“动图间隔”设置较大时可作为相册",
            "\t“动图间隔”最小支持0.02秒，最大无限制。默认是0.1秒",
            "时间：显示实时时间，背景使用烧写的背景图像，用“文字颜色”调整颜色",
            "单个相册图片：显示烧写的相册图像",
            "屏幕镜像：使用“屏幕镜像窗口”选择窗口，使用“最大FPS”设置刷新率",
            "\t对于最小化窗口和部分游戏窗口，镜像失败会只显示黑色",
            "相机视频：使用“相机名称”选择摄像头，使用“最大FPS”设置刷新率",
            "\t没有摄像头不显示该页面。最大FPS支持1-50，再大没有意义",
            "电脑CPU/内存/磁盘/电池使用率监控：每秒刷新，用“文字颜色”调整颜色",
            "网络流量监控：图表显示网络速度，单位Byte/s，用“文字颜色”调整颜色",
            "自定义显示两项图表：使用“自定义内容”按钮来修改，详情见“说明”按钮",
            "自定义显示多项数值：使用“自定义内容”按钮来修改，详情见“说明”按钮",
            "",
            "屏幕镜像、相机视频处理方式：",
            "填充：裁剪掉多余部分以使图像填充满屏幕，部分图像会被裁剪掉",
            "适应：保持图像完整显示时适应屏幕，图像可能不会占满整个屏幕",
            "",
            "板载触摸按键：",
            "单击：下翻页，双击：上翻页，长按：切换显示方向",
            "",
            "启动时隐藏：",
            "支持启动既隐藏，可在快捷方式中或启动命令后增加参数-h或-hide"
        ])
        tk.messagebox.showinfo(title="帮助", message=help_msg, parent=root, icon='question')

    # 帮助按钮
    helpimage = MiniMark.load_image("resource/ios-8-Help-icon.ico")
    # linespace是行高，2是边框，10是因为pady设置为0，两边各空出5
    help_image_height = tkfont.nametofont(str(Label1.cget('font'))).metrics("linespace") + 12 * scale_factor // 100
    helpimage = helpimage.resize((help_image_height, help_image_height), Image.Resampling.LANCZOS)
    helpicon = ImageTk.PhotoImage(helpimage)
    help_instruction_btn = tk.Button(state_frame, image=helpicon, relief=tk.FLAT, command=help_instruction)
    help_instruction_btn.grid(row=0, column=0, sticky=tk.NSEW, padx=0, pady=0)

    # 隐藏按钮

    def quit_window(icon, item):
        icon.stop()
        # 使用新线程退出，否则就是在托盘图标中退出，会导致托盘图标不消失
        threading.Thread(target=on_closing, daemon=True).start()

    def show_window(icon, item):
        icon.stop()
        window.deiconify()  # 恢复窗口
        hide_btn.focus_set()  # 恢复后设置默认焦点

    def hide_to_tray(event=None):
        try:
            menu = (
                pystray.MenuItem("显示", show_window, default=True),
                pystray.MenuItem("退出", quit_window)
            )
            icon = pystray.Icon(PROGRAM_TITLE, iconimage, PROGRAM_TITLE, menu)
            # 使用新线程启用图标，防止阻塞进入事件循环，如显示桌面。不设置daemon会导致从托盘退出时该线程不结束
            threading.Thread(target=icon.run, daemon=True).start()

            window.withdraw()  # 隐藏主窗口
        except Exception as e:
            insert_text_message("Failed to use pystray to hide to tray, %s" % e)

    hide_btn = ttk.Button(root, text="隐藏", width=12, padding=pad_scale_xy, command=hide_to_tray)
    hide_btn.grid(row=0, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # 选择和烧写按钮（半宽，左：选择+烧写，右：预留新功能）

    Label3 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=pad_scale_xy5, pady=pad_scale_xy5)
    Label3.grid(row=1, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    insert_text_message("选择闪存固件", item=Label3)
    burn_frame1 = ttk.Frame(root)
    burn_frame1.grid(row=1, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    ttk.Button(burn_frame1, text="选择", width=6, padding=pad_scale_xy,
               command=lambda: Get_Photo_Path(1)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Button(burn_frame1, text="烧写", width=6, padding=pad_scale_xy,
               command=lambda: Start_Write_Photo_Path(1)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    Label5 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=pad_scale_xy5, pady=pad_scale_xy5)
    Label5.grid(row=2, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    insert_text_message("选择相册图像", item=Label5)
    burn_frame2 = ttk.Frame(root)
    burn_frame2.grid(row=2, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    ttk.Button(burn_frame2, text="选择", width=6, padding=pad_scale_xy,
               command=lambda: Get_Photo_Path(3)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Button(burn_frame2, text="烧写", width=6, padding=pad_scale_xy,
               command=lambda: Start_Write_Photo_Path(3)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    Label4 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=pad_scale_xy5, pady=pad_scale_xy5)
    Label4.grid(row=3, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    insert_text_message("选择背景图像", item=Label4)
    burn_frame3 = ttk.Frame(root)
    burn_frame3.grid(row=3, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    ttk.Button(burn_frame3, text="选择", width=6, padding=pad_scale_xy,
               command=lambda: Get_Photo_Path(2)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Button(burn_frame3, text="烧写", width=6, padding=pad_scale_xy,
               command=lambda: Start_Write_Photo_Path(2)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    Label6 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=pad_scale_xy5, pady=pad_scale_xy5)
    Label6.grid(row=4, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    insert_text_message("选择动图文件", item=Label6)
    burn_frame4 = ttk.Frame(root)
    burn_frame4.grid(row=4, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    ttk.Button(burn_frame4, text="选择", width=6, padding=pad_scale_xy,
               command=lambda: Get_Photo_Path(4)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    ttk.Button(burn_frame4, text="烧写", width=6, padding=pad_scale_xy,
               command=lambda: Start_Write_Photo_Path(4)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 自定义显示内容

    def change_netspeed_font():
        global config_obj, netspeed_font, netspeed_font_size
        name0 = config_obj.custom_selected_displayname[0][:8]
        name1 = config_obj.custom_selected_displayname[1][:8]
        if netspeed_font.getlength(name0) > netspeed_font.getlength(name1):
            longer = name0
        else:
            longer = name1
        if not_english(name0 + name1):
            netspeed_font = default_font  # 因Orbitron不支持汉字，有汉字使用默认字体
        else:
            for index in range(4, 14, 2):
                netspeed_font = MiniMark.load_font("resource/Orbitron-Bold.ttf", netspeed_font_size - index)
                if netspeed_font.getlength(longer) < SHOW_WIDTH // 2:
                    break

    change_netspeed_font()

    def show_custom():
        global config_obj, sub_window
        if hardware_monitor_manager == 1:
            insert_text_message("Libre Hardware Monitor 加载失败，自定义内容功能不可用")
            return
        elif hardware_monitor_manager is None:
            insert_text_message("Libre Hardware Monitor 正在加载，请稍候……", cleanNext=False)
            return

        def sub_on_closing():
            window.attributes("-disabled", False)  # 启用主窗口
            sub_window.destroy()  # 关闭并销毁子窗口

        # 不销毁子窗口虽然会加快下次打开的速度，但是会多占用内存。考虑到这个窗口使用频率不高，下次重新创建即可
        #     # 点击关闭时仅隐藏子窗口，不真正关闭
        #     sub_window.withdraw()
        #
        # if sub_window is not None:
        #     sub_window.deiconify()  # 如果已经创建过子窗口直接显示
        #     window.attributes("-disabled", True)  # 禁用主窗口
        #     return

        sub_window = tk.Toplevel(window)  # 创建一个子窗口
        sub_window.geometry("+%d+%d" % (window.winfo_x(), window.winfo_y()))  # 移到主窗口所在位置
        sub_window.title("自定义显示内容")
        sub_window.resizable(0, 0)  # 锁定窗口大小不能改变
        sub_window.protocol("WM_DELETE_WINDOW", sub_on_closing)
        sub_window.bind("<Escape>", lambda event: sub_on_closing())  # 按Esc按钮关闭
        sub_window.transient(window)  # 置于主窗口前面
        window.attributes("-disabled", True)  # 禁用主窗口

        sensor_vars = []
        sensor_displayname_vars = []
        sensor_vars_tech = []
        sensor_displayname_vars_tech = []

        # 创建一个选项卡
        notebook = ttk.Notebook(sub_window)
        notebook.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5 * 2, pady=pad_scale_xy5 * 2)

        # 添加“自定义多项”标签页

        tech_frame = tk.Frame(master=sub_window)
        notebook.add(tech_frame, text="  显示多项数值  ")
        tech_frame.focus_set()  # 设置默认焦点

        desc_label = tk.Label(tech_frame, text="名称")
        desc_label.grid(row=1, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        desc_label = tk.Label(tech_frame, text="项目")
        desc_label.grid(row=1, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        def update_sensor_value_tech(event, tvars, i):
            global config_obj
            event.widget.selection_clear()
            if config_obj.custom_selected_names_tech[i] != tvars[i].get():
                config_obj.custom_selected_names_tech[i] = tvars[i].get()
                save_config()

        def change_sensor_displayname_tech(dvars, i):
            global config_obj
            if config_obj.custom_selected_displayname_tech[i] != dvars[i].get():
                config_obj.custom_selected_displayname_tech[i] = dvars[i].get()
                save_config()

        row = 6  # 设置自定义项目数
        for row1 in range(row):
            if row1 >= len(config_obj.custom_selected_names_tech):
                config_obj.custom_selected_names_tech = config_obj.custom_selected_names_tech + [""]
                save_config()
            if row1 >= len(config_obj.custom_selected_displayname_tech):
                config_obj.custom_selected_displayname_tech = config_obj.custom_selected_displayname_tech + [""]
                save_config()

            sensor_displayname_var = tk.StringVar(tech_frame, config_obj.custom_selected_displayname_tech[row1])
            sensor_displayname_vars_tech.append(sensor_displayname_var)
            sensor_entry = ttk.Entry(tech_frame, textvariable=sensor_displayname_var, width=10)
            sensor_entry.bind("<KeyRelease>",
                              lambda event, ii=row1: change_sensor_displayname_tech(sensor_displayname_vars_tech, ii))
            sensor_entry.grid(row=row1 + 2, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

            sensor_var = tk.StringVar(tech_frame, config_obj.custom_selected_names_tech[row1])
            sensor_vars_tech.append(sensor_var)
            sensor_combobox = ttk.Combobox(tech_frame, textvariable=sensor_var, width=60,
                                           values=[""] + list(hardware_monitor_manager.sensors.keys()))
            sensor_combobox.bind("<<ComboboxSelected>>",
                                 lambda event, ii=row1: update_sensor_value_tech(event, sensor_vars_tech, ii))
            sensor_combobox.grid(row=row1 + 2, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
            sensor_combobox.configure(state="readonly")  # 设置选择框不可编辑

        row += 2
        desc_label = tk.Label(tech_frame, text="完全自定义模板代码：", anchor=tk.W, justify=tk.LEFT)
        desc_label.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        # 可视化命令编辑器：无需记忆模板语法，逐条选择命令类型、填入参数即可插入模板
        row += 1
        cmd_frame = ttk.Frame(tech_frame, padding="5")
        cmd_frame.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=0)
        cmd_frame.grid_columnconfigure(1, weight=1)

        cmd_type_list = ["p 文本", "a 锚点", "m 移动到", "t 相对移动", "f 字体", "c 颜色", "i 图片", "v 数值", "r 矩形", "l 线条", "o 圆", "g 动图"]
        cmd_hints = {
            "p 文本": "输入要显示的文字，如 CPU 或 你好",
            "a 锚点": "输入锚点，如 la / ra / ls / rs（参考Pillow锚点）",
            "m 移动到": "输入 x y 绝对坐标，如 8 8",
            "t 相对移动": "输入 dx dy 相对位移，如 8 0",
            "f 字体": "输入 字体文件 字号，如 resource/Orbitron-Bold.ttf 20",
            "c 颜色": "输入颜色 hex，如 #ff0000，或点“浏览…”选颜色",
            "i 图片": "输入图片路径，如 resource/example_background.png，或点“浏览…”选文件",
            "v 数值": "输入 序号 [格式]，如 1 或 1 {:.1f}（序号对应上方第1~6项）",
            "r 矩形": "输入 x1 y1 x2 y2，如 10 10 150 70",
            "l 线条": "输入 x1 y1 x2 y2，如 0 0 159 79",
            "o 圆": "输入 x y 半径，如 80 40 20",
            "g 动图": "输入 GIF 文件路径，如 resource/anim.gif，或点“浏览…”选文件",
        }
        cmd_type_var = tk.StringVar(tech_frame, cmd_type_list[0])
        cmd_arg_var = tk.StringVar(tech_frame, "")
        cmd_hint_var = tk.StringVar(tech_frame, cmd_hints[cmd_type_list[0]])

        def update_cmd_hint(event=None):
            if event is not None:
                event.widget.selection_clear()
            cmd_hint_var.set(cmd_hints.get(cmd_type_var.get(), ""))

        cmd_type_combobox = ttk.Combobox(cmd_frame, textvariable=cmd_type_var, values=cmd_type_list,
                                         width=12, state="readonly")
        cmd_type_combobox.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, pad_scale_xy5))
        cmd_type_combobox.bind("<<ComboboxSelected>>", update_cmd_hint)

        cmd_arg_entry = ttk.Entry(cmd_frame, textvariable=cmd_arg_var)
        cmd_arg_entry.grid(row=0, column=1, sticky=tk.NSEW, padx=pad_scale_xy5)

        def browse_resource():
            """根据当前命令类型，智能选择颜色/字体/图片资源并填入参数框"""
            letter = cmd_type_var.get()[0]
            if letter == "c":
                color = tkinter.colorchooser.askcolor(color="#3366cc", parent=sub_window)
                if color and color[1]:
                    cmd_arg_var.set(color[1])
            elif letter == "f":
                path = tkinter.filedialog.askopenfilename(parent=sub_window, title="选择字体",
                                                          filetypes=[("字体文件", "*.ttf *.otf"), ("所有文件", "*.*")])
                if path:
                    cmd_arg_var.set(path + " 20")  # 默认字号20，可自行修改
            elif letter == "i":
                path = tkinter.filedialog.askopenfilename(parent=sub_window, title="选择图片",
                                                          filetypes=IMAGE_FILE_TYPES)
                if path:
                    cmd_arg_var.set(path)

        browse_btn = ttk.Button(cmd_frame, text="浏览…", width=8, padding=pad_scale_xy, command=browse_resource)
        browse_btn.grid(row=0, column=2, sticky=tk.NSEW, padx=pad_scale_xy5)

        def insert_command():
            sel = cmd_type_var.get()
            if not sel:
                return
            letter = sel[0]
            arg = cmd_arg_var.get().strip()
            line = letter + (" " + arg if arg else "")
            text_area.insert(tk.INSERT, line + "\n")  # 插入到光标处
            text_area.see(tk.INSERT)
            update_global_text()
            cmd_arg_entry.focus_set()
            cmd_arg_entry.selection_range(0, tk.END)

        insert_btn = ttk.Button(cmd_frame, text="插入", width=8, padding=pad_scale_xy, command=insert_command)
        insert_btn.grid(row=0, column=3, sticky=tk.NSEW, padx=pad_scale_xy5)

        cmd_hint_label = tk.Label(cmd_frame, textvariable=cmd_hint_var, anchor=tk.W, justify=tk.LEFT,
                                  fg="gray", font=("", 9))
        cmd_hint_label.grid(row=1, column=0, columnspan=4, sticky=tk.NSEW, padx=pad_scale_xy5,
                            pady=(pad_scale_xy5, 0))

        # 创建自定义内容输入框
        row += 1
        text_frame = ttk.Frame(tech_frame, padding="5")
        text_frame.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=0)

        def update_global_canvas():
            # UI预览模式：跳过传感器更新，避免与daemon线程并发冲突
            im = get_full_custom_im(update_sensors=False)
            im = im.resize((SHOW_WIDTH * scale_factor // 100, SHOW_HEIGHT * scale_factor // 100),
                           Image.Resampling.LANCZOS)
            tk_im = ImageTk.PhotoImage(im)
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_im)
            canvas.image = tk_im

        def update_global_text(event=None):
            global config_obj
            # Get the current content of the text area and update the global variable
            full_custom_template_tmp = text_area.get("1.0", tk.END).rstrip('\n')  # tk.END会多一个换行
            if config_obj.full_custom_template != full_custom_template_tmp:
                config_obj.full_custom_template = full_custom_template_tmp
                save_config()
                update_global_canvas()

        # wrap: WORD 按空白符如空格换行，CHAR 按字符换行，NONE 不换行
        text_area = tk.Text(text_frame, wrap=tk.CHAR, width=10, height=10, padx=0, pady=0)
        text_area.insert(tk.END, config_obj.full_custom_template)
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0, pady=0)

        view_frame = ttk.Frame(text_frame, padding="0")
        view_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=0, pady=0)

        desc_label = tk.Label(view_frame, width=1, text="效果预览：", anchor=tk.NW, justify=tk.LEFT, padx=0, pady=0)
        desc_label.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=0, pady=0)

        canvas = tk.Canvas(view_frame, width=(SHOW_WIDTH * scale_factor // 100),
                           height=(SHOW_HEIGHT * scale_factor // 100), borderwidth=0)
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=0, pady=0)

        text_area.bind("<KeyRelease>", update_global_text)  # 按键弹起时触发
        # text_area.bind("<FocusOut>", update_global_text)  # 当组件失去焦点触发
        update_global_canvas()

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area["yscrollcommand"] = scrollbar.set

        row += 1
        btn_frame = ttk.Frame(tech_frame, padding="5")
        btn_frame.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=0, pady=0)
        btn_frame.grid_columnconfigure(0, weight=1)  # 设置第1列自动调整宽度
        btn_frame.grid_columnconfigure(1, weight=1)  # 设置第2列自动调整宽度
        btn_frame.grid_columnconfigure(2, weight=1)  # 设置第3列自动调整宽度
        btn_frame.grid_columnconfigure(3, weight=1)  # 设置第4列自动调整宽度

        def show_error():
            update_global_canvas()
            print(full_custom_error.rstrip('\n'))
            if full_custom_error == "OK":
                tk.messagebox.showinfo(title="提示", message=full_custom_error, parent=sub_window)
            else:
                tk.messagebox.showerror(title="错误", message=full_custom_error, parent=sub_window)

        show_error_btn = ttk.Button(btn_frame, text="查看模板错误", width=15, padding=pad_scale_xy, command=show_error)
        show_error_btn.grid(row=0, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        def example(i):
            global config_obj
            if i == 1:
                full_custom_template = '\n'.join([
                    "i resource/example_background.png", "c #ff3333", "f resource/Orbitron-Regular.ttf 22",
                    "m 16 16", "v 1 {:.0f}", "p %",
                    "m 96 16", "v 2 {:.0f}", "p %",
                    "m 96 44", "v 3 {:.0f}", "p %"
                ])
            elif i == 2:
                full_custom_template = '\n'.join([
                    "m 8 8", "f resource/Orbitron-Bold.ttf 20", "p CPU", "t 8 0", "c #3366cc", "v 1",
                    "m 8 28", "c #000000", "f resource/Orbitron-Bold.ttf 20", "p GPU", "t 8 0", "c #3366cc", "v 2",
                    "m 8 48", "c #000000", "f resource/Orbitron-Bold.ttf 20", "p RAM", "t 8 0", "c #3366cc", "v 3"
                ])
            if full_custom_template != config_obj.full_custom_template:
                config_obj.full_custom_template = full_custom_template
                save_config()
            text_area.delete("1.0", tk.END)
            text_area.insert(tk.END, config_obj.full_custom_template)
            update_global_canvas()

        example_btn_1 = ttk.Button(btn_frame, text="科技", width=15, padding=pad_scale_xy, command=lambda: example(1))
        example_btn_1.grid(row=0, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        example_btn_2 = ttk.Button(btn_frame, text="简单", width=15, padding=pad_scale_xy, command=lambda: example(2))
        example_btn_2.grid(row=0, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        def show_instruction():
            instruction = '\n'.join([
                "自定义显示内容。一共有两个模式，第一个固定显示两行，有图表；第二个是完全自定义模式，可以自己加文本和图片。",
                "模板代码在框中输入，结果可以在预览中看到，模板代码从前往后顺序执行，每行执行一个操作。",
                "p [文本] \t\t绘制文本，会自动移动坐标",
                "a [锚点] \t\t更改文本锚点，参考Pillow文档，如la,ra,ls,rs",
                "m [x] [y] \t\t移动到坐标(x,y)",
                "t [x] [y] \t\t相对当前位置移动(x,y)",
                "f [文件名] [字号] \t更换字体，文件名如 arial.ttf",
                "c [hex码] \t\t更改文字颜色，如 c #ffff00",
                "i [文件名] \t\t绘制图片",
                "v [序号] [格式] \t绘制选择项目的值，格式符可省略，如 v 1 {:.2f}",
                "",
                "* 部分项目需要以管理员身份运行本程序，否则可能显示为<*>或--，甚至可能不会在项目下拉列表中显示。"
                "当选择没有权限的项目时，点击“查看模板错误”会给出错误提示。"
            ])
            tk.messagebox.showinfo(title="说明", message=instruction, parent=sub_window, icon='question')

        show_instruction_btn = ttk.Button(btn_frame, text="说明", width=15, padding=pad_scale_xy,
                                          command=show_instruction)
        show_instruction_btn.grid(row=0, column=3, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        # 添加“简单两项图表”标签页

        simple_frame = tk.Frame(master=sub_window)
        notebook.add(simple_frame, text="  显示两项图表  ")

        desc_label = tk.Label(simple_frame, text="名称")
        desc_label.grid(row=1, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        desc_label = tk.Label(simple_frame, text="项目")
        desc_label.grid(row=1, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        def update_sensor_value(event, vvars, i):
            global config_obj, custom_plot_data
            event.widget.selection_clear()
            if config_obj.custom_selected_names[i] != vvars[i].get():
                config_obj.custom_selected_names[i] = vvars[i].get()
                save_config()

                # 项目变更时清空旧项目数据
                if i == 0:
                    custom_plot_data["sent"] = [0] * (SHOW_WIDTH // 2)
                elif i == 1:
                    custom_plot_data["recv"] = [0] * (SHOW_WIDTH // 2)

        def change_sensor_displayname(dvars, i):
            global config_obj
            if config_obj.custom_selected_displayname[i] != dvars[i].get():
                config_obj.custom_selected_displayname[i] = dvars[i].get()
                save_config()
                change_netspeed_font()

        # "简单"模式显示2项
        for row in range(2):
            sensor_displayname_var = tk.StringVar(simple_frame, config_obj.custom_selected_displayname[row])
            sensor_displayname_vars.append(sensor_displayname_var)
            sensor_entry = ttk.Entry(simple_frame, textvariable=sensor_displayname_var, width=8)
            sensor_entry.bind("<KeyRelease>",
                              lambda event, ii=row: change_sensor_displayname(sensor_displayname_vars, ii))
            sensor_entry.grid(row=row + 2, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

            sensor_var = tk.StringVar(simple_frame, config_obj.custom_selected_names[row])
            sensor_vars.append(sensor_var)
            sensor_combobox = ttk.Combobox(simple_frame, textvariable=sensor_var, width=60,
                                           values=[""] + list(hardware_monitor_manager.sensors.keys()))
            sensor_combobox.bind("<<ComboboxSelected>>",
                                 lambda event, ii=row: update_sensor_value(event, sensor_vars, ii))
            sensor_combobox.grid(row=row + 2, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
            sensor_combobox.configure(state="readonly")  # 设置选择框不可编辑

        # 添加“图形化编辑”标签页：把模板代码完全图像化，无需接触代码即可完整使用所有命令
        visual_frame = tk.Frame(master=sub_window)
        notebook.add(visual_frame, text="  图形化编辑  ")

        CMD_NAMES = {"p": "文本", "a": "锚点", "m": "位置", "t": "偏移", "f": "字体", "c": "颜色", "i": "图片", "v": "数值",
                     "r": "矩形", "l": "线条", "o": "圆", "g": "动图"}

        def cmd_to_line(cmd):
            letter = cmd[0]
            if letter == "raw":
                return cmd[1]
            if letter == "p":
                return "p " + cmd[1]
            if letter == "a":
                return "a " + cmd[1]
            if letter == "m":
                return "m %s %s" % (cmd[1], cmd[2])
            if letter == "t":
                return "t %s %s" % (cmd[1], cmd[2])
            if letter == "f":
                return "f %s %s" % (cmd[1], cmd[2])
            if letter == "c":
                return "c " + cmd[1]
            if letter == "i":
                return "i " + cmd[1]
            if letter == "v":
                return "v %s %s" % (cmd[1], cmd[2]) if cmd[2] else "v " + cmd[1]
            if letter == "r":
                return "r %s %s %s %s" % (cmd[1], cmd[2], cmd[3], cmd[4])
            if letter == "l":
                return "l %s %s %s %s" % (cmd[1], cmd[2], cmd[3], cmd[4])
            if letter == "o":
                return "o %s %s %s" % (cmd[1], cmd[2], cmd[3])
            if letter == "g":
                return "g " + cmd[1]
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

        tip = tk.Label(visual_frame, text="双击列表项可编辑；下方按钮添加元素；右侧为实时预览。结果与“显示多项数值”页共享。",
                       anchor=tk.W, justify=tk.LEFT, fg="gray")
        tip.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        list_frame = ttk.Frame(visual_frame)
        list_frame.grid(row=1, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        cmd_listbox = tk.Listbox(list_frame, width=46, height=14, exportselection=False)
        scrollbar_v = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=cmd_listbox.yview)
        cmd_listbox.configure(yscrollcommand=scrollbar_v.set)
        cmd_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)

        visual_canvas = tk.Canvas(visual_frame, width=(SHOW_WIDTH * scale_factor // 100),
                                  height=(SHOW_HEIGHT * scale_factor // 100), borderwidth=0)
        visual_canvas.grid(row=1, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        def refresh_cmd_list():
            cmd_listbox.delete(0, tk.END)
            for cmd in visual_cmds:
                cmd_listbox.insert(tk.END, cmd_to_desc(cmd))

        def update_visual_preview():
            im = get_full_custom_im(update_sensors=False)
            im = im.resize((SHOW_WIDTH * scale_factor // 100, SHOW_HEIGHT * scale_factor // 100),
                           Image.Resampling.LANCZOS)
            tk_im = ImageTk.PhotoImage(im)
            visual_canvas.create_image(0, 0, anchor=tk.NW, image=tk_im)
            visual_canvas.image = tk_im

        def rebuild_template_and_preview():
            config_obj.full_custom_template = "\n".join(cmd_to_line(c) for c in visual_cmds)
            save_config()
            refresh_cmd_list()
            update_visual_preview()
            # 同步“显示多项数值”页的模板文本框
            text_area.delete("1.0", tk.END)
            text_area.insert(tk.END, config_obj.full_custom_template)

        def open_cmd_dialog(cmd_type, edit_index=None):
            dialog = tk.Toplevel(sub_window)
            dialog.title("添加" + CMD_NAMES.get(cmd_type, "") + ("" if edit_index is None else "（编辑）"))
            dialog.transient(sub_window)
            dialog.resizable(0, 0)

            existing = None
            if edit_index is not None and 0 <= edit_index < len(visual_cmds):
                existing = visual_cmds[edit_index]

            frm = ttk.Frame(dialog, padding=pad_scale_xy5 * 2)
            frm.grid(row=0, column=0, sticky=tk.NSEW)
            frm.grid_columnconfigure(1, weight=1)

            collect = None

            if cmd_type == "p":
                ttk.Label(frm, text="文字：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                var = tk.StringVar(frm, existing[1] if existing else "")
                ttk.Entry(frm, textvariable=var, width=32).grid(row=0, column=1, sticky=tk.EW, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: ("p", var.get())

            elif cmd_type == "v":
                ttk.Label(frm, text="数值项：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                idx_var = tk.StringVar(frm, existing[1] if existing else "1")
                ttk.Combobox(frm, textvariable=idx_var, values=["1", "2", "3", "4", "5", "6"], width=8,
                             state="readonly").grid(row=0, column=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                names_tip = "，".join("%d=%s" % (i + 1, (config_obj.custom_selected_displayname_tech[i]
                                     if i < len(config_obj.custom_selected_displayname_tech) and config_obj.custom_selected_displayname_tech[i]
                                     else "第%d项" % (i + 1))) for i in range(6))
                ttk.Label(frm, text=names_tip, foreground="gray", wraplength=320, justify=tk.LEFT).grid(
                    row=1, column=0, columnspan=2, sticky=tk.W, padx=pad_scale_xy5, pady=(0, pad_scale_xy5))
                ttk.Label(frm, text="格式(可选)：").grid(row=2, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                fmt_var = tk.StringVar(frm, existing[2] if existing else "")
                ttk.Entry(frm, textvariable=fmt_var, width=16).grid(row=2, column=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                ttk.Label(frm, text="例：{:.1f} 保留1位小数，留空则原样显示", foreground="gray").grid(
                    row=3, column=0, columnspan=2, sticky=tk.W, padx=pad_scale_xy5, pady=(0, pad_scale_xy5))
                collect = lambda: ("v", idx_var.get(), fmt_var.get().strip())

            elif cmd_type in ("m", "t"):
                label = "坐标 x / y：" if cmd_type == "m" else "偏移 dx / dy："
                ttk.Label(frm, text=label).grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                v1 = tk.StringVar(frm, existing[1] if existing else "0")
                v2 = tk.StringVar(frm, existing[2] if existing else "0")
                ttk.Entry(frm, textvariable=v1, width=8).grid(row=0, column=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                ttk.Entry(frm, textvariable=v2, width=8).grid(row=0, column=2, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: (cmd_type, v1.get(), v2.get())

            elif cmd_type == "a":
                anchors = ["la", "ma", "ra", "ls", "ms", "rs", "lt", "mt", "rt", "lm", "mm", "rm",
                           "lb", "mb", "rb", "ld", "md", "rd", "ct"]
                ttk.Label(frm, text="锚点：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                a_var = tk.StringVar(frm, existing[1] if existing else "la")
                ttk.Combobox(frm, textvariable=a_var, values=anchors, width=12).grid(
                    row=0, column=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                ttk.Label(frm, text="la/ra/ma=左/右/中 顶对齐，ls/rs/ms=基线，lb/rb=底部，ct=居中",
                          foreground="gray", wraplength=320, justify=tk.LEFT).grid(
                    row=1, column=0, columnspan=2, sticky=tk.W, padx=pad_scale_xy5, pady=(0, pad_scale_xy5))
                collect = lambda: ("a", a_var.get())

            elif cmd_type == "c":
                ttk.Label(frm, text="颜色：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                c_var = tk.StringVar(frm, existing[1] if existing else "#ff0000")
                ttk.Entry(frm, textvariable=c_var, width=12).grid(row=0, column=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)

                def pick_color():
                    color = tkinter.colorchooser.askcolor(color=c_var.get(), parent=dialog)
                    if color and color[1]:
                        c_var.set(color[1])

                ttk.Button(frm, text="调色板", padding=pad_scale_xy, command=pick_color).grid(
                    row=0, column=2, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: ("c", c_var.get())

            elif cmd_type == "f":
                ttk.Label(frm, text="字体文件：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                f_var = tk.StringVar(frm, existing[1] if existing else "")
                ttk.Entry(frm, textvariable=f_var, width=28).grid(row=0, column=1, sticky=tk.EW, padx=pad_scale_xy5, pady=pad_scale_xy5)

                def pick_font():
                    path = tkinter.filedialog.askopenfilename(parent=dialog, title="选择字体",
                                                              filetypes=[("字体文件", "*.ttf *.otf"), ("所有文件", "*.*")])
                    if path:
                        f_var.set(path)

                ttk.Button(frm, text="浏览…", padding=pad_scale_xy, command=pick_font).grid(
                    row=0, column=2, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                ttk.Label(frm, text="字号：").grid(row=1, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                s_var = tk.StringVar(frm, existing[2] if existing else "20")
                ttk.Entry(frm, textvariable=s_var, width=8).grid(row=1, column=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: ("f", f_var.get(), s_var.get())

            elif cmd_type == "i":
                ttk.Label(frm, text="图片文件：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                i_var = tk.StringVar(frm, existing[1] if existing else "")
                ttk.Entry(frm, textvariable=i_var, width=28).grid(row=0, column=1, sticky=tk.EW, padx=pad_scale_xy5, pady=pad_scale_xy5)

                def pick_image():
                    path = tkinter.filedialog.askopenfilename(parent=dialog, title="选择图片", filetypes=IMAGE_FILE_TYPES)
                    if path:
                        i_var.set(path)

                ttk.Button(frm, text="浏览…", padding=pad_scale_xy, command=pick_image).grid(
                    row=0, column=2, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: ("i", i_var.get())

            elif cmd_type in ("r", "l"):
                ttk.Label(frm, text="x1 y1 x2 y2：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                vals = []
                for k in range(4):
                    v = tk.StringVar(frm, existing[k + 1] if existing else "0")
                    vals.append(v)
                    ttk.Entry(frm, textvariable=v, width=6).grid(row=0, column=1 + k, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: (cmd_type, vals[0].get(), vals[1].get(), vals[2].get(), vals[3].get())

            elif cmd_type == "o":
                ttk.Label(frm, text="x y 半径：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                vals = []
                for k in range(3):
                    v = tk.StringVar(frm, existing[k + 1] if existing else "0")
                    vals.append(v)
                    ttk.Entry(frm, textvariable=v, width=6).grid(row=0, column=1 + k, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: ("o", vals[0].get(), vals[1].get(), vals[2].get())

            elif cmd_type == "g":
                ttk.Label(frm, text="GIF文件：").grid(row=0, column=0, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                g_var = tk.StringVar(frm, existing[1] if existing else "")
                ttk.Entry(frm, textvariable=g_var, width=28).grid(row=0, column=1, sticky=tk.EW, padx=pad_scale_xy5, pady=pad_scale_xy5)

                def pick_gif():
                    path = tkinter.filedialog.askopenfilename(parent=dialog, title="选择动图",
                                                              filetypes=[("GIF", "*.gif"), ("所有文件", "*.*")])
                    if path:
                        g_var.set(path)

                ttk.Button(frm, text="浏览…", padding=pad_scale_xy, command=pick_gif).grid(
                    row=0, column=2, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)
                collect = lambda: ("g", g_var.get())

            btn_row = ttk.Frame(frm)
            btn_row.grid(row=50, column=0, columnspan=3, sticky=tk.EW, pady=(pad_scale_xy5 * 2, 0))

            def on_ok():
                if collect is not None:
                    data = collect()
                    if edit_index is None:
                        visual_cmds.append(data)
                    else:
                        visual_cmds[edit_index] = data
                    rebuild_template_and_preview()
                dialog.destroy()

            ttk.Button(btn_row, text="确定", padding=pad_scale_xy, command=on_ok).pack(side=tk.RIGHT, padx=pad_scale_xy5)
            ttk.Button(btn_row, text="取消", padding=pad_scale_xy, command=dialog.destroy).pack(side=tk.RIGHT, padx=pad_scale_xy5)
            dialog.grab_set()

        def edit_selected():
            sel = cmd_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            cmd = visual_cmds[idx]
            if cmd[0] == "raw":
                tk.messagebox.showinfo("提示", "该行无法识别，请在“显示多项数值”页手动修改，或删除后重新添加。", parent=sub_window)
                return
            open_cmd_dialog(cmd[0], idx)

        def delete_selected():
            sel = cmd_listbox.curselection()
            if not sel:
                return
            del visual_cmds[sel[0]]
            rebuild_template_and_preview()

        def move_selected(delta):
            sel = cmd_listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            new_idx = idx + delta
            if 0 <= new_idx < len(visual_cmds):
                visual_cmds[idx], visual_cmds[new_idx] = visual_cmds[new_idx], visual_cmds[idx]
                rebuild_template_and_preview()
                cmd_listbox.selection_set(new_idx)

        def clear_all():
            if not visual_cmds:
                return
            if tk.messagebox.askyesno("确认", "确定清空所有元素吗？", parent=sub_window):
                visual_cmds[:] = []
                rebuild_template_and_preview()

        cmd_listbox.bind("<Double-Button-1>", lambda event: edit_selected())

        # 添加元素按钮
        btn_frame1 = ttk.Frame(visual_frame)
        btn_frame1.grid(row=2, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=(0, pad_scale_xy5))
        for i in range(8):
            btn_frame1.grid_columnconfigure(i, weight=1)
        add_buttons = [
            ("添加文本", "p"), ("添加数值", "v"), ("添加图片", "i"), ("添加位置", "m"),
            ("添加偏移", "t"), ("添加锚点", "a"), ("添加颜色", "c"), ("添加字体", "f"),
            ("添加矩形", "r"), ("添加线条", "l"), ("添加圆", "o"), ("添加动图", "g"),
        ]
        for idx, (label, letter) in enumerate(add_buttons):
            ttk.Button(btn_frame1, text=label, padding=pad_scale_xy,
                       command=lambda l=letter: open_cmd_dialog(l)).grid(
                row=idx // 8, column=idx % 8, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        # 编辑操作按钮
        btn_frame2 = ttk.Frame(visual_frame)
        btn_frame2.grid(row=3, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        for i in range(5):
            btn_frame2.grid_columnconfigure(i, weight=1)
        ttk.Button(btn_frame2, text="编辑", padding=pad_scale_xy, command=edit_selected).grid(
            row=0, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        ttk.Button(btn_frame2, text="删除", padding=pad_scale_xy, command=delete_selected).grid(
            row=0, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        ttk.Button(btn_frame2, text="上移", padding=pad_scale_xy, command=lambda: move_selected(-1)).grid(
            row=0, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        ttk.Button(btn_frame2, text="下移", padding=pad_scale_xy, command=lambda: move_selected(1)).grid(
            row=0, column=3, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        ttk.Button(btn_frame2, text="清空", padding=pad_scale_xy, command=clear_all).grid(
            row=0, column=4, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        # 预设/导入/导出
        btn_frame3 = ttk.Frame(visual_frame)
        btn_frame3.grid(row=4, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        for i in range(3):
            btn_frame3.grid_columnconfigure(i, weight=1)

        PRESET_TEMPLATES = {
            "大字时钟": ["c #00ccff", "f resource/Orbitron-Bold.ttf 40", "m 20 20", "p 12:00"],
            "监控面板": ["c #ffffff", "f resource/Orbitron-Bold.ttf 16", "m 4 4", "p CPU", "t 8 0", "v 1",
                       "m 4 30", "p RAM", "t 8 0", "v 2"],
            "简约问候": ["c #ffcc00", "f resource/Orbitron-Bold.ttf 20", "m 8 28", "p Hello"],
        }

        def apply_preset():
            win = tk.Toplevel(sub_window)
            win.title("选择预设模板")
            win.transient(sub_window)
            win.resizable(0, 0)

            def choose(name):
                visual_cmds[:] = parse_template_to_cmds("\n".join(PRESET_TEMPLATES[name]))
                rebuild_template_and_preview()
                win.destroy()

            for name in PRESET_TEMPLATES.keys():
                ttk.Button(win, text=name, padding=pad_scale_xy, command=lambda n=name: choose(n)).pack(
                    fill=tk.X, padx=pad_scale_xy5, pady=pad_scale_xy5)
            win.grab_set()

        def export_template():
            path = tkinter.filedialog.asksaveasfilename(defaultextension=".txt",
                                                        filetypes=[("模板文件", "*.txt")], title="导出模板")
            if not path:
                return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(config_obj.full_custom_template)
                insert_text_message("模板已导出到：%s" % path)
            except Exception as e:
                insert_text_message("导出模板失败：%s" % e)

        def import_template():
            path = tkinter.filedialog.askopenfilename(filetypes=[("模板文件", "*.txt")], title="导入模板")
            if not path:
                return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                visual_cmds[:] = parse_template_to_cmds(content)
                rebuild_template_and_preview()
                insert_text_message("模板已导入")
            except Exception as e:
                insert_text_message("导入模板失败：%s" % e)

        ttk.Button(btn_frame3, text="预设模板", padding=pad_scale_xy, command=apply_preset).grid(
            row=0, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        ttk.Button(btn_frame3, text="导入模板", padding=pad_scale_xy, command=import_template).grid(
            row=0, column=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
        ttk.Button(btn_frame3, text="导出模板", padding=pad_scale_xy, command=export_template).grid(
            row=0, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

        refresh_cmd_list()
        update_visual_preview()

    show_custom_btn = ttk.Button(root, text="自定义内容", width=12, padding=pad_scale_xy, command=show_custom)
    show_custom_btn.grid(row=5, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # 显示方向选择
    global lcd_direction_combobox
    lcd_direction_combobox = ttk.Combobox(root, values=LCD_STATE_MESSAGE, state="readonly", width=14)
    lcd_direction_combobox.grid(row=6, column=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    lcd_direction_combobox.bind("<<ComboboxSelected>>", on_lcd_direction_select)
    sync_lcd_combobox()

    # 上翻/下翻 并排（各半宽）
    page_btn_frame = ttk.Frame(root)
    page_btn_frame.grid(row=5, column=3, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    btn1 = ttk.Button(page_btn_frame, text="▲上翻", width=5, padding=pad_scale_xy, command=Page_UP)
    btn1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    btn2 = ttk.Button(page_btn_frame, text="▼下翻", width=5, padding=pad_scale_xy, command=Page_Down)
    btn2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 页面下拉选择列表
    global page_combobox
    page_combobox = ttk.Combobox(root, values=list(PAGE_ID.values()), state="readonly", width=14)
    page_combobox.grid(row=6, column=3, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    page_combobox.bind("<<ComboboxSelected>>", on_page_combobox_select)
    sync_page_combobox()  # 初始化当前页面显示

    # 创建颜色滑块

    def update_label_color(r1, g1, b1):
        global config_obj
        dev = get_current_device()
        if Label2:
            color_La = "#{:02x}{:02x}{:02x}".format(r1, g1, b1)
            Label2.config(bg=color_La)
        dev_color = ((r1 & 0xF8) << 8) | ((g1 & 0xFC) << 3) | ((b1 & 0xF8) >> 3)
        if dev is not None:
            dev.color_use = dev_color
        save_config()
        if dev is not None and config_obj.state_machine in [PCTIME_PAGE_ID, STATE_PAGE_ID]:
            dev.state_change = 1

    def update_label_color_red():
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.text_color_r = int(text_color_red_scale.get())
        update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    def update_label_color_green():
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.text_color_g = int(text_color_green_scale.get())
        update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    def update_label_color_blue():
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        config_obj.text_color_b = int(text_color_blue_scale.get())
        update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    scale_desc = tk.Label(root, text="文字颜色")
    scale_desc.grid(row=0, column=3, columnspan=1, sticky=tk.W, padx=pad_scale_xy5, pady=pad_scale_xy5)

    Label2 = tk.Label(root, width=2, borderwidth=pad_scale_xy)  # 颜色预览框
    Label2.grid(row=0, column=3, columnspan=1, sticky=tk.E, padx=pad_scale_xy5, pady=pad_scale_xy5)

    update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    # 预设颜色下拉列表（常用色 + 马卡龙色 + 丰富色卡）
    color_presets = {
        # === 基础色 ===
        "⚪ 纯白":       (255, 255, 255),
        "⚫ 纯黑":       (0, 0, 0),
        "🔴 大红":       (255, 0, 0),
        "🟢 翠绿":       (0, 255, 0),
        "🔵 宝蓝":       (0, 0, 255),
        "🟡 明黄":       (255, 255, 0),
        "🟣 紫罗兰":     (255, 0, 255),
        "🩵 天青":       (0, 255, 255),
        "🟠 橙色":       (255, 128, 0),
        "🩶 中灰":       (128, 128, 128),
        "🤎 棕色":       (139, 69, 19),
        "💗 粉色":       (255, 192, 203),
        # === 马卡龙色系 ===
        "—— 马卡龙色系 ——": None,
        "💗 马卡龙粉":   (255, 179, 186),
        "💚 马卡龙绿":   (186, 255, 201),
        "💙 马卡龙蓝":   (186, 225, 255),
        "💜 马卡龙紫":   (221, 186, 255),
        "🧡 马卡龙橘":   (255, 214, 186),
        "💛 马卡龙柠檬": (255, 255, 186),
        "🤍 马卡龙灰":   (210, 210, 210),
        "🤎 马卡龙棕":   (210, 180, 160),
        "💝 马卡龙红":   (255, 150, 150),
        "🩵 马卡龙青":   (180, 240, 240),
        # === Material Design 色系 ===
        "—— Material 色系 ——": None,
        "🔴 Red 500":    (244, 67, 54),
        "💗 Pink 300":   (240, 98, 146),
        "💜 DeepPurple": (103, 58, 183),
        "💙 Indigo":     (63, 81, 181),
        "🔵 Blue 500":   (33, 150, 243),
        "🩵 Cyan 500":   (0, 188, 212),
        "🟢 Teal 500":   (0, 150, 136),
        "🍏 LightGreen": (139, 195, 74),
        "🟡 Amber 500":  (255, 193, 7),
        "🟠 Orange 500": (255, 152, 0),
        "🤎 Brown 400":  (141, 110, 99),
        "🩶 BlueGrey":   (96, 125, 139),
        # === 暖色系 ===
        "—— 暖色系 ——": None,
        "🔥 暖橙":       (255, 140, 50),
        "🌅 夕阳橙":     (255, 180, 100),
        "🌹 玫瑰红":     (220, 50, 80),
        "🍑 蜜桃":       (255, 200, 170),
        "🍫 巧克力":     (139, 90, 43),
        "🍊 珊瑚":       (255, 127, 80),
        "🍓 草莓":       (255, 60, 80),
        "🥭 芒果":       (255, 180, 50),
        "🥕 胡萝卜":     (255, 140, 60),
        # === 冷色系 ===
        "—— 冷色系 ——": None,
        "❄ 冰蓝":       (135, 206, 235),
        "🌊 深海蓝":     (30, 80, 180),
        "🌿 薄荷绿":     (152, 255, 152),
        "🍀 森林绿":     (50, 150, 80),
        "💧 水滴蓝":     (100, 180, 255),
        "🫒 橄榄绿":     (107, 142, 35),
        "🌌 星空紫":     (75, 0, 130),
        "🐬 海豚灰":     (160, 190, 210),
        # === 暗色系 ===
        "—— 暗色系 ——": None,
        "⬛ 炭灰":       (60, 60, 60),
        "⬜ 银白":       (200, 200, 200),
        "🟤 暗金":       (200, 160, 60),
        "💎 午夜蓝":     (20, 30, 80),
        "🖤 深灰":       (40, 40, 40),
        "🤍 象牙白":     (240, 230, 210),
        "💜 暗紫":       (80, 40, 120),
        "💚 暗绿":       (30, 80, 40),
        # === 霓虹/荧光 ===
        "—— 霓虹色系 ——": None,
        "💚 霓虹绿":     (57, 255, 20),
        "💗 霓虹粉":     (255, 20, 147),
        "💛 霓虹黄":     (255, 255, 50),
        "💙 霓虹蓝":     (50, 200, 255),
        "🧡 霓虹橙":     (255, 100, 20),
        "💜 霓虹紫":     (180, 50, 255),
    }

    def apply_color_preset(event=None):
        name = color_combo.get()
        rgb = color_presets.get(name)
        if rgb is None:
            return
        r, g, b = rgb
        text_color_red_scale.set(r)
        text_color_green_scale.set(g)
        text_color_blue_scale.set(b)
        update_label_color(r, g, b)

    color_combo = ttk.Combobox(root, values=list(color_presets.keys()), state="readonly", width=14)
    color_combo.grid(row=1, column=3, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    color_combo.bind("<<ComboboxSelected>>", apply_color_preset)
    # 初始显示当前颜色匹配
    current_rgb = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
    for name, rgb in color_presets.items():
        if rgb == current_rgb:
            color_combo.set(name)
            break

    color_frame = ttk.Frame(root, padding="0")
    color_frame.grid(row=0, column=4, rowspan=3, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    color_frame.grid_columnconfigure(1, weight=1)  # 设置第2列自动调整宽度
    color_frame.grid_propagate(0)  # 禁止被内部控件撑大

    scale_ind_r = tk.Label(color_frame, text="R")
    scale_ind_r.grid(row=0, column=0, sticky=tk.NSEW, padx=0, pady=pad_scale_xy5)

    text_color_red_scale = tk.Scale(color_frame, from_=0, to=255, orient=tk.HORIZONTAL, borderwidth=0,
                                    width=scale_factor // 10, sliderlength=scale_factor // 8,
                                    takefocus=1, resolution=1, troughcolor="red", font=("TkDefaultFont", 9))
    text_color_red_scale.grid(row=0, column=1, sticky=tk.NSEW, padx=0, pady=0)
    text_color_red_scale.set(config_obj.text_color_r)
    text_color_red_scale.config(command=lambda x: update_label_color_red())

    scale_ind_g = tk.Label(color_frame, text="G")
    scale_ind_g.grid(row=1, column=0, sticky=tk.NSEW, padx=0, pady=pad_scale_xy5)

    text_color_green_scale = tk.Scale(color_frame, from_=0, to=255, orient=tk.HORIZONTAL, borderwidth=0,
                                      width=scale_factor // 10, sliderlength=scale_factor // 8,
                                      takefocus=1, resolution=1, troughcolor="green", font=("TkDefaultFont", 9))
    text_color_green_scale.grid(row=1, column=1, sticky=tk.NSEW, padx=0, pady=0)
    text_color_green_scale.set(config_obj.text_color_g)
    text_color_green_scale.config(command=lambda x: update_label_color_green())

    scale_ind_b = tk.Label(color_frame, text="B")
    scale_ind_b.grid(row=2, column=0, sticky=tk.NSEW, padx=0, pady=pad_scale_xy5)

    text_color_blue_scale = tk.Scale(color_frame, from_=0, to=255, orient=tk.HORIZONTAL, borderwidth=0,
                                     width=scale_factor // 10, sliderlength=scale_factor // 8,
                                     takefocus=1, resolution=1, troughcolor="blue", font=("TkDefaultFont", 9))
    text_color_blue_scale.grid(row=2, column=1, sticky=tk.NSEW, padx=0, pady=0)
    text_color_blue_scale.set(config_obj.text_color_b)
    text_color_blue_scale.config(command=lambda x: update_label_color_blue())

    # 镜像视频填充方式：裁剪/适应

    def change_shrink_type(value):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        if value != config_obj.shrink_type:
            config_obj.shrink_type = value
            save_config()

    shrink_type = tk.IntVar(root, config_obj.shrink_type)
    shrink_type_button1 = tk.Radiobutton(root, text=" 填充", anchor="center", value=1, variable=shrink_type,
                                         command=lambda: change_shrink_type(shrink_type.get()))
    shrink_type_button1.grid(row=3, column=4, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    shrink_type_button2 = tk.Radiobutton(root, text=" 适应", anchor="center", value=2, variable=shrink_type,
                                         command=lambda: change_shrink_type(shrink_type.get()))
    shrink_type_button2.grid(row=3, column=5, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # 创建自定义单选圆圈，因为默认圆圈在高分屏下不能自动调整大小，导致圆圈太小
    font_size = 12 * scale_factor // 100
    select_img = Image.new('RGBA', (24, 24), (255, 255, 255, 0))
    draw = ImageDraw.Draw(select_img)
    draw.ellipse([2, 2, 22, 22], outline='#0078d7', width=1)
    draw.ellipse([8, 8, 16, 16], fill='#0078d7')
    select_img = select_img.resize((font_size, font_size), Image.Resampling.LANCZOS)
    select_tk = ImageTk.PhotoImage(select_img)
    unselect_img = Image.new('RGBA', (24, 24), (255, 255, 255, 0))
    draw = ImageDraw.Draw(unselect_img)
    draw.ellipse([2, 2, 22, 22], outline='#888888', width=1)
    unselect_img = unselect_img.resize((font_size, font_size), Image.Resampling.LANCZOS)
    unselect_tk = ImageTk.PhotoImage(unselect_img)
    # 使用自定义单选圆圈
    shrink_type_button1.config(image=unselect_tk, selectimage=select_tk, indicatoron=0, compound=tk.LEFT, bd=0,
                               relief=tk.FLAT, overrelief=tk.FLAT, highlightthickness=0, selectcolor='#f0f0f0')
    shrink_type_button2.config(image=unselect_tk, selectimage=select_tk, indicatoron=0, compound=tk.LEFT, bd=0,
                               relief=tk.FLAT, overrelief=tk.FLAT, highlightthickness=0, selectcolor='#f0f0f0')

    # 动图间隔

    def change_photo_interval(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        try:
            photo_interval_tmp = float(interval_var.get())
        except ValueError as e:
            if len(interval_var.get()) > 0:
                insert_text_message("Invalid number entered: %s" % e)
            return
        if (photo_interval_tmp >= 0 and config_obj.photo_interval_var + config_obj.second_times !=
                photo_interval_tmp):
            config_obj.second_times = int(photo_interval_tmp)  # 舍去小数部分
            config_obj.photo_interval_var = photo_interval_tmp - config_obj.second_times
            if config_obj.second_times > 0 and config_obj.photo_interval_var < 0.2:
                config_obj.photo_interval_var += 1
                config_obj.second_times -= 1
            if config_obj.state_machine == GIF_PAGE_ID:
                state_change_set()
            else:
                save_config()

    interval_var = tk.StringVar(root, "0.1")
    interval_var.trace_add("write", change_photo_interval)
    interval_var.set(config_obj.photo_interval_var + config_obj.second_times)

    label_screen_number = ttk.Label(root, text="动图间隔")
    label_screen_number.grid(row=4, column=4, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    number_entry = ttk.Entry(root, textvariable=interval_var, width=4)
    number_entry.grid(row=4, column=5, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # fps

    def change_fps(*args):
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        screenshot_limit_fps_tmp = 0
        try:
            screenshot_limit_fps_tmp = int(fps_var.get())
        except ValueError as e:
            if len(fps_var.get()) > 0:
                insert_text_message("Invalid number entered: %s" % e)
            return
        if 0 < screenshot_limit_fps_tmp != config_obj.fps_var:
            config_obj.fps_var = screenshot_limit_fps_tmp
            save_config()

    fps_var = tk.StringVar(root, "5")
    fps_var.trace_add("write", change_fps)
    fps_var.set(config_obj.fps_var)

    label = ttk.Label(root, text="最大 FPS")
    label.grid(row=5, column=4, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    fps_entry = ttk.Entry(root, textvariable=fps_var, width=4)
    fps_entry.grid(row=5, column=5, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # 相机编号

    def combo_configure(event):
        combo = event.widget
        values = combo.cget('values')
        if len(values) == 0:
            return

        font = tkfont.nametofont(str(combo.cget('font')))
        maxWidth = combo.winfo_width()
        for value in values:
            fontw = font.measure(value)
            if maxWidth < fontw:
                maxWidth = fontw

        if len(values) > 10:
            maxWidth += font.measure('000') - combo.winfo_width()
        else:
            maxWidth += font.measure('0') - combo.winfo_width()
        width = combo.winfo_screenwidth() - combo.winfo_rootx() - combo.winfo_width()
        if width < 0 or width > maxWidth:
            width = maxWidth

        # create an unique style name using widget's id
        style_name = combo.cget('style') or "TCombobox"
        # the new style must inherit from curret widget style (unless it's our custom style!)
        if str(combo.winfo_id()) not in style_name:
            style_name = "Combobox%s.%s" % (combo.winfo_id(), style_name)
        style = ttk.Style()
        style.configure(style_name, postoffset=(0, 0, width, 0))
        combo.configure(style=style_name)

    def update_camera_list(event):
        global config_obj, all_cameras
        all_cameras = get_all_cameras()
        event.widget["value"] = list(all_cameras.keys())
        if config_obj.camera_var not in all_cameras.keys():
            config_obj.camera_var = list(all_cameras.keys())[0]
            event.widget.set(config_obj.camera_var)
        combo_configure(event)

    def update_select_camera(event):
        global config_obj, all_cameras
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        dev = get_current_device()
        event.widget.selection_clear()
        camera_id = event.widget.get()
        if camera_id != config_obj.camera_var:
            config_obj.camera_var = camera_id
            if config_obj.state_machine == CAMERA_VIDEO_ID and dev:
                clear_queue(dev.screen_shot_queue)
                clear_queue(dev.screen_process_queue)
                state_change_set()
            else:
                save_config()

    label_camera_number = ttk.Label(root, text="相机名称")
    label_camera_number.grid(row=6, column=4, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    all_cameras = get_all_cameras()
    if len(all_cameras) > 1:
        PAGE_ID[CAMERA_VIDEO_ID] = PAGE_ID_EN[CAMERA_VIDEO_ID] if config_obj.language == "English" else PAGE_ID_CN[CAMERA_VIDEO_ID]
        # 用于保持页面的顺序
        new_PAGE_ID = sorted(PAGE_ID.items(), key=lambda a: a[0])
        PAGE_ID.clear()
        PAGE_ID.update(new_PAGE_ID)
    if not config_obj.camera_var or config_obj.camera_var not in all_cameras.keys():
        config_obj.camera_var = list(all_cameras.keys())[0]
    camera_var = tk.StringVar(root, config_obj.camera_var)
    # camera_var.trace_add("write", change_screenshot_monitor)

    camera_combobox = ttk.Combobox(root, textvariable=camera_var, width=4, values=list(all_cameras.keys()))
    camera_combobox.bind('<Configure>', combo_configure)
    camera_combobox.bind('<ButtonPress>', update_camera_list)
    camera_combobox.bind("<KeyPress>", update_camera_list)
    camera_combobox.bind("<<ComboboxSelected>>", update_select_camera)
    camera_combobox.grid(row=6, column=5, columnspan=1, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    camera_combobox.configure(state="readonly")  # 设置选择框不可编辑

    def update_windows_list(event):
        global config_obj, all_windows
        if isWindows:
            all_windows = get_all_windows()  # 带缓存刷新，避免每次点击都全量枚举造成卡顿
        desc = get_hwnd_desc(config_obj.select_window_hwnd)
        if desc:
            event.widget.set(desc)
        event.widget["values"] = sorted(all_windows.keys(), key=str.lower)
        combo_configure(event)

    def update_select_hwnd(event):
        global config_obj, all_windows
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        dev = get_current_device()
        event.widget.selection_clear()
        select_str = event.widget.get()
        select_window_hwnd, _ = all_windows.get(select_str)
        if select_window_hwnd != config_obj.select_window_hwnd:
            config_obj.select_window_hwnd = select_window_hwnd
            if config_obj.state_machine == SCREEN_PAGE_ID and dev:
                dev.screen_frame_generation += 1
                clear_queue(dev.screen_shot_queue)
                clear_queue(dev.screen_process_queue)
                time.sleep(0.05)
                clear_queue(dev.screen_shot_queue)
                clear_queue(dev.screen_process_queue)
                state_change_set()
            else:
                save_config()

    label = ttk.Label(root, text="屏幕镜像窗口:")
    label.grid(row=7, column=2, columnspan=1, sticky=tk.E, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # 先用桌面占位初始化下拉框，窗口列表在后台线程枚举完成后刷新，避免启动时同步枚举所有窗口造成卡顿
    global desktop_hwnd
    if desktop_hwnd == 0:
        desktop_hwnd = win32gui.GetDesktopWindow()
    if not all_windows:
        all_windows = {"[%s] - 桌面" % desktop_hwnd: (desktop_hwnd, 0)}

    select_windows = get_hwnd_desc(config_obj.select_window_hwnd)
    if select_windows is None:
        select_windows = list(all_windows.keys())[0]
        config_obj.select_window_hwnd, _ = all_windows.get(select_windows)
    win32_windows_var = tk.StringVar(root, select_windows)

    windows_combobox = ttk.Combobox(root, textvariable=win32_windows_var, width=10,
                                    values=sorted(all_windows.keys(), key=str.lower))
    windows_combobox.bind('<Configure>', combo_configure)
    windows_combobox.bind('<ButtonPress>', update_windows_list)
    windows_combobox.bind("<KeyPress>", update_windows_list)
    windows_combobox.bind("<<ComboboxSelected>>", update_select_hwnd)
    windows_combobox.grid(row=7, column=3, columnspan=3, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    windows_combobox.configure(state="readonly")  # 设置选择框不可编辑

    # 后台线程枚举窗口列表，完成后刷新下拉框
    def load_windows_async():
        global all_windows
        wins = None
        try:
            wins = get_all_windows()
        except Exception:
            wins = None
        if wins:
            def apply_windows():
                global all_windows
                all_windows = wins
                try:
                    windows_combobox["values"] = sorted(wins.keys(), key=str.lower)
                    desc = get_hwnd_desc(config_obj.select_window_hwnd)
                    if desc:
                        win32_windows_var.set(desc)
                        windows_combobox.set(desc)
                except Exception:
                    pass
            window.after(0, apply_windows)

    threading.Thread(target=load_windows_async, daemon=True).start()

    # ==================== LCD 屏幕分辨率设置 ====================
    label_lcd_size = ttk.Label(root, text="屏幕分辨率:")
    label_lcd_size.grid(row=8, column=2, columnspan=1, sticky=tk.E, padx=pad_scale_xy5, pady=pad_scale_xy5)

    global lcd_size_var
    lcd_size_var = tk.StringVar(root)
    current_size = str(LCD_MAX_X) + 'x' + str(LCD_MAX_Y) + ' (默认)'
    lcd_size_options = ['160x80 (默认)', '128x64 (0.96寸OLED)', '240x240 (1.54寸)',
                        '320x240 (2.4寸)', '240x320 (竖屏)']
    if current_size not in lcd_size_options:
        lcd_size_options.insert(0, current_size)
    lcd_size_var.set(current_size)
    lcd_size_menu = ttk.OptionMenu(root, lcd_size_var, current_size, *lcd_size_options,
                                   command=Set_LCD_Size_Manual)
    lcd_size_menu.grid(row=8, column=3, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)
    lcd_size_menu.configure(width=18)

    btn_detect_lcd = ttk.Button(root, text="检测屏幕", width=9, command=ReDetect_LCD_Size)
    btn_detect_lcd.grid(row=8, column=4, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    # ==================== 设备切换联动：主控页控件刷新 ====================
    def _apply_main_ui_to_config():
        """把当前设备配置刷新到主控页控件（切换设备时调用）"""
        global config_obj, lcd_size_var
        try:
            # 文字颜色滑块 + 颜色预览
            text_color_red_scale.set(config_obj.text_color_r)
            text_color_green_scale.set(config_obj.text_color_g)
            text_color_blue_scale.set(config_obj.text_color_b)
            update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
            # 预设颜色匹配
            cur_rgb = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
            matched = None
            for name, rgb in color_presets.items():
                if rgb == cur_rgb:
                    matched = name
                    break
            color_combo.set(matched or "")
            # 动图间隔 / FPS
            interval_var.set(config_obj.photo_interval_var + config_obj.second_times)
            fps_var.set(config_obj.fps_var)
            # 相机
            if config_obj.camera_var in all_cameras:
                camera_var.set(config_obj.camera_var)
            # 填充/适应
            shrink_type.set(config_obj.shrink_type)
            # 分辨率下拉
            cur_size = "%dx%d (默认)" % (LCD_MAX_X, LCD_MAX_Y)
            if cur_size not in lcd_size_options:
                lcd_size_options.insert(0, cur_size)
            lcd_size_var.set(cur_size)
            # 镜像窗口
            desc = get_hwnd_desc(config_obj.select_window_hwnd)
            if desc:
                win32_windows_var.set(desc)
            # 页面/方向下拉
            sync_page_combobox()
            sync_lcd_combobox()
        except Exception as e:
            print("刷新主控页控件失败：%s" % e)

    # ==================== 实时预览 ====================
    preview_label = ttk.Label(root, text="实时预览:")
    preview_label.grid(row=9, column=0, columnspan=6, sticky=tk.W, padx=pad_scale_xy5, pady=(pad_scale_xy5, 0))
    
    # 预览画布：宽度自适应（最大480），高度按比例，居中显示
    preview_max_w = 480
    preview_max_h = int(preview_max_w * SHOW_HEIGHT / SHOW_WIDTH)  # 2:1 → 240
    preview_canvas = tk.Canvas(root, width=preview_max_w, height=preview_max_h,
                               bg='black', highlightthickness=1, 
                               highlightbackground='gray')
    preview_canvas.grid(row=10, column=0, columnspan=6, sticky=tk.NSEW, 
                        padx=pad_scale_xy5, pady=pad_scale_xy5)
    # 配置行/列权重使canvas居中
    root.grid_rowconfigure(10, weight=0)
    
    def update_preview():
        """定时刷新预览画面（自动缩放居中）"""
        if config_obj and config_obj.preview_enabled:
            dev = get_current_device()
            if dev:
                with dev._preview_lock:
                    img = dev.last_preview_rgb
            else:
                img = None
            if img is not None and img.size > 0:
                try:
                    cw = preview_canvas.winfo_width()
                    ch = preview_canvas.winfo_height()
                    if cw > 10 and ch > 10:
                        # 计算缩放比例，保持2:1宽高比，取较小维度适应
                        scale_w = cw / SHOW_WIDTH
                        scale_h = ch / SHOW_HEIGHT
                        scale = min(scale_w, scale_h)
                        new_w = int(SHOW_WIDTH * scale)
                        new_h = int(SHOW_HEIGHT * scale)
                        # 居中偏移
                        ox = (cw - new_w) // 2
                        oy = (ch - new_h) // 2
                        
                        pil_img = Image.fromarray(img, 'RGB')
                        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.NEAREST)
                        tk_img = ImageTk.PhotoImage(pil_img)
                        preview_canvas.delete("all")
                        preview_canvas.create_image(ox, oy, anchor=tk.NW, image=tk_img)
                        preview_canvas.image = tk_img
                except Exception:
                    pass
        window.after(200, update_preview)
    
    update_preview()

    def on_closing():
        stop_api_server()
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.resizable(0, 0)  # 锁定窗口大小不能改变
    # 点击最小化按钮时隐藏窗口
    # window.bind("<Unmap>", lambda event: hide_to_tray() if window.state() == "iconic" else False)
    if len(sys.argv) > 1:
        arg = sys.argv[1].lstrip('-').lower()
        if arg == "h" or arg == "hide":
            hide_to_tray()  # 命令行启动时设置隐藏

    # 参数全部获取后再启动截图线程（幂等启动，避免与daemon线程重复启动）
    if _primary_device:
        _primary_device.start_threads()
    manager_thread.start()
    
    # 定期刷新设备列表 + 恢复当前设备上次的页面/方向选择
    last_synced_device_state = None
    def _periodic_refresh():
        nonlocal last_synced_device_state
        refresh_device_list()
        try:
            # 设备配置加载/变化后，把页面/方向下拉框同步为该设备上次的状态
            dev = get_current_device()
            if dev is not None and dev.config is not None:
                key = (dev.device_name, dev.config.state_machine, dev.config.lcd_change)
                if key != last_synced_device_state:
                    last_synced_device_state = key
                    sync_page_combobox()
                    sync_lcd_combobox()
        except Exception:
            pass
        window.after(2000, _periodic_refresh)
    window.after(2000, _periodic_refresh)

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
        window.after(1000, _auto_cycle_tick)
    window.after(1000, _auto_cycle_tick)

    # 启动本地 API 投屏服务器（HTTP + WebSocket）
    try:
        if getattr(config_obj, "api_enable", 1):
            start_api_server()
    except Exception as e:
        print("启动 API 服务器失败：%s" % e)

    # 进入消息循环
    window.mainloop()


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
    device.state_machine = config_obj.state_machine  # 继承当前页面（每屏独立配置）
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

    if write_path_index != 0:
        if write_path_index == 1:
            photo_path = Label3.get("1.0", tk.END).rstrip()
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
        if config_obj.state_machine == PCTIME_PAGE_ID:
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
    """打开传感器选择子窗口。
    mode: "multi"=多选(硬件详情) / "single"=单选(仪表盘某项)
    type_filter: 传感器类型过滤（如 "Temperature"），None=全部
    on_done: 确定保存后回调（用于刷新界面显示）
    """
    global config_obj, hardware_monitor_manager
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        tk.messagebox.showinfo(title="提示", message="硬件监控未就绪，请稍后再试。", parent=parent)
        return
    sensors = hardware_monitor_manager.list_sensors()
    if type_filter:
        sensors = [x for x in sensors if x[3] == type_filter]
    if not sensors:
        tk.messagebox.showinfo(
            title="提示",
            message="未检测到%s传感器。\n主板传感器(CPU温度/风扇等)需以管理员身份运行才能读取。" % (type_filter or ""),
            parent=parent)
        return

    picker = tk.Toplevel(parent)
    picker.title(title)
    picker.resizable(0, 0)
    picker.transient(parent)
    if label_hint:
        ttk.Label(picker, text=label_hint, wraplength=430, justify=tk.LEFT).pack(anchor=tk.W, padx=10, pady=(10, 4))

    body = ttk.Frame(picker)
    body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
    canvas = tk.Canvas(body, width=440, height=280)
    scrollbar = ttk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
    list_frame = ttk.Frame(canvas)
    list_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=list_frame, anchor=tk.NW)
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    if mode == "multi":
        current = [n.strip() for n in (getattr(config_obj, cfg_key) or "").split(",") if n.strip()]
        vars_map = {}
        for name, hw, s, t, val in sensors:
            var = tk.IntVar(list_frame, 1 if name in current else 0)
            vars_map[name] = var
            ttk.Checkbutton(list_frame, text=_format_sensor_display(name, val), variable=var).pack(anchor=tk.W)
    else:
        current = getattr(config_obj, cfg_key) or ""
        selected = tk.StringVar(list_frame, current or "AUTO")
        ttk.Radiobutton(list_frame, text="自动检测（推荐）", value="AUTO", variable=selected).pack(anchor=tk.W)
        for name, hw, s, t, val in sensors:
            ttk.Radiobutton(list_frame, text=_format_sensor_display(name, val), value=name, variable=selected).pack(anchor=tk.W)

    def on_ok():
        global config_obj
        _ui_set_active()  # 锁定到UI当前设备（避免多屏设置冲突）
        if mode == "multi":
            sel = [n for n, v in vars_map.items() if v.get()]
            setattr(config_obj, cfg_key, ",".join(sel))
        else:
            val = selected.get()
            setattr(config_obj, cfg_key, "" if val == "AUTO" else val)
        save_config()
        picker.destroy()
        if on_done:
            on_done()

    btn_bar = ttk.Frame(picker)
    btn_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
    ttk.Button(btn_bar, text="确定", padding=(20, 4), command=on_ok).pack(side=tk.RIGHT, padx=(5, 0))
    ttk.Button(btn_bar, text="取消", padding=(20, 4), command=picker.destroy).pack(side=tk.RIGHT)


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


def daemon_task():
    global Device_State_Labelen, screen_off, last_key_activity_time, config_obj, preferred_com_port
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
                # 定期重新扫描（可能有新设备插入）
                now = time.monotonic()
                if now - last_scan_time < 5:
                    continue
                last_scan_time = now
            
            # 无设备连接或定期扫描：检测新设备
            if Device_State_Labelen == 2:
                if _primary_device:
                    set_current_device(_primary_device)
                set_device_state(_primary_device.device_state if _primary_device else 0)

            if _primary_device is None:
                _init_single_device()
            
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
            tk.messagebox.showerror(title="错误", message=message)
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
        # 结束时保存配置
        save_config(True)
        if load_thread.is_alive():
            load_thread.join(timeout=5.0)

        sys.exit(exit_code)

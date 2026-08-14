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
PROGRAM_VERSION = "4.5.1"
PROGRAM_AUTHOR = "杜玛"
PROGRAM_GITHUB = "https://github.com/duma520/MSU2_MINI_V2"
PROGRAM_LICENSE = "MIT"
PROGRAM_BUILD_DATE = "2026-08-13"

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
        
        # --- 网络/自定义图表数据 ---
        self.netspeed_last_refresh_snetio = None
        self.netspeed_plot_data = None
        self.custom_plot_data = None
        self.last_data_half = (0, 0)
        
        # --- MSN设备信息 ---
        self.msn_device = None
        self.msn_data = None
        self.ADC_det = 0
        self.adc_fail_count = 0  # ADC读取连续失败计数
        
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


def show_netspeed(text_color=(255, 128, 0), bar1_color=(235, 139, 139),
                  bar2_color=(146, 211, 217), back_color=(0, 0, 0)):
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

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back_color)
    draw = ImageDraw.Draw(im1)

    text = "上传 %9s/s" % sizeof_fmt(sent_per_second)
    draw.text((0, 0), text, fill=text_color, font=default_font)
    text = "下载 %9s/s" % sizeof_fmt(recv_per_second)
    draw.text((0, SHOW_HEIGHT // 2), text, fill=text_color, font=default_font)

    min_draw = 1
    for start_y, key, color in zip([SHOW_HEIGHT // 4 - 1, SHOW_HEIGHT - SHOW_HEIGHT // 4 - 1],
                                   ["sent", "recv"], [bar1_color, bar2_color]):
        sent_values = dev.netspeed_plot_data[key]
        max_value = max(min_draw, max(sent_values))

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
        HWDETAIL_PAGE_ID: ("硬件详情：设置监控类型与数量", 5, (1, "monitor")),
        GAUGE_PAGE_ID: ("仪表盘：设置项目与颜色", 5, (2, "monitor")),
        SCREEN_PAGE_ID: ("屏幕镜像：设置放大镜", 6, None),
    }

    ttk.Label(page_guide_frame, text="选择页面，查看该页面有哪些设置并可一键前往：").pack(anchor=tk.W, pady=(0, pad_scale_xy5))
    guide_combobox = ttk.Combobox(page_guide_frame, state="readonly", width=26)
    guide_combobox.pack(anchor=tk.W, pady=pad_scale_xy5)
    guide_desc = tk.Label(page_guide_frame, text="", wraplength=320, justify=tk.LEFT, fg="gray")
    guide_desc.pack(anchor=tk.W, pady=pad_scale_xy5)

    def on_guide_select(event=None):
        name = guide_combobox.get()
        for pid, pname in PAGE_ID.items():
            if pname == name:
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
        config_obj.marquee_font = marquee_font_var.get() or "./simhei.ttf"
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

    marquee_font_row = ttk.Frame(marquee_frame)
    marquee_font_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Label(marquee_font_row, text="字体文件:").pack(side=tk.LEFT)
    marquee_font_var = tk.StringVar(marquee_frame, config_obj.marquee_font)
    ttk.Entry(marquee_font_row, textvariable=marquee_font_var, width=24).pack(side=tk.LEFT, padx=pad_scale_xy5)

    def pick_marquee_font():
        path = tkinter.filedialog.askopenfilename(parent=window, title="选择字体",
                                                  filetypes=[("字体文件", "*.ttf *.otf"), ("所有文件", "*.*")])
        if path:
            marquee_font_var.set(path)

    ttk.Button(marquee_font_row, text="浏览…", padding=pad_scale_xy, command=pick_marquee_font).pack(side=tk.LEFT)

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
            font_path = marquee_font_var.get() or "./simhei.ttf"
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
    marquee_font_var.trace_add("write", change_marquee)
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
            marquee_font_var.set(config_obj.marquee_font)
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
            # ---- 屏幕镜像 ----
            zoom_enable_var.set(config_obj.zoom_enable)
            zoom_scale_var.set(config_obj.zoom_scale)
        except Exception as e:
            print("刷新设置页控件失败：%s" % e)

    # ---- 子页6：数据管理 ----
    data_frame = ttk.Frame(settings_notebook, padding=(pad_scale_xy5 * 2, pad_scale_xy5 * 2))
    settings_notebook.add(data_frame, text="  数据管理  ")

    cfg_row = ttk.Frame(data_frame)
    cfg_row.pack(anchor=tk.W, pady=pad_scale_xy5)
    ttk.Button(cfg_row, text="导出配置", width=12, padding=pad_scale_xy, command=export_config).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))
    ttk.Button(cfg_row, text="导入配置", width=12, padding=pad_scale_xy, command=import_config).pack(side=tk.LEFT, padx=(0, pad_scale_xy5))

    def check_update_async():
        threading.Thread(target=check_update, daemon=True).start()

    ttk.Button(cfg_row, text="检查更新", width=12, padding=pad_scale_xy, command=check_update_async).pack(side=tk.LEFT)

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
    
    # 定期刷新设备列表
    def _periodic_refresh():
        refresh_device_list()
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
            rgb_tuple = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
            show_netspeed(text_color=rgb_tuple, bar1_color=bar_colors[0], bar2_color=bar_colors[1],
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
    try:
        font = MiniMark.load_font(config_obj.marquee_font or "./simhei.ttf", font_size)
    except Exception:
        font = MiniMark.load_font("./simhei.ttf", font_size)
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


def show_diskio():
    """磁盘实时读写速率"""
    global diskio_last, diskio_last_time
    dev = get_current_device()
    if dev is None:
        return
    if dev.state_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        diskio_last = psutil.disk_io_counters()
        diskio_last_time = time.monotonic()
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
    except Exception:
        read_s = 0
        write_s = 0
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(im1)
    font = MiniMark.load_font("./simhei.ttf", 16)
    draw.text((4, 6), "磁盘读写", fill=(255, 255, 255), font=font)
    draw.text((4, 34), "读 %.1f MB/s" % (read_s / 1048576.0), fill=(255, 128, 0), font=font)
    draw.text((4, 56), "写 %.1f MB/s" % (write_s / 1048576.0), fill=(0, 255, 255), font=font)
    rgb888 = np.asarray(im1, dtype=np.uint32)
    _safe_send_rgb888(rgb888)
    dev.sleep_event.wait(0.5)


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

        MG_daemon_running = True
        primary.mg_screen_thread_running = True
        MG_screen_thread_running = True
        daemon_thread = threading.Thread(target=daemon_task, daemon=True)
        load_thread = threading.Thread(target=load_task, daemon=True)
        manager_thread = threading.Thread(target=manage_task, daemon=True)
        ping_thread = threading.Thread(target=ping_worker, daemon=True)
        primary.screen_shot_thread = threading.Thread(target=screen_shot_task, args=(primary,), daemon=True)
        primary.screen_process_thread = threading.Thread(target=screen_process_task, args=(primary,), daemon=True)

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

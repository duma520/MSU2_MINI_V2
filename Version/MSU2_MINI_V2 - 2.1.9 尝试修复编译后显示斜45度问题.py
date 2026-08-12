#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import glob
import json  # 用于保存json格式配置
import os  # 用于读取文件
import queue  # geezmo: 流水线同步和交换数据用
import sys
import threading  # 引入多线程支持
import time  # 引入延时库
import tkinter as tk  # 引入UI库
import tkinter.filedialog  # 用于获取文件路径
import tkinter.font as tkfont
import tkinter.messagebox
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
PROGRAM_VERSION = "2.1.6"
PROGRAM_AUTHOR = "杜玛"
PROGRAM_GITHUB = "https://github.com/duma520/MSU2_MINI_V2"
PROGRAM_LICENSE = "MIT"
PROGRAM_BUILD_DATE = "2026-08-11"

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

    def parse_line(self, line, draw, img, record_dict=None):
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

    def parse(self, size, lines, record_dict=None):
        img = Image.new("RGBA", size, color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        for line in lines:
            self.parse_line(line, draw, img, record_dict)
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

        if not self.hwnd:
            # 初始化资源
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
PAGE_ID = {
    GIF_PAGE_ID: "动图",
    PCTIME_PAGE_ID: "时间",
    PHOTO_PAGE_ID: "单个相册图片",
    SCREEN_PAGE_ID: "屏幕镜像",
    STATE_PAGE_ID: "电脑CPU/内存/磁盘/电池使用率监控",
    NETSPEED_PAGE_ID: "网络流量监控",
    ABOUT_PAGE_ID: "关于",
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


def get_all_windows():
    global desktop_hwnd

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

    return hwnd_titles


class Win32_Image:
    def __init__(self, rgb=None, bgra=None, size=(0, 0)):
        self.rgb = rgb
        self.bgra = bgra
        self.size = size


default_capture = None


def get_window_image(hWnd=None):
    global desktop_hwnd, default_capture

    # 显示器截图（hWnd 为负数表示显示器编号，-1=屏幕1, -2=屏幕2...）
    if hWnd is not None and hWnd < 0:
        monitor_index = -hWnd
        with mss() as sct:
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
        with mss() as sct:
            monitor = sct.monitors[0]  # 0号是完整桌面
            sct_img = sct.grab(monitor)
            return Win32_Image(rgb=sct_img.rgb, size=(sct_img.width, sct_img.height))

    # 普通窗口截图：使用 ContinuousCapture (PrintWindow API)
    if not default_capture:
        default_capture = ContinuousCapture()
    default_capture.set_hwnd(hWnd)
    bmpstr, width, height = default_capture.capture_window()
    # 使用DPI缩放后的实际位图尺寸，避免下游数据长度校验失败
    dpi_w, dpi_h = default_capture.get_actual_size()
    return Win32_Image(bgra=bmpstr, size=(dpi_w, dpi_h))


def insert_text_message(text, cleanNext=True, item=None):
    global Text1, cleanNextTime
    if text:
        print(text)
    if item is None:
        if Text1 is None:
            return
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
    global State_change, sleep_event, burn_offset_x, burn_offset_y, burn_offset_time
    State_change = 1
    sleep_event.set()  # 取消sleep, 使sleep_event.wait无效
    # 切换页面时重置防烧屏偏移
    burn_offset_x = 0
    burn_offset_y = 0
    burn_offset_time = 0
    if save:
        save_config()
    if message is not None:
        insert_text_message(message)


def state_change_clear():
    global State_change, sleep_event
    State_change = 0
    sleep_event.clear()  # 使sleep_event.wait生效


def Page_UP():  # 上一页
    global config_obj, State_change, sleep_event
    try:
        index = list(PAGE_ID.keys()).index(config_obj.state_machine)
        if index >= len(PAGE_ID) - 1:
            index = 0
        else:
            index = index + 1
    except:
        index = 0
    config_obj.state_machine = list(PAGE_ID.keys())[index]
    if config_obj.state_machine == CAMERA_VIDEO_ID:
        clear_queue(screen_shot_queue)  # 清空缓存
        clear_queue(screen_process_queue)  # 清空缓存
    state_change_set(PAGE_ID[config_obj.state_machine])
    sync_page_combobox()


def Page_Down():  # 下一页
    global config_obj, State_change, sleep_event
    try:
        index = list(PAGE_ID.keys()).index(config_obj.state_machine)
        if index == 0:
            index = len(PAGE_ID) - 1
        else:
            index = index - 1
    except:
        index = 0
    config_obj.state_machine = list(PAGE_ID.keys())[index]
    if config_obj.state_machine == SCREEN_PAGE_ID:
        clear_queue(screen_shot_queue)  # 清空缓存
        clear_queue(screen_process_queue)  # 清空缓存
    state_change_set(PAGE_ID[config_obj.state_machine])
    sync_page_combobox()


def sync_page_combobox():
    """同步页面下拉列表的显示值"""
    global page_combobox, config_obj
    if page_combobox is not None:
        try:
            page_combobox['values'] = list(PAGE_ID.values())
            page_name = PAGE_ID.get(config_obj.state_machine, "")
            page_combobox.set(page_name)
        except Exception:
            pass


def on_page_combobox_select(event):
    """用户通过下拉列表选择页面"""
    global config_obj, page_combobox, screen_shot_queue, screen_process_queue
    event.widget.selection_clear()
    selected_name = page_combobox.get()
    for pid, pname in PAGE_ID.items():
        if pname == selected_name:
            if config_obj.state_machine != pid:
                config_obj.state_machine = pid
                if pid == CAMERA_VIDEO_ID or pid == SCREEN_PAGE_ID:
                    clear_queue(screen_shot_queue)
                    clear_queue(screen_process_queue)
                state_change_set(pname)
            break


def LCD_Change():  # 切换显示方向（循环）
    global config_obj, Device_State, sleep_event
    if Device_State == 0:
        insert_text_message("设备未连接，切换失败")
        return
    config_obj.lcd_change = (config_obj.lcd_change + 1) % len(LCD_STATE_MESSAGE)
    state_change_set(LCD_STATE_MESSAGE[config_obj.lcd_change])
    sync_lcd_combobox()


def set_lcd_direction(index):
    """直接设置显示方向"""
    global config_obj, Device_State, sleep_event
    if Device_State == 0:
        insert_text_message("设备未连接，切换失败")
        return
    if config_obj.lcd_change != index:
        config_obj.lcd_change = index
        state_change_set(LCD_STATE_MESSAGE[config_obj.lcd_change])


def sync_lcd_combobox():
    """同步显示方向下拉列表"""
    global lcd_direction_combobox, config_obj
    if lcd_direction_combobox is not None:
        try:
            lcd_direction_combobox.set(LCD_STATE_MESSAGE[config_obj.lcd_change])
        except Exception:
            pass


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
    global ser
    # 尝试发出指令,有两种无法正确发送命令的情况：1.设备被移除,发送出错；2.设备处于MSN连接状态，对于电脑发送的指令响应迟缓
    ser.reset_input_buffer()  # 清空输出缓存
    ser.write(Data_U0)
    ser.flush()


# 由于设备不支持多线程访问，请不要直接使用SER_Read，应使用SER_rw方法
def SER_Read():
    global ser
    trytimes = 500000  # 尝试次数计数，防止一直获取不到数据
    recv = ser.read(ser.in_waiting)
    while len(recv) == 0 and trytimes > 0:
        recv = ser.read(ser.in_waiting)
        trytimes -= 1
    if trytimes == 0:
        print("SER_Read timeout")
        # raise RuntimeError("SER_Read timeout")
        return 0
    return recv


def SER_rw(data, read=True, size=0):
    global ser, SER_lock

    result = bytearray()
    SER_lock.acquire()
    try:
        if not ser.is_open:
            print("设备未连接，取消串口读写")
            return result

        SER_Write(data)  # 发出指令
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
    set_device_state(0)
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
    hex_use = bytearray()
    hex_use.append(8)  # 读取ADC
    hex_use.append(ch)  # 通道
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 5 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return recv[4] * 256 + recv[5]
    else:
        print("Read_ADC_CH failed, will reconnect: %s" % recv)
        set_device_state(0)
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
    global burn_offset_x, burn_offset_y, burn_offset_time, config_obj
    if not config_obj or config_obj.anti_burn == 0:
        burn_offset_x = 0
        burn_offset_y = 0
        return
    now = time.monotonic()
    if now - burn_offset_time > BURN_INTERVAL:
        burn_offset_time = now
        idx = int(now // BURN_INTERVAL) % len(BURN_OFFSETS)
        burn_offset_x, burn_offset_y = BURN_OFFSETS[idx]

def LCD_ADD(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size):
    # 防烧屏：微调显示位置
    update_burn_offset()
    x = max(0, LCD_X + burn_offset_x)
    y = max(0, LCD_Y + burn_offset_y)
    hex_use = LCD_Set_XY(x, y)
    hex_use.extend(LCD_Set_Size(LCD_X_Size, LCD_Y_Size))
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(7)  # 载入地址
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == 2 and recv[1] == 3:
        return 1
    else:
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

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 5 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        LCD_Color_set(0, 0, SHOW_WIDTH, SHOW_HEIGHT, (0, 0, 0))  # 切换方向后屏幕会变白，改成黑色
        # print("LCD towards change to: %s" % LCD_S)
        return 1
    else:
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
    global config_obj, second_pass, sleep_event, last_refresh_time, gif_wait_time, State_change, gif_num
    current_monoto_time = time.monotonic()
    if State_change == 1:
        state_change_clear()
        # gif_num = 0
        gif_wait_time = 0
        last_refresh_time = current_monoto_time
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    if gif_num > 35:
        gif_num = 0

    LCD_Photo(gif_num * 100)

    # 因为设备超过5秒没有发送图片，就会认为断开了，所以这里每秒发送一次同一张图片
    if config_obj.second_times != 0:
        if second_pass < config_obj.second_times:
            second_pass += 1
            sleep_event.wait(1)
            return
        else:
            second_pass = 0

    gif_num = gif_num + 1
    # 精确调整动图播放速度
    elapse_time = current_monoto_time - last_refresh_time
    last_refresh_time = current_monoto_time
    if elapse_time - config_obj.second_times > config_obj.photo_interval_var + 5:
        gif_wait_time = config_obj.photo_interval_var
    else:
        gif_wait_time += config_obj.photo_interval_var - elapse_time + config_obj.second_times
    if gif_wait_time > 0:
        sleep_event.wait(gif_wait_time)


def show_PC_state(FC, BC):  # 显示PC状态
    global State_change, sleep_event, last_refresh_time, wait_time
    current_monoto_time = time.monotonic()
    photo_add = 4038
    num_add = 4026
    if State_change == 1:
        state_change_clear()
        wait_time = 0
        last_refresh_time = current_monoto_time
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

    seconds_elapsed = current_monoto_time - last_refresh_time
    last_refresh_time = current_monoto_time
    # 1秒左右刷新一次
    wait_time += 1 - seconds_elapsed
    if wait_time > 0:
        sleep_event.wait(wait_time)


def show_Photo():  # 显示照片
    global State_change, sleep_event
    if State_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    LCD_Photo(3926)  # 放置背景
    sleep_event.wait(1)  # 1秒刷新一次


def show_PC_time(FC):
    """显示24小时制 HH:MM 大字时间（32x64字体，满屏）"""
    global State_change, sleep_event
    num_add = 3651  # ASC64 大字库
    if State_change == 1:
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

    if time_m != 59:
        sleep_event.wait(1)
    else:
        sleep_event.wait(1 - current_time.microsecond / 1000000.0)


def digit_to_ints(di):
    return [(di >> 24) & 0xFF, (di >> 16) & 0xFF, (di >> 8) & 0xFF, di & 0xFF]


def Screen_Date_Process(Photo_data):  # 对数据进行转换处理
    total_data_size = len(Photo_data)  # SHOW_WIDTH * SHOW_HEIGHT ?
    data_per_page = 128
    data_page1 = 0
    data_page2 = 0
    hex_use = bytearray()
    for j in range(0, total_data_size // data_per_page):  # 每次写入一个Page
        data_page1 = data_page2
        data_page2 += data_per_page
        data_w = Photo_data[data_page1: data_page2]
        cmp_use = data_w[::2] << 16 | data_w[1::2]  # 256字节数据分为64个指令

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
        cmp_use = data_w[::2] << 16 | data_w[1::2]
        for i, cmp_value in enumerate(cmp_use):
            hex_use.extend([4, i])
            hex_use.extend(digit_to_ints(cmp_value))
        hex_use.extend([2, 3, 8, 0, remaining_data_size * 2, 0])
    return hex_use


# in: [[[255 255 255]]], type: np.asarray((((r, g, b),),)), out: [[rgb565_int]]
def rgb888_to_rgb565(rgb888_array):
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

    # Calculate the new shape
    new_shape = (int(image.shape[0] / shrink_factor), int(image.shape[1] / shrink_factor))

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

    return np.mean(shrunk_parts, axis=0, dtype=np.uint32)

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
    global config_obj, windows_combobox, screen_shot_queue, screen_process_queue
    config_obj.select_window_hwnd = hwnd
    save_config()
    clear_queue(screen_shot_queue)  # 清空缓存，防止显示旧的窗口
    clear_queue(screen_process_queue)  # 清空缓存，防止显示旧的窗口
    desc = get_hwnd_desc(hwnd)
    if not desc:
        desc = hwnd
    windows_combobox.set(desc)


def clear_queue(queue):
    for _ in range(queue.qsize()):
        queue.get()


def screen_shot_task():  # 创建专门的函数来获取屏幕图像和处理转换数据
    global config_obj, all_cameras, MG_screen_thread_running, Device_State, screen_shot_queue, desktop_hwnd
    global screenshot_last_limit_time, wait_time
    if not isWindows:
        from mss import mss

        sct = mss()
        # 序号为0的monitor是总体屏幕
        monitor = sct.monitors[0]
        # cropped_monitor = {
        #     "left": screenshot_region[0] + monitor["left"],
        #     "top": screenshot_region[1] + monitor["top"],
        #     "width": screenshot_region[2] or monitor["width"],
        #     "height": screenshot_region[3] or monitor["height"],
        #     "mon": screenshot_monitor_id,
        # }
        cropped_monitor = monitor
        cropped_monitor["mon"] = 0

    wait_time = 0
    screenshot_last_limit_time = time.monotonic()
    print("Start screenshot")
    while MG_screen_thread_running:
        if Device_State != 1 or (config_obj.state_machine != SCREEN_PAGE_ID
                                 and config_obj.state_machine != CAMERA_VIDEO_ID):
            if not screen_shot_queue.empty():
                time.sleep(0.5)  # 等一下再清空，防止页面切换缓慢
                clear_queue(screen_shot_queue)  # 清空缓存，防止显示旧的窗口
            time.sleep(0.5)  # 不需要截图时
            continue
        if screen_shot_queue.full():
            time.sleep(1.0 / config_obj.fps_var)
            # if screen_shot_queue.full():  # 这儿用于防止队列堆积，但是因为队列长度只有2，所以也不怕，所以注释掉
            #     screen_shot_queue.get()

        try:
            if config_obj.state_machine == CAMERA_VIDEO_ID:
                camera_id = all_cameras.get(config_obj.camera_var)
                if camera_id is None:
                    # 没有图像时显示黑色背景
                    rgb888 = get_draw_text("请选择相机…")
                    image = Win32_Image(rgb=rgb888, size=(LCD_MAX_X, LCD_MAX_Y))
                    screen_shot_queue.put((image, {"width": LCD_MAX_X, "height": LCD_MAX_Y}), timeout=1)
                    time.sleep(0.5)
                    continue

                # 打开相机
                rgb888 = get_draw_text("打开中…")
                image = Win32_Image(rgb=rgb888, size=(LCD_MAX_X, LCD_MAX_Y))
                screen_shot_queue.put((image, {"width": LCD_MAX_X, "height": LCD_MAX_Y}), timeout=1)
                camera_name = config_obj.camera_var
                # 偶尔会出现打开很慢的情况，暂无法解决
                cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)  # 默认媒体类型是CAP_MSMF，可能会导致设置分辨率失败，所以改为CAP_DSHOW
                try:
                    if cap.isOpened():
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, LCD_MAX_X)  # 这个设置不一定生效，cv2会使用摄像头支持的最近的分辨率
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, LCD_MAX_Y)
                        # cap.set(cv2.CAP_PROP_FPS, config_obj.fps_var)  # 这个程序中相机fps无效
                        # cap.set(cv2.CAP_PROP_EXPOSURE, 4)  # 曝光度调节
                        # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 缓冲帧数量大小
                        # cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)  # 是否将图像转为RGB，取值0/1
                        # cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))  # 设置视频编码为MJPG
                        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        last_time = time.monotonic()
                        while (MG_screen_thread_running and Device_State == 1
                               and config_obj.state_machine == CAMERA_VIDEO_ID
                               and camera_name == config_obj.camera_var):
                            # 色调应该在0-360之间，摄像头断开时先返回13，然后返回-1。但是有些摄像头不支持该参数始终返回-1
                            cap_hue = cap.get(cv2.CAP_PROP_HUE)
                            if cap_hue == 13:
                                time.sleep(1)
                                raise Exception("get CAP_PROP_HUE failed")
                            if screen_shot_queue.full():
                                time.sleep(1.0 / config_obj.fps_var)
                                # if screen_shot_queue.full():
                                #     screen_shot_queue.get()
                            suc, frame = cap.read()
                            if not suc:
                                raise Exception("cap.read() failed")
                            current_time = time.monotonic()
                            if current_time - last_time > 5.0:  # 解决待机恢复后图像异常问题
                                raise Exception("cap.read() timeout")
                            last_time = current_time
                            image = Win32_Image(rgb=frame[:, :, [2, 1, 0]], size=(width, height))
                            try:
                                screen_shot_queue.put((image, {"width": width, "height": height}), timeout=1)
                            except queue.Full:
                                time.sleep(1.0 / config_obj.fps_var)
                                continue

                            # 精确控制FPS
                            fps_control()
                    else:
                        raise Exception("capture open failed")
                finally:
                    cap.release()
            elif isWindows:
                sct_img = get_window_image(config_obj.select_window_hwnd)
                screen_shot_queue.put((sct_img, {"width": sct_img.size[0], "height": sct_img.size[1]}), timeout=1)
            else:
                sct_img = sct.grab(cropped_monitor)  # geezmo: 截屏已优化
                screen_shot_queue.put((sct_img, cropped_monitor), timeout=1)
        except queue.Full:
            time.sleep(1.0 / config_obj.fps_var)
            continue
        except Exception as e:
            print("获取图像失败 %s" % traceback.format_exc())
            # 没有图像时显示黑色背景
            image = Win32_Image(rgb=bytes(6), size=(2, 1))
            screen_shot_queue.put((image, {"width": 2, "height": 1}), timeout=1)
            time.sleep(0.5)
            continue

        # 精确控制FPS
        fps_control()

    # stop
    print("Stop screenshot")


def fps_control():
    global screenshot_last_limit_time, wait_time, sleep_event  # 用于控制TPS
    global screen_shot_queue, screenshot_test_time, screenshot_test_frame  # 用于计算串流FPS
    # 精确控制FPS
    current_monoto_time = time.monotonic()
    elapse_time = current_monoto_time - screenshot_last_limit_time
    if elapse_time > 5:  # 有切换，重置参数
        wait_time = 0
        elapse_time = 1.0 / config_obj.fps_var  # 第一次不需要wait

    #     # 这段用于计算串流FPS，不需要可以注释掉（缩进格式就是这样的，不需要改动）
    #     screenshot_test_frame = 1
    #     screenshot_test_time = current_monoto_time - 1
    # elif (screenshot_test_frame % config_obj.fps_var) == 0:
    #     # 测试用：显示帧率
    #     real_fps = config_obj.fps_var / (current_monoto_time - screenshot_test_time)
    #     print("串流FPS: %s" % real_fps)
    #     screenshot_test_time = current_monoto_time
    # screenshot_test_frame += 1

    screenshot_last_limit_time = current_monoto_time
    wait_time += 1.0 / config_obj.fps_var - elapse_time
    if wait_time > 0:
        sleep_event.wait(wait_time)  # 精确控制FPS
    elif wait_time < -5:
        wait_time = 0


# geezmo: 流水线 第二步 处理图像
def screen_process_task():
    global config_obj, MG_screen_thread_running, Device_State, screen_process_queue, screen_shot_queue
    print("Start screen process")
    while MG_screen_thread_running:
        if Device_State != 1 or (config_obj.state_machine != SCREEN_PAGE_ID
                                 and config_obj.state_machine != CAMERA_VIDEO_ID):
            if not screen_process_queue.empty():
                time.sleep(0.5)  # 等一下再清空，防止页面切换缓慢
                clear_queue(screen_process_queue)  # 清空缓存，防止显示旧的窗口
            time.sleep(0.5)  # 不需要截图时
            continue

        try:
            if screen_process_queue.full():
                time.sleep(1.0 / config_obj.fps_var)
                # if screen_process_queue.full():  # 这儿用于防止队列堆积，但是因为队列长度只有2，所以也不怕，所以注释掉
                #     screen_process_queue.get()

            # 转换图像为rgb格式
            sct_img, monitor = screen_shot_queue.get(timeout=2)
            if sct_img.rgb is None:
                # win32gui截图 (PrintWindow API)
                bgra = sct_img.bgra
                img_w, img_h = sct_img.size
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
            else:
                rgb = sct_img.rgb  # 相机视频
                if type(rgb) == bytes:  # sct.grab截图
                    rgb = np.frombuffer(rgb, dtype=np.uint8).reshape((sct_img.size[1], sct_img.size[0], 3))

            # 是否需要旋转90度
            # if sct_img.size[1] > sct_img.size[0]:
            #     rgb = np.rot90(rgb, 1)

            # 压缩图像到LCD屏幕尺寸，不足的填充
            width = monitor["width"]
            heightx2 = monitor["height"] * 2
            if config_obj.shrink_type == 1:
                # 方法1：裁剪以 填充屏幕
                if width > heightx2:  # 图片长宽比例超过2:1
                    im1 = shrink_image_block_average(rgb, rgb.shape[0] / LCD_MAX_Y)
                    offset = (im1.shape[1] - LCD_MAX_X) // 2
                    im1 = im1[:, offset: LCD_MAX_X + offset]
                else:  # 纵向裁剪
                    im1 = shrink_image_block_average(rgb, rgb.shape[1] / LCD_MAX_X)
                    offset = (im1.shape[0] - LCD_MAX_Y) // 2
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

            # 转化为可直接写入小屏幕的格式
            # rgb888 = np.asarray(im1)
            rgb565 = rgb888_to_rgb565(im1)
            # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
            hexstream = Screen_Date_Process(rgb565.flatten())

            screen_process_queue.put(hexstream, timeout=1)
        except (queue.Empty, queue.Full):
            continue
        except Exception as e:
            print("screen_process_task error: %s" % traceback.format_exc())
            time.sleep(0.2)

    # stop
    print("Stop screen process")


# 重启截图线程
def screenshot_panic(clean_queue=True):
    global MG_screen_thread_running, screen_shot_thread, screen_process_thread, screen_shot_queue, screen_process_queue
    MG_screen_thread_running = False
    screen_shot_thread_old = screen_shot_thread
    screen_process_thread_old = screen_process_thread
    screen_shot_thread = threading.Thread(target=screen_shot_task, daemon=True)
    screen_process_thread = threading.Thread(target=screen_process_task, daemon=True)

    if clean_queue:
        clear_queue(screen_shot_queue)  # 清空缓存，防止显示旧的窗口
        clear_queue(screen_process_queue)  # 清空缓存，防止显示旧的窗口
    if screen_shot_thread_old.is_alive():
        screen_shot_thread_old.join()
    if screen_process_thread_old.is_alive():
        screen_process_thread_old.join()

    MG_screen_thread_running = True
    screen_shot_thread.start()
    screen_process_thread.start()


def show_PC_Screen():  # 显示屏幕镜像 / 相机视频
    global State_change, screen_process_queue, LCD_MAX_X, LCD_MAX_Y
    if State_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, LCD_MAX_X, LCD_MAX_Y)

    try:
        hexstream = screen_process_queue.get(timeout=0.3)  # timeout设置较小，用于增加页面切换效率
    except queue.Empty:
        return
    SER_rw(hexstream, read=False)  # 发出指令


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


def show_netspeed(text_color=(255, 128, 0), bar1_color=(235, 139, 139),
                  bar2_color=(146, 211, 217), back_color=(0, 0, 0)):
    global last_refresh_time, netspeed_last_refresh_snetio, netspeed_plot_data
    global default_font, State_change, wait_time, sleep_event, last_data_half
    current_monoto_time = time.monotonic()

    current_snetio = psutil.net_io_counters()
    # geezmo: 预渲染图片，显示网速
    if State_change == 1:
        state_change_clear()
        wait_time = 0
        last_refresh_time = current_monoto_time - 0.001  # -0.001防止出现除0错误
        netspeed_last_refresh_snetio = current_snetio
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    # 获取网速 bytes/second
    seconds_elapsed = current_monoto_time - last_refresh_time

    # 因为刷新间隔刚好是1秒，所以不需要除时间
    sent_per_second = (current_snetio.bytes_sent - netspeed_last_refresh_snetio.bytes_sent) / seconds_elapsed
    recv_per_second = (current_snetio.bytes_recv - netspeed_last_refresh_snetio.bytes_recv) / seconds_elapsed
    new_data_half = (sent_per_second // 2, recv_per_second // 2)
    sent_per_second = last_data_half[0] + new_data_half[0]
    recv_per_second = last_data_half[1] + new_data_half[1]
    last_data_half = new_data_half
    netspeed_plot_data["sent"].pop(0)
    netspeed_plot_data["recv"].pop(0)
    netspeed_plot_data["sent"].append(sent_per_second)
    netspeed_plot_data["recv"].append(recv_per_second)

    last_refresh_time = current_monoto_time
    netspeed_last_refresh_snetio = current_snetio

    # 绘制图片
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back_color)
    draw = ImageDraw.Draw(im1)

    # 绘制文字
    text = "上传 %9s/s" % sizeof_fmt(sent_per_second)
    draw.text((0, 0), text, fill=text_color, font=default_font)
    text = "下载 %9s/s" % sizeof_fmt(recv_per_second)
    draw.text((0, SHOW_HEIGHT // 2), text, fill=text_color, font=default_font)

    # 绘图
    min_draw = 1  # 最小范围
    for start_y, key, color in zip([SHOW_HEIGHT // 4 - 1, SHOW_HEIGHT - SHOW_HEIGHT // 4 - 1],
                                   ["sent", "recv"], [bar1_color, bar2_color]):
        sent_values = netspeed_plot_data[key]
        max_value = max(min_draw, max(sent_values))

        x0 = -BAR_WIDTH
        x1 = -1
        y1 = IMAGE_HEIGHT + start_y
        percent = IMAGE_HEIGHT / max_value
        for i, sent in enumerate(sent_values[-(SHOW_WIDTH // BAR_WIDTH):]):
            # Scale the sent value to the image height
            bar_height = percent * sent
            x0 += BAR_WIDTH
            x1 += BAR_WIDTH
            y0 = y1 - bar_height

            # Draw the bar
            draw.rectangle([x0, y0, x1, y1], fill=color)

    rgb888 = np.asarray(im1, dtype=np.uint32)
    rgb565 = rgb888_to_rgb565(rgb888)
    # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
    hex_use = Screen_Date_Process(rgb565.flatten())
    SER_rw(hex_use, read=False)  # 发出指令

    # 大约每1秒刷新一次
    wait_time += 1 - seconds_elapsed
    if wait_time > 0:
        sleep_event.wait(wait_time)


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
    rgb565 = rgb888_to_rgb565(rgb888)
    hex_use = Screen_Date_Process(rgb565.flatten())
    SER_rw(hex_use, read=False)


def show_custom_two_rows(text_color=(255, 128, 0), bar1_color=(235, 139, 139),
                         bar2_color=(146, 211, 217), back_color=(0, 0, 0)):
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global config_obj, last_refresh_time, State_change, wait_time
    global custom_plot_data, hardware_monitor_manager, netspeed_font, sleep_event
    current_monoto_time = time.monotonic()
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        draw_text("加载中…")
        sleep_event.wait(0.5)
        return

    if State_change == 1:
        state_change_clear()
        wait_time = 0
        last_refresh_time = current_monoto_time
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

    custom_plot_data["sent"].pop(0)
    custom_plot_data["sent"].append(sent)
    custom_plot_data["recv"].pop(0)
    custom_plot_data["recv"].append(recv)

    seconds_elapsed = current_monoto_time - last_refresh_time
    last_refresh_time = current_monoto_time

    # 绘制图片

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), back_color)

    draw = ImageDraw.Draw(im1)

    # 绘制文字

    text = "%-6s %-s" % (config_obj.custom_selected_displayname[0][:8], sent_text)
    draw.text((0, 0), text, fill=text_color, font=netspeed_font)
    text = "%-6s %-s" % (config_obj.custom_selected_displayname[1][:8], recv_text)
    draw.text((0, SHOW_HEIGHT // 2), text, fill=text_color, font=netspeed_font)

    # 绘图
    # 决定最小范围, 需大于0
    min_max = [0.001, 0.001]
    for start_y, key, color, minmax_it in zip([SHOW_HEIGHT // 4 - 1, SHOW_HEIGHT - SHOW_HEIGHT // 4 - 1],
                                              ["sent", "recv"], [bar1_color, bar2_color], min_max):
        sent_values = custom_plot_data[key]

        min_value = min(sent_values)  # 防止显示太满
        max_value = max(minmax_it, min_value * 2, max(sent_values))

        x0 = -BAR_WIDTH
        x1 = -1
        y1 = IMAGE_HEIGHT + start_y
        percent = IMAGE_HEIGHT / max_value
        for i, sent in enumerate(sent_values[-(SHOW_WIDTH // BAR_WIDTH):]):
            # Scale the sent value to the image height
            bar_height = percent * sent
            x0 += BAR_WIDTH
            x1 += BAR_WIDTH
            y0 = y1 - bar_height

            # Draw the bar
            draw.rectangle([x0, y0, x1, y1], fill=color)

    rgb888 = np.asarray(im1, dtype=np.uint32)
    rgb565 = rgb888_to_rgb565(rgb888)
    # arr = np.frombuffer(rgb565.flatten().tobytes(), dtype=np.uint16).astype(np.uint32)
    hex_use = Screen_Date_Process(rgb565.flatten())
    SER_rw(hex_use, read=False)  # 发出指令

    # 大约每1秒刷新一次
    wait_time += 1 - seconds_elapsed
    if wait_time > 0:
        sleep_event.wait(wait_time)


def get_full_custom_im():
    global config_obj, full_custom_error, mini_mark_parser, hardware_monitor_manager

    full_custom_error_tmp = ""
    # 获取 libre hardware monitor 数值
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
            value, value_formatted = hardware_monitor_manager.get_value_formatted(name)
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
        for line in config_obj.full_custom_template.split('\n'):
            line = line.rstrip('\r')  # possible
            error_line = line
            mini_mark_parser.parse_line(line, draw, im1, record_dict=record_dict)
        if full_custom_error_tmp != "":
            if full_custom_error != full_custom_error_tmp:
                full_custom_error = full_custom_error_tmp
        elif full_custom_error != "OK":
            full_custom_error = "OK"
    except Exception as e:
        full_custom_error = "%s\nerror line: %s" % (traceback.format_exc(), error_line)
        im1.paste((255, 0, 255), (0, 0, im1.size[0], im1.size[1]))  # 异常时显示粉色

    return im1


def show_full_custom():
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global last_refresh_time, State_change, wait_time, hardware_monitor_manager, sleep_event
    current_monoto_time = time.monotonic()
    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        draw_text("加载中…")
        sleep_event.wait(0.5)
        return

    if State_change == 1:
        state_change_clear()
        wait_time = 0
        last_refresh_time = current_monoto_time
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    seconds_elapsed = current_monoto_time - last_refresh_time

    last_refresh_time = current_monoto_time

    im1 = get_full_custom_im()

    rgb888 = np.asarray(im1, dtype=np.uint32)
    rgb565 = rgb888_to_rgb565(rgb888)
    # arr = np.frombuffer(rgb565.flatten().tobytes(), dtype=np.uint16).astype(np.uint32)
    hex_use = Screen_Date_Process(rgb565.flatten())
    SER_rw(hex_use, read=False)  # 发出指令

    # 大约每1秒刷新一次
    wait_time += 1 - seconds_elapsed
    if wait_time > 0:
        sleep_event.wait(wait_time)


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
        if config_event.isSet():
            config_event.clear()  # 使config_event.wait生效
        config_event.wait(sleep_time)
        sleep_time = last_config_save_time - time.monotonic() + 5

    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_obj.__dict__, f)
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
        self.custom_selected_names = [""] * 2
        self.custom_selected_displayname = [""] * 2
        self.custom_selected_names_tech = [""] * 6
        self.full_custom_template = "p Hello world"


# ==================== LCD 屏幕分辨率检测 ====================

def Detect_LCD_Size():
    """自动检测小屏幕尺寸（尝试从设备SFR读取LCD分辨率）"""
    global LCD_MAX_X, LCD_MAX_Y

    lcd_w_names = [b'Lcd_X', b'LCD_X', b'LCD_W', b'MSN_LCD_W', b'LCD_Width',
                   b'LCD_X_Max', b'LCD_Max_X', b'LCD_Size_X', b'LCD_Pixel_X', b'LCD_Col']
    lcd_h_names = [b'Lcd_Y', b'LCD_Y', b'LCD_H', b'MSN_LCD_H', b'LCD_Height',
                   b'LCD_Y_Max', b'LCD_Max_Y', b'LCD_Size_Y', b'LCD_Pixel_Y', b'LCD_Row']

    detected_w = 0
    detected_h = 0

    print('--- 开始自动检测LCD屏幕分辨率 ---')

    # 先打印所有可用的MSN数据名称，并建立名称→条目映射
    name_map = {}
    try:
        data_names = [d.name.decode('utf-8', errors='replace') for d in My_MSN_Data]
        print('设备SFR数据名称列表: ' + str(data_names))
        for d in My_MSN_Data:
            name_map[bytes(d.name)] = d  # bytearray不可哈希，转为bytes
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
        try:
            my_device = My_MSN_Device
        except NameError:
            my_device = None
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
    global State_change
    State_change = 1


def Set_LCD_Size_Manual(*args):
    """手动设置LCD分辨率"""
    global LCD_MAX_X, LCD_MAX_Y, State_change, lcd_size_var
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
        State_change = 1
        msg = '手动设置屏幕分辨率: ' + str(LCD_MAX_X) + 'x' + str(LCD_MAX_Y)
        print(msg)
        insert_text_message(msg)


def Cleanup_LCD_On_Exit():
    """程序退出前清理LCD屏幕，避免残留花屏"""
    global Device_State, LCD_MAX_X, LCD_MAX_Y
    try:
        if Device_State == 1:
            print('正在清除LCD屏幕...')
            LCD_Color_set(0, 0, LCD_MAX_X, LCD_MAX_Y, BLACK)
            time.sleep(0.1)
            print('LCD屏幕已清除')
    except:
        pass


# ==================== UI 界面 ====================

def UI_Page():  # 进行图像界面显示
    global config_obj, Text1, interval_var, all_windows, all_cameras, windows_combobox
    global State_change, Label1, Label3, Label4, Label5, Label6, PAGE_ID

    config_obj = load_config()
    pad_scale_xy = scale_factor / 100.0
    pad_scale_xy5 = pad_scale_xy * 5

    # 创建主窗口
    window = tk.Tk()  # 实例化主窗口
    # window.tk.call('tk', 'scaling', pad_scale_xy)
    window.title(f"{PROGRAM_TITLE} v{PROGRAM_VERSION} - {PROGRAM_SUBTITLE} - {PROGRAM_GITHUB}")  # 设置标题

    # 修改默认图标
    if scale_factor < 200:
        iconimage = MiniMark.load_image("resource/icon_small.ico")
    else:
        iconimage = MiniMark.load_image("resource/icon.ico")
    defaulticon = ImageTk.PhotoImage(iconimage)
    window.wm_iconphoto(True, defaulticon)

    # 创建标签页容器（Notebook）
    notebook = ttk.Notebook(window)
    notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=pad_scale_xy5 * 2, pady=pad_scale_xy5 * 2)

    # ==================== 第一页：主控 ====================
    # 创建 Frame 容器
    root = tk.Frame(notebook, padx=pad_scale_xy5, pady=pad_scale_xy5, highlightthickness=1,
                    highlightcolor="lightgray", highlightbackground="lightgray")
    notebook.add(root, text="  主控  ")

    # ==================== 设置标签页 ====================
    settings_frame = ttk.Frame(notebook, padding=(pad_scale_xy5 * 3, pad_scale_xy5 * 3))
    notebook.add(settings_frame, text="  设置  ")

    # --- 防烧屏 ---

    def change_anti_burn(*args):
        global config_obj
        config_obj.anti_burn = anti_burn_var.get()
        if config_obj.anti_burn == 0:
            global burn_offset_x, burn_offset_y
            burn_offset_x = 0
            burn_offset_y = 0
        save_config()

    anti_burn_var = tk.IntVar(settings_frame, 0)
    anti_burn_var.set(config_obj.anti_burn)
    anti_burn_cb = ttk.Checkbutton(
        settings_frame, text="防烧屏（每30秒微调像素位置，延缓OLED烧屏）", variable=anti_burn_var,
        command=change_anti_burn
    )
    anti_burn_cb.pack(anchor=tk.W, pady=pad_scale_xy5)

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

    # 这两个线程尽早启动
    daemon_thread.start()
    load_thread.start()

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

        type_list = ["1. CPU", "2. GPU", "3. 内存"]
        row = 6  # 设置自定义项目数
        for row1 in range(row):
            if row1 >= len(config_obj.custom_selected_names_tech):
                config_obj.custom_selected_names_tech = config_obj.custom_selected_names_tech + [""]
                save_config()
            if row1 < len(type_list):
                rowtype = type_list[row1]
            else:
                rowtype = "%d." % (row1 + 1)

            sensor_label = tk.Label(tech_frame, text=rowtype, width=8, anchor=tk.W)
            sensor_label.grid(row=row1 + 2, column=0, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

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

        # 创建自定义内容输入框
        row += 1
        text_frame = ttk.Frame(tech_frame, padding="5")
        text_frame.grid(row=row, column=0, columnspan=2, sticky=tk.NSEW, padx=pad_scale_xy5, pady=0)

        def update_global_canvas():
            im = get_full_custom_im()
            im = im.resize((SHOW_WIDTH * scale_factor // 100, SHOW_HEIGHT * scale_factor // 100),
                           Image.Resampling.LANCZOS)
            tk_im = ImageTk.PhotoImage(im)
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_im)
            canvas.image = tk_im

        def update_global_text(event=None):
            global config_obj
            # Get the current content of the text area and update the global variable
            full_custom_template_tmp = event.widget.get("1.0", tk.END).rstrip('\n')  # tk.END会多一个换行
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
        global config_obj, color_use, State_change
        if Label2:
            color_La = "#{:02x}{:02x}{:02x}".format(r1, g1, b1)
            Label2.config(bg=color_La)
        # color_use = rgb888_to_rgb565(np.asarray((((r1, g1, b1),),), dtype=np.uint32))[0][0]
        color_use = ((r1 & 0xF8) << 8) | ((g1 & 0xFC) << 3) | ((b1 & 0xF8) >> 3)
        save_config()
        if config_obj.state_machine in [PCTIME_PAGE_ID, STATE_PAGE_ID]:
            State_change = 1

    def update_label_color_red():
        global config_obj
        config_obj.text_color_r = int(text_color_red_scale.get())
        update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    def update_label_color_green():
        global config_obj
        config_obj.text_color_g = int(text_color_green_scale.get())
        update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    def update_label_color_blue():
        global config_obj
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
        global config_obj, all_cameras, State_change, sleep_event, screen_shot_queue, screen_process_queue
        event.widget.selection_clear()
        camera_id = event.widget.get()
        if camera_id != config_obj.camera_var:
            config_obj.camera_var = camera_id
            if config_obj.state_machine == CAMERA_VIDEO_ID:
                # screenshot_panic()  # 重启截图线程。这是标准流程，但是多耗资源，改为如下只清空队列
                clear_queue(screen_shot_queue)  # 清空缓存，防止显示旧的窗口
                clear_queue(screen_process_queue)  # 清空缓存，防止显示旧的窗口
                state_change_set()
            else:
                save_config()

    label_camera_number = ttk.Label(root, text="相机名称")
    label_camera_number.grid(row=6, column=4, sticky=tk.NSEW, padx=pad_scale_xy5, pady=pad_scale_xy5)

    all_cameras = get_all_cameras()
    if len(all_cameras) > 1:
        PAGE_ID[CAMERA_VIDEO_ID] = "相机视频"
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
        desc = get_hwnd_desc(config_obj.select_window_hwnd)
        if desc:
            event.widget.set(desc)
        event.widget["value"] = sorted(all_windows.keys(), key=str.lower)
        combo_configure(event)

    def update_select_hwnd(event):
        global config_obj, all_windows, State_change, sleep_event, screen_shot_queue, screen_process_queue
        event.widget.selection_clear()
        select_str = event.widget.get()
        select_window_hwnd, _ = all_windows.get(select_str)
        if select_window_hwnd != config_obj.select_window_hwnd:
            config_obj.select_window_hwnd = select_window_hwnd
            if config_obj.state_machine == SCREEN_PAGE_ID:
                # screenshot_panic()  # 重启截图线程。这是标准流程，但是多耗资源，改为如下只清空队列
                clear_queue(screen_shot_queue)  # 清空缓存，防止显示旧的窗口
                clear_queue(screen_process_queue)  # 清空缓存，防止显示旧的窗口
                state_change_set()
            else:
                save_config()

    label = ttk.Label(root, text="屏幕镜像窗口:")
    label.grid(row=7, column=2, columnspan=1, sticky=tk.E, padx=pad_scale_xy5, pady=pad_scale_xy5)

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

    # 参数全部获取后再启动截图线程
    screen_shot_thread.start()
    screen_process_thread.start()
    manager_thread.start()

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
    global ser, Label1, Device_State, Device_State_Labelen
    if Device_State != state:
        Device_State = state
        if Device_State == 0:
            ser.close()  # 先将异常的串口连接关闭，防止无法打开
    if Device_State_Labelen == 2:
        Device_State_Labelen = 0
    if Device_State_Labelen == 0:
        try:
            if Device_State == 1:
                Label1.config(text="设备已连接", fg="white", bg="green")
            else:
                Label1.config(text="设备未连接", fg="white", bg="red")
        except Exception as e:
            Device_State_Labelen = 2
    elif Device_State_Labelen == 1:
        Device_State_Labelen = 3


def Get_MSN_Device(port_list):  # 尝试获取MSN设备
    global config_file, config_obj, ADC_det, ser, State_change, LCD_Change_now, My_MSN_Device, My_MSN_Data
    if ser is not None and ser.is_open:
        ser.close()  # 先将异常的串口连接关闭，防止无法打开

    # 对串口进行监听，确保其为MSN设备
    My_MSN_Device = None
    My_MSN_Data = None
    for port in port_list:
        try:  # 尝试打开串口
            # 初始化串口连接,初始使用
            ser = serial.Serial(port.device, 115200, timeout=5.0, write_timeout=5.0, inter_byte_timeout=0.1)
            recv = SER_Read()
            if recv == 0:
                print("未接收到设备响应，打开失败：%s" % port.device)
                ser.close()  # 将串口关闭，防止下次无法打开
                continue  # 尝试下一个端口
        except Exception as e:  # 出现异常
            print("%s 无法打开，请检查是否被其他程序占用: %s" % (port.device, e))
            if ser is not None and ser.is_open:
                ser.close()  # 将串口关闭，防止下次无法打开
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
                    GIF_PAGE_ID: "动图",
                    PCTIME_PAGE_ID: "时间",
                    PHOTO_PAGE_ID: "单个相册图片",
                    SCREEN_PAGE_ID: "屏幕镜像",
                    CAMERA_VIDEO_ID: "相机视频",
                    STATE_PAGE_ID: "电脑CPU/内存/磁盘/电池使用率监控",
                    NETSPEED_PAGE_ID: "网络流量监控",
                    CUSTOM1_PAGE_ID: "自定义显示两项图表",
                    CUSTOM2_PAGE_ID: "自定义显示多项数值",
                    ABOUT_PAGE_ID: "关于",
                }
                if config_obj.state_machine < len(PAGE_ID_tmp):
                    page_index = config_obj.state_machine
                else:
                    page_index = 0

                # 对MSN设备进行登记
                My_MSN_Device = MSN_Device(port.device, msn_version)
                print(get_formatted_time_string(datetime.now()), end=' ')
                if port.location is None:
                    insert_text_message("连接成功：%s\n当前页面：%s\n显示方向：%s\n配置文件：%s" % (
                        port.device, PAGE_ID_tmp[page_index], LCD_STATE_MESSAGE[config_obj.lcd_change], config_file))
                else:
                    insert_text_message("连接成功：%s@%s\n当前页面：%s\n显示方向：%s\n配置文件：%s" % (
                        port.device, port.location, PAGE_ID_tmp[page_index], LCD_STATE_MESSAGE[config_obj.lcd_change],
                        config_file))
                break  # 退出当前for循环
            else:
                print("设备无法连接，请检查连接是否正常：%s" % recv)

        if My_MSN_Device is None:
            print("设备校验失败：%s" % port.device)
            ser.close()  # 将串口关闭，防止下次无法打开
        else:
            break  # 连接成功即退出循环

    if My_MSN_Device is None:  # 没有找到可用的设备
        return

    ser.reset_input_buffer()
    ser.reset_output_buffer()
    My_MSN_Data = Read_M_SFR_Data(256)  # 读取u8在0x0100之后的128字节
    Print_MSN_Data(My_MSN_Data)  # 解析字节中的数据格式
    # Read_MSN_Data(My_MSN_Data)  # 从设备读取更详细的数据，如序列号等
    LCD_Change_now = config_obj.lcd_change
    LCD_State(LCD_Change_now)  # 配置显示方向
    State_change = 1  # 状态发生变化
    set_device_state(1)  # 可以正常连接
    # 自动检测LCD屏幕分辨率
    Detect_LCD_Size()
    # 配置按键阈值
    ADC_det = (Read_ADC_CH(9) + Read_ADC_CH(9) + Read_ADC_CH(9)) // 3
    ADC_det = ADC_det - 250  # 根据125的阈值判断是否被按下


def MSN_Device_1_State_machine():  # MSN设备1的循环状态机
    global config_obj, State_change, LCD_Change_now, Label3
    global write_path_index, Img_data_use, color_use

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

    if LCD_Change_now != config_obj.lcd_change:  # 显示方向与设置不符合
        LCD_Change_now = config_obj.lcd_change
        LCD_State(LCD_Change_now)  # 配置显示方向

    if config_obj.state_machine == PCTIME_PAGE_ID:
        show_PC_time(color_use)  # 展示时钟
    elif config_obj.state_machine == PHOTO_PAGE_ID:
        show_Photo()  # 展示单张相册图像
    elif config_obj.state_machine == SCREEN_PAGE_ID or config_obj.state_machine == CAMERA_VIDEO_ID:
        show_PC_Screen()  # 屏幕串流 和 相机视频
    elif config_obj.state_machine == STATE_PAGE_ID:
        show_PC_state(color_use, BLACK)  # 展示CPU/内存/磁盘/电池 使用率
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
        show_about()  # 显示关于页面
    else:  # default GIF_PAGE_ID
        show_gif()  # 展示36张动图


def show_about():
    """在LCD屏幕上显示关于信息"""
    global config_obj, State_change, sleep_event
    if State_change == 1:
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
    rgb565 = rgb888_to_rgb565(rgb888)
    hex_use = Screen_Date_Process(rgb565.flatten())
    SER_rw(hex_use, read=False)

    sleep_event.wait(3)  # 静态页面，3秒刷新一次即可


def get_formatted_time_string(time):
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load_task():
    global hardware_monitor_manager, PAGE_ID
    try:
        HardwareMonitorManager = load_hardware_monitor()
        hardware_monitor_manager = HardwareMonitorManager()
        PAGE_ID[CUSTOM1_PAGE_ID] = "自定义显示两项图表"
        PAGE_ID[CUSTOM2_PAGE_ID] = "自定义显示多项数值"
        print("Libre hardware monitor load successed")
    except Exception as e:
        hardware_monitor_manager = 1
        print("Libre hardware monitor 加载失败，%s" % traceback.format_exc())


def daemon_task():
    global Device_State, Device_State_Labelen, sleep_event

    wch_port_list_old = None
    retry_times = 0
    print("Start daemon")
    while MG_daemon_running:
        try:
            if Device_State_Labelen == 2:
                set_device_state(Device_State)

            if Device_State == 1:  # 已检测到设备
                MSN_Device_1_State_machine()
                continue

            # 尝试获取MSN设备
            port_list = list(serial.tools.list_ports.comports())  # 查询所有串口
            # geezmo: 如果有 VID = 0x1a86 （沁恒）的，优先考虑这些设备，防止访问其他串口出错
            # 如果没有这些设备，或者 pyserial 没有提供信息，则不管
            wch_port_list = [x for x in port_list if x.vid == 0x1a86]

            if wch_port_list != wch_port_list_old:
                wch_port_list_old = wch_port_list
                retry_times = 0
            else:
                retry_times += 1
                if retry_times >= 5:
                    if sleep_event.isSet():
                        sleep_event.clear()
                    sleep_event.wait(1)  # 防止频繁重试
                    if (retry_times % 5) != 0:  # 减缓重试频率，5秒重试一次
                        continue

            Get_MSN_Device(wch_port_list)
            if Device_State != 0:
                retry_times = 0
                continue
            # 这儿去掉对VID非0x1a86的检测，因为很多反馈对蓝牙有影响
            # not_wch_port_list = [x for x in port_list if x.vid != 0x1a86]
            # Get_MSN_Device(not_wch_port_list)
            # if Device_State != 0:
            #     continue
            print(get_formatted_time_string(datetime.now()), end=' ')
            insert_text_message("没有找到可用的设备，请确认设备是否正确连接")
            if sleep_event.isSet():
                sleep_event.clear()
            sleep_event.wait(0.2)  # 防止频繁重试
        except Exception as e:  # 出现非预期异常
            print("Exception in daemon_task, %s" % traceback.format_exc())
            if sleep_event.isSet():
                sleep_event.clear()
            sleep_event.wait(1)  # 防止频繁重试

    # stop
    print("Stop daemon")


# 检测按键是否被按下，兼具心跳功能
# 单击：下一页
# 双击：上一页
# 长按：切换方向
def manage_task():
    global ADC_det
    now = time.monotonic()
    key_on = 0  # 按键是否按下
    check_limit = 2.0  # 持续检测阈值
    key_on_limit = 0.5  # 长按阈值
    double_key_limit = 0.7  # 双击间隔时长，同时影响单击反应时间
    last_check_time = now - check_limit
    first_press_time = 0  # 按下起始时间，未按下0，按下且已触发事件1
    print("Start manager")
    while MG_daemon_running:
        if Device_State == 0:
            time.sleep(0.3)
            continue

        try:
            now = time.monotonic()
            ADC_ch = Read_ADC_CH(9)
            if ADC_ch == 0:
                continue
            if ADC_ch < ADC_det:  # 按键按下
                if Read_ADC_CH(9) > ADC_det or Read_ADC_CH(9) > ADC_det:
                    continue  # 没有连续3次则忽略

                if ADC_det - ADC_ch > 900:  # 阈值过大，校正检测阈值
                    ADC_det = ADC_ch - 250
                    print("校正按下检测阈值为：%d" % ADC_det)
                    continue

                if key_on == 0:  # 第一次检测到按下
                    ADC_det += 150  # 增加后续检测的灵敏度
                    key_on = 1
                    if first_press_time != 0:
                        if now - first_press_time < double_key_limit:
                            Page_Down()  # 双击上一页
                            first_press_time = 1  # 已触发事件
                    else:  # 第一次按下
                        first_press_time = now
                else:
                    if first_press_time != 1:
                        if first_press_time != 0:
                            if now - first_press_time > key_on_limit:
                                LCD_Change()  # 长按切换方向
                                first_press_time = 1  # 已触发事件
                        else:
                            first_press_time = now
            else:  # 按键放开
                if key_on != 0:  # 第一次检测到放开
                    if Read_ADC_CH(9) < ADC_det or Read_ADC_CH(9) < ADC_det:
                        continue  # 没有连续3次则忽略
                    ADC_det -= 150  # 恢复检测的灵敏度
                    key_on = 0
                    last_check_time = now  # 从第一次检测到放开1秒后再减缓频率
                    if first_press_time == 1:
                        first_press_time = 0
                elif now - last_check_time > check_limit:
                    if ADC_ch - ADC_det > 40 + 250:  # 阈值过小，校正检测阈值
                        ADC_det = (ADC_det + ADC_ch - 250) // 2
                        print("校正按键检测阈值为：%d" % ADC_det)
                    time.sleep(0.1)  # 没有按键时减缓读取频率
                else:
                    if first_press_time != 0:
                        if now - first_press_time > double_key_limit:  # 没有双击，就是单击
                            Page_UP()  # 单击下一页
                            first_press_time = 0
        except Exception as e:
            print("Exception in manage_task, %s" % traceback.format_exc())

    print("Stop manager")


Img_data_use = None

cleanNextTime = False

sleep_event = None  # 用event代替time.sleep，加快切换速度
SER_lock = None

last_refresh_time = 0
gif_wait_time = 0.0
second_pass = 0

screen_shot_queue = None
screen_process_queue = None
desktop_hwnd = 0
all_windows = None
all_cameras = None

row_np_zero = None
column_np_zero = None

screenshot_test_time = 0  # 用于计算串流FPS
screenshot_test_frame = 1  # 用于计算串流FPS。初始值为1，这样开始就不会马上打印不准确的FPS值
screenshot_last_limit_time = 0
wait_time = 0.0

netspeed_last_refresh_snetio = None
netspeed_plot_data = None  # 用于 show_netspeed

custom_plot_data = None  # 用于 show_custom_two_rows

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

State_change = 1  # 状态发生变化
gif_num = 0
Device_State = 0  # 初始为未连接
Device_State_Labelen = 0  # 0无修改，1窗口已隐藏，2窗口已恢复有修改，3窗口已隐藏有修改
LCD_Change_now = 0  # 实际显示方向
color_use = RED  # 彩色图片点阵算法 5R6G5B
write_path_index = 0

# 曲线图颜色和背景颜色
back_color = (0, 0, 0)
bar_colors = [(235, 139, 139), (146, 212, 217)]
# bar_colors = [(128, 255, 128), (255, 128, 255)]
# bar_colors = [(128, 128, 255), (0, 128, 192)]

Label1 = None  # 设备状态显示框
Label3 = None  # 背景图像路径显示框
Label4 = None  # 闪存固件路径显示框
Label5 = None  # 相册图像路径显示框
Label6 = None  # 动图文件路径显示框
Text1 = None  # 信息显示文本框
windows_combobox = None
interval_var = None
lcd_size_var = None
ser = None  # 设备连接句柄
ADC_det = 0  # 按键阈值
sub_window = None  # 子窗口，设置为全局变量用于重新打开时不需要重复创建
hardware_monitor_manager = None
My_MSN_Device = None  # 当前连接的MSN设备信息
My_MSN_Data = None     # 当前设备的SFR数据描述表
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
        last_refresh_time = time.monotonic()
        screenshot_test_time = last_refresh_time
        screenshot_last_limit_time = last_refresh_time
        sleep_event = threading.Event()  # 用event代替time.sleep，加快切换速度
        config_event = threading.Event()  # 用event代替time.sleep，用于退出时快速保存
        SER_lock = threading.Lock()
        screen_shot_queue = queue.Queue(2)
        screen_process_queue = queue.Queue(2)

        config_file = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), config_file))
        config_obj = sys_config()
        mini_mark_parser = MiniMarkParser()
        default_font = MiniMark.load_font("./simhei.ttf", netspeed_font_size)
        netspeed_font = MiniMark.load_font("resource/Orbitron-Bold.ttf", netspeed_font_size - 4)

        row_np_zero = np.zeros([1, LCD_MAX_X, 3], dtype=np.uint8)
        column_np_zero = np.zeros([LCD_MAX_Y, 1, 3], dtype=np.uint8)

        netspeed_plot_data = {"sent": [0] * (LCD_MAX_X // 2), "recv": [0] * (LCD_MAX_X // 2)}
        custom_plot_data = {"sent": [0] * (LCD_MAX_X // 2), "recv": [0] * (LCD_MAX_X // 2)}

        MG_daemon_running = True
        MG_screen_thread_running = True
        daemon_thread = threading.Thread(target=daemon_task, daemon=True)
        load_thread = threading.Thread(target=load_task, daemon=True)
        manager_thread = threading.Thread(target=manage_task, daemon=True)
        screen_shot_thread = threading.Thread(target=screen_shot_task, daemon=True)
        screen_process_thread = threading.Thread(target=screen_process_task, daemon=True)

        # 打开主页面
        UI_Page()
    except Exception as e:
        exit_code = 1
        message = "Error: %s" % traceback.format_exc()
        print(message)
        tk.messagebox.showerror(title="错误", message=message)
    finally:
        MG_screen_thread_running = False
        MG_daemon_running = False
        sleep_event.set()  # 取消sleep, 使sleep_event.wait无效
        # 退出前清理LCD屏幕，避免残留花屏
        Cleanup_LCD_On_Exit()
        if ser is not None and ser.is_open:
            print("%s close" % ser.name)
            ser.close()  # 正常关闭串口。串口先于线程关闭，可能会出现访问串口异常，不过能够加快整体关闭速度
        # 结束时保存配置
        save_config(True)
        if load_thread.is_alive():
            load_thread.join(timeout=5.0)
        if manager_thread.is_alive():
            manager_thread.join(timeout=5.0)
        if screen_process_thread.is_alive():
            screen_process_thread.join(timeout=5.0)
        if screen_shot_thread.is_alive():
            screen_shot_thread.join(timeout=5.0)
        if daemon_thread.is_alive():
            daemon_thread.join(timeout=5.0)

        sys.exit(exit_code)

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

import numpy as np  # 使用numpy加速数据处理
import psutil  # 引入psutil获取设备信息（需要额外安装）
import pystray
import serial  # 引入串口库（需要额外安装）
import serial.tools.list_ports
from PIL import Image, ImageDraw, ImageTk  # 引入PIL库进行图像处理

import MSU2_MINI_MG_minimark as MiniMark
from MSU2_MINI_MG_minimark import MiniMarkParser

isWindows = True if os.name == "nt" else False

if isWindows:
    from ctypes import windll
    import win32con
    import win32gui
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
        system_dpi = windll.user32.GetDpiForSystem()
    except:
        system_dpi = 1

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
    except:
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

SHOW_WIDTH = 160  # 画布宽度
SHOW_HEIGHT = 80  # 画布高度

GIF_PAGE_ID = 0
PCTIME_PAGE_ID = 1
PHOTO_PAGE_ID = 2
SCREEN_PAGE_ID = 3
STATE_PAGE_ID = 4
NETSPEED_PAGE_ID = 5
CUSTOM1_PAGE_ID = 6
CUSTOM2_PAGE_ID = 7
PAGE_DESSCRIPTION = [
    "页面1：动图",  # GIF_PAGE_ID = 0
    "页面2：时间",  # PCTIME_PAGE_ID = 1
    "页面3：单个相册图片",  # PHOTO_PAGE_ID = 2
    "页面4：屏幕镜像",  # SCREEN_PAGE_ID = 3
    "页面5：电脑CPU/内存/磁盘/电池使用率监控",  # STATE_PAGE_ID = 4
    "页面6：网络流量监控",  # NETSPEED_PAGE_ID = 5
]

LCD_STATE_MESSAGE = [
    "正向",
    "反向"
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
    ("Image file", "*.dib")
]


def get_all_windows():
    global desktop_hwnd

    def children(hwnd, parent_hwnd, param):
        window_class = win32gui.GetClassName(hwnd)
        window_title = win32gui.GetWindowText(hwnd)
        if window_class == "TrayClockWClass":  # 系统时钟
            # or window_title == "Game Bar":  # Xbox Game Bar
            param["%s - %s" % (hwnd, window_title)] = (hwnd, parent_hwnd)
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
            if window_title and window_class != "Windows.UI.Core.CoreWindow":  # 普通窗口
                # and window_class != "Internet Explorer_Hidden"
                parent = win32gui.GetParent(hwnd)
                hwnd_title["%s - %s" % (hwnd, window_title)] = (hwnd, parent)
            elif window_class == "Shell_TrayWnd":  # 任务栏
                hwnd_title.update(get_children_windows(hwnd, 0))
        return True

    hwnd_titles = dict()
    try:
        # 添加桌面
        desktop_hwnd = win32gui.GetDesktopWindow()
        hwnd_titles.update({"%s - 桌面" % desktop_hwnd: (desktop_hwnd, 0)})

        # 遍历其他所有窗口
        win32gui.EnumWindows(get_all_hwnd, hwnd_titles)

        # 添加特殊窗口
        # hwnd_titles.update(get_children_windows(desktop_hwnd, desktop_hwnd))
    except Exception as e:
        print(e)
        hwnd_titles = {"": (0, 0)}

    return hwnd_titles


class Win32_Image:
    def __init__(self, bgra, size):
        self.bgra = bgra
        self.size = size


# 根据dpi获取窗口实际大小
def get_rect_by_dpi(rect, hWnd):
    app_dpi = windll.user32.GetDpiForWindow(hWnd)
    if app_dpi != system_dpi:
        dpi = app_dpi / system_dpi
        rect = [int(x * dpi) for x in rect]
    width = rect[2] - rect[0]
    height = rect[3] - rect[1]
    return rect[0], rect[1], width, height


def get_window_image(hWnd=None):
    global desktop_hwnd

    # if win32gui.IsIconic(hWnd):  # 判断窗口是否最小化
    #     print("最小化")
    #     return
    while not win32gui.IsWindow(hWnd):  # 只需要窗口在，不需要可见，比如最小化或者隐藏到任务栏
        hWnd = get_parent(hWnd)
        if hWnd == 0:
            hWnd = desktop_hwnd
        set_select_hwnd(hWnd)
    # 将窗口置于最前端
    # win32gui.SetForegroundWindow(hWnd)

    # 初始化截屏所需内存
    hWndDC = win32gui.GetWindowDC(hWnd)
    mfcDC = win32ui.CreateDCFromHandle(hWndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()

    try:
        # # 获取窗口大小，包含标题栏和工具栏
        # get_rect = win32gui.GetWindowRect(hWnd)
        # print_mode = 0b10
        # 获取窗口大小，不包含标题栏和工具栏
        get_rect = win32gui.GetClientRect(hWnd)
        print_mode = 0b11

        if hWnd == desktop_hwnd:  # PrintWindow不能截取桌面，需要用BitBlt
            # 获取窗口长宽
            width = get_rect[2] - get_rect[0]
            height = get_rect[3] - get_rect[1]

            # 使用win32gui截屏
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)

            # 保存bitmap到内存设备描述表。win32con.NOTSRCCOPY 翻转颜色
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (get_rect[0], get_rect[1]), win32con.SRCCOPY)
        else:
            # 获取窗口实际大小
            get_rect = get_rect_by_dpi(get_rect, hWnd)

            # 使用win32gui截屏
            saveBitMap.CreateCompatibleBitmap(mfcDC, get_rect[2], get_rect[3])
            saveDC.SelectObject(saveBitMap)

            # 后台窗口使用PrintWindow代替BitBlt解决部分窗口黑屏问题, 但是PrintWindow不能截取桌面
            result = windll.user32.PrintWindow(hWnd, saveDC.GetSafeHdc(), print_mode)
            # if not result:
            #     print("PrintWindow failed: %s" % result)
            #     return Win32_Image(bytes(8), (2, 1))  # 异常时初始化为黑色背景

        # 获取位图信息
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        # # 生成图像
        # im_PIL = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        #                           bmpstr, 'raw', 'BGRX', 0, 1)
        # im_PIL = Image.frombuffer('RGB', (len(bmpstr) // (bmpinfo['bmHeight'] * 4), bmpinfo['bmHeight']),
        #                           bmpstr, 'raw', 'BGRX', 0, 1)
        # im_PIL.save("im_PIL.png")  # 保存
        image = Win32_Image(bmpstr, (bmpinfo['bmWidth'], bmpinfo['bmHeight']))
        return image
    except Exception as e:
        print(traceback.format_exc())
        time.sleep(0.2)
        return Win32_Image(bytes(8), (2, 1))  # 异常时初始化为黑色背景
    finally:
        # 内存释放
        try:
            win32gui.DeleteObject(saveBitMap.GetHandle())
        except:
            pass
        try:
            saveDC.DeleteDC()
        except:
            pass
        try:
            mfcDC.DeleteDC()
        except:
            pass
        try:
            win32gui.ReleaseDC(hWnd, hWndDC)
        except:
            pass


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
    if image.mode != "RGB":
        image = image.convert("RGB")  # 转换为RGB格式。虽然转换再缩放会降低效率，但是能够提升缩小后的图片质量
    if image.width > (image.height * 2):  # 图片长宽比例超过2:1
        im2 = image.resize((SHOW_HEIGHT * image.width // image.height, SHOW_HEIGHT))
        # 定义需要裁剪的空间
        box = ((im2.width - SHOW_WIDTH) // 2, 0, (im2.width + SHOW_WIDTH) // 2, SHOW_HEIGHT)
        im2 = im2.crop(box)
    else:
        im2 = image.resize((SHOW_WIDTH, SHOW_WIDTH * image.height // image.width))
        # 定义需要裁剪的空间
        box = (0, (im2.height - SHOW_HEIGHT) // 2, SHOW_WIDTH, (im2.height + SHOW_HEIGHT) // 2)
        im2 = im2.crop(box)

    # im2 = im2.convert("RGB")  # 转换为RGB格式
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
            title="选择文件", filetypes=IMAGE_FILE_TYPES + [("Image file", "*.gif")])
        insert_text_message(photo_path, item=Label3)
    elif index == 2:
        photo_path = tk.filedialog.askopenfilename(
            title="选择文件", filetypes=[("Bin file", "*.bin")])
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
    global config_obj, Label3, write_path_index, Img_data_use, sleep_event
    photo_path = Label3.get("1.0", tk.END).rstrip()
    if not photo_path:
        insert_text_message("背景图像未选择")
        return

    insert_text_message("图像格式转换...", cleanNext=False)
    Img_data_use = convertImageFileToRGB(photo_path)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 1
    if config_obj.state_machine == PCTIME_PAGE_ID:
        state_change_set(save=False)


def Write_Photo_Path2():  # 写入文件
    global Label4, write_path_index, sleep_event
    photo_path = Label4.get("1.0", tk.END).rstrip()
    if not photo_path:
        insert_text_message("闪存固件未选择")
        return
    insert_text_message("准备烧写Flash固件...", cleanNext=False)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 2
    state_change_set(save=False)


def Write_Photo_Path3():  # 写入文件
    global config_obj, Label5, write_path_index, Img_data_use, sleep_event
    photo_path = Label5.get("1.0", tk.END).rstrip()
    if not photo_path:
        insert_text_message("相册图像未选择")
        return

    insert_text_message("图像格式转换...", cleanNext=False)
    Img_data_use = convertImageFileToRGB(photo_path)

    if write_path_index != 0:  # 确保上次执行写入完毕
        insert_text_message("有正在执行的任务%d，写入失败" % write_path_index)
        return
    write_path_index = 3
    if config_obj.state_machine == PHOTO_PAGE_ID:
        state_change_set(save=False)


def Write_Photo_Path4():  # 写入文件
    global config_obj, Label6, interval_var, write_path_index, Img_data_use, sleep_event
    photo_path = Label6.get("1.0", tk.END).rstrip()
    if not photo_path:
        insert_text_message("动图文件未选择")
        return

    Img_data_use = bytearray()
    insert_text_message("动图格式转换中...", cleanNext=False)
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
                converted = convertImageToRGB(gif)
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
    if config_obj.state_machine == GIF_PAGE_ID:
        state_change_set(save=False)


def state_change_set(message=None, save=True):
    global State_change, sleep_event
    State_change = 1
    sleep_event.set()  # 取消sleep, 使sleep_event.wait无效
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
    if config_obj.state_machine >= len(PAGE_DESSCRIPTION) - 1:
        config_obj.state_machine = 0
    else:
        config_obj.state_machine = config_obj.state_machine + 1
    state_change_set(PAGE_DESSCRIPTION[config_obj.state_machine])


def Page_Down():  # 下一页
    global config_obj, State_change, sleep_event
    if config_obj.state_machine <= 0:
        config_obj.state_machine = len(PAGE_DESSCRIPTION) - 1
    else:
        config_obj.state_machine = config_obj.state_machine - 1
    state_change_set(PAGE_DESSCRIPTION[config_obj.state_machine])


def LCD_Change():  # 切换显示方向
    global config_obj, Device_State, sleep_event
    if Device_State == 0:
        insert_text_message("设备未连接，切换失败")
        return
    config_obj.lcd_change ^= 1
    state_change_set(LCD_STATE_MESSAGE[config_obj.lcd_change])


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
    global ser

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
            i, My_MSN_Data[i].name.decode("gbk"), My_MSN_Data[i].unit, type_list[ord(My_MSN_Data[i].family) // 32],
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
        print("%-10s = %s" % (My_MSN_Data[i].name.decode("gbk"), use_data))


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

        insert_text_message("找到\"%s\"文件，大小%dB，烧录中..." % (filepath, Fsize), cleanNext=False)
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
    insert_text_message("大小%dB，烧录中..." % Fsize, cleanNext=False)
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


def LCD_ADD(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
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
    if len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
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
    if len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
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
    if len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
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
    if len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_GB2312_16X16_MIX failed: %s" % recv)
        set_device_state(0)  # 接收出错
        return 0


# 对指定区域进行颜色填充
def LCD_Color_set(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, F_Color):
    hex_use = LCD_Set_XY(LCD_X, LCD_Y)
    hex_use.extend(LCD_Set_Size(LCD_X_Size, LCD_Y_Size))
    hex_use.append(2)  # 对LCD多次写入
    hex_use.append(3)  # 设置指令
    hex_use.append(11)  # 显示彩色图片
    hex_use.append(F_Color // 256)
    hex_use.append(F_Color % 256)
    hex_use.append(0)

    recv = SER_rw(hex_use)  # 发出指令
    if len(recv) > 1 and recv[0] == hex_use[0] and recv[1] == hex_use[1]:
        return 1
    else:
        print("LCD_Color_set failed: %s" % recv)
        set_device_state(0)  # 接收出错
        return 0


def show_gif():  # 显示GIF动图
    global config_obj, second_pass, sleep_event
    global current_monoto_time, last_refresh_time, gif_wait_time, State_change, gif_num
    if State_change == 1:
        state_change_clear()
        # gif_num = 0
        gif_wait_time = 0
        last_refresh_time = current_monoto_time
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
    if gif_num > 35:
        gif_num = 0

    LCD_Photo(gif_num * 100)

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
    global State_change, sleep_event, last_refresh_time, wait_time, current_monoto_time
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
    if battery is not None:
        BAT = round(battery.percent)
    else:
        BAT = 100
    # 磁盘使用率
    disk_info = psutil.disk_usage("/")
    if disk_info.total == 0:
        FRQ = 100
    else:
        FRQ = round(disk_info.used * 100 / disk_info.total)

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
    global State_change, sleep_event
    photo_add = 3826
    num_add = 3651
    if State_change == 1:
        state_change_clear()
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)
        LCD_Photo(photo_add)  # 放置背景
        LCD_Set_Color(FC, photo_add)
        hex_use = LCD_ASCII_32X64_MIX(56 + 8, 0, ":", num_add)
        recv = SER_rw(hex_use)  # 发出指令
        if len(recv) == 0 or recv[0] != 2 or recv[1] != 3:
            print("show_PC_time failed: %s" % recv)
            set_device_state(0)
        # LCD_ASCII_32X64_MIX(136+8,32,":",FC,photo_add,num_add)

    hex_use = bytearray()
    current_time = datetime.now()

    time_h = int(current_time.hour)
    time_m = int(current_time.minute)
    time_S = int(current_time.second)
    hex_use.extend(LCD_ASCII_32X64_MIX(0 + 8, 8, chr((time_h // 10) + 48), num_add))
    hex_use.extend(LCD_ASCII_32X64_MIX(32 + 8, 8, chr((time_h % 10) + 48), num_add))
    hex_use.extend(LCD_ASCII_32X64_MIX(80 + 8, 8, chr((time_m // 10) + 48), num_add))
    hex_use.extend(LCD_ASCII_32X64_MIX(112 + 8, 8, chr((time_m % 10) + 48), num_add))
    # LCD_ASCII_32X64_MIX(160 + 8, 8, chr((time_S // 10) + 48), FC, photo_add, num_add)
    # LCD_ASCII_32X64_MIX(192 + 8, 8, chr((time_S % 10) + 48), FC, photo_add, num_add)

    recv = SER_rw(hex_use, size=6 * 4)  # 发出指令
    if len(recv) == 0 or recv[0] != 2 or recv[1] != 3:
        print("show_PC_time failed: %s" % recv)
        set_device_state(0)

    if time_S != 59:
        sleep_event.wait(1)  # 1秒刷新一次
    else:
        sleep_event.wait(1 - current_time.microsecond / 1000000.0)  # 分钟切换时


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
    global config_obj, MG_screen_thread_running, screen_shot_queue, desktop_hwnd
    if not isWindows:
        from mss import mss

        with mss() as sct:
            monitors = sct.monitors
            # cropped_monitor = {
            #     "left": screenshot_region[0] + monitor["left"],
            #     "top": screenshot_region[1] + monitor["top"],
            #     "width": screenshot_region[2] or monitor["width"],
            #     "height": screenshot_region[3] or monitor["height"],
            #     "mon": screenshot_monitor_id,
            # }
            # 序号为0的monitor是总体屏幕
            cropped_monitor = monitors[0]
            cropped_monitor["mon"] = 0

    while MG_screen_thread_running:
        if config_obj.state_machine != SCREEN_PAGE_ID:
            if not screen_shot_queue.empty():
                time.sleep(0.5)  # 等一下再清空，防止页面切换缓慢
                clear_queue(screen_shot_queue)  # 清空缓存，防止显示旧的窗口
            time.sleep(0.5)  # 不需要截图时
            continue
        if screen_shot_queue.full():
            time.sleep(1.0 / config_obj.fps_var)  # 队列满时暂停一个周期
            continue

        try:
            if isWindows:
                sct_img = get_window_image(config_obj.select_window_hwnd)
                screen_shot_queue.put((sct_img, {"width": sct_img.size[0], "height": sct_img.size[1]}), timeout=3)
            else:
                sct_img = sct.grab(cropped_monitor)  # geezmo: 截屏已优化
                screen_shot_queue.put((sct_img, cropped_monitor), timeout=1.0)
        except queue.Full:
            continue
        except Exception as e:
            print("截屏失败 %s" % traceback.format_exc())
            time.sleep(0.2)

    # stop
    print("Stop screenshot")


# geezmo: 流水线 第二步 处理图像
def screen_process_task():
    global config_obj, MG_screen_thread_running, screen_process_queue, screen_shot_queue
    while MG_screen_thread_running:
        if config_obj.state_machine != SCREEN_PAGE_ID:
            if not screen_process_queue.empty():
                time.sleep(0.5)  # 等一下再清空，防止页面切换缓慢
                clear_queue(screen_process_queue)  # 清空缓存，防止显示旧的窗口
            time.sleep(0.5)  # 不需要截图时
            continue
        if screen_process_queue.full():
            time.sleep(1.0 / config_obj.fps_var)  # 队列满时暂停一个周期
            continue

        try:
            sct_img, monitor = screen_shot_queue.get(timeout=1.0)
            bgra = sct_img.bgra
            remain = sct_img.size[1] * sct_img.size[0] * 4 - len(bgra)
            if remain >= 0:
                if remain > 0:
                    bgra += bytes(remain)
                # rgb = np.frombuffer(sct_img.rgb, dtype=np.uint8).reshape((sct_img.size[1], sct_img.size[0], 3))
                bgra = np.frombuffer(bgra, dtype=np.uint8).reshape((sct_img.size[1], sct_img.size[0], 4))
                # rgb = bgra[:, :, :3]
                # rgb = rgb[:, :, ::-1]
                rgb = bgra[:, :, [2, 1, 0]]
            else:  # 针对windows管理控制台框架的窗口，如服务管理
                bgra = np.frombuffer(bgra, dtype=np.uint8).reshape(
                    (sct_img.size[1], len(bgra) // (sct_img.size[1] * 4), 4))
                rgb = bgra[:, :sct_img.size[0], [2, 1, 0]]

            # 方法1：裁剪
            # if monitor["width"] > monitor["height"] * 2:  # 图片长宽比例超过2:1
            #     im1 = shrink_image_block_average(rgb, rgb.shape[0] / SHOW_HEIGHT)
            #     im1 = im1[:, 0: SHOW_WIDTH]
            # else:  # 纵向裁剪
            #     im1 = shrink_image_block_average(rgb, rgb.shape[1] / SHOW_WIDTH)
            #     im1 = im1[0: SHOW_HEIGHT, :]

            # 方法2：填充
            if monitor["width"] > monitor["height"] * 2:  # 图片长宽比例超过2:1
                im1 = shrink_image_block_average(rgb, rgb.shape[1] / SHOW_WIDTH)
                total = SHOW_HEIGHT - len(im1)
                np_fill_zero = row_np_zero.repeat(total // 2, axis=0)
                if total % 2:
                    im1 = np.row_stack((np_fill_zero, im1, np_fill_zero, row_np_zero))
                else:
                    im1 = np.row_stack((np_fill_zero, im1, np_fill_zero))
            else:  # 纵向充满
                im1 = shrink_image_block_average(rgb, rgb.shape[0] / SHOW_HEIGHT)
                if monitor["width"] != monitor["height"] * 2:
                    total = SHOW_WIDTH - len(im1[0])
                    np_fill_zero = column_np_zero.repeat(total // 2, axis=1)
                    if total % 2:
                        im1 = np.column_stack((np_fill_zero, im1, np_fill_zero, column_np_zero))
                    else:
                        im1 = np.column_stack((np_fill_zero, im1, np_fill_zero))

            # rgb888 = np.asarray(im1)
            rgb565 = rgb888_to_rgb565(im1)
            # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
            hexstream = Screen_Date_Process(rgb565.flatten())

            screen_process_queue.put(hexstream, timeout=1.0)
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
    if screen_shot_thread.is_alive():
        screen_shot_thread.join()
    if screen_process_thread.is_alive():
        screen_process_thread.join()

    if clean_queue:
        clear_queue(screen_shot_queue)  # 清空缓存，防止显示旧的窗口
        clear_queue(screen_process_queue)  # 清空缓存，防止显示旧的窗口

    MG_screen_thread_running = True
    screen_shot_thread = threading.Thread(target=screen_shot_task, daemon=True)
    screen_process_thread = threading.Thread(target=screen_process_task, daemon=True)
    screen_shot_thread.start()
    screen_process_thread.start()


def show_PC_Screen():  # 显示照片
    global config_obj, State_change, screenshot_test_frame, screen_process_queue
    global current_monoto_time, screenshot_test_time, screenshot_last_limit_time, wait_time, sleep_event
    if State_change == 1:
        state_change_clear()
        wait_time = 0
        screenshot_last_limit_time = current_monoto_time
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    try:
        hexstream = screen_process_queue.get(timeout=1.0)
    except queue.Empty:
        return
    SER_rw(hexstream, read=False)  # 发出指令

    elapse_time = current_monoto_time - screenshot_last_limit_time
    if elapse_time > 5:  # 有切换，重置参数
        wait_time = 0
        screenshot_test_time = current_monoto_time
        screenshot_test_frame = 0
        elapse_time = 1.0 / config_obj.fps_var  # 第一次不需要wait
    elif screenshot_test_frame % config_obj.fps_var == 0:
        # 测试用：显示帧率
        # real_fps = config_obj.fps_var / (current_monoto_time - screenshot_test_time)
        # print("串流FPS: %s" % real_fps)
        screenshot_test_time = current_monoto_time
    screenshot_last_limit_time = current_monoto_time
    screenshot_test_frame += 1
    wait_time += 1.0 / config_obj.fps_var - elapse_time
    if wait_time > 0:
        sleep_event.wait(wait_time)  # 精确控制FPS


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


def show_netspeed(text_color=(255, 128, 0), bar1_color=(235, 139, 139), bar2_color=(146, 211, 217)):
    global last_refresh_time, netspeed_last_refresh_snetio, netspeed_plot_data
    global default_font, State_change, wait_time, current_monoto_time, sleep_event

    bar_width = 2  # 每个点宽度
    image_height = SHOW_HEIGHT // 4  # 高度

    current_snetio = psutil.net_io_counters()
    # geezmo: 预渲染图片，显示网速
    if State_change == 1:
        state_change_clear()
        wait_time = 0
        last_refresh_time = current_monoto_time - 0.001
        netspeed_last_refresh_snetio = current_snetio
        LCD_ADD(0, 0, SHOW_WIDTH, SHOW_HEIGHT)

    # 获取网速 bytes/second
    seconds_elapsed = current_monoto_time - last_refresh_time

    # 因为刷新间隔刚好是1秒，所以不需要除时间
    sent_per_second = (current_snetio.bytes_sent - netspeed_last_refresh_snetio.bytes_sent) / seconds_elapsed
    netspeed_plot_data["sent"].pop(0)
    netspeed_plot_data["sent"].append(sent_per_second)
    recv_per_second = (current_snetio.bytes_recv - netspeed_last_refresh_snetio.bytes_recv) / seconds_elapsed
    netspeed_plot_data["recv"].pop(0)
    netspeed_plot_data["recv"].append(recv_per_second)

    last_refresh_time = current_monoto_time
    netspeed_last_refresh_snetio = current_snetio

    # 绘制图片
    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))
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

        x0 = -bar_width
        x1 = -1
        y1 = image_height + start_y
        percent = image_height / max_value
        for i, sent in enumerate(sent_values[-(SHOW_WIDTH // bar_width):]):
            # Scale the sent value to the image height
            bar_height = percent * sent
            x0 += bar_width
            x1 += bar_width
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


def show_custom_two_rows(text_color=(255, 128, 0), bar1_color=(235, 139, 139), bar2_color=(146, 211, 217)):
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global config_obj, last_refresh_time, State_change, wait_time, current_monoto_time
    global custom_plot_data, hardware_monitor_manager, netspeed_font, sleep_event

    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        sleep_event.wait(0.2)
        return

    bar_width = 2  # 每个点宽度
    image_height = SHOW_HEIGHT // 4  # 高度

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

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (0, 0, 0))

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

        x0 = -bar_width
        x1 = -1
        y1 = image_height + start_y
        percent = image_height / max_value
        for i, sent in enumerate(sent_values[-(SHOW_WIDTH // bar_width):]):
            # Scale the sent value to the image height
            bar_height = percent * sent
            x0 += bar_width
            x1 += bar_width
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
                full_custom_error_tmp += "获取项目 \"%s\" 失败，请尝试以管理员身份运行本程序。\n" % name
        # 没有数据也要放入列表，因为脚本是用序号来读数据的
        record_dict[str(index)] = (value_formatted, value)
        index += 1

    # 绘制图片

    im1 = Image.new("RGB", (SHOW_WIDTH, SHOW_HEIGHT), (255, 255, 255))

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
        im1.paste((255, 0, 255), (0, 0, im1.size[0], im1.size[1]))

    return im1


def show_full_custom():
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global last_refresh_time, State_change, wait_time, hardware_monitor_manager, current_monoto_time, sleep_event

    if hardware_monitor_manager is None or hardware_monitor_manager == 1:
        sleep_event.wait(0.2)
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
        self.state_machine = 0  # 页面状态
        self.lcd_change = 0  # LCD显示方向
        self.photo_interval_var = 0.1  # 动图间隔，小数部分，实际间隔为 photo_interval_var + second_times
        self.second_times = 0  # 动图间隔，整数部分。设备超过5秒收不到消息就会断开连接，所以每隔1秒发送一次消息
        self.number_var = 1  # 屏幕变化 未使用
        self.select_window_hwnd = 0
        self.fps_var = 5
        self.screen_region_var = "0,0,,"  # 投屏区域，未使用
        self.custom_selected_names = [""] * 2
        self.custom_selected_displayname = [""] * 2
        self.custom_selected_names_tech = [""] * 6
        self.full_custom_template = "p Hello world"


def UI_Page():  # 进行图像界面显示
    global config_obj, Text1, interval_var, all_windows, windows_combobox
    global State_change, Label1, Label3, Label4, Label5, Label6

    # 这两个线程尽早启动
    daemon_thread.start()
    load_thread.start()

    config_obj = load_config()

    # 创建主窗口
    window = tk.Tk()  # 实例化主窗口
    window.title("MG USB屏幕助手V1.0")  # 设置标题

    # 修改默认图标
    iconimage = MiniMark.load_image("resource/icon.ico")
    defaulticon = ImageTk.PhotoImage(iconimage)
    window.wm_iconphoto(True, defaulticon)

    # 创建 Frame 容器，并将其填充到整个窗口
    root = tk.Frame(window, padx=5, pady=5, highlightthickness=1, highlightcolor="lightgray",
                    highlightbackground="lightgray")
    root.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # 设备连接状态标签
    Label1 = tk.Label(root, text="设备未连接", fg="white", bg="red")
    Label1.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)

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
            icon = pystray.Icon("MG", iconimage, "MSU2_mini", menu)
            # 使用新线程启用图标，防止阻塞进入事件循环，如显示桌面。不设置daemon会导致从托盘退出时该线程不结束
            threading.Thread(target=icon.run, daemon=True).start()

            window.withdraw()  # 隐藏主窗口
        except Exception as e:
            insert_text_message("Failed to use pystray to hide to tray, %s" % e)

    hide_btn = ttk.Button(root, text="隐藏", width=12, command=hide_to_tray)
    hide_btn.grid(row=0, column=1, padx=5, pady=5)
    hide_btn.focus_set()  # 设置默认焦点

    # 选择和烧写按钮

    Label3 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label3.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    btn3 = ttk.Button(root, text="选择背景图像", width=12, command=lambda: Get_Photo_Path(1))
    btn3.grid(row=1, column=1, padx=5, pady=5)
    btn5 = ttk.Button(root, text="烧写", width=8, command=lambda: Start_Write_Photo_Path(1))
    btn5.grid(row=1, column=2, padx=5, pady=5)

    Label4 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label4.grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
    btn4 = ttk.Button(root, text="选择闪存固件", width=12, command=lambda: Get_Photo_Path(2))
    btn4.grid(row=2, column=1, padx=5, pady=5)
    btn6 = ttk.Button(root, text="烧写", width=8, command=lambda: Start_Write_Photo_Path(2))
    btn6.grid(row=2, column=2, padx=5, pady=5)

    Label5 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label5.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
    btn10 = ttk.Button(root, text="选择相册图像", width=12, command=lambda: Get_Photo_Path(3))
    btn10.grid(row=3, column=1, padx=5, pady=5)
    btn8 = ttk.Button(root, text="烧写", width=8, command=lambda: Start_Write_Photo_Path(3))
    btn8.grid(row=3, column=2, padx=5, pady=5)

    Label6 = tk.Text(root, state=tk.DISABLED, wrap=tk.NONE, width=22, height=1, padx=5, pady=5)
    Label6.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
    btn11 = ttk.Button(root, text="选择动图文件", width=12, command=lambda: Get_Photo_Path(4))
    btn11.grid(row=4, column=1, padx=5, pady=5)
    btn9 = ttk.Button(root, text="烧写", width=8, command=lambda: Start_Write_Photo_Path(4))
    btn9.grid(row=4, column=2, padx=5, pady=5)

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
    scale_desc.grid(row=0, column=3, columnspan=1, sticky=tk.E, padx=5, pady=5)

    Label2 = tk.Label(root, width=2)  # 颜色预览框
    Label2.grid(row=0, column=4, columnspan=1, padx=5, pady=5, sticky=tk.W)

    update_label_color(config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)

    color_frame = ttk.Frame(root, padding="0")
    color_frame.grid(row=1, column=3, rowspan=3, columnspan=2, padx=5, pady=0, sticky=tk.NSEW)
    color_frame.grid_columnconfigure(1, weight=1)  # 设置第2列自动调整宽度
    color_frame.grid_propagate(0)  # 禁止被内部控件撑大

    scale_ind_r = tk.Label(color_frame, text="R")
    scale_ind_r.grid(row=0, column=0, padx=0, pady=0, sticky=tk.SW)

    text_color_red_scale = tk.Scale(color_frame, from_=0, to=255, orient=tk.HORIZONTAL, borderwidth=0,
                                    takefocus=1, resolution=1, troughcolor="red", font=("TkDefaultFont", 9))
    text_color_red_scale.grid(row=0, column=1, sticky=tk.EW, padx=0, pady=0)
    text_color_red_scale.set(config_obj.text_color_r)
    text_color_red_scale.config(command=lambda x: update_label_color_red())

    scale_ind_g = tk.Label(color_frame, text="G")
    scale_ind_g.grid(row=1, column=0, padx=0, pady=0, sticky=tk.SW)

    text_color_green_scale = tk.Scale(color_frame, from_=0, to=255, orient=tk.HORIZONTAL, borderwidth=0,
                                      takefocus=1, resolution=1, troughcolor="green", font=("TkDefaultFont", 9))
    text_color_green_scale.grid(row=1, column=1, sticky=tk.EW, padx=0, pady=0)
    text_color_green_scale.set(config_obj.text_color_g)
    text_color_green_scale.config(command=lambda x: update_label_color_green())

    scale_ind_b = tk.Label(color_frame, text="B")
    scale_ind_b.grid(row=2, column=0, padx=0, pady=0, sticky=tk.SW)

    text_color_blue_scale = tk.Scale(color_frame, from_=0, to=255, orient=tk.HORIZONTAL, borderwidth=0,
                                     takefocus=1, resolution=1, troughcolor="blue", font=("TkDefaultFont", 9))
    text_color_blue_scale.grid(row=2, column=1, sticky=tk.EW, padx=0, pady=0)
    text_color_blue_scale.set(config_obj.text_color_b)
    text_color_blue_scale.config(command=lambda x: update_label_color_blue())

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

    def center_window(top_window):
        # Get the dimensions of the screen
        screen_width = top_window.winfo_screenwidth()
        screen_height = top_window.winfo_screenheight()

        # Get the dimensions of the parent window
        parent_width = window.winfo_width()
        parent_height = window.winfo_height()
        parent_x = window.winfo_x()
        parent_y = window.winfo_y()

        # Get the dimensions of the child window (default size)
        top_window.update_idletasks()  # Update the window's size information
        child_width = top_window.winfo_width()
        child_height = top_window.winfo_height()

        # Calculate the position
        x = parent_x + (parent_width - child_width) // 2
        y = parent_y + (parent_height - child_height) // 2

        # Check if the child window exceeds the right boundary of the screen
        x1 = screen_width - child_width - 50
        if x > x1:
            x = x1

        # Check if the child window exceeds the bottom boundary of the screen
        y1 = screen_height - child_height - 200
        if y > y1:
            y = y1

        # Ensure the child window is not positioned outside of the left or top borders of the screen
        if x < 50:
            if x1 >= 50:
                x = 50
            elif x < 0:
                x = 0

        if y < 50:
            if y1 >= 50:
                y = 50
            elif y < 0:
                y = 0

        # Set the position of the child window
        top_window.geometry("+%d+%d" % (x, y))

    def show_custom():
        global config_obj, sub_window
        if hardware_monitor_manager == 1:
            tk.messagebox.showerror(title="提示", message="Libre Hardware Monitor 加载失败！", parent=window)
            return
        elif hardware_monitor_manager is None:
            tk.messagebox.showwarning(title="提示", message="Libre Hardware Monitor 正在加载，请稍候……", parent=window)
            return

        def sub_on_closing():
            window.attributes("-disabled", False)  # 启用主窗口
            sub_window.destroy()

        #     # 点击关闭时仅隐藏子窗口，不真正关闭
        #     sub_window.withdraw()
        #
        # if sub_window is not None:
        #     sub_window.deiconify()  # 如果已经创建过子窗口直接显示
        #     window.attributes("-disabled", True)  # 禁用主窗口
        #     return

        sub_window = tk.Toplevel(window)  # 创建一个子窗口
        sub_window.title("自定义显示内容")
        sub_window.resizable(0, 0)  # 锁定窗口大小不能改变
        sub_window.protocol("WM_DELETE_WINDOW", sub_on_closing)
        window.attributes("-disabled", True)  # 禁用主窗口
        sub_window.transient(window)  # 置于主窗口前面

        sensor_vars = []
        sensor_displayname_vars = []
        sensor_vars_tech = []

        # 创建一个选项卡
        notebook = ttk.Notebook(sub_window)
        notebook.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W)

        # 添加“自定义多项”标签页

        tech_frame = tk.Frame(master=sub_window)
        notebook.add(tech_frame, text="  显示多项数值  ")
        tech_frame.focus_set()  # 设置默认焦点

        desc_label = tk.Label(tech_frame, text="名称")
        desc_label.grid(row=1, column=0, padx=5, pady=5)
        desc_label = tk.Label(tech_frame, text="项目")
        desc_label.grid(row=1, column=1, padx=5, pady=5)

        def update_sensor_value_tech(tvars, i):
            global config_obj
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
            sensor_label.grid(row=row1 + 2, column=0, sticky=tk.EW, padx=5, pady=5)

            sensor_var = tk.StringVar(tech_frame, config_obj.custom_selected_names_tech[row1])
            sensor_vars_tech.append(sensor_var)
            sensor_combobox = ttk.Combobox(tech_frame, textvariable=sensor_var, width=60,
                                           values=[""] + list(hardware_monitor_manager.sensors.keys()))
            sensor_combobox.bind("<<ComboboxSelected>>",
                                 lambda event, ii=row1: update_sensor_value_tech(sensor_vars_tech, ii))
            sensor_combobox.grid(row=row1 + 2, column=1, sticky=tk.EW, padx=5, pady=5)
            sensor_combobox.configure(state="readonly")  # 设置选择框不可编辑

        row += 2
        desc_label = tk.Label(tech_frame, text="完全自定义模板代码：", anchor=tk.W, justify=tk.LEFT)
        desc_label.grid(row=row, column=0, columnspan=2, padx=5, pady=5, sticky=tk.EW)

        # 创建自定义内容输入框
        row += 1
        text_frame = ttk.Frame(tech_frame, padding="5")
        text_frame.grid(row=row, column=0, columnspan=2, padx=5, pady=0, sticky=tk.EW)

        def update_global_canvas():
            im = get_full_custom_im()
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

        text_area = tk.Text(text_frame, wrap=tk.WORD, width=10, height=10, padx=0, pady=0)
        text_area.insert(tk.END, config_obj.full_custom_template)
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0, pady=0)

        view_frame = ttk.Frame(text_frame, padding="0")
        view_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=0, pady=0)

        desc_label = tk.Label(view_frame, width=1, text="效果预览：", anchor=tk.NW, justify=tk.LEFT, padx=0, pady=0)
        desc_label.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=0, pady=0)

        canvas = tk.Canvas(view_frame, width=SHOW_WIDTH, height=SHOW_HEIGHT, borderwidth=0)
        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=0, pady=0)

        text_area.bind("<KeyRelease>", update_global_text)  # 按键弹起时触发
        # text_area.bind("<FocusOut>", update_global_text)  # 当组件失去焦点触发
        update_global_canvas()

        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area["yscrollcommand"] = scrollbar.set

        row += 1
        btn_frame = ttk.Frame(tech_frame, padding="5")
        btn_frame.grid(row=row, column=0, columnspan=2, padx=0, pady=0, sticky=tk.EW)
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

        show_error_btn = ttk.Button(btn_frame, text="查看模板错误", width=15, command=show_error)
        show_error_btn.grid(row=0, column=0, padx=5, pady=5, sticky=tk.EW)

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

        example_btn_1 = ttk.Button(btn_frame, text="科技", width=15, command=lambda: example(1))
        example_btn_1.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        example_btn_2 = ttk.Button(btn_frame, text="简单", width=15, command=lambda: example(2))
        example_btn_2.grid(row=0, column=2, padx=5, pady=5, sticky=tk.EW)

        instruction = '\n'.join([
            "自定义显示内容。一共有两个模式，第一个固定显示两行，有图表；第二个是完全自定义模式，可以自己加文本和图片。",
            "模板代码在框中输入，结果可以在预览中看到，模板代码从前往后顺序执行，每行执行一个操作。",
            "p <文本>   \t绘制文本，会自动移动坐标",
            "a <锚点>   \t更改文本锚点，参考Pillow文档，如la,ra,ls,rs",
            "m <x> <y>  \t移动到坐标(x,y)",
            "t <x> <y>  \t相对当前位置移动(x,y)",
            "f <文件名> <字号> \t更换字体，文件名如 arial.ttf",
            "c <hex码>  \t更改文字颜色，如 c #ffff00",
            "i <文件名> \t绘制图片",
            "v <序号> <格式> \t绘制选择项目的值，格式符可省略，如 v 1 {:.2f}",
            "\n* 部分项目需要以管理员身份运行本程序，否则可能显示为<*>或--，甚至可能不会在项目下拉列表中显示。"
        ])

        def show_instruction():
            tk.messagebox.showinfo(title="说明", message=instruction, parent=sub_window)

        show_instruction_btn = ttk.Button(btn_frame, text="说明", width=15, command=show_instruction)
        show_instruction_btn.grid(row=0, column=3, padx=5, pady=5, sticky=tk.EW)

        # 添加“简单两项图表”标签页

        simple_frame = tk.Frame(master=sub_window)
        notebook.add(simple_frame, text="  显示两项图表  ")

        desc_label = tk.Label(simple_frame, text="名称")
        desc_label.grid(row=1, column=0, padx=5, pady=5)
        desc_label = tk.Label(simple_frame, text="项目")
        desc_label.grid(row=1, column=1, padx=5, pady=5)

        def update_sensor_value(vvars, i):
            global config_obj, custom_plot_data
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
            sensor_entry.grid(row=row + 2, column=0, sticky=tk.EW, padx=5, pady=5)

            sensor_var = tk.StringVar(simple_frame, config_obj.custom_selected_names[row])
            sensor_vars.append(sensor_var)
            sensor_combobox = ttk.Combobox(simple_frame, textvariable=sensor_var, width=60,
                                           values=[""] + list(hardware_monitor_manager.sensors.keys()))
            sensor_combobox.bind("<<ComboboxSelected>>", lambda event, ii=row: update_sensor_value(sensor_vars, ii))
            sensor_combobox.grid(row=row + 2, column=1, sticky=tk.EW, padx=5, pady=5)
            sensor_combobox.configure(state="readonly")  # 设置选择框不可编辑

        center_window(sub_window)

    show_custom_btn = ttk.Button(root, text="自定义内容", width=12, command=show_custom)
    show_custom_btn.grid(row=5, column=1, padx=5, pady=5)

    # 方向和翻页按钮

    btn7 = ttk.Button(root, text="切换显示方向", width=12, command=LCD_Change)
    btn7.grid(row=6, column=1, padx=5, pady=5)

    btn1 = ttk.Button(root, text="上翻页", width=8, command=Page_UP)
    btn1.grid(row=5, column=2, padx=5, pady=5)

    btn2 = ttk.Button(root, text="下翻页", width=8, command=Page_Down)
    btn2.grid(row=6, column=2, padx=5, pady=5)

    # 动图间隔

    def change_photo_interval(*args):
        global config_obj
        try:
            photo_interval_tmp = float(interval_var.get())
        except ValueError as e:
            if len(interval_var.get()) > 0:
                insert_text_message("Invalid number entered: %s" % e)
            return
        if (photo_interval_tmp >= 0 and config_obj.photo_interval_var + config_obj.second_times * 2 !=
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
    label_screen_number.grid(row=4, column=3, sticky=tk.E, padx=5, pady=5)

    number_entry = ttk.Entry(root, textvariable=interval_var, width=4)
    number_entry.grid(row=4, column=4, sticky=tk.EW, padx=5, pady=5)

    # 屏幕编号

    number_var = tk.StringVar(root, "1")
    # number_var.trace_add("write", change_screenshot_monitor)
    number_var.set(config_obj.number_var)

    label_screen_number = ttk.Label(root, text="屏幕编号")
    label_screen_number.grid(row=5, column=3, sticky=tk.E, padx=5, pady=5)

    number_entry = ttk.Entry(root, textvariable=number_var, width=4)
    number_entry.grid(row=5, column=4, sticky=tk.EW, padx=5, pady=5)

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
    label.grid(row=6, column=3, sticky=tk.E, padx=5, pady=5)

    fps_entry = ttk.Entry(root, textvariable=fps_var, width=4)
    fps_entry.grid(row=6, column=4, sticky=tk.EW, padx=5, pady=5)

    def combo_configure(event):
        combo = event.widget
        values = combo.cget('values')
        if len(values) > 10:
            add = '000'
        else:
            add = '0'
        long = (max(values, key=len).rstrip() + add)[:75]  # 最长显示100字符
        font = tkfont.nametofont(str(combo.cget('font')))
        width = max(0, font.measure(long) - combo.winfo_width())
        # create an unique style name using widget's id
        style_name = combo.cget('style') or "TCombobox"
        # the new style must inherit from curret widget style (unless it's our custom style!)
        if str(combo.winfo_id()) not in style_name:
            style_name = "Combobox%s.%s" % (combo.winfo_id(), style_name)
        style = ttk.Style()
        style.configure(style_name, postoffset=(0, 0, width, 0))
        combo.configure(style=style_name)

    def update_windows_list(event):
        global config_obj, all_windows
        desc = get_hwnd_desc(config_obj.select_window_hwnd)
        if desc:
            event.widget.set(desc)
        event.widget["value"] = list(all_windows.keys())
        combo_configure(event)

    def update_select_hwnd(event):
        global config_obj, all_windows, State_change, sleep_event, screen_shot_queue, screen_process_queue
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
    label.grid(row=7, column=1, columnspan=1, sticky=tk.E, padx=5, pady=5)

    win32_windows_var = tk.StringVar(
        root, get_hwnd_desc(config_obj.select_window_hwnd)
              or config_obj.select_window_hwnd or list(all_windows.keys())[0])
    windows_combobox = ttk.Combobox(root, textvariable=win32_windows_var, width=10,
                                    values=list(all_windows.keys()))
    windows_combobox.bind('<Configure>', combo_configure)
    windows_combobox.bind('<ButtonPress>', update_windows_list)
    windows_combobox.bind("<<ComboboxSelected>>", update_select_hwnd)
    windows_combobox.grid(row=7, column=2, columnspan=3, sticky=tk.EW, padx=5, pady=5)
    windows_combobox.configure(state="readonly")  # 设置选择框不可编辑

    # 创建信息显示文本框
    Text1 = tk.Text(root, state=tk.DISABLED, width=22, height=4, padx=5, pady=5)
    Text1.grid(row=5, column=0, rowspan=3, columnspan=1, sticky=tk.NS, padx=5, pady=5)

    def on_closing():
        global MG_screen_thread_running, MG_daemon_running, sleep_event
        MG_screen_thread_running = False
        MG_daemon_running = False
        sleep_event.set()  # 取消sleep, 使sleep_event.wait无效

        # 结束时保存配置
        save_config(True)
        window.destroy()

    window.protocol("WM_DELETE_WINDOW", on_closing)
    window.resizable(0, 0)  # 锁定窗口大小不能改变
    # 点击最小化按钮时隐藏窗口
    # window.bind("<Unmap>", lambda event: hide_to_tray() if window.state() == "iconic" else False)
    if len(sys.argv) > 1 and sys.argv[1] == "hide":
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
    global config_obj, ADC_det, ser, State_change, LCD_Change_now
    if ser is not None and ser.is_open:
        ser.close()  # 先将异常的串口连接关闭，防止无法打开

    # 对串口进行监听，确保其为MSN设备
    My_MSN_Device = None
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
                # 对MSN设备进行登记
                My_MSN_Device = MSN_Device(port.device, msn_version)
                print(get_formatted_time_string(datetime.now()), end=' ')
                if port.location is None:
                    insert_text_message("%s连接成功" % port.device)
                else:
                    insert_text_message("%s@%s连接成功" % (port.device, port.location))
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

    # My_MSN_Data = Read_M_SFR_Data(256)  # 读取u8在0x0100之后的128字节
    # Print_MSN_Data(My_MSN_Data)  # 解析字节中的数据格式
    # Read_MSN_Data(My_MSN_Data)  # 从设备读取更详细的数据，如序列号等
    LCD_Change_now = config_obj.lcd_change
    LCD_State(LCD_Change_now)  # 配置显示方向
    # 配置按键阈值
    ADC_det = (Read_ADC_CH(9) + Read_ADC_CH(9) + Read_ADC_CH(9)) // 3
    ADC_det = ADC_det - 200  # 根据125的阈值判断是否被按下
    State_change = 1  # 状态发生变化
    set_device_state(1)  # 可以正常连接


def MSN_Device_1_State_machine():  # MSN设备1的循环状态机
    global config_obj, State_change, LCD_Change_now, Label4, current_monoto_time
    global write_path_index, Img_data_use, color_use

    current_monoto_time = time.monotonic()

    if write_path_index != 0:
        if write_path_index == 1:
            Write_Flash_hex_fast(3826, Img_data_use)
        elif write_path_index == 2:
            photo_path = Label4.get("1.0", tk.END).rstrip()
            Write_Flash_Photo_fast(0, photo_path)
        elif write_path_index == 3:
            Write_Flash_hex_fast(3926, Img_data_use)
        elif write_path_index == 4:
            Write_Flash_hex_fast(0, Img_data_use)
        write_path_index = 0

    if LCD_Change_now != config_obj.lcd_change:  # 显示方向与设置不符合
        LCD_Change_now = config_obj.lcd_change
        LCD_State(LCD_Change_now)  # 配置显示方向

    bar_colors = [(235, 139, 139), (146, 212, 217)]
    # bar_colors = [(128, 255, 128), (255, 128, 255)]
    # bar_colors = [(128, 128, 255), (0, 128, 192)]
    if config_obj.state_machine == PCTIME_PAGE_ID:
        show_PC_time(color_use)  # 展示时钟
    elif config_obj.state_machine == PHOTO_PAGE_ID:
        show_Photo()  # 展示单张相册图像
    elif config_obj.state_machine == SCREEN_PAGE_ID:
        show_PC_Screen()  # 屏幕串流
    elif config_obj.state_machine == STATE_PAGE_ID:
        show_PC_state(color_use, BLACK)  # 展示CPU/内存/磁盘/电池 使用率
    elif config_obj.state_machine == NETSPEED_PAGE_ID:
        rgb_tuple = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
        show_netspeed(text_color=rgb_tuple, bar1_color=bar_colors[0], bar2_color=bar_colors[1])
    elif config_obj.state_machine == CUSTOM1_PAGE_ID:
        rgb_tuple = (config_obj.text_color_r, config_obj.text_color_g, config_obj.text_color_b)
        show_custom_two_rows(text_color=rgb_tuple, bar1_color=bar_colors[0], bar2_color=bar_colors[1])
    elif config_obj.state_machine == CUSTOM2_PAGE_ID:
        show_full_custom()
    else:  # default GIF_PAGE_ID
        show_gif()  # 展示36张动图


def get_formatted_time_string(time):
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load_task():
    global hardware_monitor_manager, PAGE_DESSCRIPTION
    try:
        HardwareMonitorManager = load_hardware_monitor()
        hardware_monitor_manager = HardwareMonitorManager()
        PAGE_DESSCRIPTION = PAGE_DESSCRIPTION + [
            "页面7：自定义显示两项图表",  # CUSTOM1_PAGE_ID = 6
            "页面8：自定义显示多项数值"  # CUSTOM2_PAGE_ID = 7
        ]
        print("Libre hardware monitor load successed")
    except Exception as e:
        hardware_monitor_manager = 1
        print("Libre hardware monitor 加载失败，%s" % traceback.format_exc())


def daemon_task():
    global Device_State, Device_State_Labelen, sleep_event

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
            Get_MSN_Device(wch_port_list)
            if Device_State != 0:
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
            sleep_event.wait(1)  # 防止频繁重试
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

                if ADC_det - ADC_ch > 2500:  # 校正检测阈值
                    ADC_det = (ADC_det + ADC_ch - 200) // 2
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
                    if ADC_ch - ADC_det > 40 + 200:  # 校正检测阈值
                        ADC_det = (ADC_det + ADC_ch - 200) // 2
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


current_monoto_time = 0
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

row_np_zero = None
column_np_zero = None

screenshot_test_time = 0
screenshot_last_limit_time = 0
screenshot_test_frame = 0
wait_time = 0.0

netspeed_last_refresh_snetio = None
netspeed_plot_data = None

custom_plot_data = None  # 用于 show_custom_two_rows,

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

Label1 = None  # 设备状态显示框
Label3 = None  # 背景图像路径显示框
Label4 = None  # 闪存固件路径显示框
Label5 = None  # 相册图像路径显示框
Label6 = None  # 动图文件路径显示框
Text1 = None  # 信息显示文本框
windows_combobox = None
interval_var = None
ser = None  # 设备连接句柄
ADC_det = 0  # 按键阈值
sub_window = None  # 子窗口，设置为全局变量用于重新打开时不需要重复创建
hardware_monitor_manager = None

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
        current_monoto_time = time.monotonic()
        last_refresh_time = current_monoto_time
        screenshot_test_time = current_monoto_time
        screenshot_last_limit_time = current_monoto_time
        sleep_event = threading.Event()  # 用event代替time.sleep，加快切换速度
        config_event = threading.Event()  # 用event代替time.sleep，用于退出时快速保存
        SER_lock = threading.Lock()
        screen_shot_queue = queue.Queue(2)
        screen_process_queue = queue.Queue(2)

        config_obj = sys_config()
        mini_mark_parser = MiniMarkParser()
        default_font = MiniMark.load_font("./simhei.ttf", netspeed_font_size)
        netspeed_font = MiniMark.load_font("resource/Orbitron-Bold.ttf", netspeed_font_size - 4)

        row_np_zero = np.zeros([1, SHOW_WIDTH, 3], dtype=np.uint8)
        column_np_zero = np.zeros([SHOW_HEIGHT, 1, 3], dtype=np.uint8)

        netspeed_plot_data = {"sent": [0] * (SHOW_WIDTH // 2), "recv": [0] * (SHOW_WIDTH // 2)}
        custom_plot_data = {"sent": [0] * (SHOW_WIDTH // 2), "recv": [0] * (SHOW_WIDTH // 2)}

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
        # reap threads
        if ser is not None and ser.is_open:
            print("%s close" % ser.name)
            ser.close()  # 正常关闭串口。串口先于线程关闭，可能会出现访问串口异常，不过能够加快整体关闭速度
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

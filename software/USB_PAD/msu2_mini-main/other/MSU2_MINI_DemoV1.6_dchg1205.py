# -*- coding: UTF-8 -*-
import json  # geezmo: 保存配置用
import os  # 用于读取文件
import queue  # geezmo: 流水线同步和交换数据用
import threading  # 引入定时回调库
import time  # 引入延时库
import tkinter as tk  # 引入UI库
import tkinter.filedialog  # 用于获取文件路径
from ctypes import windll
from datetime import datetime, timedelta  # 用于获取当前时间
from tkinter import ttk  # geezmo: 好看的皮肤

import numpy as np  # 使用numpy加速数据处理
import psutil  # 引入psutil获取设备信息（需要额外安装）
import serial  # 引入串口库（需要额外安装）
import serial.tools.list_ports
from mss import mss  # geezmo: 快速截图
from PIL import Image, ImageDraw, ImageFont  # 引入PIL库进行图像处理

# import pyautogui  # 用于截图(需要额外安装pillow) geezmo: 已去除依赖


# 使用高dpi缩放适配高分屏
try:  # >= win 8.1
    windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
except:  # win 8.0 or less
    windll.user32.SetProcessDPIAware()

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

Img_data_use = bytearray()  # 空数组
size_USE_X1 = 160
size_USE_Y1 = 80


# 参数定义
# SHOW_WIDTH = 160  # 显示宽度
# SHOW_HEIGHT = 80  # 画布高度


# 按键功能定义
def Get_Photo_Path1():  # 获取文件路径
    global photo_path1, Label3
    photo_path1 = tk.filedialog.askopenfilename(
        title="选择文件",
        filetypes=[
            ("Image file", "*.jpg"),
            ("Image file", "*.jpeg"),
            ("Image file", "*.png"),
            ("Image file", "*.bmp"),
        ]
    )
    Label3.config(text=photo_path1[-20:])

    # photo_path1=photo_path1[:-4]
    # print(photo_path1)


def Get_Photo_Path2():  # 获取文件路径
    global photo_path2, Label4
    photo_path2 = tk.filedialog.askopenfilename(
        title="选择文件",
        filetypes=[
            ("Bin file", "*.bin")
        ]
    )
    Label4.config(text=photo_path2[-20:])
    photo_path2 = photo_path2[:-4]
    # print(photo_path2)


def Get_Photo_Path3():  # 获取文件路径
    global photo_path3, Label5  # 支持JPG、PNG、BMP图像格式
    photo_path3 = tk.filedialog.askopenfilename(
        title="选择文件",
        filetypes=[
            ("Image file", "*.jpg"),
            ("Image file", "*.jpeg"),
            ("Image file", "*.png"),
            ("Image file", "*.bmp"),
        ]
    )
    Label5.config(text=photo_path3[-20:])

    # photo_path3=photo_path3[:-4]
    # print(photo_path3)


def Get_Photo_Path4():  # 获取文件路径
    global photo_path4, Label6
    photo_path4 = tk.filedialog.askopenfilename(
        title="选择文件",
        filetypes=[
            ("Image file", "*.jpg"),
            ("Image file", "*.jpeg"),
            ("Image file", "*.png"),
            ("Image file", "*.bmp"),
        ]
    )
    Label6.config(text=photo_path4[-20:])

    # photo_path4=photo_path4[:-4]
    # print(photo_path4)


def Writet_Photo_Path1():  # 写入文件
    global photo_path1, write_path_index, Text1, Img_data_use
    if write_path != 0:  # 确保上次执行写入完毕
        return

    Text1.delete(1.0, tk.END)  # 清除文本框
    Text1.insert(tk.END, "图像格式转换...\n")
    im1 = Image.open(photo_path1)
    if im1.width >= (im1.height * 2):  # 图片长宽比例超过2:1
        im2 = im1.resize((int(80 * im1.width / im1.height), 80))
        Img_m = int(im2.width / 2)
        box = (Img_m - 80, 0, Img_m + 80, 80)  # 定义需要裁剪的空间
        im2 = im2.crop(box)
    else:
        im2 = im1.resize((160, int(160 * im1.height / im1.width)))
        Img_m = int(im2.height / 2)
        box = (0, Img_m - 40, 160, Img_m + 40)  # 定义需要裁剪的空间
        im2 = im2.crop(box)
    im2 = im2.convert("RGB")  # 转换为RGB格式
    Img_data_use = bytearray()  # 空数组
    for y in range(0, 80):  # 逐字解析编码
        for x in range(0, 160):  # 逐字解析编码
            r, g, b = im2.getpixel((x, y))
            Img_data_use.append(((r >> 3) << 3) | (g >> 5))
            Img_data_use.append((((g % 32) >> 2) << 5) | (b >> 3))
    write_path = 1


def Writet_Photo_Path2():  # 写入文件
    global photo_path2, write_path_index, Text1
    if write_path != 0:  # 确保上次执行写入完毕
        return

    Text1.delete(1.0, tk.END)  # 清除文本框
    Text1.insert(tk.END, "准备烧写Flash固件...\n")
    write_path = 2


def Writet_Photo_Path3():  # 写入文件
    global photo_path3, write_path_index, Text1, Img_data_use
    if write_path != 0:  # 确保上次执行写入完毕
        return

    Text1.delete(1.0, tk.END)  # 清除文本框
    Text1.insert(tk.END, "图像格式转换...\n")

    im1 = Image.open(photo_path3)
    if im1.width >= (im1.height * 2):  # 图片长宽比例超过2:1
        im2 = im1.resize((int(80 * im1.width / im1.height), 80))
        Img_m = int(im2.width / 2)
        box = (Img_m - 80, 0, Img_m + 80, 80)  # 定义需要裁剪的空间
        im2 = im2.crop(box)
    else:
        im2 = im1.resize((160, int(160 * im1.height / im1.width)))
        Img_m = int(im2.height / 2)
        box = (0, Img_m - 40, 160, Img_m + 40)  # 定义需要裁剪的空间
        im2 = im2.crop(box)
    im2 = im2.convert("RGB")  # 转换为RGB格式
    Img_data_use = bytearray()  # 空数组
    for y in range(0, 80):  # 逐字解析编码
        for x in range(0, 160):  # 逐字解析编码
            r, g, b = im2.getpixel((x, y))
            Img_data_use.append(((r >> 3) << 3) | (g >> 5))
            Img_data_use.append((((g % 32) >> 2) << 5) | (b >> 3))
    write_path = 3

    # print(img_use)

    # im2.show()
    # Text1.insert(tk.END,'准备烧写背景图像...\n')


def Writet_Photo_Path4():  # 写入文件
    global photo_path4, write_path_index, Text1, Img_data_use
    if write_path != 0:  # 确保上次执行写入完毕
        Text1.insert(tk.END, "转换失败\n")
        return

    Text1.delete(1.0, tk.END)  # 清除文本框
    Text1.insert(tk.END, "动图格式转换中...\n")
    Path_use = photo_path4
    if Path_use[-4] == ".":
        write_path = Path_use[-4:]
        Path_use = Path_use[:-5]
    elif Path_use[-5] == ".":
        write_path = Path_use[-5:]
        Path_use = Path_use[:-6]
    else:
        Text1.insert(tk.END, "动图名称不符合要求！\n")
        return  # 如果文件名不符合要求，直接返回

    Img_data_use = bytearray()
    u_time = time.time()
    for i in range(0, 36):  # 依次转换36张图片
        file_path = Path_use + str(i) + write_path
        if not os.path.exists(file_path):  # 检查文件是否存在
            Text1.insert(tk.END, "缺少动图文件：%s\n" % file_path)
            return  # 如果文件不存在，直接返回，不执行后续代码

        im1 = Image.open(file_path)
        if im1.width >= (im1.height * 2):  # 图片长宽比例超过2:1
            im2 = im1.resize((int(80 * im1.width / im1.height), 80))
            Img_m = int(im2.width / 2)
            box = (Img_m - 80, 0, Img_m + 80, 80)  # 定义需要裁剪的空间
            im2 = im2.crop(box)
        else:
            im2 = im1.resize((160, int(160 * im1.height / im1.width)))
            Img_m = int(im2.height / 2)
            box = (0, Img_m - 40, 160, Img_m + 40)  # 定义需要裁剪的空间
            im2 = im2.crop(box)
        im2 = im2.convert("RGB")  # 转换为RGB格式
        for y in range(0, 80):  # 逐字解析编码
            for x in range(0, 160):  # 逐字解析编码
                r, g, b = im2.getpixel((x, y))
                Img_data_use.append(((r >> 3) << 3) | (g >> 5))
                Img_data_use.append((((g % 32) >> 2) << 5) | (b >> 3))

    Text1.insert(tk.END, "转换完成，耗时%.3f秒\n" % (time.time() - u_time))
    write_path = 4


def Page_UP():  # 上一页
    global State_change, machine_model
    if State_machine == 3901:
        State_machine = 0
    elif State_machine == 5:
        State_machine = 3901
    else:
        State_machine = State_machine + 1
    State_change = 1
    print("Current state changed to: %s" % State_machine)


def Page_Down():  # 下一页
    global State_change, machine_model
    if State_machine == 3901:
        State_machine = 5
    elif State_machine == 0:
        State_machine = 3901
    else:
        State_machine = State_machine - 1
    State_change = 1
    print("Current state changed to: %s" % State_machine)


# State_change = 0  # 全局变量初始化
# def now_the_state_machine():
#     if State_change == 1:
#         print(State_machine)
#
# now_the_state_machine()


def LCD_Change():  # 切换显示方向
    global LCD_Change_use
    if LCD_Change_use == 0:
        LCD_Change_use = 1
    elif LCD_Change_use == 1:
        LCD_Change_use = 0


def SER_Write(Data_U0):
    global Device_State, ser
    if not ser.is_open:
        if Device_State == 1:
            Device_State = 0  # 恢复到未连接状态
        print("设备未连接，取消发送")
        return
    # print('发送数据ing')
    try:  # 尝试发出指令,有两种无法正确发送命令的情况：1.设备被移除,发送出错；2.设备处于MSN连接状态，对于电脑发送的指令响应迟缓
        # 进行超时检测
        # u_time=time.time()
        ser.write(Data_U0)
        ser.flush()
        # print(Data_U0)
        # u_time=time.time()-u_time
        # if u_time>2:
        # print('发送超时')
        # Device_State=0#恢复到未连接状态
        # else:
        # print('发送完成')
    except Exception as e:  # 出现异常
        print("发送异常, %s: %s" % (type(e), e))
        Device_State = 0  # 出现异常，串口需要重连
        ser.close()  # 将串口关闭，防止下次无法打开


def SER_Read():
    global Device_State, ser
    if not ser.is_open:
        if Device_State == 1:
            Device_State = 0  # 恢复到未连接状态
        print("设备未连接，取消读取")
        return 0
    # print('接收数据ing')
    try:  # 尝试获取数据
        # Data_U1 = ser.read_all()
        recv_num = ser.inWaiting()
        while recv_num == 0:
            recv_num = ser.inWaiting()
        Data_U1 = b""
        while recv_num > 0:
            Data_U1 += ser.read(recv_num)
            recv_num = ser.inWaiting()
        return Data_U1
    except Exception as e:  # 出现异常
        print("接收异常, %s: %s" % (type(e), e))
        Device_State = 0  # 出现异常，串口需要重连
        ser.close()  # 将串口关闭，防止下次无法打开
        return 0


def Read_M_u8(add):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(0 * 32)  # 识别为8bit SFR读
    hex_use.append(add // 256)  # 高地址
    hex_use.append(add % 256)  # 低地址
    hex_use.append(0)  # 数值
    SER_Write(hex_use)  # 发出指令

    # 等待收回信息
    recv = SER_Read()  # .decode("byte")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 5:
        return recv[5]


def Read_M_u16(add):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(1 * 32)  # 识别为16bit SFR读
    hex_use.append(add % 256)  # 地址
    hex_use.append(0)  # 高位数值
    hex_use.append(0)  # 低位数值
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("gbk")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 5:
        return recv[4] * 256 + recv[5]


def Write_M_u8(add, data_w):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(4 * 32)  # 识别为16bit SFR写
    hex_use.append(add // 256)  # 高地址
    hex_use.append(add % 256)  # 低地址
    hex_use.append(data_w % 256)  # 数值
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) != 0:
        return 0


def Write_M_u16(add, data_w):  # 读取主机u8寄存器（MSC设备编码，Add）
    hex_use = bytearray()  # 空数组
    hex_use.append(0)  # 发给主机
    hex_use.append(48)  # 识别为SFR指令
    hex_use.append(1 * 32)  # 识别为16bit SFR写
    hex_use.append(add % 256)  # 地址
    hex_use.append(data_w // 256)  # 高位数值
    hex_use.append(data_w % 256)  # 低位数值
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("gbk")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) != 0:
        return 0


def Read_ADC_CH(ch):  # 读取主机ADC寄存器数值（ADC通道）
    hex_use = bytearray()  # 空数组
    hex_use.append(8)  # 读取ADC
    hex_use.append(ch)  # 通道
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("gbk")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 5:
        return recv[4] * 256 + recv[5]


def Read_M_SFR_Data(add):  # 从u8区域获取SFR描述
    SFR_data = bytearray()  # 空数组
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        SFR_data.append(Read_M_u8(add + i))  # 读取编码数据
    data_type = 0  # 根据是否为0进行类型循环统计
    # data_num = 0
    data_len = 0
    data_use = bytearray()  # 空数组
    data_name = b""
    data_unit = b""
    data_family = b""
    # data_data = b''
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        if data_type < 3:
            if SFR_data[i] != 0:  # 未检测到0
                data_use.append(SFR_data[i])  # 将非0数据合并到一块
                continue
            if len(data_use) == 0:  # 没有接收到数据时就接收到00
                break  # 检测到0后收集的数据为空，判断为结束
            if data_type == 0:
                data_name = data_use  # 名称
                data_type = 1
            elif data_type == 1:
                data_unit = data_use  # 单位
                data_type = 2
            else:
                data_family = data_use  # 类型
                data_type = 3
                if ord(data_use) // 32 == 0:  # u8 data 2B add
                    data_len = 2
                elif ord(data_use) // 32 == 1:  # u16 data 1B add
                    data_len = 1
                elif ord(data_use) // 32 == 2:  # u32 data 2B add
                    data_len = 2
                elif ord(data_use) // 32 == 3:  # u8 Text XB data
                    data_len = data_family[0] % 32  # 计算数据长度
            data_use = bytearray()  # 空数组
            continue  # 进行下一次循环
        else:
            if data_len > 0:  # 正式的有效数据
                data_use.append(SFR_data[i])  # 将非0数据合并到一块
                data_len = data_len - 1
            if data_len == 0:  # 将后续数据收集完整
                # data_data = data_use
                data_type = 0  # 重置类型
                # 对数据进行登记
                My_MSN_Data.append(MSN_Data(data_name, data_unit, data_family, data_use))
                data_use = bytearray()  # 获取完成，重置数组


def Print_MSN_Data():
    type_list = ["u8_SFR地址", "u16_SFR地址", "u32_SFR地址", "字符串  ", "u8数组数据"]
    num = len(My_MSN_Data)
    print("MSN数据总数为：%d" % num)
    # 进行数据解析
    for i in range(0, num):  # 将数据全部打印出来
        data_str = "序号：%d\t名称：%s\t单位：%s\t类型：%s\t长度：%d\t地址：%d" % (
            i, My_MSN_Data[i].name.decode("gbk"), My_MSN_Data[i].unit, type_list[ord(My_MSN_Data[i].family) // 32],
            ord(My_MSN_Data[i].family) % 32, int.from_bytes(My_MSN_Data[i].data, byteorder="big"))
        print(data_str)


def Read_MSN_Data(name_use):  # 读取MSN_data中的数据
    num = len(My_MSN_Data)
    use_data = []  # 创建一个空列表
    for i in range(0, num):  # 将数据查找一遍
        if My_MSN_Data[i].name != name_use:
            continue
        if ord(My_MSN_Data[i].family) // 32 == 0:  # 数据类型为u8地址(16bit)
            sfr_add = int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1])
            for n in range(0, ord(My_MSN_Data[i].family) % 32):
                use_data.append(Read_M_u8(sfr_add + n))
        elif ord(My_MSN_Data[i].family) // 32 == 1:  # 数据类型为u16地址(8bit)
            use_data.append(Read_M_u16(int(My_MSN_Data[i].data[0])))
        elif ord(My_MSN_Data[i].family) // 32 == 2:  # 数据类型为u32地址(16bit)
            sfr_add = int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1])
            for n in range(0, ord(My_MSN_Data[i].family) % 32):
                use_data.append(Read_M_u8(sfr_add + n))
        elif ord(My_MSN_Data[i].family) // 32 == 3:  # 数据类型为u8字符串
            use_data.append(My_MSN_Data[i].data)
        elif ord(My_MSN_Data[i].family) // 32 == 4:  # 数据类型为u8数组
            use_data.append(My_MSN_Data[i].data)
        print("use_data：%s = %s" % (My_MSN_Data[i].name, use_data))
        return use_data
    if name_use != 0:
        print('"%s"不存在,请检查名称是否正确' % name_use)
    return []


def Write_MSN_Data(name_use, data_w):  # 在MSN_data写入数据
    num = len(My_MSN_Data)
    for i in range(0, num):  # 将数据查找一遍
        if My_MSN_Data[i].name != name_use:
            continue
        if int(My_MSN_Data[i].family) // 32 == 0:  # 数据类型为u8地址(16bit)
            Write_M_u8(int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1]), data_w)
            print('"%s"写入%s完成' % (name_use, str(data_w)))
            return 0
        elif int(My_MSN_Data[i].family) // 32 == 1:  # 数据类型为u16地址(8bit)
            Write_M_u16(int(My_MSN_Data[i].data[0]), data_w)
            print('"%s"写入%s完成' % (name_use, str(data_w)))
            return 0
    print('"%s"不存在,请检查名称是否正确' % name_use)
    return 0


def Write_Flash_Page(Page_add, data_w, Page_num):  # 往Flash指定页写入256B数据
    # 先把数据传输完成
    hex_use = bytearray()  # 空数组
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use.append(4)  # 多次写入Flash
        hex_use.append(i)  # 低位地址
        hex_use.append(data_w[i * 4 + 0])  # Data0
        hex_use.append(data_w[i * 4 + 1])  # Data1
        hex_use.append(data_w[i * 4 + 2])  # Data2
        hex_use.append(data_w[i * 4 + 3])  # Data3
    #     SER_Write(hex_use)  # 发出指令
    # hex_use = bytearray()  # 空数组
    hex_use.append(3)  # 对Flash操作
    hex_use.append(1)  # 写Flash
    hex_use.append(Page_add // 65536)  # Data0
    hex_use.append((Page_add % 65536) // 256)  # Data1
    hex_use.append((Page_add % 65536) % 256)  # Data2
    hex_use.append(Page_num % 256)  # Data3
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) != 0:
        return 0


# 未经过擦除，直接往Flash指定页写入256B数据
def Write_Flash_Page_fast(Page_add, data_w, Page_num):
    # 先把数据传输完成
    hex_use = b""
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use = hex_use + int(4).to_bytes(1, byteorder="little")  # 多次写入Flash
        hex_use = hex_use + int(i).to_bytes(1, byteorder="little")  # 低位地址
        hex_use = hex_use + data_w[i * 4 + 0].to_bytes(1, byteorder="little")  # Data0
        hex_use = hex_use + data_w[i * 4 + 1].to_bytes(1, byteorder="little")  # Data1
        hex_use = hex_use + data_w[i * 4 + 2].to_bytes(1, byteorder="little")  # Data2
        hex_use = hex_use + data_w[i * 4 + 3].to_bytes(1, byteorder="little")  # Data3
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 对Flash操作
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 经过擦除，写Flash
    # Data0
    hex_use = hex_use + int(Page_add // (256 * 256)).to_bytes(1, byteorder="little")
    # Data1
    hex_use = hex_use + int((Page_add % 65536) // 256).to_bytes(1, byteorder="little")
    # Data2
    hex_use = hex_use + int((Page_add % 65536) % 256).to_bytes(1, byteorder="little")
    # Data3
    hex_use = hex_use + int(Page_num).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) != 0:
        return 0


def Erase_Flash_page(add, size):  # 清空指定区域的内存
    hex_use = bytearray()  # 空数组
    hex_use.append(3)  # 对Flash操作
    hex_use.append(2)  # 清空指定区域的内存
    hex_use.append((add % 65536) // 256)  # Data1
    hex_use.append((add % 65536) % 256)  # Data2
    hex_use.append((size % 65536) // 256)  # Data1
    hex_use.append((size % 65536) % 256)  # Data2
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) != 0:
        return 0


def Read_Flash_byte(add):  # 读取指定地址的数值
    hex_use = bytearray()  # 空数组
    hex_use.append(3)  # 对Flash操作
    hex_use.append(0)  # 读Flash
    hex_use.append(add // (256 * 256))  # Data0
    hex_use.append((add % 65536) // 256)  # Data1
    hex_use.append((add % 65536) % 256)  # Data2
    hex_use.append(0)  # Data3
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 5:
        return recv[5]


def Write_Flash_Photo_fast(Page_add, Photo_name):  # 往Flash里面写入Bin格式的照片
    global Text1
    filepath = "%s.bin" % Photo_name  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件'%s', %s: %s" % (filepath, type(e), e))
        # Text1.delete(1.0,tk.END)#清除文本框
        Text1.insert(tk.END, "文件路径或格式出错!\n")
        return 0
    Fsize = os.path.getsize(filepath)
    print("找到'%s'文件,大小：%dB" % (filepath, Fsize))
    Text1.insert(tk.END, "大小%dB,烧录中...\n" % Fsize)
    u_time = time.time()
    # 进行擦除
    if Fsize % 256 != 0:
        Erase_Flash_page(Page_add, Fsize // 256 + 1)  # 清空指定区域的内存
    else:
        Erase_Flash_page(Page_add, Fsize // 256)  # 清空指定区域的内存

    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = binfile.read(256)
        Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page_fast(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    u_time = time.time() - u_time
    print("%s 烧写完成，耗时%.3f秒" % (filepath, u_time))
    Text1.insert(tk.END, "烧写完成，耗时%.3f秒\n" % u_time)


def Write_Flash_hex_fast(Page_add, img_use):  # 往Flash里面写入hex数据
    Fsize = len(img_use)
    Text1.insert(tk.END, "大小%dB,烧录中...\n" % Fsize)
    u_time = time.time()
    # 进行擦除
    if Fsize % 256 != 0:
        Erase_Flash_page(Page_add, Fsize // 256 + 1)  # 清空指定区域的内存
    else:
        Erase_Flash_page(Page_add, Fsize // 256)  # 清空指定区域的内存
    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = img_use[:256]  # 取前256字节
        img_use = img_use[256:]  # 取剩余字节
        Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = img_use  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page_fast(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    Text1.insert(tk.END, "烧写完成，耗时%.3f秒\n" % (time.time() - u_time))


def Write_Flash_ZK(Page_add, ZK_name):  # 往Flash里面写入Bin格式的字库
    filepath = "%s.bin" % ZK_name  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件'%s', %s: %s" % (filepath, type(e), e))
        return 0
    Fsize = os.path.getsize(filepath) - 6  # 字库文件的最后六个字节不是点阵信息
    print("找到'%s'文件,大小：%dB" % (filepath, Fsize))
    for i in range(0, Fsize // 256):  # 每次写入一个Pag
        Fdata = binfile.read(256)
        Write_Flash_Page(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    print("%s 烧写完成" % filepath)


def LCD_Set_XY(LCD_D0, LCD_D1):  # 设置起始位置
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")  # 设置起始位置
    hex_use = hex_use + int(LCD_D0 // 256).to_bytes(1, byteorder="little")  # Data0
    hex_use = hex_use + int(LCD_D0 % 256).to_bytes(1, byteorder="little")  # Data1
    hex_use = hex_use + int(LCD_D1 // 256).to_bytes(1, byteorder="little")  # Data2
    hex_use = hex_use + int(LCD_D1 % 256).to_bytes(1, byteorder="little")  # Data3
    SER_Write(hex_use)  # 发出指令


def LCD_Set_Size(LCD_D0, LCD_D1):  # 设置大小
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(1).to_bytes(1, byteorder="little")  # 设置大小
    hex_use = hex_use + int(LCD_D0 // 256).to_bytes(1, byteorder="little")  # Data0
    hex_use = hex_use + int(LCD_D0 % 256).to_bytes(1, byteorder="little")  # Data1
    hex_use = hex_use + int(LCD_D1 // 256).to_bytes(1, byteorder="little")  # Data2
    hex_use = hex_use + int(LCD_D1 % 256).to_bytes(1, byteorder="little")  # Data3
    SER_Write(hex_use)  # 发出指令


def LCD_Set_Color(LCD_D0, LCD_D1):  # 设置颜色（FC,BC）
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(2).to_bytes(1, byteorder="little")  # 设置颜色
    hex_use = hex_use + int(LCD_D0 // 256).to_bytes(1, byteorder="little")  # Data0
    hex_use = hex_use + int(LCD_D0 % 256).to_bytes(1, byteorder="little")  # Data1
    hex_use = hex_use + int(LCD_D1 // 256).to_bytes(1, byteorder="little")  # Data2
    hex_use = hex_use + int(LCD_D1 % 256).to_bytes(1, byteorder="little")  # Data3
    SER_Write(hex_use)  # 发出指令


def LCD_Photo(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")  # 显示彩色图片
    hex_use = hex_use + int(Page_Add // 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Page_Add % 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_ADD(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(7).to_bytes(1, byteorder="little")  # 载入地址
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_State(LCD_S):
    global Device_State
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(10).to_bytes(1, byteorder="little")  # 载入地址
    hex_use = hex_use + int(LCD_S).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_DATA(data_w, size):  # 往LCD写入指定大小的数据
    # 先把数据传输完成
    hex_use = b""
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use = hex_use + int(4).to_bytes(1, byteorder="little")  # 多次写入Flash
        hex_use = hex_use + int(i).to_bytes(1, byteorder="little")  # 低位地址
        hex_use = hex_use + data_w[i * 4 + 0].to_bytes(1, byteorder="little")  # Data0
        hex_use = hex_use + data_w[i * 4 + 1].to_bytes(1, byteorder="little")  # Data1
        hex_use = hex_use + data_w[i * 4 + 2].to_bytes(1, byteorder="little")  # Data2
        hex_use = hex_use + data_w[i * 4 + 3].to_bytes(1, byteorder="little")  # Data3
    hex_use = hex_use + int(2).to_bytes(1, byteorder="little")  # 对Flash操作
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 经过擦除，写Flash
    hex_use = hex_use + int(8).to_bytes(1, byteorder="little")  # Data0
    hex_use = hex_use + int(size // 256).to_bytes(1, byteorder="little")  # Data1
    hex_use = hex_use + int(size % 256).to_bytes(1, byteorder="little")  # Data2
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")  # Data3
    SER_Write(hex_use)  # 发出指令


# 往Flash里面写入Bin格式的照片
def Write_LCD_Photo_fast(x_star, y_star, x_size, y_size, Photo_name):
    filepath = "%s.bin" % Photo_name  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件'%s', %s: %s" % (filepath, type(e), e))
        return
    Fsize = os.path.getsize(filepath)
    print("找到'%s'文件,大小：%dB" % (filepath, Fsize))
    u_time = time.time()
    # 进行地址写入
    LCD_ADD(x_star, y_star, x_size, y_size)
    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = binfile.read(256)
        LCD_DATA(Fdata, 256)  # (page,数据，大小)
    if Fsize % 256 != 0:  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        LCD_DATA(Fdata, Fsize % 256)  # (page,数据，大小)
    u_time = time.time() - u_time
    print("%s 显示完成，耗时%.3f秒" % (filepath, u_time))


# 往Flash里面写入Bin格式的照片
def Write_LCD_Photo_fast1(x_star, y_star, x_size, y_size, Photo_name):
    filepath = "%s.bin" % Photo_name  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, "rb")  # 以只读方式打开
    except Exception as e:  # 出现异常
        print("找不到文件'%s', %s: %s" % (filepath, type(e), e))
        return
    Fsize = os.path.getsize(filepath)
    print("找到'%s'文件,大小：%dB" % (filepath, Fsize))
    u_time = time.time()
    # 进行地址写入
    LCD_ADD(x_star, y_star, x_size, y_size)
    hex_use = bytearray()  # 空数组
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
        data_w = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            # 不足位置补充0xFF
            data_w = data_w + int(255).to_bytes(1, byteorder="little")
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
    SER_Write(hex_use)  # 发出指令
    u_time = time.time() - u_time
    print("%s 显示完成，耗时%.3f秒" % (filepath, u_time))


# 往Flash里面写入Bin格式的照片
def Write_LCD_Screen_fast(x_star, y_star, x_size, y_size, Photo_data):
    LCD_ADD(x_star, y_star, x_size, y_size)
    Photo_data_use = Photo_data
    hex_use = bytearray()  # 空数组
    for j in range(0, x_size * y_size * 2 // 256):  # 每次写入一个Page
        data_w = Photo_data_use[:256]
        Photo_data_use = Photo_data_use[256:]
        cmp_use = []  # 空数组,
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
            ) != result:  #
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
    if x_size * y_size * 2 % 256 != 0:  # 还存在没写完的数据
        data_w = Photo_data_use  # 将剩下的数据读完
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
    SER_Write(hex_use)  # 发出指令


# 往Flash里面写入Bin格式的照片，对发送的数据进行编码分析,缩短数据指令
def Write_LCD_Screen_fast1(x_star, y_star, x_size, y_size, Photo_data):
    LCD_ADD(x_star, y_star, x_size, y_size)
    Photo_data_use = Photo_data
    hex_use = bytearray()  # 空数组
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
    if x_size * y_size * 2 % 256 != 0:  # 还存在没写完的数据
        data_w = Photo_data_use  # 将剩下的数据读完
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
    SER_Write(hex_use)  # 发出指令


def LCD_Photo_wb(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add, LCD_FC, LCD_BC):
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    LCD_Set_Color(LCD_FC, LCD_BC)
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(1).to_bytes(1, byteorder="little")  # 显示单色图片
    hex_use = hex_use + int(Page_Add // 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Page_Add % 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:  # 对于回传的数据需要进行校验，确保设备状态能够被准确识别到
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_ASCII_32X64(LCD_X, LCD_Y, Txt, LCD_FC, LCD_BC, Num_Page):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, LCD_BC)
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(2).to_bytes(1, byteorder="little")  # 显示ASCII
    hex_use = hex_use + int(ord(Txt)).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Num_Page // 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Num_Page % 256).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_GB2312_16X16(LCD_X, LCD_Y, Txt, LCD_FC, LCD_BC):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, LCD_BC)
    Txt_Data = Txt.encode("gb2312")
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 显示彩色图片
    hex_use = hex_use + int(Txt_Data[0]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Txt_Data[1]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_Photo_wb_MIX(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add, LCD_FC, BG_Page):
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    LCD_Set_Color(LCD_FC, BG_Page)
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(4).to_bytes(1, byteorder="little")  # 显示单色图片
    hex_use = hex_use + int(Page_Add // 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Page_Add % 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_ASCII_32X64_MIX(LCD_X, LCD_Y, Txt, LCD_FC, BG_Page, Num_Page):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, BG_Page)
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(5).to_bytes(1, byteorder="little")  # 显示ASCII
    hex_use = hex_use + int(ord(Txt)).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Num_Page // 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Num_Page % 256).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


def LCD_GB2312_16X16_MIX(LCD_X, LCD_Y, Txt, LCD_FC, BG_Page):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, BG_Page)
    Txt_Data = Txt.encode("gb2312")
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(6).to_bytes(1, byteorder="little")  # 显示彩色图片
    hex_use = hex_use + int(Txt_Data[0]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Txt_Data[1]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错
        return 0


# 对指定区域进行颜色填充
def LCD_Color_set(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, F_Color):
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Size(LCD_X_Size, LCD_Y_Size)
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(11).to_bytes(1, byteorder="little")  # 显示彩色图片
    hex_use = hex_use + int(F_Color // 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(F_Color % 256).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    recv = SER_Read()  # .decode("UTF-8")#获取串口数据
    if recv == 0:
        return 0
    elif len(recv) > 1:
        if (recv[0] != hex_use[0]) or (recv[1] != hex_use[1]):
            Device_State = 0  # 接收出错


def show_gif():  # 显示GIF动图
    global State_change, gif_num
    if State_change == 1:
        State_change = 0
        gif_num = 0

    LCD_Photo(0, 0, 160, 80, gif_num * 100)
    gif_num = gif_num + 1
    if gif_num > 35:
        gif_num = 0
    time.sleep(0.05)  # 用来调整动图播放速度
    # LCD_Color_set(40,0,80,80,RED)


disk_io_counter = None
net_io_counter = None


def show_PC_state(FC, BC):  # 显示PC状态
    global State_change, disk_io_counter, net_io_counter
    photo_add = 4038
    num_add = 4026
    if State_change == 1:
        State_change = 0
        LCD_Photo_wb(0, 0, 160, 80, photo_add, FC, BC)  # 放置背景

    # CPU
    CPU = int(psutil.cpu_percent(interval=0.5))
    # mem
    mem = psutil.virtual_memory()
    RAM = int(mem.percent)
    # battery
    # battery = psutil.sensors_battery()
    # if battery is not None:
    #     BAT = int(battery.percent)
    # else:
    #     BAT = 100
    # 磁盘使用率
    # FRQ = int(psutil.disk_usage("/").used * 100 / psutil.disk_usage("/").total)
    # 磁盘IO
    FRQ = 0
    disk_io_counter_cur = psutil.disk_io_counters()
    if disk_io_counter is not None:
        disk_used = (disk_io_counter_cur.read_bytes + disk_io_counter_cur.write_bytes
                     - disk_io_counter.read_bytes - disk_io_counter.write_bytes)
        if disk_used > 0:
            FRQ = disk_used // 1024 // 1024  # MB
    disk_io_counter = disk_io_counter_cur
    # 网络IO
    BAT = 0
    net_io_counter_cur = psutil.net_io_counters()
    if net_io_counter is not None:
        net_used = (net_io_counter_cur.bytes_sent + net_io_counter_cur.bytes_recv
                    - net_io_counter.bytes_sent - net_io_counter.bytes_recv)
        if net_used > 0:
            BAT = net_used * 8 // 1024 // 1024  # Mb
    net_io_counter = net_io_counter_cur

    if CPU >= 100:
        LCD_Photo_wb(24, 0, 8, 33, 10 + num_add, FC, BC)
        CPU = CPU % 100
    else:
        LCD_Photo_wb(24, 0, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(32, 0, 24, 33, (CPU // 10) + num_add, FC, BC)
    LCD_Photo_wb(56, 0, 24, 33, (CPU % 10) + num_add, FC, BC)
    if RAM >= 100:
        LCD_Photo_wb(104, 0, 8, 33, 10 + num_add, FC, BC)
        RAM = RAM % 100
    else:
        LCD_Photo_wb(104, 0, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(112, 0, 24, 33, (RAM // 10) + num_add, FC, BC)
    LCD_Photo_wb(136, 0, 24, 33, (RAM % 10) + num_add, FC, BC)
    if BAT >= 100:
        LCD_Photo_wb(104, 47, 8, 33, 10 + num_add, FC, BC)
        BAT = BAT % 100
    else:
        LCD_Photo_wb(104, 47, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(112, 47, 24, 33, (BAT // 10) + num_add, FC, BC)
    LCD_Photo_wb(136, 47, 24, 33, (BAT % 10) + num_add, FC, BC)
    if FRQ >= 100:
        LCD_Photo_wb(24, 47, 8, 33, 10 + num_add, FC, BC)
        FRQ = FRQ % 100
    else:
        LCD_Photo_wb(24, 47, 8, 33, 11 + num_add, FC, BC)
    LCD_Photo_wb(32, 47, 24, 33, (FRQ // 10) + num_add, FC, BC)
    LCD_Photo_wb(56, 47, 24, 33, (FRQ % 10) + num_add, FC, BC)
    time.sleep(0.3)  # 1秒左右刷新一次


def show_Photo1():  # 显示照片
    global State_change
    # FC = BLUE
    # BC = BLACK
    if State_change == 1:
        State_change = 0

    LCD_Photo(0, 0, 160, 80, 3926)  # 放置背景
    time.sleep(1)  # 1秒刷新一次


def show_PC_time():
    global State_change
    FC = color_use
    photo_add = 3826
    num_add = 3651
    if State_change == 1:
        State_change = 0
        LCD_Photo(0, 0, 160, 80, photo_add)  # 放置背景
        LCD_ASCII_32X64_MIX(56 + 8, 0, ":", FC, photo_add, num_add)
        # LCD_ASCII_32X64_MIX(136+8,32,':',FC,photo_add,num_add)

    date = datetime.now()
    time_h = int(date.hour)
    time_m = int(date.minute)
    time_S = int(date.second)
    LCD_ASCII_32X64_MIX(0 + 8, 8, chr((time_h // 10) + 48), FC, photo_add, num_add)
    LCD_ASCII_32X64_MIX(32 + 8, 8, chr((time_h % 10) + 48), FC, photo_add, num_add)
    LCD_ASCII_32X64_MIX(80 + 8, 8, chr((time_m // 10) + 48), FC, photo_add, num_add)
    LCD_ASCII_32X64_MIX(112 + 8, 8, chr((time_m % 10) + 48), FC, photo_add, num_add)
    # LCD_ASCII_32X64_MIX(160 + 8, 8, chr((time_S // 10) + 48), FC, photo_add, num_add)
    # LCD_ASCII_32X64_MIX(192 + 8, 8, chr((time_S % 10) + 48), FC, photo_add, num_add)
    time.sleep(1)  # 1秒刷新一次


def digit_to_ints(di):
    return [(di >> 24) & 0xFF, (di >> 16) & 0xFF, (di >> 8) & 0xFF, di & 0xFF]


def Screen_Date_Process(Photo_data):  # 对数据进行转换处理
    uint16_data = Photo_data.astype(np.uint32)
    hex_use = bytearray()  # 空数组
    total_data_size = size_USE_X1 * size_USE_Y1
    data_per_page = 128
    for j in range(0, total_data_size // data_per_page):  # 每次写入一个Page
        data_w = uint16_data[j * data_per_page: (j + 1) * data_per_page]
        cmp_use = data_w[::2] << 16 | data_w[1::2]  # 256字节数据分为64个指令

        result = 0
        if data_w.size > 0:
            u, c = np.unique(cmp_use, return_counts=True)
            result = u[c.argmax()]  # 找最频繁的指令

        hex_use.extend([2, 4])

        # 最常见的指令，背景色？
        hex_use.extend(digit_to_ints(result))
        # 每个前景色
        for i, cmp_value in enumerate(cmp_use):
            if cmp_value != result:
                hex_use.extend([4, i] + digit_to_ints(cmp_value))

        # Append footer
        hex_use.extend([2, 3, 8, 1, 0, 0])
    remaining_data_size = total_data_size % data_per_page
    if remaining_data_size != 0:  # 还存在没写完的数据
        data_w = uint16_data[-remaining_data_size:]  # 取最后的没有写的
        data_w += b"\xff\xff" * (128 - remaining_data_size)  # 补全128个 uint16
        cmp_use = data_w[::2] << 16 | data_w[1::2]
        for i in range(0, 64):
            cmp_value = cmp_use[i]
            hex_use.extend([4, i] + digit_to_ints(cmp_value))
        hex_use.extend([2, 3, 8, 0, remaining_data_size * 2, 0])
    return hex_use


def rgb888_to_rgb565(rgb888_array):
    # Convert RGB888 to RGB565
    r = (rgb888_array[:, :, 0] >> 3) & 0x1F  # 5 bits for red
    g = (rgb888_array[:, :, 1] >> 2) & 0x3F  # 6 bits for green
    b = (rgb888_array[:, :, 2] >> 3) & 0x1F  # 5 bits for blue

    r = r.astype(np.uint16)
    g = g.astype(np.uint16)
    b = b.astype(np.uint16)

    # Combine into RGB565 format
    rgb565 = (r << 11) | (g << 5) | b

    # Convert to a 16-bit unsigned integer array
    return rgb565.astype(np.uint16)


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
    # final_shape = (int(image.shape[0] / shrink_factor), int(image.shape[1] / shrink_factor))
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


MG_daemon_should_stop = False
MG_screen_thread_running = False
screen_shot_queue = queue.Queue(2)
screenshot_monitor_id = 1
screen_process_queue = queue.Queue(2)
cropped_monitor = {}
screenshot_region = (None, None, None, None)


def screen_shot_task():  # 创建专门的函数来获取屏幕图像和处理转换数据
    print("截图线程创建成功")

    with mss() as sct:
        while True:
            if MG_screen_thread_running:
                print("stop screenshot")
                break  # exit screenshot thread
            if machine_model != 5:
                if not screen_shot_queue.empty():
                    screen_shot_queue.get()
                time.sleep(0.5)  # 不需要截图时
                continue
            if screen_shot_queue.full():
                time.sleep(1.0 / screenshot_limit_fps)  # 队列满时暂停一个周期
                continue

            try:
                sct_img = sct.grab(cropped_monitor)  # geezmo: 截屏已优化
                screen_shot_queue.put((sct_img, cropped_monitor), timeout=3)
            except queue.Full:
                # 每1s检测一次退出，并且如果下游不拿走，则重新截图
                pass
            except Exception as e:
                print("截屏失败 %s: %s" % (type(e), e))


# geezmo: 流水线 第二步 处理图像
def screen_process_task():
    while True:
        if MG_screen_thread_running:
            print("stop screen process")
            break  # exit screenshot thread
        if machine_model != 5:
            if not screen_process_queue.empty():
                screen_process_queue.get()
            time.sleep(0.5)  # 不需要截图时
            continue
        if screen_process_queue.full():
            time.sleep(1.0 / screenshot_limit_fps)  # 队列满时暂停一个周期
            continue

        try:
            sct_img, monitor = screen_shot_queue.get(timeout=3)
        except queue.Empty:
            continue

        # u_time1 = time.time()

        bgra = np.frombuffer(sct_img.bgra, dtype=np.uint8).reshape((sct_img.size[1], sct_img.size[0], 4))
        rgb = bgra[:, :, :3]
        rgb = rgb[:, :, ::-1]

        if monitor["width"] <= monitor["height"] * 2:  # 横向充满
            # new_width = 160
            # new_height = new_width * screen_height // screen_width
            im1 = shrink_image_block_average(rgb, rgb.shape[1] / size_USE_X1)

            # start_y = (new_height - 80) // 2
            im1 = im1[0: size_USE_Y1, :]
        else:  # 纵向充满
            # new_height = 80
            # new_width = new_height * screen_width // screen_height
            im1 = shrink_image_block_average(rgb, rgb.shape[0] / size_USE_Y1)

            # start_x = (new_width - 160) // 2
            im1 = im1[:, 0: size_USE_X1]

        rgb888 = np.asarray(im1)

        rgb565 = rgb888_to_rgb565(rgb888)
        # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
        hexstream = Screen_Date_Process(rgb565.flatten())

        # u_time1 = time.time() - u_time1
        # print("截屏耗时%.3f" % u_time1)

        try:
            screen_process_queue.put(hexstream, timeout=3)
        except queue.Full:
            pass


screenshot_test_time = datetime.now()
screenshot_last_limit_time = screenshot_test_time
screenshot_test_frame = 0
screenshot_limit_fps = 100
wait_time = 0


# 连续多次截图失败，重启截图线程
def screenshot_panic():
    global MG_screen_thread_running, screen_shot_thread, screen_process_thread
    MG_screen_thread_should_stop = True
    print("Screenshot threads are panicking")
    if screen_shot_thread.is_alive():
        screen_shot_thread.join()
    if screen_process_thread.is_alive():
        screen_process_thread.join()
    # time.sleep(3)
    MG_screen_thread_should_stop = False
    screen_shot_thread.start()
    screen_process_thread.start()


def show_PC_Screen():  # 显示照片
    global State_change, Screen_Error, Device_State, screenshot_test_frame
    global screenshot_test_time, screenshot_last_limit_time, wait_time, screenshot_limit_fps
    if State_change == 1:
        State_change = 0
        Screen_Error = 0
        LCD_ADD((160 - size_USE_X1) // 2, (80 - size_USE_Y1) // 2, size_USE_X1, size_USE_Y1)

    try:
        hexstream = screen_process_queue.get(timeout=1)
    except queue.Empty:
        Screen_Error = Screen_Error + 1
        time.sleep(0.05)  # 防止频繁重试
        if Screen_Error > 100:
            screenshot_panic()
        return
    # u_time = time.time()
    SER_Write(hexstream)
    # u_time = time.time() - u_time
    # print("传输耗时%.3f" % u_time)
    current_time = datetime.now()
    elapse_time = (current_time - screenshot_last_limit_time).total_seconds()
    if elapse_time > 5:  # 有切换，重置参数
        screenshot_test_time = current_time
        screenshot_test_frame = 0
        elapse_time = 1.0 / screenshot_limit_fps  # 第一次不需要wait
    elif screenshot_test_frame % screenshot_limit_fps == 0:
        real_fps = screenshot_limit_fps / ((current_time - screenshot_test_time).total_seconds())
        print("串流FPS: %s" % real_fps)
        screenshot_test_time = current_time
    wait_time += 1.0 / screenshot_limit_fps - elapse_time
    if wait_time > 0:
        time.sleep(wait_time)  # 精确控制FPS
    screenshot_last_limit_time = current_time
    screenshot_test_frame += 1
    if Screen_Error != 0:
        Screen_Error = 0


netspeed_last_refresh_time = None
netspeed_last_refresh_snetio = None
netspeed_plot_data = [{}]


def sizeof_fmt(num, suffix="B", base=1024.0):
    # Use KB for small value
    for unit in ("K", "M", "G", "T", "P", "E", "Z"):
        num /= base
        if abs(num) < base:
            return "%3.1f%s%s" % (num, unit, suffix)
    return "%3.1fY%s" % (num, suffix)


netspeed_font = None
netspeed_font_size = 20
try:
    netspeed_font = ImageFont.truetype("simhei.ttf", netspeed_font_size)
except OSError:
    # Pillow 可能不能忽略文件大小写，以免读取失败
    try:
        netspeed_font = ImageFont.truetype("SimHei.ttf", netspeed_font_size)
    except OSError as e:

        def _(*args, **kwargs):
            pass


        # 字体读取失败，停用 netspeed
        print("字体读取失败，停用 netspeed: %s: %s" % (type(e), e))
        show_netspeed = _


def show_netspeed(text_color=(255, 128, 0)):
    global netspeed_last_refresh_time, netspeed_last_refresh_snetio, netspeed_plot_data, State_change

    SHOW_WIDTH = 160  # 显示宽度
    SHOW_HEIGHT = 80  # 画布高度
    bar_width = 2  # 每个点宽度
    image_height = 20  # 高度

    # geezmo: 预渲染图片，显示网速
    if netspeed_last_refresh_time is None or State_change == 1:
        # 初始化
        State_change = 0
        netspeed_last_refresh_time = datetime.now()
        netspeed_last_refresh_snetio = psutil.net_io_counters()
        netspeed_plot_data = [{"sent": 0, "recv": 0}] * int(SHOW_WIDTH / bar_width)
        # 初始化的时候，网速先显示0
        current_snetio = netspeed_last_refresh_snetio
        LCD_ADD((SHOW_WIDTH - size_USE_X1) // 2, (SHOW_HEIGHT - size_USE_Y1) // 2, size_USE_X1, size_USE_Y1)
    else:
        current_snetio = psutil.net_io_counters()

    # 获取网速 bytes/second

    current_time = datetime.now()
    seconds_elapsed = (current_time - netspeed_last_refresh_time) / timedelta(seconds=1)

    sent_per_second = (current_snetio.bytes_sent - netspeed_last_refresh_snetio.bytes_sent) / seconds_elapsed
    recv_per_second = (current_snetio.bytes_recv - netspeed_last_refresh_snetio.bytes_recv) / seconds_elapsed
    # print(current_snetio.bytes_sent, netspeed_last_refresh_snetio.bytes_sent, seconds_elapsed)

    # netspeed_plot_data = netspeed_plot_data[1:] + [{"sent": sent_per_second, "recv": recv_per_second}]
    netspeed_plot_data.append({"sent": sent_per_second, "recv": recv_per_second})
    netspeed_plot_data.pop(0)

    netspeed_last_refresh_time = current_time
    netspeed_last_refresh_snetio = current_snetio

    # 绘制图片
    im1 = Image.new("RGB", (size_USE_X1, size_USE_Y1), (0, 0, 0))
    # im1 = Image.open('示例.png')

    draw = ImageDraw.Draw(im1)

    # 绘制文字
    text = "上传%10s" % sizeof_fmt(sent_per_second)
    draw.text((0, 0), text, fill=text_color, font=netspeed_font)
    text = "下载%10s" % sizeof_fmt(recv_per_second)
    draw.text((0, SHOW_HEIGHT / 2), text, fill=text_color, font=netspeed_font)

    # 绘图
    for start_y, key, color in zip([19, 59], ["sent", "recv"], [(235, 139, 139), (146, 211, 217)]):
        sent_values = [data[key] for data in netspeed_plot_data]
        max_value = max(1024 * 100, max(sent_values))  # 最小范围 100KB/s

        for i, sent in enumerate(sent_values[-int(SHOW_WIDTH / bar_width):]):
            # Scale the sent value to the image height
            bar_height = int((sent / max_value) * image_height) if max_value else 0
            x0 = i * bar_width
            y0 = image_height - bar_height
            x1 = (i + 1) * bar_width
            y1 = image_height

            # Draw the bar
            draw.rectangle([x0, start_y + y0, x1 - 1, max(start_y + y0, start_y + y1 - 1)], fill=color)

    rgb888 = np.asarray(im1)
    rgb565 = rgb888_to_rgb565(rgb888)
    # arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
    hexstream = Screen_Date_Process(rgb565.flatten())
    SER_Write(hexstream)

    # 大约每1秒刷新一次
    time.sleep(1 - (datetime.now() - netspeed_last_refresh_time) / timedelta(seconds=1))
    # 测试用：显示帧率
    # print(1 / seconds_elapsed)


def save_config(config_obj):
    with open("MSU2_MINI.json", "w", encoding="utf-8") as f:
        json.dump(config_obj, f)


def load_config():
    try:
        with open("MSU2_MINI.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def UI_Page():  # 进行图像界面显示
    global root, text_color_red_scale, text_color_green_scale, text_color_blue_scale, Text1
    global machine_model, State_change, LCD_Change_use, Label1, Label2, Label3, Label4, Label5, Label6
    # 创建主窗口
    root = tk.Tk()  # 实例化主窗口
    root.title("MG USB屏幕助手V1.0")  # 设置标题
    # screen_width = root.winfo_screenwidth()
    # screen_height = root.winfo_screenheight()
    # Show_X = int(screen_width / 2) - int(Show_W / 2)
    # Show_Y = int(screen_height / 2) - int(Show_H / 2)
    # root.geometry("%dx%d+%d+%d" % (Show_W, Show_H, Show_X, Show_Y))  # 主窗口的大小以及在显示器上的位置

    config_obj = load_config()

    # 创建标签
    Label1 = tk.Label(root, text="设备未连接", fg="white", bg="Red")
    Label1.grid(row=0, column=0, sticky="w", padx=5, pady=5)

    Label2 = tk.Label(root, bg="#ff8000", width=2)
    Label2.grid(row=4, column=3, padx=5, pady=5)

    Label3 = tk.Label(root, bg="white", width=21)
    Label3.grid(row=1, column=0, sticky="w", padx=5, pady=5)

    Label4 = tk.Label(root, bg="white", width=21)
    Label4.grid(row=2, column=0, sticky="w", padx=5, pady=5)

    Label5 = tk.Label(root, bg="white", width=21)
    Label5.grid(row=3, column=0, sticky="w", padx=5, pady=5)

    Label6 = tk.Label(root, bg="white", width=21)
    Label6.grid(row=4, column=0, sticky="w", padx=5, pady=5)

    # 创建文本框
    Text1 = tk.Text(root, width=22, height=4)
    Text1.grid(row=5, column=0, rowspan=2, padx=5, pady=5)

    def update_label_color():
        global color_use, rgb_tuple, State_change
        r1 = int(text_color_red_scale.get())
        g1 = int(text_color_green_scale.get())
        b1 = int(text_color_blue_scale.get())
        color_use = r1 * 2048 + g1 * 32 + b1  # 彩色图片点阵算法 5R6G5B
        r2 = r1 * 255 // 31
        g2 = g1 * 255 // 63
        b2 = b1 * 255 // 31
        rgb_tuple = (r2, g2, b2)  # rgb
        if Label2:
            color_La = "#{:02x}{:02x}{:02x}".format(r2, g2, b2)
            Label2.config(bg=color_La)
        State_change = 1
        time.sleep(0.05)  # 鼠标移动时会频繁刷新，用来降低刷新频率

    # 创建滑块

    scale_desc = tk.Label(root, text="文字颜色")
    scale_desc.grid(row=0, column=3, sticky="w", padx=5, pady=5)

    text_color_red_scale = ttk.Scale(root, from_=0, to=31, orient=tk.HORIZONTAL)
    text_color_red_scale.grid(row=1, column=3, sticky="w", padx=5)
    text_color_red_scale.set(config_obj.get("text_color_r", 31))
    text_color_red_scale.config(command=lambda x: update_label_color())

    scale_ind_r = tk.Label(root, bg="red", width=2)
    scale_ind_r.grid(row=1, column=4, padx=5, pady=5, sticky="w")

    text_color_green_scale = ttk.Scale(root, from_=0, to=63, orient=tk.HORIZONTAL)
    text_color_green_scale.grid(row=2, column=3, sticky="w", padx=5)
    text_color_green_scale.set(config_obj.get("text_color_g", 32))
    text_color_green_scale.config(command=lambda x: update_label_color())

    scale_ind_g = tk.Label(root, bg="green", width=2)
    scale_ind_g.grid(row=2, column=4, padx=5, pady=5, sticky="w")

    text_color_blue_scale = ttk.Scale(root, from_=0, to=31, orient=tk.HORIZONTAL)
    text_color_blue_scale.grid(row=3, column=3, sticky="w", padx=5)
    text_color_blue_scale.set(config_obj.get("text_color_b", 0))
    text_color_blue_scale.config(command=lambda x: update_label_color())

    scale_ind_b = tk.Label(root, bg="blue", width=2)
    scale_ind_b.grid(row=3, column=4, padx=5, pady=5, sticky="w")

    # 创建按钮

    btn3 = ttk.Button(root, text="选择背景图像", width=12, command=Get_Photo_Path1)
    btn3.grid(row=1, column=1, padx=5)

    btn4 = ttk.Button(root, text="选择闪存固件", width=12, command=Get_Photo_Path2)
    btn4.grid(row=2, column=1, padx=5)

    btn10 = ttk.Button(root, text="选择相册图像", width=12, command=Get_Photo_Path3)
    btn10.grid(row=3, column=1, padx=5)

    btn11 = ttk.Button(root, text="选择动图文件", width=12, command=Get_Photo_Path4)
    btn11.grid(row=4, column=1, padx=5)

    btn7 = ttk.Button(root, text="切换显示方向", width=12, command=LCD_Change)
    btn7.grid(row=6, column=1, padx=5)

    btn5 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path1)
    btn5.grid(row=1, column=2, padx=5)

    btn6 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path2)
    btn6.grid(row=2, column=2, padx=5)

    btn8 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path3)
    btn8.grid(row=3, column=2, padx=5)

    btn9 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path4)
    btn9.grid(row=4, column=2, padx=5)

    btn1 = ttk.Button(root, text="上翻页", width=8, command=Page_UP)
    btn1.grid(row=5, column=2, padx=5)

    btn2 = ttk.Button(root, text="下翻页", width=8, command=Page_Down)
    btn2.grid(row=6, column=2, padx=5)

    # 按钮涉及的配置项

    # 创建一个新容器
    screen_frame = tk.Frame(root)
    screen_frame.grid(row=5, column=3, rowspan=2, columnspan=2)

    State_machine = config_obj.get("state_machine", 3901)
    State_change = 1
    LCD_Change_use = config_obj.get("lcd_change", 2)

    number_var = tk.StringVar(root, "1")

    def change_screenshot_monitor(*args):
        global screenshot_monitor_id, screenshot_region, cropped_monitor
        try:
            screenshot_monitor_id_tmp = int(number_var.get())
        except ValueError as e:
            if len(number_var.get()) > 0:
                print("Invalid number entered: %s: %s" % (type(e), e))
            return

        with mss() as sct:
            if 0 < screenshot_monitor_id_tmp <= len(sct.monitors[1:]):
                screenshot_monitor_id = screenshot_monitor_id_tmp
                try:
                    monitor = sct.monitors[screenshot_monitor_id]
                except IndexError:
                    monitor = sct.monitors[1]
                cropped_monitor = {
                    "left": (screenshot_region[0] or 0) + monitor["left"],
                    "top": (screenshot_region[1] or 0) + monitor["top"],
                    "width": screenshot_region[2] or monitor["width"],
                    "height": screenshot_region[3] or monitor["height"],
                    "mon": screenshot_monitor_id,
                }
                State_change = 1  # 刷新屏幕

    number_var.trace("w", change_screenshot_monitor)
    number_var.set(config_obj.get("number_var", "1"))

    label_screen_number = ttk.Label(screen_frame, text="屏幕编号")
    label_screen_number.grid(row=0, column=0, padx=5)

    number_entry = ttk.Entry(screen_frame, textvariable=number_var, width=4)
    number_entry.grid(row=0, column=1, padx=5, pady=5)

    fps_var = tk.StringVar(root, "100")

    def change_fps(*args):
        global screenshot_limit_fps
        screenshot_limit_fps_tmp = 0
        try:
            screenshot_limit_fps_tmp = int(fps_var.get())
        except ValueError as e:
            if len(fps_var.get()) > 0:
                print("Invalid number entered: %s: %s" % (type(e), e))
        if screenshot_limit_fps_tmp > 0:
            screenshot_limit_fps = screenshot_limit_fps_tmp

    fps_var.trace("w", change_fps)
    fps_var.set(config_obj.get("fps_var", "100"))

    label = ttk.Label(screen_frame, text="最大 FPS")
    label.grid(row=1, column=0, padx=5)

    fps_entry = ttk.Entry(screen_frame, textvariable=fps_var, width=4)
    fps_entry.grid(row=1, column=1, padx=5, pady=5)

    screen_region_var = tk.StringVar(root, "0,0,,")

    def change_screen_region(*args):
        global screenshot_region, cropped_monitor, screenshot_monitor_id, State_change
        try:
            t = tuple((None if x.strip() == "" else int(x)) for x in screen_region_var.get().split(","))
        except ValueError as e:
            if len(screen_region_var.get()) > 0:
                print("screen_region Invalid: %s: %s" % (type(e), e))
            return
        if len(t) != 4:
            print("screen_region Invalid, example: 0,0,160,80")
            return

        screenshot_region = t
        with mss() as sct:
            try:
                monitor = sct.monitors[screenshot_monitor_id]
            except IndexError:
                monitor = sct.monitors[1]
        cropped_monitor = {
            "left": (screenshot_region[0] or 0) + monitor["left"],
            "top": (screenshot_region[1] or 0) + monitor["top"],
            "width": screenshot_region[2] or monitor["width"],
            "height": screenshot_region[3] or monitor["height"],
            "mon": screenshot_monitor_id,
        }
        State_change = 1  # 刷新屏幕

    screen_region_var.trace("w", change_screen_region)
    screen_region_var.set(config_obj.get("screen_region_var", "0,0,,"))

    label = ttk.Label(screen_frame, text="区域：左,上,宽,高")
    label.grid(row=2, column=0, padx=5, columnspan=2)

    screen_region_entry = ttk.Entry(screen_frame, textvariable=screen_region_var, width=14)
    screen_region_entry.grid(row=3, column=0, padx=5, pady=5, columnspan=2)

    update_label_color()

    def on_closing():
        # 结束以后保存配置

        config_obj = {
            "text_color_r": int(text_color_red_scale.get()),
            "text_color_g": int(text_color_green_scale.get()),
            "text_color_b": int(text_color_blue_scale.get()),
            "state_machine": State_machine,
            "lcd_change": LCD_Change_use,
            "number_var": screenshot_monitor_id,
            "fps_var": screenshot_limit_fps,
            "screen_region_var": screen_region_var.get(),
        }

        save_config(config_obj)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # 参数全部获取后再启动截图线程
    screen_shot_thread.start()
    screen_process_thread.start()

    # 进入消息循环
    root.mainloop()


class MSN_Device:  # 定义一个结构体
    def __init__(self, com, version):
        self.com = com  # 登记串口位置
        self.version = version  # 登记MSN版本
        self.name = "MSN"  # 登记设备名称
        # self.baud_rate = 19200  # 登记波特率（没有用到）


My_MSN_Device = []  # 创建一个空的结构体数组


class MSN_Data:  # 定义一个结构体
    def __init__(self, name, unit, family, data):
        self.name = name
        self.unit = unit
        self.family = family
        self.data = data


My_MSN_Data = []  # 创建一个空的结构体数组


def Get_MSN_Device():  # 尝试获取MSN设备
    global Device_State, ADC_det, ser, State_change, machine_model
    global My_MSN_Device, My_MSN_Data, Screen_Error, Label1, Text1
    if Device_State == 1:
        print("取消连接，设备已连接")
        return
    if ser is not None and ser.is_open:
        ser.close()  # 先将异常的串口连接关闭，防止无法打开

    port_list = list(serial.tools.list_ports.comports())  # 查询所有串口
    if len(port_list) == 0:
        print("未检测到串口,请确保设备已连接到电脑")
        # Label1.config(text="设备已连接",bg="GREEN")
        if not MG_daemon_should_stop:
            Label1.config(text="设备未连接", fg="white", bg="RED")
        Device_State = 0  # 未能连接
        time.sleep(1)  # 1秒重新检测一次串口
        return

    # 对串口进行监听，确保其为MSN设备
    My_MSN_Device = []
    My_MSN_Data = []
    for i in range(0, len(port_list)):
        try:  # 尝试打开串口
            # 初始化串口连接,初始使用
            ser = serial.Serial(port_list[i].name, 115200, timeout=10)
        except Exception as e:  # 出现异常
            print("%s 无法打开,请检查是否被其他程序占用: %s" % (port_list[i].name, str(e)))
            if ser.is_open:
                ser.close()  # 将串口关闭，防止下次无法打开
            # time.sleep(0.1)  # 防止频繁重试
            continue  # 尝试下一个端口
        recv = SER_Read()
        if recv == 0:
            print("未接受到设备响应，打开失败：%s" % port_list[i].name)
            ser.close()  # 将串口关闭，防止下次无法打开
            continue  # 尝试下一个端口
        else:
            recv = recv.decode("gbk")  # 获取串口数据

        checkfails = True
        # 逐字解析编码，收到6个字符以上数据时才进行解析
        for n in range(0, len(recv) - 5):
            # 当前字节为0时进行解析，确保为MSN设备，确保版本号为数字ASC码
            if not (ord(recv[n]) == 0 and recv[n + 1: n + 4] == "MSN"
                    and "0" <= recv[n + 4] <= "9" and "0" <= recv[n + 5] <= "9"):
                continue

            # msn_version = (ord(recv[n + 4]) - 48) * 10 + (ord(recv[n + 5]) - 48)
            # 可以逐个加入数组
            hex_code = int(0).to_bytes(1, byteorder="little")
            hex_code = hex_code + b"MSNCN"
            SER_Write(hex_code)  # 返回消息
            # 获取串口数据
            recv = SER_Read().decode("gbk")
            # 确保为MSN设备
            # if ord(recv[0]) == 0 and recv[1] == "M" and recv[2] == "S"
            #     and recv[3] == "N" and recv[4] == "C" and recv[5] == "N":
            if ord(recv[0]) == 0 and recv[1:6] == "MSNCN":
                print("MSN设备%s连接完成" % port_list[i].name)
                # 对MSN设备进行登记
                msn_version = (ord(recv[4]) - 48) * 10 + (ord(recv[5]) - 48)
                msn_dev = MSN_Device(port_list[i].name, msn_version)
                My_MSN_Device.append(msn_dev)
                checkfails = False
                break  # 退出当前for循环
            else:
                print("MSN设备%s无法连接，请检查连接是否正常" % port_list[i].name)

        if checkfails:
            print("设备校验失败：%s" % port_list[i].name)
            ser.close()  # 将串口关闭，防止下次无法打开

    print("MSN设备数量为%d个" % len(My_MSN_Device))  # 显示MSN设备数量
    if len(My_MSN_Device) == 0:
        print("没有找到可用的MSN设备")
        Device_State = 0
        return

    Read_M_SFR_Data(256)  # 读取u8在0x0100之后的128字节
    Print_MSN_Data()  # 解析字节中的数据格式
    if not MG_daemon_should_stop:
        Label1.config(text="设备已连接", fg="white", bg="green")
        Text1.delete(1.0, tk.END)  # 清除文本框
    Device_State = 1  # 可以正常连接
    State_change = 1  # 状态发生变化
    Screen_Error = 0
    # 配置按键阈值
    ADC_det = Read_ADC_CH(9)
    ADC_det = (ADC_det + Read_ADC_CH(9)) / 2
    ADC_det = ADC_det - 125  # 根据125的阈值判断是否被按下
    # Read_MSN_Data(b"MSN_Status")
    # Read_MSN_Data(My_MSN_Data[2].name)
    # UID = Read_MSN_Data(b'MSN_UID')
    # LCD_State(1)#配置显示方向
    # Text1.insert(tk.END,'设备识别码:')

    # Label1=tk.Label(root,text="设备已连接",bg="GREEN")

    # for i in range(1,37):
    #   Write_Flash_Photo_fast(100*(i-1),str(i))#160*80分辨率彩色图片，占用100个Page

    # Write_Flash_Photo_fast(3600,'Demo1')#240*240单色图片，占用29个Page
    # Write_Flash_Photo_fast(3629,'N48X66P')#48*66分辨率数码管图像，占用22个Page

    # Write_Flash_ZK(3651,'ASC64')#32*64分辨率ASCII表格，占用128个Page

    # Write_Flash_Photo_fast(3779,'logo')#240*102单色LOGO,占用12个Page
    # Write_Flash_Photo_fast(3791,'J1')#240*240单色图片，占用29个Page

    # Write_Flash_Photo_fast(3820,'MLOGO')#160*68单色图片，占用6个Page
    # Write_Flash_Photo_fast(3826,'CLK_BG')#160*80彩色图片，占用100个Page
    # Write_Flash_Photo_fast(3926,'PH1')#160*80彩色图片，占用100个Page
    # Write_Flash_Photo_fast(4026,'N24X33P')#24*33分辨率数码管图像，占用12个Page
    # Write_Flash_Photo_fast(4038,'MP1')#160*80单色图片，占用7个Page


last_read_adc_time = datetime.now()
read_adc_timedelta = timedelta(milliseconds=300)


def MSN_Device_1_State_machine():  # MSN设备1的循环状态机
    global machine_model, key_on, State_change, text_color_red_scale, LCD_Change_now, LCD_Change_use
    global text_color_green_scale, text_color_blue_scale, Label2, photo_path1, photo_path2
    global write_path_index, Img_data_use, color_use, rgb_tuple, last_read_adc_time
    # print("State_machine: %s" % State_machine)
    # if write_path==1:
    if LCD_Change_now != LCD_Change_use:  # 显示方向与设置不符合
        LCD_Change_now = LCD_Change_use
        LCD_State(LCD_Change_now)  # 配置显示方向
        State_change = 1

    if write_path != 0:
        if write_path == 1:
            Write_Flash_hex_fast(3826, Img_data_use)
        elif write_path == 2:
            Write_Flash_Photo_fast(0, photo_path2)
        elif write_path == 3:
            Write_Flash_hex_fast(3926, Img_data_use)
        elif write_path == 4:
            Write_Flash_hex_fast(0, Img_data_use)
        write_path = 0
        State_change = 1

    # always use all
    # if State_machine != 5:

    now = datetime.now()
    if now - last_read_adc_time > read_adc_timedelta or key_on == 1:
        last_read_adc_time = now
        if Read_ADC_CH(9) < ADC_det:  # 按键按下时触发动作
            if key_on == 0:
                key_on = 1
                Page_UP()
        elif key_on == 1:  # 按键不再按下
            key_on = 0

    if State_machine == 0:
        show_gif()
    elif State_machine == 1:
        show_PC_state(BLUE, BLACK)
    elif State_machine == 2:
        show_PC_state(color_use, BLACK)
    elif State_machine == 3:
        show_Photo1()
    elif State_machine == 4:
        show_PC_time()
    elif State_machine == 5:
        show_PC_Screen()
    elif State_machine == 3901:
        show_netspeed(text_color=rgb_tuple)
        # import cProfile
        # cProfile.runctx(


# '''
# for i in range(100):
#     show_netspeed(text_color=rgb_tuple)
# ''', globals(), locals())


print("该设备具有%d个内核和%d个逻辑处理器" % (psutil.cpu_count(logical=False), psutil.cpu_count()))
print("该CPU主频为%.1fGHZ" % (psutil.cpu_freq().current / 1000))
print("当前CPU占用率为%s%%" % psutil.cpu_percent())
mem = psutil.virtual_memory()
print("该设备具有%.0fGB的内存" % (mem.total / (1024 * 1024 * 1024)))
print("当前内存占用率为%s%%" % mem.percent)
print("系统开始运行时间%s" % datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"))

battery = psutil.sensors_battery()
if battery is not None:
    print("电池剩余电量%d%%" % battery.percent)
# if battery.power_plugged:
#     print("已连接电源线")
# else:
#     print("已断开电源线")

# 创建定时器,延时为0.2秒
# D = 0
# while(1):
#     D=D+1
#     print(D)
#     time.sleep(0.5)


CPU = 0
FC = BLUE
BC = BLACK
key_on = 0
State_change = 1  # 状态发生变化
Screen_Error = 0
gif_num = 0
machine_model = 3901  # 定义初始状态
Device_State = 0  # 初始为未连接
LCD_Change_use = 0  # 初始显示方向
LCD_Change_now = 0
color_use = RED
rgb_tuple = (0, 0, 0)
write_path_index = 0
photo_path1 = ""
photo_path2 = ""
photo_path3 = ""
photo_path4 = ""

Label1 = None
Label2 = None
Label3 = None
Label4 = None
Label5 = None
Label6 = None
Text1 = None
root = None
text_color_red_scale = None
text_color_green_scale = None
text_color_blue_scale = None
ser = None
ADC_det = 0


def daemon_task():
    global ser

    while True:
        if MG_daemon_should_stop:
            print("stop daemon")
            if ser.is_open:
                ser.close()  # 正常关闭串口
            break
        try:
            # D = D + 1
            # print(D)
            if Device_State == 0:  # 未检测到设备
                Get_MSN_Device()  # 尝试获取MSN设备
            # print("Waiting")
            elif Device_State == 1:  # 已检测到设备
                MSN_Device_1_State_machine()
            # print("OK")
        except Exception as e:  # 出现非预期异常
            print("Exception in daemon_task, %s: %s" % (type(e), e))


# 设备交互只能串行进行，所有的跟设备交互操作必须全部由daemon_thread完成
daemon_thread = threading.Thread(target=daemon_task)
screen_shot_thread = threading.Thread(target=screen_shot_task)
screen_process_thread = threading.Thread(target=screen_process_task)

# tkinter requires the main thread
try:
    daemon_thread.start()  # 尽早启动daemon_thread
    # 打开主页面
    UI_Page()
finally:
    # reap threads
    print("closing")

    MG_screen_thread_running = True
    MG_daemon_should_stop = True
    if screen_shot_thread.is_alive():
        screen_shot_thread.join()
    if screen_process_thread.is_alive():
        screen_process_thread.join()
    if daemon_thread.is_alive():
        daemon_thread.join()

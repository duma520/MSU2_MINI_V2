# -*- coding: UTF-8 -*-
import serial  # 引入串口库（需要额外安装）
import serial.tools.list_ports
import time  # 引入延时库
import threading  # 引入定时回调库
import queue # geezmo: 流水线同步和交换数据用
import json # geezmo: 保存配置用
import psutil  # 引入psutil获取设备信息（需要额外安装）
import os  # 用于读取文件
# import pyautogui  # 用于截图(需要额外安装pillow) geezmo: 已去除依赖
from mss import mss # geezmo: 快速截图
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(2)
except Exception as e:
    print('unable to set dpi awareness, possibly not windows')
    print(e)

from datetime import datetime, timedelta  # 用于获取当前时间
import tkinter as tk # 引入UI库
from tkinter import ttk # geezmo: 好看的皮肤
import tkinter.filedialog  # 用于获取文件路径
from PIL import Image, ImageDraw, ImageFont, ImageTk  # 引入PIL库进行图像处理
import sys  # 用于关闭程序
import numpy as np #使用numpy加速数据处理

MG_daemon_should_stop = False

class MSN_Device:  # 定义一个结构体
    def __init__(self, com, version):
        self.com = com  # 登记串口位置
        self.version = version  # 登记MSN版本
        self.name = 'MSN'  # 登记设备名称
        # self.baud_rate = 19200  # 登记波特率（没有用到）


My_MSN_Device = []  # 创建一个空的结构体数组


class MSN_Data:  # 定义一个结构体
    def __init__(self, name, unit, family, data):
        self.name = name
        self.unit = unit
        self.family = family
        self.data = data


My_MSN_Data = []  # 创建一个空的结构体数组

# 颜色对应的RGB565编码
RED = 0xf800
GREEN = 0x07e0
BLUE = 0x001f
WHITE = 0xffff
BLACK = 0x0000
YELLOW = 0xFFE0
GRAY0 = 0xEF7D
GRAY1 = 0x8410
GRAY2 = 0x4208

hex_code = b''

G_screnn0 = bytearray()  # 空数组
G_screnn1 = bytearray()  # 空数组
Img_data_use = bytearray()  # 空数组
G_screnn0_OK = 0
G_screnn1_OK = 0
size_USE_X1 = 0
size_USE_Y1 = 0

# 参数定义
Show_W = 500  # 显示宽度
Show_H = 350  # 画布高度

# 按键功能定义
def Get_Photo_Path1():  # 获取文件路径
    global photo_path1, Label3
    photo_path1 = tk.filedialog.askopenfilename(title="选择文件",
                                                filetypes=[('Image file', '*.jpg'), ('Image file', '*.jpeg'),
                                                           ('Image file', '*.png'), ('Image file', '*.bmp')])
    Label3.config(text=photo_path1[-20:])

    # photo_path1=photo_path1[:-4]
    # print(photo_path1)


def Get_Photo_Path2():  # 获取文件路径
    global photo_path2, Label4
    photo_path2 = tk.filedialog.askopenfilename(title="选择文件", filetypes=[('Bin file', '*.bin')])
    Label4.config(text=photo_path2[-20:])
    photo_path2 = photo_path2[:-4]
    # print(photo_path2)


def Get_Photo_Path3():  # 获取文件路径
    global photo_path3, Label5  # 支持JPG、PNG、BMP图像格式
    photo_path3 = tk.filedialog.askopenfilename(title="选择文件",
                                                filetypes=[('Image file', '*.jpg'), ('Image file', '*.jpeg'),
                                                           ('Image file', '*.png'), ('Image file', '*.bmp')])
    Label5.config(text=photo_path3[-20:])

    # photo_path3=photo_path3[:-4]
    # print(photo_path3)


def Get_Photo_Path4():  # 获取文件路径
    global photo_path4, Label6
    photo_path4 = tk.filedialog.askopenfilename(title="选择文件",
                                                filetypes=[('Image file', '*.jpg'), ('Image file', '*.jpeg'),
                                                           ('Image file', '*.png'), ('Image file', '*.bmp')])
    Label6.config(text=photo_path4[-20:])

    # photo_path4=photo_path4[:-4]
    # print(photo_path4)


def Writet_Photo_Path1():  # 写入文件
    global photo_path1, write_path1, Text1, Img_data_use
    if write_path1 == 0:  # 确保上次执行写入完毕
        Text1.delete(1.0, tk.END)  # 清除文本框
        Text1.insert(tk.END, '图像格式转换...\n')  # 在文本框开始位置插入“内容一”
        im1 = Image.open(photo_path1)
        if im1.width >= (im1.height * 2):  # 图片长宽比例超过2:1
            im2 = im1.resize((int(80 * im1.width / im1.height), 80))
            Img_m = int(im2.width / 2)
            box = ((Img_m - 80, 0, Img_m + 80, 80))  # 定义需要裁剪的空间
            im2 = im2.crop(box)
        else:
            im2 = im1.resize((160, int(160 * im1.height / im1.width)))
            Img_m = int(im2.height / 2)
            box = ((0, Img_m - 40, 160, Img_m + 40))  # 定义需要裁剪的空间
            im2 = im2.crop(box)
        im2 = im2.convert('RGB')  # 转换为RGB格式
        Img_data_use = bytearray()  # 空数组
        for y in range(0, 80):  # 逐字解析编码
            for x in range(0, 160):  # 逐字解析编码
                r, g, b = im2.getpixel((x, y))
                Img_data_use.append(((r >> 3) << 3) | (g >> 5))
                Img_data_use.append((((g % 32) >> 2) << 5) | (b >> 3))
        write_path1 = 1


def Writet_Photo_Path2():  # 写入文件
    global photo_path2, write_path2, Text1
    if write_path2 == 0:  # 确保上次执行写入完毕
        write_path2 = 1
        Text1.delete(1.0, tk.END)  # 清除文本框
        Text1.insert(tk.END, '准备烧写Flash固件...\n')  # 在文本框开始位置插入“内容一”


def Writet_Photo_Path3():  # 写入文件
    global photo_path3, write_path3, Text1, Img_data_use
    if write_path3 == 0:  # 确保上次执行写入完毕
        Text1.delete(1.0, tk.END)  # 清除文本框
        Text1.insert(tk.END, '图像格式转换...\n')  # 在文本框开始位置插入“内容一”

        im1 = Image.open(photo_path3)
        if im1.width >= (im1.height * 2):  # 图片长宽比例超过2:1
            im2 = im1.resize((int(80 * im1.width / im1.height), 80))
            Img_m = int(im2.width / 2)
            box = ((Img_m - 80, 0, Img_m + 80, 80))  # 定义需要裁剪的空间
            im2 = im2.crop(box)
        else:
            im2 = im1.resize((160, int(160 * im1.height / im1.width)))
            Img_m = int(im2.height / 2)
            box = ((0, Img_m - 40, 160, Img_m + 40))  # 定义需要裁剪的空间
            im2 = im2.crop(box)
        im2 = im2.convert('RGB')  # 转换为RGB格式
        Img_data_use = bytearray()  # 空数组
        for y in range(0, 80):  # 逐字解析编码
            for x in range(0, 160):  # 逐字解析编码
                r, g, b = im2.getpixel((x, y))
                Img_data_use.append(((r >> 3) << 3) | (g >> 5))
                Img_data_use.append((((g % 32) >> 2) << 5) | (b >> 3))
        write_path3 = 1

        # print(img_use)

        # im2.show()
        # Text1.insert(tk.END,'准备烧写背景图像...\n')#在文本框开始位置插入“内容一”


def Writet_Photo_Path4():  # 写入文件
    global photo_path4, write_path4, Text1, Img_data_use
    if write_path4 == 0:  # 确保上次执行写入完毕
        Text1.delete(1.0, tk.END)  # 清除文本框
        Text1.insert(tk.END, '动图格式转换中...\n')  # 在文本框开始位置插入“内容一”
        time.sleep(0.1)
        Path_use = photo_path4
        if Path_use[-4] == '.':  #
            write_path4 = Path_use[-4:]
            Path_use = Path_use[:-5]

        elif Path_use[-5] == '.':
            write_path4 = Path_use[-5:]
            Path_use = Path_use[:-6]
        else:
            Text1.insert(tk.END, '动图名称不符合要求！\n')  # 在文本框开始位置插入“内容一”
            return  # 如果文件名不符合要求，直接返回

        Img_data_use = bytearray()
        u_time = time.time()
        for i in range(0, 36):  # 依次转换36张图片
            file_path = Path_use + str(i) + write_path4
            if not os.path.exists(file_path):  # 检查文件是否存在
                Text1.insert(tk.END, '缺少动图文件：' + file_path + '\n')
                return  # 如果文件不存在，直接返回，不执行后续代码

            im1 = Image.open(file_path)
            if im1.width >= (im1.height * 2):  # 图片长宽比例超过2:1
                im2 = im1.resize((int(80 * im1.width / im1.height), 80))
                Img_m = int(im2.width / 2)
                box = ((Img_m - 80, 0, Img_m + 80, 80))  # 定义需要裁剪的空间
                im2 = im2.crop(box)
            else:
                im2 = im1.resize((160, int(160 * im1.height / im1.width)))
                Img_m = int(im2.height / 2)
                box = ((0, Img_m - 40, 160, Img_m + 40))  # 定义需要裁剪的空间
                im2 = im2.crop(box)
            im2 = im2.convert('RGB')  # 转换为RGB格式
            for y in range(0, 80):  # 逐字解析编码
                for x in range(0, 160):  # 逐字解析编码
                    r, g, b = im2.getpixel((x, y))
                    Img_data_use.append(((r >> 3) << 3) | (g >> 5))
                    Img_data_use.append((((g % 32) >> 2) << 5) | (b >> 3))

        u_time = time.time() - u_time
        u_time = int(u_time * 1000)
        Text1.insert(tk.END, '转换完成,耗时' + str(u_time) + 'ms\n')  # 在文本框开始位置插入“内容一”
        write_path4 = 1
    else:
        Text1.insert(tk.END, '转换失败' + 'ms\n')  # 在文本框开始位置插入“内容一”


# geezmo: 禁用的模式，以免有些组件没加载好，就跳过这些模式
banned_states = []

def Page_UP():  # 上一页
    global State_change, State_machine
    State_machine = State_machine + 1
    State_change = 1
    if State_machine > 5:
        if State_machine == 6:
            State_machine = 3901
        elif State_machine == 3904:
            State_machine = 0
    if State_machine in banned_states:
        Page_UP()
    print("Current state changed to: " + str(State_machine))



def Page_Down():  # 下一页
    global State_change, State_machine
    State_machine = State_machine - 1
    State_change = 1
    if State_machine < 0:
        State_machine = 3903
    if State_machine == 3900:
        State_machine = 5
    if State_machine in banned_states:
        Page_Down()
    print("Current state changed to: " + str(State_machine))

# State_change = 0  # 全局变量初始化
# def now_the_state_machine():
#     if State_change == 1:
#         print(str(State_machine))
#
# now_the_state_machine()


def LCD_Change():  # 切换显示方向
    global LCD_Change_use
    LCD_Change_use = LCD_Change_use + 1
    if LCD_Change_use > 1:  # 限制切换模式
        LCD_Change_use = 0


def SER_Write(Data_U0):
    global Device_State
    # print('发送数据ing');
    try:  # 尝试发出指令,有两种无法正确发送命令的情况：1.设备被移除,发送出错；2.设备处于MSN连接状态，对于电脑发送的指令响应迟缓
        # 进行超时检测
        # u_time=time.time()
        if (False == ser.is_open):
            Device_State = 0  # 恢复到未连接状态
        ser.write(Data_U0)
        # print(Data_U0)
        # u_time=time.time()-u_time
        # if u_time>2:
        # print('发送超时');
        # Device_State=0#恢复到未连接状态
        # ser.close()#将串口关闭，防止下次无法打开
        # else:
        # print('发送完成');
    except:  # 出现异常
        # print('发送异常');
        Device_State = 0
        ser.close()  # 将串口关闭，防止下次无法打开


def SER_Read():
    global Device_State
    # print('接收数据ing');
    try:  # 尝试获取数据
        Data_U1 = ser.read(ser.in_waiting)
        return Data_U1
    except:  # 出现异常
        # print('接收异常');
        Device_State = 0
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
    while (1):
        recv = SER_Read()  # .decode("byte")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
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
    while (1):
        recv = SER_Read()  # .decode("gbk")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
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
    while (1):
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            break
            # return recv[5]


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
    while (1):
        recv = SER_Read()  # .decode("gbk")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            break


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
    while (1):
        recv = SER_Read()  # .decode("gbk")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            return recv[4] * 256 + recv[5]


def Read_M_SFR_Data(add):  # 从u8区域获取SFR描述
    SFR_data = bytearray()  # 空数组
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        SFR_data.append(Read_M_u8(add + i))  # 读取编码数据
    data_type = 0  # 根据是否为0进行类型循环统计
    data_num = 0
    data_len = 0
    data_use = bytearray()  # 空数组
    data_name = b''
    data_unit = b''
    data_family = b''
    data_data = b''
    for i in range(0, 256):  # 以128字节为单位进行解析编码
        if (SFR_data[i] != 0 and data_type < 3):
            data_use.append(SFR_data[i])  # 将非0数据合并到一块
        elif (data_type < 3):  # 检测到0且未超纲
            if (len(data_use) == 0):  # 没有接收到数据时就接收到00
                break  # 检测到0后收集的数据为空，判断为结束
            if (data_type == 0):
                data_name = data_use  # 名称
                data_type = 1
            elif (data_type == 1):
                data_unit = data_use  # 单位
                data_type = 2
            elif (data_type == 2):
                data_family = data_use  # 类型
                data_type = 3
                if (int(ord(data_use) // 32) == 0):  # u8 data 2B add
                    data_len = 2
                elif (int(ord(data_use) // 32) == 1):  # u16 data 1B add
                    data_len = 1
                elif (int(ord(data_use) // 32) == 2):  # u32 data 2B add
                    data_len = 2
                elif (int(ord(data_use) // 32) == 3):  # u8 Text XB data
                    data_len = data_family[0] % 32  # 计算数据长度
            data_use = bytearray()  # 空数组
            continue  # 进行下一次循环
        if (data_len > 0 and data_type == 3):  # 正式的有效数据
            data_use.append(SFR_data[i])  # 将非0数据合并到一块
            data_len = data_len - 1
        if (data_len == 0 and data_type == 3):  # 将后续数据收集完整
            data_data = data_use
            data_type = 0  # 重置类型
            My_MSN_Data.append(MSN_Data(data_name, data_unit, data_family, data_data))  # 对数据进行登记
            data_use = bytearray()  # 空数组


def Print_MSN_Data():
    num = len(My_MSN_Data)
    data_str = ''
    print('MSN数据总数为：' + str(num))
    # 进行数据解析
    for i in range(0, num):  # 将数据全部打印出来
        data_str = data_str + '序号：' + str(i) + '    名称：' + str(My_MSN_Data[i].name) + '    单位:' + str(
            My_MSN_Data[i].unit)
        if (ord(My_MSN_Data[i].family) // 32 == 0):  # 数据类型为u8地址(16bit)
            data_str = data_str + '    类型：u8_SFR地址,长度' + str(ord(My_MSN_Data[i].family) % 32)
            data_str = data_str + '    地址：' + str(int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1]))
        elif (ord(My_MSN_Data[i].family) // 32 == 1):  # 数据类型为u16地址(8bit)
            data_str = data_str + '    类型：u16_SFR地址,长度' + str(ord(My_MSN_Data[i].family) % 32)
            data_str = data_str + '    地址：' + str(int(My_MSN_Data[i].data[0]))
        elif (ord(My_MSN_Data[i].family) // 32 == 2):  # 数据类型为u32地址(16bit)
            data_str = data_str + '    类型：u32_SFR地址,长度：' + str(ord(My_MSN_Data[i].family) % 32)
            data_str = data_str + '    地址：' + str(int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1]))
        elif (ord(My_MSN_Data[i].family) // 32 == 3):  # 数据类型为u8字符串
            data_str = data_str + '    类型：字符串,长度' + str(ord(My_MSN_Data[i].family) % 32)
            data_str = data_str + '    数据：' + str(My_MSN_Data[i].data)
        elif (ord(My_MSN_Data[i].family) // 32 == 4):  # 数据类型为u8数组
            data_str = data_str + '    类型：u8数组数据,长度' + str(int(My_MSN_Data[i].family) % 32)
            data_str = data_str + '    数据：' + str(My_MSN_Data[i].data)
        print(data_str)
        data_str = ''


def Read_MSN_Data(name_use):  # 读取MSN_data中的数据
    num = len(My_MSN_Data)
    use_data = []  # 创建一个空列表
    for i in range(0, num):  # 将数据查找一遍
        if (My_MSN_Data[i].name == name_use):
            if (ord(My_MSN_Data[i].family) // 32 == 0):  # 数据类型为u8地址(16bit)
                sfr_add = int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1])
                for n in range(0, ord(My_MSN_Data[i].family) % 32):
                    use_data.append(Read_M_u8(sfr_add + n))
            elif (ord(My_MSN_Data[i].family) // 32 == 1):  # 数据类型为u16地址(8bit)
                use_data = Read_M_u16(int(My_MSN_Data[i].data[0]))
            elif (ord(My_MSN_Data[i].family) // 32 == 3):  # 数据类型为u8字符串
                use_data = My_MSN_Data[i].data
            elif (ord(My_MSN_Data[i].family) // 32 == 4):  # 数据类型为u8数组
                use_data = My_MSN_Data[i].data
            print(str(My_MSN_Data[i].name) + '=' + str(use_data))
            return use_data
    if name_use != 0:
        print('"' + name_use + '"' + '不存在,请检查名称是否正确')
    return 0


def Write_MSN_Data(name_use, data_w):  # 在MSN_data写入数据
    num = len(My_MSN_Data)
    for i in range(0, num):  # 将数据查找一遍
        if (My_MSN_Data[i].name == name_use):
            if (int(My_MSN_Data[i].family) // 32 == 0):  # 数据类型为u8地址(16bit)
                Write_M_u8(int(My_MSN_Data[i].data[0]) * 256 + int(My_MSN_Data[i].data[1]), data_w)
                print('"' + name_use + '"' + '写入' + str(data_w) + '完成')
                return 0
            elif (int(My_MSN_Data[i].family) // 32 == 1):  # 数据类型为u16地址(8bit)
                Write_M_u16(int(My_MSN_Data[i].data[0]), data_w)
                print('"' + name_use + '"' + '写入' + str(data_w) + '完成')
                return 0
    print('"' + name_use + '"' + '不存在,请检查名称是否正确')


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
        SER_Write(hex_use)  # 发出指令
    hex_use = bytearray()  # 空数组
    hex_use.append(3)  # 对Flash操作
    hex_use.append(1)  # 写Flash
    hex_use.append(Page_add // (65536))  # Data0
    hex_use.append((Page_add % 65536) // 256)  # Data1
    hex_use.append((Page_add % 65536) % 256)  # Data2
    hex_use.append(Page_num % 256)  # Data3
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    while (1):
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            break


def Write_Flash_Page_fast(Page_add, data_w, Page_num):  # 未经过擦除，直接往Flash指定页写入256B数据
    # 先把数据传输完成
    hex_use = b''
    for i in range(0, 64):  # 256字节数据分为64个指令
        hex_use = hex_use + int(4).to_bytes(1, byteorder="little")  # 多次写入Flash
        hex_use = hex_use + int(i).to_bytes(1, byteorder="little")  # 低位地址
        hex_use = hex_use + data_w[i * 4 + 0].to_bytes(1, byteorder="little")  # Data0
        hex_use = hex_use + data_w[i * 4 + 1].to_bytes(1, byteorder="little")  # Data1
        hex_use = hex_use + data_w[i * 4 + 2].to_bytes(1, byteorder="little")  # Data2
        hex_use = hex_use + data_w[i * 4 + 3].to_bytes(1, byteorder="little")  # Data3
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 对Flash操作
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 经过擦除，写Flash
    hex_use = hex_use + int(Page_add // (256 * 256)).to_bytes(1, byteorder="little")  # Data0
    hex_use = hex_use + int((Page_add % 65536) // 256).to_bytes(1, byteorder="little")  # Data1
    hex_use = hex_use + int((Page_add % 65536) % 256).to_bytes(1, byteorder="little")  # Data2
    hex_use = hex_use + int(Page_num).to_bytes(1, byteorder="little")  # Data3
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    while (1):
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            break


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
    while (1):
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            break


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
    while (1):
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            print(recv[5])
            return recv[5]


def Write_Flash_Photo_fast(Page_add, Photo_name):  # 往Flash里面写入Bin格式的照片
    global Text1
    filepath = Photo_name + '.bin'  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, 'rb')  # 以只读方式打开
    except:  # 出现异常
        print('找不到“' + filepath + '”文件,请检查其位置是否位于当前目录下')
        # Text1.delete(1.0,tk.END)#清除文本框
        Text1.insert(tk.END, '文件路径或格式出错!\n')  # 在文本框开始位置插入“内容一”
        return 0
    Fsize = os.path.getsize(filepath)
    print('找到“' + filepath + '”文件,大小：' + str(Fsize) + ' B')
    Text1.insert(tk.END, '大小' + str(Fsize) + 'B,烧录中...\n')  # 在文本框开始位置插入“内容一”
    u_time = time.time()
    # 进行擦除
    if (Fsize % 256 != 0):
        Erase_Flash_page(Page_add, Fsize // 256 + 1)  # 清空指定区域的内存
    else:
        Erase_Flash_page(Page_add, Fsize // 256)  # 清空指定区域的内存

    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = binfile.read(256)
        Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if (Fsize % 256 != 0):  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page_fast(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    u_time = time.time() - u_time
    print(filepath + ' 烧写完成,耗时' + str(u_time) + '秒')
    Text1.insert(tk.END, '烧写完成,耗时' + str(int(u_time * 1000)) + 'ms\n')  # 在文本框开始位置插入“内容一”


def Write_Flash_hex_fast(Page_add, img_use):  # 往Flash里面写入hex数据
    Fsize = len(img_use)
    Text1.insert(tk.END, '大小' + str(Fsize) + 'B,烧录中...\n')  # 在文本框开始位置插入“内容一”
    u_time = time.time()
    # 进行擦除
    if (Fsize % 256 != 0):
        Erase_Flash_page(Page_add, Fsize // 256 + 1)  # 清空指定区域的内存
    else:
        Erase_Flash_page(Page_add, Fsize // 256)  # 清空指定区域的内存
    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = img_use[:256]  # 取前256字节
        img_use = img_use[256:]  # 取剩余字节
        Write_Flash_Page_fast(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if (Fsize % 256 != 0):  # 还存在没写完的数据
        Fdata = img_use  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page_fast(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    u_time = time.time() - u_time
    Text1.insert(tk.END, '烧写完成,耗时' + str(int(u_time * 1000)) + 'ms\n')  # 在文本框开始位置插入“内容一”


def Write_Flash_ZK(Page_add, ZK_name):  # 往Flash里面写入Bin格式的字库
    filepath = ZK_name + '.bin'  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, 'rb')  # 以只读方式打开
    except:  # 出现异常
        print('找不到“' + filepath + '”文件,请检查其位置是否位于当前目录下')
        return 0
    Fsize = os.path.getsize(filepath) - 6  # 字库文件的最后六个字节不是点阵信息
    print('找到“' + filepath + '”文件,大小：' + str(Fsize) + ' B')
    for i in range(0, Fsize // 256):  # 每次写入一个Pag
        Fdata = binfile.read(256)
        Write_Flash_Page(Page_add + i, Fdata, 1)  # (page,数据，大小)
    if (Fsize % 256 != 0):  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        Write_Flash_Page(Page_add + Fsize // 256, Fdata, 1)  # (page,数据，大小)
    print(filepath + ' 烧写完成')


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
    while (1):
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


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
    while (1):
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break
        time.sleep(0.001)


def LCD_State(LCD_S):  #
    global Device_State
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(10).to_bytes(1, byteorder="little")  # 载入地址
    hex_use = hex_use + int(LCD_S).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    while (1):
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


def LCD_DATA(data_w, size):  # 往LCD写入指定大小的数据
    # 先把数据传输完成
    hex_use = b''
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


def Write_LCD_Photo_fast(x_star, y_star, x_size, y_size, Photo_name):  # 往Flash里面写入Bin格式的照片
    filepath = Photo_name + '.bin'  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, 'rb')  # 以只读方式打开
    except:  # 出现异常
        print('找不到“' + filepath + '”文件,请检查其位置是否位于当前目录下')
        return 0
    Fsize = os.path.getsize(filepath)
    print('找到“' + filepath + '”文件,大小：' + str(Fsize) + ' B')
    u_time = time.time()
    # 进行地址写入
    LCD_ADD(x_star, y_star, x_size, y_size)
    for i in range(0, Fsize // 256):  # 每次写入一个Page
        Fdata = binfile.read(256)
        LCD_DATA(Fdata, 256)  # (page,数据，大小)
    if (Fsize % 256 != 0):  # 还存在没写完的数据
        Fdata = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            Fdata = Fdata + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
        LCD_DATA(Fdata, Fsize % 256)  # (page,数据，大小)
    u_time = time.time() - u_time
    print(filepath + ' 显示完成,耗时' + str(u_time) + '秒')


def Write_LCD_Photo_fast1(x_star, y_star, x_size, y_size, Photo_name):  # 往Flash里面写入Bin格式的照片
    filepath = Photo_name + '.bin'  # 合成文件名称
    try:  # 尝试打开bin文件
        binfile = open(filepath, 'rb')  # 以只读方式打开
    except:  # 出现异常
        print('找不到“' + filepath + '”文件,请检查其位置是否位于当前目录下')
        return 0
    Fsize = os.path.getsize(filepath)
    print('找到“' + filepath + '”文件,大小：' + str(Fsize) + ' B')
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
    if (Fsize % 256 != 0):  # 还存在没写完的数据
        data_w = binfile.read(Fsize % 256)  # 将剩下的数据读完
        for i in range(Fsize % 256, 256):
            data_w = data_w + int(255).to_bytes(1, byteorder="little")  # 不足位置补充0xFF
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
    print(filepath + ' 显示完成,耗时' + str(u_time) + '秒')


def Write_LCD_Screen_fast(x_star, y_star, x_size, y_size, Photo_data):  # 往Flash里面写入Bin格式的照片
    LCD_ADD(x_star, y_star, x_size, y_size)
    Photo_data_use = Photo_data
    hex_use = bytearray()  # 空数组
    for j in range(0, x_size * y_size * 2 // 256):  # 每次写入一个Page
        data_w = Photo_data_use[:256]
        Photo_data_use = Photo_data_use[256:]
        cmp_use = []  # 空数组,
        for i in range(0, 64):  # 256字节数据分为64个指令
            cmp_use.append(
                data_w[i * 4 + 0] * 256 * 256 * 256 + data_w[i * 4 + 1] * 256 * 256 + data_w[i * 4 + 2] * 256 + data_w[
                    i * 4 + 3])
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
            if ((data_w[i * 4 + 0] * 256 * 256 * 256 + data_w[i * 4 + 1] * 256 * 256 + data_w[i * 4 + 2] * 256 + data_w[
                i * 4 + 3]) != result):  #
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
    if (x_size * y_size * 2 % 256 != 0):  # 还存在没写完的数据
        data_w = Photo_data_use  # 将剩下的数据读完
        for i in range(x_size * y_size * 2 % 256, 256):
            data_w.append(0xff)  # 不足位置补充0xFF
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


# 对发送的数据进行编码分析,缩短数据指令
def Write_LCD_Screen_fast1(x_star, y_star, x_size, y_size, Photo_data):  # 往Flash里面写入Bin格式的照片
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
    if (x_size * y_size * 2 % 256 != 0):  # 还存在没写完的数据
        data_w = Photo_data_use  # 将剩下的数据读完
        for i in range(x_size * y_size * 2 % 256, 256):
            data_w.append(0xff)  # 不足位置补充0xFF
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


def LCD_Photo_wb(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add, LCD_FC, LCD_BC):  #
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
    while (1):
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):  # 对于回传的数据需要进行校验，确保设备状态能够被准确识别到
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


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
    while (1):
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


def LCD_GB2312_16X16(LCD_X, LCD_Y, Txt, LCD_FC, LCD_BC):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, LCD_BC)
    Txt_Data = Txt.encode('gb2312')
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 显示彩色图片
    hex_use = hex_use + int(Txt_Data[0]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Txt_Data[1]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    while (1):
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


def LCD_Photo_wb_MIX(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, Page_Add, LCD_FC, BG_Page):  #
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
    while (1):
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


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
    while (1):
        # time.sleep(0.5)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


def LCD_GB2312_16X16_MIX(LCD_X, LCD_Y, Txt, LCD_FC, BG_Page):  #
    global Device_State
    LCD_Set_XY(LCD_X, LCD_Y)
    LCD_Set_Color(LCD_FC, BG_Page)
    Txt_Data = Txt.encode('gb2312')
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(3).to_bytes(1, byteorder="little")  # 设置指令
    hex_use = hex_use + int(6).to_bytes(1, byteorder="little")  # 显示彩色图片
    hex_use = hex_use + int(Txt_Data[0]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(Txt_Data[1]).to_bytes(1, byteorder="little")
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")
    SER_Write(hex_use)  # 发出指令
    # 等待收回信息
    while (1):
        time.sleep(0.2)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


def LCD_Color_set(LCD_X, LCD_Y, LCD_X_Size, LCD_Y_Size, F_Color):  # 对指定区域进行颜色填充
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
    while (1):
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break


def show_gif():  # 显示GIF动图
    global State_change, gif_num
    if (State_change == 1):
        State_change = 0
        gif_num = 0
    if (State_change == 0):
        LCD_Photo(0, 0, 160, 80, gif_num * 100)
        gif_num = gif_num + 1
        if (gif_num > 35):
            gif_num = 0

    time.sleep(0.05)
    # LCD_Color_set(40,0,80,80,RED)


def show_PC_state(FC, BC):  # 显示PC状态
    global State_change
    photo_add = 4038
    num_add = 4026
    if (State_change == 1):
        State_change = 0
        LCD_Photo_wb(0, 0, 160, 80, photo_add, FC, BC)  # 放置背景
    if (State_change == 0):
        CPU = int(psutil.cpu_percent(interval=0.5))
        mem = psutil.virtual_memory()
        RAM = int(mem.percent)

        battery = psutil.sensors_battery()
        if battery != None:
            BAT = int(battery.percent)
        else:
            BAT = 100
        FRQ = int(psutil.disk_usage('/').used * 100 / psutil.disk_usage('/').total)
        if (CPU >= 100):
            LCD_Photo_wb(24, 0, 8, 33, 10 + num_add, FC, BC)
            CPU = CPU % 100
        else:
            LCD_Photo_wb(24, 0, 8, 33, 11 + num_add, FC, BC)
        LCD_Photo_wb(32, 0, 24, 33, (CPU // 10) + num_add, FC, BC)
        LCD_Photo_wb(56, 0, 24, 33, (CPU % 10) + num_add, FC, BC)
        if (RAM >= 100):
            LCD_Photo_wb(104, 0, 8, 33, 10 + num_add, FC, BC)
            RAM = RAM % 100
        else:
            LCD_Photo_wb(104, 0, 8, 33, 11 + num_add, FC, BC)
        LCD_Photo_wb(112, 0, 24, 33, (RAM // 10) + num_add, FC, BC)
        LCD_Photo_wb(136, 0, 24, 33, (RAM % 10) + num_add, FC, BC)
        if (BAT >= 100):
            LCD_Photo_wb(104, 47, 8, 33, 10 + num_add, FC, BC)
            BAT = BAT % 100
        else:
            LCD_Photo_wb(104, 47, 8, 33, 11 + num_add, FC, BC)
        LCD_Photo_wb(112, 47, 24, 33, (BAT // 10) + num_add, FC, BC)
        LCD_Photo_wb(136, 47, 24, 33, (BAT % 10) + num_add, FC, BC)

        if (FRQ >= 100):
            LCD_Photo_wb(24, 47, 8, 33, 10 + num_add, FC, BC)
            FRQ = FRQ % 100
        else:
            LCD_Photo_wb(24, 47, 8, 33, 11 + num_add, FC, BC)
        LCD_Photo_wb(32, 47, 24, 33, (FRQ // 10) + num_add, FC, BC)
        LCD_Photo_wb(56, 47, 24, 33, (FRQ % 10) + num_add, FC, BC)


def show_Photo1():  # 显示照片
    global State_change
    FC = BLUE
    BC = BLACK
    if (State_change == 1):
        State_change = 0
        LCD_Photo(0, 0, 160, 80, 3926)  # 放置背景
    if (State_change == 0):
        time.sleep(0.2)


def show_PC_time():
    global State_change
    FC = color_use
    photo_add = 3826
    num_add = 3651
    if (State_change == 1):
        State_change = 0
        LCD_Photo(0, 0, 160, 80, photo_add)  # 放置背景
        # while(1):
        #    time.sleep(1)
        LCD_ASCII_32X64_MIX(56 + 8, 8, ':', FC, photo_add, num_add)
        # LCD_ASCII_32X64_MIX(136+8,32,':',FC,photo_add,num_add)
    if (State_change == 0):
        time_h = int(datetime.now().hour)
        time_m = int(datetime.now().minute)
        time_S = int(datetime.now().second)
        LCD_ASCII_32X64_MIX(0 + 8, 8, chr((time_h // 10) + 48), FC, photo_add, num_add)
        LCD_ASCII_32X64_MIX(32 + 8, 8, chr((time_h % 10) + 48), FC, photo_add, num_add)
        LCD_ASCII_32X64_MIX(80 + 8, 8, chr((time_m // 10) + 48), FC, photo_add, num_add)
        LCD_ASCII_32X64_MIX(112 + 8, 8, chr((time_m % 10) + 48), FC, photo_add, num_add)
        # LCD_ASCII_32X64_MIX(160+8,8,chr((time_S//10)+48),FC,photo_add,num_add)
        # LCD_ASCII_32X64_MIX(192+8,8,chr((time_S%10)+48),FC,photo_add,num_add)
        time.sleep(0.2)


def Screen_Date_Process(Photo_data):  # 对数据进行转换处理
    uint16_data = Photo_data.astype(np.uint32)
    hex_use = bytearray()  # 空数组
    total_data_size = size_USE_X1 * size_USE_Y1
    data_per_page = 128
    for j in range(0, total_data_size // data_per_page):  # 每次写入一个Page
        data_w = uint16_data[j * data_per_page:(j + 1) * data_per_page]
        
        cmp_use = data_w[::2] << 16 | data_w[1::2]  # 256字节数据分为64个指令
        u, c = np.unique(cmp_use, return_counts=True)
        result = u[c.argmax()] # 找最频繁的指令
        
        hex_use.extend([2, 4])

        # 最常见的指令，背景色？
        hex_use.extend([
            (result >> 24) & 0xFF,
            (result >> 16) & 0xFF,
            (result >> 8) & 0xFF,
            result & 0xFF
        ])
        # 每个前景色
        for i, cmp_value in enumerate(cmp_use):
            if cmp_value != result:
                hex_use.extend([
                    4, i,
                    (cmp_value >> 24) & 0xFF,
                    (cmp_value >> 16) & 0xFF,
                    (cmp_value >> 8) & 0xFF,
                    cmp_value & 0xFF
                ])

        # Append footer
        hex_use.extend([2, 3, 8, 1, 0, 0])
    remaining_data_size = total_data_size % data_per_page
    if (remaining_data_size != 0):  # 还存在没写完的数据
        data_w = uint16_data[-remaining_data_size:] # 取最后的没有写的
        data_w += b'\xff\xff' * (128 - remaining_data_size) # 补全128个 uint16
        cmp_use = data_w[::2] << 16 | data_w[1::2]
        for i in range(0, 64):
            cmp_value = cmp_use[i]
            hex_use.extend([
                4, i,
                (cmp_value >> 24) & 0xFF,
                (cmp_value >> 16) & 0xFF,
                (cmp_value >> 8) & 0xFF,
                cmp_value & 0xFF
            ])
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
    new_shape = (
        int(image.shape[0] / shrink_factor),
        int(image.shape[1] / shrink_factor)
    )

    shrunk_parts = []
    # 4倍多重采样
    for rand in [
        (0.0, 0.0), (0.25, 0.5), (0.5, 0.25), (0.75, 0.75)
    ]:
        row_indices = np.round(np.linspace(0 + shrink_factor * rand[0], image.shape[0] - 1 - shrink_factor * (1 - rand[0]), new_shape[0])).astype(np.uint32)
        col_indices = np.round(np.linspace(0 + shrink_factor * rand[1], image.shape[1] - 1 - shrink_factor * (1 - rand[1]), new_shape[1])).astype(np.uint32)

        # Handle color and grayscale images
        if image.ndim == 3:
            shrunk_image = image[np.ix_(row_indices, col_indices, np.arange(image.shape[2]))]
        else:
            shrunk_image = image[np.ix_(row_indices, col_indices)]
        shrunk_parts.append(shrunk_image)
    
    return np.mean(shrunk_parts, axis=0, dtype=np.uint32)
    
    
    # 下面的算法可以用（每块所有像素平均），但是慢，所以用上面的简单算法，取少数几个点
    
    # Calculate integer block size for averaging
    block_size = int(np.floor(shrink_factor))

    # Calculate the shape after block averaging
    new_shape = (
        image.shape[0] // block_size,
        image.shape[1] // block_size
    )

    # Perform block averaging
    if image.ndim == 3:  # Color image
        averaged_image = image.reshape(
            new_shape[0], block_size, new_shape[1], block_size, image.shape[2]
        ).mean(axis=(1, 3), dtype=np.uint32)
    else:  # Grayscale image
        averaged_image = image.reshape(
            new_shape[0], block_size, new_shape[1], block_size
        ).mean(axis=(1, 3), dtype=np.uint32)

    # Nearest neighbor interpolation to handle fractional part
    final_shape = (
        int(image.shape[0] / shrink_factor),
        int(image.shape[1] / shrink_factor)
    )

    row_indices = np.round(np.linspace(0, averaged_image.shape[0] - 1, final_shape[0])).astype(np.uint32)
    col_indices = np.round(np.linspace(0, averaged_image.shape[1] - 1, final_shape[1])).astype(np.uint32)

    # Handle color and grayscale images
    if image.ndim == 3:
        shrunk_image = averaged_image[np.ix_(row_indices, col_indices, np.arange(image.shape[2]))].astype(np.uint8)
    else:
        shrunk_image = averaged_image[np.ix_(row_indices, col_indices)].astype(np.uint8)

    return shrunk_image


MG_screen_thread_should_stop = False
screen_shot_queue = queue.Queue(2)
screenshot_monitor_id = 1
screen_process_queue = queue.Queue(2)

screenshot_region = (None,None,None,None)
def screen_shot_task():  # 创建专门的函数来获取屏幕图像和处理转换数据
    print("截图线程创建成功")
    with mss() as sct:
        monitor = sct.monitors[screenshot_monitor_id]
        screen_width = screenshot_region[2] or monitor['width']
        screen_height = screenshot_region[3] or monitor['height']
        while True:
            try:
                monitor = sct.monitors[screenshot_monitor_id]
            except IndexError:
                monitor = sct.monitors[1]
            cropped_monitor = {
                'top': monitor['top'] + (screenshot_region[0] or 0),
                'left': monitor['left'] + (screenshot_region[1] or 0),
                'width': screenshot_region[2] or monitor['width'],
                'height': screenshot_region[3] or monitor['height'],
                'mon': screenshot_monitor_id
            }
            print(sct.monitors)
            sct_img = sct.grab(cropped_monitor) # geezmo: 截屏已优化
            try:
                screen_shot_queue.put((sct_img, cropped_monitor), timeout=3)
            except queue.Full:
                # 每1s检测一次退出，并且如果下游不拿走，则重新截图
                pass
            if MG_screen_thread_should_stop:
                print('stop screenshot')
                break # exit screenshot thread

# geezmo: 流水线 第二步 处理图像
def screen_process_task():
    while True:
        try:
            sct_img, monitor = screen_shot_queue.get(timeout=3)
        except queue.Empty:
            # 每1s检测一次退出
            if MG_screen_thread_should_stop:
                print('stop screen process')
                break # exit screenshot thread
    
        u_time1 = time.time()
        
        screen_width = monitor['width']
        screen_height = monitor['height']
        
        if screen_width > screen_height * 2:
            size_mode = 1
        else:
            size_mode = 0
        
        bgra = np.frombuffer(sct_img.bgra, dtype=np.uint8).reshape((sct_img.size[1], sct_img.size[0], 4))
        rgb = bgra[:, :, :3]
        rgb = rgb[:, :, ::-1]
        

        if size_mode == 0:  # 横向充满
            new_width = 160
            new_height = 160 * screen_height // screen_width
            im1 = shrink_image_block_average(rgb, rgb.shape[1] / new_width)

            start_y = (new_height - 80) // 2
            im1 = im1[start_y:start_y + 80, :]

        elif size_mode == 1:  # 纵向充满
            new_width = 80 * screen_width // screen_height
            new_height = 80
            im1 = shrink_image_block_average(rgb, rgb.shape[1] / new_width)

            start_x = (new_width - 160) // 2
            im1 = im1[:, start_x:start_x + 160]

        elif size_mode == 2:
            # not implemented currently
            raise NotImplementedError()
        
        rgb888 = np.asarray(im1)

        rgb565 = rgb888_to_rgb565(rgb888)
        arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
        hexstream = Screen_Date_Process(rgb565.flatten())
        
        u_time1 = time.time() - u_time1
        # print("截屏耗时" + str(u_time1))
        
        try:
            screen_process_queue.put(hexstream, timeout=3)
        except queue.Full:
            pass
        if MG_screen_thread_should_stop:
            print('stop screen process')
            break # exit screenshot thread

screenshot_test_time = datetime.now()
screenshot_test_frame = 0
screenshot_limit_fps = 50
screenshot_last_limit_time = datetime.now()

def screenshot_panic():
    MG_screen_thread_should_stop = True
    MG_daemon_should_stop = True
    print('Screenshot threads are panicking')
    if screen_shot_thread.is_alive():
        screen_shot_thread.join()
    if screen_process_thread.is_alive():
        screen_process_thread.join()
    time.sleep(3)
    screen_shot_thread.start()
    screen_process_thread.start()

def show_PC_Screen():  # 显示照片
    global State_change, Screen_Error, Device_State, screenshot_test_time, screenshot_test_frame, screenshot_last_limit_time
    if (State_change == 1):
        State_change = 0
        Screen_Error = 0
        LCD_ADD((160 - size_USE_X1) // 2, (80 - size_USE_Y1) // 2, size_USE_X1, size_USE_Y1)
    if (State_change == 0):
        try:
            hexstream = screen_process_queue.get(timeout=1)
        except queue.Empty:
            Screen_Error = Screen_Error + 1
            time.sleep(0.05)
            if Screen_Error > 100:
                screenshot_panic()
            return
        u_time = time.time()
        SER_Write(hexstream)
        u_time = time.time() - u_time
        # print("传输耗时"+str(u_time))
        current_time = datetime.now()
        if screenshot_test_frame % screenshot_limit_fps == 0:
            print(f"串流FPS: {screenshot_limit_fps / ((current_time - screenshot_test_time).total_seconds() + 1e-9)}")
            screenshot_test_time = current_time
        wait_time = 1.0 / screenshot_limit_fps - (current_time - screenshot_last_limit_time).total_seconds()
        if wait_time > 0:
            time.sleep(wait_time)
        screenshot_last_limit_time = current_time
        screenshot_test_frame += 1
        Screen_Error = 0


netspeed_last_refresh_time = None
netspeed_last_refresh_snetio = None
netspeed_plot_data = None

def sizeof_fmt(num, suffix="B", base=1024.0):
    # Use KiB for small value
    if abs(num) < base:
        return f"{num / base:3.1f}Ki{suffix}"
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < base:
            return f"{num:3.1f}{unit}{suffix}"
        num /= base
    return f"{num:.1f}Yi{suffix}"

netspeed_font = None
test_frame = 0

def show_netspeed(text_color=(255, 128, 0)):
    # geezmo: 预渲染图片，显示网速
    global netspeed_last_refresh_time, netspeed_last_refresh_snetio, netspeed_plot_data, State_change, test_frame
    test_frame += 1
    
    if netspeed_last_refresh_time is None or State_change == 1:
        # 初始化
        State_change = 0
        netspeed_last_refresh_time = datetime.now()
        netspeed_last_refresh_snetio = psutil.net_io_counters()
        netspeed_plot_data = [{'sent': 0, 'recv': 0}] * 120 # 存 120 格的绘图数据
        # 初始化的时候，网速先显示0
        current_snetio = netspeed_last_refresh_snetio
        LCD_ADD((160 - size_USE_X1) // 2, (80 - size_USE_Y1) // 2, size_USE_X1, size_USE_Y1)
    else:
        current_snetio = psutil.net_io_counters()
    
    # 获取网速 bytes/second
    
    current_time = datetime.now()
    seconds_elapsed = (current_time - netspeed_last_refresh_time) / timedelta(seconds=1)
    
    sent_per_second = (current_snetio.bytes_sent - netspeed_last_refresh_snetio.bytes_sent) / seconds_elapsed
    recv_per_second = (current_snetio.bytes_recv - netspeed_last_refresh_snetio.bytes_recv) / seconds_elapsed
    # print(current_snetio.bytes_sent, netspeed_last_refresh_snetio.bytes_sent, seconds_elapsed)
    
    netspeed_plot_data = netspeed_plot_data[1:] + [{
        'sent': sent_per_second,
        'recv': recv_per_second,
    }]
    
    netspeed_last_refresh_time = current_time
    netspeed_last_refresh_snetio = current_snetio
    
    # 绘制图片
    
    im1 = Image.new('RGB', (size_USE_X1, size_USE_Y1), (0, 0, 0))
    # im1 = Image.open('示例.png')
    
    draw = ImageDraw.Draw(im1)

    # 绘制文字
    
    #text = f"{test_frame}"
    text = f"上传  {sizeof_fmt(sent_per_second):>8}"
    draw.text((0, 0), text, fill=text_color, font=netspeed_font)
    text = f"下载  {sizeof_fmt(recv_per_second):>8}"
    draw.text((0, 40), text, fill=text_color, font=netspeed_font)

    # 绘图
    
    for start_y, key, color in zip([19, 59], ['sent', 'recv'], [(235, 139, 139), (146, 211, 217)]):
        sent_values = [data[key] for data in netspeed_plot_data]

        max_value = max(1024 * 100, max(sent_values)) # 最小范围 100KB/s
        bar_width = 2  # 每个点宽度
        image_height = 20  # 高度
        
        for i, sent in enumerate(sent_values[-80:]):
            # Scale the sent value to the image height
            bar_height = int((sent / max_value) * image_height) if max_value else 0
            x0 = i * bar_width
            y0 = image_height - bar_height
            x1 = (i + 1) * bar_width
            y1 = image_height

            # Draw the bar
            draw.rectangle([x0, start_y + y0, x1 - 1, max(start_y + y0, start_y + y1 - 1)], fill=color)  # Green bars
    
    rgb888 = np.asarray(im1)
    
    rgb565 = rgb888_to_rgb565(rgb888)
    arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
    hexstream = Screen_Date_Process(rgb565.flatten())
    SER_Write(hexstream)
    
    # 大约每1秒刷新一次
    time.sleep(1 - (datetime.now() - netspeed_last_refresh_time) / timedelta(seconds=1))
    # 测试用：显示帧率
    #print(1 / seconds_elapsed)

# 独立加载，忽略错误，以免错误影响到程序的其他功能
def load_hardware_monitor():
    from HardwareMonitor.Hardware import IVisitor, IComputer, IHardware, IParameter, ISensor
    from HardwareMonitor.Hardware import Computer
    from HardwareMonitor.Util import SensorValueToString

    class UpdateVisitor(IVisitor):
        __namespace__ = "TestHardwareMonitor"
        
        def __init__(self):
            self.sensors = []

        def VisitComputer(self, computer: IComputer):
            computer.Traverse(self)

        def VisitHardware(self, hardware: IHardware):
            hardware.Update()
            for subHardware in hardware.SubHardware:
                subHardware.Update()
                for sensor in subHardware.Sensors:
                    self.sensors.append([subHardware, sensor])
            
            for sensor in hardware.Sensors:
                self.sensors.append([hardware, sensor])

        def VisitParameter(self, parameter: IParameter): 
            pass

        def VisitSensor(self, sensor: ISensor): 
            pass
    
    def format_sensor_name(hardware, sensor):
        return hardware.Name + ': ' + str(sensor.SensorType) + ' - ' + sensor.Name
    
    class HardwareMonitorManager:
        def __init__(self):
            self.computer = Computer()
            self.computer.IsMotherboardEnabled = True
            self.computer.IsControllerEnabled = True
            self.computer.IsCpuEnabled = True
            self.computer.IsGpuEnabled = True
            self.computer.IsBatteryEnabled = True
            self.computer.IsMemoryEnabled = True
            self.computer.IsNetworkEnabled = True
            self.computer.IsStorageEnabled = True
            self.computer.Open()
            
            self.visitor = UpdateVisitor()
            self.computer.Accept(self.visitor)
            
            self.sensors = {format_sensor_name(hardware, sensor): (hardware, sensor) for hardware, sensor in self.visitor.sensors}
        
        def get_value(self, sensor_name):
            hardware, sensor = self.sensors[sensor_name]
            hardware.Update()
            return sensor.Value

        def get_value_formatted(self, sensor_name):
            hardware, sensor = self.sensors[sensor_name]
            hardware.Update()
            return sensor.Value, SensorValueToString(sensor.Value, sensor.SensorType)
        
    return HardwareMonitorManager

try:
    HardwareMonitorManager = load_hardware_monitor()
    hardware_monitor_manager = HardwareMonitorManager()
except Exception as e:
    HardwareMonitorManager = None
    hardware_monitor_manager = None
    print('Libre hardware monitor 加载失败')
    print(e)
    banned_states.append(3902)
    banned_states.append(3903)

custom_selected_names = [''] * 6
custom_selected_displayname = [''] * 6

custom_last_refresh_time = None
custom_plot_data = None

def show_custom_two_rows(text_color=(255, 128, 0)):
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global custom_last_refresh_time, custom_plot_data, State_change, test_frame
    test_frame += 1
    
    if custom_last_refresh_time is None or State_change == 1:
        # 初始化
        State_change = 0
        custom_last_refresh_time = datetime.now()
        custom_plot_data = [{'sent': 0, 'recv': 0}] * 120 # 存 120 格的绘图数据
        # 初始化的时候，先显示0
        LCD_ADD((160 - size_USE_X1) // 2, (80 - size_USE_Y1) // 2, size_USE_X1, size_USE_Y1)
        
    # 获取 libre hardware monitor 数值
    
    assert hardware_monitor_manager is not None
    
    try:
        sent, sent_text = hardware_monitor_manager.get_value_formatted(custom_selected_names[0])
    except KeyError:
        sent = 0
        sent_text = '--'
    try:
        recv, recv_text = hardware_monitor_manager.get_value_formatted(custom_selected_names[1])
    except KeyError:
        recv = 0
        recv_text = '--'
    
    current_time = datetime.now()
    seconds_elapsed = (current_time - custom_last_refresh_time) / timedelta(seconds=1)
    custom_plot_data = custom_plot_data[1:] + [{
        'sent': sent,
        'recv': recv,
    }]
    
    custom_last_refresh_time = current_time
    
    # 绘制图片
    
    im1 = Image.new('RGB', (size_USE_X1, size_USE_Y1), (0, 0, 0))
    # im1 = Image.open('示例.png')
    
    draw = ImageDraw.Draw(im1)

    # 绘制文字
    
    text = custom_selected_displayname[0] + sent_text
    draw.text((0, 0), text, fill=text_color, font=netspeed_font)
    text = custom_selected_displayname[1] + recv_text
    draw.text((0, 40), text, fill=text_color, font=netspeed_font)

    # 绘图
    # 决定最小范围
    min_max = [0.01, 0.01]
    # 百分比或温度的，是100
    if sent_text[-1] in ('%', 'C'):
        min_max[0] = 100
    if recv_text[-1] in ('%', 'C'):
        min_max[1] = 100
    
    for start_y, key, color, minmax_it in zip([19, 59], ['sent', 'recv'], [(235, 139, 139), (146, 211, 217)], min_max):
        sent_values = [data[key] for data in custom_plot_data]

        max_value = max(minmax_it, max(sent_values)) 
        bar_width = 2  # 每个点宽度
        image_height = 20  # 高度
        
        for i, sent in enumerate(sent_values[-80:]):
            # Scale the sent value to the image height
            bar_height = int((sent / max_value) * image_height) if max_value else 0
            x0 = i * bar_width
            y0 = image_height - bar_height
            x1 = (i + 1) * bar_width
            y1 = image_height

            # Draw the bar
            draw.rectangle([x0, start_y + y0, x1 - 1, max(start_y + y0, start_y + y1 - 1)], fill=color)  # Green bars
    
    
    rgb888 = np.asarray(im1)
    
    rgb565 = rgb888_to_rgb565(rgb888)
    arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
    hexstream = Screen_Date_Process(rgb565.flatten())
    SER_Write(hexstream)
    
    # 大约每1秒刷新一次
    time.sleep(1 - (datetime.now() - custom_last_refresh_time) / timedelta(seconds=1))
    # 测试用：显示帧率
    #print(1 / seconds_elapsed)

from MSU2_MINI_MG_minimark import MiniMarkParser
mini_mark_parser = MiniMarkParser()

full_custom_template = 'p Hello world'
full_custom_error = ''

def get_full_custom_im():
    global full_custom_error
        
    # 获取 libre hardware monitor 数值
    
    assert hardware_monitor_manager is not None
    
    custom_values = []
    for name in custom_selected_names:
        try:
            value, value_formatted = hardware_monitor_manager.get_value_formatted(name)
        except KeyError:
            value, value_formatted = 0, '--'
        custom_values.append((value, value_formatted))
            
    # 绘制图片
    
    im1 = Image.new('RGB', (size_USE_X1, size_USE_Y1), (255, 255, 255))
    # im1 = Image.open('示例.png')
    
    draw = ImageDraw.Draw(im1)
    error_line = ''
    record_dict = {str(i+1): v for i, (_, v) in enumerate(custom_values)} 
    record_dict_value = {str(i+1): v for i, (v, _) in enumerate(custom_values)} 
    try:
        mini_mark_parser.reset_state()
        for line in full_custom_template.strip().split('\n'):
            line.rstrip('\r') # possible
            error_line = line
            mini_mark_parser.parse_line(line, draw, im1, record_dict=record_dict, record_dict_value=record_dict_value)
        full_custom_error = 'OK'
    except Exception as e:
        import traceback
        full_custom_error = traceback.format_exc() + '\n' + error_line
        im1.paste((255, 0, 255), (0, 0, im1.size[0], im1.size[1]))
    
    return im1
    

def show_full_custom(text_color=(255, 128, 0)):
    # geezmo: 预渲染图片，显示两个 hardwaremonitor 里的项目
    global custom_last_refresh_time, State_change, test_frame
    test_frame += 1
    
    if custom_last_refresh_time is None or State_change == 1:
        # 初始化
        State_change = 0
        custom_last_refresh_time = datetime.now()
        custom_last_refresh_snetio = psutil.net_io_counters()
        LCD_ADD((160 - size_USE_X1) // 2, (80 - size_USE_Y1) // 2, size_USE_X1, size_USE_Y1)
    
    current_time = datetime.now()
    seconds_elapsed = (current_time - custom_last_refresh_time) / timedelta(seconds=1)
    
    custom_last_refresh_time = current_time
    
    im1 = get_full_custom_im()
    
    rgb888 = np.asarray(im1)
    
    rgb565 = rgb888_to_rgb565(rgb888)
    arr = np.frombuffer(rgb565.flatten().tobytes(),dtype=np.uint16).astype(np.uint32)
    hexstream = Screen_Date_Process(rgb565.flatten())
    SER_Write(hexstream)
    
    # 大约每1秒刷新一次
    time.sleep(1 - (datetime.now() - custom_last_refresh_time) / timedelta(seconds=1))
    # 测试用：显示帧率
    #print(1 / seconds_elapsed)

# Font cache
font_cache = {}

def load_font(font_name, font_size):
    """
    Load a font and cache it based on font name and size.
    
    Args:
        font_name (str): The path to the font file or the font name.
        font_size (int): The size of the font.
    
    Returns:
        ImageFont.FreeTypeFont: The loaded font.

    Raises:
        FileNotFoundError: If the font file does not exist.
        ValueError: If the font cannot be loaded.
    """
    key = (font_name, font_size)

    # Check if the font is already cached
    if key in font_cache:
        return font_cache[key]
    
    try:
        # Load the font
        font = ImageFont.truetype(font_name, font_size)
        # Cache the font
        font_cache[key] = font
        return font
    except OSError:
        raise FileNotFoundError(f"Font file '{font_name}' not found.")
    except Exception as e:
        raise ValueError(f"Could not load font '{font_name}' with size {font_size}: {str(e)}")

netspeed_font_size = 20
try:
    netspeed_font = load_font("simhei.ttf", netspeed_font_size)
except OSError:
    # Pillow 可能不能忽略文件大小写，以免读取失败
    try:
        netspeed_font = load_font("SimHei.ttf", netspeed_font_size)
    except OSError:
        # 字体读取失败，使用默认字体
        netspeed_font = ImageFont.load_default(netspeed_font_size)

def save_config(config_obj):
    with open('MSU2_MINI.json', 'w', encoding='utf-8') as f:
        json.dump(config_obj, f)

def load_config():
    try:
        with open('MSU2_MINI.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

def UI_Page():  # 进行图像界面显示
    global Label1, root, s1, s2, s3, Label2, Label3, Label4, Label5, Label6, Text1
    global State_machine, State_change, custom_selected_names, custom_selected_displayname, full_custom_template
    # 创建主窗口
    root = tk.Tk()  # 实例化主窗口
    root.title("MG USB屏幕助手V1.0")  # 设置标题
    root.iconbitmap('icon.ico')
    # screen_width = root.winfo_screenwidth()
    # screen_height = root.winfo_screenheight()
    # Show_X = int(screen_width / 2) - int(Show_W / 2)
    # Show_Y = int(screen_height / 2) - int(Show_H / 2)
    # root.geometry(f"{Show_W}x{Show_H}+{Show_X}+{Show_Y}")  # 主窗口的大小以及在显示器上的位置
    
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
    Text1 = tk.Text(root, width=23, height=4)
    Text1.grid(row=5, column=0, rowspan=2, padx=5, pady=5)

    def update_label_color():
        global color_use
        color_La = '#{:02x}{:02x}{:02x}'.format(int(s1.get()) * 8, int(s2.get()) * 4, int(s3.get()) * 8)
        color_use = int(s1.get()) * 2048 + int(s2.get()) * 32 + int(s3.get())
        if Label2:
            Label2.config(bg=color_La)

    # 创建滑块
    
    scale_desc = tk.Label(root, text="文字颜色")
    scale_desc.grid(row=0, column=3, sticky="w", padx=5, pady=5)
    
    s1 = ttk.Scale(root, from_=0, to=31, orient=tk.HORIZONTAL)
    s1.grid(row=1, column=3, sticky="w", padx=5)
    s1.set(config_obj.get('text_color_r', 31))
    s1.config(command=lambda x: update_label_color())
    
    scale_ind_r = tk.Label(root, bg="red", width=2)
    scale_ind_r.grid(row=1, column=4, padx=5, pady=5, sticky="w")

    s2 = ttk.Scale(root, from_=0, to=63, orient=tk.HORIZONTAL)
    s2.grid(row=2, column=3, sticky="w", padx=5)
    s2.set(config_obj.get('text_color_g', 32))
    s2.config(command=lambda x: update_label_color())
    
    scale_ind_g = tk.Label(root, bg="green", width=2)
    scale_ind_g.grid(row=2, column=4, padx=5, pady=5, sticky="w")

    s3 = ttk.Scale(root, from_=0, to=31, orient=tk.HORIZONTAL)
    s3.grid(row=3, column=3, sticky="w", padx=5)
    s3.set(config_obj.get('text_color_b', 0))
    s3.config(command=lambda x: update_label_color())
    
    scale_ind_b = tk.Label(root, bg="blue", width=2)
    scale_ind_b.grid(row=3, column=4, padx=5, pady=5, sticky="w")

    # 按钮涉及的配置项
    State_machine = config_obj.get('state_machine', 3901)
    State_change = 1
    LCD_Change_use = config_obj.get('lcd_change', 0)

    # 创建按钮
    
    btn1 = ttk.Button(root, text="上翻页", width=8, command=Page_UP)
    btn1.grid(row=5, column=2, padx=5)

    btn2 = ttk.Button(root, text="下翻页", width=8, command=Page_Down)
    btn2.grid(row=6, column=2, padx=5)

    btn3 = ttk.Button(root, text="选择背景图像", width=12, command=Get_Photo_Path1)
    btn3.grid(row=1, column=1, padx=5)

    btn4 = ttk.Button(root, text="选择闪存固件", width=12, command=Get_Photo_Path2)
    btn4.grid(row=2, column=1, padx=5)

    btn5 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path1)
    btn5.grid(row=1, column=2, padx=5)

    btn6 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path2)
    btn6.grid(row=2, column=2, padx=5)

    btn7 = ttk.Button(root, text="切换显示方向", width=12, command=LCD_Change)
    btn7.grid(row=6, column=1, padx=5)

    btn8 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path3)
    btn8.grid(row=3, column=2, padx=5)

    btn9 = ttk.Button(root, text="烧写", width=8, command=Writet_Photo_Path4)
    btn9.grid(row=4, column=2, padx=5)

    btn10 = ttk.Button(root, text="选择相册图像", width=12, command=Get_Photo_Path3)
    btn10.grid(row=3, column=1, padx=5)

    btn11 = ttk.Button(root, text="选择动图文件", width=12, command=Get_Photo_Path4)
    btn11.grid(row=4, column=1, padx=5)
    
    # geezmo: 选择屏幕
    
    number_var = tk.StringVar(root, '1')
    def change_screenshot_monitor(*args):
        global screenshot_monitor_id
        try:
            screenshot_monitor_id = int(number_var.get())
        except ValueError:
            print("Invalid number entered.")
    
    number_var.trace_add('write', change_screenshot_monitor)
    number_var.set(config_obj.get('number_var', '1'))
    
    screen_frame = tk.Frame(root)
    screen_frame.grid(row=5, column=3, rowspan=2, columnspan=2)
    
    label_screen_number = ttk.Label(screen_frame, text="屏幕编号")
    label_screen_number.grid(row=0, column=0, padx=5)

    number_entry = ttk.Entry(screen_frame, textvariable=number_var, width=4)
    number_entry.grid(row=0, column=1, padx=5, pady=5)
    
    fps_var = tk.StringVar(root, '100')
    def change_fps(*args):
        global screenshot_limit_fps
        try:
            screenshot_limit_fps = int(fps_var.get())
        except ValueError:
            print("Invalid number entered.")
    
    fps_var.trace_add('write', change_fps)
    fps_var.set(config_obj.get('fps_var', '100'))
    
    label = ttk.Label(screen_frame, text="最大 FPS")
    label.grid(row=1, column=0, padx=5)

    fps_entry = ttk.Entry(screen_frame, textvariable=fps_var, width=4)
    fps_entry.grid(row=1, column=1, padx=5, pady=5)
    
    screen_region_var = tk.StringVar(root, '0,0,,')
    def change_screen_region(*args):
        global screenshot_region
        try:
            t = tuple((None if x.strip() == '' else int(x)) for x in screen_region_var.get().split(','))
            if len(t) != 4:
                raise ValueError()
            screenshot_region = t
            State_change = 1 # 刷新屏幕
        except ValueError:
            print("Invalid.")
    
    screen_region_var.trace_add('write', change_screen_region)
    screen_region_var.set(config_obj.get('screen_region_var', '0,0,,'))
    
    label = ttk.Label(screen_frame, text="区域(左,上,宽,高)")
    label.grid(row=2, column=0, padx=5, columnspan=2)

    screen_region_entry = ttk.Entry(screen_frame, textvariable=screen_region_var, width=14)
    screen_region_entry.grid(row=3, column=0, padx=5, pady=5, columnspan=2)
    
    # 自定义显示内容
    
    custom_selected_names = config_obj.get('custom_selected_names', custom_selected_names)
    custom_selected_displayname = config_obj.get('custom_selected_displayname', custom_selected_displayname)
    full_custom_template = config_obj.get('full_custom_template', full_custom_template)
    
    def center_window(window):
        # Get the dimensions of the screen
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # Get the dimensions of the parent window
        parent_width = root.winfo_width()
        parent_height = root.winfo_height()
        parent_x = root.winfo_x()
        parent_y = root.winfo_y()

        # Get the dimensions of the child window (default size)
        window.update_idletasks()  # Update the window's size information
        child_width = window.winfo_width()
        child_height = window.winfo_height()

        # Calculate the position
        x = parent_x + (parent_width // 2) - (child_width // 2)
        y = parent_y + (parent_height // 2) - (child_height // 2)

        # Check if the child window exceeds the right boundary of the screen
        if x + child_width > screen_width - 50:
            x = screen_width - 50 - child_width

        # Check if the child window exceeds the bottom boundary of the screen
        if y + child_height > screen_height - 50:
            y = screen_height - 50 - child_height

        # Ensure the child window is not positioned outside of the left or top borders of the screen
        if x < 50:
            x = 50

        if y < 50:
            y = 50

        # Set the position of the child window
        window.geometry(f"+{x}+{y}")

    def show_custom():
        if hardware_monitor_manager is None:
            tkinter.messagebox.showerror(message='Libre Hardware Monitor 加载失败，不能自定义')
            return
        custom_window = tk.Toplevel(root)
        custom_window.title("自定义显示内容")
        
        sensor_vars = []
        sensor_displayname_vars = []
        
        def update_sensor_value(i):
            custom_selected_names[i] = sensor_vars[i].get()
        
        def change_sensor_displayname(i):
            custom_selected_displayname[i] = sensor_displayname_vars[i].get()
        
        desc_label = tk.Label(custom_window, text=f"有图表的模式显示前两条。完全自定义模式可以自己选择")
        desc_label.grid(row=0, column=0, columnspan=3, padx=5, pady=5)
        desc_label = tk.Label(custom_window, text="名称")
        desc_label.grid(row=1, column=1, padx=5, pady=5)
        desc_label = tk.Label(custom_window, text="项目")
        desc_label.grid(row=1, column=2, padx=5, pady=5)
        for i in range(6):
            sensor_label = tk.Label(custom_window, text=f"第{i+1}项")
            sensor_label.grid(row=i+2, column=0, padx=5, pady=5)
            sensor_var = tk.StringVar(custom_window, '')
            sensor_vars.append(sensor_var)
            sensor_combobox = ttk.Combobox(custom_window, textvariable=sensor_var, values=[''] + list(hardware_monitor_manager.sensors.keys()), width=60)
            sensor_combobox.set(custom_selected_names[i])
            sensor_combobox.bind("<<ComboboxSelected>>", lambda event, ii=i: update_sensor_value(ii))
            sensor_combobox.grid(row=i+2, column=2, padx=5, pady=5)
            
            sensor_displayname_var = tk.StringVar(custom_window, '')
            sensor_displayname_vars.append(sensor_displayname_var)
            
            sensor_displayname_var.set(custom_selected_displayname[i])
            sensor_entry = ttk.Entry(custom_window, textvariable=sensor_displayname_var, width=14)
            sensor_entry.bind("<KeyRelease>", lambda event, ii=i: change_sensor_displayname(ii))
            sensor_entry.grid(row=i+2, column=1, padx=5, pady=5)
        
        i = 6 + 2
        desc_label = tk.Label(custom_window, text=f"完全自定义模板代码：", anchor="w", justify="left")
        desc_label.grid(row=i+1, column=0, columnspan=3, padx=5, pady=5, sticky='w')
        
        text_frame = ttk.Frame(custom_window, padding="10")
        text_frame.grid(row=i+2, column=0, columnspan=3, padx=10, pady=5, sticky='w')
        
        text_area = tk.Text(text_frame, wrap=tk.WORD, width=60, height=10)
        text_area.insert(tk.END, full_custom_template)
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(custom_window, width=160, height=80)
        canvas.grid(row=i+4, column=0, columnspan=3, padx=5, pady=5, sticky='w')
        
        def update_global_text(event):
            global full_custom_template
            # Get the current content of the text area and update the global variable
            full_custom_template = text_area.get("1.0", tk.END)
            im = get_full_custom_im()
            tk_im = ImageTk.PhotoImage(im)
            canvas.create_image(0, 0, anchor=tk.NW, image=tk_im)
            canvas.image = tk_im
        
        text_area.bind("<KeyRelease>", update_global_text)
        update_global_text(None)
        
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_area['yscrollcommand'] = scrollbar.set

        desc_label = tk.Label(custom_window, text='\n'.join([
            "说明：自定义显示内容一共有两个模式，第一个固定显示两行，有图表，第二个是完全自定义模式，可以自己加文本和图片",
            "模板代码在上方输入，结果会显示在下方，模板代码从前往后顺序执行，每行执行一个操作",
            "p <文本> 代表绘制文本，会自动移动坐标; a <锚点> 代表更改文本锚点，参考Pillow文档，如la,ra,ls,rs",
            "m <x> <y> 代表移动到坐标(x,y); t <x> <y> 代表相对当前位置移动(x,y)",
            "f <文件名> <大小> 代表更换字体，文件名如 arial.ttf; c <hex码> 代表更改文字颜色，如 c #ffff00",
            "i <文件名> 代表绘制图片; v <项目编号> <格式符> 绘制上面选择的某个值，格式符可省略，如 v 1 {:.2f}",
            ]), wraplength=850, anchor="w", justify="left")
        desc_label.grid(row=i+3, column=0, columnspan=3, padx=5, pady=5, sticky='w')
        
        def show_error():
            tkinter.messagebox.showinfo(message=full_custom_error)
            print(full_custom_error)
        btn_frame = ttk.Frame(custom_window, padding="10")
        btn_frame.grid(row=i+5, column=0, columnspan=3, padx=5, pady=5, sticky='w')
        show_error_btn = ttk.Button(btn_frame, text="查看模板错误", width=12, command=show_error)
        show_error_btn.grid(row=0, column=0)
        def example(i):
            global full_custom_template
            if i == 1:
                full_custom_template = '\n'.join([
                    'i example_background.png',
                    'c #ff3333',
                    'f Orbitron-Bold.ttf 22',
                    'm 16 16',
                    'v 1 {:.0f}',
                    'p %',
                    'm 96 16',
                    'v 2 {:.0f}',
                    'p %',
                    'm 96 44',
                    'v 3 {:.0f}',
                    'p %',
                ])
            elif i == 2:
                full_custom_template = '\n'.join([
                    'f arial.ttf 20',
                    'm 8 8',
                    'p CPU',
                    't 8 0',
                    'c #3366cc',
                    'v 1',
                    'm 8 28',
                    'c #000000',
                    'p GPU',
                    't 8 0',
                    'c #3366cc',
                    'v 2',
                    'm 8 48',
                    'c #000000',
                    'f Times.ttf 20',
                    'p RAM',
                    't 8 0',
                    'c #3366cc',
                    'v 3',
                ])
            text_area.delete('1.0', tk.END)
            text_area.insert(tk.END, full_custom_template)
            update_global_text(None)
        example_btn_1 = ttk.Button(btn_frame, text="示例1科技", width=12, command=lambda: example(1))
        example_btn_1.grid(row=0, column=1)
        example_btn_2 = ttk.Button(btn_frame, text="示例2简单", width=12, command=lambda: example(2))
        example_btn_2.grid(row=0, column=2)
        example_btn_2 = ttk.Label(btn_frame, text="示例请将第1项至第3项设为CPU、GPU和RAM")
        example_btn_2.grid(row=0, column=3)
        
        center_window(custom_window)

    show_custom_btn = ttk.Button(root, text="自定义内容", width=12, command=show_custom)
    show_custom_btn.grid(row=5, column=1, padx=5)
    
    def quit_window(icon, item):
        icon.stop()
        root.destroy()

    def show_window(icon, item):
        icon.stop()
        root.after(0,root.deiconify)
    def hide_to_tray():
        try:
            root.withdraw()
            import pystray
            image = Image.open("icon.ico")
            menu = (pystray.MenuItem('显示', show_window), pystray.MenuItem('退出', quit_window))
            icon = pystray.Icon("name", image, "title", menu)
            icon.run()
        except Exception as e:
            print("failed to use pystray to hide to tray")
            root.after(0, root.deiconify)
    
    hide_btn = ttk.Button(root, text="隐藏", width=12, command=hide_to_tray)
    hide_btn.grid(row=0, column=1, padx=5)

    update_label_color()
    
    def on_closing():
        # 结束以后保存配置
        
        config_obj = {
            'text_color_r': int(s1.get()),
            'text_color_g': int(s2.get()),
            'text_color_b': int(s3.get()),
            'state_machine': State_machine,
            'lcd_change': LCD_Change_use,
            'number_var': number_var.get(),
            'fps_var': fps_var.get(),
            'screen_region_var': screen_region_var.get(),
            'custom_selected_names': custom_selected_names,
            'custom_selected_displayname': custom_selected_displayname,
            'full_custom_template': full_custom_template,
        }
        
        save_config(config_obj)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # 启动其他线程
    daemon_thread.start()
    screen_shot_thread.start()
    screen_process_thread.start()
    
    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == 'hide':
        hide_to_tray()

    # 进入消息循环
    root.mainloop()
    

def Get_MSN_Device():  # 尝试获取MSN设备
    global Device_State, ADC_det, ser, State_change, State_machine, My_MSN_Device, My_MSN_Data, Screen_Error, Label1, LCD_Change_now, Text1
    port_list = list(serial.tools.list_ports.comports())  # 查询所有串口
    # geezmo: 如果有 VID = 0x1a86 （沁恒）的，优先考虑这些设备，防止访问其他串口出错
    # 如果没有这些设备，或者 pyserial 没有提供信息，则不管
    wch_port_list = [x for x in port_list if x.vid == 0x1a86]
    not_wch_port_list = [x for x in port_list if x.vid != 0x1a86]
    port_list = wch_port_list + not_wch_port_list
    if len(port_list) == 0:
        print('未检测到串口,请确保设备已连接到电脑')
        # Label1.config(text="设备已连接",bg="GREEN")
        time.sleep(1)
        if not MG_daemon_should_stop:
            try:
                Label1.config(text="设备未连接", fg="white", bg="RED")
            except RuntimeError:
                pass
        Device_State = 0  # 未能连接
    else:  # 对串口进行监听，确保其为MSN设备
        My_MSN_Device = []
        My_MSN_Data = []
        for i in range(0, len(port_list)):
            try:  # 尝试打开串口
                ser = serial.Serial(port_list[i].name, 115200, timeout=2)  # 初始化串口连接,初始使用
            except:  # 出现异常
                print(port_list[i].name + '无法打开,请检查是否被其他程序占用')  # 显示MSN设备数量
                # ser.close()#将串口关闭，防止下次无法打开
                time.sleep(0.1)
                continue  # 执行下一次循环
            time.sleep(0.25)  # 理论上MSN设备100ms要发送一次“ MSN01”,在250ms内至少会收到一次
            recv = SER_Read()
            if (recv == 0):
                break  # 退出当前for循环
            else:
                recv = recv.decode("gbk")  # 获取串口数据
            if (len(recv) > 5):  # 收到6个字符以上数据时才进行解析
                for n in range(0, len(recv) - 5):  # 逐字解析编码
                    if (ord(recv[n]) == 0):  # 当前字节为0时进行解析
                        if ((recv[n + 1] == 'M') and (recv[n + 2] == 'S') and (recv[n + 3] == 'N')):  # 确保为MSN设备
                            if ((recv[n + 4] >= '0') and (recv[n + 4] <= '9') and (recv[n + 5] >= '0') and (
                                    recv[n + 5] <= '9')):  # 确保版本号为数字ASC码
                                My_MSN_Device.append(MSN_Device((port_list[i].name), (ord(recv[4]) - 48) * 10 + (
                                            ord(recv[5]) - 48)))  # 对MSN设备进行登记
                                hex_code = int(0).to_bytes(1, byteorder="little")  # 可以逐个加入数组
                                hex_code = hex_code + b'MSNCN'
                                SER_Write(hex_code)  # 返回消息
                                # 等待返回消息，确认连接
                                time.sleep(0.25)  # 理论上MSN设备100ms要发送一次“ MSN01”,在250ms内至少会收到一次
                                recv = SER_Read().decode("gbk")  # 获取串口数据
                                if ((ord(recv[0]) == 0) and (recv[1] == 'M') and (recv[2] == 'S') and (
                                        recv[3] == 'N') and (recv[4] == 'C') and (recv[5] == 'N')):  # 确保为MSN设备
                                    print('MSN设备' + str(len(My_MSN_Device)) + '——' + port_list[
                                        i].name + '连接完成')  # 显示MSN设备数量
                                else:
                                    print('MSN设备' + str(
                                        len(My_MSN_Device)) + '无法连接,请检查连接是否正常')  # 显示MSN设备数量
                                    My_MSN_Device.pop()
                                break  # 退出当前for循环
            if len(My_MSN_Device) > 0:
                break # 如果已经发现连接好了，那就不继续连后面的了
        print('MSN设备数量为' + str(len(My_MSN_Device)) + '个')  # 显示MSN设备数量
        if (len(My_MSN_Device) >= 1 and Device_State == 0):
            Device_State = 1  # 可以正常连接
            State_change = 1  # 状态发生变化
            Screen_Error = 0
            Read_M_SFR_Data(256)  # 读取u8在0x0100之后的128字节
            Print_MSN_Data()  # 解析字节中的数据格式
            Read_MSN_Data(b'MSN_Status')
            UID = Read_MSN_Data(b'MSN_UID')
            # 获取按键状态
            # LCD_State(1)#配置显示方向
            ADC_det = Read_ADC_CH(9)
            ADC_det = (ADC_det + Read_ADC_CH(9)) / 2
            ADC_det = ADC_det - 125  # 根据125的阈值判断是否被按下
            if not MG_daemon_should_stop:
                try:
                    Label1.config(text="设备已连接", fg="white", bg="green")
                except RuntimeError:
                    pass
            LCD_Change_now = 0
            if not MG_daemon_should_stop:
                try:
                    Text1.delete(1.0, tk.END)  # 清除文本框
                except RuntimeError:
                    pass
            # Text1.insert(tk.END,'设备识别码:')#在文本框开始位置插入“内容一”

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

        else:
            Device_State = 0  # 可以正常连接

last_adc_check = datetime.now()

def MSN_Device_1_State_machine():  # MSN设备1的循环状态机
    global State_machine, last_adc_check, key_eff, key_on, State_change, s1, s2, s3, color_use, Label2, photo_path1, photo_path2, write_path1, write_path2, LCD_Change_use, LCD_Change_now, write_path3, write_path4, Img_data_use
    global size_USE_X1, size_USE_Y1
    # print("State_machine"+str(State_machine))
    # if write_path1==1:
    if LCD_Change_now != LCD_Change_use:  # 显示方向与设置不符合
        LCD_Change_now = LCD_Change_use
        LCD_State(LCD_Change_now)  # 配置显示方向
        State_change = 1

    if (write_path1 == 1):
        Write_Flash_hex_fast(3826, Img_data_use)
        write_path1 = 0
        State_change = 1
    if (write_path2 == 1):
        Write_Flash_Photo_fast(0, photo_path2)
        write_path2 = 0
        State_change = 1

    if (write_path3 == 1):
        Write_Flash_hex_fast(3926, Img_data_use)
        write_path3 = 0
        State_change = 1

    if (write_path4 == 1):
        Write_Flash_hex_fast(0, Img_data_use)
        write_path4 = 0
        State_change = 1
    
    size_USE_X1 = 160
    size_USE_Y1 = 80
    # always use all 
    #if State_machine != 5:
    
    # 每 0.3 秒检测一次ADC按键
    current_time = datetime.now()
    if ((current_time - last_adc_check).total_seconds() > 0.3):
        last_adc_check = current_time
        if (Read_ADC_CH(9) < ADC_det):  # 按键按下
            key_on = 1
        elif (key_on == 1):
            key_eff = 1
            key_on = 0
        else:
            key_on = 0
        if (key_eff == 1):
            key_eff = 0
            Page_UP()
    elif (State_machine == 0):
        show_gif()
    elif (State_machine == 1):
        show_PC_state(BLUE, BLACK)
    elif (State_machine == 2):
        show_PC_state(color_use, BLACK)
    elif (State_machine == 3):
        show_Photo1()
    elif (State_machine == 4):
        show_PC_time()
    elif (State_machine == 5):
        show_PC_Screen()
    elif (State_machine == 3901):
        rgb_tuple = (((color_use >> 11) & 0x1F) * 255 // 31, ((color_use >> 5) & 0x3F) * 255 // 63, (color_use & 0x1F) * 255 // 31)
        show_netspeed(text_color=rgb_tuple)
    elif (State_machine == 3902):
        rgb_tuple = (((color_use >> 11) & 0x1F) * 255 // 31, ((color_use >> 5) & 0x3F) * 255 // 63, (color_use & 0x1F) * 255 // 31)
        show_custom_two_rows(text_color=rgb_tuple)
    elif (State_machine == 3903):
        rgb_tuple = (((color_use >> 11) & 0x1F) * 255 // 31, ((color_use >> 5) & 0x3F) * 255 // 63, (color_use & 0x1F) * 255 // 31)
        show_full_custom(text_color=rgb_tuple)
        # import cProfile
        # cProfile.runctx(
# '''
# for i in range(100):
#     show_netspeed(text_color=rgb_tuple)
# ''', globals(), locals())


print("该设备具有" + str(psutil.cpu_count(logical=False)) + "个内核和" + str(psutil.cpu_count()) + "个逻辑处理器")
print("该CPU主频为" + str(round((psutil.cpu_freq().current / 1000), 1)) + "GHZ")
print("当前CPU占用率为" + str(psutil.cpu_percent()) + "%")  # 并不准确
mem = psutil.virtual_memory()
print("该设备具有" + str(round(mem.total / (1024 * 1024 * 1024))) + "GB的内存")
print("当前内存占用率为" + str(mem.percent) + "%")
print("开始运行时间" + datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"))
battery = psutil.sensors_battery()

if battery != None:
    print("电池剩余电量" + str(battery.percent) + "%")
# if battery.power_plugged:
#	print("已连接电源线")
# else:
#	print("已断开电源线")

# 创建定时器,延时为0.2秒
D = 0
# while(1):
#    D=D+1
#    print(D)
#    time.sleep(0.5)


CPU = 0
FC = BLUE
BC = BLACK
key_on = 0
key_eff = 0
State_change = 1  # 状态发生变化
gif_num = 0
State_machine = 3901  # 定义初始状态
Device_State = 0  # 初始为未连接
LCD_Change_use = 0  # 初始显示方向
LCD_Change_now = 0
color_use = RED
write_path1 = 0
write_path2 = 0
write_path3 = 0
write_path4 = 0
photo_path1 = ""
photo_path2 = ""
photo_path3 = ""
photo_path4 = ""

screen_shot_thread = threading.Thread(target=screen_shot_task)
screen_process_thread = threading.Thread(target=screen_process_task)

def daemon_task():
    global D
        
    while (1):
        D = D + 1
        # print(D)
        if (Device_State == 0):  # 未检测到设备
            Get_MSN_Device()  # 尝试获取MSN设备
        # print("Waiting")
        elif (Device_State == 1):  # 已检测到设备
            MSN_Device_1_State_machine()
        if MG_daemon_should_stop:
            print('stop daemon')
            break
            # time.sleep(10)
        # print("OK")

daemon_thread = threading.Thread(target=daemon_task)


# tkinter requires the main thread
try:
    UI_Page()
finally:
    # reap threads
    print('ui closed')

    MG_screen_thread_should_stop = True
    MG_daemon_should_stop = True
    print('reap threads')
    if screen_shot_thread.is_alive():
        screen_shot_thread.join()
    if screen_process_thread.is_alive():
        screen_process_thread.join()
    daemon_thread.join()


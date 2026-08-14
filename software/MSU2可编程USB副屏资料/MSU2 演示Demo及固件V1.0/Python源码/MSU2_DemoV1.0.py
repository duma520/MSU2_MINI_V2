# -*- coding: UTF-8 -*-
import serial#引入串口库（需要额外安装）
import serial.tools.list_ports
import time#引入延时库
import threading#引入定时回调库
import psutil #引入psutil获取设备信息（需要额外安装）
import os#用于读取文件
import pyautogui#用于截图(需要额外安装pillow)
from datetime import datetime#用于获取当前时间

class MSN_Device:#定义一个结构体
    def __init__(self,com,version):
        self.com=com #登记串口位置
        self.version=version#登记MSN版本
        self.name='MSN'  #登记设备名称
        self.baud_rate=19200  #登记波特率
My_MSN_Device=[]#创建一个空的结构体数组

class MSN_Data:#定义一个结构体
    def __init__(self,name,unit,family,data):
        self.name=name 
        self.unit=unit
        self.family=family 
        self.data=data  

My_MSN_Data=[]#创建一个空的结构体数组

RED=0xf800
GREEN=0x07e0
BLUE=0x001f
WHITE=0xffff
BLACK=0x0000
YELLOW=0xFFE0
GRAY0=0xEF7D
GRAY1=0x8410
GRAY2=0x4208

hex_code=b''

G_screnn0=bytearray()#空数组
G_screnn1=bytearray()#空数组
G_screnn0_OK=0
G_screnn1_OK=0
size_USE_X1=0
size_USE_Y1=0

def Read_M_u8(add):#读取主机u8寄存器（MSC设备编码，Add）
    hex_use=int(0).to_bytes(1,byteorder="little")#发给主机
    hex_use=hex_use+b'0'#识别为SFR指令
    hex_use=hex_use+int(0*32).to_bytes(1,byteorder="little")#识别为8bit SFR读
    hex_use=hex_use+int(add/256).to_bytes(1,byteorder="little")#高地址
    hex_use=hex_use+int(add%256).to_bytes(1,byteorder="little")#低地址
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#数值
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("byte")#获取串口数据
        if(len(recv)!=0):
            return recv[5]

def Read_M_u16(add):#读取主机u8寄存器（MSC设备编码，Add）
    hex_use=int(0).to_bytes(1,byteorder="little")#发给主机
    hex_use=hex_use+b'0'#识别为SFR指令
    hex_use=hex_use+int(1*32).to_bytes(1,byteorder="little")#识别为16bit SFR读
    hex_use=hex_use+int(add%256).to_bytes(1,byteorder="little")#地址
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#数值
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#数值
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("gbk")#获取串口数据
        if(len(recv)!=0):
            return recv[4]*256+recv[5]

def Write_M_u8(add,data_w):#读取主机u8寄存器（MSC设备编码，Add）
    hex_use=int(0).to_bytes(1,byteorder="little")#发给主机
    hex_use=hex_use+b'0'#识别为SFR指令
    hex_use=hex_use+int(4*32).to_bytes(1,byteorder="little")#识别为8bit SFR写
    hex_use=hex_use+int(add/256).to_bytes(1,byteorder="little")#高地址
    hex_use=hex_use+int(add%256).to_bytes(1,byteorder="little")#低地址
    hex_use=hex_use+int(data_w%256).to_bytes(1,byteorder="little")#数值
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break
            #return recv[5]

def Write_M_u16(add,data_w):#读取主机u8寄存器（MSC设备编码，Add）
    hex_use=int(0).to_bytes(1,byteorder="little")#发给主机
    hex_use=hex_use+b'0'#识别为SFR指令
    hex_use=hex_use+int(5*32).to_bytes(1,byteorder="little")#识别为16bit SFR写
    hex_use=hex_use+int(add%256).to_bytes(1,byteorder="little")#地址
    hex_use=hex_use+int(data_w/256).to_bytes(1,byteorder="little")#数值
    hex_use=hex_use+int(data_w%256).to_bytes(1,byteorder="little")#数值
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("gbk")#获取串口数据
        if(len(recv)!=0):
            break

def Read_ADC_CH(ch):#读取主机u8寄存器（MSC设备编码，Add）
    hex_use=int(8).to_bytes(1,byteorder="little")#读取ADC
    hex_use=hex_use+int(ch).to_bytes(1,byteorder="little")#通道
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#地址
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#数值
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#数值
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("gbk")#获取串口数据
        if(len(recv)!=0):
            return recv[4]*256+recv[5]
            
def Read_M_SFR_Data(add):#从u8区域获取SFR描述
    SFR_data=b''
    for i in range(0,256):#以128字节为单位进行解析编码
        SFR_data=SFR_data+int(Read_M_u8(add+i)).to_bytes(1,byteorder="little")#读取编码数据
    data_type=0#根据是否为0进行类型循环统计
    data_num=0
    data_len=0
    data_use=b''
    data_name=b''
    data_unit=b''
    data_family=b''
    data_data=b''
    for i in range(0,256):#以128字节为单位进行解析编码
        if(SFR_data[i]!=0 and data_type<3):
            data_use=data_use+int(SFR_data[i]).to_bytes(1,byteorder="little")##将非0数据合并到一块
        elif(data_type<3):#检测到0且未超纲
            if(len(data_use)==0):#没有接收到数据时就接收到00
                break#检测到0后收集的数据为空，判断为结束
            if(data_type==0):
                data_name=data_use#名称
                data_type=1
            elif(data_type==1):
                data_unit=data_use#单位
                data_type=2
            elif(data_type==2):
                data_family=data_use#类型
                data_type=3
                if(int(ord(data_use)//32)==0):#u8 data 2B add
                    data_len=2
                elif(int(ord(data_use)//32)==1):#u16 data 1B add
                    data_len=1
                elif(int(ord(data_use)//32)==2):#u32 data 2B add
                    data_len=2
                elif(int(ord(data_use)//32)==3):#u8 Text XB data
                    data_len=data_family[0]%32#计算数据长度
            data_use=b''
            continue #进行下一次循环
        if(data_len>0  and data_type==3):#正式的有效数据
            data_use=data_use+int(SFR_data[i]).to_bytes(1,byteorder="little")##将非0数据合并到一块
            data_len=data_len-1
        if(data_len==0 and data_type==3):#将后续数据收集完整
            data_data=data_use
            data_type=0#重置类型
            My_MSN_Data.append(MSN_Data(data_name,data_unit,data_family,data_data))#对数据进行登记
            data_use=b''

def Print_MSN_Data():
    num=len(My_MSN_Data)
    data_str=''
    print('MSN数据总数为：'+str(num))
    #进行数据解析
    for i in range(0,num):#将数据全部打印出来
        data_str=data_str+'序号：'+str(i)+'    名称：'+str(My_MSN_Data[i].name)+'    单位:'+str(My_MSN_Data[i].unit)
        if(ord(My_MSN_Data[i].family)//32==0):#数据类型为u8地址(16bit)
            data_str=data_str+'    类型：u8_SFR地址,长度'+str(ord(My_MSN_Data[i].family)%32)
            data_str=data_str+'    地址：'+str(int(My_MSN_Data[i].data[0])*256+int(My_MSN_Data[i].data[1]))
        elif(ord(My_MSN_Data[i].family)//32==1):#数据类型为u16地址(8bit)
            data_str=data_str+'    类型：u16_SFR地址,长度'+str(ord(My_MSN_Data[i].family)%32)
            data_str=data_str+'    地址：'+str(int(My_MSN_Data[i].data[0]))
        elif(ord(My_MSN_Data[i].family)//32==2):#数据类型为u32地址(16bit)
            data_str=data_str+'    类型：u32_SFR地址,长度：'+str(ord(My_MSN_Data[i].family)%32)
            data_str=data_str+'    地址：'+ str(int(My_MSN_Data[i].data[0])*256+int(My_MSN_Data[i].data[1]))
        elif(ord(My_MSN_Data[i].family)//32==3):#数据类型为u8字符串
            data_str=data_str+'    类型：字符串,长度'+str(ord(My_MSN_Data[i].family)%32)
            data_str=data_str+'    数据：'+str(My_MSN_Data[i].data)
        elif(ord(My_MSN_Data[i].family)//32==4):#数据类型为u8数组
            data_str=data_str+'    类型：u8数组数据,长度'+str(int(My_MSN_Data[i].family)%32)
            data_str=data_str+'    数据：'+str(My_MSN_Data[i].data)
        print(data_str)
        data_str=''

def Read_MSN_Data(name_use):#读取MSN_data中的数据
    num=len(My_MSN_Data)
    use_data=[]#创建一个空列表
    for i in range(0,num):#将数据查找一遍
        if(My_MSN_Data[i].name == name_use):
            if(ord(My_MSN_Data[i].family)//32==0):#数据类型为u8地址(16bit)
                sfr_add=int(My_MSN_Data[i].data[0])*256+int(My_MSN_Data[i].data[1])
                for n in range(0,ord(My_MSN_Data[i].family)%32):
                    use_data.append(Read_M_u8(sfr_add+n))
            elif(ord(My_MSN_Data[i].family)//32==1): #数据类型为u16地址(8bit)
                use_data=Read_M_u16(int(My_MSN_Data[i].data[0]))
            elif(ord(My_MSN_Data[i].family)//32==3): #数据类型为u8字符串
                use_data=My_MSN_Data[i].data
            elif(ord(My_MSN_Data[i].family)//32==4):#数据类型为u8数组
                use_data=My_MSN_Data[i].data
            print(str(My_MSN_Data[i].name)+'='+str(use_data))
            return use_data
    print('"'+name_use+'"'+'不存在,请检查名称是否正确')
    return 0

def Write_MSN_Data(name_use,data_w):#在MSN_data写入数据
    num=len(My_MSN_Data)
    for i in range(0,num):#将数据查找一遍
        if(My_MSN_Data[i].name == name_use):
            if(int(My_MSN_Data[i].family)//32==0):#数据类型为u8地址(16bit)
                Write_M_u8(int(My_MSN_Data[i].data[0])*256+int(My_MSN_Data[i].data[1]),data_w)
                print('"'+name_use+'"'+'写入'+str(data_w)+'完成')
                return 0
            elif(int(My_MSN_Data[i].family)//32==1): #数据类型为u16地址(8bit)
                Write_M_u16(int(My_MSN_Data[i].data[0]),data_w)
                print('"'+name_use+'"'+'写入'+str(data_w)+'完成')
                return 0
    print('"'+name_use+'"'+'不存在,请检查名称是否正确')

def Write_Flash_Page(Page_add,data_w,Page_num):#往Flash指定页写入256B数据
    #先把数据传输完成
    for i in range(0,64):#256字节数据分为64个指令
        hex_use=int(4).to_bytes(1,byteorder="little")#多次写入Flash
        hex_use=hex_use+int(i).to_bytes(1,byteorder="little")#低位地址
        hex_use=hex_use+data_w[i*4+0].to_bytes(1,byteorder="little")#Data0
        hex_use=hex_use+data_w[i*4+1].to_bytes(1,byteorder="little")#Data1
        hex_use=hex_use+data_w[i*4+2].to_bytes(1,byteorder="little")#Data2
        hex_use=hex_use+data_w[i*4+3].to_bytes(1,byteorder="little")#Data3
        ser.write(hex_use)#发出指令
    hex_use=int(3).to_bytes(1,byteorder="little")#对Flash操作
    hex_use=hex_use+int(1).to_bytes(1,byteorder="little")#写Flash
    hex_use=hex_use+int(Page_add//(256*256)).to_bytes(1,byteorder="little")#Data0
    hex_use=hex_use+int((Page_add%65536)//256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int((Page_add%65536)%256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int(Page_num).to_bytes(1,byteorder="little")#Data3
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def Write_Flash_Page_fast(Page_add,data_w,Page_num):#未经过擦除，直接往Flash指定页写入256B数据
    #先把数据传输完成
    hex_use=b''
    for i in range(0,64):#256字节数据分为64个指令
        hex_use=hex_use+int(4).to_bytes(1,byteorder="little")#多次写入Flash
        hex_use=hex_use+int(i).to_bytes(1,byteorder="little")#低位地址
        hex_use=hex_use+data_w[i*4+0].to_bytes(1,byteorder="little")#Data0
        hex_use=hex_use+data_w[i*4+1].to_bytes(1,byteorder="little")#Data1
        hex_use=hex_use+data_w[i*4+2].to_bytes(1,byteorder="little")#Data2
        hex_use=hex_use+data_w[i*4+3].to_bytes(1,byteorder="little")#Data3
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#对Flash操作
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#经过擦除，写Flash
    hex_use=hex_use+int(Page_add//(256*256)).to_bytes(1,byteorder="little")#Data0
    hex_use=hex_use+int((Page_add%65536)//256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int((Page_add%65536)%256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int(Page_num).to_bytes(1,byteorder="little")#Data3
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def Erase_Flash_page(add,size):#清空指定区域的内存
    hex_use=int(3).to_bytes(1,byteorder="little")#对Flash操作
    hex_use=hex_use+int(2).to_bytes(1,byteorder="little")#读Flash
    hex_use=hex_use+int((add%65536)//256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int((add%65536)%256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int((size%65536)//256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int((size%65536)%256).to_bytes(1,byteorder="little")#Data2
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def Read_Flash_byte(add):#读取指定地址的数值
    hex_use=int(3).to_bytes(1,byteorder="little")#对Flash操作
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#读Flash
    hex_use=hex_use+int(add//(256*256)).to_bytes(1,byteorder="little")#Data0
    hex_use=hex_use+int((add%65536)//256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int((add%65536)%256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#Data3
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            print(recv[5])
            return recv[5]
    
def Write_Flash_Photo_fast(Page_add,Photo_name):#往Flash里面写入Bin格式的照片
    filepath=Photo_name+'.bin'#合成文件名称
    try:#尝试打开bin文件
        binfile=open(filepath,'rb')#以只读方式打开
    except:#出现异常
        print('找不到“'+filepath+'”文件,请检查其位置是否位于当前目录下');
        return 0
    Fsize=os.path.getsize(filepath)
    print('找到“'+filepath+'”文件,大小：'+str(Fsize)+' B');
    u_time=time.time()
    #进行擦除
    if(Fsize%256 !=0):
        Erase_Flash_page(Page_add,Fsize//256+1)#清空指定区域的内存
    else:
        Erase_Flash_page(Page_add,Fsize//256)#清空指定区域的内存
    
    for i in range(0,Fsize//256):#每次写入一个Page
        Fdata=binfile.read(256)
        Write_Flash_Page_fast(Page_add+i,Fdata,1)#(page,数据，大小)
    if(Fsize%256 !=0):#还存在没写完的数据
        Fdata=binfile.read(Fsize%256)#将剩下的数据读完
        for i in range(Fsize%256,256):
            Fdata=Fdata+int(255).to_bytes(1,byteorder="little")#不足位置补充0xFF
        Write_Flash_Page_fast(Page_add+Fsize//256,Fdata,1)#(page,数据，大小)
    u_time=time.time()-u_time
    print(filepath+' 烧写完成,耗时'+str(u_time)+'秒')
    
def Write_Flash_ZK(Page_add,ZK_name):#往Flash里面写入Bin格式的字库
    filepath=ZK_name+'.bin'#合成文件名称
    try:#尝试打开bin文件
        binfile=open(filepath,'rb')#以只读方式打开
    except:#出现异常
        print('找不到“'+filepath+'”文件,请检查其位置是否位于当前目录下');
        return 0
    Fsize=os.path.getsize(filepath)-6#字库文件的最后六个字节不是点阵信息
    print('找到“'+filepath+'”文件,大小：'+str(Fsize)+' B');
    for i in range(0,Fsize//256):#每次写入一个Page
        Fdata=binfile.read(256)
        Write_Flash_Page(Page_add+i,Fdata,1)#(page,数据，大小)
    if(Fsize%256 !=0):#还存在没写完的数据
        Fdata=binfile.read(Fsize%256)#将剩下的数据读完
        for i in range(Fsize%256,256):
            Fdata=Fdata+int(255).to_bytes(1,byteorder="little")#不足位置补充0xFF
        Write_Flash_Page(Page_add+Fsize//256,Fdata,1)#(page,数据，大小)
    print(filepath+' 烧写完成')

def LCD_Set_XY(LCD_D0,LCD_D1):#设置起始位置
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#设置起始位置
    hex_use=hex_use+int(LCD_D0//256).to_bytes(1,byteorder="little")#Data0
    hex_use=hex_use+int(LCD_D0%256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int(LCD_D1//256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int(LCD_D1%256).to_bytes(1,byteorder="little")#Data3
    ser.write(hex_use)#发出指令

def LCD_Set_Size(LCD_D0,LCD_D1):#设置大小
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(1).to_bytes(1,byteorder="little")#设置大小
    hex_use=hex_use+int(LCD_D0//256).to_bytes(1,byteorder="little")#Data0
    hex_use=hex_use+int(LCD_D0%256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int(LCD_D1//256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int(LCD_D1%256).to_bytes(1,byteorder="little")#Data3
    ser.write(hex_use)#发出指令
    
def LCD_Set_Color(LCD_D0,LCD_D1):#设置颜色（FC,BC）
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(2).to_bytes(1,byteorder="little")#设置颜色
    hex_use=hex_use+int(LCD_D0//256).to_bytes(1,byteorder="little")#Data0
    hex_use=hex_use+int(LCD_D0%256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int(LCD_D1//256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int(LCD_D1%256).to_bytes(1,byteorder="little")#Data3
    ser.write(hex_use)#发出指令
    
def LCD_Photo(LCD_X,LCD_Y,LCD_X_Size,LCD_Y_Size,Page_Add):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Size(LCD_X_Size,LCD_Y_Size)
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#显示彩色图片
    hex_use=hex_use+int(Page_Add//256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Page_Add%256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        time.sleep(0.001)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def LCD_ADD(LCD_X,LCD_Y,LCD_X_Size,LCD_Y_Size):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Size(LCD_X_Size,LCD_Y_Size)
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(7).to_bytes(1,byteorder="little")#载入地址
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        time.sleep(0.001)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def LCD_DATA(data_w,size):#往LCD写入指定大小的数据
    #先把数据传输完成
    hex_use=b''
    for i in range(0,64):#256字节数据分为64个指令
        hex_use=hex_use+int(4).to_bytes(1,byteorder="little")#多次写入Flash
        hex_use=hex_use+int(i).to_bytes(1,byteorder="little")#低位地址
        hex_use=hex_use+data_w[i*4+0].to_bytes(1,byteorder="little")#Data0
        hex_use=hex_use+data_w[i*4+1].to_bytes(1,byteorder="little")#Data1
        hex_use=hex_use+data_w[i*4+2].to_bytes(1,byteorder="little")#Data2
        hex_use=hex_use+data_w[i*4+3].to_bytes(1,byteorder="little")#Data3
    hex_use=hex_use+int(2).to_bytes(1,byteorder="little")#对Flash操作
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#经过擦除，写Flash
    hex_use=hex_use+int(8).to_bytes(1,byteorder="little")#Data0
    hex_use=hex_use+int(size//256).to_bytes(1,byteorder="little")#Data1
    hex_use=hex_use+int(size%256).to_bytes(1,byteorder="little")#Data2
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")#Data3
    ser.write(hex_use)#发出指令
   
def Write_LCD_Photo_fast(x_star,y_star,x_size,y_size,Photo_name):#往Flash里面写入Bin格式的照片
    filepath=Photo_name+'.bin'#合成文件名称
    try:#尝试打开bin文件
        binfile=open(filepath,'rb')#以只读方式打开
    except:#出现异常
        print('找不到“'+filepath+'”文件,请检查其位置是否位于当前目录下');
        return 0
    Fsize=os.path.getsize(filepath)
    print('找到“'+filepath+'”文件,大小：'+str(Fsize)+' B');
    u_time=time.time()
    #进行地址写入
    LCD_ADD(x_star,y_star,x_size,y_size)
    for i in range(0,Fsize//256):#每次写入一个Page
        Fdata=binfile.read(256)
        LCD_DATA(Fdata,256)#(page,数据，大小)
    if(Fsize%256 !=0):#还存在没写完的数据
        Fdata=binfile.read(Fsize%256)#将剩下的数据读完
        for i in range(Fsize%256,256):
            Fdata=Fdata+int(255).to_bytes(1,byteorder="little")#不足位置补充0xFF
        LCD_DATA(Fdata,Fsize%256)#(page,数据，大小)
    u_time=time.time()-u_time
    print(filepath+' 显示完成,耗时'+str(u_time)+'秒')

def Write_LCD_Photo_fast1(x_star,y_star,x_size,y_size,Photo_name):#往Flash里面写入Bin格式的照片
    filepath=Photo_name+'.bin'#合成文件名称
    try:#尝试打开bin文件
        binfile=open(filepath,'rb')#以只读方式打开
    except:#出现异常
        print('找不到“'+filepath+'”文件,请检查其位置是否位于当前目录下');
        return 0
    Fsize=os.path.getsize(filepath)
    print('找到“'+filepath+'”文件,大小：'+str(Fsize)+' B');
    u_time=time.time()
    #进行地址写入
    LCD_ADD(x_star,y_star,x_size,y_size)
    hex_use=bytearray()#空数组
    for j in range(0,Fsize//256):#每次写入一个Page
        data_w=binfile.read(256)
        #先把数据格式转换好
        for i in range(0,64):#256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i*4+0])
            hex_use.append(data_w[i*4+1])
            hex_use.append(data_w[i*4+2])
            hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if(Fsize%256 !=0):#还存在没写完的数据
        data_w=binfile.read(Fsize%256)#将剩下的数据读完
        for i in range(Fsize%256,256):
            data_w=data_w+int(255).to_bytes(1,byteorder="little")#不足位置补充0xFF
        for i in range(0,64):#256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i*4+0])
            hex_use.append(data_w[i*4+1])
            hex_use.append(data_w[i*4+2])
            hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(Fsize%256)
        hex_use.append(0)  
    hex_use.append(2)
    hex_use.append(3)
    hex_use.append(9)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    ser.write(hex_use)#发出指令
    u_time=time.time()-u_time
    print(filepath+' 显示完成,耗时'+str(u_time)+'秒')
    

def Write_LCD_Screen_fast(x_star,y_star,x_size,y_size,Photo_data):#往Flash里面写入Bin格式的照片
    LCD_ADD(x_star,y_star,x_size,y_size)
    Photo_data_use=Photo_data
    hex_use=bytearray()#空数组
    for j in range(0,x_size*y_size*2//256):#每次写入一个Page
        data_w=Photo_data_use[:256]
        Photo_data_use=Photo_data_use[256:]
        cmp_use=[]#空数组,
        for i in range(0,64):#256字节数据分为64个指令
            cmp_use.append(data_w[i*4+0]*256*256*256+data_w[i*4+1]*256*256+data_w[i*4+2]*256+data_w[i*4+3])
        result=max(set(cmp_use),key=cmp_use.count)#统计出现最多的数据
        hex_use.append(2)
        hex_use.append(4)
        color_ram=result
        hex_use.append(color_ram//(256*256*256))
        color_ram=color_ram%(256*256*256)
        hex_use.append(color_ram//(256*256))
        color_ram=color_ram%(256*256)
        hex_use.append(color_ram//256)
        hex_use.append(color_ram%256)
        #先把数据格式转换好
        for i in range(0,64):#256字节数据分为64个指令
            if((data_w[i*4+0]*256*256*256+data_w[i*4+1]*256*256+data_w[i*4+2]*256+data_w[i*4+3])!=result):#
                hex_use.append(4)
                hex_use.append(i)
                hex_use.append(data_w[i*4+0])
                hex_use.append(data_w[i*4+1])
                hex_use.append(data_w[i*4+2])
                hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if(x_size*y_size*2%256 !=0):#还存在没写完的数据
        data_w=Photo_data_use#将剩下的数据读完
        for i in range(x_size*y_size*2%256,256):
            data_w.append(0xff)#不足位置补充0xFF
        for i in range(0,64):#256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i*4+0])
            hex_use.append(data_w[i*4+1])
            hex_use.append(data_w[i*4+2])
            hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(x_size*y_size*2%256)
        hex_use.append(0)
    ser.write(hex_use)#发出指令
    
#对发送的数据进行编码分析,缩短数据指令
def Write_LCD_Screen_fast1(x_star,y_star,x_size,y_size,Photo_data):#往Flash里面写入Bin格式的照片
    LCD_ADD(x_star,y_star,x_size,y_size)
    Photo_data_use=Photo_data
    hex_use=bytearray()#空数组
    for j in range(0,x_size*y_size*2//256):#每次写入一个Page
        data_w=Photo_data_use[:256]
        Photo_data_use=Photo_data_use[256:]
        #先把数据格式转换好
        for i in range(0,64):#256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i*4+0])
            hex_use.append(data_w[i*4+1])
            hex_use.append(data_w[i*4+2])
            hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if(x_size*y_size*2%256 !=0):#还存在没写完的数据
        data_w=Photo_data_use#将剩下的数据读完
        for i in range(x_size*y_size*2%256,256):
            data_w.append(0xff)#不足位置补充0xFF
        for i in range(0,64):#256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i*4+0])
            hex_use.append(data_w[i*4+1])
            hex_use.append(data_w[i*4+2])
            hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(x_size*y_size*2%256)
        hex_use.append(0)
    #等待传输完成
    hex_use.append(2)
    hex_use.append(3)
    hex_use.append(9)
    hex_use.append(0)
    hex_use.append(0)
    hex_use.append(0)
    ser.write(hex_use)#发出指令
    
def LCD_Photo_wb(LCD_X,LCD_Y,LCD_X_Size,LCD_Y_Size,Page_Add,LCD_FC,LCD_BC):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Size(LCD_X_Size,LCD_Y_Size)
    LCD_Set_Color(LCD_FC,LCD_BC)
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(1).to_bytes(1,byteorder="little")#显示单色图片
    hex_use=hex_use+int(Page_Add//256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Page_Add%256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        time.sleep(0.001)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def LCD_ASCII_32X64(LCD_X,LCD_Y,Txt,LCD_FC,LCD_BC,Num_Page):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Color(LCD_FC,LCD_BC)
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(2).to_bytes(1,byteorder="little")#显示ASCII
    hex_use=hex_use+int(ord(Txt)).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Num_Page//256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Num_Page%256).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        time.sleep(0.001)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def LCD_GB2312_16X16(LCD_X,LCD_Y,Txt,LCD_FC,LCD_BC):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Color(LCD_FC,LCD_BC)
    Txt_Data=Txt.encode('gb2312')
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#显示彩色图片
    hex_use=hex_use+int(Txt_Data[0]).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Txt_Data[1]).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        time.sleep(0.001)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def LCD_Photo_wb_MIX(LCD_X,LCD_Y,LCD_X_Size,LCD_Y_Size,Page_Add,LCD_FC,BG_Page):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Size(LCD_X_Size,LCD_Y_Size)
    LCD_Set_Color(LCD_FC,BG_Page)
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(4).to_bytes(1,byteorder="little")#显示单色图片
    hex_use=hex_use+int(Page_Add//256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Page_Add%256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        time.sleep(0.001)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def LCD_ASCII_32X64_MIX(LCD_X,LCD_Y,Txt,LCD_FC,BG_Page,Num_Page):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Color(LCD_FC,BG_Page)
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(5).to_bytes(1,byteorder="little")#显示ASCII
    hex_use=hex_use+int(ord(Txt)).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Num_Page//256).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Num_Page%256).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        #time.sleep(0.5)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break

def LCD_GB2312_16X16_MIX(LCD_X,LCD_Y,Txt,LCD_FC,BG_Page):#
    LCD_Set_XY(LCD_X,LCD_Y)
    LCD_Set_Color(LCD_FC,BG_Page)
    Txt_Data=Txt.encode('gb2312')
    hex_use=int(2).to_bytes(1,byteorder="little")#对LCD多次写入
    hex_use=hex_use+int(3).to_bytes(1,byteorder="little")#设置指令
    hex_use=hex_use+int(6).to_bytes(1,byteorder="little")#显示彩色图片
    hex_use=hex_use+int(Txt_Data[0]).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(Txt_Data[1]).to_bytes(1,byteorder="little")
    hex_use=hex_use+int(0).to_bytes(1,byteorder="little")
    ser.write(hex_use)#发出指令
    #等待收回信息
    while(1):
        time.sleep(0.2)
        recv = ser.read(ser.in_waiting)#.decode("UTF-8")#获取串口数据
        if(len(recv)!=0):
            break
    
def TIM1():#接收数据
    global timer1,time_out
    time_out=1
    timer1=threading.Timer(0.2,TIM1)#创建定时器,延时为1秒
    timer1.start()

def show_gif():#显示GIF动图
    global State_change,gif_num
    if(State_change==1):
        State_change=0
        gif_num=0
    if(State_change==0):
        LCD_Photo(0,0,240,240,gif_num*450)
        gif_num=gif_num+1
        if(gif_num>5):
            gif_num=0

def show_PC_state(FC,BC):#显示PC状态
    global State_change
    photo_add=3600
    num_add=3629
    if(State_change==1):
        State_change=0
        LCD_Photo_wb(0,0,240,240,photo_add,FC,BC)#放置背景
    if(State_change==0):
        CPU=int(psutil.cpu_percent(interval=0.5))
        mem=psutil.virtual_memory()
        RAM=int(mem.percent)
        battery = psutil.sensors_battery()
        BAT=int(battery.percent)
        if(CPU>=100):
            LCD_Photo_wb(120,24,24,66,20+num_add,FC,BC)
            CPU=CPU%100
        else:
            LCD_Photo_wb(120,24,24,66,21+num_add,FC,BC)
        LCD_Photo_wb(144,24,48,66,(CPU//10)*2+num_add,FC,BC)
        LCD_Photo_wb(192,24,48,66,(CPU%10)*2+num_add,FC,BC)
        if(RAM>=100):
            LCD_Photo_wb(120,87,24,66,20+num_add,FC,BC)
            RAM=RAM%100
        else:
            LCD_Photo_wb(120,87,24,66,21+num_add,FC,BC)
        LCD_Photo_wb(144,87,48,66,(RAM//10)*2+num_add,FC,BC)
        LCD_Photo_wb(192,87,48,66,(RAM%10)*2+num_add,FC,BC)
        if(BAT>=100):
            LCD_Photo_wb(120,150,24,66,20+num_add,FC,BC)
            BAT=BAT%100
        else:
            LCD_Photo_wb(120,150,24,66,21+num_add,FC,BC)
        LCD_Photo_wb(144,150,48,66,(BAT//10)*2+num_add,FC,BC)
        LCD_Photo_wb(192,150,48,66,(BAT%10)*2+num_add,FC,BC)
    
def show_Photo1():#显示照片
    global State_change
    FC=BLUE
    BC=BLACK
    if(State_change==1):
        State_change=0
        LCD_Photo(0,0,240,240,450*6)#放置背景
    if(State_change==0):
        time.sleep(0.5)
    
def show_PC_time():
    global State_change
    FC=YELLOW
    photo_add=450*7
    num_add=3651
    if(State_change==1):
        State_change=0
        LCD_Photo(0,0,240,240,photo_add)#放置背景
        LCD_ASCII_32X64_MIX(56+8,32,':',FC,photo_add,num_add)
        LCD_ASCII_32X64_MIX(136+8,32,':',FC,photo_add,num_add)
    if(State_change==0):
        time_h=int(datetime.now().hour)
        time_m=int(datetime.now().minute)
        time_S=int(datetime.now().second)
        LCD_ASCII_32X64_MIX(0+8,32,chr((time_h//10)+48),FC,photo_add,num_add)
        LCD_ASCII_32X64_MIX(32+8,32,chr((time_h%10)+48),FC,photo_add,num_add)
        LCD_ASCII_32X64_MIX(80+8,32,chr((time_m//10)+48),FC,photo_add,num_add)
        LCD_ASCII_32X64_MIX(112+8,32,chr((time_m%10)+48),FC,photo_add,num_add)
        LCD_ASCII_32X64_MIX(160+8,32,chr((time_S//10)+48),FC,photo_add,num_add)
        LCD_ASCII_32X64_MIX(192+8,32,chr((time_S%10)+48),FC,photo_add,num_add)
        time.sleep(0.2)
def Screen_Date_Process(Photo_data):#对数据进行转换处理
    Photo_data_use=Photo_data
    hex_use=bytearray()#空数组
    for j in range(0,size_USE_X1*size_USE_Y1*2//256):#每次写入一个Page
        data_w=Photo_data_use[:256]
        Photo_data_use=Photo_data_use[256:]
        cmp_use=[]#空数组,
        for i in range(0,64):#256字节数据分为64个指令
            cmp_use.append(data_w[i*4+0]*256*256*256+data_w[i*4+1]*256*256+data_w[i*4+2]*256+data_w[i*4+3])
        result=max(set(cmp_use),key=cmp_use.count)#统计出现最多的数据
        hex_use.append(2)
        hex_use.append(4)
        color_ram=result
        hex_use.append(color_ram//(256*256*256))
        color_ram=color_ram%(256*256*256)
        hex_use.append(color_ram//(256*256))
        color_ram=color_ram%(256*256)
        hex_use.append(color_ram//256)
        hex_use.append(color_ram%256)
        #先把数据格式转换好
        for i in range(0,64):#256字节数据分为64个指令
            if((data_w[i*4+0]*256*256*256+data_w[i*4+1]*256*256+data_w[i*4+2]*256+data_w[i*4+3])!=result):#
                hex_use.append(4)
                hex_use.append(i)
                hex_use.append(data_w[i*4+0])
                hex_use.append(data_w[i*4+1])
                hex_use.append(data_w[i*4+2])
                hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if(size_USE_X1*size_USE_Y1*2%256 !=0):#还存在没写完的数据
        data_w=Photo_data_use#将剩下的数据读完
        for i in range(size_USE_X1*size_USE_Y1*2%256,256):
            data_w.append(0xff)#不足位置补充0xFF
        for i in range(0,64):#256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i*4+0])
            hex_use.append(data_w[i*4+1])
            hex_use.append(data_w[i*4+2])
            hex_use.append(data_w[i*4+3])
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(size_USE_X1*size_USE_Y1*2%256)
        hex_use.append(0)
    return hex_use

#创建两个数据缓存区，防止冲突
def Screen_Date_get():#创建专门的函数来获取屏幕图像和处理转换数据
    global G_screnn0_OK,G_screnn1_OK,G_screnn0,G_screnn1,size_USE_X1,size_USE_Y1
    print("截图线程创建成功")
    size_PC=pyautogui.size()
    size_mode=1
    if(size_mode==0):#横向充满
        if(size_PC.width>=size_PC.height):
            size_USE_X1=240
            size_USE_Y1=240*size_PC.height//size_PC.width
        else:
            size_USE_X1=240
            size_USE_Y1=240
    elif(size_mode==1):#纵向充满
        if(size_PC.height>=size_PC.width):
            size_USE_X1=240*size_PC.width//size_PC.height
            size_USE_Y1=240
        else:
            size_USE_X1=240
            size_USE_Y1=240
    elif(size_mode==2):#拉伸充满
        size_USE_X1=240
        size_USE_Y1=240
    while(1):
        if(G_screnn0_OK==0 or G_screnn1_OK==0):
            hex_16RGB=bytearray()#空数组
            im=pyautogui.screenshot()#截屏需要110ms太慢了
            u_time1=time.time()
            if(size_mode==0):#横向充满
                if(size_PC.width>=size_PC.height):
                    im1=im.resize((size_USE_X1,size_USE_Y1))#进行缩放
                else:
                    im1=im.resize((240,240*size_PC.height//size_PC.width))#进行缩放                
                    im1=im1.crop((0,(240*size_PC.height//size_PC.width-240)//2,240,(240*size_PC.height//size_PC.width-240)//2+240))#进行中心裁剪#进行中心裁剪
            elif(size_mode==1):#纵向充满
                if(size_PC.height>=size_PC.width):
                    im1=im.resize((size_USE_X1,size_USE_Y1))#进行缩放
                else:
                    im1=im.resize((240*size_PC.width//size_PC.height,240))#进行缩放      
                    im1=im1.crop(((240*size_PC.width//size_PC.height-240)//2,0,(240*size_PC.width//size_PC.height-240)//2+240,240))#进行中心裁剪
            elif(size_mode==2):#拉伸充满
                im1=im.resize((size_USE_X1,size_USE_Y1))#进行缩放
            im2=im1.load()#直接将内存的数组加载出来处理
            for y in range(0,size_USE_Y1):
                for x in range(0,size_USE_X1):
                    hex_16RGB.append((im2[x,y][0]//8)*8+im2[x,y][1]//32)
                    hex_16RGB.append(((im2[x,y][1]%32)//4)*32+im2[x,y][2]//8)
            if(G_screnn0_OK==0):
                G_screnn0=Screen_Date_Process(hex_16RGB)
                G_screnn0_OK=1
            elif(G_screnn1_OK==0):
                G_screnn1=Screen_Date_Process(hex_16RGB)
                G_screnn1_OK=1
            u_time1=time.time()-u_time1
            u_time=time.time()
        time.sleep(0.001)

def show_PC_Screen():#显示照片
    global State_change
    global G_screnn0_OK,G_screnn1_OK,G_screnn0,G_screnn1,size_USE_X1,size_USE_Y1
    if(State_change==1):
        State_change=0
    if(State_change==0):
        if(G_screnn0_OK==1 or G_screnn1_OK==1):
            u_time=time.time()
            if(G_screnn0_OK==1):
                LCD_ADD((240-size_USE_X1)//2,(240-size_USE_Y1)//2,size_USE_X1,size_USE_Y1)
                ser.write(G_screnn0)
                G_screnn0_OK=0
            elif(G_screnn1_OK==1):
                LCD_ADD((240-size_USE_X1)//2,(240-size_USE_Y1)//2,size_USE_X1,size_USE_Y1)
                ser.write(G_screnn1)
                G_screnn1_OK=0
            u_time=time.time()-u_time
        time.sleep(0.001)

print("该设备具有"+str(psutil.cpu_count(logical=False))+"个内核和"+str(psutil.cpu_count())+"个逻辑处理器")
print("该CPU主频为"+str(round((psutil.cpu_freq().current/1000),1))+"GHZ")
print("当前CPU占用率为"+str(psutil.cpu_percent())+"%")#并不准确
mem = psutil.virtual_memory()
print("该设备具有"+str(round(mem.total/(1024*1024*1024)))+"GB的内存")
print("当前内存占用率为"+str(mem.percent)+"%")
print("开始运行时间"+datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S"))
battery = psutil.sensors_battery()
if battery.power_plugged:
	print("已连接电源线")
else:
	print("已断开电源线")
print("电池剩余电量"+str(battery.percent)+"%")

#创建定时器,延时为0.2秒
timer1=threading.Timer(0.2,TIM1)
time_out=0
State_change=1#状态发生变化
gif_num=0

port_list = list(serial.tools.list_ports.comports())#查询所有串口
if len(port_list) == 0:
   print('未检测到串口,请确保设备已连接到电脑')
else:#对串口进行监听，确保其为MSN设备
    for i in range(0,len(port_list)):
        try:#尝试打开串口
            ser=serial.Serial(port_list[i].name,19200,timeout =2)#初始化串口连接,初始使用
        except:#出现异常
            print(port_list[i].name+'无法打开,请检查是否被其他程序占用');#显示MSN设备数量
            continue#执行下一次循环
        time.sleep(0.25)#理论上MSN设备100ms要发送一次“ MSN01”,在250ms内至少会收到一次
        recv = ser.read(ser.in_waiting).decode("gbk")#获取串口数据
        if(len(recv)>5):#收到6个字符以上数据时才进行解析
            for n in range(0,len(recv)-5):#逐字解析编码
                if(ord(recv[n]) == 0):#当前字节为0时进行解析
                    if((recv[n+1] == 'M') and (recv[n+2] == 'S') and (recv[n+3] == 'N')):#确保为MSN设备
                        if((recv[n+4] >= '0') and (recv[n+4] <= '9') and (recv[n+5] >= '0')and (recv[n+5] <= '9')):#确保版本号为数字ASC码
                            My_MSN_Device.append(MSN_Device((port_list[i].name),(ord(recv[4])-48)*10+(ord(recv[5])-48)))#对MSN设备进行登记
                            hex_code=int(0).to_bytes(1,byteorder="little")#可以逐个加入数组
                            hex_code=hex_code+b'MSNCN'
                            ser.write(hex_code)#返回消息
                            #等待返回消息，确认连接
                            time.sleep(0.25)#理论上MSN设备100ms要发送一次“ MSN01”,在250ms内至少会收到一次
                            recv = ser.read(ser.in_waiting).decode("gbk")#获取串口数据
                            if((ord(recv[0]) == 0) and (recv[1] == 'M') and (recv[2] == 'S') and (recv[3] == 'N') and (recv[4] == 'C') and (recv[5] == 'N')):#确保为MSN设备
                                print('MSN设备'+str(len(My_MSN_Device))+'——'+port_list[i].name+'连接完成');#显示MSN设备数量
                            else:
                                print('MSN设备'+str(len(My_MSN_Device))+'无法连接,请检查连接是否正常');#显示MSN设备数量
                            break#退出当前for循环
    print('MSN设备数量为'+str(len(My_MSN_Device))+'个');#显示MSN设备数量
    num=0
    time1=0
    Read_M_SFR_Data(256)#读取u8在0x0100之后的128字节
    Print_MSN_Data()#解析字节中的数据格式
    MSN_Status=Read_MSN_Data(b'MSN_Status')
    MSN_Status=Read_MSN_Data(b'MSN_UID')
    try:#尝试建立屏幕截屏线程
    
        Thread1=threading.Thread(target=Screen_Date_get)
        Thread1.start()
    except:
        print("警告,无法创建截图线程")
    
    #将电脑端文件烧录到MSU2的1MB Flash(出厂时已烧录，后续可以根据需要进行修改)
    #Write_Flash_Photo_fast(45*0,'1')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(450*1,'2')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(450*2,'3')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(450*3,'4')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(450*4,'5')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(450*5,'6')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(450*6,'C3')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(450*7,'C6')#240*240分辨率彩色图片，占用450个Page
    #Write_Flash_Photo_fast(3600,'Demo1')#240*240单色图片，占用29个Page
    #Write_Flash_Photo_fast(3629,'N48X66P')#48*66分辨率数码管图像，占用22个Page
    #Write_Flash_ZK(3651,'ASC64')#32*64分辨率ASCII表格，占用128个Page
    #Write_Flash_Photo_fast(3779,'logo')#240*102单色LOGO,占用12个Page
    #Write_Flash_Photo_fast(3791,'J1')#240*240单色图片，占用29个Page

    CPU=0
    FC=BLUE
    BC=BLACK
    key_on=0
    key_eff=0
    State_machine=1#定义初始状态
    timer1.start()#开启计时
    ADC_det=Read_ADC_CH(9)
    ADC_det=(ADC_det+Read_ADC_CH(9))/2
    ADC_det=ADC_det-125#根据125的阈值判断是否被按下
    #状态机检测和切换
    while(1):
        if(time_out==1):
            time_out=0
            if(Read_ADC_CH(9)<ADC_det):#按键按下
                key_on=1
            elif(key_on==1):
                key_eff=1
                key_on=0
            else:
                key_on=0
        if(key_eff==1):
            key_eff=0
            State_machine=State_machine+1
            if(State_machine>5):
                State_machine=0
            State_change=1
        if(State_machine==0):
            show_gif()
        elif(State_machine==1):
            show_PC_state(BLUE,BLACK)
        elif(State_machine==2):
            show_PC_state(RED,BLACK)
        elif(State_machine==3):
            show_Photo1()
        elif(State_machine==4):
            show_PC_time()
        elif(State_machine==5):
            show_PC_Screen()
            
            
 

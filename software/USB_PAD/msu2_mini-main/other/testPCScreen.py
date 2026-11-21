import serial,time,threading,pyautogui
from datetime import datetime, timedelta  # 用于获取当前时间
import serial.tools.list_ports as list_ports

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
size_USE_X1 = 160
size_USE_Y1 = 80

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
com_name=""

port_list = list(list_ports.comports())  # 查询所有串口
if len(port_list) == 0:
    print('未检测到串口,请确保设备已连接到电脑')
    # Label1.config(text="设备已连接",bg="GREEN")
    time.sleep(1)

else:  # 对串口进行监听，确保其为MSN设备
    for i in range(0, len(port_list)):
        try:  # 尝试打开串口
            ser = serial.Serial(port_list[i].name, 19200, timeout=2)  # 初始化串口连接,初始使用
        except:  # 出现异常
            print(port_list[i].name + '无法打开,请检查是否被其他程序占用')  # 显示MSN设备数量
            # ser.close()#将串口关闭，防止下次无法打开
            time.sleep(0.1)
            continue  # 执行下一次循环
        time.sleep(0.25)  # 理论上MSN设备100ms要发送一次“ MSN01”,在250ms内至少会收到一次
        recv = SER_Read()
        print(len(recv))
        if len(recv)>10:
            print("找到MSN设备，端口：",port_list[i].name)
            com_name=port_list[i].name
ser.close()

State_change = 1  # 状态发生变化
ser=serial.Serial(com_name,19200,timeout=0.5)
print(ser.is_open)


def LCD_Set_Color(LCD_D0, LCD_D1):  # 设置颜色（FC,BC）
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(2).to_bytes(1, byteorder="little")  # 设置颜色
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

def LCD_Set_XY(LCD_D0, LCD_D1):  # 设置起始位置
    hex_use = int(2).to_bytes(1, byteorder="little")  # 对LCD多次写入
    hex_use = hex_use + int(0).to_bytes(1, byteorder="little")  # 设置起始位置
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
    print(hex_use)
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

def show_PC_time():
    global State_change
    FC = YELLOW
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
        time.sleep(0.001)
        recv = SER_Read()  # .decode("UTF-8")#获取串口数据
        if (recv == 0):
            return 0
        elif (len(recv) != 0):
            if ((recv[0] != hex_use[0]) or (recv[1] != hex_use[1])):
                Device_State = 0  # 接收出错
            break        
        
def show_PC_Screen():  # 显示照片
    global State_change, Screen_Error, Device_State, Thread1
    global G_screnn0_OK, G_screnn1_OK, G_screnn0, G_screnn1, size_USE_X1, size_USE_Y1
    if (State_change == 1):
        State_change = 0
        Screen_Error = 0
        LCD_ADD((160 - size_USE_X1) // 2, (80 - size_USE_Y1) // 2, size_USE_X1, size_USE_Y1)
    if (State_change == 0):

        if (G_screnn0_OK == 1 or G_screnn1_OK == 1):
            # print("传输画面ing")
            u_time = time.time()
            if (G_screnn0_OK == 1):
                # LCD_ADD((240-size_USE_X1)//2,(240-size_USE_Y1)//2,size_USE_X1,size_USE_Y1)
                SER_Write(G_screnn0)
                G_screnn0_OK = 0
            elif (G_screnn1_OK == 1):
                # LCD_ADD((240-size_USE_X1)//2,(240-size_USE_Y1)//2,size_USE_X1,size_USE_Y1)
                SER_Write(G_screnn1)
                G_screnn1_OK = 0
            u_time = time.time() - u_time
            # print("传输耗时"+str(u_time))
            Screen_Error = 0
        else:
            Screen_Error = Screen_Error + 1
            if Screen_Error > 1000:
                Device_State = 0
                try:  # 尝试建立屏幕截屏线程
                    Thread1.stop()
                except:
                    print("警告,无法关闭截图线程")
                try:  # 尝试建立屏幕截屏线程
                    Thread1.start()
                except:
                    print("警告,无法创建截图线程")
            # print("无传输画面")
        time.sleep(0.05)

def Screen_Date_Process(Photo_data):  # 对数据进行转换处理
    Photo_data_use = Photo_data
    hex_use = bytearray()  # 空数组
    for j in range(0, size_USE_X1 * size_USE_Y1 // 128):  # 每次写入一个Page
        data_w = Photo_data_use[:128]
        Photo_data_use = Photo_data_use[128:]
        cmp_use = []  # 空数组,
        for i in range(0, 64):  # 256字节数据分为64个指令
            cmp_use.append(data_w[i * 2 + 0] * 65536 + data_w[i * 2 + 1])
        result = max(set(cmp_use), key=cmp_use.count)  # 统计出现最多的数据
        hex_use.append(2)
        hex_use.append(4)
        color_ram = result
        hex_use.append(color_ram >> 24)
        color_ram = color_ram % 16777216
        hex_use.append(color_ram >> 16)
        color_ram = color_ram % 65536
        hex_use.append(color_ram >> 8)
        hex_use.append(color_ram % 256)
        # 先把数据格式转换好
        for i in range(0, 64):  # 256字节数据分为64个指令
            if ((data_w[i * 2 + 0] * 65536 + data_w[i * 2 + 1]) != result):
                hex_use.append(4)
                hex_use.append(i)
                hex_use.append(data_w[i * 2 + 0] >> 8)
                hex_use.append(data_w[i * 2 + 0] % 256)
                hex_use.append(data_w[i * 2 + 1] >> 8)
                hex_use.append(data_w[i * 2 + 1] % 256)
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(1)
        hex_use.append(0)
        hex_use.append(0)
    if (size_USE_X1 * size_USE_Y1 * 2 % 256 != 0):  # 还存在没写完的数据
        data_w = Photo_data_use  # 将剩下的数据读完
        for i in range(size_USE_X1 * size_USE_Y1 * 2 % 256, 256):
            data_w.append(0xffff)  # 不足位置补充0xFFFF
        for i in range(0, 64):  # 256字节数据分为64个指令
            hex_use.append(4)
            hex_use.append(i)
            hex_use.append(data_w[i * 2 + 0] >> 8)
            hex_use.append(data_w[i * 2 + 0] % 256)
            hex_use.append(data_w[i * 2 + 1] >> 8)
            hex_use.append(data_w[i * 2 + 1] % 256)
        hex_use.append(2)
        hex_use.append(3)
        hex_use.append(8)
        hex_use.append(0)
        hex_use.append(size_USE_X1 * size_USE_Y1 * 2 % 256)
        hex_use.append(0)
    return hex_use


MG_screen_thread_running = False

# 创建两个数据缓存区，防止冲突
def Screen_Date_get():  # 创建专门的函数来获取屏幕图像和处理转换数据
    global G_screnn0_OK, G_screnn1_OK, G_screnn0, G_screnn1, size_USE_X1, size_USE_Y1
    print("截图线程创建成功")
    size_PC = pyautogui.size()
    size_mode = 0
    if (size_mode == 0):  # 横向充满
        if (size_PC.width >= size_PC.height * 2):  # 极宽屏
            size_USE_X1 = 160
            size_USE_Y1 = 160 * size_PC.height // size_PC.width
        else:
            size_USE_X1 = 160
            size_USE_Y1 = 80
    elif (size_mode == 1):  # 纵向充满
        if (size_PC.height * 2 >= size_PC.width):
            size_USE_X1 = 80 * size_PC.width // size_PC.height
            size_USE_Y1 = 80
        else:
            size_USE_X1 = 160
            size_USE_Y1 = 80
    elif (size_mode == 2):  # 拉伸充满
        size_USE_X1 = 160
        size_USE_Y1 = 80
    while (1):
        if (G_screnn0_OK == 0 or G_screnn1_OK == 0):
            u_time1 = time.time()
            hex_16RGB = []  # bytearray()
            im = pyautogui.screenshot()  # 截屏需要110ms太慢了#截屏约45ms，裁剪约18ms，格式转换24ms，
            if (size_mode == 0):  # 横向充满
                if (size_PC.width >= size_PC.height * 2):
                    im1 = im.resize((size_USE_X1, size_USE_Y1))  # 进行缩放
                else:
                    im1 = im.resize((160, 160 * size_PC.height // size_PC.width))  # 进行缩放
                    im1 = im1.crop((0, (160 * size_PC.height // size_PC.width - 80) // 2, 160,
                                    (160 * size_PC.height // size_PC.width - 80) // 2 + 80))  # 进行中心裁剪#进行中心裁剪
            elif (size_mode == 1):  # 纵向充满
                if (size_PC.height * 2 >= size_PC.width):
                    im1 = im.resize((size_USE_X1, size_USE_Y1))  # 进行缩放
                else:
                    im1 = im.resize((80 * size_PC.width // size_PC.height, 80))  # 进行缩放
                    im1 = im1.crop(((80 * size_PC.width // size_PC.height - 160) // 2, 0,
                                    (80 * size_PC.width // size_PC.height - 160) // 2 + 160, 80))  # 进行中心裁剪
            elif (size_mode == 2):  # 拉伸充满
                im1 = im.resize((size_USE_X1, size_USE_Y1))  # 进行缩放
            im2 = im1.load()  # 直接将内存的数组加载出来处理

            for y in range(0, size_USE_Y1):
                for x in range(0, size_USE_X1):
                    hex_16RGB.append(
                        ((im2[x, y][0] >> 3) << 11) | ((im2[x, y][1] >> 2) << 5) | (im2[x, y][2] >> 3))  # 先直接添加16bit数组
                    # hex_16RGB.append(Color_16bit>>8)
                    # hex_16RGB.append(Color_16bit%256)
                    # hex_16RGB.append((im2[x,y][0]>>3)*8+im2[x,y][1]//32)
                    # hex_16RGB.append(((im2[x,y][1]%32)//4)*32+im2[x,y][2]//8)

            if (G_screnn0_OK == 0):
                G_screnn0 = Screen_Date_Process(hex_16RGB)
                G_screnn0_OK = 1
            elif (G_screnn1_OK == 0):
                G_screnn1 = Screen_Date_Process(hex_16RGB)
                G_screnn1_OK = 1
            u_time1 = time.time() - u_time1
            print("截屏耗时" + str(u_time1))
        if MG_screen_thread_running:
            print('stop screenshot')
            break # exit screenshot thread
        time.sleep(0.05)

hex_code = int(0).to_bytes(1, byteorder="little")  # 可以逐个加入数组
hex_code = hex_code + b'MSNCN'
SER_Write(hex_code)  # 返回消息
# 等待返回消息，确认连接
time.sleep(0.25)  # 理论上MSN设备100ms要发送一次“ MSN01”,在250ms内至少会收到一次

Thread1 = threading.Thread(target=Screen_Date_get) 
Thread1.start()
while 1:
    # show_PC_time()
    # time.sleep(0.5)
    show_PC_Screen()
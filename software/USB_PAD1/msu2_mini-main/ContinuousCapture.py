import os
import time

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
        system_dpi = 96.0


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
        # print(self.dpi_width, self.dpi_height)

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
        """
        根据窗口标题查找窗口句柄

        Args:
            window_title: 窗口标题（可以是部分标题）

        Returns:
            窗口句柄，如果找不到返回None
        """

        def callback(hwnd, hwnds):
            if win32gui.IsWindowVisible(hwnd) and window_title in win32gui.GetWindowText(hwnd):
                hwnds.append(hwnd)
                return False  # 结束遍历，只需找到一个
            return True

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds[0] if hwnds else None

    def capture_window(self):
        """
        截取单个窗口

        Returns:
            PIL Image对象
        """
        # 检查窗口尺寸是否变化
        new_width, new_height = self.getRect()

        # 如果窗口尺寸变化，重新初始化资源
        if new_width != self.width or new_height != self.height:
            self.cleanup_resources()
            self.width = new_width
            self.height = new_height
            self.setup_resources()

        # 后台窗口使用PrintWindow代替BitBlt解决部分窗口黑屏问题, 但是PrintWindow不能截取桌面
        windll.user32.PrintWindow(self.hwnd, self.saveDC.GetSafeHdc(), self.print_mode)

        # 获取位图信息
        bmpinfo = self.saveBitMap.GetInfo()
        bmpstr = self.saveBitMap.GetBitmapBits(True)

        return bmpstr, bmpinfo['bmWidth'], bmpinfo['bmHeight']

    def capture_screen(self):
        """
        截取整个屏幕

        Returns:
            PIL Image对象
        """
        # 检查窗口尺寸是否变化
        new_width, new_height = self.getRect()

        # 如果窗口尺寸变化，重新初始化资源
        if new_width != self.width or new_height != self.height:
            self.cleanup_resources()
            self.width = new_width
            self.height = new_height
            self.setup_resources()

        # PrintWindow不能截取桌面，需要用BitBlt。BitBlt截取后台窗口时部分窗口会截取不到，只有黑色
        try:
            # 保存bitmap到内存设备描述表。win32con.NOTSRCCOPY 翻转颜色
            self.saveDC.BitBlt((0, 0), (self.dpi_width, self.dpi_height), self.mfcDC, (0, 0), win32con.SRCCOPY)
        except:
            pass

        # 获取位图信息
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

    def capture_to_file(self, save_path):
        """
        执行截图操作

        Args:
            save_path: 截图保存路径
        """
        self.capture_screen()
        # 保存位图到文件
        self.saveBitMap.SaveBitmapFile(self.saveDC, save_path)

    def continuous_capture(self, interval=1, duration=10, output_dir="screenshots",
                           pformat="bmp", callback=None):
        """
        连续截图函数

        Args:
            interval: 截图间隔（秒）
            duration: 总持续时间（秒）
            output_dir: 输出目录
            pformat: 图像格式，"bmp"或"png"或"jpg"
            callback: 可选的回调函数，接收两个参数：图像路径和PIL图像对象
        """
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 计算截图次数
        num_shots = int(duration / interval)

        print(f"开始连续截图，共 {num_shots} 次，间隔 {interval} 秒")

        for i in range(num_shots):
            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{i + 1:04d}.{pformat}"
            save_path = os.path.join(output_dir, filename)

            # 执行截图
            if pformat == "bmp":
                self.capture_to_file(save_path)
                pil_img = None
            else:
                pil_img = self.capture_to_pil()
                pil_img.save(save_path)

            print(f"已保存截图: {save_path}")

            # 调用回调函数（如果提供）
            if callback:
                callback(save_path, pil_img)

            # 等待下一次截图
            if i < num_shots - 1:  # 最后一次不需要等待
                time.sleep(interval)

        print("截图完成")

    def __del__(self):
        """ 析构函数，确保资源被正确释放 """
        self.cleanup_resources()


# 使用示例
if __name__ == "__main__":
    # 示例1：截取整个屏幕，每2秒一次，持续20秒，保存为PNG
    capture = ContinuousCapture()
    capture.continuous_capture(
        interval=2,
        duration=20,
        output_dir="screen_shots",
        format="png"
    )

    # 示例2：截取特定窗口（例如记事本），每1秒一次，持续10秒
    # capture = ContinuousCapture(
    #     capture_type="window",
    #     window_title="记事本"
    # )
    # capture.continuous_capture(
    #     interval=1,
    #     duration=10,
    #     output_dir="notepad_shots"
    # )

    # 示例3：使用回调函数处理截图
    # def process_image(path, img):
    #     if img:  # 如果不是BMP格式，img会是PIL图像对象
    #         # 在这里进行图像处理，例如调整大小、添加水印等
    #         small_img = img.resize((img.width // 2, img.height // 2))
    #         small_img.save(path.replace('.png', '_small.png'))
    #
    # capture = ContinuousCapture(capture_type="screen")
    # capture.continuous_capture(
    #     interval=1,
    #     duration=5,
    #     output_dir="processed_shots",
    #     format="png",
    #     callback=process_image
    # )

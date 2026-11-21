import argparse
import shutil
import os
import subprocess
import glob

# 替换为你的视频文件路径, 必须和video_path字符串相同
video_path:str = "test2.mp4" # 可以使用几乎所有视频格式, 包括jpg, gif等动图格式

# 截取视频从start_time秒到end_time秒的部分, 一般 3.6 秒左右刚好
# 之所以建议 3.6 是因为每 0.1 秒播放一帧, 而最大总帧数为 36
# 如果end_time大于总时长，则等价于总时长
start_time:float = 2.8
end_time:float = 5.7

# 是否旋转
# 0 是不旋转，1 是顺时针 90 度，2 是逆时针 90 度
transpose:int = 1
# 是否连续转两次, 0 是 False, 1 是 True (用于实现 180 度旋转)
rotate_double:int = 1

# 需要自行安装FFMPEG
# FFMPEG介绍: FFMPEG 是一个开源的多媒体处理工具
# 如果不愿意把ffmpeg添加到系统环境变量, 可以使用ffmpeg的文件路径
ffmpeg_path = "ffmpeg" # 可以使用文件路径替代
# ffprobe 是 ffmpeg 的一个子模块, 也可以使用ffprobe的文件路径
ffprobe_path = "ffprobe" # 可以使用文件路径替代

# 以下为不建议修改的配置---------------------------------------------------------------------------------
num_frames:int = 36  # 总帧数

# 是否保留临时文件
keep_temp_file:bool = True

# 输出图片名称格式
# out_image_format[0] 是前缀
# out_image_format[1] 是后缀, 要带上 '.'
# 可以使用几乎所有图片格式
out_image_format = ["A", ".png"]

# 输出图片的文件夹路径, 可以不管, 程序会自行创建该文件
output_folder:str = video_path + "_to_36_pictures"

# 运行前必须保证与临时文件同名的文件为不重要的文件
temp_cut_video:str = "tmp_cut.mp4"  # 临时截取视频
temp_rotate_video:str = "tmp_rotate.mp4"  # 临时旋转视频
temp_scale_video:str = "temp_scale.mp4"  # 临时放缩视频
temp_frames_folder:str = "temp_frames"  # 临时帧文件夹
temp_frame_format:str = "frame_%04d" + out_image_format[1]  # 临时帧文件

# 如果想要长宽比不变的话，可以把 height 可以选择
width: int = 160  # 像素宽度 不建议修改
# height: int = 80  # 像素长度 不建议修改
height = -1  # 不建议修改 但可以选择

def get_video_duration(_video_path) -> float:
    """获取视频的总时长（秒）"""
    command = [
        f"{ffprobe_path}",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        _video_path
    ]
    
    [print(i, end=" ") for i in command]
    print()
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        return float(result.stdout.strip())
    except ValueError:
        print("\033[31mPlease Check You Video File")
        exit()
    except FileNotFoundError:
        print("PLEASE INSTALL FFMPEG")
        print("GOTO FFMPEG DOWNLOAD WEB: https://ffmpeg.org/download.html")
        exit()

def cut_video_rotate(_video_path: str, _start_time: float, _end_time: float, _width: int, _height: int) -> str:
    """截取视频从start_time到end_time的部分
    并旋转视频
    """
    # 截取视频
    command = [
        f"{ffmpeg_path}",
        "-i",
        _video_path,
        "-ss",
        str(_start_time),
        "-to",
        str(_end_time),
        temp_cut_video
    ]
    
    [print(i, end=" ") for i in command]
    print()
    try:
        subprocess.run(command, capture_output=True)
    except FileNotFoundError:
        print("PLEASE INSTALL FFMPEG")
        print("GOTO FFMPEG DOWNLOAD WEB: https://ffmpeg.org/download.html")
        exit()
    # 放缩视频
    command = [
        f"{ffmpeg_path}",
        "-i",
        temp_cut_video,
        "-vf",
        f"scale={_width}:{_height}",
        "-crf",
        "0",
        temp_scale_video
    ]
    
    [print(i, end=" ") for i in command]
    print()
    try:
        subprocess.run(command, capture_output=True)
    except FileNotFoundError:
        print("PLEASE INSTALL FFMPEG")
        print("GOTO FFMPEG DOWNLOAD WEB: https://ffmpeg.org/download.html")
        exit()
    # 旋转视频
    if transpose == 0:
        return temp_scale_video
    else:
        if rotate_double == 0:
            transpose_string = f"transpose={transpose}"
        else:
            transpose_string = f"transpose={transpose}, transpose={transpose}"
            
        command = [
            f"{ffmpeg_path}",
            "-i",
            temp_scale_video,
            "-vf",
            transpose_string,
            "-codec:v",
            "libx264",
            "-codec:a",
            "copy",
            temp_rotate_video
        ]
        
        [print(i, end=" ") for i in command]
        print()

        try:
            subprocess.run(command, capture_output=True)
        except FileNotFoundError:
            print("PLEASE INSTALL FFMPEG")
            print("GOTO FFMPEG DOWNLOAD WEB: https://ffmpeg.org/download.html")
            exit()
        return temp_rotate_video

def extract_frames(_video_path, _output_folder, _num_frames=36):
    # 确保输出文件夹存在
    if not os.path.exists(_output_folder):
        os.makedirs(_output_folder)
    # 确保临时文件夹存在
    if not os.path.exists(temp_frames_folder):
        os.makedirs(temp_frames_folder)

    # 拆解视频为帧
    command = [
        "ffmpeg",
        "-i",
        _video_path,
        f"{temp_frames_folder}/{temp_frame_format}"
    ]
    
    [print(i, end=" ") for i in command]
    print()
    try:
        subprocess.run(command, capture_output=True)
    except FileNotFoundError:
        print("PLEASE INSTALL FFMPEG")
        print("GOTO FFMPEG DOWNLOAD WEB: https://ffmpeg.org/download.html")
        exit()
    # 获取所有帧文件
    jpg_files = sorted(glob.glob(f"{temp_frames_folder}/*{out_image_format[1]}"))
    total_frames = len(jpg_files)
    print(f"总帧数: {total_frames}帧")
    if total_frames == 0:
        print("提取帧失败")
        return
    # 计算需要提取的帧索引
    frame_indices = [int(total_frames * (i / (_num_frames + 1))) for i in range(1, _num_frames + 1)]
    [print(i, end=" ") for i in frame_indices]
    print()
    [print(frame_indices[i] - frame_indices[i - 1], end=" ") for i in range(1, len(frame_indices))]
    print()
    # 提取并处理帧
    for i, index in enumerate(frame_indices, 0):
        input_path = jpg_files[index]
        output_path = os.path.join(_output_folder, out_image_format[0] + str(i) + out_image_format[1])
        shutil.copyfile(input_path, output_path)


# 使用
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="将视频或动图转换为 36 张图片")
    parser.add_argument("-i", required=False, help="str 输入视频或动图文件的路径")
    parser.add_argument("-s", required=False, help="float 截取视频的起始部分 (单位: 秒)")
    parser.add_argument("-t", required=False, help="float 截取视频的结束部分 (单位: 秒)")
    parser.add_argument("-r", required=False, help="int 旋转视频: 0 是不旋转，1 是顺时针 90 度，2 是逆时针 90 度")
    parser.add_argument("-rr", required=False, help="int 额外连续转多次 (用于实现 180 度旋转)")
    args = parser.parse_args()
    if args.i is not None:
        video_path = args.i
        output_folder  = video_path + "_to_36_pictures"
    if args.s is not None:
        start_time = float(args.s)
    if args.t is not None:
        end_time = float(args.t)
    if args.r is not None:
        transpose = int(args.r)
    if args.rr is not None:
        rotate_double = int(args.rr)

    # 防止输出阻塞, 先删除同名文件
    if os.path.exists(temp_cut_video):
        os.remove(temp_cut_video)
        print("REMOVED", temp_cut_video)
    if os.path.exists(temp_scale_video):
        os.remove(temp_scale_video)
        print("REMOVED", temp_scale_video)
    if os.path.exists(temp_rotate_video):
        os.remove(temp_rotate_video)
        print("REMOVED", temp_rotate_video)
    if os.path.exists(temp_frames_folder):
        # 删除临时帧文件夹
        shutil.rmtree(temp_frames_folder)
        print("REMOVED", temp_frames_folder)
    # 获取视频总时长
    duration = get_video_duration(video_path)
    # 如果end_time大于总时长，设置为总时长
    if end_time > duration:
        end_time = duration
    if start_time >= end_time:
        print("Start Time 配置错误")
        exit()

    output_file:str = cut_video_rotate(video_path, _start_time=start_time, _end_time=end_time, _width=width, _height=height)

    # 对截取放缩旋转后的视频进行帧提取
    extract_frames(output_file, output_folder, _num_frames=num_frames)
    print("Start Time: ", start_time, "s", sep="")
    print("End Time: ", end_time, "s", sep="")

    if not keep_temp_file:
        if os.path.exists(temp_cut_video):
            os.remove(temp_cut_video)
            print("REMOVED", temp_cut_video)
        if os.path.exists(temp_scale_video):
            os.remove(temp_scale_video)
            print("REMOVED", temp_scale_video)
        if os.path.exists(temp_rotate_video):
            os.remove(temp_rotate_video)
            print("REMOVED", temp_rotate_video)
        if os.path.exists(temp_frames_folder):
            # 删除临时帧文件夹
            shutil.rmtree(temp_frames_folder)
            print("REMOVED", temp_frames_folder)

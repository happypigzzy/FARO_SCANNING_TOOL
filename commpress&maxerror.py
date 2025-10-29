# skip_star_tcp.py
import cv2
import numpy as np
import subprocess
import pytesseract
import re
import os

# 输入需要解析的视频：视频会自动解码为H.264 480p mp4封装视频
input = r"C:\Users\tiantian\b1.mp4"

pytesseract.pytesseract.tesseract_cmd = r'C:\Users\tiantian\AppData\Local\Tesseract-OCR\tesseract.exe'
VIDEO_PATH = r"1.mp4"
OUTPUT_TXT = "valid_xyz.txt"

# 同时捕获数字或 *****
NUM_OR_STAR_RE = re.compile(r'([+-]?\d+\.\d+|\*{4,5})')


def compress_video(input_path, output_path, crf=28, preset='ultrafast'):
    """
    压缩视频并转换编码格式

    参数:
        input_path (str): 输入视频文件路径
        output_path (str): 输出视频文件路径
        crf (int): 恒定速率因子，控制视频质量 (0-51，默认23)
        preset (str): 编码预设，影响编码速度和压缩效率
    """
    # 计算目标分辨率 (保持16:10宽高比)
    # 原始分辨率 3200x2000 = 16:10
    # 480p 保持16:10比例的目标分辨率是 768x480
    target_width = 768
    target_height = 480

    command = [
        'ffmpeg',
        '-i', input_path,  # 输入文件
        '-ss', '00:00:05',
        '-vf', f'scale={target_width}:{target_height}',  # 缩放视频
        '-c:v', 'libx264',  # 使用H.264编码
        '-crf', str(crf),  # 质量参数
        '-preset', preset,  # 编码速度预设
        '-r', '20',  # 帧率保持20fps
        '-c:a', 'aac',  # 音频编码为AAC
        '-b:a', '32k',  # 音频比特率
        '-y',  # 覆盖输出文件
        output_path
    ]

    try:
        print(f"开始处理视频: {os.path.basename(input_path)}")
        print(" ".join(command))  # 打印执行的命令

        # 执行FFmpeg命令
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"视频处理成功! 输出文件: {output_path}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"处理失败。错误信息: {e.stderr}")
        return False
    except FileNotFoundError:
        print("未找到FFmpeg，请确保已安装并添加到系统环境变量。")
        return False


def extract_data(filename):
    data = []  # 存储所有有效数据 (位移值, x, y, z, frame)
    pattern = r'Frame(\d+):\s+X\s+([-\d.]+)\s+Y\s+([-\d.]+)\s+Z\s+([-\d.]+)\s+->\s+([\d.]+)\s+mm'

    with open(filename, 'r') as file:
        for line in file:
            match = re.search(pattern, line)
            if match:
                try:
                    frame = match.group(1)
                    x = float(match.group(2))
                    y = float(match.group(3))
                    z = float(match.group(4))
                    displacement = float(match.group(5))

                    # 只保留0到3之间的有效数据
                    if 0 <= displacement <= 3:
                        data.append((displacement, x, y, z, frame))
                    else:
                        print(f"排除超出范围的数据: Frame{frame} 位移值 {displacement} mm")
                except ValueError as e:
                    print(f"数据转换错误: {line.strip()} - {e}")

    return data


def calculate_median(data):
    """计算位移值的中位数"""
    if not data:
        return None

    # 提取位移值
    displacements = [item[0] for item in data]

    # 排序
    sorted_displacements = sorted(displacements)
    n = len(sorted_displacements)

    # 计算中位数
    if n % 2 == 1:
        # 奇数个数据，取中间值
        median = sorted_displacements[n // 2]
    else:
        # 偶数个数据，取中间两个数的平均值
        mid1 = sorted_displacements[n // 2 - 1]
        mid2 = sorted_displacements[n // 2]
        median = (mid1 + mid2) / 2

    return median


def main():
    if not os.path.isfile(VIDEO_PATH):
        print("❌ 视频不存在");
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    ret, first = cap.read()
    if not ret:
        print("❌ 读不到第一帧");
        return

    roi = cv2.selectROI("在第一帧框 ROI（空格确认）", first, False)
    cv2.destroyAllWindows()
    x, y, w, h = map(int, roi)
    print("ROI =", roi)

    fout = open(OUTPUT_TXT, "w", encoding="utf-8")
    max_err = 0.0
    hits = 0
    step = 5  # 可改成 1 不跳帧

    frame_id = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_id % step != 0:
            frame_id += 1
            continue

        roi_img = frame[y:y + h, x:x + w]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        sharpen = cv2.filter2D(gray, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
        _, bin_img = cv2.threshold(sharpen, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        text = pytesseract.image_to_string(bin_img, lang='eng',
                                           config='--psm 6 -c tessedit_char_whitelist=0123456789.+-*')
        tokens = NUM_OR_STAR_RE.findall(text)

        # 只保留前 3 个 token
        tokens = tokens[:3]
        if len(tokens) != 3:
            frame_id += 1
            continue

        # 只要出现 * 就整组丢弃
        if any('*' in tok for tok in tokens):
            frame_id += 1
            continue

        try:
            x_val, y_val, z_val = map(float, tokens)
        except ValueError:
            frame_id += 1
            continue

        hits += 1
        err = (x_val ** 2 + y_val ** 2 + z_val ** 2) ** 0.5
        max_err = max(max_err, err)
        out = f"Frame{frame_id}: X {x_val:.4f} Y {y_val:.4f} Z {z_val:.4f} -> {err:.6f} mm"
        print(out)
        fout.write(out + "\n")

        frame_id += 1

    cap.release()
    fout.close()
    print(f"\n✅ 完成，有效坐标 {hits} 组，最大空间误差 = {max_err:.6f} mm")

    filename = "valid_xyz.txt"

    try:
        data = extract_data(filename)

        if not data:
            print("未找到有效数据")
            return

        # 找到最大位移值及其对应的数据
        max_displacement = 0
        max_data = None

        for displacement, x, y, z, frame in data:
            if displacement > max_displacement:
                max_displacement = displacement
                max_data = (displacement, x, y, z, frame)

        # 计算所有有效数据的平均值
        total_displacement = sum(item[0] for item in data)
        avg_displacement = total_displacement / len(data)

        # 计算中位数
        median_displacement = calculate_median(data)

        # 计算中位数和平均数的差值
        median_avg_difference = abs(median_displacement - avg_displacement)

        # 可选：输出所有数据供参考
        print("\n所有有效数据:")
        print("帧号\t\t位移值(mm)\tX\t\tY\t\tZ")
        for displacement, x, y, z, frame in data:
            print(f"Frame{frame}\t{displacement:.6f}\t\t{x:.6f}\t{y:.6f}\t{z:.6f}")
        print(f"找到 {len(data)} 个有效位移数据 (范围: 0-3 mm)")
        print(f"平均值: {avg_displacement:.6f} mm")
        print(f"中位数: {median_displacement:.6f} mm")
        print(f"中位数与平均数的差值: {median_avg_difference:.6f} mm")

        # 根据差值大小给出评估
        if median_avg_difference < 0.01:
            print("数据分布评估: 非常对称 (中位数与平均数几乎相等)")
        elif median_avg_difference < 0.05:
            print("数据分布评估: 相对对称")
        elif median_avg_difference < 0.1:
            print("数据分布评估: 轻微偏态")
        else:
            print("数据分布评估: 明显偏态 (可能存在异常值影响)")

        print("\n最大值详细信息:")
        print(f"帧号: Frame{max_data[4]}")
        print(f"位移值: {max_data[0]:.6f} mm")
        print(f"X: {max_data[1]:.6f}")
        print(f"Y: {max_data[2]:.6f}")
        print(f"Z: {max_data[3]:.6f}")

    except FileNotFoundError:
        print(f"文件 {filename} 未找到")


if __name__ == "__main__":
    input_video = input  # 替换为你的输入视频路径
    output_video = "1.mp4"  # 输出视频路径

    # 压缩视频
    success = compress_video(input_video, output_video)

    if success:
        # 显示文件大小变化
        if os.path.exists(input_video) and os.path.exists(output_video):
            original_size = os.path.getsize(input_video) / (1024 * 1024)  # MB
            compressed_size = os.path.getsize(output_video) / (1024 * 1024)  # MB
            reduction = (1 - (compressed_size / original_size)) * 100

            print(f"原始大小: {original_size:.2f} MB")
            print(f"压缩后大小: {compressed_size:.2f} MB")
            print(f"体积减少: {reduction:.2f}%")
    main()
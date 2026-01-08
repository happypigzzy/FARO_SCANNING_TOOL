# skip_star_tcp.py
import cv2
import io
import sys
import numpy as np
import subprocess
import pytesseract
import re
import os
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SIMHEI']
plt.rcParams['axes.unicode_minus'] = False
from scipy.stats import skew, kurtosis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='gb18030')

input = r"C:\Users\0070\Desktop\宁波52\11\4600-522690\重定位数据\1021.mp4"

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
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
        print(f"error处理失败。错误信息: {e.stderr}")
        return False
    except FileNotFoundError:
        print("error未找到FFmpeg，请确保已安装并添加到系统环境变量。")
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


def calculate_advanced_stats(data):
    """计算高级统计指标"""
    if not data:
        return None

    displacements = [item[0] for item in data]

    # 基础统计量
    mean_val = np.mean(displacements)
    median_val = np.median(displacements)
    std_dev = np.std(displacements)  # 标准差
    variance = np.var(displacements)  # 方差

    # 百分位数
    percentiles = {
        '25th': np.percentile(displacements, 25),
        '50th': np.percentile(displacements, 50),
        '75th': np.percentile(displacements, 75),
        '90th': np.percentile(displacements, 90),
        '95th': np.percentile(displacements, 95)
    }

    # 四分位距
    iqr = percentiles['75th'] - percentiles['25th']

    # 偏度和峰度
    skewness = skew(displacements)
    kurt = kurtosis(displacements)

    # 变异系数
    cv = (std_dev / mean_val) * 100 if mean_val != 0 else 0

    return {
        'mean': mean_val,
        'median': median_val,
        'std_dev': std_dev,
        'variance': variance,
        'percentiles': percentiles,
        'iqr': iqr,
        'skewness': skewness,
        'kurtosis': kurt,
        'cv': cv
    }


def plot_error_distribution(data):
    """绘制误差分布图"""
    if not data:
        print("无数据可绘制")
        return

    displacements = [item[0] for item in data]

    # 创建图形
    plt.figure(figsize=(15, 10))

    # 1. 直方图
    plt.subplot(2, 3, 1)
    n, bins, patches = plt.hist(displacements, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    plt.xlabel('位移误差 (mm)')
    plt.ylabel('频数')
    plt.title('tcp重定位运动误差分布直方图')
    plt.grid(True, alpha=0.3)

    # 添加统计信息到直方图
    stats_text = f'平均值: {np.mean(displacements):.4f} mm\n标准差: {np.std(displacements):.4f} mm'
    plt.text(0.95, 0.95, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 2. 箱线图
    plt.subplot(2, 3, 2)
    box_plot = plt.boxplot(displacements, patch_artist=True)
    box_plot['boxes'][0].set_facecolor('lightgreen')
    plt.ylabel('重定位过程位移误差 (mm)')
    plt.title('误差箱线图')
    plt.grid(True, alpha=0.3)

    # 3. 概率密度图
    plt.subplot(2, 3, 3)
    from scipy.stats import gaussian_kde
    density = gaussian_kde(displacements)
    xs = np.linspace(min(displacements), max(displacements), 200)
    plt.plot(xs, density(xs), 'b-', linewidth=2)
    plt.fill_between(xs, density(xs), alpha=0.3, color='blue')
    plt.xlabel('位移误差 (mm)')
    plt.ylabel('概率密度')
    plt.title('重定位误差概率密度分布')
    plt.grid(True, alpha=0.3)

    # 4. 累积分布函数图
    plt.subplot(2, 3, 4)
    sorted_data = np.sort(displacements)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    plt.plot(sorted_data, yvals, 'r-', linewidth=2)
    plt.xlabel('位移误差 (mm)')
    plt.ylabel('累积概率')
    plt.title('误差累积分布函数')
    plt.grid(True, alpha=0.3)

    # 5. Q-Q图（正态概率图）
    plt.subplot(2, 3, 5)
    from scipy.stats import probplot
    probplot(displacements, dist="norm", plot=plt)
    plt.title('Q-Q图 (正态检验)')
    plt.grid(True, alpha=0.3)

    # 6. 时间序列图
    plt.subplot(2, 3, 6)
    frames = [int(item[4]) for item in data]
    plt.plot(frames, displacements, 'b.-', alpha=0.7, markersize=3)
    plt.xlabel('帧号')
    plt.ylabel('位移误差 (mm)')
    plt.title('误差时间序列')
    plt.grid(True, alpha=0.3)

    # 添加移动平均线
    window_size = min(10, len(displacements) // 10)
    if window_size > 1:
        moving_avg = np.convolve(displacements, np.ones(window_size) / window_size, mode='valid')
        plt.plot(frames[window_size - 1:], moving_avg, 'r-', linewidth=2, label=f'{window_size}帧移动平均')
        plt.legend()

    plt.tight_layout()
    plt.savefig('error_analysis_comprehensive.png', dpi=300, bbox_inches='tight')
    print(" 误差分析图表已保存为 'error_analysis_comprehensive.png'")
    plt.show()


def comprehensive_error_analysis(data):
    """综合误差分析报告"""
    if not data:
        print("无有效数据进行评估")
        return

    displacements = [item[0] for item in data]

    # 计算高级统计指标
    stats = calculate_advanced_stats(data)

    print("\n" + "=" * 70)
    print("                   以下是机器人重定位误差综合评估")
    print("=" * 70)

    print(f"\n 基础统计:")
    print(f"   样本数量: {len(displacements)}")
    print(f"   平均值: {stats['mean']:.6f} mm")
    print(f"   中位数: {stats['median']:.6f} mm")
    print(f"   最小值: {min(displacements):.6f} mm")
    print(f"   最大值: {max(displacements):.6f} mm")
    print(f"   极差: {max(displacements) - min(displacements):.6f} mm")

    print(f"\n 变异性指标:")
    print(f"   标准差: {stats['std_dev']:.6f} mm")
    print(f"   方差: {stats['variance']:.6f} (mm)^2")
    print(f"   变异系数: {stats['cv']:.2f}%")
    print(f"   四分位距 (IQR): {stats['iqr']:.6f} mm")

    print(f"\n 百分位数分析:")
    for key, value in stats['percentiles'].items():
        print(f"   {key}分位数: {value:.6f} mm")

    print(f"\n 分布形状分析:")
    print(f"   偏度: {stats['skewness']:.4f}")
    skew_interpretation = "右偏分布" if stats['skewness'] > 0.5 else "左偏分布" if stats['skewness'] < -0.5 else "基本对称"
    print(f"   分布形态: {skew_interpretation}")

    print(f"   峰度: {stats['kurtosis']:.4f}")
    kurt_interpretation = "尖峰分布" if stats['kurtosis'] > 1 else "低峰分布" if stats['kurtosis'] < -1 else "接近正态峰度"
    print(f"   峰度特征: {kurt_interpretation}")

    print(f"\n 质量评估:")
    if stats['cv'] < 10:
        print("   ok 误差稳定性: 优秀 (变异系数 < 10%)")
    elif stats['cv'] < 20:
        print("   fine  误差稳定性: 良好 (变异系数 10-20%)")
    else:
        print("   warning 误差稳定性: 参考结果图以评估机器人精度 (变异系数 > 20%)")

    if stats['iqr'] / stats['mean'] < 0.1:
        print("   ok 数据集中度: 优秀")
    elif stats['iqr'] / stats['mean'] < 0.2:
        print("   fine  数据集中度: 良好")
    else:
        print("   warning 数据集中度: 分散")

    # 偏度对误差分析的影响
    if abs(stats['skewness']) > 1:
        print("   warning 注意: 数据明显偏态，可能存在系统性误差或异常值")
    elif abs(stats['skewness']) > 0.5:
        print("   tips 提示: 数据轻微偏态，建议检查误差分布")
    else:
        print(" ok 数据分布: 接近对称分布")

    return stats


def main():
    if not os.path.isfile(VIDEO_PATH):
        print("error 视频不存在");
        sys.exit()
        return

    cap = cv2.VideoCapture(VIDEO_PATH)
    ret, first = cap.read()
    if not ret:
        print("error 读不到第一帧");
        return

    roi = cv2.selectROI("在第一帧框 ROI（空格确认）", first, False)
    cv2.destroyAllWindows()
    x, y, w, h = map(int, roi)
    print("ROI =", roi)

    fout = open(OUTPUT_TXT, "w", encoding="utf-8")
    max_err = 0.0
    hits = 0
    step = 3  # 可改成 1 不跳帧

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
    print(f"\n 完成，有效坐标 {hits} 组，最大空间误差 = {max_err:.6f} mm")

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


        # 综合统计分析
        stats = comprehensive_error_analysis(data)

        # 绘制误差分布图
        print("\n生成误差分布图表...")
        plot_error_distribution(data)

        # 生成分析报告摘要
        print("\n" + "=" * 70)
        print("分析报告摘要")
        print("=" * 70)
        print(f" 数据概况: 共分析 {len(data)} 个有效样本")
        print(f" 主要指标: 平均误差 {stats['mean']:.4f} mm ± {stats['std_dev']:.4f} mm")
        print(f" 分布特征: {stats['skewness']:.2f} 偏度, {stats['kurtosis']:.2f} 峰度")
        print(f" 稳定性: 变异系数 {stats['cv']:.1f}%")
        print("=" * 70)

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
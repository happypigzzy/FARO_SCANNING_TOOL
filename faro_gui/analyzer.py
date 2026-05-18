# analyzer.py — 统计分析逻辑（statistical analysis logic）
# 从原始 commpress&maxerror.py 提取，纯函数，不依赖 GUI
import re
import numpy as np
from scipy.stats import skew, kurtosis
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SIMHEI']
plt.rcParams['axes.unicode_minus'] = False


def extract_data(filepath, min_disp=0.0, max_disp=3.0):
    """从 OCR 输出文件中提取有效位移数据"""
    data = []
    pattern = r'Frame(\d+):\s+X\s+([-\d.]+)\s+Y\s+([-\d.]+)\s+Z\s+([-\d.]+)\s+->\s+([\d.]+)\s+mm'

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(pattern, line)
            if match:
                try:
                    frame = match.group(1)
                    x = float(match.group(2))
                    y = float(match.group(3))
                    z = float(match.group(4))
                    displacement = float(match.group(5))
                    if min_disp <= displacement <= max_disp:
                        data.append((displacement, x, y, z, frame))
                except ValueError:
                    pass
    return data


def calculate_median(data):
    """计算位移值中位数"""
    if not data:
        return None
    displacements = [item[0] for item in data]
    sorted_d = sorted(displacements)
    n = len(sorted_d)
    if n % 2 == 1:
        return sorted_d[n // 2]
    else:
        return (sorted_d[n // 2 - 1] + sorted_d[n // 2]) / 2


def calculate_advanced_stats(data):
    """计算高级统计指标"""
    if not data:
        return None
    displacements = [item[0] for item in data]

    mean_val = np.mean(displacements)
    median_val = np.median(displacements)
    std_dev = np.std(displacements)
    variance = np.var(displacements)

    percentiles = {
        '25th': np.percentile(displacements, 25),
        '50th': np.percentile(displacements, 50),
        '75th': np.percentile(displacements, 75),
        '90th': np.percentile(displacements, 90),
        '95th': np.percentile(displacements, 95),
    }

    iqr = percentiles['75th'] - percentiles['25th']
    skewness = skew(displacements)
    kurt = kurtosis(displacements)
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
        'cv': cv,
        'min': min(displacements),
        'max': max(displacements),
        'count': len(displacements),
    }


def generate_report(data, stats):
    """生成文本分析报告"""
    displacement_list = [item[0] for item in data]
    lines = []
    lines.append("=" * 60)
    lines.append("           机器人重定位误差综合评估")
    lines.append("=" * 60)
    lines.append("")
    lines.append(" 基础统计:")
    lines.append(f"   样本数量: {stats['count']}")
    lines.append(f"   平均值:   {stats['mean']:.6f} mm")
    lines.append(f"   中位数:   {stats['median']:.6f} mm")
    lines.append(f"   最小值:   {stats['min']:.6f} mm")
    lines.append(f"   最大值:   {stats['max']:.6f} mm")
    lines.append(f"   极差:     {stats['max'] - stats['min']:.6f} mm")
    lines.append("")
    lines.append(" 变异性指标:")
    lines.append(f"   标准差:       {stats['std_dev']:.6f} mm")
    lines.append(f"   方差:         {stats['variance']:.6f} (mm)^2")
    lines.append(f"   变异系数:     {stats['cv']:.2f}%")
    lines.append(f"   四分位距 IQR: {stats['iqr']:.6f} mm")
    lines.append("")
    lines.append(" 百分位数:")
    for key, value in stats['percentiles'].items():
        lines.append(f"   {key}: {value:.6f} mm")
    lines.append("")
    lines.append(" 分布形状:")
    lines.append(f"   偏度: {stats['skewness']:.4f}")
    if stats['skewness'] > 0.5:
        lines.append("   分布形态: 右偏分布")
    elif stats['skewness'] < -0.5:
        lines.append("   分布形态: 左偏分布")
    else:
        lines.append("   分布形态: 基本对称")
    lines.append(f"   峰度: {stats['kurtosis']:.4f}")
    if stats['kurtosis'] > 1:
        lines.append("   峰度特征: 尖峰分布")
    elif stats['kurtosis'] < -1:
        lines.append("   峰度特征: 低峰分布")
    else:
        lines.append("   峰度特征: 接近正态峰度")
    lines.append("")
    lines.append(" 质量评估:")
    if stats['cv'] < 10:
        lines.append("   [OK] 误差稳定性: 优秀 (变异系数 < 10%)")
    elif stats['cv'] < 20:
        lines.append("   [OK] 误差稳定性: 良好 (变异系数 10-20%)")
    else:
        lines.append("   [!!] 误差稳定性: 请参考图表评估 (变异系数 > 20%)")
    return "\n".join(lines)


def create_figures(data):
    """创建所有分析图表，返回 {name: Figure}"""
    if not data:
        return {}

    displacements = [item[0] for item in data]
    frames = [int(item[4]) for item in data]
    figures = {}

    # -------- Figure 1: 综合 3x2 大图 --------
    fig1, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig1.suptitle('TCP 重定位运动误差综合分析', fontsize=14, fontweight='bold')

    # 1.1 直方图
    ax = axes[0, 0]
    ax.hist(displacements, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax.set_xlabel('位移误差 (mm)')
    ax.set_ylabel('频数')
    ax.set_title('误差分布直方图')
    ax.grid(True, alpha=0.3)
    stats_text = f'平均值: {np.mean(displacements):.4f} mm\n标准差: {np.std(displacements):.4f} mm'
    ax.text(0.95, 0.95, stats_text, transform=ax.transAxes,
            va='top', ha='right', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 1.2 箱线图
    ax = axes[0, 1]
    bp = ax.boxplot(displacements, patch_artist=True)
    bp['boxes'][0].set_facecolor('lightgreen')
    ax.set_ylabel('位移误差 (mm)')
    ax.set_title('误差箱线图')
    ax.grid(True, alpha=0.3)

    # 1.3 KDE
    ax = axes[0, 2]
    from scipy.stats import gaussian_kde
    density = gaussian_kde(displacements)
    xs = np.linspace(min(displacements), max(displacements), 200)
    ax.plot(xs, density(xs), 'b-', linewidth=2)
    ax.fill_between(xs, density(xs), alpha=0.3, color='blue')
    ax.set_xlabel('位移误差 (mm)')
    ax.set_ylabel('概率密度')
    ax.set_title('误差概率密度分布')
    ax.grid(True, alpha=0.3)

    # 1.4 CDF
    ax = axes[1, 0]
    sorted_data = np.sort(displacements)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    ax.plot(sorted_data, yvals, 'r-', linewidth=2)
    ax.set_xlabel('位移误差 (mm)')
    ax.set_ylabel('累积概率')
    ax.set_title('误差累积分布函数')
    ax.grid(True, alpha=0.3)

    # 1.5 Q-Q 图
    ax = axes[1, 1]
    from scipy.stats import probplot
    probplot(displacements, dist="norm", plot=ax)
    ax.set_title('Q-Q 图 (正态检验)')
    ax.grid(True, alpha=0.3)

    # 1.6 时间序列
    ax = axes[1, 2]
    ax.plot(frames, displacements, 'b.-', alpha=0.7, markersize=3)
    ax.set_xlabel('帧号')
    ax.set_ylabel('位移误差 (mm)')
    ax.set_title('误差时间序列')
    ax.grid(True, alpha=0.3)
    window_size = min(10, len(displacements) // 10)
    if window_size > 1:
        moving_avg = np.convolve(displacements, np.ones(window_size) / window_size, mode='valid')
        ax.plot(frames[window_size - 1:], moving_avg, 'r-', linewidth=2, label=f'{window_size}帧移动平均')
        ax.legend()

    fig1.tight_layout()
    figures['comprehensive'] = fig1

    # -------- Figure 2: 直方图 + 箱线图 --------
    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    ax1.hist(displacements, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
    ax1.set_xlabel('位移误差 (mm)'); ax1.set_ylabel('频数')
    ax1.set_title('误差分布直方图'); ax1.grid(True, alpha=0.3)

    bp = ax2.boxplot(displacements, patch_artist=True)
    bp['boxes'][0].set_facecolor('lightgreen')
    ax2.set_ylabel('位移误差 (mm)')
    ax2.set_title('误差箱线图'); ax2.grid(True, alpha=0.3)
    fig2.tight_layout()
    figures['histogram_box'] = fig2

    # -------- Figure 3: KDE + CDF --------
    fig3, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    from scipy.stats import gaussian_kde
    density = gaussian_kde(displacements)
    xs = np.linspace(min(displacements), max(displacements), 200)
    ax1.plot(xs, density(xs), 'b-', linewidth=2)
    ax1.fill_between(xs, density(xs), alpha=0.3, color='blue')
    ax1.set_xlabel('位移误差 (mm)'); ax1.set_ylabel('概率密度')
    ax1.set_title('概率密度分布'); ax1.grid(True, alpha=0.3)

    sorted_data = np.sort(displacements)
    yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1)
    ax2.plot(sorted_data, yvals, 'r-', linewidth=2)
    ax2.set_xlabel('位移误差 (mm)'); ax2.set_ylabel('累积概率')
    ax2.set_title('累积分布函数'); ax2.grid(True, alpha=0.3)
    fig3.tight_layout()
    figures['kde_cdf'] = fig3

    # -------- Figure 4: Q-Q + 时间序列 --------
    fig4, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    from scipy.stats import probplot
    probplot(displacements, dist="norm", plot=ax1)
    ax1.set_title('Q-Q 图'); ax1.grid(True, alpha=0.3)

    ax2.plot(frames, displacements, 'b.-', alpha=0.7, markersize=3)
    ax2.set_xlabel('帧号'); ax2.set_ylabel('位移误差 (mm)')
    ax2.set_title('误差时间序列'); ax2.grid(True, alpha=0.3)
    window_size = min(10, len(displacements) // 10)
    if window_size > 1:
        moving_avg = np.convolve(displacements, np.ones(window_size) / window_size, mode='valid')
        ax2.plot(frames[window_size - 1:], moving_avg, 'r-', linewidth=2, label=f'{window_size}帧MA')
        ax2.legend()
    fig4.tight_layout()
    figures['qq_timeseries'] = fig4

    return figures

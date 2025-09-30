import re


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


def main():
    filename = "../valid_xyz.txt"

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



        # 可选：输出所有数据供参考
        print("\n所有有效数据:")
        print("帧号\t\t位移值(mm)\tX\t\tY\t\tZ")
        for displacement, x, y, z, frame in data:
            print(f"Frame{frame}\t{displacement:.6f}\t\t{x:.6f}\t{y:.6f}\t{z:.6f}")
        print(f"找到 {len(data)} 个有效位移数据 (范围: 0-3 mm)")
        print(f"平均值: {avg_displacement:.6f} mm")
        print("\n最大值详细信息:")
        print(f"帧号: Frame{max_data[4]}")
        print(f"位移值: {max_data[0]:.6f} mm")
        print(f"X: {max_data[1]:.6f}")
        print(f"Y: {max_data[2]:.6f}")
        print(f"Z: {max_data[3]:.6f}")

    except FileNotFoundError:
        print(f"文件 {filename} 未找到")


if __name__ == "__main__":
    main()
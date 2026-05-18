# workers.py — 后台线程（background workers for ffmpeg & OCR）
import threading
import subprocess
import os
import re
import cv2
import numpy as np
import pytesseract

NUM_OR_STAR_RE = re.compile(r'([+-]?\d+\.\d+|\*{4,5})')


class CompressWorker(threading.Thread):
    """后台 ffmpeg 视频压缩线程"""

    def __init__(self, input_path, output_path, settings, queue):
        super().__init__(daemon=True)
        self.input_path = input_path
        self.output_path = output_path
        self.settings = settings
        self.queue = queue
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            w = self.settings['width']
            h = self.settings['height']
            fps = self.settings['fps']
            crf = self.settings['crf']
            preset = self.settings['preset']

            cmd = [
                'ffmpeg',
                '-i', self.input_path,
                '-vf', f'scale={w}:{h}',
                '-c:v', 'libx264',
                '-crf', str(crf),
                '-preset', preset,
                '-r', str(fps),
                '-c:a', 'aac',
                '-b:a', '32k',
                '-y',
                '-progress', 'pipe:1',
                '-nostats',
                self.output_path,
            ]

            self.queue.put(('log', f"执行命令: {' '.join(cmd)}"))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
            )

            for line in process.stdout:
                if self._stop_event.is_set():
                    process.terminate()
                    self.queue.put(('log', '压缩已取消（compress cancelled）'))
                    self.queue.put(('done', False))
                    return

                line = line.strip()
                if line:
                    self.queue.put(('log', line))
                if line.startswith('out_time='):
                    self.queue.put(('progress_pulse',))

            process.wait()

            if process.returncode == 0:
                if os.path.exists(self.input_path) and os.path.exists(self.output_path):
                    orig_size = os.path.getsize(self.input_path) / (1024 * 1024)
                    comp_size = os.path.getsize(self.output_path) / (1024 * 1024)
                    reduction = (1 - comp_size / orig_size) * 100 if orig_size > 0 else 0
                    self.queue.put(('log', f'原始大小: {orig_size:.2f} MB'))
                    self.queue.put(('log', f'压缩后:   {comp_size:.2f} MB'))
                    self.queue.put(('log', f'体积减少: {reduction:.2f}%'))
                self.queue.put(('log', '压缩完成（compress finished）'))
                self.queue.put(('done', True))
            else:
                stderr = process.stderr.read()
                self.queue.put(('log', f'FFmpeg 错误: {stderr[:500]}'))
                self.queue.put(('done', False))

        except FileNotFoundError:
            self.queue.put(('log', '错误: 未找到 FFmpeg，请确保已安装（ffmpeg not found）'))
            self.queue.put(('done', False))
        except Exception as e:
            self.queue.put(('log', f'压缩异常: {str(e)}'))
            self.queue.put(('done', False))


class OCRWorker(threading.Thread):
    """后台 OCR 识别线程"""

    def __init__(self, video_path, roi, step, displacement_max, output_txt, tesseract_cmd, queue):
        super().__init__(daemon=True)
        self.video_path = video_path
        self.roi = roi
        self.step = step
        self.displacement_max = displacement_max
        self.output_txt = output_txt
        self.tesseract_cmd = tesseract_cmd
        self.queue = queue
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd

            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.queue.put(('error', '无法打开视频文件（cannot open video）'))
                return

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            x, y, w, h = self.roi

            results = []
            max_err = 0.0
            hits = 0
            frame_id = 0

            self.queue.put(('log', f'开始处理，总帧数约 {total_frames}，采样间隔 {self.step} 帧'))
            self.queue.put(('log', f'ROI: x={x} y={y} w={w} h={h}'))

            while True:
                if self._stop_event.is_set():
                    cap.release()
                    self.queue.put(('log', 'OCR 已取消（OCR cancelled）'))
                    self.queue.put(('done', results))
                    return

                ret, frame = cap.read()
                if not ret:
                    break

                if frame_id % self.step != 0:
                    frame_id += 1
                    continue

                roi_img = frame[y:y + h, x:x + w]
                gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
                sharpen = cv2.filter2D(gray, -1, np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]))
                _, bin_img = cv2.threshold(sharpen, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                text = pytesseract.image_to_string(
                    bin_img, lang='eng',
                    config='--psm 6 -c tessedit_char_whitelist=0123456789.+-*'
                )
                tokens = NUM_OR_STAR_RE.findall(text)
                tokens = tokens[:3]

                if len(tokens) != 3 or any('*' in tok for tok in tokens):
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

                if 0 <= err <= self.displacement_max:
                    results.append((err, x_val, y_val, z_val, frame_id))
                    self.queue.put(('hit', frame_id, x_val, y_val, z_val, err))

                if hits % 10 == 0 or frame_id % 30 == 0:
                    self.queue.put(('stats', hits, max_err, frame_id, total_frames))

                frame_id += 1

            cap.release()

            # 写入输出文件
            with open(self.output_txt, 'w', encoding='utf-8') as f:
                for err, xv, yv, zv, fid in results:
                    f.write(f"Frame{fid}: X {xv:.4f} Y {yv:.4f} Z {zv:.4f} -> {err:.6f} mm\n")

            self.queue.put(('log', ''))
            self.queue.put(('log', f'完成! 有效坐标 {hits} 组，最大空间误差 = {max_err:.6f} mm'))
            self.queue.put(('log', f'有效位移数据 (0-{self.displacement_max} mm): {len(results)} 条'))
            self.queue.put(('done', results))

        except Exception as e:
            self.queue.put(('error', f'OCR 异常: {str(e)}'))

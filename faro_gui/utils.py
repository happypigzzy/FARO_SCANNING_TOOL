# utils.py — 工具函数（utility functions）
import cv2
from PIL import Image, ImageTk


def tr(zh_text, en_text):
    """返回统一的中英双语格式: 中文（English）"""
    return f"{zh_text}（{en_text}）"


def cv2_to_tk(cv_image, max_width=None, max_height=None):
    """将 OpenCV BGR 图像转换为 Tkinter PhotoImage，可选缩放"""
    if cv_image is None:
        return None

    h, w = cv_image.shape[:2]

    if max_width and max_height:
        scale = min(max_width / w, max_height / h)
        if scale < 1:
            new_w, new_h = int(w * scale), int(h * scale)
            cv_image = cv2.resize(cv_image, (new_w, new_h))

    rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    return ImageTk.PhotoImage(pil_img)


def get_video_info(video_path):
    """读取视频基本信息，返回 dict"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        return None

    info = {
        'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        'fps': cap.get(cv2.CAP_PROP_FPS),
        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        'duration': 0,
        'size_mb': 0,
    }

    if info['fps'] > 0 and info['frame_count'] > 0:
        info['duration'] = info['frame_count'] / info['fps']

    import os
    if os.path.isfile(video_path):
        info['size_mb'] = os.path.getsize(video_path) / (1024 * 1024)

    # 读取第一帧
    ret, first_frame = cap.read()
    info['first_frame'] = first_frame if ret else None

    cap.release()
    return info

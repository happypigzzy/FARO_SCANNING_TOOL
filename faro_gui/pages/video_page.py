# video_page.py — Step1: 选择视频（Select Video）
import tkinter as tk
from tkinter import ttk, filedialog
import os

from utils import tr, get_video_info, cv2_to_tk


class VideoPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._photo = None
        self._build_ui()

    def _build_ui(self):
        # 标题
        title = ttk.Label(
            self,
            text=tr("Step 1: 选择视频文件", "Step 1: Select Video File"),
            font=('', 13, 'bold'),
        )
        title.pack(pady=(15, 20))

        # 文件选择行
        file_frame = ttk.Frame(self)
        file_frame.pack(fill=tk.X, padx=30, pady=5)

        ttk.Label(file_frame, text=tr("视频路径:", "Video Path:"), font=('', 10)).pack(side=tk.LEFT)

        self._path_var = tk.StringVar()
        path_entry = ttk.Entry(file_frame, textvariable=self._path_var, font=('', 10))
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))

        browse_btn = ttk.Button(
            file_frame,
            text=tr("浏览...", "Browse..."),
            command=self._browse,
        )
        browse_btn.pack(side=tk.RIGHT)

        # 视频信息区
        info_frame = ttk.LabelFrame(
            self,
            text=tr("视频信息", "Video Information"),
            padding=15,
        )
        info_frame.pack(fill=tk.X, padx=30, pady=15)

        # 信息网格
        self._info_labels = {}
        info_fields = [
            ('resolution', tr("分辨率", "Resolution")),
            ('fps', tr("帧率", "FPS")),
            ('frame_count', tr("总帧数", "Total Frames")),
            ('duration', tr("时长", "Duration")),
            ('size', tr("文件大小", "File Size")),
        ]

        for i, (key, label) in enumerate(info_fields):
            row = i // 2
            col = (i % 2) * 2
            ttk.Label(info_frame, text=label + ":", font=('', 10)).grid(
                row=row, column=col, sticky='w', padx=(0, 5), pady=3)
            val = ttk.Label(info_frame, text="—", font=('', 10))
            val.grid(row=row, column=col + 1, sticky='w', padx=(0, 30), pady=3)
            self._info_labels[key] = val

        # 缩略图预览
        preview_frame = ttk.LabelFrame(
            self,
            text=tr("首帧预览", "First Frame Preview"),
            padding=10,
        )
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        self._preview_label = ttk.Label(preview_frame)
        self._preview_label.pack(expand=True)

        # 提示文字
        self._hint_label = ttk.Label(
            preview_frame,
            text=tr("请选择一个视频文件以预览首帧", "Please select a video file to preview the first frame"),
            foreground='gray',
        )
        self._hint_label.place(relx=0.5, rely=0.5, anchor='center')

    def _browse(self):
        path = filedialog.askopenfilename(
            title=tr("选择视频文件", "Select Video File"),
            filetypes=[
                (tr("视频文件", "Video Files"), "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                (tr("所有文件", "All Files"), "*.*"),
            ],
        )
        if path:
            self.refresh(path)

    def refresh(self, path):
        """当选择新视频时刷新界面"""
        self._path_var.set(path)
        self.app.shared['input_video'] = path

        info = get_video_info(path)
        if info is None:
            self._info_labels['resolution'].config(text=tr("无法读取", "Cannot read"))
            return

        self._info_labels['resolution'].config(text=f"{info['width']} × {info['height']}")
        self._info_labels['fps'].config(text=f"{info['fps']:.2f}")
        self._info_labels['frame_count'].config(text=str(info['frame_count']))
        mins = int(info['duration'] // 60)
        secs = int(info['duration'] % 60)
        self._info_labels['duration'].config(text=f"{mins}m {secs}s")
        self._info_labels['size'].config(text=f"{info['size_mb']:.1f} MB")

        # 保存第一帧供后续步骤使用
        if info['first_frame'] is not None:
            self.app.shared['first_frame'] = info['first_frame']

            # 显示缩略图
            preview_w = self._preview_label.winfo_width() or 600
            preview_h = self._preview_label.winfo_height() or 350
            self._photo = cv2_to_tk(info['first_frame'], preview_w, preview_h)
            if self._photo:
                self._preview_label.config(image=self._photo)
                self._hint_label.place_forget()

        self.app.mark_step_done(0)

    def on_enter(self):
        self.app.set_status(tr("Step 1: 选择要分析的视频文件", "Step 1: Select video file for analysis"))

    def handle_worker_msg(self, msg):
        pass

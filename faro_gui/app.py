# app.py — 主窗口（main window with sidebar + content area）
import tkinter as tk
from tkinter import ttk, messagebox
import os
import queue

from utils import tr

# 在页面导入之前设置 matplotlib 中文字体
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SIMHEI']
plt.rcParams['axes.unicode_minus'] = False

from pages.video_page import VideoPage
from pages.compress_page import CompressPage
from pages.roi_page import ROIPage
from pages.ocr_page import OCRPage
from pages.results_page import ResultsPage


class MainApp(tk.Tk):
    """主应用程序窗口"""

    def __init__(self):
        super().__init__()

        self.title("FARO SCANNING TOOL — 机器人重定位误差分析（Robot Relocation Error Analysis）")
        self.geometry("1200x800")
        self.minsize(1000, 650)

        # -------- 共享状态（shared state across pages）--------
        self.shared = {
            'input_video': '',
            'output_video': os.path.join(os.path.dirname(__file__), 'compressed.mp4'),
            'output_txt': os.path.join(os.path.dirname(__file__), 'valid_xyz.txt'),
            'roi': None,                # (x, y, w, h)
            'first_frame': None,        # OpenCV BGR image
            'display_scale': 1.0,       # ROI 页面图像缩放比
            'ocr_step': 3,
            'displacement_min': 0.0,
            'displacement_max': 3.0,
            'ocr_results': [],          # [(displacement, x, y, z, frame), ...]
            'compress_settings': {
                'width': 768,
                'height': 480,
                'fps': 20,
                'crf': 28,
                'preset': 'ultrafast',
            },
            'compress_done': False,
            'ocr_done': False,
            'tesseract_cmd': r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        }

        # 后台线程引用
        self._worker = None
        self._poll_id = None

        # -------- 构建界面 --------
        self._build_menu()
        self._build_layout()

        # -------- 消息轮询 --------
        self._msg_queue = queue.Queue()
        self._poll_queue()

    # ============================================================
    #  菜单栏（Menu Bar）
    # ============================================================
    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label=tr("打开视频...", "Open Video..."),
            command=self._menu_open_video,
        )
        file_menu.add_separator()
        file_menu.add_command(
            label=tr("设置 Tesseract 路径...", "Set Tesseract Path..."),
            command=self._menu_set_tesseract,
        )
        file_menu.add_separator()
        file_menu.add_command(label=tr("退出", "Exit"), command=self.quit)
        menubar.add_cascade(label=tr("文件", "File"), menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(
            label=tr("关于", "About"),
            command=lambda: messagebox.showinfo(
                tr("关于", "About"),
                "FARO SCANNING TOOL\n"
                + tr("机器人重定位运动误差分析工具", "Robot Relocation Error Analysis Tool")
                + "\n\nv1.0",
            ),
        )
        menubar.add_cascade(label=tr("帮助", "Help"), menu=help_menu)

    def _menu_open_video(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title=tr("选择视频文件", "Select Video File"),
            filetypes=[
                (tr("视频文件", "Video Files"), "*.mp4 *.avi *.mov *.mkv *.flv *.wmv"),
                (tr("所有文件", "All Files"), "*.*"),
            ],
        )
        if path:
            self.shared['input_video'] = path
            self._pages[0].refresh(path)
            self.navigate_to(0)

    def _menu_set_tesseract(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title=tr("选择 Tesseract 可执行文件", "Select Tesseract Executable"),
            filetypes=[("tesseract.exe", "tesseract.exe"), (tr("所有文件", "All Files"), "*.*")],
        )
        if path:
            self.shared['tesseract_cmd'] = path
            messagebox.showinfo(tr("提示", "Info"), f"Tesseract 路径已设为:\n{path}")

    # ============================================================
    #  主布局（Main Layout）
    # ============================================================
    def _build_layout(self):
        # 主容器
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- 左侧边栏（Sidebar）----
        sidebar = ttk.Frame(main_frame, width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0), pady=5)
        sidebar.pack_propagate(False)

        ttk.Label(
            sidebar,
            text=tr("处理步骤", "Steps"),
            font=('', 11, 'bold'),
        ).pack(pady=(15, 20))

        self._step_btns = []
        self._step_labels = [
            tr("Step1: 选择视频", "Select Video"),
            tr("Step2: 压缩设置", "Compress"),
            tr("Step3: ROI 框选", "ROI Select"),
            tr("Step4: 运行 OCR", "Run OCR"),
            tr("Step5: 分析结果", "Results"),
        ]

        for i, label in enumerate(self._step_labels):
            btn = tk.Button(
                sidebar,
                text=f"  {label}",
                anchor='w',
                font=('', 10),
                relief=tk.FLAT,
                bd=2,
                padx=12,
                pady=8,
                command=lambda idx=i: self.navigate_to(idx),
            )
            btn.pack(fill=tk.X, padx=8, pady=2)
            self._step_btns.append(btn)

        # Step 完成标记
        self._step_done = [False] * 5

        # 分隔线
        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=20)

        # 导航按钮
        nav_frame = ttk.Frame(sidebar)
        nav_frame.pack(fill=tk.X, padx=8, pady=5)

        self._prev_btn = ttk.Button(
            nav_frame,
            text=tr("← 上一步", "← Prev"),
            command=self._prev_step,
        )
        self._prev_btn.pack(fill=tk.X, pady=2)

        self._next_btn = ttk.Button(
            nav_frame,
            text=tr("下一步 →", "Next →"),
            command=self._next_step,
        )
        self._next_btn.pack(fill=tk.X, pady=2)

        # ---- 右侧内容区（Content Area）----
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self._content_frame = content_frame
        self._pages: list = []
        self._current_step = 0

        # 创建 5 个页面
        self._pages.append(VideoPage(content_frame, self))
        self._pages.append(CompressPage(content_frame, self))
        self._pages.append(ROIPage(content_frame, self))
        self._pages.append(OCRPage(content_frame, self))
        self._pages.append(ResultsPage(content_frame, self))

        # 叠放（stack）所有页面
        for p in self._pages:
            p.place(in_=content_frame, x=0, y=0, relwidth=1, relheight=1)

        # ---- 底部状态栏（Status Bar）----
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self._status_var = tk.StringVar(value=tr("就绪", "Ready"))
        ttk.Label(status_frame, textvariable=self._status_var, relief=tk.SUNKEN, anchor='w',
                  padding=(8, 3)).pack(fill=tk.X)

        # 初始显示第一页
        self.navigate_to(0)

    # ============================================================
    #  导航控制（Navigation）
    # ============================================================
    def navigate_to(self, index):
        """跳转到指定步骤页"""
        if index < 0 or index >= len(self._pages):
            return

        self._current_step = index
        self._pages[index].tkraise()
        self._pages[index].on_enter()

        # 更新侧边栏按钮样式
        for i, btn in enumerate(self._step_btns):
            if i == index:
                btn.config(
                    bg='#0078d4', fg='white',
                    font=('', 10, 'bold'),
                    relief=tk.RAISED,
                )
            elif self._step_done[i]:
                check_label = self._step_labels[i]
                if not check_label.startswith('✓ '):
                    pass  # 通过刷新标记
                btn.config(
                    bg='#e8f5e9', fg='#2e7d32',
                    font=('', 10),
                    relief=tk.FLAT,
                    text=f"  ✓ {self._step_labels[i]}",
                )
            else:
                btn.config(
                    bg='#f0f0f0', fg='#666666',
                    font=('', 10),
                    relief=tk.FLAT,
                    text=f"  {self._step_labels[i]}",
                )

        # 更新导航按钮
        self._prev_btn.config(state=tk.NORMAL if index > 0 else tk.DISABLED)
        self._next_btn.config(state=tk.NORMAL if index < 4 else tk.DISABLED)

    def _prev_step(self):
        if self._current_step > 0:
            self.navigate_to(self._current_step - 1)

    def _next_step(self):
        if self._current_step < 4:
            self.navigate_to(self._current_step + 1)

    def mark_step_done(self, index):
        """标记某步骤已完成"""
        self._step_done[index] = True
        self.navigate_to(index)  # 刷新按钮样式

    # ============================================================
    #  状态栏（Status Bar）
    # ============================================================
    def set_status(self, text):
        self._status_var.set(text)

    # ============================================================
    #  后台队列轮询（Queue Polling）
    # ============================================================
    def submit_worker(self, worker):
        """启动后台线程并开始轮询其消息队列"""
        self._worker = worker
        self._msg_queue = queue.Queue()
        worker.queue = self._msg_queue
        worker.start()
        self._poll_id = self.after(100, self._poll_queue)

    def _poll_queue(self):
        """定时轮询后台线程消息"""
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                current_page = self._pages[self._current_step]
                if hasattr(current_page, 'handle_worker_msg'):
                    current_page.handle_worker_msg(msg)
        except queue.Empty:
            pass

        # 检查 worker 是否存活
        if self._worker and self._worker.is_alive():
            self._poll_id = self.after(100, self._poll_queue)
        else:
            self._poll_id = None

    def cancel_worker(self):
        """取消当前后台任务"""
        if self._worker and self._worker.is_alive():
            self._worker.stop()

    def on_worker_done(self):
        """worker 线程结束后的清理"""
        self._worker = None
        if self._poll_id:
            self.after_cancel(self._poll_id)
            self._poll_id = None

# roi_page.py — Step3: ROI 框选（ROI Selection）
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk

from utils import tr


class ROIPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self._tk_image = None       # 当前显示的 PhotoImage
        self._display_w = 0         # 显示宽度
        self._display_h = 0         # 显示高度
        self._scale = 1.0           # 缩放比
        self._orig_w = 0
        self._orig_h = 0

        # ROI 框选状态
        self._start_x = None
        self._start_y = None
        self._rect_id = None
        self._roi = None            # (x, y, w, h) in original coords

        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(
            self,
            text=tr("Step 3: ROI 区域框选", "Step 3: ROI Region Selection"),
            font=('', 13, 'bold'),
        )
        title.pack(pady=(15, 10))

        ttk.Label(
            self,
            text=tr(
                "在图像上拖拽鼠标框选需要 OCR 识别的坐标区域",
                "Drag mouse on the image to select the coordinate area for OCR",
            ),
            foreground='gray',
        ).pack(pady=(0, 10))

        # 按钮行
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=30, pady=5)

        ttk.Button(
            btn_frame,
            text=tr("重置选区", "Reset Selection"),
            command=self._reset_roi,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            btn_frame,
            text=tr("确认选区 →", "Confirm Selection →"),
            command=self._confirm_roi,
        ).pack(side=tk.LEFT)

        # ROI 信息
        self._roi_label = ttk.Label(
            btn_frame,
            text=tr("ROI: 未选择", "ROI: Not selected"),
            foreground='gray',
            font=('', 10),
        )
        self._roi_label.pack(side=tk.RIGHT)

        # 画布
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        self._canvas = tk.Canvas(canvas_frame, bg='#1a1a1a', cursor='cross')
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._canvas.bind('<ButtonPress-1>', self._on_mouse_down)
        self._canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self._canvas.bind('<ButtonRelease-1>', self._on_mouse_up)

        # 提示覆盖文字
        self._hint_id = self._canvas.create_text(
            0, 0, anchor='center',
            text=tr("请先在 Step1 选择视频", "Please select a video in Step1 first"),
            fill='#888888', font=('', 12),
        )

    def _load_image(self):
        """加载第一帧到画布"""
        first_frame = self.app.shared.get('first_frame')
        if first_frame is None:
            return False

        self._orig_h, self._orig_w = first_frame.shape[:2]

        # 计算适合画布的缩放比
        canvas_w = self._canvas.winfo_width()
        canvas_h = self._canvas.winfo_height()

        if canvas_w < 50:
            canvas_w = 800
        if canvas_h < 50:
            canvas_h = 500

        self._scale = min(canvas_w / self._orig_w, canvas_h / self._orig_h)
        self._display_w = int(self._orig_w * self._scale)
        self._display_h = int(self._orig_h * self._scale)

        # 缩放并转换
        display_img = cv2.resize(first_frame, (self._display_w, self._display_h))
        rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self._tk_image = ImageTk.PhotoImage(pil_img)

        # 放到画布中央
        self._canvas.delete('all')
        self._canvas.config(
            width=self._display_w,
            height=self._display_h,
            scrollregion=(0, 0, self._display_w, self._display_h),
        )
        self._canvas.create_image(0, 0, anchor='nw', image=self._tk_image)

        # 恢复已有 ROI
        existing = self.app.shared.get('roi')
        if existing:
            x, y, w, h = existing
            dx, dy = x * self._scale, y * self._scale
            dw, dh = w * self._scale, h * self._scale
            self._rect_id = self._canvas.create_rectangle(
                dx, dy, dx + dw, dy + dh,
                outline='#00ff00', width=2,
            )
            self._roi = existing
            self._update_roi_label()

        return True

    def _on_mouse_down(self, event):
        self._start_x = event.x
        self._start_y = event.y

        if self._rect_id:
            self._canvas.delete(self._rect_id)
            self._rect_id = None

    def _on_mouse_drag(self, event):
        if self._start_x is None:
            return

        if self._rect_id:
            self._canvas.delete(self._rect_id)

        self._rect_id = self._canvas.create_rectangle(
            self._start_x, self._start_y, event.x, event.y,
            outline='#00ff00', width=2,
        )

    def _on_mouse_up(self, event):
        if self._start_x is None:
            return

        x1, y1 = self._start_x, self._start_y
        x2, y2 = event.x, event.y

        # 确保左上→右下
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        # 转换回原始坐标
        ox = max(0, int(x1 / self._scale))
        oy = max(0, int(y1 / self._scale))
        ow = min(self._orig_w - ox, int((x2 - x1) / self._scale))
        oh = min(self._orig_h - oy, int((y2 - y1) / self._scale))

        if ow < 5 or oh < 5:
            self._reset_roi()
            return

        self._roi = (ox, oy, ow, oh)
        self.app.shared['roi'] = self._roi
        self.app.shared['display_scale'] = self._scale
        self._update_roi_label()

        self._start_x = None
        self._start_y = None

    def _reset_roi(self):
        if self._rect_id:
            self._canvas.delete(self._rect_id)
            self._rect_id = None
        self._roi = None
        self.app.shared['roi'] = None
        self._roi_label.config(
            text=tr("ROI: 未选择", "ROI: Not selected"),
            foreground='gray',
        )

    def _update_roi_label(self):
        if self._roi:
            x, y, w, h = self._roi
            self._roi_label.config(
                text=f"ROI: x={x} y={y} w={w} h={h}",
                foreground='#2e7d32',
            )

    def _confirm_roi(self):
        if not self._roi:
            messagebox.showwarning(
                tr("提示", "Notice"),
                tr("请先在图像上框选 ROI 区域", "Please select a ROI region on the image first"),
            )
            return
        self.app.mark_step_done(2)

    def on_enter(self):
        self.app.set_status(tr("Step 3: 在图像上拖拽框选 ROI 区域", "Step 3: Drag to select ROI region"))
        # 延迟加载，确保画布已有尺寸
        self.after(200, self._load_image)

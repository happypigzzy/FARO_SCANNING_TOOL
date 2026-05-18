# results_page.py — Step5: 分析结果（Analysis Results）
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
import os

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from utils import tr
from analyzer import extract_data, calculate_median, calculate_advanced_stats, create_figures


class ResultsPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._figures = {}
        self._current_fig_key = None
        self._canvas_widget = None
        self._toolbar_widget = None
        self._data = []
        self._stats = None
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(
            self,
            text=tr("Step 5: 误差分析结果", "Step 5: Error Analysis Results"),
            font=('', 13, 'bold'),
        )
        title.pack(pady=(15, 5))

        # ---- 顶部操作按钮 ----
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=30, pady=5)

        ttk.Button(
            toolbar,
            text=tr("刷新分析", "Refresh Analysis"),
            command=self._run_analysis,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            toolbar,
            text=tr("导出图表 PNG", "Export Charts PNG"),
            command=self._export_chart,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            toolbar,
            text=tr("导出数据 CSV", "Export Data CSV"),
            command=self._export_csv,
        ).pack(side=tk.LEFT, padx=(0, 10))

        # ---- 统计摘要卡片（paned window 上部分）----
        self._cards_frame = ttk.Frame(self)
        self._cards_frame.pack(fill=tk.X, padx=30, pady=5)

        self._card_vars = {}
        card_fields = [
            ('count', tr("样本数", "Samples"), '0'),
            ('mean', tr("平均误差", "Mean"), '— mm'),
            ('max', tr("最大误差", "Max"), '— mm'),
            ('std_dev', tr("标准差", "Std Dev"), '— mm'),
            ('cv', tr("变异系数", "CV"), '— %'),
            ('iqr', tr("IQR", "IQR"), '— mm'),
        ]

        for i, (key, label, default) in enumerate(card_fields):
            card = ttk.LabelFrame(self._cards_frame, text=label, padding=(10, 6))
            card.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, pady=3)

            var = tk.StringVar(value=default)
            self._card_vars[key] = var
            ttk.Label(card, textvariable=var, font=('', 12, 'bold')).pack()

        # ---- 中部: 图表区域 + 数据表格 (Notebook) ----
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        # Tab: 图表
        self._chart_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._chart_tab, text=tr("图表", "Charts"))

        # 图表切换按钮
        chart_nav = ttk.Frame(self._chart_tab)
        chart_nav.pack(fill=tk.X, pady=5)

        ttk.Label(chart_nav, text=tr("选择图表:", "Select Chart:"), font=('', 10)).pack(side=tk.LEFT, padx=(5, 10))

        self._chart_combo = ttk.Combobox(
            chart_nav,
            values=[
                tr("综合 3×2", "Comprehensive 3×2"),
                tr("直方图 + 箱线图", "Histogram + Box"),
                tr("KDE + CDF", "KDE + CDF"),
                tr("Q-Q + 时间序列", "Q-Q + Timeseries"),
            ],
            state='readonly',
        )
        self._chart_combo.current(0)
        self._chart_combo.pack(side=tk.LEFT)
        self._chart_combo.bind('<<ComboboxSelected>>', self._on_chart_select)

        # 图表容器
        self._chart_container = ttk.Frame(self._chart_tab)
        self._chart_container.pack(fill=tk.BOTH, expand=True)

        # Tab: 数据表格
        self._table_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._table_tab, text=tr("数据表格", "Data Table"))

        self._build_table()

        # Tab: 文本报告
        self._report_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._report_tab, text=tr("分析报告", "Report"))

        report_frame = ttk.Frame(self._report_tab)
        report_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._report_text = tk.Text(
            report_frame, font=('Consolas', 10),
            wrap=tk.NONE, bg='#1e1e1e', fg='#d4d4d4',
            insertbackground='white',
        )
        self._report_text.pack(fill=tk.BOTH, expand=True)

        # 横向+纵向滚动条
        h_scroll = ttk.Scrollbar(self._report_text, orient=tk.HORIZONTAL, command=self._report_text.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        v_scroll = ttk.Scrollbar(self._report_text, command=self._report_text.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._report_text.config(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)

    def _build_table(self):
        """构建 Treeview 数据表格"""
        table_frame = ttk.Frame(self._table_tab)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ('frame', 'x', 'y', 'z', 'displacement')
        self._tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            selectmode='extended',
        )

        col_labels = {
            'frame': tr("帧号", "Frame"),
            'x': 'X (mm)',
            'y': 'Y (mm)',
            'z': 'Z (mm)',
            'displacement': tr("位移 (mm)", "Disp. (mm)"),
        }
        col_widths = {'frame': 80, 'x': 150, 'y': 150, 'z': 150, 'displacement': 160}

        for col in columns:
            self._tree.heading(col, text=col_labels[col],
                               command=lambda c=col: self._sort_column(c, False))
            self._tree.column(col, width=col_widths[col], anchor='center', minwidth=60)

        # 滚动条
        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._tree.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self._tree.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self._tree.config(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self._tree.pack(fill=tk.BOTH, expand=True)

    def _sort_column(self, col, reverse):
        """点击表头排序"""
        rows = [(self._tree.set(item, col), item) for item in self._tree.get_children('')]
        try:
            rows.sort(key=lambda x: float(x[0]), reverse=reverse)
        except ValueError:
            rows.sort(key=lambda x: x[0], reverse=reverse)

        for i, (_, item) in enumerate(rows):
            self._tree.move(item, '', i)

        self._tree.heading(col, command=lambda: self._sort_column(col, not reverse))

    # ============================================================
    #  分析逻辑
    # ============================================================
    def _run_analysis(self):
        """执行完整分析流程"""
        txt_file = self.app.shared.get('output_txt', '')
        dmin = self.app.shared.get('displacement_min', 0.0)
        dmax = self.app.shared.get('displacement_max', 3.0)

        # 尝试从文件读取
        if not os.path.isfile(txt_file):
            # 使用 OCR 结果
            results = self.app.shared.get('ocr_results', [])
            if not results:
                self._card_vars['count'].set('0')
                messagebox.showwarning(
                    tr("提示", "Notice"),
                    tr("请先完成 Step4 OCR 识别", "Please complete Step4 OCR first"),
                )
                return
            self._data = results
        else:
            self._data = extract_data(txt_file, dmin, dmax)

        if not self._data:
            self._card_vars['count'].set('0')
            messagebox.showwarning(
                tr("提示", "Notice"),
                tr("无有效数据可分析", "No valid data to analyze"),
            )
            return

        # 统计
        self._stats = calculate_advanced_stats(self._data)
        if self._stats is None:
            return

        # 更新摘要卡片
        self._card_vars['count'].set(str(self._stats['count']))
        self._card_vars['mean'].set(f"{self._stats['mean']:.4f} mm")
        self._card_vars['max'].set(f"{self._stats['max']:.4f} mm")
        self._card_vars['std_dev'].set(f"{self._stats['std_dev']:.4f} mm")
        self._card_vars['cv'].set(f"{self._stats['cv']:.2f} %")
        self._card_vars['iqr'].set(f"{self._stats['iqr']:.4f} mm")

        # 图表
        self._figures = create_figures(self._data)
        self._show_figure('comprehensive')

        # 表格
        self._populate_table()

        # 报告
        from analyzer import generate_report
        report = generate_report(self._data, self._stats)
        self._report_text.delete(1.0, tk.END)
        self._report_text.insert(1.0, report)

        self.app.set_status(
            tr(f"分析完成: {self._stats['count']} 条数据, 均值 {self._stats['mean']:.4f} mm",
               f"Analysis done: {self._stats['count']} samples, mean {self._stats['mean']:.4f} mm"))

    def _show_figure(self, key):
        """显示指定图表"""
        if key not in self._figures:
            return

        # 清除旧内容
        for w in self._chart_container.winfo_children():
            w.destroy()

        fig = self._figures[key]
        self._current_fig_key = key

        canvas = FigureCanvasTkAgg(fig, master=self._chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 工具栏
        toolbar = NavigationToolbar2Tk(canvas, self._chart_container)
        toolbar.update()

        self._canvas_widget = canvas

    def _on_chart_select(self, event=None):
        idx = self._chart_combo.current()
        keys = ['comprehensive', 'histogram_box', 'kde_cdf', 'qq_timeseries']
        if 0 <= idx < len(keys):
            self._show_figure(keys[idx])

    def _populate_table(self):
        """填充数据表格"""
        for item in self._tree.get_children(''):
            self._tree.delete(item)

        for displacement, x, y, z, frame in self._data:
            self._tree.insert('', tk.END, values=(
                frame,
                f"{x:.4f}",
                f"{y:.4f}",
                f"{z:.4f}",
                f"{displacement:.6f}",
            ))

    # ============================================================
    #  导出功能
    # ============================================================
    def _export_chart(self):
        if not self._figures:
            messagebox.showwarning(tr("提示", "Notice"),
                                   tr("请先运行分析", "Please run analysis first"))
            return

        path = filedialog.asksaveasfilename(
            title=tr("保存图表", "Save Chart"),
            defaultextension='.png',
            filetypes=[('PNG', '*.png'), ('PDF', '*.pdf'), ('SVG', '*.svg')],
            initialfile='error_analysis.png',
        )
        if path:
            fig = self._figures.get(self._current_fig_key)
            if fig:
                fig.savefig(path, dpi=300, bbox_inches='tight')
                self.app.set_status(tr(f"图表已保存至: {path}", f"Chart saved to: {path}"))

    def _export_csv(self):
        if not self._data:
            messagebox.showwarning(tr("提示", "Notice"),
                                   tr("请先运行分析", "Please run analysis first"))
            return

        path = filedialog.asksaveasfilename(
            title=tr("导出数据 CSV", "Export Data CSV"),
            defaultextension='.csv',
            filetypes=[('CSV', '*.csv')],
            initialfile='error_data.csv',
        )
        if path:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['Frame', 'X', 'Y', 'Z', 'Displacement(mm)'])
                for displacement, x, y, z, frame in self._data:
                    writer.writerow([frame, f"{x:.4f}", f"{y:.4f}", f"{z:.4f}", f"{displacement:.6f}"])
            self.app.set_status(tr(f"数据已导出至: {path}", f"Data exported to: {path}"))

    # ============================================================
    #  生命周期
    # ============================================================
    def on_enter(self):
        self.app.set_status(tr("Step 5: 点击刷新分析查看结果", "Step 5: Click Refresh Analysis to view results"))
        # 首次进入自动分析
        if not self._data and self.app.shared.get('ocr_done'):
            self.after(300, self._run_analysis)

    def handle_worker_msg(self, msg):
        pass

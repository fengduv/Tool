import tkinter as tk
from tkinter import messagebox
import tkinter.ttk as ttk
import json
import os
import time
import random
import sys
import threading
import pystray
from PIL import Image, ImageDraw

# 配置文件路径
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(APP_DIR, 'notes_config.json')

# 便签背景颜色
BG_COLORS = [
    {'name': '黄色', 'bg': '#fff9c4', 'fg': '#333333'},
    {'name': '粉色', 'bg': '#f8bbd0', 'fg': '#333333'},
    {'name': '蓝色', 'bg': '#bbdefb', 'fg': '#333333'},
    {'name': '绿色', 'bg': '#c8e6c9', 'fg': '#333333'},
    {'name': '紫色', 'bg': '#e1bee7', 'fg': '#333333'},
    {'name': '橙色', 'bg': '#ffe0b2', 'fg': '#333333'},
]

# 字体大小选项
FONT_SIZES = [14, 16, 18, 20, 22, 24, 26, 28, 30, 32]

# 字体颜色选项
FONT_COLORS = [
    {'name': '黑色', 'color': '#000000'},
    {'name': '深灰', 'color': '#333333'},
    {'name': '灰色', 'color': '#666666'},
    {'name': '红色', 'color': '#e74c3c'},
    {'name': '蓝色', 'color': '#3498db'},
    {'name': '绿色', 'color': '#27ae60'},
    {'name': '紫色', 'color': '#9b59b6'},
    {'name': '橙色', 'color': '#e67e22'},
]

# 默认便签尺寸（放大20%后）
DEFAULT_WIDTH  = 336   # 280 * 1.2
DEFAULT_HEIGHT = 300   # 250 * 1.2

# 默认设置文件
SETTINGS_FILE = os.path.join(APP_DIR, 'default_settings.json')

# 默认设置（新建便签时的默认值）
default_settings = {
    'font_size': 14,
    'font_color': '#333333',
    'bg_color': 0  # 0-5 对应 BG_COLORS 索引，-1 表示随机
}

# 全局变量
notes = []
root = None
tray_icon = None
mutex_handle = None
note_canvas = None
note_list_inner = None
note_scrollbar_ref = None

# ==================== 默认设置相关函数 ====================
def load_default_settings():
    """加载默认设置"""
    global default_settings
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                default_settings.update(loaded)
    except Exception as e:
        print(f"加载默认设置失败: {e}")

def save_default_settings():
    """保存默认设置"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"保存默认设置失败: {e}")

def open_default_settings():
    """打开默认设置窗口"""
    global default_settings
    
    settings_win = tk.Toplevel(root)
    settings_win.title("默认设置")
    settings_win.geometry("320x320")
    settings_win.resizable(False, False)
    settings_win.attributes('-topmost', True)
    # 移除 -toolwindow 属性，使用默认样式关闭按钮
    
    # 居中显示
    settings_win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() - 320) // 2
    y = root.winfo_y() + (root.winfo_height() - 320) // 2
    settings_win.geometry(f"+{x}+{y}")
    
    main_frame = tk.Frame(settings_win, bg='#F5F5F5', padx=30, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # 居中布局
    main_frame.columnconfigure(0, weight=1)
    main_frame.columnconfigure(1, weight=1)
    
    # 字体大小
    tk.Label(main_frame, text="默认字体大小：", bg='#F5F5F5', font=('Microsoft YaHei', 10)).grid(row=0, column=0, sticky='e', pady=12)
    font_size_var = tk.StringVar(value=str(default_settings['font_size']))
    font_size_combo = ttk.Combobox(main_frame, textvariable=font_size_var, values=[str(s) for s in FONT_SIZES], width=10, state='readonly')
    font_size_combo.grid(row=0, column=1, pady=12)
    
    # 字体颜色
    tk.Label(main_frame, text="默认字体颜色：", bg='#F5F5F5', font=('Microsoft YaHei', 10)).grid(row=1, column=0, sticky='e', pady=12)
    font_color_options = ['随机'] + [c['name'] for c in FONT_COLORS]
    font_color_names = {'随机': 'random'}
    for c in FONT_COLORS:
        font_color_names[c['name']] = c['color']
    font_color_display = '随机' if default_settings['font_color'] == 'random' else next((c['name'] for c in FONT_COLORS if c['color'] == default_settings['font_color']), '深灰')
    font_color_var = tk.StringVar(value=font_color_display)
    font_color_combo = ttk.Combobox(main_frame, textvariable=font_color_var, values=font_color_options, width=10, state='readonly')
    font_color_combo.grid(row=1, column=1, pady=12)
    
    # 便签背景色
    tk.Label(main_frame, text="默认便签背景：", bg='#F5F5F5', font=('Microsoft YaHei', 10)).grid(row=2, column=0, sticky='e', pady=12)
    bg_color_options = ['随机'] + [c['name'] for c in BG_COLORS]
    bg_color_display = '随机' if default_settings['bg_color'] == -1 else BG_COLORS[default_settings['bg_color']]['name']
    bg_color_var = tk.StringVar(value=bg_color_display)
    bg_color_combo = ttk.Combobox(main_frame, textvariable=bg_color_var, values=bg_color_options, width=10, state='readonly')
    bg_color_combo.grid(row=2, column=1, pady=12)
    
    # 开机自动启动
    startup_var = tk.BooleanVar(value=is_startup_enabled())
    startup_check = tk.Checkbutton(main_frame, text="开机自动启动", variable=startup_var, bg='#F5F5F5', font=('Microsoft YaHei', 10), activebackground='#F5F5F5')
    startup_check.grid(row=3, column=0, columnspan=2, pady=15)
    
    def apply_settings():
        """应用设置"""
        global default_settings
        
        # 字体大小
        default_settings['font_size'] = int(font_size_var.get())
        
        # 字体颜色
        fc = font_color_var.get()
        default_settings['font_color'] = 'random' if fc == '随机' else font_color_names.get(fc, '#333333')
        
        # 便签背景色
        bc = bg_color_var.get()
        if bc == '随机':
            default_settings['bg_color'] = -1
        else:
            for i, c in enumerate(BG_COLORS):
                if c['name'] == bc:
                    default_settings['bg_color'] = i
                    break
        
        # 开机自启
        if startup_var.get() != is_startup_enabled():
            if set_startup(startup_var.get()):
                update_tray_menu()
        
        save_default_settings()
        messagebox.showinfo("成功", "默认设置已保存！", parent=settings_win)
        settings_win.destroy()
    
    # 按钮
    btn_frame = tk.Frame(main_frame, bg='#F5F5F5')
    btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
    
    tk.Button(btn_frame, text="保存", font=('Microsoft YaHei', 10), bg='#4CAF50', fg='white', bd=0, padx=25, pady=6, command=apply_settings).pack(side=tk.LEFT, padx=15)
    tk.Button(btn_frame, text="取消", font=('Microsoft YaHei', 10), bg='#E57373', fg='white', bd=0, padx=25, pady=6, command=settings_win.destroy).pack(side=tk.LEFT, padx=15)

def _update_scrollbar_visibility():
    """根据便签数量控制滚动条显隐"""
    global note_scrollbar_ref
    if note_scrollbar_ref and note_scrollbar_ref.winfo_exists():
        if len(notes) >= 6:
            note_scrollbar_ref.grid(row=0, column=1, sticky='ns')
        else:
            note_scrollbar_ref.grid_remove()
        
        # 滚动条显隐后，手动触发 Canvas 宽度重新计算
        note_canvas.after(10, lambda: note_canvas.itemconfig(note_canvas_window, width=note_canvas.winfo_width()))

# ==================== 悬浮提示工具 ====================
class ToolTip:
    """为控件添加悬浮气泡提示（显示在控件上方）"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        widget.bind('<Enter>', self.show_tooltip)
        widget.bind('<Leave>', self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        # 计算位置：控件上方
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() - 28  # 显示在上方
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes('-topmost', True)  # 确保显示在最上层
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", foreground="#333333",
                         relief=tk.SOLID, borderwidth=1,
                         font=('Microsoft YaHei', 9), padx=4, pady=2)
        label.pack()

    def hide_tooltip(self, event=None):
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()

# ==================== 单实例检测 ====================
MUTEX_NAME = "Global\\DesktopNotes_SingleInstance_20260319"

def check_single_instance():
    global mutex_handle
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mutex_handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        last_error = kernel32.GetLastError()
        return last_error == 183
    except Exception as e:
        print(f"单实例检测失败: {e}")
        return False

def notify_existing_instance():
    try:
        import socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2)
        client.connect(('127.0.0.1', 19998))
        client.send(b'show')
        client.close()
        return True
    except:
        return False

def release_mutex():
    global mutex_handle
    if mutex_handle:
        try:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(mutex_handle)
        except:
            pass

# ==================== 开机自启 ====================
import winreg

def is_startup_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, "DesktopNotes")
            winreg.CloseKey(key)
            return value == sys.executable
        except:
            winreg.CloseKey(key)
            return False
    except:
        return False

def set_startup(enable=True):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_WRITE)
        if enable:
            winreg.SetValueEx(key, "DesktopNotes", 0, winreg.REG_SZ, sys.executable)
        else:
            try:
                winreg.DeleteValue(key, "DesktopNotes")
            except:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"设置开机自启失败: {e}")
        return False

# ==================== 托盘图标 ====================
def create_tray_icon():
    """创建托盘图标（黄色便签样式）"""
    width = height = 64
    # 透明背景（RGBA 模式支持透明）
    image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 便签主体 - 黄色背景带阴影
    note_bg = (255, 247, 130)      # 亮黄色便签
    note_shadow = (200, 180, 80)  # 阴影
    note_border = (230, 210, 90)   # 边框
    
    # 绘制阴影
    draw.rounded_rectangle([6, 8, 58, 60], radius=4, fill=note_shadow)
    # 绘制便签主体
    draw.rounded_rectangle([4, 4, 56, 58], radius=4, fill=note_bg, outline=note_border, width=1)
    
    # 便签顶部折叠效果（浅色区域）
    draw.polygon([(4, 4), (56, 4), (56, 12), (4, 16)], fill=(255, 255, 200))
    draw.line([(4, 16), (56, 16)], fill=(230, 210, 90), width=1)
    
    # 图钉
    pin_head = (220, 80, 80)       # 红色
    pin_shadow = (180, 60, 60)     # 阴影
    pin_gloss = (255, 150, 150)    # 高光
    # 钉子阴影
    draw.ellipse([27, 2, 37, 12], fill=pin_shadow)
    # 钉子主体
    draw.ellipse([26, 1, 36, 11], fill=pin_head)
    # 高光
    draw.ellipse([28, 3, 32, 7], fill=pin_gloss)
    
    # 便签上的文字线条
    line_color = (180, 160, 60)
    for i, y in enumerate([24, 30, 36, 42, 48]):
        if i == 4:  # 最后一行短一些
            draw.line([12, y, 38, y], fill=line_color, width=2)
        else:
            draw.line([12, y, 50, y], fill=line_color, width=2)
    
    return image

def toggle_startup_menu(icon=None, item=None):
    def do_toggle():
        current_state = is_startup_enabled()
        new_state = not current_state
        if set_startup(new_state):
            update_tray_menu()
            status = "开启" if new_state else "关闭"
            messagebox.showinfo("开机自启", f"已{status}开机自动启动")
        else:
            messagebox.showerror("错误", "设置开机自启失败，可能需要管理员权限")
    if root:
        root.after(0, do_toggle)

def update_tray_menu():
    global tray_icon
    if tray_icon:
        try:
            tray_icon.menu = create_tray_menu()
        except Exception as e:
            print(f"更新菜单失败: {e}")

def create_tray_menu():
    startup_checked = is_startup_enabled()
    startup_text = "✓ 开机自动启动" if startup_checked else "  开机自动启动"
    return pystray.Menu(
        pystray.MenuItem('📝 显示便签管理器', show_window, default=True),
        pystray.MenuItem('👁 显示/隐藏所有便签', toggle_all_notes),
        pystray.MenuItem('➕ 新建便签', create_note),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(startup_text, toggle_startup_menu, checked=lambda item: startup_checked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('❌ 退出', exit_app)
    )

def setup_tray():
    global tray_icon
    image = create_tray_icon()
    tray_icon = pystray.Icon('DesktopNotes', image, '桌面便签', create_tray_menu())
    tray_thread = threading.Thread(target=run_tray, daemon=True)
    tray_thread.start()

def run_tray():
    global tray_icon
    if tray_icon:
        try:
            tray_icon.run()
        except Exception as e:
            print(f"托盘运行错误: {e}")

def show_window(icon=None, item=None):
    global root
    if root:
        root.deiconify()
        root.lift()
        root.focus_force()

def hide_window():
    global root
    if root:
        root.wm_state('iconic')
        root.withdraw()

def _do_exit_app():
    global tray_icon, root
    save_all_notes()
    if tray_icon:
        try:
            tray_icon.stop()
        except:
            pass
    release_mutex()
    if root:
        try:
            root.destroy()
        except:
            pass
    sys.exit(0)

def exit_app(icon=None, item=None):
    if root:
        root.after(0, _do_exit_app)

# ==================== 便签类 ====================
class StickyNote:
    """桌面便签窗口"""

    def __init__(self, parent, note_id, title="新便签", content="",
                 bg_color=0, font_size=14, font_color='#333333',
                 is_top=False, x=100, y=100,
                 width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT,
                 created_time=None):
        self.parent     = parent
        self.note_id    = note_id
        self.title      = title
        self.content    = content
        self.bg_color_idx = bg_color
        self.font_size  = font_size
        self.font_color = font_color
        self.is_top     = is_top
        self.x = x
        self.y = y
        self.width  = max(width,  DEFAULT_WIDTH)
        self.height = max(height, DEFAULT_HEIGHT)
        
        # 创建时间（精确到分钟）
        if created_time:
            self.created_time = created_time
        else:
            self.created_time = time.strftime('%Y-%m-%d %H:%M')

        # 最小尺寸 = 默认尺寸
        self.min_width  = DEFAULT_WIDTH
        self.min_height = DEFAULT_HEIGHT

        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', self.is_top)
        self.window.attributes('-alpha', 1.0)  # 完全不透明
        self.window.resizable(True, True)
        self.window.bind('<Configure>', self.on_resize)

        # 拖拽缩放状态
        self._resize_edge   = None
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_w = 0
        self._resize_start_h = 0
        self._resize_start_wx = 0
        self._resize_start_wy = 0

        self.setup_ui()

    # ---------- UI 构建 ----------
    def setup_ui(self):
        bg = BG_COLORS[self.bg_color_idx]

        self.frame = tk.Frame(self.window, bg=bg['bg'], bd=2, relief='solid')
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ── 标题栏 ──
        title_bar = tk.Frame(self.frame, bg=bg['bg'], height=35)
        title_bar.pack(fill=tk.X, padx=2, pady=(2, 0))
        title_bar.pack_propagate(False)

        self.title_entry = tk.Entry(
            title_bar, bg=bg['bg'], fg=bg['fg'],
            font=('Microsoft YaHei', 11, 'bold'),
            bd=0, highlightthickness=0, width=10)
        self.title_entry.insert(0, self.title)
        self.title_entry.pack(side=tk.LEFT, padx=3, pady=5)
        self.title_entry.bind('<FocusOut>', self.save_title)
        self.title_entry.bind('<Return>', lambda e: self.window.focus())

        drag_area = tk.Frame(title_bar, bg=bg['bg'], cursor='fleur')
        drag_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        drag_area.bind('<Button-1>',   self.start_move)
        drag_area.bind('<B1-Motion>',  self.on_move)

        btn_frame = tk.Frame(title_bar, bg=bg['bg'])
        
        # 初始隐藏菜单栏
        btn_frame.pack_forget()
        
        # 菜单栏显示/隐藏控制
        def show_menu_bar():
            btn_frame.pack(side=tk.RIGHT)
        
        def hide_menu_bar():
            btn_frame.pack_forget()
        
        # 绑定焦点事件
        self.window.bind('<FocusIn>', lambda e: show_menu_bar())
        self.window.bind('<FocusOut>', lambda e: hide_menu_bar())

        # 加粗按钮
        self.bold_btn = tk.Button(
            btn_frame, text='B', font=('Microsoft YaHei', 9, 'bold'),
            bg=bg['bg'], fg=bg['fg'], bd=1, relief='groove',
            width=2, height=1, cursor='hand2',
            command=self.toggle_bold)
        self.bold_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.bold_btn, "加粗选中文字")

        # 删除线按钮
        self.strike_btn = tk.Button(
            btn_frame, text='S̶', font=('Microsoft YaHei', 9),
            bg=bg['bg'], fg=bg['fg'], bd=1, relief='groove',
            width=2, height=1, cursor='hand2',
            command=self.toggle_strikethrough)
        self.strike_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.strike_btn, "删除线")

        # 背景颜色切换
        bg_btn = tk.Button(btn_frame, text='🎨', bg=bg['bg'], fg=bg['fg'], bd=0,
                  font=('Arial', 12), width=2,
                  command=self.show_color_picker)
        bg_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(bg_btn, "切换背景颜色")

        # 置顶切换
        self.top_btn = tk.Button(
            btn_frame, text='📌' if self.is_top else '📍',
            bg=bg['bg'], fg=bg['fg'], bd=0, font=('Arial', 9), width=2,
            command=self.toggle_top)
        self.top_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(self.top_btn, "置顶/取消置顶")

        # 字体大小选择（Menubutton 下拉菜单，只显示数字，无背景框）
        self.font_size_btn = tk.Menubutton(
            btn_frame, text=str(self.font_size),
            bg=bg['bg'], fg=bg['fg'], bd=0, highlightthickness=0,
            font=('Arial', 9), width=2, indicatoron=False,
            activebackground=bg['bg'], activeforeground=bg['fg']
        )
        self.font_size_btn.pack(side=tk.LEFT, padx=1)
        self.font_size_menu = tk.Menu(self.font_size_btn, tearoff=0, bg='#FFFFFF', fg='#333333', font=('Arial', 9))
        for size in FONT_SIZES:
            self.font_size_menu.add_command(label=str(size), command=lambda s=size: self.on_font_size_changed(s))
        self.font_size_btn.config(menu=self.font_size_menu)
        ToolTip(self.font_size_btn, "选择字体大小")

        # 字体颜色选择（Menubutton 下拉菜单，显示颜色块）
        self.font_color_btn = tk.Menubutton(
            btn_frame, text='🖊', bg=bg['bg'], fg=self.font_color,
            bd=0, highlightthickness=0, font=('Arial', 12), width=2,
            indicatoron=False, activebackground=bg['bg'], activeforeground=self.font_color
        )
        self.font_color_btn.pack(side=tk.LEFT, padx=1)
        self.font_color_menu = tk.Menu(self.font_color_btn, tearoff=0, bg='#FFFFFF')
        
        # 为每个颜色创建菜单项（显示颜色块）
        for color_info in FONT_COLORS:
            color_code = color_info['color']
            # 创建一个带颜色背景的菜单项
            self.font_color_menu.add_command(
                label='  ',  # 空白标签，用颜色块代替
                background=color_code,
                foreground=color_code,
                activebackground=color_code,
                activeforeground=color_code,
                command=lambda c=color_code: self.on_font_color_changed(c)
            )
        self.font_color_btn.config(menu=self.font_color_menu)
        ToolTip(self.font_color_btn, "选择字体颜色")

        # 隐藏便签按钮
        hide_btn = tk.Button(btn_frame, text='👁', bg=bg['bg'], fg=bg['fg'], bd=0,
                  font=('Arial', 10), width=2,
                  command=self.window.withdraw)
        hide_btn.pack(side=tk.LEFT, padx=1)
        ToolTip(hide_btn, "隐藏便签")

        # ❌ 已删除：最小化到托盘按钮（🗕），因为已有隐藏按钮

        # ── 内容区域（文本 + 底部菜单栏）────
        content_frame = tk.Frame(self.frame, bg=bg['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # 文本区域
        self.text_area = tk.Text(
            content_frame, bg=bg['bg'], fg=self.font_color,
            font=('Microsoft YaHei', self.font_size),
            wrap=tk.WORD, bd=0, padx=10, pady=5,
            relief='flat', insertbackground=self.font_color)
        self.text_area.pack(fill=tk.BOTH, expand=True)
        self.text_area.insert('1.0', self.content)
        self.text_area.bind('<KeyRelease>', lambda e: self.save())
        self.text_area.bind('<FocusOut>', lambda e: self.save_and_refresh())

        # 配置富文本标签
        self.text_area.tag_configure('bold', font=('Microsoft YaHei', self.font_size, 'bold'))
        self.text_area.tag_configure('strikethrough', overstrike=True)

        # ── 状态栏 ──
        self.status_bar = tk.Frame(self.frame, bg=bg['bg'], height=20)
        self.status_bar.pack(fill=tk.X, padx=2, pady=(0, 2))

        self.status_label = tk.Label(
            self.status_bar,
            text=f"字号:{self.font_size}px 颜色:{self.get_font_color_name()}",
            bg=bg['bg'], fg=bg['fg'], font=('Microsoft YaHei', 8))
        self.status_label.pack(side=tk.LEFT, padx=5)

        # ── 右下角拖拽缩放手柄 ──
        self._build_resize_handle(bg)

    def _build_resize_handle(self, bg):
        """右下角拖拽缩放手柄"""
        handle = tk.Label(self.frame, text='⇲', bg=bg['bg'], fg=bg['fg'],
                          font=('Arial', 10), cursor='size_nw_se')
        handle.place(relx=1.0, rely=1.0, anchor='se', x=-2, y=-2)
        handle.bind('<Button-1>',  self._resize_start)
        handle.bind('<B1-Motion>', self._resize_drag)
        handle.bind('<ButtonRelease-1>', self._resize_end)

    # ---------- 富文本操作 ----------
    def toggle_bold(self):
        """切换选中文字的加粗状态"""
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end   = self.text_area.index(tk.SEL_LAST)
        except tk.TclError:
            return  # 没有选中文字
        current_tags = self.text_area.tag_names(sel_start)
        if 'bold' in current_tags:
            self.text_area.tag_remove('bold', sel_start, sel_end)
            self.bold_btn.config(relief='groove')
        else:
            self.text_area.tag_add('bold', sel_start, sel_end)
            self.bold_btn.config(relief='sunken')

    def toggle_strikethrough(self):
        """切换选中文字的删除线状态"""
        try:
            sel_start = self.text_area.index(tk.SEL_FIRST)
            sel_end   = self.text_area.index(tk.SEL_LAST)
        except tk.TclError:
            return
        current_tags = self.text_area.tag_names(sel_start)
        if 'strikethrough' in current_tags:
            self.text_area.tag_remove('strikethrough', sel_start, sel_end)
            self.strike_btn.config(relief='groove')
        else:
            self.text_area.tag_add('strikethrough', sel_start, sel_end)
            self.strike_btn.config(relief='sunken')

    # ---------- 拖拽缩放 ----------
    def _resize_start(self, event):
        self._resize_edge     = 'se'
        self._resize_start_x  = event.x_root
        self._resize_start_y  = event.y_root
        self._resize_start_w  = self.window.winfo_width()
        self._resize_start_h  = self.window.winfo_height()
        self._resize_start_wx = self.window.winfo_x()
        self._resize_start_wy = self.window.winfo_y()

    def _resize_drag(self, event):
        if not self._resize_edge:
            return
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        new_w = max(self.min_width,  self._resize_start_w + dx)
        new_h = max(self.min_height, self._resize_start_h + dy)
        self.window.geometry(
            f"{new_w}x{new_h}+{self._resize_start_wx}+{self._resize_start_wy}")

    def _resize_end(self, event):
        self._resize_edge = None
        self.width  = self.window.winfo_width()
        self.height = self.window.winfo_height()
        self.save()

    # ---------- 原有功能 ----------
    def get_font_color_name(self):
        for c in FONT_COLORS:
            if c['color'] == self.font_color:
                return c['name']
        return '自定义'

    def on_resize(self, event):
        if event.widget == self.window:
            # 强制不低于最小尺寸
            w = max(event.width,  self.min_width)
            h = max(event.height, self.min_height)
            if w != event.width or h != event.height:
                self.window.geometry(f"{w}x{h}")
            self.width  = w
            self.height = h
            self.save()

    def start_move(self, event):
        self.x_offset = event.x
        self.y_offset = event.y

    def on_move(self, event):
        x = self.window.winfo_x() + event.x - self.x_offset
        y = self.window.winfo_y() + event.y - self.y_offset
        self.window.geometry(f"+{x}+{y}")
        self.x = x
        self.y = y

    def show_color_picker(self):
        """显示颜色选择网格（仿 Windows 便笺风格）"""
        # 创建颜色选择器窗口
        picker = tk.Toplevel(self.window)
        picker.title("选择背景颜色")
        picker.geometry("280x120")
        picker.resizable(False, False)
        picker.attributes('-topmost', True)
        
        # 设置窗口位置在便签右上角附近
        wx = self.window.winfo_x() + self.window.winfo_width() - 280
        wy = self.window.winfo_y() + 50
        picker.geometry(f"+{wx}+{wy}")
        
        # 创建颜色网格（3 行 2 列）
        grid_frame = tk.Frame(picker, bg='#F5F5F5', padx=10, pady=10)
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        for idx, color_info in enumerate(BG_COLORS):
            row = idx // 3
            col = idx % 3
            
            # 颜色块按钮
            color_btn = tk.Button(
                grid_frame,
                bg=color_info['bg'],
                fg=color_info['fg'],
                text=color_info['name'],
                font=('Microsoft YaHei', 9),
                width=8,
                height=2,
                bd=2 if idx == self.bg_color_idx else 0,
                relief='solid' if idx == self.bg_color_idx else 'flat',
                cursor='hand2',
                command=lambda i=idx: self.apply_color(i, picker)
            )
            color_btn.grid(row=row, column=col, padx=5, pady=5)
    
    def apply_color(self, color_idx, picker):
        """应用选中的颜色"""
        self.bg_color_idx = color_idx
        self.reload_ui()
        self.save()
        picker.destroy()

    def on_font_size_changed(self, value):
        """字体大小下拉菜单选择变化时"""
        self.font_size = int(value)
        # 更新按钮显示的数字
        if hasattr(self, 'font_size_btn'):
            self.font_size_btn.config(text=str(value))
        self.reload_ui()
        self.save()

    def on_font_color_changed(self, color):
        """字体颜色下拉菜单选择变化时"""
        self.font_color = color
        # 更新按钮前景色
        if hasattr(self, 'font_color_btn'):
            self.font_color_btn.config(fg=color, activeforeground=color)
        self.reload_ui()
        self.save()

    def toggle_top(self):
        self.is_top = not self.is_top
        self.window.attributes('-topmost', self.is_top)
        self.top_btn.config(text='📌' if self.is_top else '📍')
        self.status_label.config(
            text=f"字号:{self.font_size}px 颜色:{self.get_font_color_name()} | "
                 f"{'置顶' if self.is_top else '可覆盖'}")
        self.save()

    def reload_ui(self):
        content = self.text_area.get('1.0', tk.END).strip()
        self.window.destroy()
        self.window = tk.Toplevel(self.parent)
        self.window.title(self.title)
        self.window.geometry(f"{self.width}x{self.height}+{self.x}+{self.y}")
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', self.is_top)
        self.window.attributes('-alpha', 1.0)  # 完全不透明
        self.window.resizable(True, True)
        self.window.bind('<Configure>', self.on_resize)
        self._resize_edge = None
        self.setup_ui()
        self.text_area.delete('1.0', tk.END)
        self.text_area.insert('1.0', content)

    def save_title(self, event=None):
        new_title = self.title_entry.get().strip()
        if new_title and new_title != self.title:
            self.title = new_title
            self.window.title(new_title)
            self.save()

    def minimize_to_tray(self):
        self.save()
        self.window.withdraw()
        if status_label:
            status_label.config(text=f"便签已最小化到托盘: {self.title}")

    def save(self):
        """保存便签内容（不自动刷新列表，避免闪烁）"""
        self.content = self.text_area.get('1.0', tk.END).strip()
        save_all_notes()

    def save_and_refresh(self, event=None):
        """保存并刷新列表（用于失去焦点时）"""
        self.save()
        # 刷新管理器列表显示
        if 'update_listbox' in globals():
            update_listbox()

    def get_data(self):
        return {
            'id':           self.note_id,
            'title':        self.title,
            'content':      self.content,
            'bg_color_idx': self.bg_color_idx,
            'font_size':    self.font_size,
            'font_color':   self.font_color,
            'is_top':       self.is_top,
            'x':            self.x,
            'y':            self.y,
            'width':        self.width,
            'height':       self.height,
            'created_time': self.created_time,
        }

# ==================== 全局函数 ====================
def save_all_notes():
    data = [note.get_data() for note in notes]
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存失败: {e}")

def remove_note(note_id):
    global notes
    notes = [n for n in notes if n.note_id != note_id]
    save_all_notes()
    update_listbox()

def _do_create_note():
    global notes, root
    x = 100 + random.randint(0, 200)
    y = 100 + random.randint(0, 150)
    note_id = int(time.time() * 1000) + random.randint(0, 999)
    
    # 使用默认设置
    font_size = default_settings['font_size']
    font_color = default_settings['font_color']
    bg_color_idx = default_settings['bg_color']
    
    # 处理随机选项
    if font_color == 'random':
        font_color = FONT_COLORS[random.randint(0, len(FONT_COLORS) - 1)]['color']
    if bg_color_idx == -1:
        bg_color_idx = random.randint(0, len(BG_COLORS) - 1)
    
    note = StickyNote(root, note_id, f"便签 {len(notes) + 1}", "",
                      bg_color=bg_color_idx,
                      font_size=font_size, font_color=font_color,
                      x=x, y=y,
                      width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT)
    notes.append(note)
    save_all_notes()
    update_listbox()
    status_label.config(text=f"已创建: {note.title}")

def create_note(icon=None, item=None):
    if root:
        root.after(0, _do_create_note)

def show_all_notes(icon=None, item=None):
    for note in notes:
        note.window.deiconify()
        note.window.lift()
    status_label.config(text=f"显示了 {len(notes)} 个便签")

def _do_toggle_all_notes():
    visible_count = 0
    for note in notes:
        if note.window.winfo_viewable():
            note.window.withdraw()
        else:
            note.window.deiconify()
            note.window.lift()
            visible_count += 1
    if visible_count > 0:
        status_label.config(text=f"显示了 {visible_count} 个便签")
    else:
        status_label.config(text="已隐藏所有便签")

def toggle_all_notes(icon=None, item=None):
    if root:
        root.after(0, _do_toggle_all_notes)

def clear_all_notes():
    if messagebox.askyesno("确认", "确认要删除所有便签吗？"):
        for note in notes:
            note.window.destroy()
        notes.clear()
        save_all_notes()
        # 删除后重置滚动条位置
        note_canvas.yview_moveto(0)
        update_listbox()
        _update_scrollbar_visibility()

def update_listbox(keyword=''):
    """以卡片形式刷新便签列表（仿 Windows 便笺风格）"""
    # 清空旧卡片
    for widget in note_list_inner.winfo_children():
        widget.destroy()

    # 清空 Canvas 上的所有标签（包括空状态水印）
    note_canvas.delete('empty_text')

    # 空状态
    if not notes:
        # 延迟绘制，确保 Canvas 已初始化
        def draw_empty_text():
            canvas_width = note_canvas.winfo_width()
            canvas_height = note_canvas.winfo_height()
            if canvas_width > 1 and canvas_height > 1:
                note_canvas.create_text(
                    canvas_width // 2, canvas_height // 2,
                    text="暂无便签\n点击「新建便签」开始记录",
                    font=('Microsoft YaHei', 10),
                    fill='#BBBBBB',
                    justify='center',
                    tags='empty_text'
                )
        note_canvas.after(100, draw_empty_text)
        
        # 空状态也要更新 scrollregion 和滚动条显隐
        note_list_inner.update_idletasks()
        note_canvas.configure(scrollregion=(0, 0, 1, 1))
        _update_scrollbar_visibility()
        status_label.config(text="共 0 条便签")
        return

    # 过滤
    k = keyword.lower().strip()
    visible_count = 0

    for idx, note in enumerate(notes):
        title_text  = note.title.lower()
        content_text = note.content.lower()
        if k and k not in title_text and k not in content_text:
            continue
        visible_count += 1
        bg_color = BG_COLORS[note.bg_color_idx]['bg']

        # ── 阴影层 + 卡片（增加间距）────
        shadow1 = tk.Frame(note_list_inner, bg='#DDDDDD')
        shadow1.pack(fill=tk.X, pady=(0, 8))  # 卡片间距 8px

        shadow2 = tk.Frame(shadow1, bg='#CCCCCC')
        shadow2.pack(fill=tk.X, pady=(0, 1))

        # 主卡片（背景色与便签底色一致，无左侧色块）
        card = tk.Frame(shadow2, bg=bg_color, bd=0)
        card.pack(fill=tk.X)

        # 内容区（无左侧颜色条）
        content_area = tk.Frame(card, bg=bg_color, padx=10, pady=8)
        content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 标题行
        title_row = tk.Frame(content_area, bg=bg_color)
        title_row.pack(fill=tk.X)
        title_var_label = tk.Label(title_row,
                                  text=note.title,
                                  font=('Microsoft YaHei', 10, 'bold'),
                                  bg=bg_color, fg='#333333', anchor='w')
        title_var_label.pack(side=tk.LEFT)
        time_var_label = tk.Label(title_row,
                                 text=note.created_time,
                                 font=('Microsoft YaHei', 8),
                                 bg=bg_color, fg='#666666', anchor='e')
        time_var_label.pack(side=tk.RIGHT)

        # 内容预览
        preview = note.content.replace('\n', ' ').strip()
        preview = preview[:40] + '…' if len(preview) > 40 else preview
        preview_label = tk.Label(content_area,
                                text=preview if preview else "（空白便签）",
                                font=('Microsoft YaHei', 9),
                                bg=bg_color, fg='#555555',
                                anchor='w', wraplength=280, justify='left')
        preview_label.pack(fill=tk.X, pady=(2, 0))

        # 所有可交互子控件（手动收集，避免 winfo_children 遗留问题）
        all_widgets = [card, shadow2, shadow1, content_area, title_row,
                       title_var_label, time_var_label, preview_label]

        def on_enter(ev, c=card, s1=shadow1, s2=shadow2, ia=content_area,
                     tr=title_row, allw=all_widgets, bc=bg_color,
                     l1=title_var_label, l2=time_var_label, l3=preview_label):
            c.config(bg=bc)
            s1.config(bg='#888888')   # 悬停阴影加深
            s2.config(bg='#999999')
            ia.config(bg=bc)
            tr.config(bg=bc)
            for w in [l1, l2, l3, ia, tr, c]:
                try: w.config(bg=bc)
                except: pass

        def on_leave(ev, c=card, s1=shadow1, s2=shadow2, ia=content_area,
                     tr=title_row, allw=all_widgets, bc=bg_color,
                     l1=title_var_label, l2=time_var_label, l3=preview_label):
            c.config(bg=bc)
            s1.config(bg='#DDDDDD')   # 离开恢复浅阴影
            s2.config(bg='#CCCCCC')
            ia.config(bg=bc)
            tr.config(bg=bc)
            for w in [l1, l2, l3, ia, tr, c]:
                try: w.config(bg=bc)
                except: pass

        def on_click(ev, i=idx):
            notes[i].window.deiconify()
            notes[i].window.lift()
            notes[i].window.focus_force()

        def on_right_click(ev, i=idx):
            m = tk.Menu(root, tearoff=0)
            m.add_command(label='打开', command=lambda: on_click(None, i))
            m.add_separator()
            m.add_command(label='删除', command=lambda: _delete_note_by_idx(i))
            m.post(ev.x_root, ev.y_root)

        # 悬停事件绑定（shadow 帧通过直接捕获的 s1/s2 句柄处理）
        for w in [card, content_area, title_row, title_var_label, time_var_label, preview_label]:
            w.bind('<Enter>',          on_enter)
            w.bind('<Leave>',          on_leave)
            w.bind('<Button-1>',       on_click)
            w.bind('<Double-Button-1>', on_click)
            w.bind('<Button-3>',       on_right_click)

    # 更新滚动区域 & 滚动条显隐
    note_list_inner.update_idletasks()
    scrollregion = note_canvas.bbox('all')
    if scrollregion:
        note_canvas.configure(scrollregion=scrollregion)
    else:
        # 如果没有内容，设置一个默认的 scrollregion
        note_canvas.configure(scrollregion=(0, 0, 1, 1))
    _update_scrollbar_visibility()

    # 搜索计数
    if k:
        status_label.config(text=f"搜索「{k}」共 {visible_count} 条结果")
    else:
        status_label.config(text=f"共 {len(notes)} 条便签")

def _delete_note_by_idx(idx):
    """按列表索引删除便签"""
    if 0 <= idx < len(notes):
        note = notes[idx]
        if messagebox.askyesno("确认删除", f"确认要删除便签「{note.title}」吗？"):
            note.window.destroy()
            remove_note(note.note_id)
            # 删除后重置滚动条位置
            note_canvas.yview_moveto(0)
            update_listbox()
            _update_scrollbar_visibility()

def load_notes():
    global notes, root
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    note = StickyNote(
                        root,
                        item['id'],
                        item.get('title',        '便签'),
                        item.get('content',      ''),
                        item.get('bg_color_idx', 0),
                        item.get('font_size',    14),
                        item.get('font_color',   '#333333'),
                        item.get('is_top',       False),
                        item.get('x',            100),
                        item.get('y',            100),
                        item.get('width',        DEFAULT_WIDTH),
                        item.get('height',       DEFAULT_HEIGHT),
                        item.get('created_time', None),
                    )
                    notes.append(note)
                    note.window.withdraw()  # 启动时隐藏便签
            print(f"已加载 {len(notes)} 个便签")
        except Exception as e:
            print(f"加载失败: {e}")

def on_closing():
    global status_label
    try:
        if root:
            root.withdraw()
        if 'status_label' in globals() and status_label:
            status_label.config(text="已最小化到系统托盘")
    except Exception as e:
        print(f"最小化到托盘失败: {e}")

# ==================== 主函数 ====================
def main():
    global root, status_label, note_canvas, note_list_inner

    if check_single_instance():
        print("已有实例在运行，尝试激活...")
        if notify_existing_instance():
            print("已激活现有窗口")
        else:
            print("无法连接现有实例，实例可能已崩溃")
        sys.exit(0)

    print("启动桌面便签...")
    print(f"配置文件: {CONFIG_FILE}")
    
    # 加载默认设置
    load_default_settings()

    root = tk.Tk()
    root.title("桌面便签管理器")
    root.geometry("360x520")
    root.resizable(False, False)
    root.configure(bg='#F5F5F5')

    def start_server():
        import socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('127.0.0.1', 19998))
            server.listen(1)
            while True:
                try:
                    conn, addr = server.accept()
                    data = conn.recv(1024)
                    if data == b'show':
                        root.after(0, show_window)
                    conn.close()
                except:
                    break
        except Exception as e:
            print(f"通信服务器失败: {e}")

    threading.Thread(target=start_server, daemon=True).start()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    setup_tray()

    # ── 菜单栏 ──
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    # 设置菜单
    settings_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="设置", menu=settings_menu)
    settings_menu.add_command(label="默认设置", command=open_default_settings)
    
    # 帮助菜单
    help_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="帮助", menu=help_menu)
    help_menu.add_command(label="关于",  command=lambda: messagebox.showinfo("关于",  "2026年3月19日官官创作"))
    help_menu.add_separator()
    help_menu.add_command(label="反馈",  command=lambda: messagebox.showinfo("反馈",  "功能改进/反馈BUG请发送至邮箱\n\n1172987125@qq.com\n\nthanks!"))

    # ── 搜索栏区域 ──
    search_area = tk.Frame(root, bg='#F5F5F5')
    search_area.pack(fill=tk.X, padx=20, pady=(16, 8))

    # 搜索框外框（带圆角阴影效果）
    search_outer = tk.Frame(search_area, bg='#DDDDDD')
    search_outer.pack(fill=tk.X)

    search_container = tk.Frame(search_outer, bg='#FFFFFF')
    search_container.pack(fill=tk.X, padx=1, pady=1)

    # 搜索图标
    tk.Label(search_container, text='🔍',
             font=('Arial', 10), bg='#FFFFFF').pack(side=tk.LEFT, padx=(10, 0), pady=0)

    search_var = tk.StringVar()

    search_entry = tk.Entry(search_container,
                            textvariable=search_var,
                            font=('Microsoft YaHei', 11),
                            bg='#FFFFFF', fg='#333333',
                            insertbackground='#4A90D9',
                            bd=0, relief='flat')
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0), pady=8)
    search_entry.insert(0, '搜索便签...')  # 初始占位符
    search_entry.config(fg='#BBBBBB')  # 占位符颜色为灰色

    def on_focus_in(event):
        """获得焦点时，清空占位符"""
        if search_entry.get() == '搜索便签...':
            search_entry.delete(0, tk.END)
            search_entry.config(fg='#333333')

    def on_focus_out(event):
        """失去焦点时，如果为空则显示占位符"""
        if search_entry.get().strip() == '':
            search_entry.insert(0, '搜索便签...')
            search_entry.config(fg='#BBBBBB')

    def on_key_release(event):
        """按键释放时搜索（避免频繁刷新）"""
        text = search_entry.get()
        # 如果是占位符，不搜索
        if text == '搜索便签...':
            keyword = ''
        else:
            keyword = text.strip().lower()
        update_listbox(keyword)

    search_entry.bind('<FocusIn>', on_focus_in)
    search_entry.bind('<FocusOut>', on_focus_out)
    search_entry.bind('<KeyRelease>', on_key_release)
    search_entry.bind('<Escape>', lambda e: (search_entry.delete(0, tk.END), search_entry.insert(0, '搜索便签...'), search_entry.config(fg='#BBBBBB'), update_listbox('')))

    def on_root_click(e):
        # 点击非搜索框区域时，清除搜索框光标闪烁
        if not search_entry.winfo_exists():
            return
        bx, by = search_entry.winfo_rootx(), search_entry.winfo_rooty()
        ew, eh = search_entry.winfo_width(), search_entry.winfo_height()
        if not (bx <= e.x_root <= bx + ew and by <= e.y_root <= by + eh):
            search_entry.selection_clear()
            root.focus()

    root.bind('<Button-1>', on_root_click)

    # ── 操作按钮区 ──
    btn_area = tk.Frame(root, bg='#F5F5F5')
    btn_area.pack(fill=tk.X, padx=20, pady=(0, 8))

    def make_btn(parent, text, color, hover_color, cmd):
        btn = tk.Button(parent, text=text,
                        font=('Microsoft YaHei', 11),
                        bg=color, fg='white',
                        activebackground=hover_color,
                        activeforeground='white',
                        bd=0, relief='flat',
                        padx=10, pady=8,
                        cursor='hand2',
                        command=cmd)
        btn.bind('<Enter>', lambda e: btn.config(bg=hover_color))
        btn.bind('<Leave>', lambda e: btn.config(bg=color))
        return btn

    btn_new    = make_btn(btn_area, "＋  新建便签",    '#4CAF50', '#388E3C', create_note)
    btn_toggle = make_btn(btn_area, "◎  显示 / 隐藏", '#4A90D9', '#2C6FAC', toggle_all_notes)
    btn_del    = make_btn(btn_area, "✕  删除全部",     '#E57373', '#C62828', clear_all_notes)

    btn_new   .grid(row=0, column=0, sticky='ew', padx=(0, 5), pady=4)
    btn_toggle.grid(row=0, column=1, sticky='ew', padx=5,      pady=4)
    btn_del   .grid(row=0, column=2, sticky='ew', padx=(5, 0), pady=4)
    btn_area.columnconfigure(0, weight=1)
    btn_area.columnconfigure(1, weight=1)
    btn_area.columnconfigure(2, weight=1)

    # ── 列表区域（无边框 + 卡片阴影）────
    list_frame = tk.Frame(root, bg='#F5F5F5')
    list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 8))

    # 可滚动卡片容器（无边框）
    list_outer = tk.Frame(list_frame, bg='#F5F5F5')
    list_outer.pack(fill=tk.BOTH, expand=True)
    list_outer.pack_propagate(False)

    note_canvas = tk.Canvas(list_outer, bg='#F5F5F5', bd=0, highlightthickness=0)

    note_scrollbar = tk.Scrollbar(list_outer, orient='vertical',
                                  command=note_canvas.yview,
                                  width=6, relief='flat', bd=0)
    note_scrollbar_ref = note_scrollbar
    note_scrollbar.configure(troughcolor='#F5F5F5', bg='#CCCCCC', activebackground='#999999')

    # grid 布局：滚动条固定宽度，canvas 自适应剩余空间
    list_outer.grid_rowconfigure(0, weight=1)
    list_outer.grid_columnconfigure(0, weight=1)
    list_outer.grid_columnconfigure(1, weight=0)

    note_canvas.grid(row=0, column=0, sticky='nsew')
    note_scrollbar.grid(row=0, column=1, sticky='ns')

    note_canvas.configure(yscrollcommand=note_scrollbar.set)
    note_scrollbar.configure(command=note_canvas.yview)

    note_list_inner = tk.Frame(note_canvas, bg='#F5F5F5')
    note_canvas_window = note_canvas.create_window((0, 0), window=note_list_inner, anchor='nw')

    def on_canvas_resize(event):
        note_canvas.itemconfig(note_canvas_window, width=event.width)

    note_canvas.bind('<Configure>', on_canvas_resize)

    def on_mousewheel(event):
        note_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    note_canvas.bind_all('<MouseWheel>', on_mousewheel)

    # ── 底部状态栏 ──
    status_bar_frame = tk.Frame(root, bg='#E0E0E0', height=26)
    status_bar_frame.pack(fill=tk.X, side=tk.BOTTOM)
    status_bar_frame.pack_propagate(False)

    status_label = tk.Label(status_bar_frame,
                            text="就绪",
                            font=('Microsoft YaHei', 8),
                            bg='#E0E0E0', fg='#777777', anchor='w')
    status_label.pack(fill=tk.X, padx=10, pady=4)

    load_notes()
    update_listbox()

    print("程序启动完成")
    root.mainloop()

if __name__ == '__main__':
    main()

import tkinter as tk
from tkinter import ttk
import subprocess
import time
import win32con
import win32gui
import win32process
import ctypes
import os
from main import Module

class GDSModule(Module):
    def __init__(self, master, shared_state, module_name="CADFileConverter", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.proc = None
        self.child_hwnd = None
        self.container = None
        self._bind_id = None
        self.create_ui()

    def find_hwnd_by_pid(self, pid):
        hwnds = []
        def callback(hwnd, hwnds):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid:
                hwnds.append(hwnd)
        win32gui.EnumWindows(callback, hwnds)
        return hwnds

    def create_ui(self):
        self.container = tk.Frame(self.frame, width=800, height=600, bg="#222")
        self.container.pack(fill="both", expand=True)
        self.frame.update_idletasks()

        exe_path = os.path.join(os.path.dirname(__file__), "ODAFileConverter 26.4.0", "ODAFileConverter.exe")
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = win32con.SW_HIDE

            self.proc = subprocess.Popen(exe_path, startupinfo=startupinfo)
            pid = self.proc.pid

            # 重試找視窗（最多2秒）
            hwnds = []
            for _ in range(20):
                time.sleep(0.1)
                hwnds = self.find_hwnd_by_pid(pid)
                if hwnds:
                    break
            if not hwnds:
                raise RuntimeError("找不到對應的視窗")
            self.child_hwnd = hwnds[0]
            self.embed_external_window(self.child_hwnd, self.container)
            win32gui.ShowWindow(self.child_hwnd, win32con.SW_SHOW)
            self._bind_id = self.container.bind("<Configure>", self._resize_child)
            self.shared_state.log(f"GDSModule: ODAFileConverter 已嵌入", level=20)
        except Exception as e:
            ttk.Label(self.container, text=f"啟動 ODAFileConverter 失敗: {e}", foreground="red").pack(expand=True)
            self.shared_state.log(f"GDSModule 啟動失敗: {e}", level=40)
    def embed_external_window(self, child_hwnd, container):
        container.update_idletasks()
        parent_hwnd = container.winfo_id()
        # 移除外部視窗的邊框與標題列
        style = win32gui.GetWindowLong(child_hwnd, win32con.GWL_STYLE)
        style = style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME)
        win32gui.SetWindowLong(child_hwnd, win32con.GWL_STYLE, style)
        # 設定父視窗
        ctypes.windll.user32.SetParent(child_hwnd, parent_hwnd)
        # 初始調整大小
        w, h = container.winfo_width(), container.winfo_height()
        win32gui.MoveWindow(child_hwnd, 0, 0, w, h, True)

    def _resize_child(self, event):
        if self.child_hwnd:
            win32gui.MoveWindow(self.child_hwnd, 0, 0, event.width, event.height, True)

    def on_destroy(self):
        # 清理外部程式
        if self._bind_id:
            self.container.unbind("<Configure>", self._bind_id)
        if self.child_hwnd:
            try:
                win32gui.ShowWindow(self.child_hwnd, win32con.SW_HIDE)
            except Exception:
                pass
        if self.proc:
            try:
                self.proc.terminate()
            except Exception:
                pass
        self.shared_state.log(f"GDSModule 已關閉", level=20)
        super().on_destroy()

# 不要有 main block，讓 main.py 匯入使用

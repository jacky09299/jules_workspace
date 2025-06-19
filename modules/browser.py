import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sys
import os
import json
from cefpython3 import cefpython as cef

class ChromeBrowser(tk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.root.title("Chrome瀏覽器")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        self.pack(fill=tk.BOTH, expand=True)

        self.bookmarks = []
        self.history = []
        self.tabs = []
        self.current_tab = None
        self.closing_tabs = 0

        self.load_bookmarks()
        self.load_history()

        self.create_interface()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_interface(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.create_toolbar(main_frame)
        self.create_tabbar(main_frame)
        self.tab_container = ttk.Frame(main_frame)
        self.tab_container.pack(fill=tk.BOTH, expand=True)
        self.create_status_bar(main_frame)

        # self.new_tab()  # <-- 移除這行

    def create_toolbar(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 2))
        self.newtab_btn = ttk.Button(toolbar, text="＋", width=3, command=self.new_tab)
        self.newtab_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.back_btn = ttk.Button(toolbar, text="←", width=3, command=self.go_back)
        self.back_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.forward_btn = ttk.Button(toolbar, text="→", width=3, command=self.go_forward)
        self.forward_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.refresh_btn = ttk.Button(toolbar, text="⟲", width=3, command=self.refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.home_btn = ttk.Button(toolbar, text="🏠", width=3, command=self.go_home)
        self.home_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.bookmark_btn = ttk.Button(toolbar, text="☆", width=3, command=self.toggle_bookmark)
        self.bookmark_btn.pack(side=tk.LEFT, padx=(0, 2))
        self.menu_btn = ttk.Button(toolbar, text="⋮", width=3, command=self.show_menu)
        self.menu_btn.pack(side=tk.RIGHT, padx=(2, 0))
        zoom_frame = ttk.Frame(toolbar)
        zoom_frame.pack(side=tk.RIGHT, padx=(0, 10))
        ttk.Button(zoom_frame, text="-", width=2, command=self.zoom_out).pack(side=tk.LEFT)
        ttk.Label(zoom_frame, text="100%").pack(side=tk.LEFT, padx=5)
        ttk.Button(zoom_frame, text="+", width=2, command=self.zoom_in).pack(side=tk.LEFT)

    def create_tabbar(self, parent):
        self.tabbar = ttk.Frame(parent)
        self.tabbar.pack(fill=tk.X, pady=(0, 2))

    def update_tabbar(self):
        for widget in self.tabbar.winfo_children():
            widget.destroy()
        for idx, tab in enumerate(self.tabs):
            style = {"background": "#e0e0e0"} if idx == self.current_tab else {}
            btn = ttk.Button(self.tabbar, text=tab.get_title(), width=18, command=lambda i=idx: self.switch_tab(i))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            if idx == self.current_tab:
                btn.state(['pressed'])
            close_btn = ttk.Button(self.tabbar, text="✕", width=2, command=lambda i=idx: self.close_tab(i))
            close_btn.pack(side=tk.LEFT, padx=(0, 4), pady=2)

    def new_tab(self):
        tab = Tab(self.tab_container, self)
        self.tabs.append(tab)
        self.switch_tab(len(self.tabs) - 1)

    def switch_tab(self, idx):
        if self.current_tab is not None:
            self.tabs[self.current_tab].pack_forget()
        self.current_tab = idx
        self.tabs[idx].pack(fill=tk.BOTH, expand=True)
        self.update_tabbar()
        self.update_toolbar_state()

    def close_tab(self, idx):
        if len(self.tabs) == 1:
            messagebox.showinfo("提示", "至少要保留一個標籤頁")
            return
        tab = self.tabs.pop(idx)
        tab.destroy()
        if self.current_tab >= len(self.tabs):
            self.current_tab = len(self.tabs) - 1
        self.switch_tab(self.current_tab)

    def update_toolbar_state(self):
        tab = self.tabs[self.current_tab]
        self.back_btn.config(state="normal" if tab.can_go_back() else "disabled")
        self.forward_btn.config(state="normal" if tab.can_go_forward() else "disabled")
        self.bookmark_btn.config(text="★" if tab.is_bookmarked() else "☆")

    def create_status_bar(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_label = ttk.Label(status_frame, text="就緒", relief="sunken")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))

    # --- Toolbar actions, delegate to current tab ---
    def go_back(self):
        self.tabs[self.current_tab].go_back()

    def go_forward(self):
        self.tabs[self.current_tab].go_forward()

    def refresh(self):
        self.tabs[self.current_tab].refresh()

    def go_home(self):
        self.tabs[self.current_tab].go_home()

    def zoom_in(self):
        self.tabs[self.current_tab].zoom_in()

    def zoom_out(self):
        self.tabs[self.current_tab].zoom_out()

    def toggle_bookmark(self):
        self.tabs[self.current_tab].toggle_bookmark()

    # --- Menu ---
    def show_menu(self):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="新標籤頁", command=self.new_tab)
        menu.add_separator()
        menu.add_command(label="書籤管理", command=self.show_bookmarks)
        menu.add_command(label="歷史記錄", command=self.show_history)
        menu.add_separator()
        menu.add_command(label="開發者工具", command=self.open_dev_tools)
        menu.add_command(label="檢視原始碼", command=self.view_source)
        menu.add_separator()
        menu.add_command(label="設定", command=self.open_settings)
        menu.add_command(label="關於", command=self.show_about)
        try:
            menu.tk_popup(self.menu_btn.winfo_rootx(), self.menu_btn.winfo_rooty() + 25)
        finally:
            menu.grab_release()

    def new_window(self):
        # 用 Toplevel 開新視窗，避免多主執行緒 CEF 問題
        new_win = tk.Toplevel(self.root)
        new_win.title("Chrome瀏覽器")
        ChromeBrowser(new_win)

    def show_bookmarks(self):
        if not self.bookmarks:
            messagebox.showinfo("書籤", "沒有書籤")
            return
        bookmark_window = tk.Toplevel(self.root)
        bookmark_window.title("書籤管理")
        bookmark_window.geometry("400x300")
        listbox = tk.Listbox(bookmark_window, font=("Arial", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for bookmark in self.bookmarks:
            if isinstance(bookmark, dict):
                listbox.insert(tk.END, f"{bookmark['title']} - {bookmark['url']}")
            else:
                listbox.insert(tk.END, bookmark)
        def open_bookmark(event):
            selection = listbox.curselection()
            if selection:
                bookmark = self.bookmarks[selection[0]]
                url = bookmark['url'] if isinstance(bookmark, dict) else bookmark
                self.url_var.set(url)
                self.navigate_to_url()
                bookmark_window.destroy()
        listbox.bind("<Double-Button-1>", open_bookmark)

    def show_history(self):
        if not self.history:
            messagebox.showinfo("歷史記錄", "沒有歷史記錄")
            return
        history_window = tk.Toplevel(self.root)
        history_window.title("歷史記錄")
        history_window.geometry("500x400")
        listbox = tk.Listbox(history_window, font=("Arial", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for item in reversed(self.history[-50:]):
            listbox.insert(tk.END, item)
        def open_history_item(event):
            selection = listbox.curselection()
            if selection:
                url = self.history[-(selection[0] + 1)]
                self.url_var.set(url)
                self.navigate_to_url()
                history_window.destroy()
        listbox.bind("<Double-Button-1>", open_history_item)

    def open_dev_tools(self):
        self.tabs[self.current_tab].open_dev_tools()

    def view_source(self):
        self.tabs[self.current_tab].view_source()

    def open_settings(self):
        messagebox.showinfo("設定", "設定功能正在開發中")

    def show_about(self):
        about_text = """Chrome瀏覽器克隆版

基於 Python tkinter + cefpython3 開發
版本: 1.0.0

功能特點:
• 完整的網頁瀏覽
• 書籤管理
• 歷史記錄
• 開發者工具
• 縮放控制
• SSL 指示器

開發者: Python 愛好者"""
        messagebox.showinfo("關於", about_text)

    def on_closing(self):
        """參考tkinter_.py，正確釋放所有 CEF browser 與 Tk 資源"""
        try:
            self.save_bookmarks()
            self.save_history()
            # 關閉所有 tab 的 browser
            for tab in self.tabs:
                if tab.browser:
                    tab.browser.CloseBrowser(True)
                    tab.browser = None
            # 直接銷毀 Tk 視窗（tkinter_.py 是這樣做的）
            self.root.destroy()
            # 關閉 CEF
            cef.Shutdown()
        except Exception as e:
            print(f"關閉錯誤: {e}")
            try:
                cef.Shutdown()
            except:
                pass
            self.root.destroy()

    def on_tab_closed(self):
        """當標籤頁關閉時呼叫"""
        self.closing_tabs -= 1
        if self.closing_tabs <= 0:
            self._final_shutdown()

    def run(self):
        self.root.mainloop()

    # --- 書籤與歷史記錄共用 ---
    def add_to_history(self, url):
        if url not in self.history:
            self.history.append(url)
            if len(self.history) > 1000:
                self.history = self.history[-500:]
            self.save_history()

    def load_bookmarks(self):
        try:
            if os.path.exists("bookmarks.json"):
                with open("bookmarks.json", "r", encoding="utf-8") as f:
                    self.bookmarks = json.load(f)
        except:
            self.bookmarks = []

    def save_bookmarks(self):
        try:
            with open("bookmarks.json", "w", encoding="utf-8") as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_history(self):
        try:
            if os.path.exists("history.json"):
                with open("history.json", "r", encoding="utf-8") as f:
                    self.history = json.load(f)
        except:
            self.history = []

    def save_history(self):
        try:
            with open("history.json", "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except:
            pass

class Tab(ttk.Frame):
    def __init__(self, parent, browser_app):
        super().__init__(parent)
        self.browser_app = browser_app
        self.url_var = tk.StringVar()
        self.is_loading = False
        self.title = "新標籤頁"
        self.browser = None
        self.closing = False  # 修正：確保有 closing 屬性

        self.create_address_bar()
        self.create_browser_container()
        self.embed_browser()

    def create_address_bar(self):
        address_frame = ttk.Frame(self)
        address_frame.pack(fill=tk.X, pady=(0, 2))
        self.ssl_label = ttk.Label(address_frame, text="🔒", foreground="green")
        self.ssl_label.pack(side=tk.LEFT, padx=(5, 2))
        self.url_entry = ttk.Entry(address_frame, textvariable=self.url_var, font=("Arial", 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.url_entry.bind("<Return>", self.navigate_to_url)
        self.url_entry.bind("<Button-1>", self.select_all_url)
        self.go_btn = ttk.Button(address_frame, text="Go", command=self.navigate_to_url)
        self.go_btn.pack(side=tk.RIGHT)

    def create_browser_container(self):
        self.browser_container = ttk.Frame(self, relief="sunken", borderwidth=1)
        self.browser_container.pack(fill=tk.BOTH, expand=True)
        self.browser_container.bind("<Configure>", self.on_browser_container_configure)

    def on_browser_container_configure(self, event):
        if not self.browser:
            self.embed_browser()
        else:
            width = self.browser_container.winfo_width()
            height = self.browser_container.winfo_height()
            try:
                import ctypes
                ctypes.windll.user32.SetWindowPos(
                    self.browser.GetWindowHandle(), 0,
                    0, 0, width, height, 0x0002)
            except Exception:
                pass
            self.browser.NotifyMoveOrResizeStarted()

    def embed_browser(self):
        if self.browser:
            return
        self.browser_app.root.update_idletasks()
        window_info = cef.WindowInfo()
        width = self.browser_container.winfo_width()
        height = self.browser_container.winfo_height()
        rect = [0, 0, width, height]
        window_info.SetAsChild(self.browser_container.winfo_id(), rect)
        browser_settings = {
            "web_security_disabled": True,
            "file_access_from_file_urls_allowed": True,
            "universal_access_from_file_urls_allowed": True,
        }
        self.browser = cef.CreateBrowserSync(
            window_info=window_info,
            url="https://www.google.com",
            settings=browser_settings
        )
        self.browser.SetClientHandler(ClientHandler(self))
        self.browser.SetClientHandler(LifespanHandler(self))  # 新增
        self.url_var.set("https://www.google.com")
        self.message_loop_work()

    def message_loop_work(self):
        cef.MessageLoopWork()
        self.browser_app.root.after(10, self.message_loop_work)

    def navigate_to_url(self, event=None):
        url = self.url_var.get().strip()
        if not url:
            return
        if not url.startswith(('http://', 'https://')):
            if '.' in url and ' ' not in url:
                url = 'https://' + url
            else:
                url = f'https://www.google.com/search?q={url}'
        if self.browser:
            self.browser.LoadUrl(url)
            self.browser_app.add_to_history(url)

    def select_all_url(self, event=None):
        self.url_entry.select_range(0, tk.END)

    def go_back(self):
        if self.browser and self.browser.CanGoBack():
            self.browser.GoBack()

    def go_forward(self):
        if self.browser and self.browser.CanGoForward():
            self.browser.GoForward()

    def refresh(self):
        if self.browser:
            self.browser.Reload()

    def go_home(self):
        self.url_var.set("https://www.google.com")
        self.navigate_to_url()

    def zoom_in(self):
        if self.browser:
            self.browser.SetZoomLevel(self.browser.GetZoomLevel() + 0.5)

    def zoom_out(self):
        if self.browser:
            self.browser.SetZoomLevel(self.browser.GetZoomLevel() - 0.5)

    def toggle_bookmark(self):
        current_url = self.url_var.get()
        urls = [b['url'] if isinstance(b, dict) else b for b in self.browser_app.bookmarks]
        if current_url in urls:
            self.browser_app.bookmarks = [b for b in self.browser_app.bookmarks if (b['url'] if isinstance(b, dict) else b) != current_url]
            self.browser_app.bookmark_btn.config(text="☆")
            messagebox.showinfo("書籤", "已從書籤中移除")
        else:
            title = simpledialog.askstring("添加書籤", "請輸入書籤標題:", initialvalue=current_url)
            if title:
                self.browser_app.bookmarks.append({"title": title, "url": current_url})
                self.browser_app.bookmark_btn.config(text="★")
                messagebox.showinfo("書籤", "已添加到書籤")
        self.browser_app.save_bookmarks()

    def open_dev_tools(self):
        if self.browser:
            self.browser.ShowDevTools()

    def view_source(self):
        if self.browser:
            current_url = self.url_var.get()
            source_url = f"view-source:{current_url}"
            self.browser.LoadUrl(source_url)

    def close_browser(self):
        """關閉瀏覽器"""
        if self.browser:
            self.closing = True
            self.browser.CloseBrowser(True)
            self.browser = None

    def can_go_back(self):
        return self.browser and self.browser.CanGoBack()

    def can_go_forward(self):
        return self.browser and self.browser.CanGoForward()

    def is_bookmarked(self):
        current_url = self.url_var.get()
        urls = [b['url'] if isinstance(b, dict) else b for b in self.browser_app.bookmarks]
        return current_url in urls

    def get_title(self):
        return self.title

    # 狀態列與標題由 ClientHandler 更新
    def update_title(self, title):
        self.title = title
        self.browser_app.update_tabbar()

class ClientHandler:
    def __init__(self, tab):
        self.tab = tab

    def OnLoadStart(self, browser, frame, **_):
        try:
            if frame.IsMain():
                self.tab.is_loading = True
                self.tab.browser_app.status_label.config(text="正在加載...")
                self.tab.browser_app.progress.start()
        except Exception as e:
            print(f"OnLoadStart 錯誤: {e}")

    def OnLoadEnd(self, browser, frame, **_):
        try:
            if frame.IsMain():
                self.tab.is_loading = False
                self.tab.browser_app.status_label.config(text="載入完成")
                self.tab.browser_app.progress.stop()
                url = browser.GetUrl()
                self.tab.url_var.set(url)
                try:
                    title = browser.GetTitle() if hasattr(browser, 'GetTitle') else "新標籤頁"
                    if title:
                        self.tab.update_title(title[:20] + "..." if len(title) > 20 else title)
                        self.tab.browser_app.root.title(f"{title} - Chrome瀏覽器")
                except:
                    pass
                if url.startswith("https://"):
                    self.tab.ssl_label.config(text="🔒", foreground="green")
                else:
                    self.tab.ssl_label.config(text="🔓", foreground="red")
                self.tab.browser_app.update_toolbar_state()
        except Exception as e:
            print(f"OnLoadEnd 錯誤: {e}")

    def OnLoadError(self, browser, frame, error_code, error_text_out, failed_url):
        try:
            if frame.IsMain():
                self.tab.browser_app.status_label.config(text=f"載入錯誤: {error_text_out}")
                self.tab.browser_app.progress.stop()
        except Exception as e:
            print(f"OnLoadError 錯誤: {e}")

    def OnLoadingStateChange(self, browser, is_loading, **_):
        try:
            self.tab.browser_app.update_toolbar_state()
        except Exception as e:
            print(f"OnLoadingStateChange 錯誤: {e}")

class LifespanHandler(object):
    def __init__(self, tab):
        self.tab = tab

    def OnBeforeClose(self, browser, **_):
        """在瀏覽器關閉前呼叫"""
        if self.tab.closing:
            self.tab.browser_app.on_tab_closed()

def main():
    sys.excepthook = cef.ExceptHook
    root = tk.Tk()
    settings = {
        "multi_threaded_message_loop": False,
    }
    cef.Initialize(settings=settings)
    app = ChromeBrowser(root)
    app.new_tab()
    app.run()

if __name__ == "__main__":
    main()
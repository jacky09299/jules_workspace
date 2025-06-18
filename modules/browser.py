import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import sys
import os
import json
from urllib.parse import urlparse
import webbrowser

# CEF Python imports
try:
    from cefpython3 import cefpython as cef
except ImportError:
    print("請安裝 cefpython3: pip install cefpython3")
    sys.exit(1)

class ChromeBrowser:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chrome瀏覽器")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 瀏覽器相關變量
        self.browser = None
        self.browser_frame = None
        self.url_var = tk.StringVar()
        self.is_loading = False
        self.bookmarks = []
        self.history = []
        self.tabs = []
        self.current_tab = 0
        
        # 載入書籤和歷史記錄
        self.load_bookmarks()
        self.load_history()
        
        # 初始化 CEF
        self.init_cef()
        
        # 創建界面
        self.create_interface()
        
        # 綁定關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def init_cef(self):
        """初始化 CEF 設置"""
        sys.excepthook = cef.ExceptHook  # 處理異常
        
        # CEF 設置
        settings = {
            "multi_threaded_message_loop": False,
            "debug": False,
            "log_severity": cef.LOGSEVERITY_INFO,
            "log_file": "debug.log",
        }
        
        cef.Initialize(settings)
        
    def create_interface(self):
        """創建用戶界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 創建工具欄
        self.create_toolbar(main_frame)
        
        # 創建地址欄
        self.create_address_bar(main_frame)
        
        # 創建瀏覽器容器
        self.create_browser_container(main_frame)
        
        # 創建狀態欄
        self.create_status_bar(main_frame)
        
        # 啟動瀏覽器
        self.start_browser()
        
    def create_toolbar(self, parent):
        """創建工具欄"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 2))
        
        # 導航按鈕
        self.back_btn = ttk.Button(toolbar, text="←", width=3, command=self.go_back)
        self.back_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.forward_btn = ttk.Button(toolbar, text="→", width=3, command=self.go_forward)
        self.forward_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.refresh_btn = ttk.Button(toolbar, text="⟲", width=3, command=self.refresh)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.home_btn = ttk.Button(toolbar, text="🏠", width=3, command=self.go_home)
        self.home_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 書籤按鈕
        self.bookmark_btn = ttk.Button(toolbar, text="☆", width=3, command=self.toggle_bookmark)
        self.bookmark_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # 菜單按鈕
        self.menu_btn = ttk.Button(toolbar, text="⋮", width=3, command=self.show_menu)
        self.menu_btn.pack(side=tk.RIGHT, padx=(2, 0))
        
        # 縮放控制
        zoom_frame = ttk.Frame(toolbar)
        zoom_frame.pack(side=tk.RIGHT, padx=(0, 10))
        
        ttk.Button(zoom_frame, text="-", width=2, command=self.zoom_out).pack(side=tk.LEFT)
        ttk.Label(zoom_frame, text="100%").pack(side=tk.LEFT, padx=5)
        ttk.Button(zoom_frame, text="+", width=2, command=self.zoom_in).pack(side=tk.LEFT)
        
    def create_address_bar(self, parent):
        """創建地址欄"""
        address_frame = ttk.Frame(parent)
        address_frame.pack(fill=tk.X, pady=(0, 2))
        
        # SSL 指示器
        self.ssl_label = ttk.Label(address_frame, text="🔒", foreground="green")
        self.ssl_label.pack(side=tk.LEFT, padx=(5, 2))
        
        # 地址輸入框
        self.url_entry = ttk.Entry(address_frame, textvariable=self.url_var, font=("Arial", 10))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.url_entry.bind("<Return>", self.navigate_to_url)
        self.url_entry.bind("<Button-1>", self.select_all_url)
        
        # 搜索/導航按鈕
        self.go_btn = ttk.Button(address_frame, text="Go", command=self.navigate_to_url)
        self.go_btn.pack(side=tk.RIGHT)
        
    def create_browser_container(self, parent):
        """創建瀏覽器容器"""
        # 標籤頁框架
        tab_frame = ttk.Frame(parent)
        tab_frame.pack(fill=tk.X, pady=(0, 2))
        
        # 當前只創建一個標籤頁，實際應用中可以添加標籤頁管理
        self.tab_label = ttk.Label(tab_frame, text="新標籤頁", background="white", relief="solid")
        self.tab_label.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 瀏覽器框架
        self.browser_container = ttk.Frame(parent, relief="sunken", borderwidth=1)
        self.browser_container.pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self, parent):
        """創建狀態欄"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(status_frame, text="就緒", relief="sunken")
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 加載進度條
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
        
    def start_browser(self):
        """啟動瀏覽器"""
        try:
            # 確保容器已經顯示
            self.root.update()
            
            # 獲取容器的窗口句柄
            window_info = cef.WindowInfo()
            window_info.SetAsChild(self.browser_container.winfo_id())
            
            # 瀏覽器設置
            browser_settings = {
                "web_security_disabled": True,
                "file_access_from_file_urls_allowed": True,
                "universal_access_from_file_urls_allowed": True,
            }
            
            # 創建瀏覽器
            self.browser = cef.CreateBrowserSync(
                window_info=window_info,
                url="https://www.google.com",
                settings=browser_settings
            )
            
            # 設置客戶端處理器
            client_handler = ClientHandler(self)
            self.browser.SetClientHandler(client_handler)
            
            # 設置初始 URL
            self.url_var.set("https://www.google.com")
            
            # 啟動消息循環
            self.message_loop()
            
        except Exception as e:
            print(f"啟動瀏覽器時發生錯誤: {e}")
            messagebox.showerror("錯誤", f"無法啟動瀏覽器引擎: {e}")
            self.root.quit()
        
    def message_loop(self):
        """CEF 消息循環"""
        cef.MessageLoopWork()
        self.root.after(10, self.message_loop)
        
    def navigate_to_url(self, event=None):
        """導航到指定 URL"""
        url = self.url_var.get().strip()
        if not url:
            return
            
        # 處理 URL
        if not url.startswith(('http://', 'https://')):
            if '.' in url and ' ' not in url:
                url = 'https://' + url
            else:
                # 搜索查詢
                url = f'https://www.google.com/search?q={url}'
                
        if self.browser:
            self.browser.LoadUrl(url)
            self.add_to_history(url)
            
    def select_all_url(self, event=None):
        """選中地址欄所有文本"""
        self.url_entry.select_range(0, tk.END)
        
    def go_back(self):
        """後退"""
        if self.browser and self.browser.CanGoBack():
            self.browser.GoBack()
            
    def go_forward(self):
        """前進"""
        if self.browser and self.browser.CanGoForward():
            self.browser.GoForward()
            
    def refresh(self):
        """刷新"""
        if self.browser:
            self.browser.Reload()
            
    def go_home(self):
        """回到首頁"""
        self.url_var.set("https://www.google.com")
        self.navigate_to_url()
        
    def zoom_in(self):
        """放大"""
        if self.browser:
            self.browser.SetZoomLevel(self.browser.GetZoomLevel() + 0.5)
            
    def zoom_out(self):
        """縮小"""
        if self.browser:
            self.browser.SetZoomLevel(self.browser.GetZoomLevel() - 0.5)
            
    def toggle_bookmark(self):
        """切換書籤"""
        current_url = self.url_var.get()
        if current_url in self.bookmarks:
            self.bookmarks.remove(current_url)
            self.bookmark_btn.config(text="☆")
            messagebox.showinfo("書籤", "已從書籤中移除")
        else:
            title = simpledialog.askstring("添加書籤", "請輸入書籤標題:", initialvalue=current_url)
            if title:
                self.bookmarks.append({"title": title, "url": current_url})
                self.bookmark_btn.config(text="★")
                messagebox.showinfo("書籤", "已添加到書籤")
        self.save_bookmarks()
        
    def show_menu(self):
        """顯示菜單"""
        menu = tk.Menu(self.root, tearoff=0)
        
        # 文件菜單
        menu.add_command(label="新標籤頁", command=self.new_tab)
        menu.add_command(label="新視窗", command=self.new_window)
        menu.add_separator()
        menu.add_command(label="書籤管理", command=self.show_bookmarks)
        menu.add_command(label="歷史記錄", command=self.show_history)
        menu.add_separator()
        menu.add_command(label="開發者工具", command=self.open_dev_tools)
        menu.add_command(label="檢視原始碼", command=self.view_source)
        menu.add_separator()
        menu.add_command(label="設定", command=self.open_settings)
        menu.add_command(label="關於", command=self.show_about)
        
        # 顯示菜單
        try:
            menu.tk_popup(self.menu_btn.winfo_rootx(), self.menu_btn.winfo_rooty() + 25)
        finally:
            menu.grab_release()
            
    def new_tab(self):
        """新標籤頁 (簡化版本)"""
        messagebox.showinfo("新標籤頁", "新標籤頁功能正在開發中")
        
    def new_window(self):
        """新視窗"""
        new_browser = ChromeBrowser()
        new_browser.run()
        
    def show_bookmarks(self):
        """顯示書籤"""
        if not self.bookmarks:
            messagebox.showinfo("書籤", "沒有書籤")
            return
            
        bookmark_window = tk.Toplevel(self.root)
        bookmark_window.title("書籤管理")
        bookmark_window.geometry("400x300")
        
        # 書籤列表
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
        """顯示歷史記錄"""
        if not self.history:
            messagebox.showinfo("歷史記錄", "沒有歷史記錄")
            return
            
        history_window = tk.Toplevel(self.root)
        history_window.title("歷史記錄")
        history_window.geometry("500x400")
        
        # 歷史記錄列表
        listbox = tk.Listbox(history_window, font=("Arial", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for item in reversed(self.history[-50:]):  # 顯示最近50條
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
        """打開開發者工具"""
        if self.browser:
            self.browser.ShowDevTools()
            
    def view_source(self):
        """檢視原始碼"""
        if self.browser:
            current_url = self.url_var.get()
            source_url = f"view-source:{current_url}"
            self.browser.LoadUrl(source_url)
            
    def open_settings(self):
        """打開設定"""
        messagebox.showinfo("設定", "設定功能正在開發中")
        
    def show_about(self):
        """關於對話框"""
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
        
    def add_to_history(self, url):
        """添加到歷史記錄"""
        if url not in self.history:
            self.history.append(url)
            if len(self.history) > 1000:  # 限制歷史記錄數量
                self.history = self.history[-500:]
            self.save_history()
            
    def load_bookmarks(self):
        """載入書籤"""
        try:
            if os.path.exists("bookmarks.json"):
                with open("bookmarks.json", "r", encoding="utf-8") as f:
                    self.bookmarks = json.load(f)
        except:
            self.bookmarks = []
            
    def save_bookmarks(self):
        """保存書籤"""
        try:
            with open("bookmarks.json", "w", encoding="utf-8") as f:
                json.dump(self.bookmarks, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    def load_history(self):
        """載入歷史記錄"""
        try:
            if os.path.exists("history.json"):
                with open("history.json", "r", encoding="utf-8") as f:
                    self.history = json.load(f)
        except:
            self.history = []
            
    def save_history(self):
        """保存歷史記錄"""
        try:
            with open("history.json", "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except:
            pass
            
    def on_closing(self):
        """關閉程序"""
        try:
            self.save_bookmarks()
            self.save_history()
            
            if self.browser:
                self.browser.CloseBrowser(True)
            
            # 等待一小段時間讓瀏覽器正確關閉
            self.root.after(100, self._final_shutdown)
        except Exception as e:
            print(f"關閉錯誤: {e}")
            self._final_shutdown()
            
    def _final_shutdown(self):
        """最終關閉程序"""
        try:
            cef.Shutdown()
        except:
            pass
        finally:
            self.root.quit()
            self.root.destroy()
        
    def run(self):
        """運行瀏覽器"""
        self.root.mainloop()


class ClientHandler:
    """CEF 客戶端處理器"""
    
    def __init__(self, browser_app):
        self.browser_app = browser_app
        
    def OnLoadStart(self, browser, frame, **_):
        """頁面開始加載"""
        try:
            if frame.IsMain():
                self.browser_app.is_loading = True
                self.browser_app.status_label.config(text="正在加載...")
                self.browser_app.progress.start()
        except Exception as e:
            print(f"OnLoadStart 錯誤: {e}")
            
    def OnLoadEnd(self, browser, frame, **_):
        """頁面加載完成"""
        try:
            if frame.IsMain():
                self.browser_app.is_loading = False
                self.browser_app.status_label.config(text="載入完成")
                self.browser_app.progress.stop()
                
                # 更新地址欄
                url = browser.GetUrl()
                self.browser_app.url_var.set(url)
                
                # 更新標題
                try:
                    title = browser.GetTitle() if hasattr(browser, 'GetTitle') else "新標籤頁"
                    if title:
                        self.browser_app.root.title(f"{title} - Chrome瀏覽器")
                        self.browser_app.tab_label.config(text=title[:20] + "..." if len(title) > 20 else title)
                except:
                    pass
                    
                # 更新 SSL 指示器
                if url.startswith("https://"):
                    self.browser_app.ssl_label.config(text="🔒", foreground="green")
                else:
                    self.browser_app.ssl_label.config(text="🔓", foreground="red")
                    
                # 更新書籤按鈕
                if url in [b['url'] if isinstance(b, dict) else b for b in self.browser_app.bookmarks]:
                    self.browser_app.bookmark_btn.config(text="★")
                else:
                    self.browser_app.bookmark_btn.config(text="☆")
        except Exception as e:
            print(f"OnLoadEnd 錯誤: {e}")
                
    def OnLoadError(self, browser, frame, error_code, error_text_out, failed_url):
        """頁面加載錯誤"""
        try:
            if frame.IsMain():
                self.browser_app.status_label.config(text=f"載入錯誤: {error_text_out}")
                self.browser_app.progress.stop()
        except Exception as e:
            print(f"OnLoadError 錯誤: {e}")
            
    def OnLoadingStateChange(self, browser, is_loading, **_):
        """加載狀態改變"""
        try:
            # 更新按鈕狀態
            can_go_back = browser.CanGoBack()
            can_go_forward = browser.CanGoForward()
            
            self.browser_app.back_btn.config(state="normal" if can_go_back else "disabled")
            self.browser_app.forward_btn.config(state="normal" if can_go_forward else "disabled")
        except Exception as e:
            print(f"OnLoadingStateChange 錯誤: {e}")


if __name__ == "__main__":
    # 檢查 CEF 支持
    try:
        print("正在啟動瀏覽器...")
        app = ChromeBrowser()
        print("瀏覽器已初始化，正在運行...")
        app.run()
    except KeyboardInterrupt:
        print("用戶中斷程序")
    except Exception as e:
        print(f"啟動瀏覽器時發生錯誤: {e}")
        print(f"錯誤類型: {type(e).__name__}")
        print("\n請確保已安裝以下依賴:")
        print("pip install cefpython3")
        print("\n注意: cefpython3 可能需要特定的 Python 版本和系統環境")
        print("支持的 Python 版本通常為 3.6-3.9")
        input("按 Enter 鍵退出...")
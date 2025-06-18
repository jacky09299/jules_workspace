import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import subprocess
import os
import sys
import time
import queue
import re

class CMDEmulator:
    def __init__(self, root):
        self.root = root
        self.root.title("CMD 模擬器 - Tkinter + subprocess")
        self.root.geometry("900x700")
        self.root.configure(bg='black')
        
        # 創建主框架
        self.main_frame = tk.Frame(root, bg='black')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 創建文本顯示區域
        self.text_area = scrolledtext.ScrolledText(
            self.main_frame,
            bg='black',
            fg='#00ff00',  # 綠色文字，更像終端
            font=('Consolas', 11),
            insertbackground='white',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # 創建命令輸入框
        self.input_frame = tk.Frame(self.main_frame, bg='black')
        self.input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.prompt_label = tk.Label(
            self.input_frame,
            text="C:\\>",
            bg='black',
            fg='#00ff00',
            font=('Consolas', 11)
        )
        self.prompt_label.pack(side=tk.LEFT)
        
        self.command_entry = tk.Entry(
            self.input_frame,
            bg='black',
            fg='white',
            font=('Consolas', 11),
            insertbackground='white',
            relief=tk.FLAT,
            bd=0
        )
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.command_entry.bind('<Return>', self.execute_command)
        self.command_entry.bind('<Up>', self.history_up)
        self.command_entry.bind('<Down>', self.history_down)
        self.command_entry.focus_set()
        
        # 初始化變量
        self.process = None
        self.command_history = []
        self.history_index = -1
        self.current_directory = os.getcwd()
        self.output_queue = queue.Queue()
        self.is_running = True
        
        # 啟動 CMD 進程
        self.init_cmd_process()
        
        # 啟動輸出讀取線程
        self.start_output_threads()
        
        # 設置關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始顯示
        self.append_output("=== CMD 模擬器已啟動 ===\n")
        self.append_output(f"當前目錄: {self.current_directory}\n")
        self.append_output("支援 conda activate, python, cd, dir 等所有命令\n\n")
        
        # 移除自動更新提示符
        
    def init_cmd_process(self):
        """初始化 CMD 進程"""
        try:
            # 使用 subprocess.Popen 創建持久的 CMD 進程
            self.process = subprocess.Popen(
                'cmd.exe',
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,  # 無緩衝
                cwd=self.current_directory,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            self.append_output("CMD 進程已啟動\n")
        except Exception as e:
            messagebox.showerror("錯誤", f"無法啟動 CMD 進程: {str(e)}")
            sys.exit(1)
    
    def start_output_threads(self):
        """啟動輸出讀取線程"""
        # 輸出讀取線程
        self.output_thread = threading.Thread(target=self.read_output, daemon=True)
        self.output_thread.start()
        
        # 輸出處理線程
        self.display_thread = threading.Thread(target=self.process_output, daemon=True)
        self.display_thread.start()
    
    def read_output(self):
        """讀取 CMD 輸出"""
        while self.is_running and self.process and self.process.poll() is None:
            try:
                char = self.process.stdout.read(1)
                if char:
                    self.output_queue.put(char)
            except Exception as e:
                if self.is_running:
                    print(f"讀取輸出錯誤: {e}")
                break
    
    def process_output(self):
        """處理輸出隊列"""
        buffer = ""
        while self.is_running:
            try:
                # 從隊列中獲取字符
                char = self.output_queue.get(timeout=0.1)
                buffer += char
                
                # 如果遇到換行符或緩衝區達到一定大小，就輸出
                if char == '\n' or len(buffer) > 100:
                    if buffer.strip():
                        cleaned_buffer = self.clean_output(buffer)
                        if cleaned_buffer:
                            self.append_output(cleaned_buffer)
                            # 移除自動更新提示符的調用
                    buffer = ""
                    
            except queue.Empty:
                # 如果隊列為空但緩衝區有內容，也要輸出
                if buffer.strip():
                    cleaned_buffer = self.clean_output(buffer)
                    if cleaned_buffer:
                        self.append_output(cleaned_buffer)
                        # 移除自動更新提示符的調用
                    buffer = ""
                continue
            except Exception as e:
                if self.is_running:
                    print(f"處理輸出錯誤: {e}")
                break
    
    def clean_output(self, output):
        """清理輸出"""
        # 移除一些不需要的控制字符和重複的提示符
        output = re.sub(r'\x08+', '', output)  # 移除退格符
        output = re.sub(r'\r\n', '\n', output)  # 統一換行符
        output = re.sub(r'\r', '\n', output)    # 處理回車符
        
        # 過濾掉重複的提示符顯示
        lines = output.split('\n')
        filtered_lines = []
        for line in lines:
            # 跳過空的提示符行
            if re.match(r'^[A-Z]:\\.*?>$', line.strip()):
                continue
            filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    def append_output(self, text):
        """安全地添加輸出到文本區域"""
        def update_text():
            self.text_area.config(state=tk.NORMAL)
            self.text_area.insert(tk.END, text)
            self.text_area.see(tk.END)
            self.text_area.config(state=tk.DISABLED)
        
        if threading.current_thread() == threading.main_thread():
            update_text()
        else:
            self.root.after(0, update_text)
    
    def update_prompt(self):
        """更新命令提示符"""
        try:
            # 不自動發送cd命令，只是靜態更新提示符
            # 提示符會在用戶執行cd命令後自然更新
            pass
        except:
            pass
    
    def execute_command(self, event):
        """執行命令"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        # 添加到歷史記錄
        if command not in self.command_history:
            self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        # 顯示命令
        prompt = self.prompt_label.cget('text')
        self.append_output(f"{prompt} {command}\n")
        
        # 清空輸入框
        self.command_entry.delete(0, tk.END)
        
        # 發送命令到 CMD
        try:
            if self.process and self.process.poll() is None:
                self.process.stdin.write(command + '\n')
                self.process.stdin.flush()
                
                # 特殊處理 cd 命令
                if command.startswith('cd ') or command == 'cd':
                    time.sleep(0.1)  # 給 cd 命令一點時間執行
                    
            else:
                self.append_output("錯誤: CMD 進程未運行\n")
                self.restart_cmd_process()
        except Exception as e:
            self.append_output(f"命令執行錯誤: {str(e)}\n")
            self.restart_cmd_process()
    
    def restart_cmd_process(self):
        """重啟 CMD 進程"""
        try:
            if self.process:
                self.process.terminate()
            self.init_cmd_process()
            self.append_output("\n=== CMD 進程已重啟 ===\n")
        except Exception as e:
            self.append_output(f"重啟進程失敗: {str(e)}\n")
    
    def history_up(self, event):
        """向上瀏覽命令歷史"""
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.history_index])
    
    def history_down(self, event):
        """向下瀏覽命令歷史"""
        if self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_entry.delete(0, tk.END)
                self.command_entry.insert(0, self.command_history[self.history_index])
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.command_entry.delete(0, tk.END)
    
    def on_closing(self):
        """處理窗口關閉事件"""
        self.is_running = False
        try:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=2)
        except:
            pass
        self.root.destroy()

def main():
    """主函數"""
    try:
        root = tk.Tk()
        app = CMDEmulator(root)
        
        # 添加一些鍵盤快捷鍵
        root.bind('<Control-c>', lambda e: app.command_entry.focus_set())
        root.bind('<Control-l>', lambda e: app.text_area.delete(1.0, tk.END))
        
        root.mainloop()
        
    except Exception as e:
        print(f"啟動錯誤: {e}")
        messagebox.showerror("啟動錯誤", f"無法啟動應用程序: {str(e)}")

if __name__ == "__main__":
    main()
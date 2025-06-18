import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import subprocess
import os
import sys
import queue
import re

class CMDEmulator:
    def __init__(self, root):
        self.root = root
        self.root.title("CMD 模擬器 (已修正)")
        self.root.geometry("900x700")
        self.root.configure(bg='black')
        
        self.main_frame = tk.Frame(root, bg='black')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text_area = scrolledtext.ScrolledText(
            self.main_frame,
            bg='black',
            fg='#00ff00',
            font=('Consolas', 11),
            insertbackground='white',
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # --- [修改 1] 簡化輸入區域 ---
        # 我們不再需要一個假的 prompt_label，因為 cmd.exe 會自己顯示真實的提示符。
        self.command_entry = tk.Entry(
            self.main_frame,
            bg='black',
            fg='white',
            font=('Consolas', 11),
            insertbackground='white',
            relief=tk.FLAT,
            bd=0
        )
        self.command_entry.pack(fill=tk.X, pady=(5, 0))
        self.command_entry.bind('<Return>', self.execute_command)
        self.command_entry.bind('<Up>', self.history_up)
        self.command_entry.bind('<Down>', self.history_down)
        self.command_entry.focus_set()

        # --- 新增: 按鈕區域 ---
        self.button_frame = tk.Frame(self.main_frame, bg='black')
        self.button_frame.pack(fill=tk.X, pady=(5, 0))

        self.deactivate_btn = tk.Button(
            self.button_frame, text="切換為正常CMD",
            command=self.conda_deactivate,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.deactivate_btn.pack(side=tk.LEFT, padx=5)

        self.activate_btn = tk.Button(
            self.button_frame, text="切換為Conda(base)",
            command=self.conda_activate_base,
            bg='#222', fg='white', font=('Consolas', 10), relief=tk.RAISED
        )
        self.activate_btn.pack(side=tk.LEFT, padx=5)

        self.process = None
        self.command_history = []
        self.history_index = -1
        # 我們不再需要自己追蹤 current_directory，讓 cmd.exe 內部處理
        self.output_queue = queue.Queue()
        self.is_running = True
        
        self.init_cmd_process()
        self.start_output_threads()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.append_output("=== CMD 模擬器已啟動 ===\n")
        self.append_output("支援 conda, python, cd, dir 等所有原生命令\n\n")

    def init_cmd_process(self):
        try:
            # 設定環境變數，確保 conda 可以被找到
            # 這一步很重要，特別是如果 conda 不在系統預設的 PATH 中
            env = os.environ.copy()
            # 如果你的 conda 不在預設路徑，可能需要手動添加 conda 的 Scripts 路徑
            # 例如: env['PATH'] = 'C:\\path\\to\\anaconda3\\Scripts;' + env['PATH']
            
            self.process = subprocess.Popen(
                ['cmd.exe'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # 將 stderr 合併到 stdout
                text=True,
                encoding='utf-8', # 明確指定編碼
                errors='replace', # 處理潛在的編碼錯誤
                bufsize=1,  # 行緩衝
                cwd=os.getcwd(),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                env=env
            )
            # 啟動時發送一個 enter，讓初始提示符顯示出來
            self.process.stdin.write('\n')
            self.process.stdin.flush()

        except Exception as e:
            messagebox.showerror("錯誤", f"無法啟動 CMD 進程: {str(e)}")
            self.root.destroy()
            sys.exit(1)
    
    def start_output_threads(self):
        self.output_thread = threading.Thread(target=self.read_output, daemon=True)
        self.output_thread.start()
        
        self.display_thread = threading.Thread(target=self.process_output, daemon=True)
        self.display_thread.start()
    
    def read_output(self):
        # 使用 iter 來讀取輸出，這比 read(1) 更高效且不易出錯
        try:
            for char in iter(lambda: self.process.stdout.read(1), ''):
                if not self.is_running:
                    break
                self.output_queue.put(char)
        except Exception as e:
            if self.is_running:
                print(f"讀取輸出時發生錯誤: {e}")

    def process_output(self):
        """處理輸出隊列，不再進行複雜的清理"""
        while self.is_running:
            try:
                # 從隊列中一次性獲取所有可用數據，減少 GUI 更新次數
                output_chunk = self.output_queue.get(block=True, timeout=0.1)
                while not self.output_queue.empty():
                    output_chunk += self.output_queue.get_nowait()
                
                if output_chunk:
                    # --- [修改 2] 簡化清理邏輯 ---
                    # 我們只做最基本的清理，不再過濾提示符
                    cleaned_output = self.clean_output(output_chunk)
                    self.append_output(cleaned_output)
                    
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_running:
                    print(f"處理輸出時發生錯誤: {e}")
                break
    
    # --- [修改 3] 大幅簡化 clean_output ---
    def clean_output(self, output):
        """只進行最基本的清理，例如統一換行符"""
        # cmd.exe 在互動模式下通常使用 \r\n，但有時也可能混雜其他東西
        # 我們把 \r\n 轉成 \n，並移除單獨的 \r
        output = output.replace('\r\n', '\n')
        output = output.replace('\r', '')
        return output
    
    def append_output(self, text):
        def update_text():
            self.text_area.config(state=tk.NORMAL)
            self.text_area.insert(tk.END, text)
            self.text_area.see(tk.END)
            self.text_area.config(state=tk.DISABLED)
        
        if threading.current_thread() == threading.main_thread():
            update_text()
        else:
            self.root.after(0, update_text)
    
    # --- [修改 4] 移除 update_prompt 方法，不再需要 ---
    
    def execute_command(self, event):
        command = self.command_entry.get().strip()
        if not command:
            # 如果用戶只按 enter，我們也發送一個換行符到 cmd
            # 這樣可以觸發 cmd 顯示一個新的提示符，體驗更流暢
            if self.process and self.process.poll() is None:
                self.process.stdin.write('\n')
                self.process.stdin.flush()
            return
        
        if command not in self.command_history:
            self.command_history.append(command)
        self.history_index = len(self.command_history)
        
        self.command_entry.delete(0, tk.END)
        
        # --- [修改 5] 不再手動顯示 "prompt + command" ---
        # cmd.exe 自己會回顯(echo)命令，我們不需要再畫蛇添足。
        # self.append_output(f"{prompt} {command}\n") # <--- 移除此行
        
        try:
            if self.process and self.process.poll() is None:
                self.process.stdin.write(command + '\n')
                self.process.stdin.flush()
                
                # --- [修改 6] 移除對 'cd' 的特殊處理，不再需要 ---
            else:
                self.append_output("\n錯誤: CMD 進程未運行。正在嘗試重啟...\n")
                self.restart_cmd_process()
        except Exception as e:
            self.append_output(f"\n命令執行錯誤: {str(e)}\n")
            self.restart_cmd_process()
    
    def restart_cmd_process(self):
        try:
            if self.process:
                self.process.terminate()
            self.init_cmd_process()
            self.append_output("\n=== CMD 進程已重啟 ===\n")
        except Exception as e:
            self.append_output(f"重啟進程失敗: {str(e)}\n")
    
    def history_up(self, event):
        if self.command_history and self.history_index > 0:
            self.history_index -= 1
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.command_history[self.history_index])
    
    def history_down(self, event):
        if self.command_history:
            if self.history_index < len(self.command_history) - 1:
                self.history_index += 1
                self.command_entry.delete(0, tk.END)
                self.command_entry.insert(0, self.command_history[self.history_index])
            elif self.history_index == len(self.command_history) - 1:
                self.history_index = len(self.command_history)
                self.command_entry.delete(0, tk.END)
    
    # --- 新增: 按鈕事件處理 ---
    def conda_deactivate(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write('conda deactivate\n')
                self.process.stdin.flush()
            except Exception as e:
                self.append_output(f"\n執行 conda deactivate 時出錯: {str(e)}\n")
                self.restart_cmd_process()

    def conda_activate_base(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write('conda activate base\n')
                self.process.stdin.flush()
            except Exception as e:
                self.append_output(f"\n執行 conda activate base 時出錯: {str(e)}\n")
                self.restart_cmd_process()

    def on_closing(self):
        self.is_running = False
        try:
            if self.process and self.process.poll() is None:
                # 結束整個進程組，避免 conda 之類的進程殘留
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], check=False)
        except Exception as e:
            print(f"關閉進程時出錯: {e}")
        finally:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = CMDEmulator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
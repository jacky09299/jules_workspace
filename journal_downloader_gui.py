
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import json
import os

class JournalDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("期刊下載器")
        self.root.geometry("600x400")

        self.config_file = 'config.json'
        self.journals = []
        self.load_config()

        self.create_widgets()
        self.populate_journal_list()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Journal list frame
        list_frame = ttk.LabelFrame(main_frame, text="期刊列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.journal_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.journal_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.journal_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.journal_listbox.config(yscrollcommand=scrollbar.set)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.add_button = ttk.Button(button_frame, text="新增期刊", command=self.add_journal)
        self.add_button.pack(side=tk.LEFT, padx=5)

        self.edit_button = ttk.Button(button_frame, text="編輯設定", command=self.edit_journal)
        self.edit_button.pack(side=tk.LEFT, padx=5)

        self.remove_button = ttk.Button(button_frame, text="移除期刊", command=self.remove_journal)
        self.remove_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(button_frame, text="儲存設定", command=self.save_config)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Action frame
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)

        self.download_button = ttk.Button(action_frame, text="開始下載選定項目", command=self.start_download)
        self.download_button.pack(side=tk.RIGHT, padx=5)

    def populate_journal_list(self):
        self.journal_listbox.delete(0, tk.END)
        for journal in self.journals:
            status = "✓" if journal.get('enabled', False) else "✗"
            self.journal_listbox.insert(tk.END, f"[{status}] {journal['name']}")

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.journals = json.load(f)
        else:
            self.journals = []

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.journals, f, indent=4, ensure_ascii=False)
        messagebox.showinfo("成功", "設定已成功儲存！")

    def add_journal(self):
        # Placeholder for add journal dialog
        messagebox.showinfo("提示", "此功能待實現。")

    def edit_journal(self):
        # Placeholder for edit journal dialog
        messagebox.showinfo("提示", "此功能待實現。")

    def remove_journal(self):
        # Placeholder for remove journal logic
        messagebox.showinfo("提示", "此功能待實現。")

    def start_download(self):
        # Placeholder for download logic
        messagebox.showinfo("提示", "此功能待實現。")


if __name__ == "__main__":
    root = tk.Tk()
    app = JournalDownloaderApp(root)
    root.mainloop()

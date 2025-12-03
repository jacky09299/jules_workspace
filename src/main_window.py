import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
from src.logic import MarkItDownConverter

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("MarkItDown GUI")
        self.root.geometry("800x700")

        self.converter = MarkItDownConverter()
        self.file_list = []

        self._create_widgets()

    def _create_widgets(self):
        # --- File Selection Section ---
        input_frame = ttk.LabelFrame(self.root, text="Input Files", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)

        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="Add Files", command=self.add_files).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Add Folder", command=self.add_folder).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear List", command=self.clear_list).pack(side="left", padx=5)

        self.file_listbox = tk.Listbox(input_frame, height=5, selectmode=tk.EXTENDED)
        self.file_listbox.pack(fill="x", padx=5, pady=5)
        scrollbar = ttk.Scrollbar(self.file_listbox, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Configuration Section ---
        config_frame = ttk.LabelFrame(self.root, text="Configuration (Optional)", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)

        # Azure Document Intelligence
        ttk.Label(config_frame, text="Azure Doc Intel Endpoint:").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.az_endpoint_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.az_endpoint_var, width=50).grid(row=0, column=1, sticky="w", padx=5, pady=2)

        # OpenAI Configuration
        ttk.Separator(config_frame, orient="horizontal").grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(config_frame, text="OpenAI API Key:").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.openai_key_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.openai_key_var, show="*", width=50).grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(config_frame, text="OpenAI Model:").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.openai_model_var = tk.StringVar(value="gpt-4o")
        ttk.Entry(config_frame, textvariable=self.openai_model_var, width=20).grid(row=3, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(config_frame, text="LLM Prompt:").grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self.openai_prompt_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.openai_prompt_var, width=50).grid(row=4, column=1, sticky="w", padx=5, pady=2)

        # --- Output Section ---
        output_frame = ttk.LabelFrame(self.root, text="Output Options", padding=10)
        output_frame.pack(fill="x", padx=10, pady=5)

        self.save_source_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(output_frame, text="Save to source directory (same filename, .md extension)",
                        variable=self.save_source_var, command=self.toggle_output_dir).pack(anchor="w", padx=5)

        self.custom_out_frame = ttk.Frame(output_frame)
        self.custom_out_frame.pack(fill="x", padx=20, pady=2)

        ttk.Label(self.custom_out_frame, text="Custom Output Directory:").pack(side="left")
        self.output_dir_var = tk.StringVar()
        self.output_dir_entry = ttk.Entry(self.custom_out_frame, textvariable=self.output_dir_var, width=40, state="disabled")
        self.output_dir_entry.pack(side="left", padx=5)
        self.browse_out_btn = ttk.Button(self.custom_out_frame, text="Browse...", command=self.browse_output_dir, state="disabled")
        self.browse_out_btn.pack(side="left")

        # --- Process Control ---
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(fill="x", padx=10)

        self.convert_btn = ttk.Button(control_frame, text="Convert All", command=self.start_conversion)
        self.convert_btn.pack(fill="x", pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=5)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.status_var).pack(anchor="w")

        # --- Preview Section ---
        preview_frame = ttk.LabelFrame(self.root, text="Preview (Last Conversion)", padding=10)
        preview_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.preview_text = tk.Text(preview_frame, wrap="word", height=10)
        self.preview_text.pack(fill="both", expand=True, side="left")

        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_text.yview)
        preview_scroll.pack(side="right", fill="y")
        self.preview_text.configure(yscrollcommand=preview_scroll.set)

    def toggle_output_dir(self):
        if self.save_source_var.get():
            self.output_dir_entry.configure(state="disabled")
            self.browse_out_btn.configure(state="disabled")
        else:
            self.output_dir_entry.configure(state="normal")
            self.browse_out_btn.configure(state="normal")

    def browse_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def add_files(self):
        files = filedialog.askopenfilenames(title="Select Files")
        for f in files:
            if f not in self.file_list:
                self.file_list.append(f)
                self.file_listbox.insert(tk.END, f)

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    full_path = os.path.join(root, file)
                    if full_path not in self.file_list:
                        self.file_list.append(full_path)
                        self.file_listbox.insert(tk.END, full_path)

    def clear_list(self):
        self.file_list = []
        self.file_listbox.delete(0, tk.END)

    def start_conversion(self):
        if not self.file_list:
            messagebox.showwarning("No Files", "Please add files to convert.")
            return

        if not self.save_source_var.get() and not self.output_dir_var.get():
            messagebox.showwarning("Output Directory", "Please select an output directory or check 'Save to source directory'.")
            return

        self.convert_btn.configure(state="disabled")
        self.progress_var.set(0)
        self.status_var.set("Starting conversion...")
        self.preview_text.delete(1.0, tk.END)

        # Collect config
        doc_intel = self.az_endpoint_var.get().strip() or None
        llm_config = {
            "api_key": self.openai_key_var.get().strip(),
            "model": self.openai_model_var.get().strip(),
            "prompt": self.openai_prompt_var.get().strip()
        }
        if not llm_config["api_key"]:
            llm_config = None

        # Run in thread
        threading.Thread(target=self._run_conversion, args=(doc_intel, llm_config), daemon=True).start()

    def _run_conversion(self, doc_intel, llm_config):
        total_files = len(self.file_list)
        success_count = 0
        errors = []

        for i, file_path in enumerate(self.file_list):
            self.status_var.set(f"Converting ({i+1}/{total_files}): {os.path.basename(file_path)}")
            try:
                content = self.converter.convert_file(file_path, doc_intel, llm_config)

                # Determine output path
                if self.save_source_var.get():
                    out_dir = os.path.dirname(file_path)
                else:
                    out_dir = self.output_dir_var.get()

                base_name = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(out_dir, f"{base_name}.md")

                self.converter.save_output(content, out_path)

                # Update preview (thread-safeish for simple tk)
                self.root.after(0, self._update_preview, content)
                success_count += 1
            except Exception as e:
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")

            # Update progress
            progress = ((i + 1) / total_files) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p), progress)

        self.root.after(0, self._finish_conversion, success_count, total_files, errors)

    def _update_preview(self, content):
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(tk.END, content)

    def _finish_conversion(self, success_count, total_files, errors):
        self.convert_btn.configure(state="normal")
        self.status_var.set(f"Completed: {success_count}/{total_files} files converted successfully.")

        if errors:
            error_msg = "\n".join(errors)
            messagebox.showerror("Conversion Errors", f"Some files failed to convert:\n{error_msg}")
        else:
            messagebox.showinfo("Success", "All files converted successfully!")

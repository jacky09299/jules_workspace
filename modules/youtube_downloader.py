
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
from pytube import YouTube
import threading

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class YoutubeDownloaderModule(Module):
    def __init__(self, master, shared_state, module_name="Youtube Downloader", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.url_entry = None
        self.status_label = None
        self.create_ui()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        # URL Entry
        url_frame = ttk.Frame(content_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        url_label = ttk.Label(url_frame, text="YouTube URL:")
        url_label.pack(side=tk.LEFT, padx=(0, 5))

        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Download Button
        download_button = ttk.Button(content_frame, text="Download MP4", command=self.start_download_thread)
        download_button.pack(pady=10)

        # Status Label
        self.status_label = ttk.Label(content_frame, text="Status: Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=5)
        
        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def start_download_thread(self):
        # Run the download in a separate thread to keep the GUI responsive
        download_thread = threading.Thread(target=self.download_video)
        download_thread.daemon = True
        download_thread.start()

    def download_video(self):
        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.", parent=self.frame)
            return

        self.update_status("Status: Downloading...")
        
        try:
            yt = YouTube(url, on_progress_callback=self.on_progress)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
            
            if not stream:
                self.update_status("Status: No MP4 stream found.")
                messagebox.showerror("Error", "No suitable MP4 stream found for this video.", parent=self.frame)
                return

            save_path = filedialog.asksaveasfilename(
                defaultextension=".mp4",
                filetypes=[("MP4 files", "*.mp4")],
                initialfile=yt.title + ".mp4",
                parent=self.frame
            )

            if save_path:
                self.update_status(f"Status: Downloading '{yt.title}'...")
                stream.download(output_path=os.path.dirname(save_path), filename=os.path.basename(save_path))
                self.update_status(f"Status: Download complete! Saved to {save_path}")
                self.shared_state.log(f"Downloaded video '{yt.title}' to {save_path}", level=logging.INFO)
                messagebox.showinfo("Success", f"Download complete!
Saved to: {save_path}", parent=self.frame)
            else:
                self.update_status("Status: Download cancelled.")

        except Exception as e:
            self.update_status(f"Status: Error - {e}")
            messagebox.showerror("Error", f"An error occurred: {e}", parent=self.frame)
            self.shared_state.log(f"Error downloading from {url}: {e}", level=logging.ERROR)

    def on_progress(self, stream, chunk, bytes_remaining):
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = (bytes_downloaded / total_size) * 100
        self.update_status(f"Status: Downloading... {percentage:.2f}%")

    def update_status(self, message):
        # Ensure UI updates are done on the main thread
        self.master.after(0, lambda: self.status_label.config(text=message))

    def on_destroy(self):
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
import threading
import subprocess
import sys

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class YoutubeDownloaderModule(Module):
    def __init__(self, master, shared_state, module_name="Youtube Downloader", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)

        self.url_entry = None
        self.status_label = None
        self.progress_bar = None
        self.download_method = None
        self.create_ui()
        self.check_dependencies()

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

        # Download Method Selection
        method_frame = ttk.Frame(content_frame)
        method_frame.pack(fill=tk.X, pady=5)
        
        method_label = ttk.Label(method_frame, text="Download Method:")
        method_label.pack(side=tk.LEFT, padx=(0, 5))

        self.download_method = ttk.Combobox(method_frame, values=["Auto", "pytube", "yt-dlp"], 
                                          state="readonly", width=15)
        self.download_method.set("Auto")
        self.download_method.pack(side=tk.LEFT, padx=(0, 5))

        # Format Selection
        format_frame = ttk.Frame(content_frame)
        format_frame.pack(fill=tk.X, pady=5)
        
        format_label = ttk.Label(format_frame, text="Format:")
        format_label.pack(side=tk.LEFT, padx=(0, 5))

        self.format_var = tk.StringVar(value="mp4")
        format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, 
                                   values=["mp4", "mp3", "best"], state="readonly", width=15)
        format_combo.pack(side=tk.LEFT, padx=(0, 5))

        # Quality Selection
        quality_label = ttk.Label(format_frame, text="Quality:")
        quality_label.pack(side=tk.LEFT, padx=(10, 5))

        self.quality_var = tk.StringVar(value="best")
        quality_combo = ttk.Combobox(format_frame, textvariable=self.quality_var,
                                   values=["best", "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p", "144p"], state="readonly", width=15)
        quality_combo.pack(side=tk.LEFT)

        # Download Button
        download_button = ttk.Button(content_frame, text="Download", command=self.start_download_thread)
        download_button.pack(pady=10)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(content_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Status Label
        self.status_label = ttk.Label(content_frame, text="Status: Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=5)
        
        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def check_dependencies(self):
        """Check which download libraries are available"""
        try:
            import pytube
            self.pytube_available = True
        except ImportError:
            self.pytube_available = False

        # Check if yt-dlp is available
        try:
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
            self.ytdlp_available = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            self.ytdlp_available = False

        # Update status based on available methods
        if not self.pytube_available and not self.ytdlp_available:
            self.update_status("Status: No download libraries available. Install pytube or yt-dlp.")
        elif self.pytube_available and not self.ytdlp_available:
            self.update_status("Status: Ready (pytube only)")
        elif not self.pytube_available and self.ytdlp_available:
            self.update_status("Status: Ready (yt-dlp only)")
        else:
            self.update_status("Status: Ready (both pytube and yt-dlp available)")

    def start_download_thread(self):
        """Run the download in a separate thread to keep the GUI responsive"""
        download_thread = threading.Thread(target=self.download_video)
        download_thread.daemon = True
        download_thread.start()

    def download_video(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.", parent=self.frame)
            return

        self.update_status("Status: Downloading...")
        self.progress_bar['value'] = 0

        method = self.download_method.get()
        
        # Determine which method to use
        if method == "Auto":
            if self.ytdlp_available:
                success = self.download_with_ytdlp(url)
                if not success and self.pytube_available:
                    self.update_status("Status: yt-dlp failed, trying pytube...")
                    success = self.download_with_pytube(url)
            elif self.pytube_available:
                success = self.download_with_pytube(url)
            else:
                messagebox.showerror("Error", "No download libraries available.", parent=self.frame)
                return
        elif method == "pytube":
            if self.pytube_available:
                success = self.download_with_pytube(url)
            else:
                messagebox.showerror("Error", "pytube is not available.", parent=self.frame)
                return
        elif method == "yt-dlp":
            if self.ytdlp_available:
                success = self.download_with_ytdlp(url)
            else:
                messagebox.showerror("Error", "yt-dlp is not available.", parent=self.frame)
                return

    def download_with_pytube(self, url):
        """Download using pytube library"""
        try:
            from pytube import YouTube
            
            yt = YouTube(url, on_progress_callback=self.on_progress_pytube)
            
            format_choice = self.format_var.get()
            quality = self.quality_var.get()
            
            if format_choice == "mp3":
                stream = yt.streams.filter(only_audio=True).first()
                default_ext = ".mp3"
            else:
                if quality == "best":
                    stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                else:
                    stream = yt.streams.filter(progressive=True, file_extension='mp4', res=quality).first()
                    if not stream:
                        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                default_ext = ".mp4"
            
            if not stream:
                self.update_status("Status: No suitable stream found.")
                messagebox.showerror("Error", "No suitable stream found for this video.", parent=self.frame)
                return False

            # Clean the title for filename
            safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_')).strip()
            
            save_path = filedialog.asksaveasfilename(
                defaultextension=default_ext,
                filetypes=[("Video files", "*.mp4"), ("Audio files", "*.mp3"), ("All files", "*.*")],
                initialfile=safe_title + default_ext,
                parent=self.frame
            )

            if save_path:
                self.update_status(f"Status: Downloading '{yt.title}'...")
                download_path = stream.download(output_path=os.path.dirname(save_path), 
                                              filename=os.path.basename(save_path))
                
                # Convert to mp3 if needed
                if format_choice == "mp3" and download_path.endswith('.mp4'):
                    self.convert_to_mp3(download_path, save_path)
                
                self.update_status(f"Status: Download complete! Saved to {save_path}")
                self.shared_state.log(f"Downloaded video '{yt.title}' to {save_path}", level=logging.INFO)
                messagebox.showinfo("Success", f"Download complete!\nSaved to: {save_path}", parent=self.frame)
                return True
            else:
                self.update_status("Status: Download cancelled.")
                return False

        except Exception as e:
            self.update_status(f"Status: pytube error - {e}")
            self.shared_state.log(f"pytube error downloading from {url}: {e}", level=logging.ERROR)
            return False

    def download_with_ytdlp(self, url):
        """Download using yt-dlp"""
        try:
            format_choice = self.format_var.get()
            quality = self.quality_var.get()
            
            # Get video info first
            info_cmd = ['yt-dlp', '--get-title', '--get-filename', url]
            result = subprocess.run(info_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.update_status("Status: Failed to get video info")
                return False
            
            lines = result.stdout.strip().split('\n')
            title = lines[0] if lines else "video"
            
            # Clean the title for filename
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            
            if format_choice == "mp3":
                default_ext = ".mp3"
                format_selector = "bestaudio/best"
            else:
                default_ext = ".mp4"
                if quality == "best":
                    format_selector = "best[ext=mp4]/best"
                elif quality.endswith("p") and quality[:-1].isdigit():
                    # e.g. 2160p -> height<=2160
                    format_selector = f"bestvideo[height<={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality[:-1]}][ext=mp4]/best"
                else:
                    format_selector = "best[ext=mp4]/best"
            
            save_path = filedialog.asksaveasfilename(
                defaultextension=default_ext,
                filetypes=[("Video files", "*.mp4"), ("Audio files", "*.mp3"), ("All files", "*.*")],
                initialfile=safe_title + default_ext,
                parent=self.frame
            )

            if save_path:
                self.update_status(f"Status: Downloading '{title}'...")
                
                cmd = ['yt-dlp', '-f', format_selector, '-o', save_path, url]
                
                if format_choice == "mp3":
                    cmd.extend(['--extract-audio', '--audio-format', 'mp3'])
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                         text=True, universal_newlines=True)
                
                # Monitor progress
                for line in iter(process.stdout.readline, ''):
                    if '[download]' in line and '%' in line:
                        try:
                            # Extract percentage from yt-dlp output
                            parts = line.split()
                            for part in parts:
                                if '%' in part:
                                    percentage = float(part.replace('%', ''))
                                    self.master.after(0, lambda p=percentage: self.progress_bar.config(value=p))
                                    break
                        except:
                            pass
                
                process.wait()
                
                if process.returncode == 0:
                    self.update_status(f"Status: Download complete! Saved to {save_path}")
                    self.shared_state.log(f"Downloaded video '{title}' to {save_path}", level=logging.INFO)
                    messagebox.showinfo("Success", f"Download complete!\nSaved to: {save_path}", parent=self.frame)
                    return True
                else:
                    error_output = process.stderr.read()
                    self.update_status(f"Status: yt-dlp error")
                    self.shared_state.log(f"yt-dlp error: {error_output}", level=logging.ERROR)
                    return False
            else:
                self.update_status("Status: Download cancelled.")
                return False

        except Exception as e:
            self.update_status(f"Status: yt-dlp error - {e}")
            self.shared_state.log(f"yt-dlp error downloading from {url}: {e}", level=logging.ERROR)
            return False

    def convert_to_mp3(self, input_path, output_path):
        """Convert video file to mp3 using ffmpeg if available"""
        try:
            subprocess.run(['ffmpeg', '-i', input_path, '-acodec', 'mp3', output_path], 
                         check=True, capture_output=True)
            os.remove(input_path)  # Remove the original video file
        except (subprocess.SubprocessError, FileNotFoundError):
            # If ffmpeg is not available, just rename the file
            os.rename(input_path, output_path)

    def on_progress_pytube(self, stream, chunk, bytes_remaining):
        """Progress callback for pytube"""
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage = (bytes_downloaded / total_size) * 100
        self.master.after(0, lambda: self.progress_bar.config(value=percentage))
        self.update_status(f"Status: Downloading... {percentage:.1f}%")

    def update_status(self, message):
        """Ensure UI updates are done on the main thread"""
        self.master.after(0, lambda: self.status_label.config(text=message))

    def on_destroy(self):
        """Clean up when module is destroyed"""
        super().on_destroy()
        self.shared_state.log(f"{self.module_name} instance destroyed.")
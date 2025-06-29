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
        self.batch_url_text = None
        self.status_label = None
        self.progress_bar = None
        self.download_method = None
        self.download_dir = None  # 新增：下載資料夾
        self.create_ui()
        self.check_dependencies()

    def create_ui(self):
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        # URL Entry
        url_frame = ttk.Frame(content_frame)
        url_frame.pack(fill=tk.X, pady=5)
        
        url_label = ttk.Label(url_frame, text="YouTube playlist URL:")
        url_label.pack(side=tk.LEFT, padx=(0, 5))

        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # 批次下載多行輸入框 + 滾動條 + 載入txt按鈕
        batch_frame = ttk.Frame(content_frame)
        batch_frame.pack(fill=tk.BOTH, pady=5)
        batch_label = ttk.Label(batch_frame, text="YouTube URLs (one per line):")
        batch_label.pack(anchor=tk.W)
        batch_text_frame = ttk.Frame(batch_frame)
        batch_text_frame.pack(fill=tk.BOTH, expand=True)
        self.batch_url_text = tk.Text(batch_text_frame, height=4)
        self.batch_url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        batch_scrollbar = ttk.Scrollbar(batch_text_frame, orient=tk.VERTICAL, command=self.batch_url_text.yview)
        batch_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_url_text.config(yscrollcommand=batch_scrollbar.set)
        # 載入txt按鈕
        load_txt_btn = ttk.Button(batch_frame, text="Load .txt", command=self.load_batch_txt)
        load_txt_btn.pack(anchor=tk.E, pady=(2, 0))

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

        # Download Button（合併單一與批次下載）
        download_button = ttk.Button(content_frame, text="Download", command=self.start_combined_download_thread)
        download_button.pack(pady=5)

        # 播放清單下載按鈕
        playlist_download_button = ttk.Button(content_frame, text="Download Playlist", command=self.start_playlist_download_thread)
        playlist_download_button.pack(pady=5)

        # 播放清單曲目選擇輸入框
        playlist_range_frame = ttk.Frame(content_frame)
        playlist_range_frame.pack(fill=tk.X, pady=(0, 5))
        playlist_range_label = ttk.Label(playlist_range_frame, text="Playlist Items (e.g. 2-3,5,7,8,10-15):")
        playlist_range_label.pack(side=tk.LEFT, padx=(0, 5))
        self.playlist_range_var = tk.StringVar()
        playlist_range_entry = ttk.Entry(playlist_range_frame, textvariable=self.playlist_range_var)
        playlist_range_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(content_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Status Label
        self.status_label = ttk.Label(content_frame, text="Status: Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=5)

        # 資料夾選擇
        folder_frame = ttk.Frame(self.frame)
        folder_frame.pack(fill=tk.X, pady=5)
        folder_label = ttk.Label(folder_frame, text="Download Folder:")
        folder_label.pack(side=tk.LEFT, padx=(0, 5))
        self.folder_path_var = tk.StringVar(value="")
        folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_path_var, state="readonly")
        folder_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        folder_btn = ttk.Button(folder_frame, text="Select...", command=self.select_download_folder)
        folder_btn.pack(side=tk.LEFT, padx=(5, 0))

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)

    def select_download_folder(self):
        folder = filedialog.askdirectory(parent=self.frame)
        if folder:
            self.download_dir = folder
            self.folder_path_var.set(folder)

    def load_batch_txt(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self.frame
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.batch_url_text.delete("1.0", tk.END)
                self.batch_url_text.insert(tk.END, content)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load txt file: {e}", parent=self.frame)

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

    def start_combined_download_thread(self):
        """合併單一與批次下載：自動判斷要下載一個還是多個網址"""
        thread = threading.Thread(target=self.combined_download)
        thread.daemon = True
        thread.start()

    def combined_download(self):
        # 取得單一網址與批次網址
        url = self.url_entry.get().strip()
        batch_urls = self.batch_url_text.get("1.0", tk.END).strip().splitlines()
        urls = []
        if url:
            urls.append(url)
        urls += [u.strip() for u in batch_urls if u.strip()]
        # 去除重複
        urls = list(dict.fromkeys(urls))
        if not urls:
            messagebox.showerror("Error", "Please enter at least one YouTube URL.", parent=self.frame)
            return
        if not self.download_dir:
            messagebox.showerror("Error", "Please select a download folder.", parent=self.frame)
            return

        total = len(urls)
        for idx, u in enumerate(urls, 1):
            self.update_status(f"Status: Downloading ({idx}/{total})...")
            self.progress_bar['value'] = 0
            method = self.download_method.get()
            success = False
            if method == "Auto":
                if self.ytdlp_available:
                    success = self.download_with_ytdlp(u)
                    if not success and self.pytube_available:
                        self.update_status("Status: yt-dlp failed, trying pytube...")
                        success = self.download_with_pytube(u)
                elif self.pytube_available:
                    success = self.download_with_pytube(u)
                else:
                    messagebox.showerror("Error", "No download libraries available.", parent=self.frame)
                    return
            elif method == "pytube":
                if self.pytube_available:
                    success = self.download_with_pytube(u)
                else:
                    messagebox.showerror("Error", "pytube is not available.", parent=self.frame)
                    return
            elif method == "yt-dlp":
                if self.ytdlp_available:
                    success = self.download_with_ytdlp(u)
                else:
                    messagebox.showerror("Error", "yt-dlp is not available.", parent=self.frame)
                    return
            # 若用戶取消或失敗，繼續下一個
        self.update_status("Status: Download finished.")

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
                    # 先嘗試用戶指定畫質
                    stream = yt.streams.filter(progressive=True, file_extension='mp4', res=quality).first()
                    if not stream:
                        # 若沒有，選該影片最高畫質
                        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
                default_ext = ".mp4"
            
            if not stream:
                self.update_status("Status: No suitable stream found.")
                messagebox.showerror("Error", "No suitable stream found for this video.", parent=self.frame)
                return False

            # Clean the title for filename
            safe_title = "".join(c for c in yt.title if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = safe_title + default_ext
            save_path = os.path.join(self.download_dir, filename)

            self.update_status(f"Status: Downloading '{yt.title}'...")
            download_path = stream.download(output_path=self.download_dir, filename=filename)
            
            # Convert to mp3 if needed
            if format_choice == "mp3" and download_path.endswith('.mp4'):
                self.convert_to_mp3(download_path, save_path)
            
            self.update_status(f"Status: Download complete! Saved to {save_path}")
            self.shared_state.log(f"Downloaded video '{yt.title}' to {save_path}", level=logging.INFO)
            # 不再彈出成功訊息框
            return True
        except Exception as e:
            self.update_status(f"Status: pytube error - {e}")
            self.shared_state.log(f"pytube error downloading from {url}: {e}", level=logging.ERROR)
            messagebox.showerror("Error", f"pytube error: {e}", parent=self.frame)
            return False

    def download_with_ytdlp(self, url):
        """Download using yt-dlp"""
        try:
            format_choice = self.format_var.get()
            quality = self.quality_var.get()
            
            # Get video info first
            info_cmd = ['yt-dlp', '--get-title', url]
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
                    format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif quality.endswith("p") and quality[:-1].isdigit():
                    # 先嘗試用戶指定畫質，若沒有則 fallback
                    # yt-dlp格式語法：bestvideo[height=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best
                    format_selector = (
                        f"bestvideo[height={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        f"best[ext=mp4]/best"
                    )
                else:
                    format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            
            filename = safe_title + default_ext
            save_path = os.path.join(self.download_dir, filename)

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
                # 不再彈出成功訊息框
                return True
            else:
                error_output = process.stderr.read()
                self.update_status(f"Status: yt-dlp error")
                self.shared_state.log(f"yt-dlp error: {error_output}", level=logging.ERROR)
                messagebox.showerror("Error", f"yt-dlp error: {error_output}", parent=self.frame)
                return False
        except Exception as e:
            self.update_status(f"Status: yt-dlp error - {e}")
            self.shared_state.log(f"yt-dlp error downloading from {url}: {e}", level=logging.ERROR)
            messagebox.showerror("Error", f"yt-dlp error: {e}", parent=self.frame)
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

    def start_playlist_download_thread(self):
        playlist_thread = threading.Thread(target=self.download_playlist)
        playlist_thread.daemon = True
        playlist_thread.start()

    def download_playlist(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube playlist URL.", parent=self.frame)
            return
        if not self.download_dir:
            messagebox.showerror("Error", "Please select a download folder.", parent=self.frame)
            return

        self.update_status("Status: Downloading playlist...")
        self.progress_bar['value'] = 0
        method = self.download_method.get()
        success = False
        if method == "Auto":
            if self.ytdlp_available:
                success = self.download_playlist_with_ytdlp(url)
                if not success and self.pytube_available:
                    self.update_status("Status: yt-dlp failed, trying pytube...")
                    success = self.download_playlist_with_pytube(url)
            elif self.pytube_available:
                success = self.download_playlist_with_pytube(url)
            else:
                messagebox.showerror("Error", "No download libraries available.", parent=self.frame)
                return
        elif method == "pytube":
            if self.pytube_available:
                success = self.download_playlist_with_pytube(url)
            else:
                messagebox.showerror("Error", "pytube is not available.", parent=self.frame)
                return
        elif method == "yt-dlp":
            if self.ytdlp_available:
                success = self.download_playlist_with_ytdlp(url)
            else:
                messagebox.showerror("Error", "yt-dlp is not available.", parent=self.frame)
                return
        if success:
            self.update_status("Status: Playlist download finished。")

    def parse_playlist_range(self, range_str, total):
        """解析用戶輸入的曲目範圍，回傳要下載的index集合（0-based）"""
        result = set()
        if not range_str.strip():
            return set(range(total))  # 空字串代表全部
        for part in range_str.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-')
                    start = int(start) - 1
                    end = int(end)
                    if start < 0: start = 0
                    if end > total: end = total
                    result.update(range(start, end))
                except:
                    continue
            else:
                try:
                    idx = int(part) - 1
                    if 0 <= idx < total:
                        result.add(idx)
                except:
                    continue
        return sorted(result)

    def download_playlist_with_pytube(self, url):
        """使用 pytube 下載整個播放清單（支援曲目選擇）"""
        try:
            from pytube import Playlist, YouTube
            pl = Playlist(url)
            videos = list(pl.video_urls)
            if not videos:
                self.update_status("Status: No videos found in playlist.")
                messagebox.showerror("Error", "No videos found in playlist.", parent=self.frame)
                return False
            total = len(videos)
            # 解析用戶輸入的曲目範圍
            selected_indexes = self.parse_playlist_range(self.playlist_range_var.get(), total)
            if not selected_indexes:
                self.update_status("Status: No valid playlist items selected.")
                messagebox.showerror("Error", "No valid playlist items selected.", parent=self.frame)
                return False
            for idx in selected_indexes:
                vurl = videos[idx]
                self.update_status(f"Status: Playlist downloading ({idx+1}/{total})...")
                self.download_with_pytube(vurl)
            self.update_status("Status: Playlist download complete!")
            self.shared_state.log(f"Downloaded playlist to {self.download_dir}", level=logging.INFO)
            return True
        except Exception as e:
            self.update_status(f"Status: pytube error - {e}")
            self.shared_state.log(f"pytube playlist error: {e}", level=logging.ERROR)
            messagebox.showerror("Error", f"pytube error: {e}", parent=self.frame)
            return False

    def download_playlist_with_ytdlp(self, url):
        """使用 yt-dlp 下載整個播放清單（支援曲目選擇）"""
        try:
            format_choice = self.format_var.get()
            quality = self.quality_var.get()
            if format_choice == "mp3":
                default_ext = ".mp3"
                format_selector = "bestaudio/best"
            else:
                default_ext = ".mp4"
                if quality == "best":
                    format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                elif quality.endswith("p") and quality[:-1].isdigit():
                    format_selector = (
                        f"bestvideo[height={quality[:-1]}][ext=mp4]+bestaudio[ext=m4a]/"
                        f"bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
                        f"best[ext=mp4]/best"
                    )
                else:
                    format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

            # 解析用戶輸入的曲目範圍
            # 先取得播放清單長度
            info_cmd = ['yt-dlp', '--flat-playlist', '--print', 'url', url]
            result = subprocess.run(info_cmd, capture_output=True, text=True)
            video_urls = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            total = len(video_urls)
            selected_indexes = self.parse_playlist_range(self.playlist_range_var.get(), total)
            if not selected_indexes:
                self.update_status("Status: No valid playlist items selected.")
                messagebox.showerror("Error", "No valid playlist items selected.", parent=self.frame)
                return False

            # 產生 --playlist-items 參數
            # yt-dlp 的 --playlist-items 是 1-based 且可用 2-3,5,7,8,10-15 格式
            playlist_items_arg = ",".join(
                str(idx + 1) if isinstance(idx, int) else idx for idx in selected_indexes
            )
            if not playlist_items_arg:
                playlist_items_arg = "1-" + str(total)

            cmd = [
                'yt-dlp', '-f', format_selector,
                '-o', os.path.join(self.download_dir, '%(title)s.%(ext)s'),
                '--playlist-items', playlist_items_arg,
                url
            ]
            if format_choice == "mp3":
                cmd.extend(['--extract-audio', '--audio-format', 'mp3'])

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True, universal_newlines=True)
            for line in iter(process.stdout.readline, ''):
                if '[download]' in line and '%' in line:
                    try:
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
                self.update_status("Status: Playlist download complete!")
                self.shared_state.log(f"Downloaded playlist to {self.download_dir}", level=logging.INFO)
                return True
            else:
                error_output = process.stderr.read()
                self.update_status(f"Status: yt-dlp error")
                self.shared_state.log(f"yt-dlp playlist error: {error_output}", level=logging.ERROR)
                messagebox.showerror("Error", f"yt-dlp error: {error_output}", parent=self.frame)
                return False
        except Exception as e:
            self.update_status(f"Status: yt-dlp error - {e}")
            self.shared_state.log(f"yt-dlp playlist error: {e}", level=logging.ERROR)
            messagebox.showerror("Error", f"yt-dlp error: {e}", parent=self.frame)
            return False
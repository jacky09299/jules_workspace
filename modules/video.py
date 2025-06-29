import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from main import Module # Assuming main.py is in parent directory
import logging # For logging level constants
import os # For os.path.basename
import json
import random
from datetime import datetime
import time

# 新增 OpenCV 與 PIL
import cv2
from PIL import Image, ImageTk
# 新增 moviepy 與 pygame
from moviepy.editor import VideoFileClip
import pygame
import tempfile

class PlaylistOrderWindow:
    def __init__(self, parent, playlist, callback):
        self.parent = parent
        self.playlist = playlist.copy()
        self.callback = callback
        self.selected_index = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("調整播放順序")
        self.window.geometry("500x400")
        self.window.transient(parent)
        self.window.grab_set()
        
        self.create_ui()
        
    def create_ui(self):
        # 列表框架
        list_frame = ttk.Frame(self.window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ttk.Label(list_frame, text="播放清單順序 (點選檔案後使用下方按鈕調整位置):").pack(anchor=tk.W)
        
        # 滾動列表
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        
        self.listbox = tk.Listbox(list_container, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        
        # 控制按鈕
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        
        ttk.Button(control_frame, text="上移", command=self.move_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="下移", command=self.move_down).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="移到頂部", command=self.move_to_top).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="移到底部", command=self.move_to_bottom).pack(side=tk.LEFT, padx=5)
        
        # 底部按鈕
        bottom_frame = ttk.Frame(self.window)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(bottom_frame, text="確定", command=self.save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="取消", command=self.window.destroy).pack(side=tk.RIGHT)
        
        self.update_listbox()
        
    def update_listbox(self):
        self.listbox.delete(0, tk.END)
        for i, filepath in enumerate(self.playlist):
            filename = os.path.basename(filepath)
            self.listbox.insert(tk.END, f"{i+1:2d}. {filename}")
            
    def on_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            self.selected_index = selection[0]
            
    def move_up(self):
        if self.selected_index is not None and self.selected_index > 0:
            # 交換位置
            self.playlist[self.selected_index], self.playlist[self.selected_index-1] = \
                self.playlist[self.selected_index-1], self.playlist[self.selected_index]
            self.selected_index -= 1
            self.update_listbox()
            self.listbox.selection_set(self.selected_index)
            
    def move_down(self):
        if self.selected_index is not None and self.selected_index < len(self.playlist) - 1:
            # 交換位置
            self.playlist[self.selected_index], self.playlist[self.selected_index+1] = \
                self.playlist[self.selected_index+1], self.playlist[self.selected_index]
            self.selected_index += 1
            self.update_listbox()
            self.listbox.selection_set(self.selected_index)
            
    def move_to_top(self):
        if self.selected_index is not None and self.selected_index > 0:
            item = self.playlist.pop(self.selected_index)
            self.playlist.insert(0, item)
            self.selected_index = 0
            self.update_listbox()
            self.listbox.selection_set(self.selected_index)
            
    def move_to_bottom(self):
        if self.selected_index is not None and self.selected_index < len(self.playlist) - 1:
            item = self.playlist.pop(self.selected_index)
            self.playlist.append(item)
            self.selected_index = len(self.playlist) - 1
            self.update_listbox()
            self.listbox.selection_set(self.selected_index)
            
    def save_and_close(self):
        self.callback(self.playlist)
        self.window.destroy()

class VideoModule(Module):
    def __init__(self, master, shared_state, module_name="Video", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.is_playing = False
        self.video_loaded = False
        self.video_filepath = ""
        self.cap = None  # OpenCV VideoCapture
        self.frame_image = None  # PIL ImageTk.PhotoImage
        self.after_id = None  # Tkinter after callback id
        
        # 播放清單相關
        self.playlist = []
        self.current_playlist_index = 0
        self.folder_path = ""
        self.playlist_json_path = ""
        self.play_mode = "single"  # "single", "folder_time", "folder_json", "folder_random"
        self.supported_formats = ('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v')

        self.audio_tempfile = None  # 暫存音訊檔案路徑
        self.audio_loaded = False
        self.pygame_initialized = False
        
        # 音訊播放控制變數
        self.audio_start_time = None  # 音訊開始播放的系統時間
        self.audio_pause_position = 0  # 暫停時的音訊位置 (秒)
        self.is_audio_paused = False  # 音訊是否處於暫停狀態

        self.folder_video_files = []  # 新增：記錄資料夾所有影片檔案

        self.create_ui()

    def create_ui(self):
        # Configure this module's main frame
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Create a content frame within self.frame for padding and organization
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)

        # Video display area
        self.video_area = tk.Frame(content_frame, bg="black", height=200)
        self.video_area.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        self.video_area.pack_propagate(False)

        # 用 Label 顯示影片畫面
        self.video_label = tk.Label(self.video_area, bg="black")
        self.video_label.pack(expand=True, fill=tk.BOTH)
        self.video_status_label = ttk.Label(self.video_area, text="請選擇影片檔案或資料夾", foreground="white", background="black")
        self.video_status_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 檔案選擇框架
        file_select_frame = ttk.LabelFrame(content_frame, text="檔案選擇")
        file_select_frame.pack(fill=tk.X, pady=(0,5))

        # 按鈕行
        button_row1 = ttk.Frame(file_select_frame)
        button_row1.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_row1, text="選擇單一檔案", command=self.load_single_video).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_row1, text="選擇資料夾", command=self.load_folder).pack(side=tk.LEFT, padx=5)

        # 播放模式選擇
        mode_frame = ttk.Frame(file_select_frame)
        mode_frame.pack(fill=tk.X, padx=5, pady=(0,5))

        ttk.Label(mode_frame, text="資料夾播放模式:").pack(side=tk.LEFT)

        self.mode_var = tk.StringVar(value="folder_time")
        ttk.Radiobutton(mode_frame, text="按建立時間", variable=self.mode_var, value="folder_time", command=self.on_mode_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="按JSON順序", variable=self.mode_var, value="folder_json", command=self.on_mode_changed).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="隨機播放", variable=self.mode_var, value="folder_random", command=self.on_mode_changed).pack(side=tk.LEFT, padx=5)

        # JSON順序調整按鈕
        self.order_button = ttk.Button(file_select_frame, text="調整播放順序", command=self.open_order_window, state=tk.DISABLED)
        self.order_button.pack(padx=5, pady=(0,5))

        # 播放資訊
        info_frame = ttk.LabelFrame(content_frame, text="播放資訊")
        info_frame.pack(fill=tk.X, pady=(0,5))

        self.info_label = ttk.Label(info_frame, text="未選擇檔案")
        self.info_label.pack(padx=5, pady=5, anchor=tk.W)

        # Controls frame
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill=tk.X, pady=(0,5))

        self.play_pause_button = ttk.Button(controls_frame, text="播放", command=self.toggle_play_pause, state=tk.DISABLED)
        self.play_pause_button.pack(side=tk.LEFT, padx=5)

        self.prev_button = ttk.Button(controls_frame, text="上一個", command=self.previous_video, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = ttk.Button(controls_frame, text="下一個", command=self.next_video, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=5)

        # === 新增：跳至影片按鈕 ===
        self.goto_button = ttk.Button(controls_frame, text="跳至影片", command=self.open_goto_window, state=tk.DISABLED)
        self.goto_button.pack(side=tk.LEFT, padx=5)

        # === 新增進度條 ===
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_scale = ttk.Scale(
            content_frame, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.progress_var, command=self.on_progress_drag
        )
        self.progress_scale.pack(fill=tk.X, padx=5, pady=(0, 5))
        self.progress_scale.bind("<Button-1>", self.on_progress_press)
        self.progress_scale.bind("<ButtonRelease-1>", self.on_progress_release)
        self.progress_dragging = False

        # === 新增音量條 ===
        volume_frame = ttk.Frame(content_frame)
        volume_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(volume_frame, text="音量:").pack(side=tk.LEFT)
        self.volume_var = tk.DoubleVar(value=100)
        self.volume_scale = ttk.Scale(
            volume_frame, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.volume_var, command=self.on_volume_changed
        )
        self.volume_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)
        self.shared_state.set(f"{self.module_name}_ready", True)

    def init_pygame(self):
        if not self.pygame_initialized:
            pygame.mixer.init()
            self.pygame_initialized = True

    def load_single_video(self):
        """選擇單一影片檔案"""
        filepath = filedialog.askopenfilename(
            title="選擇影片檔案",
            filetypes=(("影片檔案", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v"),
                       ("所有檔案", "*.*"))
        )
        if not filepath:
            return

        self.play_mode = "single"
        self.playlist = [filepath]
        self.current_playlist_index = 0
        self.folder_path = ""
        
        self.update_info_display()
        self.load_current_video()
        self.update_button_states()

    def load_folder(self):
        """選擇資料夾"""
        folder_path = filedialog.askdirectory(title="選擇包含影片的資料夾")
        if not folder_path:
            return

        self.folder_path = folder_path
        self.playlist_json_path = os.path.join(folder_path, "playlist.json")
        
        # 掃描資料夾中的影片檔案
        video_files = []
        try:
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(self.supported_formats):
                    video_files.append(os.path.join(folder_path, filename))
        except Exception as e:
            self.shared_state.log(f"掃描資料夾時發生錯誤: {e}", logging.ERROR)
            return

        if not video_files:
            messagebox.showwarning("警告", "選擇的資料夾中沒有找到支援的影片檔案")
            return

        # 依照建立時間排序
        video_files.sort(key=lambda x: os.path.getctime(x))

        self.folder_video_files = video_files  # 記錄所有影片檔案
        self.play_mode = self.mode_var.get()
        self.setup_playlist(self.folder_video_files)
        
        if self.playlist:
            self.current_playlist_index = 0
            self.update_info_display()
            self.load_current_video()
            self.update_button_states()

    def on_mode_changed(self):
        """切換播放模式時，重建播放清單，但不影響目前播放的影片"""
        if not self.folder_path or not self.folder_video_files:
            return
        new_mode = self.mode_var.get()
        prev_file = self.video_filepath
        self.play_mode = new_mode
        self.setup_playlist(self.folder_video_files)
        # 嘗試維持目前播放的影片
        if prev_file and prev_file in self.playlist:
            self.current_playlist_index = self.playlist.index(prev_file)
        else:
            self.current_playlist_index = 0
        self.update_info_display()
        self.update_button_states()
        # 不自動切換影片，也不 reload_current_video

    def setup_playlist(self, video_files):
        """根據播放模式設置播放清單"""
        if self.play_mode == "folder_time":
            self.playlist = video_files
            self.order_button.config(state=tk.DISABLED)
        elif self.play_mode == "folder_json":
            self.playlist = self.load_or_create_json_playlist(video_files)
            self.order_button.config(state=tk.NORMAL)
        elif self.play_mode == "folder_random":
            self.playlist = video_files.copy()
            random.shuffle(self.playlist)
            self.order_button.config(state=tk.DISABLED)
        else:
            self.playlist = video_files
            self.order_button.config(state=tk.DISABLED)

    def load_or_create_json_playlist(self, current_files):
        """載入或建立JSON播放清單"""
        try:
            if os.path.exists(self.playlist_json_path):
                with open(self.playlist_json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    stored_playlist = json_data.get('playlist', [])
                
                # 檢查檔案變更
                stored_set = set(stored_playlist)
                current_set = set(current_files)
                
                # 移除不存在的檔案
                valid_stored = [f for f in stored_playlist if f in current_set]
                
                # 添加新檔案到列表末尾
                new_files = [f for f in current_files if f not in stored_set]
                new_files.sort(key=lambda x: os.path.getctime(x))  # 按建立時間排序新檔案
                
                updated_playlist = valid_stored + new_files
                
                # 如果有變更，更新JSON檔案
                if len(updated_playlist) != len(stored_playlist) or set(updated_playlist) != stored_set:
                    self.save_json_playlist(updated_playlist)
                    self.shared_state.log(f"播放清單已更新，新增 {len(new_files)} 個檔案", logging.INFO)
                
                return updated_playlist
            else:
                # 建立新的JSON檔案
                self.save_json_playlist(current_files)
                self.shared_state.log("已建立新的播放清單JSON檔案", logging.INFO)
                return current_files
                
        except Exception as e:
            self.shared_state.log(f"處理JSON播放清單時發生錯誤: {e}", logging.ERROR)
            return current_files

    def save_json_playlist(self, playlist):
        """儲存播放清單到JSON檔案"""
        try:
            json_data = {
                'created': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'playlist': playlist
            }
            with open(self.playlist_json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.shared_state.log(f"儲存JSON播放清單時發生錯誤: {e}", logging.ERROR)

    def open_order_window(self):
        """開啟順序調整視窗"""
        if not self.playlist:
            return
            
        def on_order_changed(new_playlist):
            self.playlist = new_playlist
            # 更新當前播放索引
            if self.video_filepath in self.playlist:
                self.current_playlist_index = self.playlist.index(self.video_filepath)
            self.save_json_playlist(new_playlist)
            self.update_info_display()
            self.shared_state.log("播放順序已更新", logging.INFO)
            
        PlaylistOrderWindow(self.frame, self.playlist, on_order_changed)

    def load_current_video(self):
        """載入當前索引的影片"""
        if not self.playlist or self.current_playlist_index >= len(self.playlist):
            return

        filepath = self.playlist[self.current_playlist_index]
        self.load_video_file(filepath)

    def on_volume_changed(self, value):
        """音量調整事件 (0~100)"""
        if self.pygame_initialized:
            vol = float(value) / 100.0
            pygame.mixer.music.set_volume(vol)

    def load_video_file(self, filepath):
        """載入指定的影片檔案 (OpenCV/PIL 版本)"""
        self.stop_video_playback()  # 停止前一部影片
        self.stop_audio_playback()  # 停止前一部音訊
        self.video_filepath = filepath

        # 關閉前一個 VideoCapture
        if self.cap:
            self.cap.release()
            self.cap = None

        # 釋放前一個音訊暫存檔
        if self.audio_tempfile:
            try:
                os.remove(self.audio_tempfile)
            except Exception:
                pass
            self.audio_tempfile = None
        self.audio_loaded = False
        
        # 重置音訊播放狀態
        self.reset_audio_state()
        
        try:
            self.cap = cv2.VideoCapture(self.video_filepath)
            if not self.cap.isOpened():
                raise Exception("無法開啟影片檔案")
            self.video_loaded = True
            self.is_playing = False
            self.play_pause_button.config(text="播放", state=tk.NORMAL)
            self.video_status_label.config(text="")
            self.video_status_label.place_forget()
            self.show_first_frame()
            # --- 抽取音訊 ---
            self.init_pygame()
            clip = VideoFileClip(self.video_filepath)
            if clip.audio is not None:
                temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
                os.close(temp_fd)
                clip.audio.write_audiofile(temp_path, logger=None)
                self.audio_tempfile = temp_path
                pygame.mixer.music.load(self.audio_tempfile)
                self.audio_loaded = True
                # === 設定音量 ===
                vol = float(self.volume_var.get()) / 100.0
                pygame.mixer.music.set_volume(vol)
            else:
                self.audio_loaded = False
            clip.close()  # 釋放 moviepy 資源
        except Exception as e:
            self.video_loaded = False
            self.audio_loaded = False
            self.shared_state.log(f"載入影片時發生錯誤 '{self.video_filepath}': {e}", logging.ERROR)
            self.video_label.config(image="", text="")
            self.video_status_label.config(text=f"載入影片錯誤:\n{os.path.basename(self.video_filepath)}\n詳細: {str(e)[:100]}...", foreground="red", background="black", justify=tk.CENTER)
            self.video_status_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            self.play_pause_button.config(state=tk.DISABLED)
            self.progress_var.set(0)  # 新增：重設進度條

    def reset_audio_state(self):
        """重置音訊播放狀態"""
        self.audio_start_time = None
        self.audio_pause_position = 0
        self.is_audio_paused = False

    def get_current_audio_position(self):
        """取得當前音訊播放位置 (秒)"""
        if not self.audio_loaded:
            return 0
        
        if self.is_audio_paused:
            return self.audio_pause_position
        
        if self.audio_start_time is None:
            return 0
        
        # 計算從開始播放到現在的時間，加上之前暫停的位置
        elapsed_time = time.time() - self.audio_start_time
        return self.audio_pause_position + elapsed_time

    def show_first_frame(self):
        """顯示影片第一幀"""
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
                self.progress_var.set(0)  # 新增：重設進度條
            else:
                self.video_label.config(image="", text="無法讀取影片畫面", fg="red")

    def display_frame(self, frame):
        """將 OpenCV frame 顯示到 Tkinter Label，固定長寬比，寬最大等比例縮放"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)

        # 固定顯示比例 16:9
        aspect_w, aspect_h = 16, 9

        # 取得 video_label 寬度
        label_w = self.video_label.winfo_width() or 400
        # 根據比例計算高度
        target_h = int(label_w * aspect_h / aspect_w)

        # 若 video_label 實際高度不足，則以高度為基準縮放
        label_h = self.video_label.winfo_height() or 200
        if target_h > label_h:
            target_h = label_h
            label_w = int(target_h * aspect_w / aspect_h)

        # 影片原始尺寸
        img_w, img_h = img.size
        # 計算縮放比例
        scale = min(label_w / img_w, target_h / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)

        # 建立黑底畫布，將影片畫面置中
        canvas = Image.new("RGB", (label_w, target_h), (0, 0, 0))
        offset_x = (label_w - new_w) // 2
        offset_y = (target_h - new_h) // 2
        canvas.paste(img, (offset_x, offset_y))

        self.frame_image = ImageTk.PhotoImage(canvas)
        self.video_label.config(image=self.frame_image)
        self.video_label.image = self.frame_image

    # === 進度條事件 ===
    def on_progress_press(self, event):
        self.progress_dragging = True

    def on_progress_release(self, event):
        if not self.video_loaded or not self.cap:
            self.progress_dragging = False
            return
        value = self.progress_var.get()
        duration = self.get_video_duration()
        if duration > 0:
            target_sec = value * duration / 100
            self.seek_to(target_sec)
        self.progress_dragging = False

    def on_progress_drag(self, value):
        # 拖曳時不自動更新進度條
        pass

    def get_video_duration(self):
        """取得影片總長度（秒）"""
        if self.cap:
            frame_count = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                return frame_count / fps
        return 0

    def seek_to(self, sec):
        """跳轉到指定秒數，音訊與視訊同步（以音訊為主時脈，確保畫面對齊音訊）"""
        if not self.cap:
            return
        if self.audio_loaded:
            pygame.mixer.music.stop()
            pygame.mixer.music.play(start=sec)
            self.audio_start_time = time.time()
            self.audio_pause_position = sec
            self.is_audio_paused = False

            # 等待音訊真正開始後再同步畫面（多等幾次直到 get_pos 有效）
            def sync_video_try(count=0):
                pos_ms = pygame.mixer.music.get_pos()
                # get_pos() 可能會回傳 0 或 -1，需多等幾次
                if pos_ms is not None and pos_ms > 0:
                    audio_now = self.audio_pause_position + pos_ms / 1000.0
                    self.cap.set(cv2.CAP_PROP_POS_MSEC, audio_now * 1000)
                    ret, frame = self.cap.read()
                    if ret:
                        self.display_frame(frame)
                elif count < 10:
                    # 最多等 10 次，每次 20ms
                    self.frame.after(20, lambda: sync_video_try(count + 1))
                else:
                    # 最後 fallback 直接用 sec
                    self.cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
                    ret, frame = self.cap.read()
                    if ret:
                        self.display_frame(frame)
            sync_video_try()
            return
        # 無音訊時直接設定影片
        self.cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)

    def _sync_video_to_audio(self):
        """音訊啟動後同步影片畫面"""
        if not self.audio_loaded:
            return
        sec = self.audio_pause_position
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms is not None and pos_ms > 0:
            sec += pos_ms / 1000.0
        self.cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)

    def update_progress_bar(self):
        """根據目前播放位置更新進度條"""
        if not self.cap or not self.video_loaded:
            return
        if self.progress_dragging:
            return  # 拖曳時不自動更新
        duration = self.get_video_duration()
        if duration > 0:
            if self.audio_loaded:
                pos = self.get_current_audio_position()
            else:
                pos = self.cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            percent = min(max(pos / duration * 100, 0), 100)
            self.progress_var.set(percent)

    def play_video(self):
        """播放影片 (以音訊為主時脈)"""
        if not self.cap or not self.video_loaded:
            return
        if not self.is_playing:
            return

        # --- 音訊為主時脈 ---
        if self.audio_loaded:
            # 檢查音訊是否還在播放
            if pygame.mixer.music.get_busy() or self.is_audio_paused:
                # 取得音訊目前播放位置
                audio_pos = self.get_current_audio_position()
                
                # 設定影片到對應時間
                self.cap.set(cv2.CAP_PROP_POS_MSEC, audio_pos * 1000)
                ret, frame = self.cap.read()
                if ret:
                    self.display_frame(frame)
                    self.update_progress_bar()  # 新增：更新進度條
                    # 30ms 後再查詢音訊位置
                    self.after_id = self.frame.after(10, self.play_video)
                else:
                    # 播放到結尾
                    self.on_video_end()
            else:
                # 音訊播放結束
                self.on_video_end()
        else:
            # 無音訊時，維持原本的 frame/fps 控制
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame)
                self.update_progress_bar()  # 新增：更新進度條
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                delay = int(1000 / fps) if fps > 1 else 40
                self.after_id = self.frame.after(delay, self.play_video)
            else:
                self.on_video_end()

    def on_video_end(self):
        """影片播放結束處理"""
        self.next_video()  # 自動播放下一個影片

    def toggle_play_pause(self):
        if not self.video_loaded or not self.cap:
            return
        
        if self.is_playing:
            # 暫停
            self.is_playing = False
            self.play_pause_button.config(text="播放")
            if self.after_id:
                self.frame.after_cancel(self.after_id)
                self.after_id = None
            
            if self.audio_loaded:
                if pygame.mixer.music.get_busy():
                    # 記錄暫停時的位置
                    self.audio_pause_position = self.get_current_audio_position()
                    pygame.mixer.music.pause()
                self.is_audio_paused = True
            
            self.shared_state.log(f"影片已暫停", logging.DEBUG)
            self.shared_state.set("video_status", "Paused")
        else:
            # 播放
            self.is_playing = True
            self.play_pause_button.config(text="暫停")
            
            if self.audio_loaded:
                if self.is_audio_paused and pygame.mixer.music.get_busy():
                    # 從暫停處繼續播放
                    pygame.mixer.music.unpause()
                    self.audio_start_time = time.time()  # 重新記錄開始時間
                    self.is_audio_paused = False
                else:
                    # 從指定位置開始播放
                    pygame.mixer.music.play(start=self.audio_pause_position)
                    self.audio_start_time = time.time()
                    self.is_audio_paused = False
            
            self.shared_state.log(f"影片播放中", logging.DEBUG)
            self.shared_state.set("video_status", "Playing")
            self.play_video()

    def stop_video_playback(self):
        if self.after_id:
            self.frame.after_cancel(self.after_id)
            self.after_id = None
        self.is_playing = False
        self.play_pause_button.config(text="播放")
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.show_first_frame()
        self.shared_state.log(f"影片已停止", logging.DEBUG)
        self.shared_state.set("video_status", "Stopped")
        if self.audio_loaded:
            pygame.mixer.music.stop()
        self.reset_audio_state()
        self.progress_var.set(0)  # 新增：重設進度條

    def stop_audio_playback(self):
        if self.audio_loaded:
            pygame.mixer.music.stop()
            self.audio_loaded = False
        if self.audio_tempfile:
            try:
                os.remove(self.audio_tempfile)
            except Exception:
                pass
            self.audio_tempfile = None
        self.reset_audio_state()

    def previous_video(self):
        """播放上一個影片"""
        if not self.playlist or len(self.playlist) <= 1:
            return
        self.stop_video_playback()
        self.current_playlist_index = (self.current_playlist_index - 1) % len(self.playlist)
        self.update_info_display()
        self.load_current_video()
        # 自動播放
        if not self.is_playing:
            self.toggle_play_pause()

    def next_video(self):
        """播放下一個影片"""
        if not self.playlist or len(self.playlist) <= 1:
            return
        self.stop_video_playback()
        self.current_playlist_index = (self.current_playlist_index + 1) % len(self.playlist)
        self.update_info_display()
        self.load_current_video()
        # 自動播放
        if not self.is_playing:
            self.toggle_play_pause()

    def open_goto_window(self):
        """彈出視窗選擇要跳至的影片"""
        if not self.playlist:
            return

        goto_win = tk.Toplevel(self.frame)
        goto_win.title("跳至影片")
        goto_win.geometry("400x350")
        goto_win.transient(self.frame)
        goto_win.grab_set()

        ttk.Label(goto_win, text="選擇要跳至的影片:").pack(anchor=tk.W, padx=10, pady=(10, 0))

        listbox = tk.Listbox(goto_win, selectmode=tk.SINGLE)
        for i, filepath in enumerate(self.playlist):
            filename = os.path.basename(filepath)
            listbox.insert(tk.END, f"{i+1:2d}. {filename}")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        listbox.selection_set(self.current_playlist_index)
        listbox.see(self.current_playlist_index)

        def on_confirm():
            sel = listbox.curselection()
            if sel:
                idx = sel[0]
                if idx != self.current_playlist_index:
                    self.stop_video_playback()
                    self.current_playlist_index = idx
                    self.update_info_display()
                    self.load_current_video()
                    if not self.is_playing:
                        self.toggle_play_pause()
            goto_win.destroy()

        btn_frame = ttk.Frame(goto_win)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        ttk.Button(btn_frame, text="確定", command=on_confirm).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=goto_win.destroy).pack(side=tk.RIGHT)

    def update_info_display(self):
        """更新播放資訊顯示"""
        if self.play_mode == "single":
            filename = os.path.basename(self.playlist[0]) if self.playlist else "無"
            info_text = f"單一檔案: {filename}"
        else:
            if self.playlist:
                current_file = os.path.basename(self.playlist[self.current_playlist_index])
                total_files = len(self.playlist)
                current_num = self.current_playlist_index + 1
                mode_text = {"folder_time": "按時間", "folder_json": "JSON順序", "folder_random": "隨機"}.get(self.play_mode, "未知")
                info_text = f"資料夾播放 ({mode_text}): {current_num}/{total_files} - {current_file}"
            else:
                info_text = "未選擇檔案"
        self.info_label.config(text=info_text)

    def update_button_states(self):
        """更新按鈕狀態"""
        has_playlist = bool(self.playlist)
        has_multiple = len(self.playlist) > 1 if self.playlist else False

        if has_multiple:
            self.prev_button.config(state=tk.NORMAL)
            self.next_button.config(state=tk.NORMAL)
            self.goto_button.config(state=tk.NORMAL)  # 新增
        else:
            self.prev_button.config(state=tk.DISABLED)
            self.next_button.config(state=tk.DISABLED)
            self.goto_button.config(state=tk.DISABLED)  # 新增

        if self.play_mode == "folder_json" and has_playlist:
            self.order_button.config(state=tk.NORMAL)
        else:
            self.order_button.config(state=tk.DISABLED)

    def on_destroy(self):
        if self.after_id:
            self.frame.after_cancel(self.after_id)
            self.after_id = None
        if self.cap:
            self.cap.release()
            self.cap = None
        self.stop_audio_playback()
        if self.pygame_initialized:
            pygame.mixer.quit()
            self.pygame_initialized = False
        super().on_destroy()
        self.shared_state.set(f"{self.module_name}_ready", False)
        self.shared_state.set("video_status", "None")
        self.shared_state.log(f"{self.module_name} 模組已銷毀", logging.INFO)

# Standalone test
if __name__ == '__main__':
    try:
        from main import Module as MainModule
    except ImportError:
        class MainModule:
            def __init__(self, master, shared_state, module_name="Test", gui_manager=None):
                self.master = master
                self.shared_state = shared_state
                self.module_name = module_name
                self.gui_manager = gui_manager
                self.frame = ttk.Frame(master)
                self.shared_state.log(f"測試模組 '{self.module_name}' 已初始化")
            def get_frame(self): return self.frame
            def create_ui(self): ttk.Label(self.frame, text=f"{self.module_name} 內容").pack()
            def on_destroy(self): self.shared_state.log(f"測試模組 '{self.module_name}' 已銷毀")
        globals()['Module'] = MainModule

    class MockSharedState:
        def __init__(self): self.vars = {}
        def log(self, message, level=logging.INFO): print(f"LOG ({logging.getLevelName(level)}): {message}")
        def get(self, key, default=None): return self.vars.get(key, default)
        def set(self, key, value):
            self.vars[key] = value
            print(f"STATE SET: {key} = {value}")

    root = tk.Tk()
    root.title("增強影片模組測試")
    root.geometry("600x500")

    mock_shared_state = MockSharedState()

    module_container_frame = ttk.Frame(root, padding=10)
    module_container_frame.pack(fill=tk.BOTH, expand=True)

    video_module_instance = None
    video_module_instance = VideoModule(module_container_frame, mock_shared_state, gui_manager=None)
    video_module_instance.get_frame().pack(fill=tk.BOTH, expand=True)

    root.mainloop()

    if video_module_instance:
        video_module_instance.on_destroy()
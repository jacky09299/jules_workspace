import tkinter as tk
from tkinter import ttk
from main import Module # Assuming main.py is in parent directory
import logging # For logging level constants

class VideoModule(Module):
    def __init__(self, master, shared_state, module_name="Video", gui_manager=None): # Added gui_manager
        super().__init__(master, shared_state, module_name, gui_manager) # Pass gui_manager
        self.is_playing = False
        self.create_ui()

    def create_ui(self):
        # Configure this module's main frame
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Create a content frame within self.frame for padding and organization
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)

        # Mock video area
        video_area = tk.Frame(content_frame, bg="black", height=150, width=250) # Added width for better initial size
        video_area.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        video_area.pack_propagate(False) # Prevent children from shrinking the video_area
        ttk.Label(video_area, text="Video Playback Area", foreground="white", background="black").pack(expand=True)

        # Controls frame
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill=tk.X)

        self.play_pause_button = ttk.Button(controls_frame, text="Play", command=self.toggle_play_pause)
        self.play_pause_button.pack(side=tk.LEFT, padx=5)

        stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop_video)
        stop_button.pack(side=tk.LEFT)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)
        self.shared_state.set("video_module_ready", True)

    def toggle_play_pause(self):
        self.is_playing = not self.is_playing
        current_status = "Playing" if self.is_playing else "Paused"
        self.play_pause_button.config(text="Pause" if self.is_playing else "Play")
        self.shared_state.log(f"Video {current_status} by {self.module_name}.", level=logging.DEBUG)
        self.shared_state.set("video_status", current_status)


    def stop_video(self):
        if self.is_playing:
            self.is_playing = False
            self.play_pause_button.config(text="Play")
        self.shared_state.log(f"Video Stopped by {self.module_name}.", level=logging.DEBUG)
        self.shared_state.set("video_status", "Stopped")

    def on_destroy(self):
        super().on_destroy()
        # Cleanup for video module, e.g., release video resources if any
        self.shared_state.set("video_module_ready", False)
        self.shared_state.set("video_status", "None") # Or some other indicator
        self.shared_state.log(f"{self.module_name} instance destroyed.", level=logging.INFO)

# Standalone test (optional)
if __name__ == '__main__':
    try:
        from main import Module as MainModule
    except ImportError:
        class MainModule: # Minimal mock
            def __init__(self, master, shared_state, module_name="Test", gui_manager=None): # Added gui_manager
                self.master = master
                self.shared_state = shared_state
                self.module_name = module_name
                self.gui_manager = gui_manager
                self.frame = ttk.Frame(master)
                self.shared_state.log(f"MockModule '{self.module_name}' initialized.")
            def get_frame(self): return self.frame
            def create_ui(self): ttk.Label(self.frame, text=f"Content for {self.module_name}").pack()
            def on_destroy(self): self.shared_state.log(f"MockModule '{self.module_name}' destroyed.")
        globals()['Module'] = MainModule

    class MockSharedState:
        def __init__(self): self.vars = {}
        def log(self, message, level=logging.INFO): print(f"LOG ({logging.getLevelName(level)}): {message}")
        def get(self, key, default=None): return self.vars.get(key, default)
        def set(self, key, value):
            self.vars[key] = value
            print(f"STATE SET: {key} = {value}")

    root = tk.Tk()
    root.title("Video Module Test")
    root.geometry("300x250")

    mock_shared_state = MockSharedState()

    module_container_frame = ttk.Frame(root, padding=10)
    module_container_frame.pack(fill=tk.BOTH, expand=True)

    video_module = VideoModule(module_container_frame, mock_shared_state, gui_manager=None) # Pass gui_manager
    video_module.get_frame().pack(fill=tk.BOTH, expand=True)

    root.mainloop()
    video_module.on_destroy()

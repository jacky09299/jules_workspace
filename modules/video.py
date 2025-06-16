import tkinter as tk
from tkinter import ttk, filedialog
from main import Module # Assuming main.py is in parent directory
import logging # For logging level constants
import os # For os.path.basename

try:
    from tkVideoPlayer import TkinterVideo
except ImportError:
    TkinterVideo = None # Placeholder if library is not installed

class VideoModule(Module):
    def __init__(self, master, shared_state, module_name="Video", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.is_playing = False
        self.video_player = None
        self.video_loaded = False
        self.video_filepath = ""

        # Add a note about dependencies
        if TkinterVideo is None:
            self.shared_state.log("tkVideoPlayer library not found. Video playback will not be available.", logging.ERROR)
            # Display this message in the UI as well (done in create_ui)

        self.create_ui()

    def create_ui(self):
        # Configure this module's main frame
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Create a content frame within self.frame for padding and organization
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)

        # Video display area
        self.video_area = tk.Frame(content_frame, bg="black", height=200) # Min height
        self.video_area.pack(fill=tk.BOTH, expand=True, pady=(0,5))
        self.video_area.pack_propagate(False)

        self.video_status_label = ttk.Label(self.video_area, text="No video loaded. Please install tkVideoPlayer.", foreground="white", background="black")
        if TkinterVideo is not None:
            self.video_status_label.config(text="No video loaded.")
        self.video_status_label.pack(expand=True)

        # Controls frame
        controls_frame = ttk.Frame(content_frame)
        controls_frame.pack(fill=tk.X, pady=(5,0))

        load_button = ttk.Button(controls_frame, text="Load Video", command=self.load_video_file)
        load_button.pack(side=tk.LEFT, padx=5)

        self.play_pause_button = ttk.Button(controls_frame, text="Play", command=self.toggle_play_pause, state=tk.DISABLED)
        self.play_pause_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(controls_frame, text="Stop", command=self.stop_video_playback, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)

        self.shared_state.log(f"UI for {self.module_name} created.", level=logging.INFO)
        self.shared_state.set(f"{self.module_name}_ready", True)

    def load_video_file(self):
        if TkinterVideo is None:
            self.shared_state.log("tkVideoPlayer is not installed, cannot load video.", logging.ERROR)
            # Ensure status label is in video_area if it was cleared
            for widget in self.video_area.winfo_children(): widget.destroy()
            self.video_status_label = ttk.Label(self.video_area, text="Error: tkVideoPlayer library not found.", foreground="red", background="black")
            self.video_status_label.pack(expand=True)
            return

        filepath = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=(("MP4 files", "*.mp4"),
                       ("AVI files", "*.avi"),
                       ("All files", "*.*"))
        )
        if not filepath:
            return

        self.video_filepath = filepath
        ae_variable_for_fast_seek_check = None # Define outside to check in success log
        try:
            # Clear previous video player and status label if any
            if self.video_player: # If a player widget exists
                self.video_player.destroy()
            self.video_player = None # Ensure it's reset

            for widget in self.video_area.winfo_children(): # Clear out any status labels etc.
                widget.destroy()

            self.video_player = TkinterVideo(master=self.video_area, scaled=True)

            try:
                self.video_player.load(self.video_filepath) # Attempt to load
            except AttributeError as ae:
                ae_variable_for_fast_seek_check = ae # Store for outer scope check
                if 'fast_seek' in str(ae).lower():
                    self.shared_state.log(
                        f"AttributeError during video load (tkVideoPlayer/PyAV issue, possibly 'fast_seek'): {ae}. Playback might be unstable.",
                        logging.WARNING
                    )
                    # Update UI to inform user, but still try to proceed if load didn't fully crash player
                    self.video_status_label = ttk.Label(self.video_area, text=f"Warning: Video library issue ('fast_seek').\nPlayback may be affected.", foreground="orange", background="black", justify=tk.CENTER)
                    self.video_status_label.pack(expand=True)
                    # Player might be in an indeterminate state, but we'll allow trying to use it
                else:
                    raise # Re-raise other AttributeErrors not related to fast_seek

            self.video_player.pack(expand=True, fill="both")

            self.video_loaded = True # Assume loaded even with warning, user can try to play
            self.is_playing = False
            self.play_pause_button.config(text="Play", state=tk.NORMAL)
            self.stop_button.config(state=tk.NORMAL)

            # Avoid double logging success if warning was already issued due to fast_seek
            if not (ae_variable_for_fast_seek_check and 'fast_seek' in str(ae_variable_for_fast_seek_check).lower()):
                 self.shared_state.log(f"Video '{self.video_filepath}' loaded by {self.module_name}.", logging.INFO)
            self.shared_state.set("video_status", "Loaded") # Indicate Loaded, even if with warning

        except Exception as e: # General catch-all for other errors during setup or re-raised AttributeErrors
            self.video_loaded = False
            self.shared_state.log(f"Error setting up video player for '{self.video_filepath}': {e}", logging.ERROR)

            # Ensure video_area is clean if general error occurs
            if self.video_player and self.video_player.winfo_exists():
                self.video_player.destroy()
            self.video_player = None # Crucial to reset
            for widget in self.video_area.winfo_children(): # Clear area again
                widget.destroy()

            error_text = f"Error loading video:\n{os.path.basename(self.video_filepath)}\nDetails: {str(e)[:100]}..."
            self.video_status_label = ttk.Label(self.video_area, text=error_text, foreground="red", background="black", justify=tk.CENTER)
            self.video_status_label.pack(expand=True)
            self.play_pause_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)


    def toggle_play_pause(self):
        if not self.video_loaded or not self.video_player or not hasattr(self.video_player, 'is_paused'): # Check for player capabilities
            return

        try:
            if self.is_playing: # If logic thinks it's playing, then pause it
                self.video_player.pause()
                self.is_playing = False
                self.play_pause_button.config(text="Play")
                self.shared_state.log(f"Video Paused by {self.module_name}.", logging.DEBUG)
                self.shared_state.set("video_status", "Paused")
            else: # If logic thinks it's paused (or just loaded), then play it
                self.video_player.play()
                self.is_playing = True
                self.play_pause_button.config(text="Pause")
                self.shared_state.log(f"Video Playing by {self.module_name}.", logging.DEBUG)
                self.shared_state.set("video_status", "Playing")
        except Exception as e:
            self.shared_state.log(f"Error during toggle_play_pause: {e}", logging.ERROR)
            # Optionally, try to reset state if an error occurs during play/pause
            self.is_playing = False
            self.play_pause_button.config(text="Play")


    def stop_video_playback(self):
        if not self.video_player or not hasattr(self.video_player, 'stop'):
             self.play_pause_button.config(state=tk.DISABLED) # Ensure buttons disabled if no player
             self.stop_button.config(state=tk.DISABLED)
             return
        try:
            self.video_player.stop()
            self.is_playing = False
            self.video_loaded = False
            self.play_pause_button.config(text="Play", state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)
            self.shared_state.log(f"Video Stopped by {self.module_name}.", logging.DEBUG)
            self.shared_state.set("video_status", "Stopped")

            if self.video_player: # Destroy and recreate status label
                self.video_player.destroy()
                self.video_player = None

            # Re-create status label after destroying player
            self.video_status_label = ttk.Label(self.video_area, text="Video stopped. Load another video.", foreground="white", background="black")
            if TkinterVideo is None:
                 self.video_status_label.config(text="Error: tkVideoPlayer library not found.")
            self.video_status_label.pack(expand=True)

        except Exception as e:
            self.shared_state.log(f"Error stopping video: {e}", logging.ERROR)


    def on_destroy(self):
        if self.video_player:
            try:
                if self.is_playing: # Check if it might be playing
                    self.video_player.stop()
                self.video_player.destroy()
                self.video_player = None
            except Exception as e:
                self.shared_state.log(f"Error destroying video player in {self.module_name}: {e}", logging.ERROR)

        super().on_destroy()
        self.shared_state.set(f"{self.module_name}_ready", False)
        self.shared_state.set("video_status", "None")
        self.shared_state.log(f"{self.module_name} instance destroyed.", logging.INFO)

# Standalone test (optional) - This will require tkVideoPlayer to be installed
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
                # self.frame.pack(fill=tk.BOTH, expand=True)
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
    root.geometry("400x350")

    mock_shared_state = MockSharedState()

    module_container_frame = ttk.Frame(root, padding=10)
    module_container_frame.pack(fill=tk.BOTH, expand=True)

    video_module_instance = None
    if TkinterVideo is None:
        # If library not found, just show a label in the container.
        # The VideoModule itself will show a message in its own frame if instantiated.
        ttk.Label(module_container_frame, text="tkVideoPlayer not installed. VideoModule cannot be fully tested.").pack(expand=True)
    else:
        video_module_instance = VideoModule(module_container_frame, mock_shared_state, gui_manager=None)
        video_module_instance.get_frame().pack(fill=tk.BOTH, expand=True)

    root.mainloop()

    if video_module_instance:
        video_module_instance.on_destroy()

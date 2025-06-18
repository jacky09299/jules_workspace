import tkinter as tk
from tkinter import ttk, scrolledtext
import os
import threading
import queue
import time # For small delays

# Conditional import for pywinpty
try:
    import pywinpty
    PYWINPTY_AVAILABLE = True
except ImportError:
    PYWINPTY_AVAILABLE = False
    # Keep subprocess for fallback if needed, or error out
    import subprocess

from main import Module # Assuming main.Module is correctly located

class GuiCmdModule(Module):
    def __init__(self, master, shared_state, module_name="GUICMD", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"Initializing {self.module_name}...", level='INFO')

        self.output_queue = queue.Queue()
        # self.input_queue = queue.Queue() # Not strictly needed with pywinpty's direct write
        self.pty_process = None
        self.pty_thread = None
        self.is_running = True

        if not PYWINPTY_AVAILABLE:
            self.shared_state.log("pywinpty is not available. GUI CMD module may not function as expected.", level='ERROR')
            # Optionally, you could prevent the module from fully initializing or show an error in the UI.

        self.create_ui()
        if PYWINPTY_AVAILABLE:
            self._start_pty_thread()
        else:
            # Fallback or error message in UI
            self.output_area.config(state=tk.NORMAL)
            self.output_area.insert(tk.END, "pywinpty is not installed. This module requires it to function.\n", ("stderr",))
            self.output_area.config(state=tk.DISABLED)

        self.frame.after(100, self._process_output_queue)
        self.shared_state.log(f"{self.module_name} initialized. pywinpty available: {PYWINPTY_AVAILABLE}", level='INFO')

    def create_ui(self):
        self.frame.config(borderwidth=1, relief=tk.SOLID)
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)
        content_frame.rowconfigure(0, weight=1)
        content_frame.columnconfigure(0, weight=1)

        self.output_area = scrolledtext.ScrolledText(
            content_frame, wrap=tk.WORD, state=tk.DISABLED,
            bg="#2B2B2B", fg="#F0F0F0", insertbackground="#F0F0F0",
            selectbackground="#555555", font=("Consolas", 10)
        )
        self.output_area.grid(row=0, column=0, sticky="nsew")
        self.output_area.tag_configure("stdout", foreground="#A9B7C6")
        self.output_area.tag_configure("stderr", foreground="#FF6B68")
        self.output_area.tag_configure("command", foreground="#FFC66D", font=("Consolas", 10, "bold"))


        input_frame = ttk.Frame(content_frame)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(5,0))
        input_frame.columnconfigure(0, weight=1)

        self.input_entry = ttk.Entry(input_frame, font=("Consolas", 10), exportselection=False)
        self.input_entry.grid(row=0, column=0, sticky="ew")
        self.input_entry.bind("<Return>", self._send_command)
        self.input_entry.after(100, self.input_entry.focus_set)
        self.shared_state.log(f"UI for {self.module_name} created.", level='INFO')

    def _start_pty_thread(self):
        if not PYWINPTY_AVAILABLE:
            self.shared_state.log("Cannot start PTY thread: pywinpty not available.", level='ERROR')
            return

        self.pty_thread = threading.Thread(target=self._pty_loop, daemon=True)
        self.pty_thread.start()
        self.shared_state.log(f"{self.module_name}: PTY thread started.", level='INFO')

    def _pty_loop(self):
        try:
            # Determine shell command based on OS
            if os.name == 'nt':
                shell_cmd = ['cmd.exe']
            else:
                # For Linux/macOS, using 'script' can help capture full session including prompts
                # and avoid some issues with raw bash -i. Requires 'script' to be installed.
                # A simpler approach is just ['bash', '-i'] or ['zsh', '-i'] etc.
                # For broader compatibility and to ensure it works in various environments,
                # let's try a common shell. If 'script' isn't available, this might need adjustment.
                shell_cmd = ['bash', '-i']
                # Check if `script` command is available for better session capturing on non-Windows
                # if shutil.which('script'):
                #    shell_cmd = ['script', '-qec', 'bash -i', '/dev/null'] # bash -i as the command for script
                # else:
                #    shell_cmd = ['bash', '-i'] # Fallback if script is not available

            self.shared_state.log(f"Starting PTY with command: {' '.join(shell_cmd)}", level='INFO')

            # Get terminal size from the text_area (approximate)
            # This helps the PTY allocate a reasonably sized buffer and format output (e.g. `ls`)
            # It's an approximation; a more robust solution might involve handling terminal resize events.
            cols = 80  # Default
            rows = 24  # Default
            if self.output_area.winfo_exists(): # Check if widget exists before accessing properties
                # Approximate cols/rows from widget width/height and font size
                # This is a rough estimate.
                char_width_approx = self.output_area.cget("font")
                # A more reliable way to get font object and measure:
                try:
                    from tkinter import font as tkFont
                    text_font = tkFont.nametofont(self.output_area.cget("font"))
                    char_width = text_font.measure("M")
                    char_height = text_font.metrics("linespace")
                    widget_width = self.output_area.winfo_width()
                    widget_height = self.output_area.winfo_height()
                    if widget_width > 1 and char_width > 0 : cols = max(10, widget_width // char_width)
                    if widget_height > 1 and char_height > 0 : rows = max(5, widget_height // char_height)
                except Exception:
                    self.shared_state.log("Could not accurately determine terminal size from widget.", level='WARNING')


            self.pty_process = pywinpty.PtyProcess.spawn(shell_cmd, cols=cols, rows=rows, cwd=os.getcwd())
            self.shared_state.log(f"PTY process spawned (PID: {self.pty_process.pid}). Reading output...", level='INFO')

            while self.is_running and self.pty_process.is_alive():
                try:
                    # Read with a timeout to allow checking self.is_running periodically
                    # Adjust timeout as needed. Small timeout for responsiveness.
                    output = self.pty_process.read(timeout=50) # timeout in ms
                    if output:
                        self.output_queue.put((output, "stdout")) # Assume stdout, stderr is harder to distinguish with pty
                except pywinpty.WinPTYError as e:
                    # This can happen if the process exits or there's a read error
                    self.shared_state.log(f"WinPTYError during read: {e}", level='WARNING')
                    if "timeout" not in str(e).lower(): # Log if not a simple timeout
                        self.output_queue.put((f"PTY Read Error: {e}\n", "stderr"))
                    break # Exit loop on PTY read errors other than timeout
                except Exception as e:
                    self.output_queue.put((f"Error reading from PTY: {e}\n", "stderr"))
                    self.shared_state.log(f"Unhandled error reading from PTY: {e}", level='ERROR')
                    break

            if not self.pty_process.is_alive() and self.is_running:
                 self.output_queue.put(("\n[Shell process terminated]\n", "stderr"))

        except pywinpty.WinPTYError as e:
            self.output_queue.put((f"Failed to spawn PTY process: {e}\n", "stderr"))
            self.shared_state.log(f"Failed to spawn PTY: {e}", level='ERROR')
        except Exception as e:
            self.output_queue.put((f"General PTY loop error: {e}\n", "stderr"))
            self.shared_state.log(f"Unhandled PTY loop error: {e}", level='ERROR')
        finally:
            if self.pty_process and self.pty_process.is_alive():
                try:
                    self.pty_process.terminate(force=False) # Try graceful termination
                    time.sleep(0.1) # Give it a moment
                    if self.pty_process.is_alive():
                        self.pty_process.terminate(force=True) # Force if still alive
                except Exception as e_term:
                    self.shared_state.log(f"Error during PTY termination: {e_term}", level='ERROR')
            self.pty_process = None # Clear the reference
            self.shared_state.log(f"{self.module_name}: PTY loop ended.", level='INFO')

    def _send_command(self, event=None):
        if not PYWINPTY_AVAILABLE or not self.pty_process or not self.pty_process.is_alive():
            self.shared_state.log("Cannot send command: PTY not available or not running.", level='WARNING')
            self.output_queue.put(("[Cannot send command: PTY not ready]\n","stderr"))
            if self.input_entry: self.input_entry.delete(0, tk.END)
            return "break"

        command = self.input_entry.get()
        if command:
            try:
                # Echo command to the terminal display.
                # This makes it feel more like a real terminal.
                # pywinpty itself doesn't typically echo typed commands back via its read output for cmd.exe
                # For bash, it might, depending on tty settings.
                # We will manually add it for consistency.
                self.output_queue.put((command + "\r\n", "command")) # Use
 for Windows PTY

                # Send command to PTY
                # For Windows cmd.exe, commands often need
. For Linux/bash,
 is usually sufficient.
                # pywinpty handles some of this, but being explicit can be safer.
                # If os.name == 'nt':
                #    self.pty_process.write(command + '\r\n')
                # else:
                #    self.pty_process.write(command + '\n')
                self.pty_process.write(command + os.linesep) # Use os.linesep for platform compatibility

                self.input_entry.delete(0, tk.END)
            except pywinpty.WinPTYError as e:
                self.output_queue.put((f"Error writing to PTY: {e}\n", "stderr"))
                self.shared_state.log(f"Error writing to PTY: {e}", level='ERROR')
            except Exception as e:
                self.output_queue.put((f"General error sending command: {e}\n", "stderr"))
                self.shared_state.log(f"General error sending command: {e}", level='ERROR')
        return "break"

    def _process_output_queue(self):
        try:
            while not self.output_queue.empty():
                message_bytes, tag = self.output_queue.get_nowait()

                self.output_area.config(state=tk.NORMAL)
                try:
                    # pywinpty reads bytes. Decode them, replacing errors.
                    message_str = message_bytes.decode('utf-8', errors='replace')
                except AttributeError: # If it's already a string (e.g. from error messages we put in queue)
                    message_str = message_bytes
                except Exception as e:
                    message_str = f"[Decoding Error: {e}] Original (hex): {message_bytes.hex() if isinstance(message_bytes, bytes) else str(message_bytes)}\n"

                message_str = message_str.replace('\x00', '') # Remove null bytes

                # More robust ANSI escape code removal (basic)
                # import re
                # message_str = re.sub(r'\x1b(\[[0-9;?]*[a-zA-Z]|[()][0-9A-B])', '', message_str)
                # A simple way to handle common backspace and cursor movements for now
                # This is very basic and won't handle all ANSI sequences.
                # For example, cmd.exe output often contains  (backspace) to overwrite.
                # A proper terminal emulator would handle these.
                # For scrolledText, we might need to manually process some simple cases.

                # Minimal handling for backspace: if line ends with char + , remove both.
                # This is tricky with streamed output. A full solution is complex.
                # For now, let's just insert. Advanced handling can be a future improvement.

                self.output_area.insert(tk.END, message_str, (tag,))
                self.output_area.see(tk.END)
                self.output_area.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        except Exception as e:
            self.shared_state.log(f"Error processing output queue: {e}", level='ERROR')
            if self.output_area.winfo_exists():
                self.output_area.config(state=tk.NORMAL)
                self.output_area.insert(tk.END, f"\n[Output Processing Error: {e}]\n", ("stderr",))
                self.output_area.config(state=tk.DISABLED)
        finally:
            if self.is_running and self.frame.winfo_exists():
                self.frame.after(100, self._process_output_queue)

    def on_destroy(self):
        self.shared_state.log(f"Destroying {self.module_name}...", level='INFO')
        self.is_running = False # Signal PTY loop to stop

        if self.pty_thread and self.pty_thread.is_alive():
            # PTY loop should exit based on self.is_running or PTY error
            self.pty_thread.join(timeout=1.5) # Wait for graceful exit
            if self.pty_thread.is_alive():
                self.shared_state.log(f"{self.module_name}: PTY thread did not terminate gracefully. Forcing PTY process kill.", level='WARNING')
                if self.pty_process and self.pty_process.is_alive():
                    try:
                        self.pty_process.terminate(force=True) # Force kill if thread join failed
                    except Exception as e_term:
                        self.shared_state.log(f"Error during forceful PTY termination in on_destroy: {e_term}", level='ERROR')

        # Ensure pty_process is definitely cleaned up if it wasn't by the thread
        if self.pty_process and self.pty_process.is_alive():
            self.shared_state.log(f"{self.module_name}: PTY process still alive after thread join. Terminating.", level='WARNING')
            try:
                self.pty_process.terminate(force=True)
            except Exception as e:
                self.shared_state.log(f"Error terminating PTY process directly in on_destroy: {e}", level='ERROR')
        self.pty_process = None # Ensure it's cleared

        # Clear queue
        while not self.output_queue.empty():
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                break

        super().on_destroy()
        self.shared_state.log(f"{self.module_name} destroyed.", level='INFO')

# Basic standalone test setup
if __name__ == '__main__':
    class MockSharedState:
        def log(self, message, level="INFO"):
            print(f"[{level}] {message}")

    # This is needed if main.py defines Module and is not in PYTHONPATH directly
    # For testing, ensure main.py is discoverable or provide a mock Module
    # If main.Module is not found, you might need to adjust sys.path for local testing:
    # import sys
    # sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # Add parent dir to path
    # from main import Module # Then this should work

    root = tk.Tk()
    root.title("GuiCmdModule Test")
    root.geometry("700x500")

    shared_state = MockSharedState()

    # If Module class is not available, create a simple mock for testing this file standalone
    if "Module" not in globals():
        shared_state.log("Mocking main.Module for standalone test.", level="WARNING")
        class Module:
            def __init__(self, master, shared_state, module_name="UnknownModule", gui_manager=None):
                self.master = master # This is the parent Tkinter widget for the module's frame
                self.shared_state = shared_state
                self.module_name = module_name
                self.gui_manager = gui_manager
                # The module should create its own content frame inside self.master
                # For this test, app.get_frame() will be the module_host_frame given to GuiCmdModule
                self.frame = master # In the actual app, Module base class creates its own frame.
                                    # Here, GuiCmdModule's self.frame IS module_host_frame.
            def get_frame(self):
                return self.frame # This is what GuiCmdModule's super().__init__ expects.
            def on_destroy(self):
                self.shared_state.log(f"MockModule {self.module_name} on_destroy called.")

    module_host_frame = ttk.Frame(root, padding=10)
    module_host_frame.pack(expand=True, fill=tk.BOTH)

    app = GuiCmdModule(module_host_frame, shared_state, gui_manager=None)
    # In the real app, ModularGUI packs app.get_frame(). Here, module_host_frame IS app.frame.
    # So, no need to pack app.get_frame() again if it's the same as module_host_frame.

    # Ensure pywinpty is installed message if not available
    if not PYWINPTY_AVAILABLE:
        print("WARNING: pywinpty is not installed. The module will show an error message in its UI.")

    root.mainloop()

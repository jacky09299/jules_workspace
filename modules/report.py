import tkinter as tk
from tkinter import ttk
from main import Module # Assuming main.py is in parent directory
import logging # For logging level constants if needed

class ReportModule(Module):
    def __init__(self, master, shared_state, module_name="Report", gui_manager=None): # Added gui_manager
        super().__init__(master, shared_state, module_name, gui_manager) # Pass gui_manager
        self.create_ui()

    def create_ui(self):
        # Configure this module's main frame (self.frame)
        self.frame.config(borderwidth=2, relief=tk.GROOVE)

        # Create a content frame within self.frame for padding and organization
        content_frame = ttk.Frame(self.frame)
        content_frame.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

        title_label = ttk.Label(content_frame, text="System Report", font=("Helvetica", 16))
        title_label.pack(pady=(0,10))

        # Demonstrate getting a value from shared_state
        # Provide a default if the key might not exist
        status = self.shared_state.get("system_status", "Nominal")
        self.info_label = ttk.Label(content_frame, text=f"Current status: {status}")
        self.info_label.pack()

        # Demonstrate setting a value in shared_state and logging
        log_button = ttk.Button(content_frame, text="Log Report Access",
                                command=self.log_access)
        log_button.pack(pady=10)

        # Example of this module setting a state that other modules might observe
        self.shared_state.set(f"{self.module_name}_initialized", True)
        self.shared_state.log(f"UI for {self.module_name} created and state '{self.module_name}_initialized' set to True.")

        # Add an observer to a shared state variable
        self.shared_state.add_observer("system_status", self.on_system_status_change)


    def log_access(self):
        self.shared_state.log(f"'{self.module_name}' was accessed by user.", level=logging.INFO)
        # Example: Update a counter in shared state
        access_count = self.shared_state.get("report_access_count", 0)
        self.shared_state.set("report_access_count", access_count + 1)
        self.info_label.config(text=f"Accessed {access_count + 1} times. Status: {self.shared_state.get('system_status', 'Nominal')}")


    def on_system_status_change(self, key, value):
        self.shared_state.log(f"Noticed '{key}' changed to '{value}' in {self.module_name}.", level=logging.DEBUG)
        if self.info_label and self.info_label.winfo_exists():
             access_count = self.shared_state.get("report_access_count", 0)
             self.info_label.config(text=f"Accessed {access_count} times. Status: {value}")


    def on_destroy(self):
        super().on_destroy()
        # Clean up: remove observer
        self.shared_state.remove_observer("system_status", self.on_system_status_change)
        self.shared_state.set(f"{self.module_name}_initialized", False)
        self.shared_state.log(f"{self.module_name} instance destroyed, observer removed, and state '{self.module_name}_initialized' set to False.")

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
                # self.frame.pack(fill=tk.BOTH, expand=True) # Ensure it's packed by derived or test
                self.shared_state.log(f"MockModule '{self.module_name}' initialized.")
            def get_frame(self): return self.frame
            def create_ui(self): ttk.Label(self.frame, text=f"Content for {self.module_name}").pack()
            def on_destroy(self): self.shared_state.log(f"MockModule '{self.module_name}' destroyed.")
        globals()['Module'] = MainModule


    class MockSharedState:
        def __init__(self):
            self.vars = {}
            self.observers = {}
        def log(self, message, level=logging.INFO): print(f"LOG ({logging.getLevelName(level)}): {message}")
        def get(self, key, default=None): return self.vars.get(key, default)
        def set(self, key, value):
            self.vars[key] = value
            print(f"STATE SET: {key} = {value}")
            self.notify(key,value)
        def add_observer(self, key, callback):
            if key not in self.observers: self.observers[key] = []
            self.observers[key].append(callback)
            print(f"OBSERVER ADDED for {key}")
        def remove_observer(self, key, callback):
            if key in self.observers and callback in self.observers[key]:
                self.observers[key].remove(callback)
                print(f"OBSERVER REMOVED for {key}")
        def notify(self, key, value):
            if key in self.observers:
                for cb in self.observers[key]: cb(key,value)

    root = tk.Tk()
    root.title("Report Module Test")
    root.geometry("300x200")

    mock_shared_state = MockSharedState()

    module_container_frame = ttk.Frame(root, padding=10)
    module_container_frame.pack(fill=tk.BOTH, expand=True)

    report_module = ReportModule(module_container_frame, mock_shared_state, gui_manager=None) # Pass gui_manager
    report_module.get_frame().pack(fill=tk.BOTH, expand=True) # Pack module's frame into its container

    # Test observer functionality
    mock_shared_state.set("system_status", "Warning")

    root.mainloop()
    # Call on_destroy when done if not relying on WM_DELETE_WINDOW
    report_module.on_destroy()

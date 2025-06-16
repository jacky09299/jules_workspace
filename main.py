import tkinter as tk
from tkinter import ttk
import os
import importlib.util
import json
from shared_state import SharedState # Assuming shared_state.py is in the same directory
import logging # Added for logging level constants
import threading
import time

# Refined Module base class
class Module:
    def __init__(self, master, shared_state, module_name="UnknownModule", gui_manager=None): # Added gui_manager
        self.master = master # This is the container frame (frame_wrapper) provided by ModularGUI
        self.shared_state = shared_state
        self.module_name = module_name
        self.gui_manager = gui_manager # Store the ModularGUI instance

        # self.frame is the main content area created by the module, placed inside self.master (frame_wrapper)
        self.frame = ttk.Frame(self.master, borderwidth=1, relief=tk.SOLID)
        # self.frame needs to be packed into self.master by ModularGUI after module instantiation,
        # or the module can do it itself if master is always its direct parent for content.
        # For now, ModularGUI's setup_initial_layout handles packing self.frame into frame_wrapper.

        # Drag handle and title bar area
        self.title_bar_frame = ttk.Frame(self.frame, height=25, style="DragHandle.TFrame")
        self.title_bar_frame.pack(fill=tk.X, side=tk.TOP, pady=(0,2))

        self.drag_handle_label = ttk.Label(self.title_bar_frame, text="☰", cursor="fleur")
        self.drag_handle_label.pack(side=tk.LEFT, padx=5)

        self.title_label = ttk.Label(self.title_bar_frame, text=self.module_name)
        self.title_label.pack(side=tk.LEFT, padx=5)

        self.fullscreen_button = ttk.Button(self.title_bar_frame, text="FS", width=3, command=self.invoke_fullscreen_toggle)
        self.fullscreen_button.pack(side=tk.RIGHT, padx=(0, 5))

        self.shared_state.log(f"Module '{self.module_name}' initialized with title bar and FS button.")

    def invoke_fullscreen_toggle(self):
        if self.gui_manager:
            self.gui_manager.toggle_fullscreen(self.module_name)
        else:
            self.shared_state.log(f"Cannot toggle fullscreen for {self.module_name}: gui_manager not available.", logging.ERROR)

    def get_frame(self):
        '''Returns the main tk.Frame of the module that contains its UI elements.'''
        return self.frame

    def create_ui(self):
        '''
        Modules must override this method to create their specific UI components
        within self.frame.
        '''
        # Example: Basic label indicating the module name
        ttk.Label(self.frame, text=f"Default content for {self.module_name}").pack(padx=10, pady=10)
        self.shared_state.log(f"Module '{self.module_name}' UI created (default implementation).")

    def on_destroy(self):
        '''
        Called when the module is being destroyed.
        Modules can override this to perform cleanup, like stopping background tasks.
        '''
        self.shared_state.log(f"Module '{self.module_name}' is being destroyed.")

class ModularGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Modular GUI Framework")
        self.root.geometry("800x600")

        # Style for drag handle (optional, can be customized)
        s = ttk.Style()
        s.configure("DragHandle.TFrame", background="lightgrey") # Example style

        self.shared_state = SharedState(config_file='layout_config.json')
        self.shared_state.log("ModularGUI initialized.")

        self.modules_dir = "modules"
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            self.shared_state.log(f"Created modules directory: {self.modules_dir}")

        self.loaded_modules = {} # To store instances of loaded modules
        # self.module_frames = {} # No longer used, frame_wrapper is in loaded_modules

        # Drag and drop state variables
        self.dragged_module_name = None
        self.drag_start_widget = None
        self.drop_target_pane = None
        self.original_dragged_module_relief = None

        # Fullscreen state
        self.fullscreen_module_name = None
        # self.store_main_pane_children = [] # Unused attribute, removed.

        # Main layout container - using PanedWindow for resizable sections
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, background="lightgrey")
        self.main_pane.pack(fill=tk.BOTH, expand=True)

        self.available_module_classes = {} # Populated by discover_modules
        self.layout_config_file = 'layout_config.json' # Config file path

        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.main_pane.bind("<Button-3>", self.show_context_menu)

        # Module Polling for dynamic discovery at runtime
        self.known_module_files = set()     # Set of filepaths for modules already processed by initial scan or poller.
        self.polling_interval = 3           # Interval in seconds for checking the modules directory.
        self.stop_polling_event = threading.Event() # Event to signal the polling thread to stop.

        self.discover_modules() # Initial discovery of modules at startup.
        self.load_layout_config() # Load layout or use default after initial discovery.

        # Start the background thread for polling the modules directory.
        # It's a daemon thread so it exits when the main program exits.
        self.module_poller_thread = threading.Thread(target=self._module_polling_thread_target, daemon=True)
        self.module_poller_thread.start()
        # Logging of thread start is now inside _module_polling_thread_target.

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _discover_single_module_file(self, filename, filepath):
        """
        Attempts to discover a single module from a given file.

        Loads the Python file specified by `filepath`, looks for a class that
        inherits from `Module` (but is not `Module` itself), and if found,
        adds it to `self.available_module_classes` keyed by `module_name`.

        Args:
            filename (str): The name of the Python file (e.g., "clock.py").
            filepath (str): The full path to the Python file.

        Returns:
            bool: True if a new module class was successfully discovered and registered, False otherwise.
        """
        module_name = filename[:-3]

        # Avoid re-registering if a class for this module_name is already known.
        # This doesn't prevent reloading if file content changes (hot-reloading not implemented),
        # but primarily handles the case where the poller might see a file multiple times
        # or if initial scan and poller overlap.
        if module_name in self.available_module_classes:
             # self.shared_state.log(f"Module '{module_name}' class already available. Skipping re-discovery.", level=logging.DEBUG)
             return True # Considered "handled" as it's already known.

        try:
            self.shared_state.log(f"Attempting to discover module from file: {filepath}", level=logging.DEBUG)
            spec = importlib.util.spec_from_file_location(module_name, filepath)

            if spec is None or spec.loader is None:
                self.shared_state.log(f"Could not get valid spec or loader for module {module_name} from {filepath}", level=logging.WARNING)
                return False

            module_lib = importlib.util.module_from_spec(spec)
            # Add to sys.modules before exec_module if modules might import themselves or each other by name.
            # Note: For simplicity, if modules are in subdirectories, their names in sys.modules might need qualification.
            # sys.modules[module_name] = module_lib

            spec.loader.exec_module(module_lib) # Execute the module's code

            module_class_found = None
            # Iterate through the module's attributes to find a class derived from our base `Module`.
            for item_name in dir(module_lib):
                item = getattr(module_lib, item_name)
                if isinstance(item, type) and issubclass(item, Module) and item is not Module:
                    module_class_found = item
                    break # Found the first suitable class

            if module_class_found:
                # Store the discovered class, making it available for instantiation.
                self.available_module_classes[module_name] = module_class_found
                self.shared_state.log(f"Discovered module class {module_class_found.__name__} in {filename} (module name: '{module_name}')")
                return True
            else:
                self.shared_state.log(f"No suitable Module class found in {filename}", level=logging.WARNING)
                return False
        except ImportError as e:
            self.shared_state.log(f"ImportError when discovering module from {filename}: {e}", level=logging.ERROR)
            return False
        except Exception as e: # Catch any other errors during module loading.
            self.shared_state.log(f"Failed to discover module from {filename} due to an unexpected error: {e}", level=logging.ERROR)
            return False

    def discover_modules(self):
        """
        Performs an initial scan of the modules directory (`self.modules_dir`)
        at application startup to find and register available module classes.
        """
        self.shared_state.log("Initial module discovery...")
        # Cleared here to ensure a fresh list at startup or if this method is called for a full refresh.
        # self.available_module_classes.clear() # This is now cleared by __init__ before first call, or by poller if needed.
        # self.known_module_files.clear() # Also cleared by __init__.

        if not os.path.exists(self.modules_dir):
            self.shared_state.log(f"Modules directory '{self.modules_dir}' not found.", level=logging.WARNING)
            return

        # Iterate over files in the modules directory.
        for filename in os.listdir(self.modules_dir):
            if filename.endswith(".py") and not filename.startswith("_"): # Standard module file criteria
                filepath = os.path.join(self.modules_dir, filename)
                # Attempt to discover and register the module.
                if self._discover_single_module_file(filename, filepath):
                    self.known_module_files.add(filepath) # Add to set of known files after successful initial discovery.

        self.shared_state.log(f"Initial module discovery complete. Available modules: {list(self.available_module_classes.keys())}")

    def _module_polling_thread_target(self):
        """
        Target function for the background thread that polls the modules directory
        for new module files.
        """
        self.shared_state.log("Module polling thread started.", level=logging.INFO)
        while not self.stop_polling_event.is_set():
            try:
                if not os.path.exists(self.modules_dir):
                    # If modules directory disappears, log and wait.
                    self.shared_state.log(f"Modules directory '{self.modules_dir}' not found during polling.", level=logging.WARNING)
                    if self.stop_polling_event.is_set(): break
                    time.sleep(self.polling_interval * 2) # Wait longer if dir is missing
                    continue

                current_files_in_dir = set()
                # Scan the directory for current Python files.
                for filename in os.listdir(self.modules_dir):
                    if filename.endswith(".py") and not filename.startswith("_"):
                        filepath = os.path.join(self.modules_dir, filename)
                        current_files_in_dir.add(filepath)

                # Identify new files by comparing with the set of known (already processed) files.
                new_files = current_files_in_dir - self.known_module_files

                if new_files:
                    self.shared_state.log(f"Polling: Detected new potential module files: {new_files}", level=logging.INFO)
                    for filepath in new_files:
                        filename = os.path.basename(filepath)
                        # Schedule the discovery of the new file to run in the main GUI thread
                        # to ensure thread safety for Tkinter operations and shared data modification.
                        self.root.after(0, lambda fp=filepath, fn=filename: self._process_newly_detected_file(fp, fn))

                # Note: This logic currently only adds new files. It does not handle deleted files
                # or changes to existing files (hot-reloading).
                # To detect deletions, one might compare self.known_module_files with current_files_in_dir.

            except Exception as e: # Catch broad exceptions to keep the poller alive.
                self.shared_state.log(f"Error in module polling thread: {e}", level=logging.ERROR)

            # Wait for the polling interval before the next scan, but break early if stop event is set.
            if self.stop_polling_event.wait(timeout=self.polling_interval): # wait returns true if event is set
                break

        self.shared_state.log("Module polling thread stopped.", level=logging.INFO)

    def _process_newly_detected_file(self, filepath, filename):
        """
        Callback executed in the main Tkinter thread (via root.after) to process
        a newly detected module file from the polling thread.
        """
        self.shared_state.log(f"Main thread processing newly detected file: {filename}", level=logging.DEBUG)
        if self._discover_single_module_file(filename, filepath):
            # If successfully discovered and registered, add to known files.
            self.known_module_files.add(filepath)
            # New modules will be available in the context menu as it rebuilds each time.
            # If immediate UI update or notification were needed, it would go here.
            self.shared_state.log(f"Successfully processed and added new module '{filename}' to available classes.", level=logging.INFO)
        else:
            # _discover_single_module_file already logs detailed errors.
            # If it fails, it's not added to known_module_files, so the poller might try again
            # if the file isn't changed or removed. This behavior is acceptable for now.
            self.shared_state.log(f"Failed to process newly detected module from file {filename}.", level=logging.WARNING)


    def instantiate_module(self, module_name, master_pane_for_wrapper):
        if module_name not in self.available_module_classes:
            self.shared_state.log(f"Module class for '{module_name}' not found.", level=logging.ERROR)
            return None

        # Callers (load_layout_config, setup_default_layout, toggle_module_visibility)
        # are responsible for managing self.loaded_modules state (e.g., clearing it
        # or checking if a module should be re-instantiated vs. just shown).
        # This method's primary job is to create a new instance and its wrapper.
        # The check for module_name in self.loaded_modules was removed from here,
        # as callers should handle that logic if they intend to reuse instances.

        ModuleClass = self.available_module_classes[module_name]

        # frame_wrapper is the direct child of the master_pane_for_wrapper (e.g., self.main_pane)
        frame_wrapper = ttk.Frame(master_pane_for_wrapper, relief=tk.SUNKEN, borderwidth=1)

        try:
            # Module instance's master is frame_wrapper. Its own self.frame is created inside frame_wrapper.
            module_instance = ModuleClass(frame_wrapper, self.shared_state, module_name, self)

            # The module's own content frame (module_instance.get_frame()) is packed into frame_wrapper.
            module_instance.get_frame().pack(fill=tk.BOTH, expand=True)

            self.loaded_modules[module_name] = {
                'class': ModuleClass,
                'instance': module_instance,
                'frame_wrapper': frame_wrapper
            }

            # Bind drag events
            drag_handle_widget = module_instance.drag_handle_label
            drag_handle_widget.bind("<ButtonPress-1>", lambda event, mn=module_name: self.start_drag(event, mn))

            master_pane_for_wrapper.add(frame_wrapper) # Removed weight parameter
            self.shared_state.log(f"Instantiated and added module '{module_name}' to pane.")
            return frame_wrapper
        except Exception as e:
            self.shared_state.log(f"Error instantiating module {module_name}: {e}", level=logging.ERROR)
            if frame_wrapper.winfo_exists(): # Clean up frame_wrapper if instance failed
                frame_wrapper.destroy()
            return None

    def setup_default_layout(self):
        self.shared_state.log("Setting up default layout...")

        # Ensure any existing panes are cleared before setting up a new layout
        if hasattr(self.main_pane, 'panes'):
            for pane_id_str in list(self.main_pane.panes()):
                self.main_pane.forget(pane_id_str)

        # Optionally, clear/destroy previously loaded module instances and their wrappers
        # This depends on whether modules should persist if not in the new layout
        # For a simple default layout, let's assume we are building from scratch or a clean state.
        # We might need a more sophisticated way to manage modules not in the current layout.
        # For now, this doesn't explicitly destroy old instances, instantiate_module handles new ones.

        modules_to_display = ['clock', 'report', 'video']
        created_wrappers = []
        for module_name in modules_to_display:
            if module_name in self.available_module_classes:
                # Check if already loaded (e.g. if setup_default_layout is called multiple times or after a partial load)
                # This check is simplistic; a robust solution would ensure module isn't already in a pane.
                if module_name in self.loaded_modules and self.loaded_modules[module_name]['instance']:
                    wrapper = self.loaded_modules[module_name]['frame_wrapper']
                    if wrapper and wrapper.winfo_exists(): # Check if widget still exists
                        try:
                            # If it's not already a child of main_pane (e.g. after fullscreen or layout clear)
                            if str(wrapper.master) != str(self.main_pane): # Compare string paths of masters
                                 self.main_pane.add(wrapper) # Re-add if not currently in main_pane (Removed weight)
                                 created_wrappers.append(wrapper)
                                 self.shared_state.log(f"Re-added existing module '{module_name}' to default layout.")
                            elif wrapper in self.main_pane.panes(): # Already there
                                 created_wrappers.append(wrapper)
                            else: # Is child of main_pane but not added as a pane (shouldn't happen with current logic)
                                 self.main_pane.add(wrapper) # Removed weight
                                 created_wrappers.append(wrapper)
                            continue
                        except tk.TclError: # If already a child or other error
                             self.shared_state.log(f"Could not re-add wrapper for {module_name}, attempting new instantiation.", level=logging.WARNING)
                             # Fall through to instantiate if re-adding fails

                # If not loaded, or re-adding failed, instantiate it
                wrapper = self.instantiate_module(module_name, self.main_pane)
                if wrapper:
                    created_wrappers.append(wrapper)
            else:
                self.shared_state.log(f"Module '{module_name}' for default layout not available.", level=logging.WARNING)

        if not created_wrappers: # Check if any modules were actually added to the pane
            # Add a default label if no modules are loaded to prevent empty PanedWindow issues
            default_label = ttk.Label(self.main_pane, text="No modules available for default layout.")
            self.main_pane.add(default_label) # Add default label to the main_pane (no weight here either)
            self.shared_state.log("No modules loaded for default layout. Displaying default message.")

    def save_layout_config(self):
        self.shared_state.log(f"Saving layout configuration to {self.layout_config_file}")
        layout_data = {
            'fullscreen_module': self.fullscreen_module_name,
            'paned_window_layout': None
        }

        if not self.fullscreen_module_name and hasattr(self.main_pane, 'panes') and self.main_pane.winfo_exists() and len(self.main_pane.panes()) > 0 :
            panes_info = []
            # Create a reverse mapping from frame_wrapper widget ID (actual object id) to module_name
            wrapper_obj_to_module_name = {}
            for name, data in self.loaded_modules.items():
                if data.get('frame_wrapper'):
                    wrapper_obj_to_module_name[id(data['frame_wrapper'])] = name

            current_pane_widgets = []
            try:
                # .panes() returns string paths. We need to convert them to actual widget objects.
                current_pane_ids_str = self.main_pane.panes()
                for pane_id_str in current_pane_ids_str:
                    # This is a bit risky if widget path changes or isn't found, but standard way.
                    current_pane_widgets.append(self.main_pane.nametowidget(pane_id_str))
            except tk.TclError as e:
                 self.shared_state.log(f"Error converting pane IDs to widgets: {e}", level=logging.ERROR)


            for wrapper_widget in current_pane_widgets:
                module_name = wrapper_obj_to_module_name.get(id(wrapper_widget))
                if module_name:
                    panes_info.append({'module_name': module_name})
                else:
                    self.shared_state.log(f"Could not find module name for pane widget {wrapper_widget} during save.", level=logging.WARNING)

            sash_positions = []
            # PanedWindow creates N-1 sashes for N panes.
            if len(current_pane_widgets) > 1:
                for i in range(len(current_pane_widgets) - 1):
                    try:
                        # For HORIZONTAL PanedWindow, sashes are vertical, position is x-coordinate
                        coord = self.main_pane.sash_coord(i) # Returns (x, y) tuple for the sash
                        sash_positions.append(coord[0]) # Store the x-coordinate
                        self.shared_state.log(f"Saved sash {i} x-coordinate: {coord[0]}", level=logging.DEBUG)
                    except tk.TclError as e: # Might happen if panes are not fully realized
                        self.shared_state.log(f"Error getting sash coordinate for sash {i}: {e}", level=logging.WARNING)

            layout_data['paned_window_layout'] = {
                'modules': panes_info,
                'sash_positions': sash_positions
            }
        elif self.fullscreen_module_name:
            self.shared_state.log("Saving layout while in fullscreen mode. PanedWindow layout not explicitly saved.", level=logging.INFO)

        try:
            with open(self.layout_config_file, 'w') as f:
                json.dump(layout_data, f, indent=4)
            self.shared_state.log(f"Layout configuration saved to {self.layout_config_file}")
        except IOError as e:
            self.shared_state.log(f"Error saving layout configuration to {self.layout_config_file}: {e}", level=logging.ERROR)
        except Exception as e:
             self.shared_state.log(f"An unexpected error occurred while saving layout: {e}", level=logging.ERROR)

    def load_layout_config(self):
        # Strategy:
        # 1. Try to load from config file. If fails (e.g., file not found, JSON error), setup default layout.
        # 2. Clear any existing modules/panes from the UI and internal tracking (self.loaded_modules).
        #    This involves calling on_destroy() for existing module instances and destroying their wrappers.
        # 3. Load modules specified in the 'paned_window_layout' section of the config.
        #    This uses self.instantiate_module() for each.
        # 4. Apply saved sash positions to the PanedWindow after UI updates.
        # 5. If a 'fullscreen_module' is specified in the config:
        #    a. Ensure this module is loaded (instantiate if it wasn't part of paned_window_layout).
        #    b. Activate fullscreen mode for it.
        # 6. If, after attempting to load the layout, no modules are visible (e.g., empty config,
        #    all configured modules failed to load) and not in fullscreen, fall back to default layout
        #    to ensure the application isn't blank.
        self.shared_state.log(f"Attempting to load layout configuration from {self.layout_config_file}")
        try:
            if not os.path.exists(self.layout_config_file):
                self.shared_state.log(f"Layout config file '{self.layout_config_file}' not found. Using default layout.", level=logging.INFO)
                self.setup_default_layout()
                return

            with open(self.layout_config_file, 'r') as f:
                layout_data = json.load(f)

            self.shared_state.log("Layout configuration loaded successfully.")

            paned_config = layout_data.get('paned_window_layout')
            fullscreen_module_from_config = layout_data.get('fullscreen_module')
            self.shared_state.log(f"Layout config data: Fullscreen='{fullscreen_module_from_config}', PanedModulesPresent={paned_config is not None}", logging.DEBUG)

            # Clear existing panes and module instances before applying new layout
            if hasattr(self.main_pane, 'panes'):
                for pane_id_str in list(self.main_pane.panes()):
                    try:
                        self.main_pane.forget(pane_id_str)
                    except tk.TclError as e:
                        self.shared_state.log(f"Error forgetting pane {pane_id_str} during layout load: {e}", level=logging.WARNING)

            # Destroy existing module instances and their wrappers to ensure a clean state
            for module_name, module_data in list(self.loaded_modules.items()):
                if module_data:
                    if module_data.get('instance'):
                        try:
                            module_data['instance'].on_destroy()
                        except Exception as e:
                            self.shared_state.log(f"Error during on_destroy for module {module_name}: {e}", level=logging.ERROR)
                    if module_data.get('frame_wrapper') and module_data['frame_wrapper'].winfo_exists():
                        module_data['frame_wrapper'].destroy()
            self.loaded_modules.clear()

            paned_config = layout_data.get('paned_window_layout')
            loaded_pane_widgets_for_sash = []
            loaded_configured_paned_modules_list = [] # For logging successfully instantiated paned modules

            if paned_config and paned_config.get('modules'):
                configured_module_names = [mi.get('module_name') for mi in paned_config.get('modules', []) if mi.get('module_name')]
                self.shared_state.log(f"Config file requests paned modules: {configured_module_names}", logging.INFO)

                for module_info in paned_config['modules']:
                    module_name = module_info.get('module_name')
                    if module_name and module_name in self.available_module_classes:
                        wrapper = self.instantiate_module(module_name, self.main_pane)
                        if wrapper:
                            loaded_pane_widgets_for_sash.append(wrapper)
                            loaded_configured_paned_modules_list.append(module_name)
                    else:
                        self.shared_state.log(f"Module '{module_name}' from layout config not loadable/available.", level=logging.WARNING)

                self.shared_state.log(f"Successfully instantiated paned modules from config: {loaded_configured_paned_modules_list}", logging.INFO)

                if loaded_pane_widgets_for_sash and paned_config.get('sash_positions'):
                    sash_positions = paned_config['sash_positions']
                    self.root.update_idletasks()
                    if len(sash_positions) == len(loaded_pane_widgets_for_sash) - 1:
                        for i, pos in enumerate(sash_positions):
                            try:
                                self.main_pane.sashpos(i, pos)
                            except tk.TclError as e:
                                self.shared_state.log(f"Error setting sash {i} to {pos}: {e}", level=logging.ERROR)
                    elif len(loaded_pane_widgets_for_sash) > 1 : # Only warn if sashes were expected
                        self.shared_state.log(f"Sash position count mismatch. Expected {len(loaded_pane_widgets_for_sash)-1}, got {len(sash_positions)}.", level=logging.WARNING)

            fullscreen_module_to_load = layout_data.get('fullscreen_module')
            if fullscreen_module_to_load:
                if fullscreen_module_to_load not in self.loaded_modules:
                    if fullscreen_module_to_load in self.available_module_classes:
                        self.shared_state.log(f"Fullscreen module '{fullscreen_module_to_load}' not in paned layout, loading it.", level=logging.INFO)
                        # Instantiate the module; it will be added to main_pane by instantiate_module.
                        # enter_fullscreen will then repack its frame_wrapper into root.
                        self.instantiate_module(fullscreen_module_to_load, self.main_pane)
                    else:
                         self.shared_state.log(f"Fullscreen module '{fullscreen_module_to_load}' not available.", level=logging.ERROR)
                         fullscreen_module_to_load = None

                if fullscreen_module_to_load and fullscreen_module_to_load in self.loaded_modules:
                    self.enter_fullscreen(fullscreen_module_to_load)

            if not self.main_pane.panes() and not self.fullscreen_module_name:
                self.shared_state.log("Layout loaded, but no modules are visible. Setting up default layout.", level=logging.INFO)
                self.setup_default_layout() # Fallback if loading results in an empty visible state

        except Exception as e:
            self.shared_state.log(f"Error loading layout configuration: {e}. Using default layout.", level=logging.ERROR)
            # Ensure a clean slate for default layout if loading fails mid-way
            if hasattr(self.main_pane, 'panes'):
                for pane_id_str in list(self.main_pane.panes()): self.main_pane.forget(pane_id_str)
            for md_name, md_data in list(self.loaded_modules.items()):
                if md_data.get('instance'): md_data['instance'].on_destroy()
                if md_data.get('frame_wrapper') and md_data['frame_wrapper'].winfo_exists(): md_data['frame_wrapper'].destroy()
            self.loaded_modules.clear()
            self.setup_default_layout()


    def on_closing(self):
        self.shared_state.log("Application closing...")
        # Signal the polling thread to stop and wait for it to finish.
        self.stop_polling_event.set()
        if hasattr(self, 'module_poller_thread') and self.module_poller_thread.is_alive():
             self.shared_state.log("Waiting for module polling thread to stop...", level=logging.DEBUG)
             self.module_poller_thread.join(timeout=self.polling_interval + 0.5) # Wait a bit longer than interval
             if self.module_poller_thread.is_alive():
                 self.shared_state.log("Module polling thread did not stop in time.", level=logging.WARNING)

        self.save_layout_config() # Save the layout before closing

        # Call on_destroy for all loaded module instances
        for module_name, module_data in list(self.loaded_modules.items()):
            if module_data and module_data.get('instance'):
                try:
                    module_data['instance'].on_destroy()
                except Exception as e:
                    self.shared_state.log(f"Error during on_destroy for module {module_name}: {e}", level=logging.ERROR)

        self.shared_state.save_config() # Saves shared_state variables
        self.root.destroy()

    # --- Context Menu Methods ---

    def show_context_menu(self, event):
        self.context_menu.delete(0, tk.END) # Clear previous menu items

        if self.fullscreen_module_name:
            self.context_menu.add_command(label="Exit Fullscreen to manage modules", command=self.exit_fullscreen)
        else:
            self.context_menu.add_command(label="Toggle Module Visibility:", state=tk.DISABLED)
            self.context_menu.add_separator()

            # Get current panes to check visibility correctly
            current_pane_wrappers = []
            if hasattr(self.main_pane, 'panes') and self.main_pane.winfo_exists():
                try:
                    pane_ids_str = self.main_pane.panes()
                    for pane_id_str in pane_ids_str:
                        current_pane_wrappers.append(self.main_pane.nametowidget(pane_id_str))
                except tk.TclError: # In case main_pane is empty or in an odd state
                    pass

            for module_name in sorted(self.available_module_classes.keys()):
                is_visible = False
                if module_name in self.loaded_modules:
                    mod_data = self.loaded_modules[module_name]
                    if mod_data.get('instance') and mod_data.get('frame_wrapper') in current_pane_wrappers:
                        is_visible = True

                prefix = "[x]" if is_visible else "[ ]"
                self.context_menu.add_command(
                    label=f"{prefix} {module_name}",
                    command=lambda mn=module_name: self.toggle_module_visibility(mn)
                )

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def toggle_module_visibility(self, module_name):
        self.shared_state.log(f"Toggle visibility for {module_name}", level=logging.DEBUG)

        is_visible = False
        wrapper_to_check = None
        if module_name in self.loaded_modules:
            mod_data = self.loaded_modules[module_name]
            if mod_data and mod_data.get('instance'): # Check mod_data exists
                wrapper_to_check = mod_data.get('frame_wrapper')
                if wrapper_to_check and wrapper_to_check.winfo_exists():
                    try:
                        # Check if the wrapper is currently a direct child (pane) of main_pane
                        if wrapper_to_check in self.main_pane.panes(): # .panes() gives IDs, need to compare widgets
                             # This check might be tricky. Let's use nametowidget if possible.
                             # A simpler check: if wrapper_to_check.master == self.main_pane and it's packed.
                             # For PanedWindow, being in .panes() is the key.
                             current_pane_widgets = [self.main_pane.nametowidget(p_id) for p_id in self.main_pane.panes()]
                             if wrapper_to_check in current_pane_widgets:
                                is_visible = True
                    except tk.TclError: # If main_pane has no panes or other issues
                        is_visible = False


        if is_visible:
            # Hide the module
            self.shared_state.log(f"Hiding module: {module_name}")
            module_data = self.loaded_modules[module_name]
            frame_wrapper = module_data.get('frame_wrapper')
            instance = module_data.get('instance')

            if frame_wrapper and frame_wrapper.winfo_exists():
                try:
                    self.main_pane.forget(frame_wrapper)
                except tk.TclError as e:
                    self.shared_state.log(f"Error forgetting pane for {module_name}: {e}", level=logging.WARNING)

                # Important: Destroy the instance and its frame_wrapper to free resources
                # and ensure it's cleanly reloaded if shown again.
                if instance:
                    instance.on_destroy() # Call module-specific cleanup

                # Destroy the frame_wrapper which contains the module's frame and the module instance's widgets
                # This should cascade and destroy children, including module_instance.frame
                frame_wrapper.destroy()

            del self.loaded_modules[module_name] # Remove from active tracking
            if not self.main_pane.panes(): # If no panes left, add a default message
                 default_label = ttk.Label(self.main_pane, text="No modules displayed. Right-click to add.")
                 self.main_pane.add(default_label)


        else:
            # Show the module
            self.shared_state.log(f"Showing module: {module_name}")
            if module_name in self.available_module_classes:
                # If there's a default label because no modules were shown, remove it.
                current_panes = self.main_pane.panes()
                if len(current_panes) == 1:
                    try:
                        pane_widget = self.main_pane.nametowidget(current_panes[0])
                        if isinstance(pane_widget, ttk.Label) and pane_widget.cget("text").startswith("No modules"):
                            self.main_pane.forget(pane_widget)
                            pane_widget.destroy()
                    except tk.TclError:
                        pass # Widget might have already been removed or is not a direct child

                self.instantiate_module(module_name, self.main_pane)
                self.root.update_idletasks() # Ensure PanedWindow updates
            else:
                self.shared_state.log(f"Module '{module_name}' cannot be shown, not found in available modules.", level=logging.WARNING)

        # Ensure layout is saved on next close
        # self.save_layout_config() # Or let it save on closing only


    # --- Drag and Drop Methods ---

    def start_drag(self, event, module_name):
        self.shared_state.log(f"Start dragging module: {module_name}", level=logging.DEBUG)
        self.dragged_module_name = module_name
        self.drag_start_widget = event.widget # This is the drag_handle or its child label

        # Store original relief for visual feedback
        dragged_frame_wrapper = self.loaded_modules[self.dragged_module_name].get('frame_wrapper')
        if dragged_frame_wrapper:
            self.original_dragged_module_relief = dragged_frame_wrapper.cget("relief")
            dragged_frame_wrapper.config(relief=tk.SOLID, borderwidth=2) # Highlight dragged item
            # Optionally, bring to front if PanedWindow respects stacking order (often not directly)
            # dragged_frame_wrapper.lift()


        self.root.config(cursor="fleur")
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.end_drag)

    def on_drag(self, event):
        if not self.dragged_module_name:
            return

        # Reset previous drop target's visual cue
        if self.drop_target_pane and self.drop_target_pane.winfo_exists():
            if self.drop_target_pane != self.loaded_modules[self.dragged_module_name].get('frame_wrapper'):
                 try:
                    self.drop_target_pane.config(borderwidth=1) # Reset border
                 except tk.TclError: pass # Widget might have been destroyed

        # Find the widget (pane) under the cursor
        # event.x_root, event.y_root are screen coordinates
        # We need to find which pane of self.main_pane this corresponds to.
        x_root, y_root = event.x_root, event.y_root

        current_target_pane = None
        for pane_name, module_data in self.loaded_modules.items():
            pane_widget = module_data.get('frame_wrapper')
            if pane_widget and pane_widget.winfo_exists():
                # Check if cursor is within this pane_widget
                x_min = pane_widget.winfo_rootx()
                x_max = x_min + pane_widget.winfo_width()
                y_min = pane_widget.winfo_rooty()
                y_max = y_min + pane_widget.winfo_height()

                if x_min <= x_root < x_max and y_min <= y_root < y_max:
                    current_target_pane = pane_widget
                    break

        if current_target_pane and current_target_pane != self.loaded_modules[self.dragged_module_name].get('frame_wrapper'):
            self.drop_target_pane = current_target_pane
            try:
                self.drop_target_pane.config(borderwidth=3) # Highlight potential drop target
            except tk.TclError: pass # Widget might have been destroyed
        else:
            self.drop_target_pane = None


    def end_drag(self, event):
        if not self.dragged_module_name:
            self.root.config(cursor="")
            self.root.unbind("<B1-Motion>")
            self.root.unbind("<ButtonRelease-1>")
            return

        self.shared_state.log(f"End dragging module: {self.dragged_module_name}", level=logging.DEBUG)
        self.root.config(cursor="")
        self.root.unbind("<B1-Motion>")
        self.root.unbind("<ButtonRelease-1>")

        dragged_module_frame_wrapper = self.loaded_modules[self.dragged_module_name].get('frame_wrapper')

        # Reset visual cue of dragged module
        if dragged_module_frame_wrapper and dragged_module_frame_wrapper.winfo_exists() and self.original_dragged_module_relief:
            try:
                dragged_module_frame_wrapper.config(relief=self.original_dragged_module_relief, borderwidth=1)
            except tk.TclError: pass


        # Reset visual cue of the last drop target
        if self.drop_target_pane and self.drop_target_pane.winfo_exists():
            try:
                self.drop_target_pane.config(borderwidth=1) # Reset border
            except tk.TclError: pass


        if self.drop_target_pane and self.drop_target_pane != dragged_module_frame_wrapper:
            try:
                # Get actual WIDGET OBJECTS currently in the PanedWindow, in order
                current_pane_widget_objects = [self.main_pane.nametowidget(p_id) for p_id in self.main_pane.panes()]
            except tk.TclError as e:
                self.shared_state.log(f"Error getting pane widgets during drag: {e}", level=logging.ERROR)
                # Reset drag state (copied from existing cleanup logic)
                self.dragged_module_name = None
                self.drag_start_widget = None
                self.drop_target_pane = None
                self.original_dragged_module_relief = None
                return

            # Ensure the widgets we are about to use for indexing still exist
            if not dragged_module_frame_wrapper.winfo_exists() or \
               not self.drop_target_pane.winfo_exists():
                self.shared_state.log("Dragged or target pane was destroyed before reorder could complete.", level=logging.WARNING)
                self.dragged_module_name = None
                self.drag_start_widget = None
                self.drop_target_pane = None
                self.original_dragged_module_relief = None
                return

            try:
                dragged_idx = current_pane_widget_objects.index(dragged_module_frame_wrapper)
                target_idx = current_pane_widget_objects.index(self.drop_target_pane)
            except ValueError:
                self.shared_state.log("Dragged or target pane widget object not found in the list of current pane widgets.", level=logging.ERROR)
                self.dragged_module_name = None
                self.drag_start_widget = None
                self.drop_target_pane = None
                self.original_dragged_module_relief = None
                return

            # Perform reorder on the list of WIDGET OBJECTS
            item_to_move = current_pane_widget_objects.pop(dragged_idx)
            current_pane_widget_objects.insert(target_idx, item_to_move)

            # Store the string IDs of all panes before forgetting, to ensure we forget correctly
            # This is important because self.main_pane.panes() will change as we forget items.
            pane_ids_to_forget = list(self.main_pane.panes())

            # Forget all panes using their string IDs
            for pane_fw_id_str in pane_ids_to_forget:
                 try:
                     self.main_pane.forget(pane_fw_id_str)
                 except tk.TclError as e:
                     self.shared_state.log(f"TclError forgetting pane {pane_fw_id_str}: {e}. May already be handled or gone.", level=logging.WARNING)

            # Re-add WIDGETS in the new order
            for widget_to_add in current_pane_widget_objects:
                if widget_to_add.winfo_exists(): # Ensure widget wasn't destroyed during forget/re-add process
                    self.main_pane.add(widget_to_add)
                else:
                    self.shared_state.log(f"Skipping re-add of destroyed widget: {widget_to_add}", level=logging.WARNING)

            self.shared_state.log(f"Module {self.dragged_module_name} reordered.", level=logging.INFO)
        else:
            self.shared_state.log(f"Drag ended without a valid drop for {self.dragged_module_name}.", level=logging.DEBUG)

        # Clear drag state
        self.dragged_module_name = None
        self.drag_start_widget = None
        self.drop_target_pane = None
        self.original_dragged_module_relief = None

    # --- Fullscreen Methods ---

    def toggle_fullscreen(self, module_name):
        if self.fullscreen_module_name:
            if self.fullscreen_module_name == module_name: # Clicking FS on already fullscreened module
                self.exit_fullscreen()
            else: # Fullscreening another module while one is already fullscreen
                self.exit_fullscreen()
                self.enter_fullscreen(module_name)
        else:
            self.enter_fullscreen(module_name)

    def enter_fullscreen(self, module_name):
        if module_name not in self.loaded_modules:
            self.shared_state.log(f"Module {module_name} not found for fullscreen.", logging.ERROR)
            return

        self.fullscreen_module_name = module_name
        fs_module_data = self.loaded_modules[module_name]
        fs_module_wrapper = fs_module_data['frame_wrapper']
        fs_module_instance = fs_module_data['instance']

        self.shared_state.log(f"Entering fullscreen for module: {module_name}", logging.INFO)

        # Store original direct children of main_pane (the frame_wrappers)
        # These are strings (widget paths) when using main_pane.panes()
        # It's better to store the actual widget references if possible,
        # but main_pane.panes() gives string IDs.
        # We already have frame_wrapper references in self.loaded_modules.
        # Let's just hide the main_pane.

        self.main_pane.pack_forget() # Hide main_pane and all its children

        # Pack the fullscreen module's wrapper directly into the root
        fs_module_wrapper.pack(fill=tk.BOTH, expand=True, before=self.main_pane) # 'before' tries to keep order if main_pane is repacked

        if fs_module_instance:
            fs_module_instance.fullscreen_button.config(text="Exit")
            # Optionally hide drag handle elements during fullscreen
            # fs_module_instance.drag_handle_label.pack_forget()
            # fs_module_instance.title_label.pack_forget()


    def exit_fullscreen(self):
        if not self.fullscreen_module_name:
            return

        fs_module_data = self.loaded_modules[self.fullscreen_module_name]
        fs_module_wrapper = fs_module_data['frame_wrapper']
        fs_module_instance = fs_module_data['instance']

        self.shared_state.log(f"Exiting fullscreen for module: {self.fullscreen_module_name}", logging.INFO)

        fs_module_wrapper.pack_forget() # Remove fullscreen module from root

        # Restore main_pane
        self.main_pane.pack(fill=tk.BOTH, expand=True)
        # The PanedWindow should remember its children (the frame_wrappers) and their states.
        # If any issues, we might need to explicitly re-add/configure panes.

        if fs_module_instance:
            fs_module_instance.fullscreen_button.config(text="FS")
            # Optionally restore drag handle elements
            # fs_module_instance.drag_handle_label.pack(side=tk.LEFT, padx=5)
            # fs_module_instance.title_label.pack(side=tk.LEFT, padx=5)


        self.fullscreen_module_name = None
        self.store_main_pane_children.clear()


if __name__ == "__main__":
    import sys
    # Ensure that 'main' module in sys.modules points to this script's execution context (__main__)
    # This helps plugins doing 'from main import Module' to get the correct Module class
    # when main.py is run as the entry point.
    if '__main__' in sys.modules: # Should always be true when run as script
        sys.modules['main'] = sys.modules['__main__']

    root = tk.Tk() # tk.Tk() should be after the sys.modules manipulation
    app = ModularGUI(root)
    root.mainloop()

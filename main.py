import tkinter as tk
from tkinter import ttk
import os
import importlib.util
import json
from shared_state import SharedState
import logging

class Module:
    def __init__(self, master, shared_state, module_name="UnknownModule", gui_manager=None):
        self.master = master
        self.shared_state = shared_state
        self.module_name = module_name
        self.gui_manager = gui_manager

        self.frame = ttk.Frame(self.master, borderwidth=1, relief=tk.SOLID)

        self.title_bar_frame = ttk.Frame(self.frame, height=25, style="DragHandle.TFrame")
        self.title_bar_frame.pack(fill=tk.X, side=tk.TOP, pady=(0,2))

        self.drag_handle_label = ttk.Label(self.title_bar_frame, text="☰", cursor="fleur")
        self.drag_handle_label.pack(side=tk.LEFT, padx=5)

        self.title_label = ttk.Label(self.title_bar_frame, text=self.module_name)
        self.title_label.pack(side=tk.LEFT, padx=5)

        self.close_button = ttk.Button(self.title_bar_frame, text="X", width=3,
                                        command=self.close_module_action)
        self.close_button.pack(side=tk.RIGHT, padx=(0, 2))

        self.fullscreen_button = ttk.Button(self.title_bar_frame, text="FS", width=3, command=self.invoke_fullscreen_toggle)
        self.fullscreen_button.pack(side=tk.RIGHT, padx=(0, 5))

        self.resize_handle = ttk.Sizegrip(self.frame)
        self.resize_handle.pack(side=tk.BOTTOM, anchor=tk.SE)
        self.resize_handle.bind("<ButtonPress-1>", self._on_resize_start)
        self.resize_handle.bind("<B1-Motion>", self._on_resize_motion)
        self.resize_handle.bind("<ButtonRelease-1>", self._on_resize_release)

        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0

        self.shared_state.log(f"Module '{self.module_name}' initialized with title bar and FS button.")

    def close_module_action(self):
        if self.gui_manager:
            self.shared_state.log(f"Close button clicked for module '{self.module_name}'.")
            self.gui_manager.hide_module(self.module_name)
        else:
            self.shared_state.log(f"Cannot close module '{self.module_name}': gui_manager not available.", "ERROR")

    def _on_resize_start(self, event):
        # --- Start of updated logic for _on_resize_start ---
        if self.gui_manager and            hasattr(self.gui_manager, 'window_size_fixed_after_init') and            self.gui_manager.window_size_fixed_after_init and            hasattr(self.gui_manager, 'root') and            hasattr(self.gui_manager.root, 'maxsize') and            hasattr(self.gui_manager.root, 'winfo_width') and            hasattr(self.gui_manager.root, 'winfo_height'):

            self.gui_manager.is_module_resizing = True

            # Store current maxsize
            self.gui_manager.root_maxsize_backup = self.gui_manager.root.maxsize()

            # Get current window dimensions
            current_width = self.gui_manager.root.winfo_width()
            current_height = self.gui_manager.root.winfo_height()

            # Store current geometry string
            self.gui_manager.window_geometry_before_module_resize = f"{current_width}x{current_height}"

            # Set maxsize to current dimensions to prevent expansion
            self.gui_manager.root.maxsize(current_width, current_height)
            # Optional: Consider also self.gui_manager.root.minsize(current_width, current_height)
            # For now, sticking to the plan which focuses on maxsize.

            if hasattr(self.gui_manager, 'shared_state'):
                self.gui_manager.shared_state.log(
                    f"Module resize started: Geometry '{self.gui_manager.window_geometry_before_module_resize}' stored. Maxsize temporarily set to {current_width}x{current_height}.", "DEBUG"
                )
        elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
             if not (hasattr(self.gui_manager, 'window_size_fixed_after_init') and self.gui_manager.window_size_fixed_after_init):
                 self.gui_manager.shared_state.log("Module resize started: window_size_fixed_after_init is False, not modifying window constraints.", "DEBUG")
             else:
                 self.gui_manager.shared_state.log("Module resize started: Could not set temporary window constraints (root or methods missing).", "WARNING")
        # --- End of updated logic for _on_resize_start ---

        # Original logic follows (ensure it's still there and correctly indented)
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root

        if self.gui_manager and self.gui_manager.main_layout_manager:
            module_props = self.gui_manager.main_layout_manager.get_module_info(self.module_name)
            if module_props:
                self.resize_start_width = module_props['width']
                self.resize_start_height = module_props['height']
            else:
                frame_wrapper = self.master
                self.resize_start_width = frame_wrapper.winfo_width()
                self.resize_start_height = frame_wrapper.winfo_height()
        else:
            frame_wrapper = self.master
            self.resize_start_width = frame_wrapper.winfo_width()
            self.resize_start_height = frame_wrapper.winfo_height()

    def _on_resize_motion(self, event):
        if not self.gui_manager or not self.gui_manager.main_layout_manager:
            return

        delta_x = event.x_root - self.resize_start_x
        delta_y = event.y_root - self.resize_start_y

        new_width = self.resize_start_width + delta_x
        new_height = self.resize_start_height + delta_y

        min_width = 50
        min_height = 50
        new_width = max(min_width, new_width)
        new_height = max(min_height, new_height)

        self.gui_manager.main_layout_manager.resize_module(self.module_name, new_width, new_height)
        
        if self.gui_manager and hasattr(self.gui_manager, 'update_layout_manager_canvas_item_config'):
            self.gui_manager.update_layout_manager_canvas_item_config()

    def _on_resize_release(self, event):
        if self.gui_manager:
            self.gui_manager.update_layout_scrollregion()

        # --- Start of updated logic for _on_resize_release ---
        if self.gui_manager and            hasattr(self.gui_manager, 'is_module_resizing') and            self.gui_manager.is_module_resizing:

            # Restore original maxsize first
            if hasattr(self.gui_manager, 'root_maxsize_backup') and                self.gui_manager.root_maxsize_backup is not None and                hasattr(self.gui_manager, 'root') and                hasattr(self.gui_manager.root, 'maxsize'):

                self.gui_manager.root.maxsize(
                    self.gui_manager.root_maxsize_backup[0],
                    self.gui_manager.root_maxsize_backup[1]
                )
                if hasattr(self.gui_manager, 'shared_state'):
                    self.gui_manager.shared_state.log(
                        f"Module resize ended: Main window maxsize restored to {self.gui_manager.root_maxsize_backup}.", "DEBUG"
                    )
            elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
                self.gui_manager.shared_state.log(
                    "Module resize ended: No valid maxsize backup found to restore.", "WARNING"
                )

            # Now, force the geometry to what it was before the drag
            if hasattr(self.gui_manager, 'window_geometry_before_module_resize') and                self.gui_manager.window_geometry_before_module_resize is not None and                hasattr(self.gui_manager, 'root') and                hasattr(self.gui_manager.root, 'geometry'):

                self.gui_manager.root.geometry(self.gui_manager.window_geometry_before_module_resize)
                if hasattr(self.gui_manager, 'shared_state'):
                    self.gui_manager.shared_state.log(
                        f"Module resize ended: Main window geometry restored to {self.gui_manager.window_geometry_before_module_resize}.", "DEBUG"
                    )
            elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
                 self.gui_manager.shared_state.log(
                    "Module resize ended: No stored geometry found to restore.", "WARNING"
                )

            # Reset flags and stored values
            self.gui_manager.is_module_resizing = False
            if hasattr(self.gui_manager, 'root_maxsize_backup'):
                self.gui_manager.root_maxsize_backup = None
            if hasattr(self.gui_manager, 'window_geometry_before_module_resize'):
                self.gui_manager.window_geometry_before_module_resize = None
        # --- End of updated logic for _on_resize_release ---

    def invoke_fullscreen_toggle(self):
        if self.gui_manager:
            self.gui_manager.toggle_fullscreen(self.module_name)
        else:
            self.shared_state.log(f"Cannot toggle fullscreen for {self.module_name}: gui_manager not available.", logging.ERROR)

    def get_frame(self):
        return self.frame

    def create_ui(self):
        ttk.Label(self.frame, text=f"Default content for {self.module_name}").pack(padx=10, pady=10)
        self.shared_state.log(f"Module '{self.module_name}' UI created (default implementation).")

    def on_destroy(self):
        self.shared_state.log(f"Module '{self.module_name}' is being destroyed.")

class CustomLayoutManager(tk.Frame):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.modules = {}
        self.canvas_parent = master
        self.current_canvas_width = self.canvas_parent.winfo_width() if self.canvas_parent.winfo_width() > 1 else 800
        self.last_calculated_content_width = 0
        self.last_calculated_content_height = 0

    def add_module(self, module_frame, module_name, width, height):
        self.modules[module_name] = {
            'frame': module_frame,
            'name': module_name,
            'width': width,
            'height': height,
        }
        self.reflow_layout()

    def remove_module(self, module_name):
        if module_name in self.modules:
            module_info = self.modules.pop(module_name)
            module_info['frame'].place_forget()
            self.reflow_layout()
        else:
            logging.getLogger().warning(f"CustomLayoutManager: Attempted to remove non-existent module '{module_name}'.")

    def resize_module(self, module_name, width, height):
        if module_name in self.modules:
            self.modules[module_name]['width'] = max(10, width)
            self.modules[module_name]['height'] = max(10, height)
            self.reflow_layout()
        else:
            logging.warning(f"CustomLayoutManager: Attempted to resize non-existent module: {module_name}")

    def _is_overlapping(self, r1_x, r1_y, r1_w, r1_h, r2_x, r2_y, r2_w, r2_h) -> bool:
        return r1_x < r2_x + r2_w and \
               r1_x + r1_w > r2_x and \
               r1_y < r2_y + r2_h and \
               r1_y + r1_h > r2_y

    def reflow_layout(self):
        placed_modules_rects = []
        container_width = self.current_canvas_width
        if container_width <= 1:
             container_width = self.canvas_parent.winfo_width()
        if container_width <= 1:
             container_width = 800

        max_x_coord = 0
        max_y_coord = 0

        scan_height_limit = 10000

        min_module_dim = 10

        for module_name, module_info in self.modules.items():
            current_w = max(min_module_dim, module_info['width'])
            current_h = max(min_module_dim, module_info['height'])

            found_position_for_module = False
            final_x, final_y = 0, 0

            for test_y_candidate in range(0, scan_height_limit, 1):
                for test_x_candidate in range(0, container_width - current_w + 1, 1):
                    can_place_here = True
                    for placed_rect in placed_modules_rects:
                        if self._is_overlapping(test_x_candidate, test_y_candidate, current_w, current_h,
                                                placed_rect['x'], placed_rect['y'], placed_rect['w'], placed_rect['h']):
                            can_place_here = False
                            break
                    if can_place_here:
                        final_x = test_x_candidate
                        final_y = test_y_candidate
                        found_position_for_module = True
                        break
                if found_position_for_module:
                    break

            if found_position_for_module:
                module_info['frame'].place(x=final_x, y=final_y, width=current_w, height=current_h)
                placed_modules_rects.append({'name': module_name, 'x': final_x, 'y': final_y, 'w': current_w, 'h': current_h})
                module_info['x'] = final_x
                module_info['y'] = final_y
                max_x_coord = max(max_x_coord, final_x + current_w)
                max_y_coord = max(max_y_coord, final_y + current_h)
            else:
                fallback_y = max_y_coord + 5 if placed_modules_rects else 0
                module_info['frame'].place(x=0, y=fallback_y, width=current_w, height=current_h)
                placed_modules_rects.append({'name': module_name, 'x': 0, 'y': fallback_y, 'w': current_w, 'h': current_h})
                module_info['x'] = 0
                module_info['y'] = fallback_y
                max_x_coord = max(max_x_coord, current_w)
                max_y_coord = max(max_y_coord, fallback_y + current_h)
                logging.warning(f"CustomLayoutManager: Could not find compact spot for {module_name}. Using fallback placement at (0, {fallback_y}).")

        self.last_calculated_content_width = max_x_coord
        self.last_calculated_content_height = max_y_coord + 5

        layout_manager_own_width = self.current_canvas_width
        if layout_manager_own_width <= 1:
            layout_manager_own_width = self.canvas_parent.winfo_width()
            if layout_manager_own_width <= 1:
                layout_manager_own_width = 800

        self.config(width=layout_manager_own_width, height=self.last_calculated_content_height)

    def get_max_module_width(self) -> int:
        if not self.modules:
            return 0

        max_w = 0
        for module_info in self.modules.values():
            if module_info.get('width', 0) > max_w:
                max_w = module_info['width']
        return max_w

    def move_module_before(self, module_to_move_name: str, target_module_name: str or None):
        if module_to_move_name not in self.modules:
            logging.error(f"CustomLayoutManager: Module to move '{module_to_move_name}' not found.")
            return

        moved_item_info = self.modules.pop(module_to_move_name)

        new_modules_dict = {}

        # Case 1: No specific target, or target is the module being moved (which is already popped).
        # This means the module should go to the end of the list.
        if target_module_name is None or target_module_name == module_to_move_name or target_module_name not in self.modules:
            # Add all remaining items from the original dictionary (already in order)
            for name, info in self.modules.items():
                new_modules_dict[name] = info
            # Add the moved item to the very end
            new_modules_dict[module_to_move_name] = moved_item_info
        else:
            # Case 2: A valid target_module_name is provided. Insert before it.
            inserted = False
            for name, info in self.modules.items():
                if name == target_module_name:
                    new_modules_dict[module_to_move_name] = moved_item_info # Insert moved item
                    inserted = True
                new_modules_dict[name] = info # Insert current item from loop
            
            # This case should ideally not be hit if target_module_name was valid and present.
            # However, as a fallback, if it wasn't inserted (e.g., target was the last item and loop finished), add to end.
            if not inserted:
                 new_modules_dict[module_to_move_name] = moved_item_info

        self.modules = new_modules_dict
        logging.info(f"New module order: {list(self.modules.keys())}")
        self.reflow_layout()

    def get_layout_data(self) -> dict:
        data = {}
        for name, info in self.modules.items():
            data[name] = {
                'width': info['width'],
                'height': info['height'],
                'x': info.get('x', 0),
                'y': info.get('y', 0)
            }
        return data

    def get_module_info(self, module_name):
        return self.modules.get(module_name)

class ModularGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Modular GUI Framework")
        self.root.geometry("800x600")

        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        self.modules_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Modules", menu=self.modules_menu)

        s = ttk.Style()
        s.configure("DragHandle.TFrame", background="lightgrey")

        self.shared_state = SharedState(config_file='layout_config.json')
        self.shared_state.log("ModularGUI initialized.")

        self.modules_dir = "modules"
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            self.shared_state.log(f"Created modules directory: {self.modules_dir}")

        self.loaded_modules = {}

        self.dragged_module_name = None
        self.drag_start_widget = None
        self.drop_target_module_frame_wrapper = None
        self.original_dragged_module_relief = None

        self.fullscreen_module_name = None
        # self.root_resizable_backup = None # This was removed, ensure it's not re-added
        self.is_module_resizing = False # This should be present
        self.root_maxsize_backup = None # This should be present
        self.window_geometry_before_module_resize = None # Added new attribute

        self.canvas_container = ttk.Frame(self.root)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_container)

        self.v_scrollbar = ttk.Scrollbar(self.canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_container.pack_propagate(False)

        self.main_layout_manager = CustomLayoutManager(self.canvas, background="lightgrey")

        self.main_layout_manager_window_id = self.canvas.create_window(
            (0, 0), window=self.main_layout_manager, anchor='nw'
        )

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        self.canvas.bind("<Configure>", self.on_canvas_configure)

        self.available_module_classes = {}
        self.layout_config_file = 'layout_config.json'
        self.window_size_fixed_after_init = False
        self.shared_state.log(f"ModularGUI.__init__: self.window_size_fixed_after_init initialized to {self.window_size_fixed_after_init}", "INFO")

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.main_layout_manager.bind("<Button-3>", self.show_context_menu)

        self.discover_modules()

        for module_name in sorted(self.available_module_classes.keys()):
            self.modules_menu.add_command(
                label=f"Add {module_name}",
                command=lambda mn=module_name: self.add_module_from_menu(mn)
            )

        self.load_layout_config()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _finalize_initial_window_state(self):
        """
        Called after the initial layout is complete.
        Sets the window_size_fixed_after_init flag and makes the window non-resizable.
        """
        self.root.update_idletasks() # Ensure dimensions are calculated
        self.window_size_fixed_after_init = True
        # self.root.resizable(False, False) # Removed this line
        current_w = self.root.winfo_width()
        current_h = self.root.winfo_height()
        self.shared_state.log(
            f"Initial window state finalized. window_size_fixed_after_init=True. Window remains user-resizable. Min size fixed. Current size: {current_w}x{current_h}",
            "INFO"
        )

    def _on_mousewheel(self, event):
        if hasattr(event, 'num') and event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif hasattr(event, 'num') and event.num == 5:
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, 'delta'):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_layout_scrollregion(self):
        self.main_layout_manager.update_idletasks()

        content_total_height = self.main_layout_manager.last_calculated_content_height

        content_total_width = self.main_layout_manager.last_calculated_content_width

        canvas_viewport_width = self.canvas.winfo_width()
        if canvas_viewport_width <= 1:
            canvas_viewport_width = 800

        item_width_for_canvas = canvas_viewport_width

        self.canvas.config(scrollregion=(0, 0, content_total_width, content_total_height))

        self.canvas.itemconfig(self.main_layout_manager_window_id,
                               width=item_width_for_canvas,
                               height=content_total_height)

    def update_layout_manager_canvas_item_config(self):
        if not hasattr(self, 'main_layout_manager') or self.main_layout_manager is None:
            self.shared_state.log("update_layout_manager_canvas_item_config: main_layout_manager not available.", "WARNING")
            return

        content_height = self.main_layout_manager.last_calculated_content_height
        content_width = self.main_layout_manager.last_calculated_content_width
        
        canvas_viewport_width = self.canvas.winfo_width()
        if canvas_viewport_width <= 1:
            canvas_viewport_width = self.root.winfo_width()
        if canvas_viewport_width <= 1:
            canvas_viewport_width = 800

        self.canvas.itemconfig(self.main_layout_manager_window_id, 
                               width=canvas_viewport_width, 
                               height=content_height)
        
        self.canvas.config(scrollregion=(0, 0, content_width, content_height))
        
        self.shared_state.log(f"update_layout_manager_canvas_item_config: Canvas item for LM set to width={canvas_viewport_width}, height={content_height}. Scrollregion set to (0,0,{content_width},{content_height})", "DEBUG")

    def on_canvas_configure(self, event):
        canvas_width = event.width

        self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width)

        if hasattr(self.main_layout_manager, 'current_canvas_width'):
            self.main_layout_manager.current_canvas_width = canvas_width

        if hasattr(self.main_layout_manager, 'reflow_layout'):
             self.main_layout_manager.reflow_layout()

        self.update_layout_scrollregion()

    def update_min_window_size(self):
        flag_exists = hasattr(self, 'window_size_fixed_after_init')
        flag_value = self.window_size_fixed_after_init if flag_exists else "N/A"
        self.shared_state.log(f"update_min_window_size CALLED. Flag 'window_size_fixed_after_init' exists: {flag_exists}, Value: {flag_value}", "INFO")

        if flag_exists and self.window_size_fixed_after_init:
            self.shared_state.log("update_min_window_size: Returning early because window_size_fixed_after_init is True.", "INFO")
            return

        if not hasattr(self, 'main_layout_manager') or self.main_layout_manager is None:
            self.shared_state.log("update_min_window_size: Returning early because main_layout_manager is not available.", "INFO")
            return

        max_module_w = self.main_layout_manager.get_max_module_width()
        base_min_width = 200
        padding = 20
        effective_min_width = max(base_min_width, max_module_w + padding if max_module_w > 0 else base_min_width)

        current_min_height = 0
        try:
            current_min_height = self.root.minsize()[1]
        except tk.TclError:
            current_min_height = 0 
        if current_min_height == 1 and self.root.winfo_height() > 1 :
             current_min_height = self.root.winfo_height() if self.root.winfo_height() > 20 else 200
        current_min_height = max(200, current_min_height)

        self.shared_state.log(f"update_min_window_size: Proceeding to set minsize. Calculated effective_min_width: {effective_min_width}, current_min_height: {current_min_height}", "INFO")
        try:
            self.root.minsize(effective_min_width, current_min_height)
            self.shared_state.log(f"update_min_window_size: self.root.minsize({effective_min_width}, {current_min_height}) CALLED.", "INFO")
            self.shared_state.log(f"Minimum window width set to: {effective_min_width}, min_height: {current_min_height}", "DEBUG") 
        except tk.TclError as e:
            self.shared_state.log(f"update_min_window_size: Error setting minsize: {e}", "WARNING")

    def add_module_from_menu(self, module_name: str):
        self.shared_state.log(f"Attempting to add module '{module_name}' from menu.")

        if module_name in self.loaded_modules:
            module_data = self.loaded_modules.get(module_name)
            if module_data and module_data.get('frame_wrapper') and \
               module_data.get('frame_wrapper').winfo_ismapped():
                self.shared_state.log(f"Module '{module_name}' is already loaded and likely visible. No action taken.", "INFO")
                return

        if module_name in self.available_module_classes:
            children = self.main_layout_manager.winfo_children()
            if len(children) == 1 and isinstance(children[0], ttk.Label):
                if "No modules available" in children[0].cget("text") or \
                   "No modules displayed" in children[0].cget("text"):
                    children[0].destroy()
                    self.shared_state.log("Removed default placeholder label.", "DEBUG")

            self.instantiate_module(module_name, self.main_layout_manager)
            self.root.update_idletasks()
            self.update_min_window_size()
            self.update_layout_scrollregion()
            self.shared_state.log(f"Module '{module_name}' instantiated from menu.")
        else:
            self.shared_state.log(f"Module '{module_name}' cannot be added, not found in available modules.", "WARNING")

    def discover_modules(self):
        self.shared_state.log("Discovering available modules...")
        self.available_module_classes.clear()
        if not os.path.exists(self.modules_dir):
            self.shared_state.log(f"Modules directory '{self.modules_dir}' not found.", level=logging.WARNING)
            return

        for filename in os.listdir(self.modules_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                try:
                    filepath = os.path.join(self.modules_dir, filename)
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    module_lib = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module_lib)

                    module_class_name = None
                    for item_name in dir(module_lib):
                        item = getattr(module_lib, item_name)
                        if isinstance(item, type) and issubclass(item, Module) and item is not Module:
                            module_class_name = item_name
                            break

                    if module_class_name:
                        ModuleClass = getattr(module_lib, module_class_name)
                        self.available_module_classes[module_name] = ModuleClass
                        self.shared_state.log(f"Discovered module class {ModuleClass.__name__} in {filename}")
                    else:
                        self.shared_state.log(f"No suitable Module class found in {filename}", level=logging.WARNING)
                except Exception as e:
                    self.shared_state.log(f"Failed to discover module from {filename}: {e}", level=logging.ERROR)
        self.shared_state.log(f"Module discovery complete. Available: {list(self.available_module_classes.keys())}")

    def instantiate_module(self, module_name, parent_layout_manager):
        if module_name not in self.available_module_classes:
            self.shared_state.log(f"Module class for '{module_name}' not found.", level=logging.ERROR)
            return None

        ModuleClass = self.available_module_classes[module_name]

        frame_wrapper = ttk.Frame(parent_layout_manager, relief=tk.SUNKEN, borderwidth=1)

        try:
            module_instance = ModuleClass(frame_wrapper, self.shared_state, module_name, self)

            module_instance.get_frame().pack(fill=tk.BOTH, expand=True)

            self.loaded_modules[module_name] = {
                'class': ModuleClass,
                'instance': module_instance,
                'frame_wrapper': frame_wrapper
            }

            drag_handle_widget = module_instance.drag_handle_label
            drag_handle_widget.bind("<ButtonPress-1>", lambda event, mn=module_name: self.start_drag(event, mn))

            initial_width, initial_height = 200, 150
            parent_layout_manager.add_module(frame_wrapper, module_name, initial_width, initial_height)
            self.update_min_window_size()
            self.update_layout_scrollregion()
            self.shared_state.log(f"Instantiated and added module '{module_name}' to layout manager.")
            return frame_wrapper
        except Exception as e:
            self.shared_state.log(f"Error instantiating module {module_name}: {e}", level=logging.ERROR)
            if frame_wrapper.winfo_exists():
                frame_wrapper.destroy()
            return None

    def setup_default_layout(self):
        self.shared_state.log("Setting up default layout...")

        modules_to_display = ['clock', 'report', 'video']
        created_wrappers = []
        for module_name in modules_to_display:
            if module_name in self.available_module_classes:
                wrapper = self.instantiate_module(module_name, self.main_layout_manager)
                if wrapper:
                    created_wrappers.append(wrapper)
            else:
                self.shared_state.log(f"Module '{module_name}' for default layout not available.", level=logging.WARNING)

        if not created_wrappers:
            default_label = ttk.Label(self.main_layout_manager, text="No modules available for default layout.")
            default_label.pack(padx=10, pady=10)
            self.shared_state.log("No modules loaded for default layout. Displaying default message in main_layout_manager.")
        self.update_min_window_size()
        self.update_layout_scrollregion()
        self._finalize_initial_window_state()

    def save_layout_config(self):
        self.shared_state.log(f"Saving layout configuration to {self.layout_config_file}")
        layout_data = {
            'fullscreen_module': self.fullscreen_module_name,
            'custom_modules_properties': None
        }

        if not self.fullscreen_module_name:
            if hasattr(self.main_layout_manager, 'get_layout_data'):
                custom_module_data = self.main_layout_manager.get_layout_data()
                layout_data['custom_modules_properties'] = custom_module_data
                self.shared_state.log(f"Saved custom layout data: {custom_module_data}", level=logging.DEBUG)
            else:
                self.shared_state.log("CustomLayoutManager has no get_layout_data method. Cannot save layout.", level=logging.WARNING)
        elif self.fullscreen_module_name:
            self.shared_state.log("Saving layout while in fullscreen mode. Main layout properties not saved.", level=logging.INFO)

        try:
            with open(self.layout_config_file, 'w') as f:
                json.dump(layout_data, f, indent=4)
            self.shared_state.log(f"Layout configuration saved to {self.layout_config_file}")
        except IOError as e:
            self.shared_state.log(f"Error saving layout configuration to {self.layout_config_file}: {e}", level=logging.ERROR)
        except Exception as e:
             self.shared_state.log(f"An unexpected error occurred while saving layout: {e}", level=logging.ERROR)

    def load_layout_config(self):
        self.shared_state.log(f"Attempting to load layout configuration from {self.layout_config_file}")
        try:
            if not os.path.exists(self.layout_config_file):
                self.shared_state.log(f"Layout config file '{self.layout_config_file}' not found. Using default layout.", level=logging.INFO)
                self.setup_default_layout()
                return

            with open(self.layout_config_file, 'r') as f:
                layout_data = json.load(f)

            self.shared_state.log("Layout configuration loaded successfully.")

            module_names_to_remove = list(self.loaded_modules.keys())
            for module_name in module_names_to_remove:
                if hasattr(self.main_layout_manager, 'remove_module'):
                    self.main_layout_manager.remove_module(module_name)
                module_data = self.loaded_modules.get(module_name)
                if module_data:
                    if module_data.get('instance'):
                        try:
                            module_data['instance'].on_destroy()
                        except Exception as e:
                            self.shared_state.log(f"Error during on_destroy for module {module_name} in load_layout_config: {e}", level=logging.ERROR)
                    if module_data.get('frame_wrapper') and module_data['frame_wrapper'].winfo_exists():
                        module_data['frame_wrapper'].destroy()
                    del self.loaded_modules[module_name]

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

            self.loaded_modules.clear()

            custom_modules_properties = layout_data.get('custom_modules_properties')
            loaded_any_module_from_config = False

            if custom_modules_properties:
                self.shared_state.log(f"Loading modules from custom_modules_properties: {list(custom_modules_properties.keys())}")

                for module_name in custom_modules_properties.keys():
                    if module_name in self.available_module_classes:
                        if module_name not in self.loaded_modules:
                            self.instantiate_module(module_name, self.main_layout_manager)
                    else:
                        self.shared_state.log(f"Module '{module_name}' from layout config not available in discovered modules.", level=logging.WARNING)

                self.root.update_idletasks()

                for module_name, props in custom_modules_properties.items():
                    if module_name in self.loaded_modules:
                        width = props.get('width', 200)
                        height = props.get('height', 150)
                        self.main_layout_manager.resize_module(module_name, width, height)
                        loaded_any_module_from_config = True
                        self.shared_state.log(f"Applied saved size to {module_name}: w={width}, h={height}", level=logging.DEBUG)

            else:
                self.shared_state.log("No 'custom_modules_properties' found in layout config.", level=logging.INFO)

            fullscreen_module_to_load = layout_data.get('fullscreen_module')
            if fullscreen_module_to_load:
                if fullscreen_module_to_load not in self.loaded_modules:
                    if fullscreen_module_to_load in self.available_module_classes:
                        self.shared_state.log(f"Fullscreen module '{fullscreen_module_to_load}' not in main layout, loading it.", level=logging.INFO)
                        self.instantiate_module(fullscreen_module_to_load, self.main_layout_manager)
                        if custom_modules_properties and fullscreen_module_to_load in custom_modules_properties:
                            props = custom_modules_properties[fullscreen_module_to_load]
                            width = props.get('width', 200)
                            height = props.get('height', 150)
                            self.main_layout_manager.resize_module(fullscreen_module_to_load, width, height)
                    else:
                         self.shared_state.log(f"Fullscreen module '{fullscreen_module_to_load}' not available.", level=logging.ERROR)
                         fullscreen_module_to_load = None

                if fullscreen_module_to_load and fullscreen_module_to_load in self.loaded_modules:
                    self.enter_fullscreen(fullscreen_module_to_load)

            if not loaded_any_module_from_config and not fullscreen_module_to_load and not self.loaded_modules:
                self.shared_state.log("Layout config processed, but no modules loaded and not entering fullscreen. Setting up default layout.", level=logging.INFO)
                self.setup_default_layout()
            else:
                self.update_min_window_size()
                self.update_layout_scrollregion()
                self._finalize_initial_window_state()
        except Exception as e:
            self.shared_state.log(f"Error loading layout configuration: {e}. Using default layout.", level=logging.ERROR)
            current_loaded_module_names = list(self.loaded_modules.keys())
            for name in current_loaded_module_names:
                if hasattr(self.main_layout_manager, 'remove_module'):
                    self.main_layout_manager.remove_module(name)
                mod_data = self.loaded_modules.pop(name, None)
                if mod_data:
                    if mod_data.get('instance'): mod_data['instance'].on_destroy()
                    if mod_data.get('frame_wrapper') and mod_data['frame_wrapper'].winfo_exists(): mod_data['frame_wrapper'].destroy()

            self.loaded_modules.clear()
            self.setup_default_layout()

    def on_closing(self):
        self.shared_state.log("Application closing...")
        self.save_layout_config()
        for module_name, module_data in list(self.loaded_modules.items()):
            if module_data and module_data.get('instance'):
                try:
                    module_data['instance'].on_destroy()
                except Exception as e:
                    self.shared_state.log(f"Error during on_destroy for module {module_name}: {e}", level=logging.ERROR)

        self.shared_state.save_config()
        self.root.destroy()

    def show_context_menu(self, event):
        self.context_menu.delete(0, tk.END)

        if self.fullscreen_module_name:
            self.context_menu.add_command(label="Exit Fullscreen to manage modules", command=self.exit_fullscreen)
        else:
            self.context_menu.add_command(label="Toggle Module Visibility:", state=tk.DISABLED)
            self.context_menu.add_separator()

            visible_module_wrappers = []
            if not self.fullscreen_module_name:
                for mod_name, mod_data in self.loaded_modules.items():
                    if mod_data.get('frame_wrapper') and mod_data['frame_wrapper'].winfo_exists():
                        visible_module_wrappers.append(mod_data['frame_wrapper'])


            for module_name in sorted(self.available_module_classes.keys()):
                is_visible = False
                if module_name in self.loaded_modules and not self.fullscreen_module_name:
                    mod_data = self.loaded_modules[module_name]
                    if mod_data.get('instance') and mod_data.get('frame_wrapper') and mod_data.get('frame_wrapper').winfo_exists():
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
        if module_name in self.loaded_modules and not self.fullscreen_module_name:
            mod_data = self.loaded_modules[module_name]
            if mod_data and mod_data.get('instance'):
                wrapper_to_check = mod_data.get('frame_wrapper')
                if wrapper_to_check and wrapper_to_check.winfo_exists():
                    is_visible = True

        if is_visible:
            self.hide_module(module_name)
        else:
            self.shared_state.log(f"Showing module: {module_name}")
            if module_name in self.available_module_classes:
                self.instantiate_module(module_name, self.main_layout_manager)
                self.root.update_idletasks()
            else:
                self.shared_state.log(f"Module '{module_name}' cannot be shown, not found in available modules.", level=logging.WARNING)

    def hide_module(self, module_name: str):
        self.shared_state.log(f"Hiding module: {module_name} via close button/hide action.")
        if module_name in self.loaded_modules:
            module_data = self.loaded_modules[module_name]
            frame_wrapper = module_data.get('frame_wrapper')
            instance = module_data.get('instance')

            if frame_wrapper and frame_wrapper.winfo_exists():
                self.main_layout_manager.remove_module(module_name)

            if instance:
                try:
                    instance.on_destroy()
                except Exception as e:
                    self.shared_state.log(f"Error during on_destroy for module {module_name} when hiding: {e}", "ERROR")

            if frame_wrapper and frame_wrapper.winfo_exists():
                frame_wrapper.destroy()

            del self.loaded_modules[module_name]
            self.shared_state.log(f"Module '{module_name}' hidden and instance destroyed.")

            self.update_min_window_size()
            self.update_layout_scrollregion()

        else:
            self.shared_state.log(f"Module '{module_name}' not found or not loaded, cannot hide.", "WARNING")

    def start_drag(self, event, module_name):
        self.shared_state.log(f"Start dragging module: {module_name}", level=logging.DEBUG)
        self.dragged_module_name = module_name
        self.drag_start_widget = event.widget

        dragged_frame_wrapper = self.loaded_modules[self.dragged_module_name].get('frame_wrapper')
        if dragged_frame_wrapper:
            self.original_dragged_module_relief = dragged_frame_wrapper.cget("relief")
            dragged_frame_wrapper.config(relief=tk.SOLID, borderwidth=2)

        self.root.config(cursor="fleur")
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.end_drag)
        
    def on_drag(self, event):
        if not self.dragged_module_name:
            return

        if self.drop_target_module_frame_wrapper and self.drop_target_module_frame_wrapper.winfo_exists():
            if self.drop_target_module_frame_wrapper != self.loaded_modules[self.dragged_module_name].get('frame_wrapper'):
                 try:
                    self.drop_target_module_frame_wrapper.config(borderwidth=1)
                 except tk.TclError: pass

        x_root, y_root = event.x_root, event.y_root
        current_target_frame_wrapper = None

        for module_name_iter, module_data_iter in self.loaded_modules.items():
            if module_name_iter == self.dragged_module_name:
                continue

            frame_wrapper_iter = module_data_iter.get('frame_wrapper')
            if frame_wrapper_iter and frame_wrapper_iter.winfo_exists():
                x_min = frame_wrapper_iter.winfo_rootx()
                x_max = x_min + frame_wrapper_iter.winfo_width()
                y_min = frame_wrapper_iter.winfo_rooty()
                y_max = y_min + frame_wrapper_iter.winfo_height()

                if x_min <= x_root < x_max and y_min <= y_root < y_max:
                    current_target_frame_wrapper = frame_wrapper_iter
                    break

        if current_target_frame_wrapper:
            self.drop_target_module_frame_wrapper = current_target_frame_wrapper
            try:
                self.drop_target_module_frame_wrapper.config(borderwidth=3)
            except tk.TclError: pass
        else:
            self.drop_target_module_frame_wrapper = None

    def end_drag(self, event):
        if not self.dragged_module_name:
            self.root.config(cursor="")
            self.root.unbind("<B1-Motion>")
            self.root.unbind("<ButtonRelease-1>")
            return

        self.shared_state.log(f"End dragging module: {self.dragged_module_name}. Target wrapper: {self.drop_target_module_frame_wrapper}", level=logging.DEBUG)
        self.root.config(cursor="")
        self.root.unbind("<B1-Motion>")
        self.root.unbind("<ButtonRelease-1>")

        dragged_frame_wrapper = self.loaded_modules[self.dragged_module_name].get('frame_wrapper')

        if dragged_frame_wrapper and dragged_frame_wrapper.winfo_exists() and self.original_dragged_module_relief:
            try:
                dragged_frame_wrapper.config(relief=self.original_dragged_module_relief, borderwidth=1)
            except tk.TclError: pass

        if self.drop_target_module_frame_wrapper and self.drop_target_module_frame_wrapper.winfo_exists():
            try:
                self.drop_target_module_frame_wrapper.config(borderwidth=1)
            except tk.TclError: pass

        if self.drop_target_module_frame_wrapper and \
           self.drop_target_module_frame_wrapper != dragged_frame_wrapper and \
           self.dragged_module_name:

            target_module_name = None
            for name, data in self.loaded_modules.items():
                if data.get('frame_wrapper') == self.drop_target_module_frame_wrapper:
                    target_module_name = name
                    break

            if target_module_name and target_module_name != self.dragged_module_name:
                self.shared_state.log(f"Attempting to move '{self.dragged_module_name}' before '{target_module_name}'")
                self.main_layout_manager.move_module_before(self.dragged_module_name, target_module_name)
            elif not target_module_name:
                 self.main_layout_manager.move_module_before(self.dragged_module_name, None)
                 self.shared_state.log(f"Moved '{self.dragged_module_name}' to the end (no specific target module identified for wrapper).", level=logging.WARNING)

        elif self.dragged_module_name and not self.drop_target_module_frame_wrapper :
            self.shared_state.log(f"'{self.dragged_module_name}' dropped on empty space, moving to end.")
            self.main_layout_manager.move_module_before(self.dragged_module_name, None)

        else:
            self.shared_state.log(f"Drag ended for {self.dragged_module_name} without a valid different drop target.", "DEBUG")

        self.dragged_module_name = None
        self.drag_start_widget = None
        self.drop_target_module_frame_wrapper = None
        self.original_dragged_module_relief = None

    def toggle_fullscreen(self, module_name):
        if self.fullscreen_module_name:
            if self.fullscreen_module_name == module_name:
                self.exit_fullscreen()
            else:
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

        self.main_layout_manager.pack_forget()

        fs_module_wrapper.pack(fill=tk.BOTH, expand=True, before=self.main_layout_manager)

        if fs_module_instance:
            fs_module_instance.fullscreen_button.config(text="Exit")

    def exit_fullscreen(self):
        if not self.fullscreen_module_name:
            return

        fs_module_data = self.loaded_modules[self.fullscreen_module_name]
        fs_module_wrapper = fs_module_data['frame_wrapper']
        fs_module_instance = fs_module_data['instance']

        self.shared_state.log(f"Exiting fullscreen for module: {self.fullscreen_module_name}", logging.INFO)

        fs_module_wrapper.pack_forget()

        self.main_layout_manager.pack(fill=tk.BOTH, expand=True)

        if fs_module_instance:
            fs_module_instance.fullscreen_button.config(text="FS")

        self.fullscreen_module_name = None
        self.store_main_pane_children.clear()

if __name__ == "__main__":
    import sys
    if '__main__' in sys.modules:
        sys.modules['main'] = sys.modules['__main__']

    root = tk.Tk()
    app = ModularGUI(root)
    root.mainloop()

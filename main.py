import tkinter as tk
from tkinter import ttk
import os
import importlib.util
from shared_state import SharedState
import logging
import json

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

        self.maximize_button = ttk.Button(
            self.title_bar_frame, text="⬜", width=3,
            command=self.toggle_maximize_action
        )
        self.maximize_button.pack(side=tk.RIGHT, padx=(0, 2))

        self.resize_handle = ttk.Sizegrip(self.frame)
        self.resize_handle.pack(side=tk.BOTTOM, anchor=tk.SE)
        self.resize_handle.bind("<ButtonPress-1>", self._on_resize_start)
        self.resize_handle.bind("<B1-Motion>", self._on_resize_motion)
        self.resize_handle.bind("<ButtonRelease-1>", self._on_resize_release)

        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0

        self.is_maximized = False

        self.shared_state.log(f"Module '{self.module_name}' initialized with title bar.")

    def close_module_action(self):
        if self.gui_manager:
            self.shared_state.log(f"Close button clicked for module '{self.module_name}'.")
            self.gui_manager.hide_module(self.module_name)
        else:
            self.shared_state.log(f"Cannot close module '{self.module_name}': gui_manager not available.", "ERROR")

    def toggle_maximize_action(self):
        if not self.gui_manager:
            self.shared_state.log(f"Cannot maximize module '{self.module_name}': gui_manager not available.", "ERROR")
            return
        if not self.is_maximized:
            self.gui_manager.maximize_module(self.module_name)
        else:
            self.gui_manager.restore_modules()

    def _on_resize_start(self, event):
        if self.gui_manager and hasattr(self.gui_manager, 'window_size_fixed_after_init') and self.gui_manager.window_size_fixed_after_init and hasattr(self.gui_manager, 'root') and hasattr(self.gui_manager.root, 'maxsize') and hasattr(self.gui_manager.root, 'winfo_width') and hasattr(self.gui_manager.root, 'winfo_height'):
            self.gui_manager.is_module_resizing = True
            self.gui_manager.root_maxsize_backup = self.gui_manager.root.maxsize()
            current_width = self.gui_manager.root.winfo_width()
            current_height = self.gui_manager.root.winfo_height()
            self.gui_manager.window_geometry_before_module_resize = f"{current_width}x{current_height}"
            self.gui_manager.root.maxsize(current_width, current_height)
            if hasattr(self.gui_manager, 'shared_state'):
                self.gui_manager.shared_state.log(
                    f"Module resize started: Geometry '{self.gui_manager.window_geometry_before_module_resize}' stored. Maxsize temporarily set to {current_width}x{current_height}.", "DEBUG"
                )
        elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
             if not (hasattr(self.gui_manager, 'window_size_fixed_after_init') and self.gui_manager.window_size_fixed_after_init):
                 self.gui_manager.shared_state.log("Module resize started: window_size_fixed_after_init is False, not modifying window constraints.", "DEBUG")
             else:
                 self.gui_manager.shared_state.log("Module resize started: Could not set temporary window constraints (root or methods missing).", "WARNING")

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
        delta_y = event.x_root - self.resize_start_x

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
            if hasattr(self.gui_manager, "save_layout_config"):
                self.gui_manager.save_layout_config()
        if self.gui_manager:
            self.gui_manager.update_layout_scrollregion()

        if self.gui_manager and hasattr(self.gui_manager, 'is_module_resizing') and self.gui_manager.is_module_resizing:
            if hasattr(self.gui_manager, 'root_maxsize_backup') and self.gui_manager.root_maxsize_backup is not None and hasattr(self.gui_manager, 'root') and hasattr(self.gui_manager.root, 'maxsize'):
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

            if hasattr(self.gui_manager, 'window_geometry_before_module_resize') and self.gui_manager.window_geometry_before_module_resize is not None and hasattr(self.gui_manager, 'root') and hasattr(self.gui_manager, 'geometry'):
                self.gui_manager.root.geometry(self.gui_manager.window_geometry_before_module_resize)
                if hasattr(self.gui_manager, 'shared_state'):
                    self.gui_manager.shared_state.log(
                        f"Module resize ended: Main window geometry restored to {self.gui_manager.window_geometry_before_module_resize}.", "DEBUG"
                    )
            elif self.gui_manager and hasattr(self.gui_manager, 'shared_state'):
                 self.gui_manager.shared_state.log(
                    "Module resize ended: No stored geometry found to restore.", "WARNING"
                )

            self.gui_manager.is_module_resizing = False
            if hasattr(self.gui_manager, 'root_maxsize_backup'):
                self.gui_manager.root_maxsize_backup = None
            if hasattr(self.gui_manager, 'window_geometry_before_module_resize'):
                self.gui_manager.window_geometry_before_module_resize = None

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

    def add_module(self, module_frame, module_name, width, height, defer_reflow=False):
        self.modules[module_name] = {
            'frame': module_frame,
            'name': module_name,
            'width': width,
            'height': height,
        }
        if not defer_reflow:
            self.reflow_layout()
        else:
            logging.debug(f"Add_module for {module_name} deferred reflow.")

    def remove_module(self, module_name):
        if module_name in self.modules:
            module_info = self.modules.pop(module_name)
            module_info['frame'].place_forget()
            self.reflow_layout()
        else:
            logging.getLogger().warning(f"CustomLayoutManager: Attempted to remove non-existent module '{module_name}'.")

    def resize_module(self, module_name, width, height, defer_reflow=False):
        if module_name in self.modules:
            self.modules[module_name]['width'] = max(10, width)
            self.modules[module_name]['height'] = max(10, height)
            if not defer_reflow:
                self.reflow_layout()
            else:
                logging.debug(f"Resize_module for {module_name} deferred reflow.")
        else:
            logging.warning(f"CustomLayoutManager: Attempted to resize non-existent module: {module_name}")

    def _is_overlapping(self, r1_x, r1_y, r1_w, r1_h, r2_x, r2_y, r2_w, r2_h) -> bool:
        return r1_x < r2_x + r2_w and \
               r1_x + r1_w > r2_x and \
               r1_y < r2_y + r2_h and \
               r1_y + r1_h > r2_y

    def reflow_layout(self, simulate=False, module_configs_override=None):
        logging.info("Reflowing layout with new optimized algorithm.")
        placed_modules_rects = []

        if module_configs_override is not None:
            module_iterator = module_configs_override
        else:
            module_iterator = list(self.modules.values())

        container_width = self.current_canvas_width
        if container_width <= 1:
             container_width = self.canvas_parent.winfo_width()
        if container_width <= 1:
             container_width = 800

        min_module_dim = 10
        module_margin_x = 5
        module_margin_y = 5

        current_x = 0
        current_y = 0
        row_height = 0
        max_x_coord = 0
        max_y_coord = 0

        for module_info in module_iterator:
            module_name = module_info['name']
            current_w = max(min_module_dim, module_info['width'])
            current_h = max(min_module_dim, module_info['height'])

            if current_x > 0 and (current_x + current_w) > container_width:
                current_y += row_height + module_margin_y
                current_x = 0
                row_height = 0
            
            final_x = current_x
            final_y = current_y

            module_info['x'] = final_x
            module_info['y'] = final_y

            if not simulate:
                if 'frame' in module_info and module_info['frame']:
                    module_info['frame'].place(x=final_x, y=final_y, width=current_w, height=current_h)
                elif not module_configs_override:
                    logging.warning(f"CustomLayoutManager: Frame not found for module {module_name} during actual placement.")

            placed_modules_rects.append({'name': module_name, 'x': final_x, 'y': final_y, 'w': current_w, 'h': current_h})

            current_x += current_w + module_margin_x
            row_height = max(row_height, current_h)

            max_x_coord = max(max_x_coord, final_x + current_w)
            max_y_coord = max(max_y_coord, final_y + current_h)

        self.last_calculated_content_width = max_x_coord
        self.last_calculated_content_height = max_y_coord

        layout_manager_own_width = self.current_canvas_width
        if layout_manager_own_width <= 1:
            layout_manager_own_width = self.canvas_parent.winfo_width()
            if layout_manager_own_width <= 1:
                layout_manager_own_width = 800

        effective_height = self.last_calculated_content_height if self.last_calculated_content_height > 0 else 10
        self.config(width=layout_manager_own_width, height=effective_height)
        logging.debug(f"Reflow complete. Content WxH: {self.last_calculated_content_width}x{self.last_calculated_content_height}. LM WxH: {layout_manager_own_width}x{effective_height}")

    def scale_modules(self, scale_ratio):
        for module_info in self.modules.values():
            module_info['width'] = int(module_info['width'] * scale_ratio)
            module_info['height'] = int(module_info['height'] * scale_ratio)
        self.reflow_layout()

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

        if target_module_name is None or target_module_name == module_to_move_name or target_module_name not in self.modules:
            for name, info in self.modules.items():
                new_modules_dict[name] = info
            new_modules_dict[module_to_move_name] = moved_item_info
        else:
            inserted = False
            for name, info in self.modules.items():
                if name == target_module_name:
                    new_modules_dict[module_to_move_name] = moved_item_info
                    inserted = True
                new_modules_dict[name] = info
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
    CONFIG_FILE = "layout_config.json"

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

        self.shared_state = SharedState()
        self.shared_state.log("ModularGUI initialized.")

        self.modules_dir = "modules"
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            self.shared_state.log(f"Created modules directory: {self.modules_dir}")

        self.loaded_modules = {}
        self.module_instance_counters = {}

        self.maximized_module_name = None
        self._pre_maximize_layout = None

        self.dragged_module_name = None
        self.drag_start_widget = None
        self.drop_target_module_frame_wrapper = None 
        self.original_dragged_module_relief = None
        
        self.ghost_module_frame = None
        self.ghost_canvas_window_id = None
        self.last_preview_target_module_name = None

        self.is_module_resizing = False
        self.root_maxsize_backup = None
        self.window_geometry_before_module_resize = None

        self.resize_debounce_timer = None
        self.resize_debounce_delay = 250

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

        self.setup_default_layout()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _finalize_initial_window_state(self):
        self.root.update_idletasks()
        self.window_size_fixed_after_init = True
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
        if self.resize_debounce_timer is not None:
            self.root.after_cancel(self.resize_debounce_timer)

        self.resize_debounce_timer = self.root.after(
            self.resize_debounce_delay,
            lambda e=event: self._handle_canvas_resize_debounced(e)
        )

    def _handle_canvas_resize_debounced(self, event):
        self.shared_state.log(f"Debounced canvas resize handling. New width: {event.width}", "DEBUG")
        canvas_width = event.width

        if self.maximized_module_name and self.maximized_module_name in self.loaded_modules:
            canvas_height = self.canvas.winfo_height()
            self.main_layout_manager.config(width=canvas_width, height=canvas_height)
            self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width, height=canvas_height)
            mod_data = self.loaded_modules[self.maximized_module_name]
            frame_wrapper = mod_data.get('frame_wrapper')
            if frame_wrapper and frame_wrapper.winfo_exists():
                frame_wrapper.place(x=0, y=0, width=canvas_width, height=canvas_height)
            self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        else:
            prev_width = 0
            if hasattr(self.main_layout_manager, 'current_canvas_width'):
                prev_width = self.main_layout_manager.current_canvas_width
                self.main_layout_manager.current_canvas_width = canvas_width

            self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width)

            if prev_width > 0 and canvas_width > 0 and prev_width != canvas_width:
                scale_ratio = canvas_width / prev_width
                self.shared_state.log(f"Debounced resize: Scaling modules. Prev width: {prev_width}, New width: {canvas_width}, Ratio: {scale_ratio}", "DEBUG")
                if hasattr(self.main_layout_manager, 'scale_modules'):
                    self.main_layout_manager.scale_modules(scale_ratio)
            elif hasattr(self.main_layout_manager, 'reflow_layout'):
                self.shared_state.log(f"Debounced resize: Reflowing layout. Prev width: {prev_width}, New width: {canvas_width}", "DEBUG")
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

    def _generate_instance_id(self, module_name):
        count = self.module_instance_counters.get(module_name, 1)
        instance_id = f"{module_name}#{count}"
        self.module_instance_counters[module_name] = count + 1
        return instance_id

    def add_module_from_menu(self, module_name: str):
        self.shared_state.log(f"Attempting to add module '{module_name}' from menu.")

        if module_name in self.available_module_classes:
            children = self.main_layout_manager.winfo_children()
            if len(children) == 1 and isinstance(children[0], ttk.Label):
                if "No modules available" in children[0].cget("text") or \
                   "No modules displayed" in children[0].cget("text"):
                    children[0].destroy()
                    self.shared_state.log("Removed default placeholder label.", "DEBUG")

            self.instantiate_module(module_name, self.main_layout_manager)
            self.main_layout_manager.reflow_layout()
            self.root.update_idletasks()
            self.update_min_window_size()
            self.update_layout_scrollregion()
            self.shared_state.log(f"Module '{module_name}' instantiated from menu and layout reflowed.")
            self.save_layout_config()
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
        instance_id = self._generate_instance_id(module_name)

        frame_wrapper = ttk.Frame(parent_layout_manager, relief=tk.SUNKEN, borderwidth=1)

        try:
            module_instance = ModuleClass(frame_wrapper, self.shared_state, instance_id, self)
            module_instance.get_frame().pack(fill=tk.BOTH, expand=True)

            self.loaded_modules[instance_id] = {
                'class': ModuleClass,
                'instance': module_instance,
                'frame_wrapper': frame_wrapper,
                'module_name': module_name,
                'instance_id': instance_id
            }

            drag_handle_widget = module_instance.drag_handle_label
            drag_handle_widget.bind("<ButtonPress-1>", lambda event, iid=instance_id: self.start_drag(event, iid))

            initial_width, initial_height = 200, 150
            parent_layout_manager.add_module(frame_wrapper, instance_id, initial_width, initial_height, defer_reflow=True)
            self.shared_state.log(f"Instantiated module '{instance_id}', reflow deferred.")
            return frame_wrapper
        except Exception as e:
            self.shared_state.log(f"Error instantiating module {module_name}: {e}", level=logging.ERROR)
            if frame_wrapper.winfo_exists():
                frame_wrapper.destroy()
            return None

    def setup_default_layout(self):
        self.shared_state.log("Setting up default layout...")
        self.update_min_window_size()
        self.update_layout_scrollregion()
        self._finalize_initial_window_state()
        self.load_layout_config()

    def save_layout_config(self):
        config_path = os.path.join(os.getcwd(), self.CONFIG_FILE)
        if not self.loaded_modules:
            print("[SAVE] No modules loaded, skip saving layout config.")
            # 寫入空 config
            empty_config = {
                "modules": [],
                "maximized_module_name": None,
                "module_order": []
            }
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(empty_config, f, indent=2)
                print(f"[SAVE] Layout config cleared.")
            except Exception as e:
                print(f"[SAVE][ERROR] Failed to clear layout config: {e}")
            return
        config = {
            "modules": [],
            "maximized_module_name": self.maximized_module_name,
            "module_order": []
        }
        current_instance_ids = set(self.loaded_modules.keys()) & set(self.main_layout_manager.modules.keys())
        config["module_order"] = [iid for iid in self.main_layout_manager.modules.keys() if iid in current_instance_ids]
        for iid in config["module_order"]:
            mod_data = self.loaded_modules.get(iid)
            info = self.main_layout_manager.get_module_info(iid)
            if mod_data:
                config["modules"].append({
                    "module_name": mod_data["module_name"],
                    "instance_id": iid,
                    "width": info["width"] if info else 200,
                    "height": info["height"] if info else 150,
                })
        print(f"[SAVE] Writing layout config to: {config_path}")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            print(f"[SAVE] Layout config written.")
        except Exception as e:
            print(f"[SAVE][ERROR] Failed to write layout config: {e}")
    def load_layout_config(self):
        config_path = os.path.join(os.getcwd(), self.CONFIG_FILE)
        print(f"[LOAD] Try loading layout config from: {config_path}")
        if not os.path.exists(config_path):
            print("[LOAD] No layout config file found, using default layout.")
            return False
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            for iid in list(self.loaded_modules.keys()):
                self.hide_module(iid)
            max_counters = {}
            for mod in config.get("modules", []):
                module_name = mod["module_name"]
                iid = mod["instance_id"]
                if "#" in iid:
                    base, num = iid.rsplit("#", 1)
                    try:
                        num = int(num)
                        if base not in max_counters or num > max_counters[base]:
                            max_counters[base] = num
                    except Exception:
                        pass
            for base, max_num in max_counters.items():
                self.module_instance_counters[base] = max_num + 1

            module_order = config.get("module_order")
            if module_order:
                iid_to_mod = {mod["instance_id"]: mod for mod in config.get("modules", [])}
                ordered_mods = [iid_to_mod[iid] for iid in module_order if iid in iid_to_mod]
            else:
                ordered_mods = config.get("modules", [])

            for mod in ordered_mods:
                module_name = mod["module_name"]
                iid = mod["instance_id"]
                width = mod.get("width", 200)
                height = mod.get("height", 150)
                if module_name in self.available_module_classes:
                    old_counter = self.module_instance_counters.get(module_name, 1)
                    try:
                        if "#" in iid:
                            base, num = iid.rsplit("#", 1)
                            num = int(num)
                            self.module_instance_counters[module_name] = num
                    except Exception:
                        pass
                    frame_wrapper = self.instantiate_module(module_name, self.main_layout_manager)
                    self.module_instance_counters[module_name] = max(old_counter, max_counters.get(module_name, 0) + 1)
                    if frame_wrapper:
                        self.loaded_modules[iid] = self.loaded_modules.pop(list(self.loaded_modules.keys())[-1])
                        self.loaded_modules[iid]["instance_id"] = iid
                        self.main_layout_manager.resize_module(iid, width, height, defer_reflow=True)
            self.main_layout_manager.reflow_layout()
            self.update_min_window_size()
            self.update_layout_scrollregion()
            maximized = config.get("maximized_module_name")
            if maximized and maximized in self.loaded_modules:
                self.maximize_module(maximized)
            print("[LOAD] Layout config loaded and restored.")
            return True
        except Exception as e:
            print(f"[LOAD][ERROR] Failed to load layout config: {e}")
            return False

    def on_closing(self):
        self.shared_state.log("Application closing...")
        for module_name, module_data in list(self.loaded_modules.items()):
            if module_data and module_data.get('instance'):
                try:
                    module_data['instance'].on_destroy()
                except Exception as e:
                    self.shared_state.log(f"Error during on_destroy for module {module_name}: {e}", level=logging.ERROR)

        self.root.destroy()

    def show_context_menu(self, event):
        self.context_menu.delete(0, tk.END)

        self.context_menu.add_command(label="Toggle Module Visibility:", state=tk.DISABLED)
        self.context_menu.add_separator()

        for instance_id, mod_data in self.loaded_modules.items():
            module_name = mod_data.get('module_name', instance_id)
            is_visible = mod_data.get('frame_wrapper') and mod_data.get('frame_wrapper').winfo_exists()
            prefix = "[x]" if is_visible else "[ ]"
            self.context_menu.add_command(
                label=f"{prefix} {instance_id}",
                command=lambda iid=instance_id: self.toggle_module_visibility(iid)
            )

        self.context_menu.add_separator()
        for module_name in sorted(self.available_module_classes.keys()):
            self.context_menu.add_command(
                label=f"Add {module_name}",
                command=lambda mn=module_name: self.add_module_from_menu(mn)
            )

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def toggle_module_visibility(self, instance_id):
        self.shared_state.log(f"Toggle visibility for {instance_id}", level=logging.DEBUG)
        is_visible = False
        wrapper_to_check = None
        if instance_id in self.loaded_modules:
            mod_data = self.loaded_modules[instance_id]
            wrapper_to_check = mod_data.get('frame_wrapper')
            if wrapper_to_check and wrapper_to_check.winfo_exists():
                is_visible = True

        if is_visible:
            self.hide_module(instance_id)
        else:
            self.shared_state.log(f"Showing module: {instance_id}")

    def hide_module(self, instance_id: str):
        if self.maximized_module_name == instance_id:
            self.restore_modules()
            if self.maximized_module_name is None and instance_id in self.loaded_modules:
                self.hide_module(instance_id)
            return
        else:
            self.shared_state.log(f"Hiding module: {instance_id} via close button/hide action.")
            if instance_id in self.loaded_modules:
                module_data = self.loaded_modules[instance_id]
                frame_wrapper = module_data.get('frame_wrapper')
                instance = module_data.get('instance')

                if frame_wrapper and frame_wrapper.winfo_exists():
                    self.main_layout_manager.remove_module(instance_id)

                if instance:
                    try:
                        instance.on_destroy()
                    except Exception as e:
                        self.shared_state.log(f"Error during on_destroy for module {instance_id} when hiding: {e}", "ERROR")

                if frame_wrapper and frame_wrapper.winfo_exists():
                    frame_wrapper.destroy()

                del self.loaded_modules[instance_id]
                self.shared_state.log(f"Module '{instance_id}' hidden and instance destroyed.")

                self.update_min_window_size()
                self.update_layout_scrollregion()
                self.save_layout_config()
            else:
                self.shared_state.log(f"Module '{instance_id}' not found or not loaded, cannot hide.", "WARNING")

    def start_drag(self, event, instance_id):
        self.shared_state.log(f"Start dragging module: {instance_id}", level=logging.DEBUG)
        self.dragged_module_name = instance_id
        self.drag_start_widget = event.widget

        if self.dragged_module_name not in self.main_layout_manager.modules or \
           self.dragged_module_name not in self.loaded_modules:
            self.shared_state.log(f"Dragged module {self.dragged_module_name} not found in layout manager or loaded modules.", "ERROR")
            self.dragged_module_name = None
            return

        dragged_module_layout_info = self.main_layout_manager.modules[self.dragged_module_name]
        original_frame_wrapper = self.loaded_modules[self.dragged_module_name]['frame_wrapper']

        original_width = dragged_module_layout_info['width']
        original_height = dragged_module_layout_info['height']
        original_x = dragged_module_layout_info['x']
        original_y = dragged_module_layout_info['y']
        
        if original_frame_wrapper:
            self.original_dragged_module_relief = original_frame_wrapper.cget("relief")
        
        self.ghost_module_frame = ttk.Frame(self.canvas, width=original_width, height=original_height)
        self.ghost_module_frame.configure(relief=tk.RIDGE, borderwidth=2)
        ttk.Label(self.ghost_module_frame, text=f"Preview: {self.dragged_module_name}").pack(expand=True, fill=tk.BOTH)

        self.ghost_canvas_window_id = self.canvas.create_window(
            original_x, original_y, 
            window=self.ghost_module_frame, 
            anchor=tk.NW, 
            width=original_width, 
            height=original_height
        )
        self.shared_state.log(f"Ghost created at {original_x},{original_y} with ID {self.ghost_canvas_window_id}", "DEBUG")

        if original_frame_wrapper:
            original_frame_wrapper.place_forget()
            self.shared_state.log(f"Original module {self.dragged_module_name} hidden.", "DEBUG")

        self.last_preview_target_module_name = None 

        self.root.config(cursor="fleur")
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.end_drag)
        
    def on_drag(self, event):
        if not self.dragged_module_name or not self.ghost_canvas_window_id or \
           self.dragged_module_name not in self.main_layout_manager.modules:
            return

        try:
            mouse_x_on_canvas = event.x_root - self.canvas.winfo_rootx()
            mouse_y_on_canvas = event.y_root - self.canvas.winfo_rooty()
        except tk.TclError: 
            return

        other_modules_info = []
        for name, module_props in self.main_layout_manager.modules.items():
            if name == self.dragged_module_name:
                continue
            if module_props and module_props.get('frame') and module_props['frame'].winfo_exists() and \
               all(k in module_props for k in ['x', 'y', 'width', 'height']):
                other_modules_info.append({
                    'name': name,
                    'x': module_props['x'],
                    'y': module_props['y'],
                    'width': module_props['width'],
                    'height': module_props['height'],
                })
        
        self.last_preview_target_module_name = None

        if other_modules_info: 
            modules_sorted_y = sorted(other_modules_info, key=lambda m: (m['y'], m['x']))
            best_h_target = {'dist': float('inf'), 'target_name': None}

            if modules_sorted_y:
                mod_y_first = modules_sorted_y[0]
                if mouse_x_on_canvas >= mod_y_first['x'] and mouse_x_on_canvas <= mod_y_first['x'] + mod_y_first['width']:
                    dist = abs(mouse_y_on_canvas - mod_y_first['y'])
                    if dist < best_h_target['dist']:
                        best_h_target['dist'] = dist
                        best_h_target['target_name'] = mod_y_first['name']
            
            for i, mod_y in enumerate(modules_sorted_y):
                gap_line_y = mod_y['y'] + mod_y['height']
                if mouse_x_on_canvas >= mod_y['x'] and mouse_x_on_canvas <= mod_y['x'] + mod_y['width']:
                    dist = abs(mouse_y_on_canvas - gap_line_y)
                    if dist < best_h_target['dist']:
                        best_h_target['dist'] = dist
                        best_h_target['target_name'] = modules_sorted_y[i+1]['name'] if (i + 1) < len(modules_sorted_y) else None

            modules_sorted_x = sorted(other_modules_info, key=lambda m: (m['x'], m['y']))
            best_v_target = {'dist': float('inf'), 'target_name': None}

            if modules_sorted_x:
                mod_x_first = modules_sorted_x[0]
                if mouse_y_on_canvas >= mod_x_first['y'] and mouse_y_on_canvas <= mod_x_first['y'] + mod_x_first['height']:
                    dist = abs(mouse_x_on_canvas - mod_x_first['x'])
                    if dist < best_v_target['dist']:
                        best_v_target['dist'] = dist
                        best_v_target['target_name'] = mod_x_first['name']

            for i, mod_x in enumerate(modules_sorted_x):
                gap_line_x = mod_x['x'] + mod_x['width']
                if mouse_y_on_canvas >= mod_x['y'] and mouse_y_on_canvas <= mod_x['y'] + mod_x_first['height']:
                    dist = abs(mouse_x_on_canvas - gap_line_x)
                    if dist < best_v_target['dist']:
                        best_v_target['dist'] = dist
                        best_v_target['target_name'] = modules_sorted_x[i+1]['name'] if (i + 1) < len(modules_sorted_x) else None
            
            final_target_name = None
            h_target_is_valid = best_h_target['dist'] != float('inf')
            v_target_is_valid = best_v_target['dist'] != float('inf')

            if h_target_is_valid and v_target_is_valid:
                if best_h_target['dist'] <= best_v_target['dist']: 
                    final_target_name = best_h_target['target_name']
                else:
                    final_target_name = best_v_target['target_name']
            elif h_target_is_valid:
                final_target_name = best_h_target['target_name']
            elif v_target_is_valid:
                final_target_name = best_v_target['target_name']
            
            self.last_preview_target_module_name = final_target_name

        self.shared_state.log("Optimized on_drag: Updating ghost position without full layout simulation.", "DEBUG")
        new_x, new_y = mouse_x_on_canvas, mouse_y_on_canvas

        if self.last_preview_target_module_name and self.last_preview_target_module_name in self.main_layout_manager.modules:
            target_props = self.main_layout_manager.modules[self.last_preview_target_module_name]
            new_x = target_props.get('x', mouse_x_on_canvas)
            new_y = target_props.get('y', mouse_y_on_canvas)
            self.shared_state.log(f"Ghost target: {self.last_preview_target_module_name} at ({new_x},{new_y})", "DEBUG")
        else:
            self.shared_state.log(f"Ghost follows mouse to ({new_x},{new_y})", "DEBUG")

        if self.ghost_canvas_window_id:
            self.canvas.coords(self.ghost_canvas_window_id, new_x, new_y)

    def end_drag(self, event):
        if not self.dragged_module_name:
            self.root.config(cursor="")
            self.root.unbind("<B1-Motion>")
            self.root.unbind("<ButtonRelease-1>")
            return

        if self.ghost_canvas_window_id:
            self.canvas.delete(self.ghost_canvas_window_id)
            self.ghost_canvas_window_id = None
        if self.ghost_module_frame: 
            self.ghost_module_frame = None

        self.shared_state.log(f"End dragging module: {self.dragged_module_name}. Target before: {self.last_preview_target_module_name}", level=logging.DEBUG)
        
        dragged_module_data = self.loaded_modules.get(self.dragged_module_name)
        if dragged_module_data:
            original_frame_wrapper = dragged_module_data.get('frame_wrapper')
            if original_frame_wrapper and hasattr(self, 'original_dragged_module_relief') and self.original_dragged_module_relief:
                try:
                    original_frame_wrapper.config(relief=self.original_dragged_module_relief, borderwidth=1)
                except tk.TclError as e:
                    self.shared_state.log(f"Error resetting relief for {self.dragged_module_name}: {e}", "WARNING")
        
        if self.dragged_module_name:
            self.main_layout_manager.move_module_before(
                self.dragged_module_name, 
                self.last_preview_target_module_name
            )
            self.update_layout_scrollregion()
            self.update_min_window_size()
            self.save_layout_config()

    def maximize_module(self, instance_id):
        if self.maximized_module_name == instance_id:
            return

        self.shared_state.log(f"Maximizing module: {instance_id}", "INFO")
        self._pre_maximize_layout = self.main_layout_manager.get_layout_data()
        self.maximized_module_name = instance_id

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.main_layout_manager.config(width=canvas_width, height=canvas_height)
        self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width, height=canvas_height)

        for iid, mod_data in self.loaded_modules.items():
            frame_wrapper = mod_data.get('frame_wrapper')
            instance = mod_data.get('instance')
            if iid == instance_id:
                if frame_wrapper and frame_wrapper.winfo_exists():
                    frame_wrapper.lift()
                    frame_wrapper.place(x=0, y=0, width=canvas_width, height=canvas_height)
                if instance:
                    instance.is_maximized = True
            else:
                if frame_wrapper and frame_wrapper.winfo_exists():
                    frame_wrapper.place_forget()
                if instance:
                    instance.is_maximized = False

        self.canvas.config(scrollregion=(0, 0, canvas_width, canvas_height))
        self.save_layout_config()

    def restore_modules(self):
        if not self.maximized_module_name:
            return
        self.shared_state.log("Restoring modules from maximized state.", "INFO")
        for iid, mod_data in self.loaded_modules.items():
            instance = mod_data.get('instance')
            if instance:
                instance.is_maximized = False

        content_height = self.main_layout_manager.last_calculated_content_height
        content_width = self.main_layout_manager.last_calculated_content_width
        self.main_layout_manager.config(width=content_width, height=content_height)
        self.canvas.itemconfig(self.main_layout_manager_window_id, width=content_width, height=content_height)

        if self._pre_maximize_layout:
            for iid, props in self._pre_maximize_layout.items():
                if iid in self.loaded_modules:
                    self.main_layout_manager.resize_module(iid, props.get('width', 200), props.get('height', 150))
            self.main_layout_manager.reflow_layout()
        else:
            self.main_layout_manager.reflow_layout()

        self.canvas.config(scrollregion=(0, 0, content_width, content_height))
        self.update_layout_scrollregion()
        self.maximized_module_name = None
        self._pre_maximize_layout = None
        self.save_layout_config()
if __name__ == "__main__":
    import sys
    if '__main__' in sys.modules:
        sys.modules['main'] = sys.modules['__main__']

    root = tk.Tk()
    app = ModularGUI(root)
    root.mainloop()

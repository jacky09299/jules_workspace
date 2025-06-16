import tkinter as tk
from tkinter import ttk
import os
import importlib.util
import json
from shared_state import SharedState # Assuming shared_state.py is in the same directory
import logging # Added for logging level constants

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

        # Close button "X"
        self.close_button = ttk.Button(self.title_bar_frame, text="X", width=3,
                                        command=self.close_module_action)
        self.close_button.pack(side=tk.RIGHT, padx=(0, 2))

        self.fullscreen_button = ttk.Button(self.title_bar_frame, text="FS", width=3, command=self.invoke_fullscreen_toggle)
        self.fullscreen_button.pack(side=tk.RIGHT, padx=(0, 5))

        # Add resize handle (visual placeholder for now)
        self.resize_handle = ttk.Sizegrip(self.frame)
        self.resize_handle.pack(side=tk.BOTTOM, anchor=tk.SE)
        # Alternatively, place in title_bar_frame if it's more appropriate for the UI design:
        # self.resize_handle = ttk.Sizegrip(self.title_bar_frame)
        # self.resize_handle.pack(side=tk.RIGHT, anchor=tk.SE)
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
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root

        if self.gui_manager and self.gui_manager.main_layout_manager:
            module_props = self.gui_manager.main_layout_manager.get_module_info(self.module_name)
            if module_props:
                self.resize_start_width = module_props['width']
                self.resize_start_height = module_props['height']
            else:
                # Fallback if props not found, though unlikely for an existing module
                frame_wrapper = self.master
                self.resize_start_width = frame_wrapper.winfo_width()
                self.resize_start_height = frame_wrapper.winfo_height()
        else:
            # Fallback if no gui_manager, should not happen in normal operation
            frame_wrapper = self.master
            self.resize_start_width = frame_wrapper.winfo_width()
            self.resize_start_height = frame_wrapper.winfo_height()
        # return "break"

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
        # return "break"

    def _on_resize_release(self, event):
        # Final dimensions are already set by the last call to resize_module in _on_resize_motion.
        if self.gui_manager:
            self.gui_manager.update_min_window_size()
            self.gui_manager.update_layout_scrollregion() # Add this call
        # return "break"

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

# CustomLayoutManager class definition
class CustomLayoutManager(tk.Frame):
    def __init__(self, master, *args, **kwargs): # master here is the canvas
        super().__init__(master, *args, **kwargs)
        self.modules = {} # Stores module_name: {frame, name, width, height, x, y}
        self.canvas_parent = master
        self.current_canvas_width = self.canvas_parent.winfo_width() if self.canvas_parent.winfo_width() > 1 else 800
        self.last_calculated_content_width = 0
        self.last_calculated_content_height = 0
        # self.bind("<Configure>", self.on_resize_internal) # Removed

    def add_module(self, module_frame, module_name, width, height):
        self.modules[module_name] = {
            'frame': module_frame,
            'name': module_name,
            'width': width,
            'height': height,
            # x and y are determined by reflow_layout
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
            self.modules[module_name]['width'] = max(10, width) # Ensure minimum size
            self.modules[module_name]['height'] = max(10, height)
            self.reflow_layout()
        else:
            logging.warning(f"CustomLayoutManager: Attempted to resize non-existent module: {module_name}")

    def _is_overlapping(self, r1_x, r1_y, r1_w, r1_h, r2_x, r2_y, r2_w, r2_h) -> bool:
        """Checks if two rectangles overlap."""
        return r1_x < r2_x + r2_w and \
               r1_x + r1_w > r2_x and \
               r1_y < r2_y + r2_h and \
               r1_y + r1_h > r2_y

    def reflow_layout(self):
        placed_modules_rects = []
        # Use the width of the canvas this CustomLayoutManager is placed in.
        # current_canvas_width should be updated by ModularGUI.on_canvas_configure
        container_width = self.current_canvas_width
        if container_width <= 1:
             container_width = self.canvas_parent.winfo_width() # Try direct query
        if container_width <= 1:
             container_width = 800 # Fallback

        # Determine the max y reached to set the height of this frame later
        max_x_coord = 0
        max_y_coord = 0

        # Estimate container height for scanning; this might need to be dynamic
        # For now, use a large enough virtual area or make it grow.
        # Let's assume a very large virtual height for scanning placement positions.
        # The actual height of this CustomLayoutManager frame will be set at the end.
        scan_height_limit = 10000 # Large virtual height for placement scanning

        min_module_dim = 10

        for module_name, module_info in self.modules.items():
            current_w = max(min_module_dim, module_info['width'])
            current_h = max(min_module_dim, module_info['height'])

            found_position_for_module = False
            final_x, final_y = 0, 0

            for test_y_candidate in range(0, scan_height_limit, 1): # Step by 1 pixel for precision
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


        self.last_calculated_content_width = max_x_coord  # Store actual max extent of content
        self.last_calculated_content_height = max_y_coord + 5 # Add some padding

        # The width CustomLayoutManager should occupy is the width given by the canvas.
        # Its height is determined by its content.
        layout_manager_own_width = self.current_canvas_width
        if layout_manager_own_width <= 1: # Fallback if canvas width isn't properly set yet
            layout_manager_own_width = self.canvas_parent.winfo_width() # Try direct query
            if layout_manager_own_width <= 1:
                layout_manager_own_width = 800 # Absolute fallback

        self.config(width=layout_manager_own_width, height=self.last_calculated_content_height)
        # logging.debug(f"CustomLayoutManager configured to: {layout_manager_own_width}x{self.last_calculated_content_height}")
        # logging.debug(f"Actual content extents: {self.last_calculated_content_width}x{self.last_calculated_content_height}")


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

        moved_item = self.modules.pop(module_to_move_name)

        if target_module_name is None or target_module_name not in self.modules:
            # Add to the end if no target or target not found
            self.modules[module_to_move_name] = moved_item
        else:
            # Create new ordered dict
            new_modules_order = {}
            for name, info in self.modules.items():
                if name == target_module_name:
                    new_modules_order[module_to_move_name] = moved_item
                new_modules_order[name] = info
            # If target_module_name was the last one and pop removed it before iteration,
            # this logic might need adjustment, but pop happens on the original dict.
            # If module_to_move was before target, target is still there.
            # If module_to_move was after target, target is still there.
            # This should be okay. If target_module_name was the *only* other module,
            # then the loop adds moved_item then target_item.
            # If target_module_name is not reached (e.g. it was the one moved, which is not possible due to first check),
            # it implies target was module_to_move, or target is not in self.modules after pop.
            # The initial check for module_to_move_name ensures it exists.
            # The check for target_module_name ensures it exists *before* this block.
            self.modules = new_modules_order
            # If target_module_name was not found in the items() after pop (should not happen if it's a valid distinct name)
            # we might need to ensure moved_item is re-added if not already by the loop.
            # However, the logic is: if target_module_name is in self.modules (which it is at this point,
            # and it's not the moved_item), the loop will find it.
            if module_to_move_name not in self.modules: # Should not happen if logic is correct
                 # This case implies something went wrong, or target_module_name was the only module left
                 # and the loop structure didn't re-add the moved_item correctly relative to it.
                 # Let's refine the new_modules_order creation slightly for clarity and robustness.

                # Refined logic for reordering:
                temp_items = list(self.modules.items()) # Items from original dict *after* pop
                new_modules_order.clear()
                inserted = False
                for name, info in temp_items:
                    if name == target_module_name:
                        new_modules_order[module_to_move_name] = moved_item
                        inserted = True
                    new_modules_order[name] = info
                if not inserted: # If target_module_name was not in temp_items (e.g. it was the last or only item before pop)
                                 # or if loop finished and target was last, place moved_item before it conceptually if it makes sense
                                 # or at the end if target was never found (covered by initial check).
                                 # Given target_module_name is confirmed to be in self.modules (the post-pop one),
                                 # this 'not inserted' case should ideally not happen unless self.modules was empty post-pop.
                                 # For safety, if it wasn't inserted, it means target was not iterated over.
                                 # This can only happen if self.modules (post-pop) was empty.
                                 # If self.modules (post-pop) is empty, new_modules_order is empty.
                                 # Then we just add moved_item.
                    if not new_modules_order and not temp_items: # Original dict became empty after pop
                         new_modules_order[module_to_move_name] = moved_item
                    # If it was meant to be inserted but target was last, it should be handled.
                    # This re-insertion logic is actually simpler: build list, insert, rebuild dict.

                # Simplest way to reorder before a target or at end:
                all_items = list(self.modules.items()) # self.modules here is after pop
                self.modules.clear() # Clear it to rebuild in new order

                if target_module_name is None or target_module_name not in [item[0] for item in all_items]:
                    # Add all original items, then the moved one at the end
                    for name, info in all_items:
                        self.modules[name] = info
                    self.modules[module_to_move_name] = moved_item
                else:
                    # Rebuild with insertion
                    inserted_flag = False
                    for name, info in all_items:
                        if name == target_module_name:
                            self.modules[module_to_move_name] = moved_item
                            inserted_flag = True
                        self.modules[name] = info
                    if not inserted_flag: # Should not happen if target_module_name was in all_items
                         self.modules[module_to_move_name] = moved_item


        self.reflow_layout()


    def get_layout_data(self) -> dict:
        data = {}
        for name, info in self.modules.items():
            data[name] = {
                'width': info['width'],
                'height': info['height'],
                # 'ref_width': info.get('ref_width', info['width']), # No longer saving ref_width
                # 'ref_height': info.get('ref_height', info['height']), # No longer saving ref_height
                'x': info.get('x', 0),
                'y': info.get('y', 0)
            }
        return data

    def get_module_info(self, module_name):
        return self.modules.get(module_name)

    # on_resize_internal is removed as primary reflow trigger is now ModularGUI.on_canvas_configure -> self.reflow_layout()
    # def on_resize_internal(self, event):
    #     if event.widget == self:
    #         # This might still be useful if CustomLayoutManager's size changes for reasons other than canvas configure
    #         # For now, relying on on_canvas_configure to drive reflows.
    #         # self.current_canvas_width = self.canvas_parent.winfo_width() # Update width
    #         # self.reflow_layout()
    #         pass


class ModularGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Modular GUI Framework")
        self.root.geometry("800x600")

        # Main menubar
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # Modules menu (populated after discovery)
        self.modules_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Modules", menu=self.modules_menu)

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
        self.drop_target_module_frame_wrapper = None # Renamed from self.drop_target_pane
        self.original_dragged_module_relief = None

        # Fullscreen state
        self.fullscreen_module_name = None
        # self.store_main_pane_children = [] # Unused attribute, removed.

        # Create a container for canvas and scrollbar for better packing
        self.canvas_container = ttk.Frame(self.root)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.canvas_container)
        # self.canvas.configure(background='pink') # For debugging canvas area

        self.v_scrollbar = ttk.Scrollbar(self.canvas_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)

        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_container.pack_propagate(False) # Prevent container resizing due to canvas content

        # Now, main_layout_manager is a child of the canvas
        # Note: CustomLayoutManager's __init__ does not currently take shared_state.
        # If shared_state logging is needed directly within CustomLayoutManager, its __init__ would need modification.
        self.main_layout_manager = CustomLayoutManager(self.canvas, background="lightgrey")

        self.main_layout_manager_window_id = self.canvas.create_window(
            (0, 0), window=self.main_layout_manager, anchor='nw'
        )

        # Mouse wheel bindings for scrolling
        # For Windows & macOS (MouseWheel)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        # For Linux (Button-4 and Button-5)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

        # Bind canvas configure event
        self.canvas.bind("<Configure>", self.on_canvas_configure)


        self.available_module_classes = {} # Populated by discover_modules
        self.layout_config_file = 'layout_config.json' # Config file path

        # Context Menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.main_layout_manager.bind("<Button-3>", self.show_context_menu) # Button-3 for right-click on Windows/Linux
        # For macOS, Button-2 might be more standard for context menus if Button-3 is not configured.
        # Or use '<Control-Button-1>' for macOS if desired.

        self.discover_modules() # Populates self.available_module_classes

        # Populate Modules menu after discovery
        for module_name in sorted(self.available_module_classes.keys()):
            self.modules_menu.add_command(
                label=f"Add {module_name}",
                command=lambda mn=module_name: self.add_module_from_menu(mn)
            )

        self.load_layout_config() # Load layout, which might call setup_default_layout as fallback

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _on_mousewheel(self, event):
        # For Linux, event.num determines scroll direction
        # For Windows/macOS, event.delta determines scroll magnitude and direction
        if hasattr(event, 'num') and event.num == 4:  # Scroll up on Linux
            self.canvas.yview_scroll(-1, "units")
        elif hasattr(event, 'num') and event.num == 5:  # Scroll down on Linux
            self.canvas.yview_scroll(1, "units")
        elif hasattr(event, 'delta'):  # For Windows/macOS
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_layout_scrollregion(self):
        self.main_layout_manager.update_idletasks() # Ensure calculations are fresh

        # Height needed by content (CustomLayoutManager configured this for itself)
        content_total_height = self.main_layout_manager.last_calculated_content_height

        # Actual width of all content in CustomLayoutManager (for horizontal scroll extent)
        content_total_width = self.main_layout_manager.last_calculated_content_width

        # The canvas item for CustomLayoutManager should be as wide as the canvas viewport.
        canvas_viewport_width = self.canvas.winfo_width()
        if canvas_viewport_width <= 1: # Fallback if canvas not sized
            canvas_viewport_width = 800

        item_width_for_canvas = canvas_viewport_width

        # Scrollregion should span the actual content width and height
        self.canvas.config(scrollregion=(0, 0, content_total_width, content_total_height))

        # The item on the canvas (CustomLayoutManager) should be configured to the canvas viewport width,
        # and the total height its content requires.
        self.canvas.itemconfig(self.main_layout_manager_window_id,
                               width=item_width_for_canvas,
                               height=content_total_height)

        # self.shared_state.log(f"ScrollRgn: (0,0,{content_total_width},{content_total_height}), ItemCfg: ({item_width_for_canvas},{content_total_height})", "DEBUG")


    def on_canvas_configure(self, event):
        # event.width is the new width of the canvas widget itself
        canvas_width = event.width

        # Update the width of the frame_window item on canvas to match the canvas viewport width.
        # This makes CustomLayoutManager aware of how much horizontal space it has.
        self.canvas.itemconfig(self.main_layout_manager_window_id, width=canvas_width)

        # Trigger a reflow in CustomLayoutManager; it should use its new allocated width
        # (which is the canvas viewport width) to rearrange modules.
        if hasattr(self.main_layout_manager, 'current_canvas_width'):
            self.main_layout_manager.current_canvas_width = canvas_width # Update CLM's knowledge of canvas width

        if hasattr(self.main_layout_manager, 'reflow_layout'):
             self.main_layout_manager.reflow_layout()

        # After reflow, CustomLayoutManager will have its own required height (and width).
        # Update the scrollregion based on this new required size.
        self.update_layout_scrollregion()


    def update_min_window_size(self):
        if not hasattr(self, 'main_layout_manager') or self.main_layout_manager is None:
            return

        max_module_w = self.main_layout_manager.get_max_module_width()

        base_min_width = 200
        padding = 20

        effective_min_width = max(base_min_width, max_module_w + padding if max_module_w > 0 else base_min_width)

        try:
            # Attempt to get current minsize, may fail if not set or on some platforms/tk versions early on
            try:
                current_min_height = self.root.minsize()[1]
            except tk.TclError: # If minsize hasn't been set, it might return empty or error
                current_min_height = 0 # Default or use a predefined app absolute min height
            if current_min_height == 1 and self.root.winfo_height() > 1 : # Often (1,1) is default unset
                 current_min_height = self.root.winfo_height() if self.root.winfo_height() > 20 else 200 # Use current or a sensible default
            current_min_height = max(200, current_min_height) # Ensure a sensible minimum height


            self.root.minsize(effective_min_width, current_min_height)
            self.shared_state.log(f"Minimum window width set to: {effective_min_width}, min_height: {current_min_height}", "DEBUG")
        except tk.TclError as e:
            self.shared_state.log(f"Error setting minsize: {e}", "WARNING")

    def add_module_from_menu(self, module_name: str):
        self.shared_state.log(f"Attempting to add module '{module_name}' from menu.")

        if module_name in self.loaded_modules:
            # Check if its frame_wrapper is currently managed by the layout.
            # This is a simplified check; a more robust one might involve asking CustomLayoutManager.
            module_data = self.loaded_modules.get(module_name)
            if module_data and module_data.get('frame_wrapper') and \
               module_data.get('frame_wrapper').winfo_ismapped(): # ismapped is a basic check for visibility
                self.shared_state.log(f"Module '{module_name}' is already loaded and likely visible. No action taken.", "INFO")
                return

        if module_name in self.available_module_classes:
            # Logic for removing a potential "No modules" label:
            # This is tricky as the label is added in setup_default_layout to main_layout_manager.
            # CustomLayoutManager doesn't inherently know about this label.
            # A simple but potentially fragile way:
            children = self.main_layout_manager.winfo_children()
            if len(children) == 1 and isinstance(children[0], ttk.Label):
                if "No modules available" in children[0].cget("text") or \
                   "No modules displayed" in children[0].cget("text"):
                    children[0].destroy()
                    self.shared_state.log("Removed default placeholder label.", "DEBUG")

            self.instantiate_module(module_name, self.main_layout_manager)
            self.root.update_idletasks()
            self.update_min_window_size() # Update after adding
            self.update_layout_scrollregion() # Update scrollregion
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

    def instantiate_module(self, module_name, parent_layout_manager): # Parameter name changed
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

        # frame_wrapper is the direct child of the parent_layout_manager
        frame_wrapper = ttk.Frame(parent_layout_manager, relief=tk.SUNKEN, borderwidth=1)

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

            initial_width, initial_height = 200, 150 # Placeholder values
            parent_layout_manager.add_module(frame_wrapper, module_name, initial_width, initial_height)
            self.update_min_window_size() # Update after instantiating
            self.update_layout_scrollregion() # Update scrollregion
            self.shared_state.log(f"Instantiated and added module '{module_name}' to layout manager.")
            return frame_wrapper
        except Exception as e:
            self.shared_state.log(f"Error instantiating module {module_name}: {e}", level=logging.ERROR)
            if frame_wrapper.winfo_exists(): # Clean up frame_wrapper if instance failed
                frame_wrapper.destroy()
            return None

    def setup_default_layout(self):
        self.shared_state.log("Setting up default layout...")

        # TODO: Adapt module clearing for CustomLayoutManager
        # Ensure any existing panes are cleared before setting up a new layout
        # if hasattr(self.main_layout_manager, 'remove_all_modules'): # Or similar method
        #     self.main_layout_manager.remove_all_modules()
        # else:
        #     # Fallback: iterate loaded_modules and remove them one by one
        #     for module_name in list(self.loaded_modules.keys()):
        #         # This assumes remove_module exists and handles cleanup of frame_wrapper
        #         self.main_layout_manager.remove_module(module_name)
        #         # We might also need to call instance.on_destroy() and del self.loaded_modules[module_name] here
        #         # For now, commenting out the original pane forgetting logic:
        #         pass # Original: for pane_id_str in list(self.main_pane.panes()): self.main_pane.forget(pane_id_str)


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
                # TODO: Re-adding existing modules needs to be adapted for CustomLayoutManager
                # For now, we will always instantiate.
                # if module_name in self.loaded_modules and self.loaded_modules[module_name]['instance']:
                #     wrapper = self.loaded_modules[module_name]['frame_wrapper']
                #     if wrapper and wrapper.winfo_exists(): # Check if widget still exists
                #         try:
                #             # Logic to check if wrapper is already in main_layout_manager and re-add if not
                #             # This depends on CustomLayoutManager's API
                #             # self.main_layout_manager.add_module(wrapper, module_name, 200, 150) # Example
                #             created_wrappers.append(wrapper)
                #             self.shared_state.log(f"Re-added existing module '{module_name}' to default layout.")
                #             continue
                #         except Exception as e: # Catch generic exception as API is unknown
                #              self.shared_state.log(f"Could not re-add wrapper for {module_name}, attempting new instantiation: {e}", level=logging.WARNING)
                #              # Fall through to instantiate if re-adding fails

                # If not loaded, or re-adding failed, instantiate it
                wrapper = self.instantiate_module(module_name, self.main_layout_manager)
                if wrapper:
                    created_wrappers.append(wrapper)
            else:
                self.shared_state.log(f"Module '{module_name}' for default layout not available.", level=logging.WARNING)

        if not created_wrappers: # Check if any modules were actually added to the layout
            # Add a default label if no modules are loaded
            default_label = ttk.Label(self.main_layout_manager, text="No modules available for default layout.")
            # How to add this depends on CustomLayoutManager's design.
            # For now, let's assume it can take simple widgets or we might need a wrapper.
            # If CustomLayoutManager's add_module expects a frame_wrapper like other modules:
            # default_wrapper = ttk.Frame(self.main_layout_manager)
            # default_label.pack(in_=default_wrapper, expand=True, fill=tk.BOTH)
            # self.main_layout_manager.add_module(default_wrapper, "default_label", 200, 50)
            # Or, if CustomLayoutManager can handle direct packing for simple labels (less likely for complex layouts):
            default_label.pack(padx=10, pady=10) # This might not work as expected without add_module
            self.shared_state.log("No modules loaded for default layout. Displaying default message in main_layout_manager.")
        self.update_min_window_size() # Update after default layout setup
        self.update_layout_scrollregion() # Update scrollregion

    def save_layout_config(self):
        self.shared_state.log(f"Saving layout configuration to {self.layout_config_file}")
        layout_data = {
            'fullscreen_module': self.fullscreen_module_name,
            # 'paned_window_layout': None, # Deprecated
            'custom_modules_properties': None # New key for CustomLayoutManager data
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

            # Clear existing modules from CustomLayoutManager and module instances
            # TODO: This assumes CustomLayoutManager will have a method to get all module names it manages,
            # or we iterate self.loaded_modules if CustomLayoutManager doesn't directly own them.
            # For now, let's iterate self.loaded_modules and call remove_module.
            # This part needs to be robust based on CustomLayoutManager's design.
            module_names_to_remove = list(self.loaded_modules.keys())
            for module_name in module_names_to_remove:
                if hasattr(self.main_layout_manager, 'remove_module'):
                    self.main_layout_manager.remove_module(module_name) # Assumes this also handles frame_wrapper removal from layout
                # The following destruction logic should ideally be part of what remove_module triggers,
                # or called after confirming the module is removed from layout.
                module_data = self.loaded_modules.get(module_name)
                if module_data:
                    if module_data.get('instance'):
                        try:
                            module_data['instance'].on_destroy()
                        except Exception as e:
                            self.shared_state.log(f"Error during on_destroy for module {module_name} in load_layout_config: {e}", level=logging.ERROR)
                    if module_data.get('frame_wrapper') and module_data['frame_wrapper'].winfo_exists():
                        module_data['frame_wrapper'].destroy() # Destroy the wrapper
                    del self.loaded_modules[module_name] # Unload from tracking

            # Fallback if the above loop didn't clear self.loaded_modules (e.g. remove_module not implemented)
            # This is a bit redundant if remove_module works perfectly and updates self.loaded_modules via callbacks or similar
            # For safety during refactor:
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

            # This part of the original code is now covered by the loop above.
            # The self.loaded_modules.clear() call below will finalize it.
            self.loaded_modules.clear() # Ensure it's cleared after destruction.

            custom_modules_properties = layout_data.get('custom_modules_properties')
            loaded_any_module_from_config = False

            if custom_modules_properties:
                self.shared_state.log(f"Loading modules from custom_modules_properties: {list(custom_modules_properties.keys())}")

                # First, instantiate all modules that are in the config and available
                for module_name in custom_modules_properties.keys():
                    if module_name in self.available_module_classes:
                        if module_name not in self.loaded_modules: # Avoid re-instantiating if somehow already loaded
                            self.instantiate_module(module_name, self.main_layout_manager)
                            # instantiate_module adds with default size, resize comes next
                    else:
                        self.shared_state.log(f"Module '{module_name}' from layout config not available in discovered modules.", level=logging.WARNING)

                # Wait for UI to update so manager has its width for scaling references
                self.root.update_idletasks()

                # Second, apply saved sizes (and implicitly ref_sizes via resize_module)
                for module_name, props in custom_modules_properties.items():
                    if module_name in self.loaded_modules:
                        # Ensure 'width' and 'height' keys exist, provide default if not (though they should from get_layout_data)
                        width = props.get('width', 200) # Default width if missing
                        height = props.get('height', 150) # Default height if missing

                        # It's important that resize_module correctly updates the module's
                        # 'ref_width' and 'ref_height' based on these loaded dimensions
                        # and the manager's current width at this point.
                        self.main_layout_manager.resize_module(module_name, width, height)
                        loaded_any_module_from_config = True
                        self.shared_state.log(f"Applied saved size to {module_name}: w={width}, h={height}", level=logging.DEBUG)

                # One final reflow after all sizes are set might be good if resize_module doesn't trigger it adequately
                # or if there are interdependencies not captured by individual resizes.
                # However, resize_module already calls reflow_layout.
                # self.main_layout_manager.reflow_layout() # Potentially redundant, but can ensure final consistency.

            else:
                self.shared_state.log("No 'custom_modules_properties' found in layout config.", level=logging.INFO)

            # Fullscreen module logic
            fullscreen_module_to_load = layout_data.get('fullscreen_module')
            if fullscreen_module_to_load:
                if fullscreen_module_to_load not in self.loaded_modules:
                    if fullscreen_module_to_load in self.available_module_classes:
                        self.shared_state.log(f"Fullscreen module '{fullscreen_module_to_load}' not in main layout, loading it.", level=logging.INFO)
                        self.instantiate_module(fullscreen_module_to_load, self.main_layout_manager)
                        # If this module also had saved properties, apply them
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

            # Fallback to default layout if no modules were loaded from config and not in fullscreen
            if not loaded_any_module_from_config and not fullscreen_module_to_load and not self.loaded_modules:
                self.shared_state.log("Layout config processed, but no modules loaded and not entering fullscreen. Setting up default layout.", level=logging.INFO)
                self.setup_default_layout() # This will call update_min_window_size and update_layout_scrollregion
            else:
                self.update_min_window_size() # Update after loading and resizing modules from config
                self.update_layout_scrollregion() # Update scrollregion

        except Exception as e:
            self.shared_state.log(f"Error loading layout configuration: {e}. Using default layout.", level=logging.ERROR)
            # Ensure a clean slate for default layout if loading fails mid-way
            # TODO: Ensure robust cleanup for CustomLayoutManager if loading fails mid-way.
            # The existing loop should handle loaded_modules, but CustomLayoutManager's internal state might also need reset.
            # For example, self.main_layout_manager.modules.clear() if not handled by remove_module calls.
            current_loaded_module_names = list(self.loaded_modules.keys())
            for name in current_loaded_module_names:
                if hasattr(self.main_layout_manager, 'remove_module'):
                    self.main_layout_manager.remove_module(name) # Should clear from layout manager
                # Standard cleanup from loaded_modules
                mod_data = self.loaded_modules.pop(name, None)
                if mod_data:
                    if mod_data.get('instance'): mod_data['instance'].on_destroy()
                    if mod_data.get('frame_wrapper') and mod_data['frame_wrapper'].winfo_exists(): mod_data['frame_wrapper'].destroy()

            self.loaded_modules.clear() # Should be empty now
            self.setup_default_layout()


    def on_closing(self):
        self.shared_state.log("Application closing...")
        self.save_layout_config() # Save the layout before closing

        # Call on_destroy for all loaded module instances
        # Create a copy of items for safe iteration if on_destroy modifies self.loaded_modules
        for module_name, module_data in list(self.loaded_modules.items()):
            if module_data and module_data.get('instance'): # Check module_data exists
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

            # Determine visible modules with CustomLayoutManager
            # TODO: This needs a robust way to check visibility with CustomLayoutManager's API.
            # For now, assume if a module is in loaded_modules and has a frame_wrapper,
            # and we are not in fullscreen, it's managed by CustomLayoutManager and thus visible.
            # This is a simplification. A proper check like `self.main_layout_manager.is_module_visible(module_name)` would be ideal.

            visible_module_wrappers = [] # This list isn't directly used in the simplified logic below but concept remains
            if not self.fullscreen_module_name: # Only consider modules visible if not in fullscreen
                for mod_name, mod_data in self.loaded_modules.items():
                    if mod_data.get('frame_wrapper') and mod_data['frame_wrapper'].winfo_exists():
                        # Assuming frame_wrapper existing means it's managed/visible by CustomLayoutManager
                        # This is where a call to CustomLayoutManager would be more accurate:
                        # e.g., if self.main_layout_manager.is_managing(mod_data['frame_wrapper']):
                        visible_module_wrappers.append(mod_data['frame_wrapper'])


            for module_name in sorted(self.available_module_classes.keys()):
                is_visible = False
                if module_name in self.loaded_modules and not self.fullscreen_module_name:
                    mod_data = self.loaded_modules[module_name]
                    # Simplified visibility check: if it's loaded and has a wrapper, assume visible in context of CustomLayoutManager
                    if mod_data.get('instance') and mod_data.get('frame_wrapper') and mod_data.get('frame_wrapper').winfo_exists():
                         # And it's a child of main_layout_manager (or its frame_wrapper is)
                         # This check could be: mod_data.get('frame_wrapper').master == self.main_layout_manager
                         # However, add_module in CustomLayoutManager might use intermediate frames.
                         # For now, trusting that if it's loaded and not fullscreen, it's "visible" for toggle purposes.
                        is_visible = True # Simplified from checking against current_pane_wrappers

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
        if module_name in self.loaded_modules and not self.fullscreen_module_name: # Also ensure not in fullscreen
            mod_data = self.loaded_modules[module_name]
            if mod_data and mod_data.get('instance'):
                wrapper_to_check = mod_data.get('frame_wrapper')
                if wrapper_to_check and wrapper_to_check.winfo_exists():
                    # Simplified visibility check for CustomLayoutManager
                    # TODO: Replace with a call to self.main_layout_manager.is_module_visible(module_name) or similar
                    # For now, if it's loaded, has a wrapper, and not fullscreen, consider it visible for toggling.
                    is_visible = True
                    # Original check for PanedWindow:
                    # try:
                    #     current_pane_widgets = [self.main_layout_manager.nametowidget(p_id) for p_id in self.main_layout_manager.panes()] # Error: main_layout_manager has no panes()
                    #     if wrapper_to_check in current_pane_widgets:
                    #        is_visible = True
                    # except tk.TclError: is_visible = False


        if is_visible:
            # Hide the module using the new centralized method
            self.hide_module(module_name)

            # TODO: Check if main_layout_manager is empty and add default label
            # This requires a method like self.main_layout_manager.get_module_count() or similar.
            # The placeholder logic from the old version of toggle_module_visibility is now
            # deferred/removed as per the hide_module implementation.
            # if not self.main_layout_manager.modules: # Check if CustomLayoutManager's dict is empty
            #     default_label = ttk.Label(self.main_layout_manager, text="No modules displayed. Right-click to add.")
            #     # This default label addition needs a strategy consistent with CustomLayoutManager
            #     # For now, this part is not actively managed here, relying on future improvements or manual add via menu.
            #     # default_label.pack(padx=10, pady=10) # This direct pack might interfere.
            #     self.shared_state.log("All modules hidden. Placeholder label logic deferred.")

        else: # Module is not currently visible, so show it
            self.shared_state.log(f"Showing module: {module_name}")
            if module_name in self.available_module_classes:
                # TODO: If a default label is showing, remove it.
                # This requires CustomLayoutManager to provide a way to find/remove such a label.
                # Example: self.main_layout_manager.remove_widget_by_name("default_label_wrapper")

                # instantiate_module will call self.main_layout_manager.add_module
                self.instantiate_module(module_name, self.main_layout_manager)
                self.root.update_idletasks()
            else:
                self.shared_state.log(f"Module '{module_name}' cannot be shown, not found in available modules.", level=logging.WARNING)

        # Ensure layout is saved on next close
        # self.save_layout_config() # Or let it save on closing only

    def hide_module(self, module_name: str):
        self.shared_state.log(f"Hiding module: {module_name} via close button/hide action.")
        if module_name in self.loaded_modules:
            module_data = self.loaded_modules[module_name]
            frame_wrapper = module_data.get('frame_wrapper')
            instance = module_data.get('instance')

            # Call CustomLayoutManager to remove the module's frame
            if frame_wrapper and frame_wrapper.winfo_exists():
                self.main_layout_manager.remove_module(module_name)

            # Call module's on_destroy for cleanup
            if instance:
                try:
                    instance.on_destroy()
                except Exception as e:
                    self.shared_state.log(f"Error during on_destroy for module {module_name} when hiding: {e}", "ERROR")

            # Destroy the frame_wrapper itself which contains the module's UI
            if frame_wrapper and frame_wrapper.winfo_exists():
                frame_wrapper.destroy()

            # Remove from active tracking
            del self.loaded_modules[module_name]
            self.shared_state.log(f"Module '{module_name}' hidden and instance destroyed.")

            # Placeholder label logic is deferred as per subtask description.
            # if not self.main_layout_manager.modules: # Check if any modules are left
            #    pass # Add placeholder logic here if desired
            self.update_min_window_size() # Update after hiding a module
            self.update_layout_scrollregion() # Update scrollregion

        else:
            self.shared_state.log(f"Module '{module_name}' not found or not loaded, cannot hide.", "WARNING")


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
        if self.drop_target_module_frame_wrapper and self.drop_target_module_frame_wrapper.winfo_exists():
            if self.drop_target_module_frame_wrapper != self.loaded_modules[self.dragged_module_name].get('frame_wrapper'):
                 try:
                    self.drop_target_module_frame_wrapper.config(borderwidth=1) # Reset border
                 except tk.TclError: pass # Widget might have been destroyed

        x_root, y_root = event.x_root, event.y_root
        current_target_frame_wrapper = None

        # Find which module's frame_wrapper is under the cursor
        for module_name_iter, module_data_iter in self.loaded_modules.items():
            # Do not consider the dragged module itself as a potential drop target
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

        if current_target_frame_wrapper: # No need to check if it's different from dragged, already skipped
            self.drop_target_module_frame_wrapper = current_target_frame_wrapper
            try:
                self.drop_target_module_frame_wrapper.config(borderwidth=3) # Highlight potential drop target
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

        # Reset visual cue of dragged module
        if dragged_frame_wrapper and dragged_frame_wrapper.winfo_exists() and self.original_dragged_module_relief:
            try:
                dragged_frame_wrapper.config(relief=self.original_dragged_module_relief, borderwidth=1)
            except tk.TclError: pass

        # Reset visual cue of the last drop target
        if self.drop_target_module_frame_wrapper and self.drop_target_module_frame_wrapper.winfo_exists():
            try:
                self.drop_target_module_frame_wrapper.config(borderwidth=1) # Reset border
            except tk.TclError: pass

        # Core Logic for reordering
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
            elif not target_module_name: # Should ideally not happen if drop_target_module_frame_wrapper is set
                 self.main_layout_manager.move_module_before(self.dragged_module_name, None) # Move to end
                 self.shared_state.log(f"Moved '{self.dragged_module_name}' to the end (no specific target module identified for wrapper).", level=logging.WARNING)
            # If target_module_name is same as dragged_module_name, do nothing (already handled by outer if)

        elif self.dragged_module_name and not self.drop_target_module_frame_wrapper :
            # If dragged to an empty space (not over another module), move to the end.
            # This behavior can be adjusted if needed.
            self.shared_state.log(f"'{self.dragged_module_name}' dropped on empty space, moving to end.")
            self.main_layout_manager.move_module_before(self.dragged_module_name, None)

        else:
            self.shared_state.log(f"Drag ended for {self.dragged_module_name} without a valid different drop target.", "DEBUG")

        # Clear drag state
        self.dragged_module_name = None
        self.drag_start_widget = None
        self.drop_target_module_frame_wrapper = None
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
        # Let's just hide the main_layout_manager.

        self.main_layout_manager.pack_forget() # Hide main_layout_manager and all its children

        # Pack the fullscreen module's wrapper directly into the root
        fs_module_wrapper.pack(fill=tk.BOTH, expand=True, before=self.main_layout_manager) # 'before' tries to keep order if main_layout_manager is repacked

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

        # Restore main_layout_manager
        self.main_layout_manager.pack(fill=tk.BOTH, expand=True)
        # The CustomLayoutManager should remember its children (the frame_wrappers) and their states.
        # If any issues, we might need to explicitly re-add/configure modules.

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

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, simpledialog
import logging
from PIL import Image, ImageTk

# Assuming main.py (and thus the Module class definition) is in the parent directory
from main import Module

class ImageEditorModule(Module):
    def __init__(self, master, shared_state, module_name="ImageEditor", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log("ImageEditorModule initializing...", level=logging.INFO)
        # self.frame is created by the parent Module's __init__
        self.canvas = None

        self.current_tool = "freehand"
        self.start_x, self.start_y = None, None
        self.last_x, self.last_y = None, None # For freehand
        self.temp_shape_id = None
        self.pen_color = "black"
        self.pen_width = 2

        self.loaded_image_tk = None # To hold ImageTk.PhotoImage object
        self.original_pil_image = None # To hold the PIL Image object

        self.crop_area = None # Stores (x1, y1, x2, y2) for cropping
        self.crop_rect_id = None # ID of the rectangle visual cue on canvas for cropping

        self.current_font_family = tk.StringVar(value="Arial")
        self.current_font_size = tk.IntVar(value=12)

        self.canvas_objects = [] # List to store dictionaries of canvas items
        self.selected_object_id = None # ID of the currently selected canvas item
        self.selection_outline_color = "blue"
        self.selection_outline_width = 2
        self.original_item_options = {}

        self.drag_start_x = None
        self.drag_start_y = None

        self.resize_handles = [] # Stores dicts: {'id': handle_id, 'type': 'nw', 'object_id': main_obj_id}
        self.current_resize_handle_info = None # Info of the handle being dragged
        self.handle_size = 8
        self.handle_fill = "blue"
        self.handle_outline = "white"

        # Application Modes
        self._in_edit_mode = False
        self._in_crop_mode = False

        # Button and UI element references
        self.btn_open_image = None
        self.btn_edit_mode = None
        self.btn_rotate = None
        self.btn_crop = None
        self.btn_save = None
        self.btn_cancel = None

        self.drawing_tool_buttons = {} # e.g. {"freehand": btn_freehand, ...}
        self.btn_pen_color = None
        self.btn_rotate_left = None # Keeping for _update_button_states temporarily, will be removed
        self.btn_rotate_right = None # Keeping for _update_button_states temporarily, will be removed
        self.btn_add_text = None
        self.font_family_combo = None
        self.font_size_spinbox = None
        self.btn_select_object = None
        self.btn_delete_selected = None

        self.status_bar = None
        self.drawing_toolbar_frame = None # Frame for drawing related tools
        self.crop_buttons_frame = None # Frame for crop confirmation buttons


        # Mode-specific buttons (will be created on demand or visibility toggled)
        self.btn_confirm_crop = None
        self.btn_cancel_crop = None
        # self.btn_save_edit will be self.btn_save with modified text/command
        # self.btn_cancel_edit will be self.btn_cancel with modified text/command


        self.create_ui()
        self._update_button_states() # Set initial state (no image loaded)
        self.shared_state.log("ImageEditorModule initialized.", level=logging.INFO)

    # --- Mode Management Methods ---
    def is_in_edit_mode(self):
        return self._in_edit_mode

    def is_in_crop_mode(self):
        return self._in_crop_mode

    def toggle_edit_mode(self):
        if not self.original_pil_image:
            self._show_hint("Please load an image before entering Edit Mode.")
            return
        if self.is_in_crop_mode(): # Cannot enter edit mode from crop mode directly
            self._show_hint("Finalize or cancel cropping before entering Edit Mode.")
            return

        self._in_edit_mode = not self._in_edit_mode
        if self._in_edit_mode:
            self.current_tool = "freehand" # Default tool for edit mode
            self.drawing_toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        else:
            # Exiting edit mode, potentially save or discard changes here if needed by spec
            # For now, just hide toolbar and update states
            self.drawing_toolbar_frame.pack_forget()
            if self.selected_object_id: # Clear selection when exiting edit mode
                self._remove_selection_visual(self.selected_object_id)
                self.selected_object_id = None
                self._clear_resize_handles()
        self._update_button_states(image_loaded=bool(self.original_pil_image),
                                   in_edit_mode=self._in_edit_mode,
                                   in_crop_mode=self._in_crop_mode)

    def toggle_crop_mode(self):
        if not self.original_pil_image:
            self._show_hint("Please load an image before starting to Crop.")
            return
        if self.is_in_edit_mode(): # Cannot enter crop mode from edit mode directly
            self._show_hint("Finalize or cancel editing before starting to Crop.")
            return

        self._in_crop_mode = not self._in_crop_mode
        if self._in_crop_mode:
            self.select_tool("crop_select") # Set tool for crop area selection
            # Crop buttons frame is managed by _update_button_states
        else:
            # Exiting crop mode
            self.select_tool("none") # Or a sensible default like "select" if in edit mode
            if self.temp_shape_id: # Clear temporary crop selection rectangle
                self.canvas.delete(self.temp_shape_id)
                self.temp_shape_id = None
            if self.crop_rect_id: # Clear finalized crop selection rectangle if not confirmed
                self.canvas.delete(self.crop_rect_id)
                self.crop_rect_id = None
            self.crop_area = None
            self.current_tool = "none" # Reset tool when exiting crop mode
        self._update_button_states(image_loaded=bool(self.original_pil_image),
                                   in_edit_mode=self._in_edit_mode,
                                   in_crop_mode=self._in_crop_mode)

    # --- Action Stubs (to be implemented) ---
    def rotate_action_menu(self):
        if not self.original_pil_image:
            self._show_hint("Please load an image to rotate.")
            return
        if self.is_in_edit_mode() or self.is_in_crop_mode():
            self._show_hint("Please exit Edit or Crop mode before rotating.")
            return

        self.shared_state.log("Rotate action menu called.", level=logging.INFO)

        rotate_menu = tk.Menu(self.frame, tearoff=0)
        rotate_menu.add_command(label="Rotate 90° Left (CCW)", command=lambda: self.execute_rotation(Image.ROTATE_90))
        rotate_menu.add_command(label="Rotate 90° Right (CW)", command=lambda: self.execute_rotation(Image.ROTATE_270))
        rotate_menu.add_command(label="Rotate 180°", command=lambda: self.execute_rotation(Image.ROTATE_180))
        # Future: rotate_menu.add_command(label="Custom Angle...", command=self.custom_rotate_action)

        try:
            if self.btn_rotate and self.btn_rotate.winfo_viewable():
                 x = self.btn_rotate.winfo_rootx()
                 y = self.btn_rotate.winfo_rooty() + self.btn_rotate.winfo_height()
                 rotate_menu.tk_popup(x, y)
            else:
                rotate_menu.tk_popup(self.frame.winfo_pointerx(), self.frame.winfo_pointery())
        except Exception as e:
            self.shared_state.log(f"Error popping up rotate menu: {e}. Trying pointer.", level=logging.WARNING)
            try:
                rotate_menu.tk_popup(self.frame.winfo_pointerx(), self.frame.winfo_pointery())
            except tk.TclError as te:
                 self.shared_state.log(f"Failed to popup rotate menu at pointer: {te}", level=logging.ERROR)


    def execute_rotation(self, pil_rotation_constant):
        if not self.original_pil_image:
            self.shared_state.log("Cannot rotate: No image loaded.", level=logging.WARNING)
            self._show_hint("No image loaded to rotate.") # User feedback
            return

        self.shared_state.log(f"Attempting to rotate image with PIL constant: {pil_rotation_constant}", level=logging.INFO)
        try:
            # Preserve filepath before clearing state that might hold it indirectly
            current_filepath = getattr(self.original_pil_image, 'filepath', None)

            self._clear_all_canvas_state()

            rotated_pil_image = self.original_pil_image.transpose(pil_rotation_constant)
            self.original_pil_image = rotated_pil_image
            if current_filepath: # Restore filepath to the new PIL image object
                 self.original_pil_image.filepath = current_filepath

            self.loaded_image_tk = ImageTk.PhotoImage(self.original_pil_image)

            self.canvas.config(width=self.loaded_image_tk.width(), height=self.loaded_image_tk.height())
            new_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.loaded_image_tk)
            # Add the new (rotated) image back to canvas_objects
            self.canvas_objects.append({'id': new_image_id, 'type': 'image', 'coords': (0,0),
                                        'image_ref': self.loaded_image_tk,
                                        'filepath': getattr(self.original_pil_image, 'filepath', None)})

            self.shared_state.log("Image rotated and canvas updated.", level=logging.INFO)
            self._update_button_states(image_loaded=True)
            self._show_hint("Image rotated.")

        except Exception as e:
            self.shared_state.log(f"Error during image rotation: {e}", level=logging.ERROR)
            self._show_hint(f"Error rotating image: {e}")
            # Consider attempting to restore previous self.original_pil_image if rotation fails
            # This would require temporarily storing it before the transpose operation.
            # For now, if it fails, the state might be inconsistent.


    def save_image_action(self):
        self.shared_state.log("Save image action called.", level=logging.INFO)
        if not self.original_pil_image:
            self._show_hint("No image to save.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
            title="Save Image As",
            parent=self.frame
        )
        if not filepath:
            self.shared_state.log("Save image cancelled.", level=logging.INFO)
            return

        try:
            image_to_save = self.original_pil_image

            has_drawings = any(obj['type'] != 'image' for obj in self.canvas_objects)

            if has_drawings:
                 self.shared_state.log("Saving image. NOTE: Drawings on canvas are NOT composited onto the saved image in this version.", level=logging.WARNING)
                 self._show_hint("Note: Drawings are not saved onto the image yet.")


            image_to_save.save(filepath)
            self.shared_state.log(f"Image saved to {filepath}", level=logging.INFO)
            self._show_hint(f"Image saved to {filepath}")
        except Exception as e:
            self.shared_state.log(f"Error saving image: {e}", level=logging.ERROR)
            self._show_hint(f"Error saving image: {e}")


    def cancel_general_action(self):
        self.shared_state.log("General cancel action called (not in Edit/Crop mode).", level=logging.INFO)

        action_taken = False
        # If the main image is "selected" (i.e., has resize handles), deselect it.
        if self.selected_object_id:
            obj_data = self._get_object_from_canvas_objects(self.selected_object_id)
            if obj_data and obj_data['type'] == 'image':
                self.shared_state.log("Clearing image selection (resize handles).", level=logging.DEBUG)
                self._remove_selection_visual(self.selected_object_id) # This clears handles for image
                self.selected_object_id = None
                self._show_hint("Image selection (for resize) cleared.")
                action_taken = True
            # No other type of selection should be active if not in edit mode.

        # If no selection was cleared, and an image exists with a known filepath,
        # offer to revert to the last loaded/saved state of that image.
        if not action_taken and self.original_pil_image and hasattr(self.original_pil_image, 'filepath') and self.original_pil_image.filepath:
            # TODO: Potentially add a confirmation dialog here if this revert is too destructive.
            # For now, direct revert as per simplified undo.
            self.shared_state.log(f"Reverting to image from filepath: {self.original_pil_image.filepath}", level=logging.INFO)
            self.load_image_action(filepath=self.original_pil_image.filepath, internal_call=True)
            # load_image_action will call _update_button_states and show a hint.
            self._show_hint("Reverted to initially loaded image state.") # Overwrite load_image_action's hint
            action_taken = True

        if not action_taken:
            self._show_hint("No specific action to cancel or revert.")

        # Ensure UI state is consistent, though load_image_action also calls it.
        self._update_button_states(image_loaded=bool(self.original_pil_image),
                                   in_edit_mode=self._in_edit_mode,
                                   in_crop_mode=self._in_crop_mode)


    def save_edit_action(self):
        self.shared_state.log("Save edit action called.", level=logging.INFO)
        # This means user is in edit mode and clicks "Save Edit"
        # Here, we should "bake" the drawings onto the original_pil_image
        # This is a complex operation (render canvas items to PIL image).
        # For now, it will just exit edit mode.
        self.shared_state.log("Drawings NOT baked onto image in this version. Exiting Edit Mode.", level=logging.WARNING)
        self._in_edit_mode = False # Exit edit mode
        # self.drawing_toolbar_frame.pack_forget() # Handled by _update_button_states
        if self.selected_object_id:
            self._remove_selection_visual(self.selected_object_id)
            self.selected_object_id = None
            self._clear_resize_handles()
        self._update_button_states(image_loaded=bool(self.original_pil_image),
                                   in_edit_mode=self._in_edit_mode,
                                   in_crop_mode=self._in_crop_mode)
        # Status bar update is handled by _update_button_states based on new mode
        # self._show_hint("Exited Edit Mode. Drawing changes are visual only.")


    def cancel_edit_action(self):
        self.shared_state.log("Cancel edit action called.", level=logging.INFO)
        # User is in edit mode and clicks "Cancel Edit"
        # This should discard any drawings made *in the current edit session*.
        # For simplicity now, it will clear ALL drawings and exit edit mode.
        # A more robust solution would track drawings per session.
        if self.original_pil_image: # Only clear drawings if there's an image context
            image_item_id = self._find_image_object_id()
            items_to_delete = [obj['id'] for obj in self.canvas_objects if obj['id'] != image_item_id]
            for item_id in items_to_delete:
                try:
                    self.canvas.delete(item_id)
                except tk.TclError:
                    pass # Item might already be gone
            self.canvas_objects = [obj for obj in self.canvas_objects if obj['id'] == image_item_id]
            self.shared_state.log("Cleared all drawings from canvas (kept base image).", level=logging.INFO)

        self._in_edit_mode = False # Exit edit mode
        self.drawing_toolbar_frame.pack_forget()
        if self.selected_object_id:
            self._remove_selection_visual(self.selected_object_id)
            self.selected_object_id = None
            self._clear_resize_handles()
        self._update_button_states(image_loaded=bool(self.original_pil_image),
                                   in_edit_mode=self._in_edit_mode,
                                   in_crop_mode=self._in_crop_mode)
        self._show_hint("Drawings cancelled. Exited Edit Mode.")


    def confirm_crop_action(self):
        self.shared_state.log("Confirm crop action called.", level=logging.INFO)
        if self.crop_area and self.original_pil_image:
            self.crop_image_action() # Use existing logic to perform the crop
        else:
            self._show_hint("No crop area selected or no image loaded.")

        self._in_crop_mode = False # Exit crop mode
        # crop_buttons_frame hide is handled by _update_button_states
        self._update_button_states(image_loaded=bool(self.original_pil_image),
                                   in_edit_mode=self._in_edit_mode,
                                   in_crop_mode=self._in_crop_mode)


    def cancel_crop_action(self):
        self.shared_state.log("Cancel crop action called.", level=logging.INFO)
        if self.crop_rect_id: # Visual selection rectangle
            self.canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None
        if self.temp_shape_id: # Temporary interactive selection
            self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = None
        self.crop_area = None

        self._in_crop_mode = False # Exit crop mode
        self._update_button_states(image_loaded=bool(self.original_pil_image),
                                   in_edit_mode=self._in_edit_mode,
                                   in_crop_mode=self._in_crop_mode)
        self._show_hint("Crop cancelled.")

    # --- Helper Methods ---
    def _show_hint(self, message):
        if self.status_bar:
            self.status_bar.config(text=message)
        else:
            simpledialog.messagebox.showinfo("Hint", message, parent=self.frame)

    def _update_button_states(self, image_loaded=False, in_edit_mode=False, in_crop_mode=False):
        """Updates the enable/disable state of all relevant UI controls."""
        no_image = not image_loaded
        normal_mode = image_loaded and not in_edit_mode and not in_crop_mode

        # Always available
        if self.btn_open_image: self.btn_open_image.config(state=tk.NORMAL)

        # Available only when an image is loaded and not in a special mode
        if self.btn_edit_mode: self.btn_edit_mode.config(state=tk.NORMAL if normal_mode else tk.DISABLED)
        if self.btn_rotate: self.btn_rotate.config(state=tk.NORMAL if normal_mode else tk.DISABLED) # Group for rotate
        if self.btn_crop: self.btn_crop.config(state=tk.NORMAL if normal_mode else tk.DISABLED)

        # Main Save/Cancel buttons - behavior changes with mode
        if self.btn_save:
            self.btn_save.config(state=tk.NORMAL if image_loaded else tk.DISABLED)
            if in_edit_mode:
                self.btn_save.config(text="Save Edit", command=self.save_edit_action)
            elif in_crop_mode: # Crop mode will have its own confirm/cancel
                self.btn_save.config(state=tk.DISABLED)
            else: # Normal mode or after an action
                self.btn_save.config(text="Save File", command=self.save_image_action)

        if self.btn_cancel:
            self.btn_cancel.config(state=tk.NORMAL if image_loaded else tk.DISABLED)
            if in_edit_mode:
                self.btn_cancel.config(text="❌ Cancel Edit", command=self.cancel_edit_action)
            elif in_crop_mode: # Crop mode will have its own confirm/cancel buttons, main cancel disabled
                self.btn_cancel.config(state=tk.DISABLED)
            else: # Normal mode or after an action
                self.btn_cancel.config(text="❌ Cancel Action", command=self.cancel_general_action)

        # Show/Hide Drawing Toolbar Frame
        if hasattr(self, 'drawing_toolbar_frame') and self.drawing_toolbar_frame:
            if in_edit_mode:
                self.drawing_toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
            else:
                self.drawing_toolbar_frame.pack_forget()

        # Enable/Disable Drawing-related tools (they are on the drawing_toolbar_frame)
        for tool_btn in self.drawing_tool_buttons.values():
            if tool_btn: tool_btn.config(state=tk.NORMAL if in_edit_mode else tk.DISABLED) # Already hidden if not in_edit_mode, but good practice
        if self.btn_pen_color: self.btn_pen_color.config(state=tk.NORMAL if in_edit_mode else tk.DISABLED)
        if self.btn_add_text: self.btn_add_text.config(state=tk.NORMAL if in_edit_mode else tk.DISABLED)
        if self.font_family_combo: self.font_family_combo.config(state=tk.NORMAL if in_edit_mode else tk.DISABLED)
        if self.font_size_spinbox: self.font_size_spinbox.config(state=tk.NORMAL if in_edit_mode else tk.DISABLED)
        if self.btn_select_object: self.btn_select_object.config(state=tk.NORMAL if in_edit_mode else tk.DISABLED)
        if self.btn_delete_selected: self.btn_delete_selected.config(state=tk.NORMAL if in_edit_mode and self.selected_object_id else tk.DISABLED)


        # Show/Hide Crop Toolbar Frame (crop_buttons_frame)
        if hasattr(self, 'crop_buttons_frame') and self.crop_buttons_frame:
            if in_crop_mode:
                self.crop_buttons_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
                if self.btn_confirm_crop: self.btn_confirm_crop.config(state=tk.NORMAL)
                if self.btn_cancel_crop: self.btn_cancel_crop.config(state=tk.NORMAL)
            else:
                self.crop_buttons_frame.pack_forget()

        # Legacy buttons (should ideally be removed from class attributes later)
        if self.btn_rotate_left: self.btn_rotate_left.config(state=tk.DISABLED)
        if self.btn_rotate_right: self.btn_rotate_right.config(state=tk.DISABLED)

        # Update status bar
        if self.status_bar:
            if no_image:
                self.status_bar.config(text="Please open an image.")
            elif in_edit_mode:
                self.status_bar.config(text="Edit Mode (Drawing/Typing)")
            elif in_crop_mode:
                self.status_bar.config(text="Crop Mode - Select area, then Confirm/Cancel.")
            else: # Image is loaded, not in edit or crop mode
                self.status_bar.config(text="Image loaded. Ready.")

        # Disable canvas interactions if not in an appropriate mode
        if self.canvas:
            if not image_loaded or (not in_edit_mode and not in_crop_mode and self.current_tool not in ["select_crop_visual_only"]): # select_crop_visual_only is a placeholder idea
                # self.canvas.unbind("<Button-1>")
                # self.canvas.unbind("<B1-Motion>")
                # self.canvas.unbind("<ButtonRelease-1>")
                # Instead of unbinding, let the event handlers check the current mode/state
                pass
            else: # Rebind if they were unbound, or ensure they are active
                # self.canvas.bind("<Button-1>", self.start_draw)
                # self.canvas.bind("<B1-Motion>", self.draw)
                # self.canvas.bind("<ButtonRelease-1>", self.stop_draw)
                pass


    def _clear_all_canvas_state(self):
        """Clears canvas, object tracking, selection, and temporary states."""
        if self.canvas:
            self.canvas.delete("all")
        self.canvas_objects = []
        self.selected_object_id = None
        self.original_item_options = {} # Clear stored original options

        if self.crop_rect_id and self.canvas: # crop_rect_id might exist even if canvas.delete("all") was called
            # self.canvas.delete(self.crop_rect_id) # Already handled by delete("all")
            pass
        self.crop_rect_id = None
        self.crop_area = None

        if self.temp_shape_id and self.canvas:
            # self.canvas.delete(self.temp_shape_id) # Already handled by delete("all")
            pass
        self.temp_shape_id = None

        self._clear_resize_handles() # Ensure no handles are left if state is cleared externally

        self.shared_state.log("Canvas state cleared (objects, selection, temp items).", level=logging.DEBUG)

    def _get_handle_at_position(self, x, y):
        """Check if a click is on any resize handle."""
        for handle_info in self.resize_handles:
            coords = self.canvas.coords(handle_info['id'])
            if coords and coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
                return handle_info
        return None

    def _clear_resize_handles(self):
        if hasattr(self, 'canvas') and self.canvas: # Ensure canvas exists
            for handle_info in self.resize_handles:
                try:
                    self.canvas.delete(handle_info['id'])
                except tk.TclError:
                    pass # Handle might have been deleted already
        self.resize_handles = []
        self.current_resize_handle_info = None # Clear any active resize operation

    def _draw_resize_handles(self, item_id):
        self._clear_resize_handles()
        obj_data = self._get_object_from_canvas_objects(item_id)
        if not obj_data or obj_data['type'] not in ['rectangle', 'image']:
            return

        coords = []
        if obj_data['type'] == 'rectangle':
            coords = list(obj_data['coords']) # x1, y1, x2, y2
        elif obj_data['type'] == 'image':
            img_x, img_y = obj_data['coords']
            # Need image dimensions. Assuming image_ref on obj_data is the tk image
            tk_image = obj_data.get('image_ref')
            if tk_image:
                coords = [img_x, img_y, img_x + tk_image.width(), img_y + tk_image.height()]
            else: # Fallback if image_ref is missing, though it shouldn't be
                self.shared_state.log(f"Cannot draw handles for image {item_id}, missing image_ref.", level=logging.WARNING)
                return

        if not coords or len(coords) < 4:
            self.shared_state.log(f"Cannot draw handles for {obj_data['type']} {item_id}, invalid coords: {coords}", level=logging.WARNING)
            return

        x1, y1, x2, y2 = coords[0], coords[1], coords[2], coords[3]

        # Define handle positions (types and their calculation from main bbox)
        # For 4 corners: nw, ne, sw, se
        handle_defs = {
            'nw': (x1, y1),
            'ne': (x2 - self.handle_size, y1),
            'sw': (x1, y2 - self.handle_size),
            'se': (x2 - self.handle_size, y2 - self.handle_size),
            # TODO: Add mid-point handles ('n', 's', 'w', 'e') if desired
        }

        for handle_type, (hx, hy) in handle_defs.items():
            handle_id = self.canvas.create_rectangle(
                hx, hy, hx + self.handle_size, hy + self.handle_size,
                fill=self.handle_fill, outline=self.handle_outline,
                tags=('resize_handle', f'handle_for_{item_id}')
            )
            self.resize_handles.append({'id': handle_id, 'type': handle_type, 'object_id': item_id,
                                        'ref_x': hx, 'ref_y': hy }) # Store ref for simple move later
        self.shared_state.log(f"Drew {len(self.resize_handles)} resize handles for item {item_id}", level=logging.DEBUG)


    def create_ui(self):
        self.shared_state.log("ImageEditorModule creating UI...", level=logging.INFO)

        # Configure the main frame (self.frame) created by the parent Module class
        self.frame.config(borderwidth=2, relief=tk.GROOVE)
        # self.frame.columnconfigure(0, weight=1)
        # self.frame.rowconfigure(1, weight=1) # Remove grid config for self.frame

        # --- Main Controls Toolbar ---
        main_controls_frame = ttk.Frame(self.frame)
        main_controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.btn_open_image = ttk.Button(main_controls_frame, text="Open Image", command=self.load_image_action)
        self.btn_open_image.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_edit_mode = ttk.Button(main_controls_frame, text="🔧 Edit Mode", command=self.toggle_edit_mode)
        self.btn_edit_mode.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_rotate = ttk.Button(main_controls_frame, text="🔁 Rotate", command=self.rotate_action_menu) # Placeholder
        self.btn_rotate.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_crop = ttk.Button(main_controls_frame, text="✂️ Crop", command=self.toggle_crop_mode) # Placeholder
        self.btn_crop.pack(side=tk.LEFT, padx=2, pady=2)

        # Spacer or align right for Save/Cancel
        ttk.Label(main_controls_frame).pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.btn_save = ttk.Button(main_controls_frame, text="💾 Save File", command=self.save_image_action) # Command changes
        self.btn_save.pack(side=tk.RIGHT, padx=2, pady=2)

        self.btn_cancel = ttk.Button(main_controls_frame, text="❌ Cancel Action", command=self.cancel_general_action) # Command changes
        self.btn_cancel.pack(side=tk.RIGHT, padx=2, pady=2)


        # --- Drawing Tools Toolbar (Initially hidden or disabled, shown in Edit Mode) ---
        self.drawing_toolbar_frame = ttk.Frame(self.frame)
        # Packed/unpacked by _update_button_states or toggle_edit_mode
        # self.drawing_toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)

        drawing_tools_map = {"Freehand": "freehand", "Line": "line", "Rectangle": "rectangle", "Circle": "circle"}
        for text, tool_name_val in drawing_tools_map.items():
            btn = ttk.Button(self.drawing_toolbar_frame, text=text,
                                command=lambda t=tool_name_val: self.select_tool(t))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            self.drawing_tool_buttons[tool_name_val] = btn

        self.btn_pen_color = ttk.Button(self.drawing_toolbar_frame, text="Pen Color", command=self.choose_color)
        self.btn_pen_color.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_add_text = ttk.Button(self.drawing_toolbar_frame, text="Add Text", command=lambda: self.select_tool("text"))
        self.btn_add_text.pack(side=tk.LEFT, padx=2, pady=2)

        font_label = ttk.Label(self.drawing_toolbar_frame, text="Font:")
        font_label.pack(side=tk.LEFT, padx=(5,2), pady=2)
        self.font_family_combo = ttk.Combobox(self.drawing_toolbar_frame, textvariable=self.current_font_family, width=15)
        self.font_family_combo['values'] = ["Arial", "Times New Roman", "Courier New", "Verdana", "Helvetica", "Calibri", "Georgia"]
        self.font_family_combo.pack(side=tk.LEFT, padx=2, pady=2)
        self.font_family_combo.set("Arial")

        size_label = ttk.Label(self.drawing_toolbar_frame, text="Size:")
        size_label.pack(side=tk.LEFT, padx=(5,2), pady=2)
        self.font_size_spinbox = ttk.Spinbox(self.drawing_toolbar_frame, from_=8, to_=72, textvariable=self.current_font_size, width=5)
        self.font_size_spinbox.pack(side=tk.LEFT, padx=2, pady=2)
        self.current_font_size.set(12)

        self.btn_select_object = ttk.Button(self.drawing_toolbar_frame, text="Select Shape", command=lambda: self.select_tool("select"))
        self.btn_select_object.pack(side=tk.LEFT, padx=2, pady=2)

        self.btn_delete_selected = ttk.Button(self.drawing_toolbar_frame, text="Delete Shape", command=self.delete_selected_object)
        self.btn_delete_selected.pack(side=tk.LEFT, padx=2, pady=2)

        # --- Crop Confirmation Toolbar (Initially hidden, shown in Crop Mode) ---
        self.crop_buttons_frame = ttk.Frame(self.frame)
        # self.crop_buttons_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2) # Packed by _update_button_states

        self.btn_confirm_crop = ttk.Button(self.crop_buttons_frame, text="✅ Confirm Crop", command=self.confirm_crop_action)
        self.btn_confirm_crop.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_cancel_crop = ttk.Button(self.crop_buttons_frame, text="❌ Cancel Crop", command=self.cancel_crop_action)
        self.btn_cancel_crop.pack(side=tk.LEFT, padx=2, pady=2)


        # --- Canvas ---
        canvas_container_frame = ttk.Frame(self.frame)
        canvas_container_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=(0,5))

        self.canvas = tk.Canvas(canvas_container_frame, bg="white", relief="sunken", borderwidth=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.stop_draw)

        # --- Status Bar ---
        self.status_bar = ttk.Label(self.frame, text="Please open an image.", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0,5))


        # Old buttons that are being phased out or integrated - keep references if needed for now for _update_button_states
        # These buttons are not created in the new UI structure directly.
        # Their functionality is being absorbed by the new main buttons or context specific ones.
        # Example: self.btn_rotate_left, self.btn_rotate_right, self.crop_select_button, self.crop_image_button
        # For now, we'll let _update_button_states try to disable them if they were to exist.
        # A cleaner approach would be to remove these attributes and their handling from _update_button_states
        # once all functionality is migrated. For now, it's safer to keep the disable logic.
        self.btn_rotate_left = None # Was: ttk.Button(toolbar_frame, text="Rotate Left 90°", command=lambda: self.rotate_image_action("left"))
        self.btn_rotate_right = None # Was: ttk.Button(toolbar_frame, text="Rotate Right 90°", command=lambda: self.rotate_image_action("right"))
        # self.crop_select_button = None # Was: ttk.Button(toolbar_frame, text="Select Crop Area", ...)
        # self.crop_image_button = None # Was: ttk.Button(toolbar_frame, text="Crop Image", ...)


        self.shared_state.log("ImageEditorModule UI created.", level=logging.INFO)

    def select_tool(self, tool_name):
        # This method is primarily for drawing tools now, or object selection within edit mode,
        # or for setting the crop selection tool.

        # Allow "crop_select" tool regardless of edit_mode, as it's set by toggle_crop_mode
        if tool_name != "crop_select" and not self.is_in_edit_mode() and tool_name != "none":
            self.shared_state.log(f"Tool selection '{tool_name}' ignored, not in edit mode or not 'crop_select'.", logging.DEBUG)
            if tool_name == "select":
                self._show_hint("Enter Edit Mode to select shapes.")
            return

        # Clean up previous tool's temporary visuals if necessary
        # (Handled by specific mode toggles or actions now, e.g. exiting crop mode clears crop rect)
        # if self.current_tool == "crop_select" and tool_name != "crop_select":
        #     if self.temp_shape_id:
        #         self.canvas.delete(self.temp_shape_id)
        #         self.temp_shape_id = None

        # Deselect any currently selected drawing object when changing tools (unless new tool is 'select' itself)
        if self.is_in_edit_mode() and self.selected_object_id and tool_name != "select":
            self._remove_selection_visual(self.selected_object_id)
            self._clear_resize_handles()
            self.selected_object_id = None
            self.shared_state.log("Drawing selection cleared due to tool change in Edit Mode.", level=logging.DEBUG)

        self.current_tool = tool_name
        self.shared_state.log(f"Selected tool: {self.current_tool}", level=logging.DEBUG)


    def choose_color(self):
        if not self.is_in_edit_mode():
            self._show_hint("Pen color can only be changed in Edit Mode.")
            return
        color_code = colorchooser.askcolor(title="Choose pen color", initialcolor=self.pen_color, parent=self.frame)
        if color_code and color_code[1]: # color_code[1] is the hex string
            self.pen_color = color_code[1]
            self.shared_state.log(f"Pen color changed to: {self.pen_color}", level=logging.DEBUG)

    def load_image_action(self, filepath=None, internal_call=False):
        if not internal_call or not filepath: # If not an internal call, always ask for filepath
            chosen_filepath = filedialog.askopenfilename(
                title="Select an Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
            )
            if not chosen_filepath:
                self.shared_state.log("Image loading cancelled by user.", level=logging.INFO)
                if not self.original_pil_image: # If still no image after cancellation
                    self._update_button_states(image_loaded=False)
                return
            filepath = chosen_filepath # Use the path chosen by user

        if not filepath: # Should not happen if logic above is correct, but as a safe guard
            self.shared_state.log("No filepath provided for image loading.", level=logging.WARNING)
            if not self.original_pil_image:
                 self._update_button_states(image_loaded=False)
            return

        self.shared_state.log(f"Attempting to load image: {filepath}", level=logging.INFO)
        try:
            # Exit any active modes before loading new image
            if self.is_in_edit_mode(): self.toggle_edit_mode() # Will call update_button_states
            if self.is_in_crop_mode(): self.toggle_crop_mode() # Will call update_button_states

            self._clear_all_canvas_state()

            self.original_pil_image = Image.open(filepath)
            self.original_pil_image.filepath = filepath # Store for potential reload/save
            self.loaded_image_tk = ImageTk.PhotoImage(self.original_pil_image)

            self.canvas.config(width=self.loaded_image_tk.width(), height=self.loaded_image_tk.height())
            item_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.loaded_image_tk)
            self.canvas_objects.append({'id': item_id, 'type': 'image', 'coords': (0,0),
                                        'image_ref': self.loaded_image_tk,
                                        'filepath': filepath})

            self.shared_state.log(f"Image '{filepath}' loaded. Canvas cleared and resized.", level=logging.INFO)
            self._update_button_states(image_loaded=True) # Key update after successful load

        except Exception as e:
            self.shared_state.log(f"Error loading image '{filepath}': {e}", level=logging.ERROR)
            self.original_pil_image = None
            self.loaded_image_tk = None
            # Optionally, display an error message to the user on the canvas or a dialog

    def start_draw(self, event):
        # Prevent drawing if an image is loaded and no specific "draw on image" tool is selected.
        # For now, we allow drawing over the image. Future enhancements could change this.
        # if self.loaded_image_tk and self.current_tool not in ["crop", ...]: # Example
        #     self.shared_state.log("Drawing is disabled while an image is loaded, unless a specific image tool is selected.", level=logging.DEBUG)
        #     return

        if self.current_tool == "text":
            self.handle_text_add(event)
            return

        if self.current_tool == "select":
            # Priority: Check if a resize handle was clicked
            clicked_handle_info = self._get_handle_at_position(event.x, event.y)
            if clicked_handle_info:
                self.current_resize_handle_info = clicked_handle_info
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                # Ensure the main associated object is considered selected if a handle is grabbed
                if self.selected_object_id != clicked_handle_info['object_id']:
                    if self.selected_object_id: # Deselect previous object first
                        self._remove_selection_visual(self.selected_object_id)
                        # Handles should be cleared by _draw_resize_handles or if selection changes
                    self.selected_object_id = clicked_handle_info['object_id']
                    self._apply_selection_visual(self.selected_object_id) # Apply visual to main object
                    # Handles will be redrawn by _draw_resize_handles if not already present
                    self._draw_resize_handles(self.selected_object_id)


                self.shared_state.log(f"Resize handle '{clicked_handle_info['type']}' for object {clicked_handle_info['object_id']} clicked. Resize drag initiated.", level=logging.INFO)
                return # Do not proceed to object selection/drag

            # If no handle was clicked, proceed with object selection/drag
            self.current_resize_handle_info = None # Ensure no resize op is active
            self.handle_selection(event) # This might change self.selected_object_id

            if self.selected_object_id:
                # Object selected or re-selected, prepare for dragging object
                self.drag_start_x = event.x
                self.drag_start_y = event.y
                self.canvas.tag_raise(self.selected_object_id)
                # Resize handles are drawn by handle_selection via _apply_selection_visual -> _draw_resize_handles
                self.shared_state.log(f"Object {self.selected_object_id} selected/re-selected. Drag initiated.", level=logging.DEBUG)
            else:
                # Clicked on empty space or deselected an item
                self.drag_start_x = None
                self.drag_start_y = None
                self._clear_resize_handles() # Clear handles if nothing is selected
            return

        if self.current_tool == "crop_select":
            if not self.original_pil_image:
                self.shared_state.log("Load an image before selecting crop area.", level=logging.WARNING)
                return
            # Clear previous visual selection rectangle if one exists from a *previous* selection
            if self.crop_rect_id:
                 self.canvas.delete(self.crop_rect_id)
                 self.crop_rect_id = None
            # also clear temp_shape_id for the current interactive selection
            if self.temp_shape_id:
                self.canvas.delete(self.temp_shape_id)
                self.temp_shape_id = None
            self.crop_area = None # Reset crop area when starting a new selection

        self.start_x, self.start_y = event.x, event.y
        if self.current_tool == "freehand":
            self.last_x, self.last_y = event.x, event.y

        self.shared_state.log(f"Draw started at ({event.x}, {event.y}) with {self.current_tool}", level=logging.DEBUG)


    def draw(self, event):
        if self.start_x is None or self.start_y is None:
            # For crop_select or other tools that don't use drag_start_x for drawing
            if self.current_tool == "crop_select" and not self.original_pil_image:
                return
            # For select tool, if drag_start_x is None, it means we are not dragging an object.
            if self.current_tool == "select" and self.drag_start_x is None :
                 return # Not dragging anything.
            # For other drawing tools, if start_x is None, we haven't started drawing.
            if self.current_tool not in ["select", "crop_select"] and self.start_x is None : # start_x is for drawing tools
                 return
            # If it's a select tool but no object is selected, or not dragging, do nothing in draw.
            if self.current_tool == "select" and (not self.selected_object_id or self.drag_start_x is None):
                return


        current_x, current_y = event.x, event.y

        if self.current_tool == "select":
            if self.current_resize_handle_info and self.drag_start_x is not None: # Resizing an object
                obj_id_being_resized = self.current_resize_handle_info['object_id']
                obj_data = self._get_object_from_canvas_objects(obj_id_being_resized)
                if not obj_data: return

                handle_type = self.current_resize_handle_info['type']
                min_size = self.handle_size * 2

                if obj_data['type'] == 'rectangle':
                    orig_coords = self.canvas.coords(obj_id_being_resized)
                    x1, y1, x2, y2 = orig_coords

                    if handle_type == 'nw':
                        x1, y1 = current_x, current_y
                    elif handle_type == 'ne':
                        x2, y1 = current_x, current_y
                    elif handle_type == 'sw':
                        x1, y2 = current_x, current_y
                    elif handle_type == 'se':
                        x2, y2 = current_x, current_y

                    # Ensure positive width/height and minimum size
                    if x2 < x1 + min_size: x2 = x1 + min_size
                    if y2 < y1 + min_size: y2 = y1 + min_size

                    self.canvas.coords(obj_id_being_resized, x1, y1, x2, y2)
                    self._draw_resize_handles(obj_id_being_resized)

                elif obj_data['type'] == 'image' and self.original_pil_image:
                    # For images, only implement 'se' handle for simplicity first
                    if handle_type == 'se':
                        img_obj_x, img_obj_y = obj_data['coords'] # Top-left from our tracking

                        new_width = current_x - img_obj_x
                        new_height = current_y - img_obj_y

                        if new_width >= min_size and new_height >= min_size:
                            try:
                                # Use the module's self.original_pil_image as the source for resize
                                # This assumes the selected image IS the main loaded image.
                                # If multiple images were supported, a direct reference in obj_data would be needed.
                                pil_image_to_resize = Image.open(self.original_pil_image.filepath) # Re-open for fresh resize
                                resized_pil = pil_image_to_resize.resize((int(new_width), int(new_height)), Image.LANCZOS)

                                # Update the PhotoImage store FOR THIS IMAGE OBJECT
                                # This is tricky because self.loaded_image_tk is module-level.
                                # For robust multi-image support, each image object would need its own PhotoImage.
                                # For now, if we resize the main image, update self.loaded_image_tk
                                if obj_id_being_resized == self._find_image_object_id(): # Check if it's the main image
                                    self.loaded_image_tk = ImageTk.PhotoImage(resized_pil)
                                    self.canvas.itemconfig(obj_id_being_resized, image=self.loaded_image_tk)

                                    # Update the image_ref in canvas_objects if it's the main image
                                    obj_data['image_ref'] = self.loaded_image_tk
                                    # Storing current display width/height could be useful
                                    obj_data['current_width'] = new_width
                                    obj_data['current_height'] = new_height

                                    self._draw_resize_handles(obj_id_being_resized)
                                else:
                                     self.shared_state.log("Resizing non-primary image not fully supported yet.", level=logging.WARNING)

                            except Exception as e:
                                self.shared_state.log(f"Error resizing image: {e}", level=logging.ERROR)
                        else:
                            self.shared_state.log("Image resize too small, skipped.", level=logging.DEBUG)

                self.drag_start_x, self.drag_start_y = current_x, current_y # Update for next delta

            elif self.selected_object_id and self.drag_start_x is not None: # Moving an object
                dx = current_x - self.drag_start_x
                dy = current_y - self.drag_start_y
                if dx != 0 or dy != 0:
                    self.canvas.move(self.selected_object_id, dx, dy)
                    self._update_object_coords_in_tracking(self.selected_object_id, dx, dy)
                    # Redraw handles as the object moves
                    self._draw_resize_handles(self.selected_object_id)
                    self.drag_start_x = current_x
                    self.drag_start_y = current_y
            return # For select tool, drawing previews below are not relevant

        # This part is for drawing previews of shapes, not for select tool dragging
        if self.temp_shape_id:
            self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = None

        # Drawing previews for non-select tools
        if self.current_tool == "freehand":
            if self.last_x is not None and self.last_y is not None: # start_x, start_y are used for initial point
                self.canvas.create_line(self.last_x, self.last_y, current_x, current_y,
                                        fill=self.pen_color, width=self.pen_width,
                                        capstyle=tk.ROUND, smooth=tk.TRUE)
                self.last_x, self.last_y = current_x, current_y
        elif self.current_tool == "line":
            self.temp_shape_id = self.canvas.create_line(self.start_x, self.start_y, current_x, current_y,
                                                         fill=self.pen_color, width=self.pen_width)
        elif self.current_tool == "rectangle":
            self.temp_shape_id = self.canvas.create_rectangle(self.start_x, self.start_y, current_x, current_y,
                                                              outline=self.pen_color, width=self.pen_width)
        elif self.current_tool == "circle":
            self.temp_shape_id = self.canvas.create_oval(self.start_x, self.start_y, current_x, current_y,
                                                         outline=self.pen_color, width=self.pen_width)
        elif self.current_tool == "crop_select":
            if self.start_x is not None and self.start_y is not None: # Ensure crop selection has started
                self.temp_shape_id = self.canvas.create_rectangle(self.start_x, self.start_y, current_x, current_y,
                                                              outline="blue", dash=(4, 2), width=1)

    def stop_draw(self, event):
        if self.current_tool == "select":
            if self.current_resize_handle_info and self.drag_start_x is not None: # Finalizing a resize
                obj_id_resized = self.current_resize_handle_info['object_id']
                obj_data = self._get_object_from_canvas_objects(obj_id_resized)
                if obj_data:
                    if obj_data['type'] == 'rectangle':
                        final_coords = tuple(map(int, self.canvas.coords(obj_id_resized)))
                        obj_data['coords'] = final_coords
                        self.shared_state.log(f"Rectangle {obj_id_resized} resized to {final_coords}", level=logging.INFO)
                    elif obj_data['type'] == 'image':
                        # Update the main original_pil_image if it was the one resized
                        if obj_id_resized == self._find_image_object_id() and hasattr(self.loaded_image_tk, 'width'):
                            # Create a new PIL image from the Tk PhotoImage (which was updated)
                            # This is a bit of a workaround. Ideally, keep PIL as source of truth.
                            # For now, we assume self.original_pil_image was the source for resize op,
                            # and self.loaded_image_tk reflects the current visual state.
                            # If the image on canvas (self.loaded_image_tk) is the true state,
                            # then original_pil_image needs to be updated to match this.
                            # This means the resize operation should have updated self.original_pil_image too.

                            # Let's assume the resize in draw() updated the main self.original_pil_image
                            # if it was the one being resized.
                            # The 'coords' (top-left) for image are updated by _update_object_coords_in_tracking if moved.
                            # If resized using 'se' handle, only width/height changed.
                            # We need to make sure the self.original_pil_image reflects the final visual state.
                            # This could be done by making a new PIL image from the final loaded_image_tk, or
                            # ensuring the PIL image used for resize in draw() becomes the new self.original_pil_image.

                            # For now, assume self.original_pil_image was updated if it was the one targeted.
                            # The obj_data['image_ref'] should point to the current self.loaded_image_tk.
                            # And obj_data['coords'] should be its current top-left.
                            # Let's ensure the main original_pil_image is updated after an image resize.
                            if hasattr(self, 'loaded_image_tk') and self.loaded_image_tk : # Check if PhotoImage exists
                                img_width = self.loaded_image_tk.width()
                                img_height = self.loaded_image_tk.height()
                                # This is tricky: if original_pil_image was used as a base for resize,
                                # it should be updated to the final resized version.
                                # Let's assume the interactive resize in draw() already set the final PIL state
                                # for self.original_pil_image if it was the one being resized.
                                # For simplicity, we are not creating a new PIL image here from PhotoImage.
                                self.shared_state.log(f"Image {obj_id_resized} resize finalized. Display size: {img_width}x{img_height}", level=logging.INFO)
                                # Store current width/height with image object for future reference
                                obj_data['current_width'] = img_width
                                obj_data['current_height'] = img_height


                    self._draw_resize_handles(obj_id_resized) # Ensure handles are correctly placed after resize

                self.shared_state.log(f"Resize operation with handle {self.current_resize_handle_info['type']} ended.", level=logging.INFO)

            elif self.selected_object_id and self.drag_start_x is not None: # Finished moving an object
                self.shared_state.log(f"Object {self.selected_object_id} finished moving.", level=logging.INFO)

            self.drag_start_x = None
            self.drag_start_y = None
            self.current_resize_handle_info = None
            return

        # General stop_draw logic for other drawing tools
        if self.start_x is None or self.start_y is None:
            # This condition might be met if e.g. text tool was used, which returns early in start_draw
            # Or if select tool didn't initiate a drag.
            if self.current_tool not in ["text", "select"]: # Avoid logging for tools that don't use start_x/y for drawing completion
                 self.shared_state.log(f"stop_draw called for {self.current_tool} but no drawing started (start_x/y is None).", level=logging.DEBUG)
            return

        end_x, end_y = event.x, event.y

        if self.temp_shape_id:
            self.canvas.delete(self.temp_shape_id)
            self.temp_shape_id = None

        item_id = None
        obj_data = None
        options = {}

        if self.current_tool == "line":
            options = {'fill': self.pen_color, 'width': self.pen_width}
            item_id = self.canvas.create_line(self.start_x, self.start_y, end_x, end_y, **options)
            obj_data = {'id': item_id, 'type': 'line', 'coords': (self.start_x, self.start_y, end_x, end_y), 'options': options.copy()}
        elif self.current_tool == "rectangle":
            options = {'outline': self.pen_color, 'width': self.pen_width}
            item_id = self.canvas.create_rectangle(self.start_x, self.start_y, end_x, end_y, **options)
            obj_data = {'id': item_id, 'type': 'rectangle', 'coords': (self.start_x, self.start_y, end_x, end_y), 'options': options.copy()}
        elif self.current_tool == "circle":
            options = {'outline': self.pen_color, 'width': self.pen_width}
            item_id = self.canvas.create_oval(self.start_x, self.start_y, end_x, end_y, **options)
            obj_data = {'id': item_id, 'type': 'circle', 'coords': (self.start_x, self.start_y, end_x, end_y), 'options': options.copy()}
        elif self.current_tool == "freehand":
            # Freehand is a series of small lines; each segment is not individually tracked here.
            # Could be improved by grouping strokes, but for now, freehand is not a selectable object.
            self.last_x, self.last_y = None, None
        elif self.current_tool == "crop_select" and self.is_in_crop_mode():
            if not self.original_pil_image:
                self.start_x, self.start_y = None, None # Reset drawing state
                return

            min_crop_dim = 10 # Minimum width/height for a crop
            x1_c, y1_c = min(self.start_x, end_x), min(self.start_y, end_y)
            x2_c, y2_c = max(self.start_x, end_x), max(self.start_y, end_y)

            # Boundary check against canvas dimensions (which should match image)
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            x1_c = max(0, x1_c); y1_c = max(0, y1_c)
            x2_c = min(canvas_w, x2_c); y2_c = min(canvas_h, y2_c)

            if (x2_c - x1_c) < min_crop_dim or (y2_c - y1_c) < min_crop_dim:
                self.shared_state.log(f"Crop area too small: {(x1_c,y1_c,x2_c,y2_c)}. Min dim: {min_crop_dim}", level=logging.WARNING)
                self._show_hint(f"Crop area is too small. Minimum size is {min_crop_dim}x{min_crop_dim} pixels.")
                self.crop_area = None
                if self.crop_rect_id: self.canvas.delete(self.crop_rect_id); self.crop_rect_id = None
                # temp_shape_id was already deleted if it existed
            else:
                self.crop_area = (x1_c, y1_c, x2_c, y2_c)
                if self.crop_rect_id: self.canvas.delete(self.crop_rect_id) # Delete old one if exists
                # Create the persistent visual selection rectangle
                self.crop_rect_id = self.canvas.create_rectangle(
                    x1_c, y1_c, x2_c, y2_c,
                    outline="blue", dash=(4,2), width=1, tags=("crop_selection_rect",)
                )
                self.shared_state.log(f"Crop area selected: {self.crop_area}", level=logging.INFO)
                self._show_hint(f"Crop area selected. Click 'Confirm Crop' or 'Cancel Crop'.")

            self.start_x, self.start_y = None, None # Reset for next potential selection
            return # Crop selection doesn't add to canvas_objects in the same way as drawings

        if item_id and obj_data:
            self.canvas_objects.append(obj_data)
            self.shared_state.log(f"Created {obj_data['type']} (ID: {item_id}). Object count: {len(self.canvas_objects)}", level=logging.DEBUG)

        self.shared_state.log(f"Draw action ended for {self.current_tool}. Coords: ({self.start_x},{self.start_y})-({end_x},{end_y})", level=logging.DEBUG)
        self.start_x, self.start_y = None, None


    def _update_object_coords_in_tracking(self, item_id, dx, dy):
        obj_dict = self._get_object_from_canvas_objects(item_id)
        if not obj_dict:
            self.shared_state.log(f"Cannot update coords for non-tracked object ID {item_id}", level=logging.WARNING)
            return

        obj_type = obj_dict.get('type')
        current_coords = list(obj_dict.get('coords', [])) # Make it a list for modification

        if obj_type in ["line", "rectangle", "circle"]:
            if len(current_coords) < 4 : # Basic check
                 self.shared_state.log(f"Invalid coords for shape {item_id}: {current_coords}", level=logging.ERROR)
                 return
            for i in range(len(current_coords)):
                current_coords[i] += dx if i % 2 == 0 else dy
            obj_dict['coords'] = tuple(current_coords)
        elif obj_type in ["text", "image"]:
            if len(current_coords) < 2 : # Basic check
                 self.shared_state.log(f"Invalid coords for {obj_type} {item_id}: {current_coords}", level=logging.ERROR)
                 return
            current_coords[0] += dx
            current_coords[1] += dy
            obj_dict['coords'] = tuple(current_coords)
        else:
            self.shared_state.log(f"Attempted to update coords for unknown object type: {obj_type}", level=logging.WARNING)
            return
        # self.shared_state.log(f"Updated coords for {obj_type} ID {item_id} to {obj_dict['coords']}", level=logging.DEBUG)

    def _find_image_object_id(self):
        """Helper to find the ID of the main image object on canvas."""
        for obj in self.canvas_objects:
            if obj['type'] == 'image':
                return obj['id']
        return None

    def crop_image_action(self):
        if not self.original_pil_image:
            self.shared_state.log("Cannot crop: No image loaded.", level=logging.WARNING)
            # Optionally: tkinter.messagebox.showwarning("Crop Error", "No image loaded.")
            return
        if not self.crop_area:
            self.shared_state.log("Cannot crop: No crop area selected.", level=logging.WARNING)
            # Optionally: tkinter.messagebox.showwarning("Crop Error", "No crop area selected.")
            return

        x1, y1, x2, y2 = self.crop_area

        # Ensure coordinates are within the image bounds before cropping
        img_width, img_height = self.original_pil_image.size

        # Crop coords should already be clamped to image dimensions by select_tool/stop_draw
        # but a final check is good.
        x1_pil = max(0, int(x1)); y1_pil = max(0, int(y1)) # Ensure positive
        x2_pil = min(img_width, int(x2)); y2_pil = min(img_height, int(y2)) # Ensure within bounds


        min_crop_dim = 10 # Consistent with stop_draw
        if (x2_pil - x1_pil) < min_crop_dim or (y2_pil - y1_pil) < min_crop_dim:
            self.shared_state.log(f"Cannot crop: Invalid final crop dimensions. Area: {(x1_pil,y1_pil,x2_pil,y2_pil)} Image: {img_width}x{img_height}", level=logging.ERROR)
            if self.crop_rect_id and self.canvas:
                try: self.canvas.delete(self.crop_rect_id)
                except tk.TclError: pass # item might be gone
            self.crop_rect_id = None
            self.crop_area = None
            self._show_hint(f"Crop failed: Area too small (min {min_crop_dim}x{min_crop_dim}).")
            return

        try:
            self.shared_state.log(f"Cropping PIL image ({self.original_pil_image.size}) with box: {(x1_pil, y1_pil, x2_pil, y2_pil)}", level=logging.INFO)

            cropped_pil_image = self.original_pil_image.crop((x1_pil, y1_pil, x2_pil, y2_pil))
            original_filepath = getattr(self.original_pil_image, 'filepath', None)

            self._clear_all_canvas_state()

            self.original_pil_image = cropped_pil_image
            if original_filepath: self.original_pil_image.filepath = original_filepath
            self.loaded_image_tk = ImageTk.PhotoImage(self.original_pil_image)

            self.canvas.config(width=self.loaded_image_tk.width(), height=self.loaded_image_tk.height())
            new_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.loaded_image_tk)
            self.canvas_objects.append({'id': new_image_id, 'type': 'image', 'coords': (0,0),
                                        'image_ref': self.loaded_image_tk,
                                        'filepath': self.original_pil_image.filepath})

            self.shared_state.log("Image cropped and updated. Canvas objects reset.", level=logging.INFO)

        except Exception as e:
            self.shared_state.log(f"Error during image cropping: {e}", level=logging.ERROR)
            self._show_hint(f"Error cropping image: {e}")
            # Attempt to restore previous state if crop failed badly?
            # For now, _clear_all_canvas_state might leave a blank canvas if PIL crop fails.
            # This needs robust error handling if self.original_pil_image is corrupted.


    # def rotate_image_action(self, direction): # This method is effectively replaced by execute_rotation
    #     # Kept for a moment if any old part of code calls it, but should be removed.
    #     self.shared_state.log(f"Legacy rotate_image_action called with {direction}. Redirecting...", level=logging.WARNING)
    #     if direction == "left":
    #         self.execute_rotation(Image.ROTATE_90)
    #     elif direction == "right":
    #         self.execute_rotation(Image.ROTATE_270)
    #     else:
    #         self.shared_state.log(f"Unknown direction for legacy rotate: {direction}", level=logging.ERROR)


    def handle_text_add(self, event):
        if not self.canvas or not self.is_in_edit_mode():
            self._show_hint("Text can only be added in Edit Mode.")
            return

        x, y = event.x, event.y
        user_text = simpledialog.askstring("Input Text", "Enter text to add:", parent=self.frame)

        if user_text:
            font_family = self.current_font_family.get()
            font_size = self.current_font_size.get()
            font_spec = (font_family, font_size)
            options = {'fill': self.pen_color, 'font': font_spec, 'anchor': tk.NW, 'text': user_text}
            item_id = self.canvas.create_text(x, y, **options)

            # For text, 'coords' is just x,y. The 'text' content is important.
            obj_data = {'id': item_id, 'type': 'text', 'coords': (x,y),
                        'text': user_text, 'options': options.copy()}
            del obj_data['options']['text'] # text is already top-level key
            del obj_data['options']['anchor'] # anchor is assumed NW for simplicity or stored if varied

            self.canvas_objects.append(obj_data)
            self.shared_state.log(f"Text '{user_text}' (ID: {item_id}) added at ({x},{y}). Font: {font_family} {font_size}pt. Objects: {len(self.canvas_objects)}", level=logging.INFO)
        else:
            self.shared_state.log("Text input cancelled or empty.", level=logging.INFO)

    def _get_object_from_canvas_objects(self, item_id):
        for obj in self.canvas_objects:
            if obj['id'] == item_id:
                return obj
        return None

    def _apply_selection_visual(self, item_id):
        if item_id is None: return
        obj_data = self._get_object_from_canvas_objects(item_id)
        if not obj_data: return

        # Store original options before changing them
        # This simplistic approach only stores and modifies outline/width, fill for text
        # More robust would be to store specific original values for each property changed
        original_opts = {}

        item_type = obj_data.get('type')
        current_config = self.canvas.itemconfig(item_id)

        if item_type in ['rectangle', 'circle', 'line']:
            original_opts['outline'] = current_config['outline'][-1] if isinstance(current_config['outline'], tuple) else current_config['outline']
            original_opts['width'] = float(current_config['width'][-1] if isinstance(current_config['width'], tuple) else current_config['width'])
            self.original_item_options[item_id] = original_opts
            self.canvas.itemconfig(item_id, outline=self.selection_outline_color, width=self.selection_outline_width)
        elif item_type == 'text':
            original_opts['fill'] = current_config['fill'][-1] if isinstance(current_config['fill'], tuple) else current_config['fill']
            self.original_item_options[item_id] = original_opts
            # For text, changing fill might be confusing. Maybe draw a bounding box instead?
            # For now, just change fill color to selection color.
            self.canvas.itemconfig(item_id, fill=self.selection_outline_color)
        # Images don't have an 'outline' from itemconfig in the same way.
        # A bounding box could be drawn around selected images or text items.
        # This part can be enhanced later.
        self.shared_state.log(f"Applied selection visual to item {item_id}",level=logging.DEBUG)
        self._draw_resize_handles(item_id) # Draw handles whenever selection visual is applied


    def _remove_selection_visual(self, item_id):
        if item_id is None: return
        self._clear_resize_handles() # Always clear handles when deselecting
        obj_data = self._get_object_from_canvas_objects(item_id)
        if not obj_data:
            try: # Attempt to reset visuals even if not tracked, then bail
                self.canvas.itemconfig(item_id, outline="black", width=1)
                if item_id in self.original_item_options: del self.original_item_options[item_id]
            except tk.TclError: pass # Item might be deleted or not support outline
            self.shared_state.log(f"Visuals reset for untracked/deleted item {item_id}.",level=logging.DEBUG)
            return

        original_opts = self.original_item_options.get(item_id)
        item_type = obj_data.get('type')

        try:
            if original_opts:
                if item_type in ['rectangle', 'circle', 'line']:
                    self.canvas.itemconfig(item_id, outline=original_opts['outline'], width=original_opts['width'])
                elif item_type == 'text':
                    self.canvas.itemconfig(item_id, fill=original_opts['fill'])
                del self.original_item_options[item_id]
            else: # If no specific original options stored, revert to defaults based on type
                if item_type in ['rectangle', 'circle', 'line']:
                     # Use options stored in canvas_objects if available
                    restored_outline = obj_data.get('options',{}).get('outline', self.pen_color if item_type != 'line' else 'black')
                    restored_width = obj_data.get('options',{}).get('width', self.pen_width)
                    if item_type == 'line': # Lines use fill for color
                        restored_fill = obj_data.get('options',{}).get('fill', self.pen_color)
                        self.canvas.itemconfig(item_id, fill=restored_fill, width=restored_width)
                    else:
                        self.canvas.itemconfig(item_id, outline=restored_outline, width=restored_width)
                elif item_type == 'text':
                    restored_fill = obj_data.get('options',{}).get('fill', self.pen_color)
                    self.canvas.itemconfig(item_id, fill=restored_fill)
            self.shared_state.log(f"Removed selection visual from item {item_id}",level=logging.DEBUG)
        except tk.TclError:
            self.shared_state.log(f"TclError removing selection from {item_id}. Item might be deleted.", level=logging.WARNING)


    def handle_selection(self, event):
        items = self.canvas.find_closest(event.x, event.y, halo=5)
        clicked_item_id = items[0] if items else None

        if self.selected_object_id is not None and self.selected_object_id != clicked_item_id:
            # Clicked on a new item or empty space, deselect current
            self._remove_selection_visual(self.selected_object_id)
            # No need to set self.selected_object_id = None yet, might be selecting new one

        if clicked_item_id:
            obj_exists_in_tracking = any(obj['id'] == clicked_item_id for obj in self.canvas_objects)
            if not obj_exists_in_tracking: # Clicked on something not in our list (e.g. crop rect)
                if self.selected_object_id: # Deselect previous if any
                     self._remove_selection_visual(self.selected_object_id)
                     self.selected_object_id = None
                self.shared_state.log(f"Clicked on non-tracked canvas item {clicked_item_id}. Selection cleared.", level=logging.DEBUG)
                return

            if self.selected_object_id == clicked_item_id:
                # Clicked on the already selected item, so deselect it
                self._remove_selection_visual(clicked_item_id)
                self.selected_object_id = None
                self.shared_state.log(f"Item {clicked_item_id} deselected.", level=logging.INFO)
                self._clear_resize_handles()
            else:
                # A new item is selected
                if self.selected_object_id : # Deselect previous one first
                    self._remove_selection_visual(self.selected_object_id)
                    # _remove_selection_visual calls _clear_resize_handles already
                self.selected_object_id = clicked_item_id
                self._apply_selection_visual(self.selected_object_id) # This will also call _draw_resize_handles
                self.shared_state.log(f"Item {self.selected_object_id} selected.", level=logging.INFO)
        else:
            # Clicked on empty space
            if self.selected_object_id:
                self._remove_selection_visual(self.selected_object_id)
                self.selected_object_id = None
                self.shared_state.log("Selection cleared (clicked empty space).", level=logging.INFO)
            self._clear_resize_handles() # Ensure handles are gone

    def delete_selected_object(self):
        if self.selected_object_id is None:
            self.shared_state.log("No object selected to delete.", level=logging.INFO)
            return

        item_id_to_delete = self.selected_object_id
        self._clear_resize_handles() # Clear handles before deleting the object

        try:
            self.canvas.delete(item_id_to_delete)
        except tk.TclError as e:
            self.shared_state.log(f"Error deleting item {item_id_to_delete} from canvas: {e}", level=logging.ERROR)

        original_count = len(self.canvas_objects)
        self.canvas_objects = [obj for obj in self.canvas_objects if obj['id'] != item_id_to_delete]
        new_count = len(self.canvas_objects)

        if item_id_to_delete in self.original_item_options:
            del self.original_item_options[item_id_to_delete]

        self.selected_object_id = None
        self.shared_state.log(f"Object {item_id_to_delete} deleted. Tracking list changed from {original_count} to {new_count}.", level=logging.INFO)


    def on_destroy(self):
        self.shared_state.log("ImageEditorModule destroying...", level=logging.INFO)
        super().on_destroy()
        # Add any specific cleanup for ImageEditorModule here if needed in the future
        self.shared_state.log("ImageEditorModule destroyed.", level=logging.INFO)

# Example of how to test this module if run directly (for development purposes)
if __name__ == '__main__':
    # This is a simplified setup for testing.
    # In the actual application, the main app initializes SharedState and Tk root.
    class MockSharedState:
        def __init__(self):
            self.log_messages = []
            self.notebook = None # In a real scenario, this would be a ttk.Notebook

        def log(self, message, level=logging.INFO):
            print(f"LOG ({logging.getLevelName(level)}): {message}")
            self.log_messages.append((message, level))

    root = tk.Tk()
    root.title("Test Image Editor Module")
    root.geometry("800x600")

    # Mock notebook for the module to attach to
    notebook = ttk.Notebook(root)
    notebook.pack(expand=True, fill='both', padx=5, pady=5)

    shared_state = MockSharedState()
    shared_state.notebook = notebook # Assign the notebook to shared_state

    # The ImageEditorModule expects 'master' to be the notebook where it adds its frame
    # and 'gui_manager' can be None for this basic setup.
    # The Module class itself creates a frame and adds it to the notebook.
    editor_module = ImageEditorModule(master=notebook, shared_state=shared_state)

    # The Module's __init__ should have already added its frame to the notebook.
    # If not, the following line would be how you'd typically add a new tab.
    # However, our Module class handles this.
    # notebook.add(editor_module.frame, text="Image Editor")

    root.mainloop()

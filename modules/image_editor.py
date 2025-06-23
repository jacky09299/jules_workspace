import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import uuid # For unique IDs

# --- Object Model for Drawn Items ---
class BaseObject:
    def __init__(self, obj_type, color="black", thickness=1, tags=None):
        self.id = uuid.uuid4()
        self.obj_type = obj_type
        self.color = color
        self.thickness = thickness
        self.selected = False
        self.tags = tags if tags else [] # For canvas item tagging

    def get_canvas_tags(self):
        """Return a tuple of tags for canvas items, including the object's ID."""
        return tuple(self.tags + [str(self.id), self.obj_type])

    def calculate_bounding_box(self):
        """Placeholder for bounding box calculation. Should be implemented by subclasses."""
        # Returns (min_x, min_y, max_x, max_y) in image coordinates
        raise NotImplementedError

    def draw(self, canvas, image_to_canvas_coords_func):
        """Placeholder for drawing logic. Should be implemented by subclasses."""
        raise NotImplementedError

    def move(self, dx, dy):
        """Placeholder for moving logic. Should be implemented by subclasses."""
        raise NotImplementedError

class FreehandPathObject(BaseObject):
    def __init__(self, points, color, thickness):
        super().__init__("freehand", color, thickness)
        self.points = points # List of (x,y) tuples in image coordinates

    def add_point(self, point):
        self.points.append(point)

    def calculate_bounding_box(self):
        if not self.points:
            return (0, 0, 0, 0)
        min_x = min(p[0] for p in self.points)
        min_y = min(p[1] for p in self.points)
        max_x = max(p[0] for p in self.points)
        max_y = max(p[1] for p in self.points)
        return (min_x, min_y, max_x, max_y)

    def draw(self, canvas, image_to_canvas_coords_func, active_preview=False):
        if len(self.points) < 2:
            return None # Not enough points to draw a line

        canvas_points = []
        for p_img in self.points:
            cx, cy = image_to_canvas_coords_func(p_img[0], p_img[1])
            canvas_points.extend([cx, cy])

        # Use specific tag if it's an active preview so it can be easily deleted/updated
        item_tags = self.get_canvas_tags()
        if active_preview:
            item_tags = ("active_preview_object",) # Single, simple tag for easy deletion

        return canvas.create_line(
            *canvas_points,
            fill=self.color,
            width=self.thickness, # Consider scaling thickness with zoom if desired
            tags=item_tags,
            capstyle=tk.ROUND, # Smoother line ends
            joinstyle=tk.ROUND  # Smoother line joins
        )

    def move(self, dx_img, dy_img):
        self.points = [(p[0] + dx_img, p[1] + dy_img) for p in self.points]

    def render_on_pil_image(self, draw_context: ImageDraw.ImageDraw):
        if len(self.points) < 2:
            return
        # Ensure points are tuples for PIL draw.line
        pil_points = [tuple(p) for p in self.points]
        draw_context.line(pil_points, fill=self.color, width=self.thickness, joint="curve")


class TextObject(BaseObject):
    def __init__(self, x_img, y_img, text_content, font_family="Arial", font_size_pt=12, color="black", anchor="nw"):
        super().__init__("text", color)
        self.x_img = x_img  # Image coordinate X
        self.y_img = y_img  # Image coordinate Y
        self.text_content = text_content
        self.font_family = font_family
        self.font_size_pt = font_size_pt # Font size in points
        self.anchor = anchor # tk.NW, tk.CENTER etc. for canvas text anchor
        self.pil_font = None
        self._update_pil_font()

    def _update_pil_font(self):
        try:
            # Attempt to load the specified font.
            # For more robust font finding, might need fontconfig or platform-specific logic.
            self.pil_font = ImageFont.truetype(f"{self.font_family.lower()}.ttf", self.font_size_pt)
        except IOError:
            # Fallback to a default font if the specified one isn't found/loadable
            try:
                self.pil_font = ImageFont.truetype("arial.ttf", self.font_size_pt) # Common fallback
                self.font_family = "Arial" # Update to reflect fallback
            except IOError:
                # Generic Pillow default font if arial also fails
                self.pil_font = ImageFont.load_default()
                self.font_family = "Default" # Update to reflect fallback

    def draw(self, canvas, image_to_canvas_coords_func, active_preview=False):
        # active_preview is not really used for text in the same way as freehand, but kept for interface consistency
        canvas_x, canvas_y = image_to_canvas_coords_func(self.x_img, self.y_img)

        # Note: Tkinter's font size is roughly in points.
        # PIL's font size is also in points for truetype.
        # If scaling text with zoom is desired, font size calculation would be more complex here.
        # For now, let's use a fixed point size that PIL renders, and Tkinter displays.
        # The visual size will scale with the zoom of the canvas coordinates.

        return canvas.create_text(
            canvas_x, canvas_y,
            text=self.text_content,
            font=(self.font_family, self.font_size_pt), # Tkinter font tuple
            fill=self.color,
            anchor=self.anchor,
            tags=self.get_canvas_tags()
        )

    def calculate_bounding_box(self):
        if not self.text_content or not self.pil_font:
            # If no text or font, return a zero-size box at the anchor point
            return (self.x_img, self.y_img, self.x_img, self.y_img)

        try:
            # Get the bounding box of the text if its origin (0,0) is the drawing point.
            # For most fonts, bbox[0] is usually 0 or small negative, bbox[1] is negative (ascent).
            # bbox[2] is width, bbox[3] is descent.
            bbox = self.pil_font.getbbox(self.text_content)
            text_left_offset = bbox[0]
            text_top_offset = bbox[1]
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

        except Exception as e:
            # Fallback to approximation if getbbox fails for some reason
            self.shared_state.log(f"Pillow getbbox failed for '{self.text_content}': {e}. Using approximation.", "WARNING")
            text_width = len(self.text_content) * self.font_size_pt * 0.6
            text_height = self.font_size_pt * 1.2
            text_left_offset = 0
            text_top_offset = -text_height * 0.8 # Crude guess for ascent part

        # Adjust bounding box based on the anchor relative to self.x_img, self.y_img
        # self.x_img, self.y_img is the point specified by the anchor.

        # Default to top-left behavior (anchor="nw")
        # For "nw", self.x_img, self.y_img is the top-left of the text's rendering box.
        # The text itself might render slightly offset due to font metrics (e.g. bbox[0], bbox[1])
        # So, actual top-left of ink is (self.x_img + text_left_offset, self.y_img + text_top_offset)

        min_x = self.x_img + text_left_offset
        min_y = self.y_img + text_top_offset

        if self.anchor == tk.CENTER:
            min_x = self.x_img - text_width / 2 + text_left_offset # Center of the ink
            min_y = self.y_img - text_height / 2 + text_top_offset
        elif self.anchor == tk.N:
            min_x = self.x_img - text_width / 2 + text_left_offset
            min_y = self.y_img + text_top_offset # self.y_img is top-center
        elif self.anchor == tk.S:
            min_x = self.x_img - text_width / 2 + text_left_offset
            min_y = self.y_img - text_height + text_top_offset # self.y_img is bottom-center
        elif self.anchor == tk.W:
            min_x = self.x_img + text_left_offset # self.x_img is left-middle
            min_y = self.y_img - text_height / 2 + text_top_offset
        elif self.anchor == tk.E:
            min_x = self.x_img - text_width + text_left_offset # self.x_img is right-middle
            min_y = self.y_img - text_height / 2 + text_top_offset
        # Add NE, NW, SE, SW if needed, NW is default
        elif self.anchor == tk.NE:
            min_x = self.x_img - text_width + text_left_offset
            min_y = self.y_img + text_top_offset
        elif self.anchor == tk.SW:
            min_x = self.x_img + text_left_offset
            min_y = self.y_img - text_height + text_top_offset
        elif self.anchor == tk.SE:
            min_x = self.x_img - text_width + text_left_offset
            min_y = self.y_img - text_height + text_top_offset

        # Default is NW, which is already min_x, min_y based on initial assignment

        max_x = min_x + text_width
        max_y = min_y + text_height

        return (min_x, min_y, max_x, max_y)

    def move(self, dx_img, dy_img):
        self.x_img += dx_img
        self.y_img += dy_img

    def render_on_pil_image(self, draw_context: ImageDraw.ImageDraw):
        # ImageDraw.text anchor is different from Tkinter's canvas text anchor.
        # Pillow's default anchor for .text is top-left.
        # If self.anchor is "nw" (top-left), then self.x_img, self.y_img can be used directly.
        # If other anchors like "center" were used for x_img, y_img, we'd need to adjust
        # the xy passed to draw_context.text based on text size (pil_font.getbbox).
        # For simplicity, assuming self.x_img, self.y_img are intended as top-left for PIL rendering.
        # Or, if self.anchor is used consistently, translate it.
        # For now, let's assume self.anchor matches Pillow's anchor options or we default to "lt" (left-top)

        pil_anchor = "lt" # Default Pillow anchor (left-top)
        # A more robust mapping from tk anchors to pil anchors might be:
        # anchor_map = {"nw": "lt", "n": "mt", "ne": "rt", ...}
        # pil_anchor = anchor_map.get(self.anchor, "lt")
        # However, PIL's getbbox and textlength are also needed for precise non-"lt" anchoring.

        # If self.anchor is 'nw', it corresponds to PIL's 'lt' (left, top).
        # If self.anchor is 'center', we'd need to calculate offset.
        # For now, let's use the object's x_img, y_img and PIL's default (top-left)
        # or map 'nw' to 'lt'.

        # Using text_obj.pil_font which should be updated via _update_pil_font()
        if not self.pil_font:
            self._update_pil_font() # Ensure font is loaded

        # Pillow's ImageDraw.text uses (x,y) as top-left corner by default.
        # If self.anchor is 'nw', this is fine.
        # If self.anchor is 'center', we'd need to:
        # text_width, text_height = draw_context.textbbox((0,0), self.text_content, font=self.pil_font)[2:4]
        # actual_x = self.x_img - text_width / 2
        # actual_y = self.y_img - text_height / 2
        # For now, stick to 'nw' behavior for simplicity on PIL.
        actual_x, actual_y = self.x_img, self.y_img
        if self.anchor == "center": # Basic center handling
            try:
                # Get bounding box of text if rendered at (0,0)
                bbox = self.pil_font.getbbox(self.text_content) # (left, top, right, bottom)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1] # ascent - descent
                actual_x = self.x_img - text_width / 2
                actual_y = self.y_img - text_height / 2
            except Exception: # Fallback if getbbox fails or font not loaded
                pass # Use x_img, y_img as is

        draw_context.text(
            (actual_x, actual_y),
            self.text_content,
            font=self.pil_font,
            fill=self.color
            # Pillow's ImageDraw.text doesn't have a direct 'anchor' parameter like canvas.create_text for all versions.
            # Newer versions might have an 'anchor' parameter (e.g. "lt", "mm" for middle-middle).
            # If using an older Pillow or for max compatibility, manual adjustment for anchors other than top-left is needed.
            # Assuming self.x_img, self.y_img is the top-left for now.
        )

# --- Classes for Line, Rectangle, Oval Objects ---

class LineObject(BaseObject):
    def __init__(self, x0_img, y0_img, x1_img, y1_img, color, thickness):
        super().__init__("line", color, thickness)
        self.x0_img = x0_img
        self.y0_img = y0_img
        self.x1_img = x1_img
        self.y1_img = y1_img

    def draw(self, canvas, image_to_canvas_coords_func, active_preview=False):
        c_x0, c_y0 = image_to_canvas_coords_func(self.x0_img, self.y0_img)
        c_x1, c_y1 = image_to_canvas_coords_func(self.x1_img, self.y1_img)
        item_tags = self.get_canvas_tags()
        if active_preview:
            item_tags = ("active_preview_object",)
        return canvas.create_line(c_x0, c_y0, c_x1, c_y1, fill=self.color, width=self.thickness, tags=item_tags)

    def calculate_bounding_box(self):
        return (min(self.x0_img, self.x1_img), min(self.y0_img, self.y1_img),
                max(self.x0_img, self.x1_img), max(self.y0_img, self.y1_img))

    def move(self, dx_img, dy_img):
        self.x0_img += dx_img
        self.y0_img += dy_img
        self.x1_img += dx_img
        self.y1_img += dy_img

    def update_points_img(self, x0_img, y0_img, x1_img, y1_img): # For resizing during drag
        self.x0_img = x0_img
        self.y0_img = y0_img
        self.x1_img = x1_img
        self.y1_img = y1_img

    def render_on_pil_image(self, draw_context: ImageDraw.ImageDraw):
        draw_context.line([(self.x0_img, self.y0_img), (self.x1_img, self.y1_img)],
                          fill=self.color, width=self.thickness)

class RectangleObject(BaseObject):
    def __init__(self, x0_img, y0_img, x1_img, y1_img, color, thickness, fill_color=None): # fill_color is future
        super().__init__("rectangle", color, thickness)
        self.x0_img = x0_img
        self.y0_img = y0_img
        self.x1_img = x1_img
        self.y1_img = y1_img
        self.fill_color = fill_color # Not used in drawing yet

    def draw(self, canvas, image_to_canvas_coords_func, active_preview=False):
        c_x0, c_y0 = image_to_canvas_coords_func(self.x0_img, self.y0_img)
        c_x1, c_y1 = image_to_canvas_coords_func(self.x1_img, self.y1_img)
        item_tags = self.get_canvas_tags()
        if active_preview:
            item_tags = ("active_preview_object",)
        # For canvas, fill is empty string for no fill.
        return canvas.create_rectangle(c_x0, c_y0, c_x1, c_y1,
                                     outline=self.color, width=self.thickness, fill="", tags=item_tags)

    def calculate_bounding_box(self):
        return (min(self.x0_img, self.x1_img), min(self.y0_img, self.y1_img),
                max(self.x0_img, self.x1_img), max(self.y0_img, self.y1_img))

    def move(self, dx_img, dy_img):
        self.x0_img += dx_img
        self.y0_img += dy_img
        self.x1_img += dx_img
        self.y1_img += dy_img

    def update_points_img(self, x0_img, y0_img, x1_img, y1_img): # For resizing during drag
        self.x0_img = x0_img
        self.y0_img = y0_img
        self.x1_img = x1_img
        self.y1_img = y1_img

    def render_on_pil_image(self, draw_context: ImageDraw.ImageDraw):
        # PIL uses (x0,y0,x1,y1) where (x0,y0) is top-left and (x1,y1) is bottom-right
        coords = (min(self.x0_img, self.x1_img), min(self.y0_img, self.y1_img),
                  max(self.x0_img, self.x1_img), max(self.y0_img, self.y1_img))
        draw_context.rectangle(coords, outline=self.color, width=self.thickness) # Add fill=self.fill_color if implemented

class OvalObject(BaseObject):
    def __init__(self, x0_img, y0_img, x1_img, y1_img, color, thickness, fill_color=None): # fill_color is future
        super().__init__("oval", color, thickness)
        self.x0_img = x0_img
        self.y0_img = y0_img
        self.x1_img = x1_img
        self.y1_img = y1_img
        self.fill_color = fill_color # Not used in drawing yet

    def draw(self, canvas, image_to_canvas_coords_func, active_preview=False):
        c_x0, c_y0 = image_to_canvas_coords_func(self.x0_img, self.y0_img)
        c_x1, c_y1 = image_to_canvas_coords_func(self.x1_img, self.y1_img)
        item_tags = self.get_canvas_tags()
        if active_preview:
            item_tags = ("active_preview_object",)
        return canvas.create_oval(c_x0, c_y0, c_x1, c_y1,
                                outline=self.color, width=self.thickness, fill="", tags=item_tags)

    def calculate_bounding_box(self):
        return (min(self.x0_img, self.x1_img), min(self.y0_img, self.y1_img),
                max(self.x0_img, self.x1_img), max(self.y0_img, self.y1_img))

    def move(self, dx_img, dy_img):
        self.x0_img += dx_img
        self.y0_img += dy_img
        self.x1_img += dx_img
        self.y1_img += dy_img

    def update_points_img(self, x0_img, y0_img, x1_img, y1_img): # For resizing during drag
        self.x0_img = x0_img
        self.y0_img = y0_img
        self.x1_img = x1_img
        self.y1_img = y1_img

    def render_on_pil_image(self, draw_context: ImageDraw.ImageDraw):
        coords = (min(self.x0_img, self.x1_img), min(self.y0_img, self.y1_img),
                  max(self.x0_img, self.x1_img), max(self.y0_img, self.y1_img))
        draw_context.ellipse(coords, outline=self.color, width=self.thickness) # Add fill=self.fill_color if implemented


class DrawnObjectManager:
    def __init__(self):
        self.objects = []
        self.id_counter = 0 # Simple counter for now, UUID is better

    def add_object(self, obj):
        # obj.id = self.id_counter # Assign an ID
        # self.id_counter += 1
        self.objects.append(obj)

    def remove_object(self, obj_id):
        self.objects = [o for o in self.objects if o.id != obj_id]

    def get_object_by_id(self, obj_id):
        for obj in self.objects:
            if obj.id == obj_id:
                return obj
        return None

    def get_all_objects(self):
        return list(self.objects) # Return a copy

    def clear_all(self):
        self.objects = []

    def get_objects_by_canvas_tag(self, canvas_tag, canvas):
        """Finds drawn objects associated with a canvas item tag."""
        # This is a bit indirect. Usually, we'd get the object ID from the canvas tag.
        found_objects = []
        canvas_item_ids = canvas.find_withtag(canvas_tag)
        for item_id in canvas_item_ids:
            tags = canvas.gettags(item_id)
            for tag in tags:
                try:
                    obj_uuid = uuid.UUID(tag) # Try to convert tag to UUID
                    obj = self.get_object_by_id(obj_uuid)
                    if obj and obj not in found_objects:
                        found_objects.append(obj)
                except ValueError:
                    continue # Tag is not a valid UUID
        return found_objects


# Assuming main.py (and thus the Module class definition) is in the parent directory
# Adjust the import path if your project structure is different.
try:
    from main import Module
    from shared_state import SharedState # If used by Module or needed directly
except ImportError:
    # Fallback for cases where main.py might be in a different relative path
    # This might happen if image_editor.py is run directly for testing (though not typical for modules)
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from main import Module
    from shared_state import SharedState


class ImageEditorModule(Module):
    def __init__(self, master, shared_state: SharedState, module_name="ImageEditor", gui_manager=None):
        super().__init__(master, shared_state, module_name, gui_manager)
        self.shared_state.log(f"ImageEditorModule '{module_name}' initialized.")

        # TODO: Initialize image variables, drawing tools, states, etc.
        self.image_path = None
        self.original_image = None # Stores the pristine loaded image
        self.displayed_image_tk = None # For Tkinter canvas
        self.current_image_pil = None # PIL image currently being worked on (after rotations, crops, etc.)

        self.edit_mode_active = False
        self.crop_mode_active = False

        self.drawing_tools_frame = None # For drawing tool buttons
        # UI Elements that need to be accessed later
        self.canvas = None
        self.crop_rect_id = None # Canvas ID for the crop rectangle
        self.crop_start_coords = None # For drawing crop rectangle
        self.open_button = None
        self.edit_button = None
        self.rotate_button = None
        self.crop_button = None
        self.save_button = None
        self.cancel_button = None
        self.status_bar_label = None

        # Drawing related
        self.draw_start_coords = None # For storing (x,y) of mouse press on canvas
        self.current_drawing_tool = "line"
        self.drawing_color = "red"
self.line_thickness = 2 # Default line thickness
# self.drawn_items = [] # List to store drawn shapes/text objects (deferred for full object model)
self.drawn_object_manager = DrawnObjectManager() # Manages all drawn objects
self.active_drawing_item_id = None # Canvas ID for temporary shape preview (for existing tools)
self.active_object_preview_id = None # Canvas ID for new object previews (e.g. freehand path)
self.current_active_object = None # Stores the object being actively drawn (e.g. a FreehandPathObject)
self.selected_object = None # Stores the currently selected TextObject or FreehandPathObject
self.selection_drag_start_img_coords = None # For calculating drag delta of selected object
self.selection_visual_id = None # Canvas item ID for the selection rectangle

self.image_draw_layer = None # PIL ImageDraw object for drawing on edit_buffer_image (for old method, may deprecate)
        self.edit_buffer_image = None # PIL image copy for drawing during an edit session

        # Zoom/Pan related
        self.zoom_factor = 1.0
        self.pan_start_x = None
        self.pan_start_y = None
        self.canvas_image_x = 0 # Top-left x of image on canvas
        self.pan_view_start_x = 0 # Original canvas_image_x at pan start
        self.pan_view_start_y = 0 # Original canvas_image_y at pan start
        self.canvas_image_y = 0 # Top-left y of image on canvas

        self.create_ui()
        self.update_button_states() # Initial state of buttons

    # --- Coordinate Conversion Helpers ---
    def _canvas_to_image_coords(self, canvas_x, canvas_y):
        """Converts canvas coordinates to image coordinates, considering pan and zoom."""
        if self.zoom_factor == 0: return (0,0) # Avoid division by zero
        img_x = (canvas_x - self.canvas_image_x) / self.zoom_factor
        img_y = (canvas_y - self.canvas_image_y) / self.zoom_factor
        return img_x, img_y

    def _image_to_canvas_coords(self, img_x, img_y):
        """Converts image coordinates to canvas coordinates, considering pan and zoom."""
        canvas_x = img_x * self.zoom_factor + self.canvas_image_x
        canvas_y = img_y * self.zoom_factor + self.canvas_image_y
        return canvas_x, canvas_y

    def create_ui(self):
        self.shared_state.log("ImageEditorModule: Creating UI...")
        # The main frame for this module is self.frame (from Module base class)

        # Top bar for main controls
        top_controls_frame = ttk.Frame(self.frame)
        top_controls_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.open_button = ttk.Button(top_controls_frame, text="開啟圖片", command=self.open_image_action)
        self.open_button.pack(side=tk.LEFT, padx=2)

        self.edit_button = ttk.Button(top_controls_frame, text="🔧 編輯模式", command=self.toggle_edit_mode_action)
        self.edit_button.pack(side=tk.LEFT, padx=2)

        self.rotate_button = ttk.Button(top_controls_frame, text="🔁 旋轉", command=self.rotate_action)
        self.rotate_button.pack(side=tk.LEFT, padx=2)

        self.crop_button = ttk.Button(top_controls_frame, text="✂️ 裁剪", command=self.toggle_crop_mode_action)
        self.crop_button.pack(side=tk.LEFT, padx=2)

        self.save_button = ttk.Button(top_controls_frame, text="💾 儲存", command=self.save_action)
        self.save_button.pack(side=tk.LEFT, padx=2)

        self.cancel_button = ttk.Button(top_controls_frame, text="❌ 取消", command=self.cancel_action)
        self.cancel_button.pack(side=tk.LEFT, padx=2)

        # Drawing tools frame (initially hidden)
        self.drawing_tools_frame = ttk.Frame(self.frame)
        # Packed/unpacked in toggle_edit_mode_action, not here directly

        ttk.Button(self.drawing_tools_frame, text="Line", command=lambda: self._set_drawing_tool("line")).pack(side=tk.LEFT)
        ttk.Button(self.drawing_tools_frame, text="Rect", command=lambda: self._set_drawing_tool("rectangle")).pack(side=tk.LEFT)
        ttk.Button(self.drawing_tools_frame, text="Oval", command=lambda: self._set_drawing_tool("oval")).pack(side=tk.LEFT)
        ttk.Button(self.drawing_tools_frame, text="Freehand", command=lambda: self._set_drawing_tool("freehand")).pack(side=tk.LEFT)
        ttk.Button(self.drawing_tools_frame, text="Text", command=lambda: self._set_drawing_tool("text")).pack(side=tk.LEFT)
        ttk.Button(self.drawing_tools_frame, text="Select", command=lambda: self._set_drawing_tool("select")).pack(side=tk.LEFT)
        self.edit_props_button = ttk.Button(self.drawing_tools_frame, text="Edit Props", command=self._edit_selected_object_properties_action, state=tk.DISABLED)
        self.edit_props_button.pack(side=tk.LEFT, padx=2)

        # Z-order buttons
        self.bring_to_front_button = ttk.Button(self.drawing_tools_frame, text="Bring Front", command=self._bring_selected_to_front_action, state=tk.DISABLED)
        self.bring_to_front_button.pack(side=tk.LEFT, padx=2)
        self.send_to_back_button = ttk.Button(self.drawing_tools_frame, text="Send Back", command=self._send_selected_to_back_action, state=tk.DISABLED)
        self.send_to_back_button.pack(side=tk.LEFT, padx=2)

        self.color_button_preview = tk.Frame(self.drawing_tools_frame, width=20, height=20, bg=self.drawing_color, relief=tk.SUNKEN, borderwidth=1)
        self.color_button_preview.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.drawing_tools_frame, text="Color", command=self._choose_drawing_color).pack(side=tk.LEFT)


        # Edit mode specific controls (e.g., line width, font selector) could go here too
        # For now, keeping it simple with tool type and color.

        # Canvas for image display
        # Ensure drawing_tools_frame is packed *before* the canvas if it's supposed to be on top of it or in sequence
        # If it's a separate bar, its pack order relative to top_controls_frame and canvas matters.
        # Let's pack it after top_controls and before canvas.
        # Canvas for image display
        self.canvas = tk.Canvas(self.frame, bg="lightgrey", relief="sunken", borderwidth=1)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Status bar
        self.status_bar_label = ttk.Label(self.frame, text="請先載入圖片", anchor=tk.W)
        self.status_bar_label.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0,5))

        self.shared_state.log("ImageEditorModule: UI creation mostly complete.")
        # Bind zoom and pan events later, only when an image is loaded

    def update_button_states(self):
        self.shared_state.log("ImageEditorModule: Updating button states...")
        if self.current_image_pil is None: # No image loaded
            self.open_button.config(state=tk.NORMAL)
            self.edit_button.config(state=tk.DISABLED)
            self.rotate_button.config(state=tk.DISABLED)
            self.crop_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.DISABLED)
            self.cancel_button.config(state=tk.DISABLED)
            self.set_status("請先載入圖片")
        else: # Image is loaded
            self.open_button.config(state=tk.NORMAL) # Or some other logic like "Open Another"

            if self.edit_mode_active:
                self.edit_button.config(text="💾 儲存繪圖", state=tk.NORMAL) # Becomes "Save Drawing"
                self.rotate_button.config(state=tk.DISABLED)
                self.crop_button.config(state=tk.DISABLED)
                self.save_button.config(state=tk.DISABLED) # Main save disabled
                self.cancel_button.config(text="❌ 取消繪圖", state=tk.NORMAL) # Becomes "Cancel Drawing"

                # Edit Props button state
                can_edit_or_reorder = self.current_drawing_tool == "select" and self.selected_object
                if can_edit_or_reorder:
                    self.edit_props_button.config(state=tk.NORMAL)
                    self.bring_to_front_button.config(state=tk.NORMAL)
                    self.send_to_back_button.config(state=tk.NORMAL)
                else:
                    self.edit_props_button.config(state=tk.DISABLED)
                    self.bring_to_front_button.config(state=tk.DISABLED)
                    self.send_to_back_button.config(state=tk.DISABLED)

                self.set_status("繪圖/打字模式中")
            elif self.crop_mode_active:
                self.edit_button.config(state=tk.DISABLED)
                if self.drawing_tools_frame.winfo_ismapped(): # Check if drawing tools are visible
                    self.edit_props_button.config(state=tk.DISABLED)
                    self.bring_to_front_button.config(state=tk.DISABLED)
                    self.send_to_back_button.config(state=tk.DISABLED)
                self.rotate_button.config(state=tk.DISABLED)
                self.crop_button.config(text="✅ 確認裁剪", state=tk.NORMAL) # Becomes "Confirm Crop"
                self.save_button.config(state=tk.DISABLED) # Main save disabled
                self.cancel_button.config(text="❌ 取消裁剪", state=tk.NORMAL) # Becomes "Cancel Crop"
                self.set_status("裁剪模式中")
            else: # Normal state with image loaded
                self.edit_button.config(text="🔧 編輯模式", state=tk.NORMAL)
                self.rotate_button.config(state=tk.NORMAL)
                self.crop_button.config(text="✂️ 裁剪", state=tk.NORMAL)
                self.save_button.config(state=tk.NORMAL)
                self.cancel_button.config(text="❌ 取消", state=tk.NORMAL) # General cancel/undo
                self.set_status("圖片已載入")
        self.shared_state.log("ImageEditorModule: Button states updated.")

    def set_status(self, message):
        if self.status_bar_label:
            self.status_bar_label.config(text=message)
            self.shared_state.log(f"Status bar: {message}", level="DEBUG")

    def open_image_action(self):
        self.shared_state.log("ImageEditorModule: 'Open Image' action triggered.")
        file_types = [
            ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp"),
            ("All files", "*.*")
        ]
        path = filedialog.askopenfilename(parent=self.frame, title="Select an image", filetypes=file_types)
        if not path:
            self.shared_state.log("ImageEditorModule: No image selected.", "DEBUG")
            return

        try:
            self.image_path = path
            pil_image = Image.open(self.image_path)
            pil_image = pil_image.convert("RGBA") # Ensure RGBA for consistency
            self.original_image = pil_image.copy()
            self.current_image_pil = pil_image.copy()

            # Reset states for the new image
            self.drawn_object_manager.clear_all() # Clear any previous objects
            self.zoom_factor = 1.0
            self.canvas_image_x = 0 # Reset pan position
            self.canvas_image_y = 0
            self.pan_start_x = None # Ensure pan state is reset
            self.pan_start_y = None

            self._display_image_on_canvas()
            self.update_button_states()
            self.set_status(f"Image loaded: {os.path.basename(self.image_path)}")

            # Bind zoom and pan events only after an image is successfully loaded
            self.canvas.bind("<MouseWheel>", self._on_mouse_wheel) # For Windows/macOS
            self.canvas.bind("<Button-4>", self._on_mouse_wheel) # For Linux (scroll up)
            self.canvas.bind("<Button-5>", self._on_mouse_wheel) # For Linux (scroll down)

            self.canvas.bind("<Shift-ButtonPress-1>", self._on_pan_start)
            self.canvas.bind("<Shift-B1-Motion>", self._on_pan_motion)
            self.canvas.bind("<Shift-ButtonRelease-1>", self._on_pan_end)

        except Exception as e:
            self.shared_state.log(f"ImageEditorModule: Error opening image '{path}': {e}", "ERROR")
            messagebox.showerror("Error Opening Image", f"Could not open image file: {e}", parent=self.frame)
            self.current_image_pil = None
            self.original_image = None
            self.image_path = None
            self.canvas.delete("all")
            self.update_button_states()

    def _unbind_zoom_pan(self):
        self.canvas.unbind("<MouseWheel>")
        self.canvas.unbind("<Button-4>")
        self.canvas.unbind("<Button-5>")
        self.canvas.unbind("<Shift-ButtonPress-1>")
        self.canvas.unbind("<Shift-B1-Motion>")
        self.canvas.unbind("<Shift-ButtonRelease-1>")

    def toggle_edit_mode_action(self):
        self.shared_state.log(f"ImageEditorModule: 'Toggle Edit Mode' action triggered. Current edit_mode_active: {self.edit_mode_active}")
        if self.edit_mode_active: # Was in edit mode, now "applying" / exiting edit mode
            self.edit_mode_active = False
            # For legacy tools, drawings are already on edit_buffer_image
            if self.edit_buffer_image and self.image_draw_layer: # Check if legacy drawing happened
                # This bake step is for legacy tools (line, rect, oval)
                # New objects in drawn_object_manager are separate.
                self.current_image_pil = self.edit_buffer_image.copy()
                self.shared_state.log("Legacy drawings from buffer baked into current_image_pil.")

            # New objects in drawn_object_manager persist. No specific action needed here for them.
            # Reset buffer-related things
            self.edit_buffer_image = None # Buffer is committed or discarded
            self.image_draw_layer = None
            self.current_active_object = None # Clear any active drawing state
            if self.active_object_preview_id:
                self.canvas.delete(self.active_object_preview_id)
                self.active_object_preview_id = None

            self.drawing_tools_frame.pack_forget()
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            # Re-bind pan if it was unbound
            self.canvas.bind("<Shift-ButtonPress-1>", self._on_pan_start)
            self.canvas.bind("<Shift-B1-Motion>", self._on_pan_motion)
            self.canvas.bind("<Shift-ButtonRelease-1>", self._on_pan_end)

            self._display_image_on_canvas() # Show the baked image
            self.set_status("繪圖儲存完畢")
        else: # Entering edit mode
            if self.current_image_pil is None:
                messagebox.showwarning("無圖片", "請先載入圖片才能進入編輯模式。", parent=self.frame)
                return
            self.edit_mode_active = True
            self.edit_buffer_image = self.current_image_pil.copy()
            self.image_draw_layer = ImageDraw.Draw(self.edit_buffer_image) # Draw on the buffer

            self.drawing_tools_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0,5), before=self.canvas) # Show tools
            # Unbind pan to avoid conflict, or make drawing take precedence.
            self.canvas.unbind("<Shift-ButtonPress-1>")
            self.canvas.unbind("<Shift-B1-Motion>")
            self.canvas.unbind("<Shift-ButtonRelease-1>")
            self.canvas.bind("<ButtonPress-1>", self._edit_on_press)
            self.canvas.bind("<B1-Motion>", self._edit_on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._edit_on_release)
            self.set_status("繪圖模式中，選擇工具開始繪圖")
        self.update_button_states()

    def rotate_action(self):
        if not self.current_image_pil:
            messagebox.showwarning("無圖片", "請先載入圖片才能旋轉。", parent=self.frame)
            return

        self.shared_state.log("ImageEditorModule: 'Rotate' action triggered.")

        # Simple dialog for choosing rotation
        dialog = tk.Toplevel(self.frame)
        dialog.title("選擇旋轉角度")
        dialog.geometry("250x200") # Increased height for buttons
        dialog.resizable(False, False)
        dialog.grab_set() # Make it modal

        ttk.Label(dialog, text="請選擇或輸入旋轉角度:").pack(pady=10)

        # angle_var = tk.StringVar() # Not directly used with this button approach

        def apply_rotation(angle_degrees):
            # Check if dialog is still alive, could be destroyed if custom dialog was cancelled.
            if not dialog.winfo_exists() and not isinstance(angle_degrees, float): # Custom dialog was closed, angle not yet set
                 # If angle_degrees is None from simpledialog cancel, it will be handled below
                 pass
            elif dialog.winfo_exists(): # Only destroy if not custom simpledialog path
                dialog.destroy()

            if angle_degrees is None: # User cancelled custom input or closed main dialog prematurely
                self.shared_state.log("Rotation cancelled or angle not provided.", "DEBUG")
                self.set_status("旋轉已取消")
                return
            try:
                angle = float(angle_degrees)
                # PIL rotates counter-clockwise.
                self.current_image_pil = self.current_image_pil.rotate(angle, expand=True, fillcolor=(0,0,0,0))
                # Reset zoom and pan after rotation for simplicity, as dimensions change
                self.zoom_factor = 1.0
                self.canvas_image_x = 0
                self.canvas_image_y = 0
                self._display_image_on_canvas()
                self.set_status(f"圖片已旋轉 {angle}°")
                self.shared_state.log(f"Image rotated by {angle} degrees.")
            except ValueError:
                messagebox.showerror("無效角度", "請輸入有效的數字角度。", parent=self.frame)
                self.set_status("無效的旋轉角度")
            except Exception as e:
                messagebox.showerror("旋轉錯誤", f"旋轉圖片時發生錯誤: {e}", parent=self.frame)
                self.shared_state.log(f"Error during rotation: {e}", "ERROR")
                self.set_status("旋轉時發生錯誤")
            finally:
                # Ensure main dialog is closed if an error occurred after simpledialog
                if dialog.winfo_exists():
                    dialog.destroy()


        ttk.Button(dialog, text="90° (順時針)", command=lambda: apply_rotation(-90.0)).pack(fill=tk.X, padx=20, pady=2)
        ttk.Button(dialog, text="180°", command=lambda: apply_rotation(180.0)).pack(fill=tk.X, padx=20, pady=2)
        ttk.Button(dialog, text="90° (逆時針)", command=lambda: apply_rotation(90.0)).pack(fill=tk.X, padx=20, pady=2)

        custom_frame = ttk.Frame(dialog)
        custom_frame.pack(fill=tk.X, padx=15, pady=5, side=tk.BOTTOM, anchor=tk.S) # Ensure it's at bottom

        def ask_custom_angle():
            # Dialog is parent here, so simpledialog will be on top of it.
            custom_angle = simpledialog.askfloat("自訂角度", "輸入角度 (逆時針為正):", parent=dialog, minvalue=-360.0, maxvalue=360.0)
            # apply_rotation will handle None if cancelled
            apply_rotation(custom_angle)

        ttk.Button(custom_frame, text="自訂角度...", command=ask_custom_angle).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(custom_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, expand=True, padx=5)


    def toggle_crop_mode_action(self):
        self.shared_state.log(f"ImageEditorModule: 'Toggle Crop Mode' action triggered. Current crop_mode_active: {self.crop_mode_active}")
        if self.crop_mode_active:
            # --- 直接執行裁剪 ---
            if not self.crop_rect_id:
                messagebox.showwarning("未選擇區域", "請先在圖片上拖曳選擇裁剪區域，再按確認裁剪。", parent=self.frame)
                self.set_status("請先選擇裁剪區域")
                return
            if self.current_image_pil:
                try:
                    c_coords = self.canvas.coords(self.crop_rect_id)
                    if len(c_coords) != 4:
                        messagebox.showwarning("裁剪區域錯誤", "裁剪區域座標無效，請重新選擇。", parent=self.frame)
                        self.set_status("裁剪區域座標無效")
                        return
                    # Ensure correct order: left_can = min(x1_can, x2_can), etc.
                    left_can, top_can, right_can, bottom_can = min(c_coords[0], c_coords[2]), min(c_coords[1], c_coords[3]), max(c_coords[0], c_coords[2]), max(c_coords[1], c_coords[3])
                    self.shared_state.log(f"[CropDebug] Ordered canvas coords: L:{left_can}, T:{top_can}, R:{right_can}, B:{bottom_can}", "DEBUG")
                    self.shared_state.log(f"[CropDebug] View state: canvas_image_x:{self.canvas_image_x}, canvas_image_y:{self.canvas_image_y}, zoom_factor:{self.zoom_factor}", "DEBUG")

                    img_left = (left_can - self.canvas_image_x) / self.zoom_factor
                    img_top = (top_can - self.canvas_image_y) / self.zoom_factor
                    img_right = (right_can - self.canvas_image_x) / self.zoom_factor
                    img_bottom = (bottom_can - self.canvas_image_y) / self.zoom_factor
                    self.shared_state.log(f"[CropDebug] Calculated img coords (before clamp): L:{img_left}, T:{img_top}, R:{img_right}, B:{img_bottom}", "DEBUG")

                    # Clamp to image boundaries
                    img_w, img_h = self.current_image_pil.size
                    self.shared_state.log(f"[CropDebug] Original image_pil size: W:{img_w}, H:{img_h}", "DEBUG")

                    img_left = max(0, img_left)
                    img_top = max(0, img_top)
                    img_right = min(img_w, img_right)
                    img_bottom = min(img_h, img_bottom)
                    self.shared_state.log(f"[CropDebug] Clamped img coords: L:{img_left}, T:{img_top}, R:{img_right}, B:{img_bottom}", "DEBUG")

                    is_valid_crop_area = img_left < img_right and img_top < img_bottom
                    self.shared_state.log(f"[CropDebug] Is valid crop area (L<R and T<B): {is_valid_crop_area}", "DEBUG")

                    if is_valid_crop_area:
                        crop_box = (int(img_left), int(img_top), int(img_right), int(img_bottom))
                        self.shared_state.log(f"[CropDebug] Integer crop_box for Pillow: {crop_box}", "DEBUG")

                        # Additional check after int conversion for zero-dimension images
                        if crop_box[0] < crop_box[2] and crop_box[1] < crop_box[3]:
                            self.current_image_pil = self.current_image_pil.crop(crop_box)
                            # 更新原始圖片（可選，讓取消時能回復到裁剪前）
                            self.original_image = self.current_image_pil.copy()
                            self.zoom_factor = 1.0
                            self.canvas_image_x = 0
                            self.canvas_image_y = 0
                            self.set_status("圖片裁剪成功")
                        else:
                            messagebox.showwarning("裁剪區域無效", "選擇的裁剪區域經轉換後寬度或高度為零。", parent=self.frame)
                            self.set_status("裁剪失敗：選擇區域尺寸為零")
                    else:
                        messagebox.showwarning("裁剪區域無效", "選擇的裁剪區域太小或無效。", parent=self.frame)
                        self.set_status("裁剪失敗：選擇區域無效")
                except Exception as e:
                    messagebox.showerror("裁剪錯誤", f"裁剪圖片時發生錯誤: {e}", parent=self.frame)
                    self.set_status("裁剪時發生錯誤")
            self.crop_mode_active = False
            if self.crop_rect_id:
                self.canvas.delete(self.crop_rect_id)
                self.crop_rect_id = None
            self.crop_start_coords = None
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            self._bind_pan_events()
            self._display_image_on_canvas()
        else:
            if not self.current_image_pil:
                messagebox.showwarning("無圖片", "請先載入圖片才能進行裁剪。", parent=self.frame)
                return
            self.crop_mode_active = True
            self._unbind_pan_events()
            self.canvas.bind("<ButtonPress-1>", self._crop_on_press)
            self.canvas.bind("<B1-Motion>", self._crop_on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._crop_on_release)
            self.set_status("請在圖片上拖曳以選擇裁剪區域")
        self.update_button_states()

    def save_action(self):
        if not self.current_image_pil:
            messagebox.showwarning("無可儲存圖片", "目前沒有圖片可供儲存。", parent=self.frame)
            return

        self.shared_state.log("ImageEditorModule: 'Save' action triggered.")

        default_filename = "untitled.png"
        if self.image_path:
            base, ext = os.path.splitext(os.path.basename(self.image_path))
            default_filename = f"{base}_edited.png" # Suggest a new name

        file_types = [
            ("PNG files", "*.png"),
            ("JPEG files", "*.jpg;*.jpeg"),
            ("BMP files", "*.bmp"),
            ("All files", "*.*")
        ]

        filepath = filedialog.asksaveasfilename(
            parent=self.frame,
            title="儲存圖片為",
            initialfile=default_filename,
            defaultextension=".png",
            filetypes=file_types
        )

        if not filepath:
            self.shared_state.log("Save action cancelled by user.", "DEBUG")
            return

        try:
            # --- Create a composite image by flattening drawn objects ---
            if not self.current_image_pil: # Should not happen if save button is enabled
                messagebox.showerror("Error", "No image data to save.", parent=self.frame)
                return

            # Start with a copy of the current base image (which might have legacy drawings baked in)
            image_with_objects_pil = self.current_image_pil.copy()

            # Create a drawing context on this copy
            draw_context = ImageDraw.Draw(image_with_objects_pil)

            # Render each managed object onto this PIL image
            if self.drawn_object_manager and self.drawn_object_manager.get_all_objects():
                self.shared_state.log(f"Flattening {len(self.drawn_object_manager.get_all_objects())} objects onto image for saving.", "INFO")
                for obj in self.drawn_object_manager.get_all_objects():
                    try:
                        obj.render_on_pil_image(draw_context)
                    except AttributeError:
                        self.shared_state.log(f"Object type {obj.obj_type} (ID: {obj.id}) does not have render_on_pil_image method. Skipping.", "WARNING")
                    except Exception as e:
                        self.shared_state.log(f"Error rendering object {obj.id} on PIL image: {e}", "ERROR")

            image_to_save = image_with_objects_pil # This is the final image to be saved
            # --- End of flattening ---

            file_ext = os.path.splitext(filepath)[1].lower()

            if file_ext in ['.jpg', '.jpeg'] and image_to_save.mode == 'RGBA':
                self.shared_state.log("Converting RGBA image to RGB for JPEG save.", "DEBUG")
                # JPEG doesn't support alpha, so convert to RGB
                # Create a white background image
                background = Image.new("RGB", image_to_save.size, (255, 255, 255))
                background.paste(image_to_save, mask=image_to_save.split()[3]) # Paste using alpha channel as mask
                image_to_save = background
            elif file_ext == '.bmp' and image_to_save.mode == 'RGBA':
                 # BMP typically doesn't handle RGBA well in all viewers, convert to RGB
                self.shared_state.log("Converting RGBA image to RGB for BMP save.", "DEBUG")
                background = Image.new("RGB", image_to_save.size, (255, 255, 255))
                background.paste(image_to_save, mask=image_to_save.split()[3])
                image_to_save = background

            image_to_save.save(filepath)
            self.set_status(f"圖片已儲存至: {os.path.basename(filepath)}")
            self.shared_state.log(f"Image saved to {filepath}")
            messagebox.showinfo("儲存成功", f"圖片已成功儲存至:\n{filepath}", parent=self.frame)
        except Exception as e:
            self.shared_state.log(f"Error saving image to {filepath}: {e}", "ERROR")
            messagebox.showerror("儲存失敗", f"儲存圖片時發生錯誤: {e}", parent=self.frame)
            self.set_status(f"儲存失敗: {e}")

    def cancel_action(self):
        self.shared_state.log(f"ImageEditorModule: 'Cancel' action triggered. Edit mode: {self.edit_mode_active}, Crop mode: {self.crop_mode_active}")
        action_cancelled = False
        if self.edit_mode_active: # This is "Cancel Drawing"
            self.edit_mode_active = False # Exit edit mode

            # Clear any active previews or temporary items from canvas and state
            if self.active_drawing_item_id: # Legacy temp item
                self.canvas.delete(self.active_drawing_item_id)
                self.active_drawing_item_id = None
            if self.active_object_preview_id: # New object preview
                self.canvas.delete(self.active_object_preview_id)
                self.active_object_preview_id = None
            self.current_active_object = None # Clear object being drawn

            # Discard buffer image and drawing layer for legacy tools
            self.edit_buffer_image = None
            self.image_draw_layer = None

            self.drawing_tools_frame.pack_forget() # Hide tools
            # Unbind drawing events
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            self._bind_pan_events() # Re-bind pan

            # Clear all drawn objects managed by DrawnObjectManager
            self.drawn_object_manager.clear_all()
            self.shared_state.log("CancelDrawing: All objects cleared from DrawnObjectManager.", "INFO")

            # Revert current_image_pil to original_image to discard any baked legacy drawings
            if self.original_image:
                 # Make a fresh copy from original to current_image_pil
                self.current_image_pil = self.original_image.copy()
                self.shared_state.log("CancelDrawing: Reverted current_image_pil to original_image.", "INFO")

            self.set_status("繪圖已取消，所有物件與變更已清除。")
            action_cancelled = True

        elif self.crop_mode_active: # This is "Cancel Crop"
            self.crop_mode_active = False
            if self.crop_rect_id:
                self.canvas.delete(self.crop_rect_id)
                self.crop_rect_id = None
            self.crop_start_coords = None
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            self._bind_pan_events() # Re-bind pan
            self.set_status("Cropping cancelled (placeholder).")
            action_cancelled = True # To trigger redraw and remove visual artifacts
        else:
            # TODO: General cancel/undo logic if applicable (e.g., undo last rotation)
            # For now, maybe revert to original image if one exists
            if self.original_image:
                if self.current_image_pil.tobytes() != self.original_image.tobytes():
                    self.current_image_pil = self.original_image.copy()
                    # Baked-in drawings are part of original_image if they were saved before this cancel.
                    # If drawn_items were for a separate object layer, this would be different.
                    # For now, current_image_pil holds everything.
                    self.drawn_items = [] # Reset if we had a separate drawing layer concept

                    self.zoom_factor = 1.0
                    self.canvas_image_x = 0
                    self.canvas_image_y = 0

                    action_cancelled = True
                    self.set_status("變更已還原至原始載入圖片")
                else:
                    self.set_status("目前圖片與原始載入版本相同，無操作取消。")
            else:
                self.set_status("沒有原始圖片可供還原。")

        if action_cancelled:
            self._display_image_on_canvas() # Refresh to show state before cancel
        self.update_button_states()

    def _display_image_on_canvas(self, use_edit_buffer=False): # Added use_edit_buffer
        self.canvas.delete("all") # Clear previous image/drawings/crop_rect

        if self.current_image_pil and self.canvas:
            try:
                # Apply zoom
                zoomed_width = int(self.current_image_pil.width * self.zoom_factor)
                zoomed_height = int(self.current_image_pil.height * self.zoom_factor)
            except (ValueError, OverflowError): # Catches potential errors if zoom_factor is NaN or Inf or too large
                self.shared_state.log(f"Invalid zoom_factor: {self.zoom_factor}. Resetting to 1.0", "WARNING")
                self.zoom_factor = 1.0
                zoomed_width = self.current_image_pil.width
                zoomed_height = self.current_image_pil.height

            image_to_display_pil = self.current_image_pil
            if use_edit_buffer and self.edit_buffer_image:
                image_to_display_pil = self.edit_buffer_image
                # Apply zoom to the buffer for display
                zoomed_width = int(image_to_display_pil.width * self.zoom_factor)
                zoomed_height = int(image_to_display_pil.height * self.zoom_factor)


            if zoomed_width <= 0 or zoomed_height <= 0:
                self.shared_state.log(f"Image dimensions too small after zoom: {zoomed_width}x{zoomed_height}. Current zoom: {self.zoom_factor}. Skipping display.", "WARNING")
                return

            img_for_display = image_to_display_pil.resize((zoomed_width, zoomed_height), Image.LANCZOS)

            self.displayed_image_tk = ImageTk.PhotoImage(img_for_display)

            # Calculate centered position or use pan coordinates
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # If canvas dimensions are not yet known (e.g. during init), use arbitrary non-zero values
            if canvas_width <= 1: canvas_width = 600
            if canvas_height <= 1: canvas_height = 400

            # self.canvas_image_x and self.canvas_image_y are the top-left coords of the image on the canvas
            # When an image is first loaded or zoom changes significantly, we might want to re-center.
            # For simplicity now, (0,0) if not panned, or current pan values.
            # A more robust solution would center if image is smaller than canvas.

            # The self.canvas_image_x/y is the offset of the image's top-left corner
            # relative to the canvas's top-left corner.
            self.canvas.create_image(self.canvas_image_x, self.canvas_image_y, anchor=tk.NW, image=self.displayed_image_tk, tags="base_image") # Tagged as base_image

            # --- Draw all objects from DrawnObjectManager ---
            # Ensure drawn objects are on top of the image and previews.
            # Clear old object previews first if any (though usually done in drag/release)
            self.canvas.delete("active_preview_object")

            for obj in self.drawn_object_manager.get_all_objects():
                obj.draw(self.canvas, self._image_to_canvas_coords)

            # If there's an object currently being drawn (e.g. freehand path being dragged),
            # it might have its own preview logic in _edit_on_drag which creates an "active_preview_object".
            # This loop ensures all committed objects are drawn. The active preview is separate.

            # After drawing all objects, update/redraw the selection visual if an object is selected
            self._update_selection_visuals()

            log_msg_suffix = " (Edit Buffer)" if use_edit_buffer and self.edit_buffer_image else ""
            self.shared_state.log(f"Image displayed on canvas{log_msg_suffix}. Zoomed Size: {zoomed_width}x{zoomed_height} at ({self.canvas_image_x},{self.canvas_image_y}). Zoom: {self.zoom_factor}. Objects: {len(self.drawn_object_manager.get_all_objects())}", "DEBUG")
        elif self.canvas:
            self.shared_state.log("No image to display or canvas not ready. Cleared canvas.", "DEBUG")
            # Still ensure selection visual is cleared if canvas is cleared but an object was somehow selected
            if self.selection_visual_id:
                self.canvas.delete(self.selection_visual_id)
                self.selection_visual_id = None


    def _set_drawing_tool(self, tool_name):
        self.current_drawing_tool = tool_name
        self.set_status(f"工具已選擇: {tool_name}")
        self.shared_state.log(f"Drawing tool set to: {self.current_drawing_tool}")

        if tool_name != "select" and self.selected_object:
            self.shared_state.log(f"Tool changed from select. Deselecting object {self.selected_object.id}", "DEBUG")
            self.selected_object = None
            self._update_selection_visuals() # Clear selection visuals
            # Redraw canvas if needed, though often changing tool implies other actions that will redraw
            self._display_image_on_canvas(use_edit_buffer=self.edit_mode_active and bool(self.image_draw_layer))
            self.update_button_states() # Ensure button states are updated


    def _choose_drawing_color(self):
        try:
            color_code = colorchooser.askcolor(title="選擇繪圖顏色", initialcolor=self.drawing_color, parent=self.frame)
            if color_code and color_code[1]:
                self.drawing_color = color_code[1]
                self.color_button_preview.config(bg=self.drawing_color)
                self.shared_state.log(f"Drawing color changed to: {self.drawing_color}")
        except Exception as e:
            self.shared_state.log(f"Error in color chooser: {e}", "ERROR")
            messagebox.showerror("顏色選擇錯誤", f"無法開啟顏色選擇器: {e}", parent=self.frame)

    def _edit_on_press(self, event):
        if not self.edit_mode_active: return
        # self.shared_state.log(f"Edit press. Tool: {self.current_drawing_tool}. Canvas: ({event.x},{event.y})")

        img_x, img_y = self._canvas_to_image_coords(event.x, event.y)
        self.draw_start_coords = (event.x, event.y) # Keep canvas coords for temp drawing

        if self.current_drawing_tool == "freehand":
            self.current_active_object = FreehandPathObject(
                points=[(img_x, img_y)],
                color=self.drawing_color,
                thickness=self.line_thickness
            )
            # No canvas object created yet, will be drawn in _edit_on_drag
            self.shared_state.log(f"Started FreehandPathObject at image_coords: ({img_x:.2f}, {img_y:.2f})", "DEBUG")
        elif self.current_drawing_tool == "text":
            # For text, press just defines position. Dialog will be shown.
            # No current_active_object needed here as it's not a drag operation.
            self._add_text_object_action(img_x, img_y)
            # Since text is added immediately, refresh canvas
            self._display_image_on_canvas(use_edit_buffer=self.edit_mode_active and bool(self.image_draw_layer))
        elif self.current_drawing_tool == "select":
            clicked_object = self._get_object_at_canvas_coords(event.x, event.y)
            if clicked_object:
                self.selected_object = clicked_object
                self.selection_drag_start_img_coords = self._canvas_to_image_coords(event.x, event.y)
                # Store original position of the object if needed for more complex drag (e.g. relative drag)
                # self.selected_object_original_pos_img = (self.selected_object.x_img, self.selected_object.y_img) # If text
                self.shared_state.log(f"Object {self.selected_object.id} selected.", "INFO")
            else:
                self.selected_object = None
                self.selection_drag_start_img_coords = None
                self.shared_state.log("No object selected (clicked empty area).", "INFO")
            self._update_selection_visuals() # Update visuals based on new selection state
            self.update_button_states() # Update button states (e.g. Edit Props)
            # No need to redraw full canvas yet, just visuals. Drag will redraw.

        # --- New object-based drawing for Line, Rectangle, Oval ---
        elif self.current_drawing_tool == "line":
            self.current_active_object = LineObject(
                img_x, img_y, img_x, img_y, # Start and end points are the same initially
                self.drawing_color, self.line_thickness
            )
            self.shared_state.log(f"Started LineObject at image_coords: ({img_x:.2f}, {img_y:.2f})", "DEBUG")
        elif self.current_drawing_tool == "rectangle":
            self.current_active_object = RectangleObject(
                img_x, img_y, img_x, img_y,
                self.drawing_color, self.line_thickness
            )
            self.shared_state.log(f"Started RectangleObject at image_coords: ({img_x:.2f}, {img_y:.2f})", "DEBUG")
        elif self.current_drawing_tool == "oval":
            self.current_active_object = OvalObject(
                img_x, img_y, img_x, img_y,
                self.drawing_color, self.line_thickness
            )
            self.shared_state.log(f"Started OvalObject at image_coords: ({img_x:.2f}, {img_y:.2f})", "DEBUG")
        # --- End new object-based drawing ---
        else: # Fallback for any other tools or if current_drawing_tool is not set
            # This branch will effectively be for the old way of handling line, rect, oval if not caught above,
            # but the goal is to replace that. If all tools become object-based, this 'else' might not be needed.
            pass # No action for unhandled tools on press regarding object creation


        # For older tools (line, rect, oval), we still use the active_drawing_item_id for temp canvas shape
        # This part should be removed once line, rect, oval fully use current_active_object for previews.
        # Future: these could also create their objects on press and update them on drag.

    def _edit_on_drag(self, event):
        if not self.edit_mode_active: return # Removed draw_start_coords check as select tool doesn't use it the same way

        # For "freehand" tool (uses self.draw_start_coords)
        if self.current_drawing_tool == "freehand" and self.current_active_object and self.draw_start_coords:
            img_x, img_y = self._canvas_to_image_coords(event.x, event.y)
            self.current_active_object.add_point((img_x, img_y))

            # Delete previous preview for this specific object
            if self.active_object_preview_id:
                self.canvas.delete(self.active_object_preview_id)

            # Draw the current state of the active freehand object as a preview
            self.active_object_preview_id = self.current_active_object.draw(self.canvas, self._image_to_canvas_coords, active_preview=True)
            # self.shared_state.log(f"Freehand drag, point added: ({img_x:.2f}, {img_y:.2f}), preview_id: {self.active_object_preview_id}", "DEBUG")

        # For "select" tool (moving an object)
        elif self.current_drawing_tool == "select" and self.selected_object and self.selection_drag_start_img_coords:
            current_mouse_img_x, current_mouse_img_y = self._canvas_to_image_coords(event.x, event.y)

            dx_img = current_mouse_img_x - self.selection_drag_start_img_coords[0]
            dy_img = current_mouse_img_y - self.selection_drag_start_img_coords[1]

            try:
                self.selected_object.move(dx_img, dy_img)
                self.selection_drag_start_img_coords = (current_mouse_img_x, current_mouse_img_y)
                self._display_image_on_canvas(use_edit_buffer=self.edit_mode_active and bool(self.image_draw_layer))
                self._update_selection_visuals()
            except Exception as e:
                self.shared_state.log(f"Error moving object {self.selected_object.id}: {e}", "ERROR")

        # --- New object-based preview for Line, Rectangle, Oval ---
        elif self.current_drawing_tool in ["line", "rectangle", "oval"] and self.current_active_object and self.draw_start_coords:
            if self.active_object_preview_id: # Delete previous object preview
                self.canvas.delete(self.active_object_preview_id)
                self.active_object_preview_id = None

            img_x_start, img_y_start = self._canvas_to_image_coords(self.draw_start_coords[0], self.draw_start_coords[1])
            img_x_end, img_y_end = self._canvas_to_image_coords(event.x, event.y)

            self.current_active_object.update_points_img(img_x_start, img_y_start, img_x_end, img_y_end)
            self.active_object_preview_id = self.current_active_object.draw(self.canvas, self._image_to_canvas_coords, active_preview=True)
        # --- End new object-based preview ---

        # self.shared_state.log(f"Draw drag to canvas ({event.x},{event.y})")


    def _edit_on_release(self, event):
        if not self.edit_mode_active or self.draw_start_coords is None: return
        # self.shared_state.log(f"Edit release. Tool: {self.current_drawing_tool}. Canvas: ({event.x},{event.y})")

        # Clear any temporary canvas item used for previewing non-object based tools
        if self.active_drawing_item_id:
            self.canvas.delete(self.active_drawing_item_id)
            self.active_drawing_item_id = None

        # Clear preview for object-based tools (like freehand)
        if self.active_object_preview_id:
            self.canvas.delete(self.active_object_preview_id)
            self.active_object_preview_id = None

        # For "freehand" tool
        if self.current_drawing_tool == "freehand" and self.current_active_object:
            img_x, img_y = self._canvas_to_image_coords(event.x, event.y)
            self.current_active_object.add_point((img_x, img_y)) # Add final point
            if len(self.current_active_object.points) >= 2: # Ensure there's something to draw
                self.drawn_object_manager.add_object(self.current_active_object)
                self.shared_state.log(f"Added FreehandPathObject with {len(self.current_active_object.points)} points.", "INFO")
            else:
                self.shared_state.log("FreehandPathObject too short, not added.", "INFO")
            self.current_active_object = None # Reset current active object

        # For older tools: Convert the temporary drawing to an object and add it. # This comment is now outdated here.
        elif self.current_drawing_tool in ["line", "rectangle", "oval"] and self.current_active_object and self.draw_start_coords:
            # Finalize points for the object
            img_x_start, img_y_start = self._canvas_to_image_coords(self.draw_start_coords[0], self.draw_start_coords[1])
            img_x_end, img_y_end = self._canvas_to_image_coords(event.x, event.y)
            self.current_active_object.update_points_img(img_x_start, img_y_start, img_x_end, img_y_end)

            self.drawn_object_manager.add_object(self.current_active_object)
            self.shared_state.log(f"Added {self.current_active_object.obj_type} object.", "INFO")
            self.current_active_object = None # Reset

        elif self.current_drawing_tool == "select":
            self.shared_state.log(f"Finished dragging object {self.selected_object.id if self.selected_object else 'None'}.", "DEBUG")

        # REMOVED old block that drew line/rect/oval on self.image_draw_layer
        # else: # Catch-all for other tools, or if conditions above aren't met.
            # self.shared_state.log(f"Unhandled tool or state in _edit_on_release: {self.current_drawing_tool}", "WARNING")


        self.draw_start_coords = None
        # Display needs to be updated to show both buffer (for legacy) and new objects
        self._display_image_on_canvas(use_edit_buffer=True) # Refresh canvas

    def _add_text_object_action(self, img_x, img_y):
        """Prompts for text and adds a TextObject to the canvas."""
        text_content = simpledialog.askstring("輸入文字", "請輸入要加入的文字:", parent=self.frame)
        if not text_content:
            self.shared_state.log("Text input cancelled.", "DEBUG")
            return

        # For now, use default font family and color, prompt for size.
        # TODO: Add UI for font family, more font options, and color selection for text.
        font_size = simpledialog.askinteger("字體大小", "請輸入字體大小 (例如: 12, 16, 24):",
                                            parent=self.frame, initialvalue=12, minvalue=6, maxvalue=120)
        if font_size is None: # User cancelled font size dialog
            self.shared_state.log("Font size input cancelled for text.", "DEBUG")
            return

        text_obj = TextObject(
            x_img=img_x,
            y_img=img_y,
            text_content=text_content,
            font_family="Arial", # Default for now
            font_size_pt=font_size,
            color=self.drawing_color, # Use current drawing color
            anchor=tk.NW # Default anchor
        )
        self.drawn_object_manager.add_object(text_obj)
        self.shared_state.log(f"Added TextObject: '{text_content}' at ({img_x:.1f},{img_y:.1f}) with size {font_size}pt", "INFO")
        # Canvas will be refreshed by the calling context (_edit_on_press)

    def _edit_selected_object_properties_action(self):
        if not self.selected_object:
            messagebox.showwarning("No Selection", "Please select an object to edit its properties.", parent=self.frame)
            return

        obj_type = self.selected_object.obj_type
        if obj_type == "freehand":
            self._edit_freehand_path_properties(self.selected_object)
        elif obj_type == "text":
            self._edit_text_object_properties(self.selected_object)
        elif obj_type == "line":
            self._edit_line_properties(self.selected_object)
        elif obj_type == "rectangle":
            self._edit_rectangle_properties(self.selected_object)
        elif obj_type == "oval":
            self._edit_oval_properties(self.selected_object)
        else:
            messagebox.showinfo("Not Editable", f"Properties for object type '{obj_type}' are not editable yet.", parent=self.frame)

        # After editing, always redraw and update button states
        self._display_image_on_canvas(use_edit_buffer=self.edit_mode_active and bool(self.image_draw_layer))
        self.update_button_states()

    def _edit_freehand_path_properties(self, path_obj: FreehandPathObject):
        self.shared_state.log(f"Editing properties for FreehandPathObject {path_obj.id}", "DEBUG")

        # Edit Color
        new_color_val = colorchooser.askcolor(initialcolor=path_obj.color, title="Choose Path Color", parent=self.frame)
        if new_color_val and new_color_val[1]:
            path_obj.color = new_color_val[1]
            self.shared_state.log(f"Path {path_obj.id} color changed to {path_obj.color}", "INFO")

        # Edit Thickness
        new_thickness = simpledialog.askinteger("Path Thickness", "Enter new path thickness (e.g., 1, 2, 5):",
                                                parent=self.frame, initialvalue=path_obj.thickness,
                                                minvalue=1, maxvalue=50)
        if new_thickness is not None:
            path_obj.thickness = new_thickness
            self.shared_state.log(f"Path {path_obj.id} thickness changed to {path_obj.thickness}", "INFO")

        # Bounding box of a path doesn't typically change with color/thickness for hit-testing purposes,
        # but visual representation does. No explicit recalculation needed for bbox here.

    def _edit_text_object_properties(self, text_obj: TextObject):
        self.shared_state.log(f"Editing properties for TextObject {text_obj.id}", "DEBUG")

        # Edit Text Content
        new_content = simpledialog.askstring("Edit Text", "Enter new text content:",
                                             parent=self.frame, initialvalue=text_obj.text_content)
        if new_content is not None: # Even empty string is a valid change
            text_obj.text_content = new_content
            self.shared_state.log(f"TextObject {text_obj.id} content changed.", "INFO")

        # Edit Font Family (simple input for now)
        new_font_family = simpledialog.askstring("Edit Font Family", "Enter font family (e.g., Arial, Times New Roman):",
                                                 parent=self.frame, initialvalue=text_obj.font_family)
        if new_font_family:
            text_obj.font_family = new_font_family
            self.shared_state.log(f"TextObject {text_obj.id} font family changed to {text_obj.font_family}", "INFO")

        # Edit Font Size
        new_font_size = simpledialog.askinteger("Edit Font Size", "Enter new font size (points):",
                                                parent=self.frame, initialvalue=text_obj.font_size_pt,
                                                minvalue=6, maxvalue=120)
        if new_font_size is not None:
            text_obj.font_size_pt = new_font_size
            self.shared_state.log(f"TextObject {text_obj.id} font size changed to {text_obj.font_size_pt}pt", "INFO")

        # Update PIL font if family or size changed
        text_obj._update_pil_font() # This is important

        # Edit Color
        new_color_val = colorchooser.askcolor(initialcolor=text_obj.color, title="Choose Text Color", parent=self.frame)
        if new_color_val and new_color_val[1]:
            text_obj.color = new_color_val[1]
            self.shared_state.log(f"TextObject {text_obj.id} color changed to {text_obj.color}", "INFO")

        # Bounding box for text WILL change if content or font properties change.
        # The current calculate_bounding_box for TextObject is a rough estimate.
        # If it were more precise, we'd call text_obj.calculate_bounding_box() here or mark it dirty.
        # For now, the visual update will handle the new appearance.

    def _edit_line_properties(self, line_obj: LineObject):
        self.shared_state.log(f"Editing properties for LineObject {line_obj.id}", "DEBUG")

        new_color_val = colorchooser.askcolor(initialcolor=line_obj.color, title="Choose Line Color", parent=self.frame)
        if new_color_val and new_color_val[1]:
            line_obj.color = new_color_val[1]
            self.shared_state.log(f"Line {line_obj.id} color changed to {line_obj.color}", "INFO")

        new_thickness = simpledialog.askinteger("Line Thickness", "Enter new line thickness:",
                                                parent=self.frame, initialvalue=line_obj.thickness,
                                                minvalue=1, maxvalue=50)
        if new_thickness is not None:
            line_obj.thickness = new_thickness
            self.shared_state.log(f"Line {line_obj.id} thickness changed to {line_obj.thickness}", "INFO")

    def _edit_rectangle_properties(self, rect_obj: RectangleObject):
        self.shared_state.log(f"Editing properties for RectangleObject {rect_obj.id}", "DEBUG")

        new_color_val = colorchooser.askcolor(initialcolor=rect_obj.color, title="Choose Rectangle Outline Color", parent=self.frame)
        if new_color_val and new_color_val[1]:
            rect_obj.color = new_color_val[1] # This is outline color
            self.shared_state.log(f"Rectangle {rect_obj.id} outline color changed to {rect_obj.color}", "INFO")

        new_thickness = simpledialog.askinteger("Rectangle Outline Thickness", "Enter new outline thickness:",
                                                parent=self.frame, initialvalue=rect_obj.thickness,
                                                minvalue=1, maxvalue=50)
        if new_thickness is not None:
            rect_obj.thickness = new_thickness
            self.shared_state.log(f"Rectangle {rect_obj.id} outline thickness changed to {rect_obj.thickness}", "INFO")

        # TODO: Add fill color editing if/when fill_color is implemented for drawing

    def _edit_oval_properties(self, oval_obj: OvalObject):
        self.shared_state.log(f"Editing properties for OvalObject {oval_obj.id}", "DEBUG")

        new_color_val = colorchooser.askcolor(initialcolor=oval_obj.color, title="Choose Oval Outline Color", parent=self.frame)
        if new_color_val and new_color_val[1]:
            oval_obj.color = new_color_val[1] # This is outline color
            self.shared_state.log(f"Oval {oval_obj.id} outline color changed to {oval_obj.color}", "INFO")

        new_thickness = simpledialog.askinteger("Oval Outline Thickness", "Enter new outline thickness:",
                                                parent=self.frame, initialvalue=oval_obj.thickness,
                                                minvalue=1, maxvalue=50)
        if new_thickness is not None:
            oval_obj.thickness = new_thickness
            self.shared_state.log(f"Oval {oval_obj.id} outline thickness changed to {oval_obj.thickness}", "INFO")

        # TODO: Add fill color editing if/when fill_color is implemented for drawing


    def _bring_selected_to_front_action(self):
        if self.selected_object and self.selected_object in self.drawn_object_manager.objects:
            self.drawn_object_manager.objects.remove(self.selected_object)
            self.drawn_object_manager.objects.append(self.selected_object)
            self.shared_state.log(f"Object {self.selected_object.id} brought to front.", "INFO")
            self._display_image_on_canvas(use_edit_buffer=self.edit_mode_active and bool(self.image_draw_layer))
            # update_button_states() will be called if selection changes, but here selection doesn't change.
            # The visual order change is the primary outcome.
        else:
            messagebox.showwarning("Z-Order Error", "No object selected or object not found in manager.", parent=self.frame)

    def _send_selected_to_back_action(self):
        if self.selected_object and self.selected_object in self.drawn_object_manager.objects:
            self.drawn_object_manager.objects.remove(self.selected_object)
            self.drawn_object_manager.objects.insert(0, self.selected_object)
            self.shared_state.log(f"Object {self.selected_object.id} sent to back.", "INFO")
            self._display_image_on_canvas(use_edit_buffer=self.edit_mode_active and bool(self.image_draw_layer))
        else:
            messagebox.showwarning("Z-Order Error", "No object selected or object not found in manager.", parent=self.frame)


    def _get_object_at_canvas_coords(self, canvas_x, canvas_y):
        """Finds the top-most object at the given canvas coordinates."""
        img_x, img_y = self._canvas_to_image_coords(canvas_x, canvas_y)

        # Iterate in reverse to select top-most objects first
        for obj in reversed(self.drawn_object_manager.get_all_objects()):
            try:
                # Use object's own bounding box for hit test (in image coordinates)
                # TODO: This might need refinement for pixel-perfect selection on complex shapes or rotated text.
                # For text, calculate_bounding_box is a rough estimate.
                # A more robust method for canvas items is to check canvas.find_withtag(CURRENT)
                # or use canvas.bbox(item_id_tag) converted back to image coords.
                # However, canvas.bbox requires the object to be drawn and tagged.

                obj_bbox_img = obj.calculate_bounding_box() # (x0, y0, x1, y1) in image coords
                if obj_bbox_img[0] <= img_x <= obj_bbox_img[2] and \
                   obj_bbox_img[1] <= img_y <= obj_bbox_img[3]:
                    return obj
            except NotImplementedError:
                self.shared_state.log(f"Object {obj.id} of type {obj.obj_type} missing calculate_bounding_box.", "WARNING")
                continue
            except Exception as e:
                self.shared_state.log(f"Error during hit-testing object {obj.id}: {e}", "ERROR")
                continue
        return None

    def _update_selection_visuals(self):
        """Draws or clears the selection indicator around the selected object."""
        # Clear previous selection visual
        if self.selection_visual_id:
            self.canvas.delete(self.selection_visual_id)
            self.selection_visual_id = None

        if self.selected_object:
            try:
                # Get bounding box from the object (image coordinates)
                img_bbox = self.selected_object.calculate_bounding_box()

                # Convert to canvas coordinates for drawing the visual
                c_x0, c_y0 = self._image_to_canvas_coords(img_bbox[0], img_bbox[1])
                c_x1, c_y1 = self._image_to_canvas_coords(img_bbox[2], img_bbox[3])

                # Ensure correct ordering for canvas rectangle
                rect_x0, rect_y0 = min(c_x0, c_x1), min(c_y0, c_y1)
                rect_x1, rect_y1 = max(c_x0, c_x1), max(c_y0, c_y1)

                self.selection_visual_id = self.canvas.create_rectangle(
                    rect_x0 - 2, rect_y0 - 2, rect_x1 + 2, rect_y1 + 2, # Add a small padding
                    outline="deepskyblue", width=1, dash=(4, 2), tags="selection_visual"
                )
                self.shared_state.log(f"Selection visual drawn for object {self.selected_object.id} at canvas bbox: ({rect_x0:.1f},{rect_y0:.1f})-({rect_x1:.1f},{rect_y1:.1f})", "DEBUG")
            except NotImplementedError:
                 self.shared_state.log(f"Selected object {self.selected_object.id} cannot calculate bounding box for visual.", "WARNING")
            except Exception as e:
                self.shared_state.log(f"Error creating selection visual: {e}", "ERROR")

    def _crop_on_press(self, event):
        if not self.crop_mode_active: return
        self.crop_start_coords = (event.x, event.y)
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
            self.crop_rect_id = None
        self.shared_state.log(f"Crop press at canvas ({event.x},{event.y})")

    def _crop_on_drag(self, event):
        if not self.crop_mode_active or self.crop_start_coords is None: return
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)

        x0, y0 = self.crop_start_coords
        x1, y1 = event.x, event.y
        # Draw dashed rectangle for crop selection
        self.crop_rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="yellow", dash=(5,3), width=1)

    def _crop_on_release(self, event):
        if not self.crop_mode_active or self.crop_start_coords is None: return
        # Finalize crop rectangle on canvas. Actual crop happens on confirm.
        x0, y0 = self.crop_start_coords
        x1, y1 = event.x, event.y
        if self.crop_rect_id: # Update final coords
             self.canvas.coords(self.crop_rect_id, x0, y0, x1, y1)
        self.shared_state.log(f"Crop selection finalized on canvas at ({x0},{y0}) to ({x1},{y1})")

    def _on_mouse_wheel(self, event):
        if not self.current_image_pil:
            return

        zoom_delta = 0.1
        # 取得滑鼠在canvas上的座標
        mouse_x, mouse_y = event.x, event.y

        # 計算滑鼠在圖片上的相對座標（未縮放前）
        img_x_before = (mouse_x - self.canvas_image_x) / self.zoom_factor
        img_y_before = (mouse_y - self.canvas_image_y) / self.zoom_factor

        # Linux uses event.num (4 for up, 5 for down)
        # Windows/macOS use event.delta (positive for up, negative for down)
        if getattr(event, 'num', None) == 4 or (hasattr(event, 'delta') and event.delta > 0):
            new_zoom = self.zoom_factor * (1 + zoom_delta)
        elif getattr(event, 'num', None) == 5 or (hasattr(event, 'delta') and event.delta < 0):
            new_zoom = self.zoom_factor / (1 + zoom_delta)
        else:
            new_zoom = self.zoom_factor

        # Zoom limits
        new_zoom = max(0.1, min(new_zoom, 5.0))

        # 計算縮放後，讓滑鼠指向的圖片點仍在滑鼠座標下，調整canvas_image_x/y
        self.canvas_image_x = mouse_x - img_x_before * new_zoom
        self.canvas_image_y = mouse_y - img_y_before * new_zoom
        self.zoom_factor = new_zoom

        self.shared_state.log(f"Zoom event. New factor: {self.zoom_factor}", "DEBUG")
        self._display_image_on_canvas()

    def _on_pan_start(self, event):
        if not self.current_image_pil: return
        self.shared_state.log(f"Pan start at ({event.x}, {event.y}). Current image offset: ({self.canvas_image_x}, {self.canvas_image_y})", "DEBUG")
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        # Store the view's state at the beginning of the pan
        self.pan_view_start_x = self.canvas_image_x
        self.pan_view_start_y = self.canvas_image_y
        self.canvas.config(cursor="fleur")

    def _on_pan_motion(self, event):
        if self.pan_start_x is None or self.pan_start_y is None or not self.current_image_pil:
            return

        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y

        # Update image's top-left position on canvas based on original position + delta
        self.canvas_image_x = self.pan_view_start_x + dx
        self.canvas_image_y = self.pan_view_start_y + dy

        self._display_image_on_canvas()

    def _on_pan_end(self, event):
        if not self.current_image_pil: return
        self.shared_state.log("Pan end.", "DEBUG")
        self.pan_start_x = None
        self.pan_start_y = None
        self.canvas.config(cursor="")

    def _bind_pan_events(self):
        self.canvas.bind("<Shift-ButtonPress-1>", self._on_pan_start)
        self.canvas.bind("<Shift-B1-Motion>", self._on_pan_motion)
        self.canvas.bind("<Shift-ButtonRelease-1>", self._on_pan_end)
        self.shared_state.log("Pan events bound.", "DEBUG")

    def _unbind_pan_events(self):
        self.canvas.unbind("<Shift-ButtonPress-1>")
        self.canvas.unbind("<Shift-B1-Motion>")
        self.canvas.unbind("<Shift-ButtonRelease-1>")
        self.shared_state.log("Pan events unbound.", "DEBUG")


    def on_destroy(self):
        # Clean up resources, if any (e.g., close files, stop timers)
        self.shared_state.log(f"ImageEditorModule '{self.module_name}' is being destroyed.")
        super().on_destroy()

# Example of how it might be added to main.py (for testing, not part of the module itself)
if __name__ == '__main__':
    # This block is for direct testing of the module, if needed.
    # It requires main.py and shared_state.py to be in the Python path.
    root = tk.Tk()
    root.geometry("800x600")

    # Mock SharedState and GUIManager for standalone testing if necessary
    class MockGUIManager:
        def hide_module(self, module_name):
            print(f"MockGUIManager: Hide module {module_name}")
        def maximize_module(self, module_name):
            print(f"MockGUIManager: Maximize module {module_name}")
        def restore_modules(self):
            print(f"MockGUIManager: Restore modules")

    mock_shared_state = SharedState(log_level="DEBUG")
    mock_gui_manager = MockGUIManager()

    # The module's frame will be parented to 'root' directly in this test setup
    editor_module = ImageEditorModule(root, mock_shared_state, gui_manager=mock_gui_manager)

    # In the actual application, the module's frame (editor_module.frame) would be
    # managed by the ModularGUI's layout manager.
    # For this test, we pack it directly if it's not already part of the root's layout.
    # The Module base class creates 'self.frame'. We need to make sure it's displayed.

    # To simulate how ModularGUI would handle it, we can pack the module's main frame:
    editor_module.frame.pack(fill=tk.BOTH, expand=True)

    root.title("Image Editor Module Test")
    root.mainloop()
    root.title("Image Editor Module Test")
    root.mainloop()

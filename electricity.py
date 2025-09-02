import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog, colorchooser
from PIL import Image, ImageTk, ImageDraw
import math
import random
import itertools
import numpy as np
import os
import subprocess
from datetime import datetime
import time
import json
import zipfile
import io


# --- 常數設定 ---
HV_COLOR = "#FF4136"  # 高壓顏色 (紅色)
GND_COLOR = "#0074D9" # 接地顏色 (藍色)
SELECTED_OUTLINE_COLOR = "#FFDC00" # 選取外框顏色 (黃色)
HANDLE_COLOR = "#FFDC00" # 控制點顏色 (黃色)
ARC_COLOR = "#7FDBFF" # 電弧顏色 (淺藍)
BACKGROUND_COLOR = "#111111" # 背景色 (深灰)
CONTROL_PANEL_BG = "#f0f0f0" # 控制面板背景色

HANDLE_RADIUS = 5 # 控制點半徑

# --- 參數設定彈出視窗 ---
class ParameterDialog(simpledialog.Dialog):
    """一個通用的參數設定對話框"""
    def __init__(self, parent, title, shape):
        self.shape = shape
        super().__init__(parent, title)

    def body(self, master):
        self.entries = {}
        # 通用參數: 電壓
        tk.Label(master, text="電壓 (V):").grid(row=0, sticky="w")
        self.entries['voltage'] = tk.Entry(master)
        self.entries['voltage'].grid(row=0, column=1)
        self.entries['voltage'].insert(0, str(self.shape.voltage))
        
        # 特定形狀的參數
        if self.shape.shape_type == "Needle":
            tk.Label(master, text="半徑:").grid(row=1, sticky="w")
            self.entries['radius'] = tk.Entry(master)
            self.entries['radius'].grid(row=1, column=1)
            self.entries['radius'].insert(0, str(self.shape.radius))
        elif self.shape.shape_type == "Rod":
            tk.Label(master, text="點 1 (x,y):").grid(row=1, sticky="w")
            self.entries['p1'] = tk.Entry(master)
            self.entries['p1'].grid(row=1, column=1)
            self.entries['p1'].insert(0, f"{self.shape.x1:.1f}, {self.shape.y1:.1f}")
            tk.Label(master, text="點 2 (x,y):").grid(row=2, sticky="w")
            self.entries['p2'] = tk.Entry(master)
            self.entries['p2'].grid(row=2, column=1)
            self.entries['p2'].insert(0, f"{self.shape.x2:.1f}, {self.shape.y2:.1f}")
        elif self.shape.shape_type in ["Plate", "Arbitrary"]:
            for i, p in enumerate(self.shape.points):
                tk.Label(master, text=f"點 {i+1} (x,y):").grid(row=i+1, sticky="w")
                self.entries[f'p{i}'] = tk.Entry(master)
                self.entries[f'p{i}'].grid(row=i+1, column=1)
                self.entries[f'p{i}'].insert(0, f"{p[0]:.1f}, {p[1]:.1f}")
        return self.entries['voltage'] 

    def apply(self):
        try:
            params = {}
            params['voltage'] = float(self.entries['voltage'].get())
            
            if self.shape.shape_type == "Needle":
                params['radius'] = float(self.entries['radius'].get())
            elif self.shape.shape_type == "Rod":
                p1 = list(map(float, self.entries['p1'].get().split(',')))
                p2 = list(map(float, self.entries['p2'].get().split(',')))
                params['points'] = [p1, p2]
            elif self.shape.shape_type in ["Plate", "Arbitrary"]:
                points = []
                for i in range(len(self.shape.points)):
                    p = list(map(float, self.entries[f'p{i}'].get().split(',')))
                    points.append(p)
                params['points'] = points
            
            self.shape.update_params(**params)
        except (ValueError, IndexError):
            messagebox.showerror("輸入錯誤", "無效的輸入格式！請檢查您的輸入。")


# --- 【新增】高解析度匯出彈出視窗 ---
class ExportDialog(simpledialog.Dialog):
    """一個用於設定高解析度匯出參數的對話框"""
    def __init__(self, parent, title):
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        # 佈局
        master.grid_columnconfigure(1, weight=1)

        # 縮放比例
        tk.Label(master, text="縮放比例 (e.g., 2, 4, 8):").grid(row=0, sticky="w")
        self.scale_entry = tk.Entry(master)
        self.scale_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.scale_entry.insert(0, "4")

        # 檔案路徑
        tk.Label(master, text="儲存路徑:").grid(row=1, sticky="w")
        self.path_entry = tk.Entry(master)
        self.path_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        browse_button = tk.Button(master, text="...", command=self._browse_file)
        browse_button.grid(row=1, column=2, padx=5, pady=5)

        return self.scale_entry # initial focus

    def _browse_file(self):
        filepath = filedialog.asksaveasfilename(
            parent=self, # 確保對話框在頂層
            title="匯出圖片為...",
            defaultextension=".png",
            filetypes=[("PNG 圖片", "*.png"), ("JPEG 圖片", "*.jpg"), ("BMP 圖片", "*.bmp")]
        )
        if filepath:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, filepath)

    def validate(self):
        # 驗證縮放比例
        try:
            scale = float(self.scale_entry.get())
            if scale <= 0:
                messagebox.showwarning("輸入無效", "縮放比例必須是正數。", parent=self)
                return 0
        except ValueError:
            messagebox.showwarning("輸入無效", "縮放比例必須是一個數字。", parent=self)
            return 0

        # 驗證檔案路徑
        filepath = self.path_entry.get()
        if not filepath:
            messagebox.showwarning("輸入無效", "請選擇一個有效的儲存路徑。", parent=self)
            return 0

        self.result = (scale, filepath)
        return 1

    def apply(self):
        # The result is already set in validate()
        pass


# --- 幾何物體基底類別 ---
class Shape:
    # Constructor now takes the main app instance instead of the canvas
    def __init__(self, app, voltage):
        self.app = app
        self.canvas = app.canvas
        self.voltage = voltage
        # These properties are now obsolete with the new rendering engine
        self.id = None
        self.outline_id = None
        self.handles = []
        self.shape_type = "Shape"

    def draw(self):
        """This method is now obsolete. Drawing is handled by draw_to_pillow."""
        pass # Obsolete
    def draw_to_pillow(self, draw): raise NotImplementedError

    def draw_selection_to_pillow(self, draw):
        """Draws the selection outline and handles on a Pillow ImageDraw context."""
        pass
    def contains(self, px, py): raise NotImplementedError

    def move(self, dx, dy): raise NotImplementedError
    def get_handle_at(self, x, y): return None
    def move_handle(self, handle_index, new_x, new_y): pass
    def get_center(self): raise NotImplementedError
    def get_emission_points(self, num_points=20): raise NotImplementedError
    
    def select(self):
        """This method is now obsolete. Selection is handled by the renderer."""
        pass # Obsolete

    def deselect(self):
        """This method is now obsolete. Selection is handled by the renderer."""
        pass # Obsolete

    def _create_handles(self): pass # Obsolete
    def _delete_handles(self): pass # Obsolete

    def update_color(self):
        """This method is now obsolete. Color is determined during rendering."""
        pass # Obsolete

    def update_params(self, **kwargs):
        if 'voltage' in kwargs:
            self.voltage = kwargs['voltage']
        # Trigger a redraw instead of calling obsolete methods
        self.app.redraw_canvas()

# --- 各種形狀的具體實現 ---
class Needle(Shape):
    def __init__(self, app, x, y, voltage=10000, radius=10):
        super().__init__(app, voltage)
        self.x, self.y, self.radius = x, y, radius
        self.shape_type = "Needle"

    def contains(self, px, py):
        return (px - self.x)**2 + (py - self.y)**2 <= self.radius**2

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.app.redraw_canvas()

    def get_outline_points(self):
        # This method no longer reads from canvas, but calculates based on geometry
        return [self.x - self.radius, self.y - self.radius, self.x + self.radius, self.y + self.radius]
    
    def get_center(self): return (self.x, self.y)

    def get_emission_points(self, num_points=24):
        points = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            px = self.x + self.radius * math.cos(angle)
            py = self.y + self.radius * math.sin(angle)
            points.append((px, py))
        return points

    def update_params(self, **kwargs):
        if 'radius' in kwargs: self.radius = kwargs['radius']
        super().update_params(**kwargs)

    def draw_to_pillow(self, draw, scale=1.0):
        """Draws the shape on a Pillow ImageDraw context."""
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        bbox_unscaled = self.get_outline_points()
        bbox_scaled = [p * scale for p in bbox_unscaled]
        draw.ellipse(bbox_scaled, fill=color, outline="white", width=int(1 * scale))

    def draw_selection_to_pillow(self, draw, scale=1.0):
        """Draws the selection outline and handles on a Pillow ImageDraw context."""
        bbox_unscaled = self.get_outline_points()
        bbox_scaled = [p * scale for p in bbox_unscaled]
        draw.ellipse(bbox_scaled, fill=None, outline=SELECTED_OUTLINE_COLOR, width=int(2 * scale))
        # Needle has no handles.

class Rod(Shape):
    def __init__(self, app, x1, y1, x2, y2, voltage=10000, thickness=5):
        super().__init__(app, voltage)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.thickness = thickness
        self.shape_type = "Rod"

    def contains(self, px, py):
        dx, dy = self.x2 - self.x1, self.y2 - self.y1
        if dx == 0 and dy == 0: return False
        t = ((px - self.x1) * dx + (py - self.y1) * dy) / (dx*dx + dy*dy)
        t = max(0, min(1, t))
        closest_x, closest_y = self.x1 + t * dx, self.y1 + t * dy
        dist_sq = (px - closest_x)**2 + (py - closest_y)**2
        return dist_sq < (self.thickness * 1.5)**2

    def move(self, dx, dy):
        self.x1 += dx; self.y1 += dy
        self.x2 += dx; self.y2 += dy
        self.app.redraw_canvas()
    
    def get_outline_points(self):
        return (self.x1, self.y1, self.x2, self.y2)

    def get_handle_at(self, x, y):
        # This logic no longer uses canvas items but pure geometry
        for i, (hx, hy) in enumerate([(self.x1, self.y1), (self.x2, self.y2)]):
            if (x - hx)**2 + (y - hy)**2 < HANDLE_RADIUS**2:
                return i
        return None

    def move_handle(self, handle_index, new_x, new_y):
        if handle_index == 0:
            self.x1, self.y1 = new_x, new_y
        else:
            self.x2, self.y2 = new_x, new_y
        self.app.redraw_canvas()
    
    def get_center(self): return ((self.x1+self.x2)/2, (self.y1+self.y2)/2)

    def get_emission_points(self, num_points=20):
        points = []
        for i in range(num_points + 1):
            t = i / num_points
            x = self.x1 + t * (self.x2 - self.x1)
            y = self.y1 + t * (self.y2 - self.y1)
            points.append((x, y))
        return points

    def update_params(self, **kwargs):
        if 'points' in kwargs:
            self.x1, self.y1 = kwargs['points'][0]
            self.x2, self.y2 = kwargs['points'][1]
        super().update_params(**kwargs)

    def draw_to_pillow(self, draw, scale=1.0):
        """Draws the shape on a Pillow ImageDraw context."""
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        draw.line(
            (self.x1 * scale, self.y1 * scale, self.x2 * scale, self.y2 * scale),
            fill=color, width=int(self.thickness * scale)
        )

    def draw_selection_to_pillow(self, draw, scale=1.0):
        """Draws the selection outline and handles on a Pillow ImageDraw context."""
        draw.line((self.x1 * scale, self.y1 * scale, self.x2 * scale, self.y2 * scale), fill=SELECTED_OUTLINE_COLOR, width=int(3 * scale))
        for x, y in [(self.x1, self.y1), (self.x2, self.y2)]:
            r = HANDLE_RADIUS * scale
            x_s, y_s = x * scale, y * scale
            draw.ellipse([x_s-r, y_s-r, x_s+r, y_s+r], fill=HANDLE_COLOR, outline='white')

class Plate(Shape):
    def __init__(self, app, x, y, voltage=0, width=150, height=30):
        super().__init__(app, voltage)
        w, h = width/2, height/2
        self.points = [(x-w, y-h), (x+w, y-h), (x+w, y+h), (x-w, y+h)]
        self.shape_type = "Plate"
        
    def contains(self, px, py):
        inside = False
        j = len(self.points) - 1
        for i in range(len(self.points)):
            xi, yi = self.points[i]
            xj, yj = self.points[j]
            intersect = ((yi > py) != (yj > py)) and \
                        (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
            if intersect:
                inside = not inside
            j = i
        return inside

    def move(self, dx, dy):
        self.points = [(p[0]+dx, p[1]+dy) for p in self.points]
        self.app.redraw_canvas()

    def get_outline_points(self):
        return [coord for point in self.points for coord in point]

    def get_handle_at(self, x, y):
        for i, (hx, hy) in enumerate(self.points):
            if (x - hx)**2 + (y - hy)**2 < HANDLE_RADIUS**2:
                return i
        return None

    def move_handle(self, handle_index, new_x, new_y):
        self.points[handle_index] = (new_x, new_y)
        self.app.redraw_canvas()

    def get_center(self):
        cx = sum(p[0] for p in self.points) / len(self.points)
        cy = sum(p[1] for p in self.points) / len(self.points)
        return (cx, cy)

    def get_emission_points(self, points_per_edge=10):
        emission_pts = []
        num_vertices = len(self.points)
        for i in range(num_vertices):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % num_vertices]
            for j in range(points_per_edge):
                t = j / points_per_edge
                x = p1[0] + t * (p2[0] - p1[0])
                y = p1[1] + t * (p2[1] - p1[1])
                emission_pts.append((x, y))
        return emission_pts
    
    def update_params(self, **kwargs):
        if 'points' in kwargs:
            self.points = kwargs['points']
        super().update_params(**kwargs)

    def draw_to_pillow(self, draw, scale=1.0):
        """Draws the shape on a Pillow ImageDraw context."""
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        if len(self.points) > 1:
            scaled_points = [(p[0] * scale, p[1] * scale) for p in self.points]
            draw.polygon(scaled_points, fill=color, outline="white", width=int(1 * scale))

    def draw_selection_to_pillow(self, draw, scale=1.0):
        """Draws the selection outline and handles on a Pillow ImageDraw context."""
        if len(self.points) > 1:
            scaled_points = [(p[0] * scale, p[1] * scale) for p in self.points]
            draw.polygon(scaled_points, fill=None, outline=SELECTED_OUTLINE_COLOR, width=int(2 * scale))
        # Draw handles
        for x, y in self.points:
            r = HANDLE_RADIUS * scale
            x_s, y_s = x * scale, y * scale
            draw.ellipse([x_s-r, y_s-r, x_s+r, y_s+r], fill=HANDLE_COLOR, outline='white')

class ArbitraryShape(Shape):
    def __init__(self, app, points, voltage=0):
        super().__init__(app, voltage)
        self.points = points 
        self.shape_type = "Arbitrary"
        
    def contains(self, px, py):
        inside = False
        j = len(self.points) - 1
        for i in range(len(self.points)):
            xi, yi = self.points[i]
            xj, yj = self.points[j]
            intersect = ((yi > py) != (yj > py)) and \
                        (px < (xj - xi) * (py - yi) / (yj - yi) + xi)
            if intersect:
                inside = not inside
            j = i
        return inside

    def move(self, dx, dy):
        self.points = [(p[0]+dx, p[1]+dy) for p in self.points]
        self.app.redraw_canvas()

    def get_outline_points(self):
        return [coord for point in self.points for coord in point]

    def get_handle_at(self, x, y):
        for i, (hx, hy) in enumerate(self.points):
            if (x - hx)**2 + (y - hy)**2 < HANDLE_RADIUS**2:
                return i
        return None

    def move_handle(self, handle_index, new_x, new_y):
        self.points[handle_index] = (new_x, new_y)
        self.app.redraw_canvas()

    def get_center(self):
        if not self.points: return (0, 0)
        cx = sum(p[0] for p in self.points) / len(self.points)
        cy = sum(p[1] for p in self.points) / len(self.points)
        return (cx, cy)

    def get_emission_points(self, points_per_edge=10):
        emission_pts = []
        num_vertices = len(self.points)
        if num_vertices < 2: return []
        for i in range(num_vertices):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % num_vertices]
            for j in range(points_per_edge):
                t = j / points_per_edge
                x = p1[0] + t * (p2[0] - p1[0])
                y = p1[1] + t * (p2[1] - p1[1])
                emission_pts.append((x, y))
        return emission_pts
    
    def update_params(self, **kwargs):
        if 'points' in kwargs:
            self.points = kwargs['points']
        super().update_params(**kwargs)

    def draw_to_pillow(self, draw, scale=1.0):
        """Draws the shape on a Pillow ImageDraw context."""
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        if len(self.points) > 1:
            scaled_points = [(p[0] * scale, p[1] * scale) for p in self.points]
            draw.polygon(scaled_points, fill=color, outline="white", width=int(1 * scale))

    def draw_selection_to_pillow(self, draw, scale=1.0):
        """Draws the selection outline and handles on a Pillow ImageDraw context."""
        if len(self.points) > 1:
            scaled_points = [(p[0] * scale, p[1] * scale) for p in self.points]
            draw.polygon(scaled_points, fill=None, outline=SELECTED_OUTLINE_COLOR, width=int(2 * scale))
        # Draw handles
        for x, y in self.points:
            r = HANDLE_RADIUS * scale
            x_s, y_s = x * scale, y * scale
            draw.ellipse([x_s-r, y_s-r, x_s+r, y_s+r], fill=HANDLE_COLOR, outline='white')


# --- 新增: 可裝飾的圖片物件 ---
class DecorativeImage:
    def __init__(self, canvas, x, y, pil_image, app):
        self.canvas = canvas
        self.pil_image_original = pil_image.convert("RGBA")
        self.x, self.y = x, y
        self.scale = 1.0
        self.angle = 0.0
        self.id = None
        self.tk_image = None  # 防止被垃圾回收
        self.outline_id = None
        self.handles = {}  # {'scale': id, 'rotate': id}
        self.shape_type = "Image"
        self.app = app # 儲存 App 實例的引用
        self.draw()

    def draw(self):
        """This method is now obsolete. Drawing is handled by draw_to_pillow."""
        pass

    def get_transformed_image(self, export_scale=1.0):
        """Applies rotation and scaling to the original PIL image and returns a new PIL image."""
        # 1. 旋轉: expand=True可確保旋轉後圖片不被裁切
        rotated_img = self.pil_image_original.rotate(self.angle, resample=Image.Resampling.BICUBIC, expand=True)

        # 2. 縮放
        w, h = rotated_img.size
        final_scale = self.scale * export_scale
        new_size = (int(w * final_scale), int(h * final_scale))
        # 使用LANCZOS以獲得較好的縮放品質
        scaled_img = rotated_img.resize(new_size, Image.Resampling.LANCZOS)
        return scaled_img

    def draw_to_pillow(self, main_image, scale=1.0):
        """Renders the transformed image onto the main Pillow image context."""
        transformed_img = self.get_transformed_image(scale)
        # The position (self.x, self.y) is the center, so we need to calculate the top-left corner for pasting.
        w, h = transformed_img.size
        paste_x = int(self.x * scale - w / 2)
        paste_y = int(self.y * scale - h / 2)
        # The image might have RGBA transparency, so we should use it as the mask for pasting.
        if transformed_img.mode == 'RGBA':
            main_image.paste(transformed_img, (paste_x, paste_y), transformed_img)
        else:
            main_image.paste(transformed_img, (paste_x, paste_y))

    def draw_selection_to_pillow(self, draw, scale=1.0):
        """Draws the selection outline and handles on a Pillow ImageDraw context."""
        w, h = self.pil_image_original.size

        # 1. Draw outline
        w_scaled = w * self.scale * scale / 2
        h_scaled = h * self.scale * scale / 2
        local_points = [(-w_scaled, -h_scaled), (w_scaled, -h_scaled), (w_scaled, h_scaled), (-w_scaled, h_scaled)]
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        center_x_s, center_y_s = self.x * scale, self.y * scale

        world_points = []
        for p_x, p_y in local_points:
            world_x = (p_x * cos_a - p_y * sin_a) + center_x_s
            world_y = (p_x * sin_a + p_y * cos_a) + center_y_s
            world_points.append((world_x, world_y))

        draw.polygon(world_points, fill=None, outline=SELECTED_OUTLINE_COLOR, width=int(2 * scale))

        # 2. Draw handles
        w_s = w * self.scale * scale
        h_s = h * self.scale * scale
        handle_positions = { 'scale': (w_s / 2, h_s / 2), 'rotate': (w_s / 2, -h_s / 2) }

        for name, (p_x, p_y) in handle_positions.items():
            world_x = (p_x * cos_a - p_y * sin_a) + center_x_s
            world_y = (p_x * sin_a + p_y * cos_a) + center_y_s
            r = HANDLE_RADIUS * scale
            draw.ellipse([world_x-r, world_y-r, world_x+r, world_y+r], fill=HANDLE_COLOR, outline='white')

    def contains(self, px, py):
        # 使用旋轉後的邊界框進行點選偵測
        # 先將點轉換回圖片的本地座標系 (反向旋轉)
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        local_x = (px - self.x) * cos_a + (py - self.y) * sin_a
        local_y = -(px - self.x) * sin_a + (py - self.y) * cos_a

        # 取得原始圖片縮放後的尺寸
        w, h = self.pil_image_original.size
        scaled_w, scaled_h = w * self.scale / 2, h * self.scale / 2

        # 判斷點是否在本地座標的矩形內
        return -scaled_w <= local_x <= scaled_w and -scaled_h <= local_y <= scaled_h

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.app.redraw_canvas()

    def select(self):
        """This method is now obsolete. Selection is handled by the renderer."""
        pass

    def deselect(self):
        """This method is now obsolete. Selection is handled by the renderer."""
        pass

    def _create_handles(self):
        """This method is now obsolete."""
        pass

    def _delete_handles(self):
        """This method is now obsolete."""
        pass

    def get_handle_at(self, x, y):
        # This logic is now based on pure geometry, not canvas items.
        w, h = self.pil_image_original.size
        w_s, h_s = w * self.scale, h * self.scale
        handle_positions = {
            'scale': (w_s / 2, h_s / 2),
            'rotate': (w_s / 2, -h_s / 2)
        }
        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        for name, (p_x, p_y) in handle_positions.items():
            world_x = (p_x * cos_a - p_y * sin_a) + self.x
            world_y = (p_x * sin_a + p_y * cos_a) + self.y
            if (x - world_x)**2 + (y - world_y)**2 < HANDLE_RADIUS**2:
                return name
        return None

    def move_handle(self, handle_name, new_x, new_y):
        dx, dy = new_x - self.x, new_y - self.y

        if handle_name == 'scale':
            orig_w, orig_h = self.pil_image_original.size
            # 用控制點到中心的距離來決定縮放比例
            dist = math.hypot(dx, dy)
            # 原始控制點到中心的距離
            orig_dist = math.hypot(orig_w / 2, orig_h / 2)
            if orig_dist > 1:
                self.scale = dist / orig_dist
                if self.scale < 0.05: self.scale = 0.05 # 避免縮太小

        elif handle_name == 'rotate':
            # 用滑鼠位置與中心點構成的角度來決定旋轉角度
            # 減去控制點本身的初始角度 (右上角)
            orig_w, orig_h = self.pil_image_original.size
            base_angle_rad = math.atan2(-orig_h / 2, orig_w / 2)
            mouse_angle_rad = math.atan2(dy, dx)
            self.angle = math.degrees(mouse_angle_rad - base_angle_rad)

        self.app.redraw_canvas()

    def set_layer(self, layer_pos):
        active_layer = self.app.get_active_layer()
        if layer_pos == 'front':
            active_layer.top_images.add(self)
        elif layer_pos == 'back':
            if self in active_layer.top_images:
                active_layer.top_images.remove(self)
        self.app.redraw_canvas()

# --- 【新增】速率控制圖表 (線性內插版本) ---
class SpeedControlGraph(tk.Canvas):
    def __init__(self, master, on_change_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_change_callback = on_change_callback
        self.points = []
        self.total_frames = 0

        self.padding = {'left': 40, 'right': 10, 'top': 10, 'bottom': 20}
        self.max_speed = 10.0
        self.point_radius = 5
        self.line_color = "#00A0FF"
        self.bg_color = BACKGROUND_COLOR
        self.grid_color = "#444444"
        self.font_color = "#FFFFFF"

        self.drag_data = {}
        self.config(bg=self.bg_color, highlightthickness=0)

        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Button-3>", self._on_right_click)
        self.reset(0)

    def _x_to_percent(self, x):
        graph_width = self.winfo_width() - self.padding['left'] - self.padding['right']
        if graph_width <= 0: return 0.0
        return max(0.0, min(1.0, (x - self.padding['left']) / graph_width))

    def _y_to_speed(self, y):
        graph_height = self.winfo_height() - self.padding['top'] - self.padding['bottom']
        if graph_height <= 0: return 0.0
        return max(0.0, min(self.max_speed, self.max_speed * (1 - (y - self.padding['top']) / graph_height)))

    def _percent_to_x(self, p):
        graph_width = self.winfo_width() - self.padding['left'] - self.padding['right']
        return self.padding['left'] + p * graph_width

    def _speed_to_y(self, s):
        graph_height = self.winfo_height() - self.padding['top'] - self.padding['bottom']
        return self.padding['top'] + (1 - s / self.max_speed) * graph_height

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 2 or h < 2: return

        # Draw axes and grid lines
        self.create_rectangle(self.padding['left'], self.padding['top'], w - self.padding['right'], h - self.padding['bottom'], outline=self.grid_color)
        self.create_text(self.padding['left'] / 2, h - self.padding['bottom'], text="0%", fill=self.font_color, font=("Arial", 8))
        self.create_text(w - self.padding['right'], h - self.padding['bottom'] + 10, text="100%", fill=self.font_color, font=("Arial", 8))
        self.create_text(self.padding['left'] / 2, self.padding['top'], text=f"{int(self.max_speed)}x", fill=self.font_color, font=("Arial", 8))
        self.create_text(self.padding['left'] / 2, h - self.padding['bottom'], text="0x", fill=self.font_color, font=("Arial", 8), anchor='w')

        if not self.points: return

        # Draw lines connecting points
        tk_points = []
        for p in self.points:
            tk_points.append(self._percent_to_x(p[0]))
            tk_points.append(self._speed_to_y(p[1]))
        self.create_line(tk_points, fill=self.line_color, width=2)

        # Draw points (handles)
        for i, p in enumerate(self.points):
            x = self._percent_to_x(p[0])
            y = self._speed_to_y(p[1])
            self.create_oval(x - self.point_radius, y - self.point_radius, x + self.point_radius, y + self.point_radius,
                             fill=self.line_color, outline='white', tags=f"point_{i}")

    def _get_point_at(self, x, y):
        for i, p in enumerate(self.points):
            px = self._percent_to_x(p[0])
            py = self._speed_to_y(p[1])
            if (x - px)**2 + (y - py)**2 < self.point_radius**2:
                return i
        return None

    def _on_press(self, event):
        if not self.total_frames > 0: return
        point_idx = self._get_point_at(event.x, event.y)
        if point_idx is not None:
            self.drag_data = {'type': 'point', 'index': point_idx}
        else:
            # Add a new point on the line
            new_percent = self._x_to_percent(event.x)
            new_speed = self._y_to_speed(event.y)
            self.points.append((new_percent, new_speed))
            self.points.sort(key=lambda p: p[0])
            new_idx = self.points.index((new_percent, new_speed))
            self.drag_data = {'type': 'point', 'index': new_idx}
            self.draw()

    def _on_drag(self, event):
        if not self.drag_data or not self.total_frames > 0: return

        idx = self.drag_data['index']

        # Prevent dragging start/end points horizontally
        if idx == 0 or idx == len(self.points) - 1:
            new_percent = self.points[idx][0]
        else:
            new_percent = self._x_to_percent(event.x)

        new_speed = self._y_to_speed(event.y)

        # Clamp horizontal position to be between neighbors
        if idx > 0:
            new_percent = max(self.points[idx-1][0], new_percent)
        if idx < len(self.points) - 1:
            new_percent = min(self.points[idx+1][0], new_percent)

        self.points[idx] = (new_percent, new_speed)
        self.draw()

    def _on_release(self, event):
        if self.drag_data:
            self.drag_data = {}
            if self.on_change_callback:
                self.on_change_callback()

    def _on_right_click(self, event):
        if not self.total_frames > 0: return
        point_idx = self._get_point_at(event.x, event.y)
        # Allow deleting any point except the first and last
        if point_idx is not None and 0 < point_idx < len(self.points) - 1:
            self.points.pop(point_idx)
            self.draw()
            if self.on_change_callback:
                self.on_change_callback()

    def reset(self, total_frames):
        self.total_frames = total_frames
        if self.total_frames > 0:
            self.points = [(0.0, 1.0), (1.0, 1.0)]
        else:
            self.points = []
        self.draw()

    def get_points(self):
        """Returns a sorted list of control points."""
        return sorted(self.points, key=lambda p: p[0])

    def set_points(self, points):
        """Sets the control points for the graph and redraws."""
        self.points = sorted(points, key=lambda p: p[0])
        self.draw()

# --- 【新增】電弧彩現器 (Pillow版本) ---
def hex_to_rgb(hex_color):
    """Converts a hex color string to an (r, g, b) tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6:
        return (0, 0, 0) # Return black on error
    try:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        return (0, 0, 0)

class ArcRenderer:
    def __init__(self, appearance_params):
        self.params = appearance_params
        self.arc_rgb = hex_to_rgb(self.params.get('arc_color', '#7FDBFF'))
        self.white_rgb = (255, 255, 255)

    def _interpolate_rgb(self, rgb1, rgb2, factor):
        """Linearly interpolates between two RGB tuples."""
        factor = max(0.0, min(1.0, factor))
        r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * factor)
        g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * factor)
        b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * factor)
        return (r, g, b)

    def _get_glow_alpha_from_profile(self, normalized_dist, glow_falloff_points):
        normalized_dist = max(0, min(1, normalized_dist))
        for i in range(len(glow_falloff_points) - 1):
            p1, p2 = glow_falloff_points[i], glow_falloff_points[i+1]
            if p1[0] <= normalized_dist <= p2[0]:
                dist_range = p2[0] - p1[0]
                if dist_range == 0: return p1[1]
                local_factor = (normalized_dist - p1[0]) / dist_range
                return p1[1] + local_factor * (p2[1] - p1[1])
        return glow_falloff_points[-1][1]

    def _draw_arc_segment(self, segment_data, draw_context, scale=1.0):
        p1_unscaled, p2_unscaled = segment_data['p1'], segment_data['p2']
        p1 = (p1_unscaled[0] * scale, p1_unscaled[1] * scale)
        p2 = (p2_unscaled[0] * scale, p2_unscaled[1] * scale)
        thickness_ratio, life = segment_data['thickness_ratio'], segment_data['life']

        base_thickness = self.params.get('arc_max_thickness', 2.0) * thickness_ratio * scale
        if base_thickness < 0.2: return

        max_life = self.params.get('arc_max_life', 200)
        life_factor = max(0, min(1, life / max_life if max_life > 0 else 0))
        core_thickness = base_thickness * (0.2 + life_factor * 0.8)
        if core_thickness < 0.2: return

        r_glow, g_glow, b_glow = self.arc_rgb

        if self.params.get('arc_glow_strength', 0.4) > 0:
            num_glow_layers = 15
            max_glow_radius = core_thickness / 2 * (1 + self.params.get('arc_glow_strength', 0.4) * 3.0)
            glow_falloff_points = self.params.get('glow_falloff_points', [])

            for i in range(num_glow_layers, 0, -1):
                normalized_dist = i / num_glow_layers
                alpha = self._get_glow_alpha_from_profile(normalized_dist, glow_falloff_points)
                if alpha <= 0.01: continue

                layer_color_rgba = (r_glow, g_glow, b_glow, int(alpha * 255))
                layer_width = max_glow_radius * normalized_dist * 2

                if layer_width >= 1:
                    draw_context.line([p1, p2], fill=layer_color_rgba, width=int(layer_width))

        # Draw the core of the arc
        core_rgb = self._interpolate_rgb(self.arc_rgb, self.white_rgb, life_factor)
        core_color_rgba = (*core_rgb, 255) # Opaque core
        if core_thickness >= 1:
            draw_context.line((*p1, *p2), fill=core_color_rgba, width=int(core_thickness))

    def render_frame_data(self, frame_data, draw_context, scale=1.0):
        for segment in frame_data:
            self._draw_arc_segment(segment, draw_context, scale)

# --- 模擬器 (V9.0 - 資料導向模型) ---
class Simulator:
    def __init__(self, all_shapes, sim_params):
        self.all_shapes = all_shapes
        self.params = sim_params
        self.target_shapes = []
        self.target_points = {}
        self.active_arcs = []
        self.simulation_data = [] # 儲存每一幀的電弧線段

    def _calculate_electric_field_at(self, p_x, p_y):
        total_ex, total_ey = 0.0, 0.0
        for shape in self.all_shapes:
            charge_points = shape.get_emission_points()
            if not charge_points: continue
            point_voltage = shape.voltage / len(charge_points)
            for (cx, cy) in charge_points:
                dx, dy = p_x - cx, p_y - cy
                dist_sq = dx*dx + dy*dy
                if dist_sq < 1.0: continue
                inv_dist_cubed = dist_sq**(-1.5)
                ex = point_voltage * dx * inv_dist_cubed
                ey = point_voltage * dy * inv_dist_cubed
                total_ex += ex
                total_ey += ey
        return total_ex, total_ey

    def _get_next_point(self, current_point, current_direction):
        base_angle = math.atan2(current_direction[1], current_direction[0])
        probes, weights = [], []
        probe_angle_rad = math.radians(self.params['probe_angle'])
        
        for i in range(int(self.params['probe_count'])):
            angle_offset = (i / (self.params['probe_count'] - 1) - 0.5) * probe_angle_rad if self.params['probe_count'] > 1 else 0
            angle = base_angle + angle_offset
            probe_x = current_point[0] + self.params['step_length'] * math.cos(angle)
            probe_y = current_point[1] + self.params['step_length'] * math.sin(angle)
            ex, ey = self._calculate_electric_field_at(probe_x, probe_y)
            field_projection = ex * math.cos(angle) + ey * math.sin(angle)
            if field_projection > 0:
                probes.append(((probe_x, probe_y), (math.cos(angle), math.sin(angle))))
                weights.append(field_projection ** self.params['field_exponent'])
        
        if not weights or sum(weights) == 0: return None, None
        return random.choices(probes, weights=weights, k=1)[0]

    def run_simulation(self, arc_jobs, canvas_size):
        if not arc_jobs:
            print("警告：沒有符合放電條件的物體配對。")
            return []

        self.target_shapes = list(set(job['target'] for job in arc_jobs))
        self.active_arcs = []
        self.simulation_data = []

        self.target_points.clear()
        for shape in self.target_shapes:
            self.target_points[shape] = shape.get_emission_points()

        for job in arc_jobs:
            source = job['source']
            possible_starts = source.get_emission_points()
            if not possible_starts: continue

            best_start_point, max_field_strength_sq = None, -1
            for start_point in possible_starts:
                ex, ey = self._calculate_electric_field_at(*start_point)
                field_strength_sq = ex*ex + ey*ey
                if field_strength_sq > max_field_strength_sq:
                    max_field_strength_sq = field_strength_sq
                    best_start_point = start_point
            
            if best_start_point:
                ex, ey = self._calculate_electric_field_at(*best_start_point)
                mag = math.hypot(ex, ey)
                initial_direction = (ex/mag, ey/mag) if mag > 1e-9 else (1, 0)
                self.active_arcs.append({
                    'current': best_start_point, 'direction': initial_direction,
                    'thickness_ratio': 1.0, 'life': self.params['arc_max_life']
                })

        if not self.active_arcs:
            messagebox.showwarning("模擬錯誤", "找不到任何有效的放電起始點。")
            return []

        # --- 主模擬迴圈 (取代 step() 和 after()) ---
        while self.active_arcs:
            current_frame_segments = []
            next_active_arcs = []

            for arc_data in self.active_arcs:
                current_point, current_direction = arc_data['current'], arc_data['direction']
                thickness_ratio, life = arc_data['thickness_ratio'], arc_data['life']

                if life <= 0 or thickness_ratio < 0.01: continue

                ex, ey = self._calculate_electric_field_at(*current_point)
                field_strength = math.hypot(ex, ey)
                decay_factor = self.params['arc_threshold_v_pixel'] * 0.3
                dynamic_interruption_chance = self.params['path_interruption_chance'] * math.exp(-field_strength / decay_factor) if decay_factor > 1e-6 else 1.0
                if random.random() < dynamic_interruption_chance: continue

                jump_occurred = False
                if self.params['final_jump_distance'] > 0:
                    min_dist_sq = self.params['final_jump_distance'] ** 2
                    closest_point = None
                    for shape in self.target_shapes:
                        for p in self.target_points.get(shape, []):
                            dist_sq = (current_point[0] - p[0])**2 + (current_point[1] - p[1])**2
                            if dist_sq < min_dist_sq:
                                min_dist_sq, closest_point = dist_sq, p
                    if closest_point:
                        current_frame_segments.append({'p1': current_point, 'p2': closest_point, 'thickness_ratio': thickness_ratio * 1.5, 'life': life})
                        jump_occurred = True
                
                if jump_occurred: continue

                if any(t.contains(*current_point) for t in self.target_shapes) or \
                   not (0 < current_point[0] < canvas_size[0] and 0 < current_point[1] < canvas_size[1]):
                    continue

                next_point, next_direction = self._get_next_point(current_point, current_direction)
                if next_point is None: continue

                current_frame_segments.append({'p1': current_point, 'p2': next_point, 'thickness_ratio': thickness_ratio, 'life': life})
                next_active_arcs.append({'current': next_point, 'direction': next_direction, 'thickness_ratio': thickness_ratio, 'life': life - 1})

                if random.random() < self.params['fork_chance']:
                    fork_point, fork_direction = self._get_next_point(current_point, current_direction)
                    if fork_point:
                        fork_thickness_ratio = thickness_ratio * 0.7
                        current_frame_segments.append({'p1': current_point, 'p2': fork_point, 'thickness_ratio': fork_thickness_ratio, 'life': life})
                        next_active_arcs.append({'current': fork_point, 'direction': fork_direction, 'thickness_ratio': fork_thickness_ratio, 'life': life - 1})

            self.active_arcs = next_active_arcs
            self.simulation_data.append(current_frame_segments)

        return self.simulation_data


# --- 【新增】圖層資料結構 ---
class Layer:
    """一個包含獨立模擬場景所有狀態的資料結構。"""
    _next_id = 1

    def __init__(self, name=None):
        if name is None:
            self.name = f"圖層 {Layer._next_id}"
            Layer._next_id += 1
        else:
            self.name = name
            # 從載入的名稱中解析數字，以避免ID衝突
            try:
                num = int(name.split()[-1])
                if num >= Layer._next_id:
                    Layer._next_id = num + 1
            except (ValueError, IndexError):
                pass

        self.is_visible = tk.BooleanVar(value=True)

        # 物件
        self.shapes = []
        self.images = []
        self.top_images = set()

        # 模擬參數
        self.sim_params = {
            'fork_chance': 0.015, 'path_interruption_chance': 0.005, 'step_length': 5,
            'arc_threshold_v_pixel': 150.0, 'probe_count': 15, 'probe_angle': 120,
            'field_exponent': 2.5, 'final_jump_distance': 30.0, 'arc_color': ARC_COLOR,
            'arc_max_thickness': 2.0, 'arc_glow_strength': 0.4, 'arc_max_life': 200,
            'glow_falloff_1': 0.7, 'glow_falloff_2': 0.3, 'glow_falloff_3': 0.1, 'glow_falloff_4': 0.0,
        }

        # 動畫與結果
        self.last_simulation_data = None
        self.speed_graph_points = [] # 速率控制曲線的點

        # 顯示設定 (這些未來可能會變成全域設定)
        self.show_conductors = tk.BooleanVar(value=True)
        self.show_images = tk.BooleanVar(value=True)
        self.background_color_str = tk.StringVar(value=BACKGROUND_COLOR)
        self.is_bg_transparent = tk.BooleanVar(value=False)

        # 匯出框設定 (這些也可能變全域)
        self.export_box = {'x': 50, 'y': 50, 'w': 400, 'h': 300}
        self.show_export_box = tk.BooleanVar(value=False)

    def to_dict(self):
        """將圖層狀態序列化為字典以便儲存。"""
        # 儲存 tk.BooleanVar 和 tk.StringVar 的值，而不是物件本身
        return {
            'name': self.name,
            'is_visible': self.is_visible.get(),
            'shapes': [self._shape_to_dict(s) for s in self.shapes],
            'images': [self._image_to_dict(i) for i in self.images],
            'sim_params': self.sim_params,
            'last_simulation_data': self.last_simulation_data,
            'speed_graph_points': self.speed_graph_points,
            'show_conductors': self.show_conductors.get(),
            'show_images': self.show_images.get(),
            'background_color': self.background_color_str.get(),
            'is_bg_transparent': self.is_bg_transparent.get(),
            'export_box': self.export_box,
            'show_export_box': self.show_export_box.get()
        }

    def _shape_to_dict(self, shape):
        """將 Shape 物件序列化。"""
        shape_dict = {
            'shape_type': shape.shape_type,
            'voltage': shape.voltage,
        }
        if shape.shape_type == "Needle":
            shape_dict.update({'x': shape.x, 'y': shape.y, 'radius': shape.radius})
        elif shape.shape_type == "Rod":
            shape_dict.update({'x1': shape.x1, 'y1': shape.y1, 'x2': shape.x2, 'y2': shape.y2, 'thickness': shape.thickness})
        elif shape.shape_type in ["Plate", "ArbitraryShape", "Arbitrary"]: # Arbitrary for backward compatibility
             shape_dict['points'] = shape.points
        return shape_dict

    def _image_to_dict(self, img_obj):
        """將 DecorativeImage 物件序列化。"""
        # 圖片本身會被單獨儲存，這裡只儲存其屬性
        img_filename = f"images/image_{id(img_obj)}.png" # 使用唯一ID命名
        return {
            'path': img_filename,
            'x': img_obj.x, 'y': img_obj.y,
            'scale': img_obj.scale, 'angle': img_obj.angle,
            'is_top': img_obj in self.top_images
        }

    @classmethod
    def from_dict(cls, data, app_instance, image_map):
        """從字典和圖片對應表中重建圖層。"""
        layer = cls(name=data['name'])
        layer.is_visible.set(data.get('is_visible', True))

        # Shapes
        for shape_dict in data.get('shapes', []):
            shape_type = shape_dict.get('shape_type')
            voltage = shape_dict.get('voltage', 0)
            shape = None
            if shape_type == "Needle":
                shape = Needle(app_instance, shape_dict['x'], shape_dict['y'], voltage, shape_dict['radius'])
            elif shape_type == "Rod":
                shape = Rod(app_instance, shape_dict['x1'], shape_dict['y1'], shape_dict['x2'], shape_dict['y2'], voltage, shape_dict['thickness'])
            elif shape_type == "Plate":
                # Plate 的 x,y 是中心點，需要從 points 推算或在儲存時加入
                shape = Plate(app_instance, 0, 0, voltage)
                shape.points = shape_dict['points']
            elif shape_type in ["ArbitraryShape", "Arbitrary"]:
                shape = ArbitraryShape(app_instance, shape_dict['points'], voltage)
            if shape:
                layer.shapes.append(shape)

        # Images
        for img_dict in data.get('images', []):
            pil_image = image_map.get(img_dict['path'])
            if pil_image:
                img_obj = DecorativeImage(app_instance.canvas, img_dict['x'], img_dict['y'], pil_image, app_instance)
                img_obj.scale = img_dict.get('scale', 1.0)
                img_obj.angle = img_dict.get('angle', 0.0)
                layer.images.append(img_obj)
                if img_dict.get('is_top', False):
                    layer.top_images.add(img_obj)

        # Parameters and data
        layer.sim_params.update(data.get('sim_params', {}))
        layer.last_simulation_data = data.get('last_simulation_data')
        layer.speed_graph_points = data.get('speed_graph_points', [])

        # Display settings
        layer.show_conductors.set(data.get('show_conductors', True))
        layer.show_images.set(data.get('show_images', True))
        layer.background_color_str.set(data.get('background_color', BACKGROUND_COLOR))
        layer.is_bg_transparent.set(data.get('is_bg_transparent', False))

        # Export settings
        layer.export_box = data.get('export_box', {'x': 50, 'y': 50, 'w': 400, 'h': 300})
        layer.show_export_box.set(data.get('show_export_box', False))

        return layer

# --- 主應用程式 GUI (V12.0 - 圖層系統) ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("進階放電模擬系統 V12.0 - 圖層系統")
        self.geometry("1200x800")

        # --- 圖層系統核心 ---
        self.layers = [Layer()]
        self.active_layer_index = 0

        # --- UI / 互動狀態 (非圖層資料) ---
        self.selected_item = None
        self.drag_data = {}
        self.add_shape_mode = None
        self.is_creating_rod = False
        self.is_creating_arbitrary_shape = False
        self.current_polygon_points = []
        self.temp_drawing_artifacts = []
        self.rubber_band_line_id, self.closing_line_id = None, None
        
        # --- 動畫/渲染狀態 (非圖層資料) ---
        self.animation_job = None
        self.animation_frame_index = 0
        self.animation_frame_map = [] # 播放時的幀對應表

        # --- 全域設定 ---
        self.keep_image_frames = tk.BooleanVar(value=False) # 影片匯出後保留圖片

        # --- UI控制元件的參照 ---
        # 為了讓UI控制元件可以被 update_ui_from_active_layer 方法更新，
        # 我們需要將它們儲存為 self 的屬性。
        self.ui_controls = {}
        self.param_vars = {}
        self.export_box_vars = {}

        self.create_widgets()
        self.update_ui_from_active_layer()

    def get_active_layer(self):
        """取得當前作用中圖層的實例。"""
        if not self.layers or self.active_layer_index >= len(self.layers):
            self.layers = [Layer()]
            self.active_layer_index = 0
        return self.layers[self.active_layer_index]

    # --- 圖層管理核心方法 ---
    def _populate_layer_list(self):
        """清除並根據 self.layers 重新填充圖層列表UI。"""
        for widget in self.layer_list_frame.winfo_children():
            widget.destroy()

        for i, layer in enumerate(self.layers):
            layer_entry_frame = tk.Frame(self.layer_list_frame, bg=CONTROL_PANEL_BG)
            if i == self.active_layer_index:
                layer_entry_frame.config(bg="#cce5ff") # Highlight color for active layer

            layer_entry_frame.pack(fill=tk.X, pady=1)

            # 可見性核取方塊
            vis_check = tk.Checkbutton(layer_entry_frame, variable=layer.is_visible, bg=layer_entry_frame.cget('bg'), command=self.redraw_canvas)
            vis_check.pack(side=tk.LEFT)

            # 圖層名稱標籤
            label = tk.Label(layer_entry_frame, text=layer.name, anchor="w", bg=layer_entry_frame.cget('bg'))
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # 綁定點擊事件以選擇圖層
            # 使用 lambda 捕獲迴圈變數 i
            select_func = lambda event, index=i: self.select_layer(index)
            layer_entry_frame.bind("<Button-1>", select_func)
            vis_check.bind("<Button-1>", select_func)
            label.bind("<Button-1>", select_func)

    def select_layer(self, index):
        """選擇一個圖層作為作用中圖層。"""
        if self.active_layer_index == index:
            return
        self.active_layer_index = index
        self._populate_layer_list() # 重繪列表以更新高亮
        self.update_ui_from_active_layer()

    def add_layer(self):
        """新增一個圖層。"""
        new_layer = Layer()
        self.layers.append(new_layer)
        self.select_layer(len(self.layers) - 1)

    def delete_layer(self):
        """刪除當前選擇的圖層。"""
        if len(self.layers) <= 1:
            messagebox.showwarning("操作無效", "必須至少保留一個圖層。")
            return

        if messagebox.askyesno("確認刪除", f"確定要刪除圖層 '{self.get_active_layer().name}' 嗎？此操作無法復原。"):
            self.layers.pop(self.active_layer_index)
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
            self._populate_layer_list()
            self.update_ui_from_active_layer()

    def rename_layer(self):
        """重新命名作用中圖層。"""
        active_layer = self.get_active_layer()
        new_name = simpledialog.askstring("重新命名", "輸入新的圖層名稱:", initialvalue=active_layer.name)
        if new_name:
            active_layer.name = new_name
            self._populate_layer_list()

    def move_layer(self, direction):
        """上移或下移作用中圖層。"""
        if not (0 <= self.active_layer_index < len(self.layers)): return

        new_index = self.active_layer_index + direction
        if not (0 <= new_index < len(self.layers)): return

        self.layers.insert(new_index, self.layers.pop(self.active_layer_index))
        self.select_layer(new_index)
        # Redraw is handled by select_layer

    def move_layer_up(self):
        self.move_layer(-1)

    def move_layer_down(self):
        self.move_layer(1)

    def update_ui_from_active_layer(self):
        """根據當前作用中圖層的狀態，更新所有相關的UI控制元件。"""
        active_layer = self.get_active_layer()

        # 更新顯示設定的 Checkbutton
        self.ui_controls['show_conductors_chk'].config(variable=active_layer.show_conductors)
        self.ui_controls['show_images_chk'].config(variable=active_layer.show_images)
        self.ui_controls['is_bg_transparent_chk'].config(variable=active_layer.is_bg_transparent)

        # 更新背景顏色按鈕和預覽
        self.ui_controls['bg_color_button'].config(command=lambda: self._choose_main_bg_color())
        self.ui_controls['bg_preview'].config(bg=active_layer.background_color_str.get())

        # 更新匯出框 Checkbutton 和 Entries
        self.ui_controls['show_export_box_chk'].config(variable=active_layer.show_export_box)
        for key, var in self.export_box_vars.items():
            var.set(str(int(active_layer.export_box[key])))

        # 更新模擬參數的滑塊
        for key, value in active_layer.sim_params.items():
            if key in self.param_vars:
                self.param_vars[key].set(value)

        # 更新電弧顏色預覽
        self.ui_controls['arc_color_preview'].config(bg=active_layer.sim_params['arc_color'])

        # 更新速率控制圖
        total_frames = len(active_layer.last_simulation_data) if active_layer.last_simulation_data else 0
        self.speed_control_graph.reset(total_frames)
        self.speed_control_graph.set_points(active_layer.speed_graph_points)

        # 觸發一次透明背景按鈕狀態的更新
        self._on_toggle_transparent_bg()

        # 最後重繪畫布
        self.redraw_canvas()

    def create_widgets(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        control_container = tk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2)
        control_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        scroll_canvas = tk.Canvas(control_container, bg=CONTROL_PANEL_BG, highlightthickness=0, width=250)
        scrollbar = ttk.Scrollbar(control_container, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollable_frame = tk.Frame(scroll_canvas, bg=CONTROL_PANEL_BG)
        scrollable_frame_window = scroll_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def configure_scroll_region(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            scroll_canvas.itemconfig(scrollable_frame_window, width=scroll_canvas.winfo_width())

        def on_mouse_wheel(event):
            if event.num == 5 or event.delta < 0:
                scroll_canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                scroll_canvas.yview_scroll(-1, "units")

        scrollable_frame.bind("<Configure>", configure_scroll_region)
        self.bind_all("<MouseWheel>", on_mouse_wheel)
        self.bind_all("<Button-4>", on_mouse_wheel)
        self.bind_all("<Button-5>", on_mouse_wheel)

        self.canvas = tk.Canvas(main_frame, bg=BACKGROUND_COLOR, highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- 【新增】圖層管理UI ---
        layer_frame = tk.LabelFrame(scrollable_frame, text="圖層管理", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        layer_frame.pack(fill=tk.X, padx=10, pady=10)

        self.layer_list_frame = tk.Frame(layer_frame, bg=CONTROL_PANEL_BG)
        self.layer_list_frame.pack(fill=tk.X, pady=5)

        layer_buttons_frame = tk.Frame(layer_frame, bg=CONTROL_PANEL_BG)
        layer_buttons_frame.pack(fill=tk.X, pady=5)

        button_config = {'expand': True, 'fill': tk.X, 'padx': 2}
        tk.Button(layer_buttons_frame, text="新增", command=self.add_layer).pack(side=tk.LEFT, **button_config)
        tk.Button(layer_buttons_frame, text="刪除", command=self.delete_layer).pack(side=tk.LEFT, **button_config)
        tk.Button(layer_buttons_frame, text="命名", command=self.rename_layer).pack(side=tk.LEFT, **button_config)
        tk.Button(layer_buttons_frame, text="上移", command=self.move_layer_up).pack(side=tk.LEFT, **button_config)
        tk.Button(layer_buttons_frame, text="下移", command=self.move_layer_down).pack(side=tk.LEFT, **button_config)

        self._populate_layer_list() # 初始填充

        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)

        add_frame = tk.LabelFrame(scrollable_frame, text="新增物體 (作用中圖層)", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(add_frame, text="針頭", command=lambda: self.set_add_mode("Needle")).pack(fill=tk.X)
        tk.Button(add_frame, text="電棒", command=lambda: self.set_add_mode("Rod")).pack(fill=tk.X)
        tk.Button(add_frame, text="平板", command=lambda: self.set_add_mode("Plate")).pack(fill=tk.X)
        tk.Button(add_frame, text="任意形狀", command=lambda: self.set_add_mode("Arbitrary")).pack(fill=tk.X)
        ttk.Separator(add_frame, orient='horizontal').pack(fill='x', pady=5)
        tk.Button(add_frame, text="新增圖片", command=self.add_image).pack(fill=tk.X)

        display_frame = tk.LabelFrame(scrollable_frame, text="圖層顯示設定", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        display_frame.pack(fill=tk.X, padx=10, pady=10)

        self.ui_controls['show_conductors_chk'] = tk.Checkbutton(display_frame, text="顯示導體", command=self.redraw_canvas, bg=CONTROL_PANEL_BG)
        self.ui_controls['show_conductors_chk'].pack(anchor="w")
        self.ui_controls['show_images_chk'] = tk.Checkbutton(display_frame, text="顯示圖片", command=self.redraw_canvas, bg=CONTROL_PANEL_BG)
        self.ui_controls['show_images_chk'].pack(anchor="w")
        self.ui_controls['is_bg_transparent_chk'] = tk.Checkbutton(display_frame, text="匯出為透明背景", command=self._on_toggle_transparent_bg, bg=CONTROL_PANEL_BG)
        self.ui_controls['is_bg_transparent_chk'].pack(anchor="w")

        bg_frame = tk.Frame(display_frame, bg=CONTROL_PANEL_BG)
        bg_frame.pack(fill='x', pady=(5,0))
        self.ui_controls['bg_color_button'] = tk.Button(bg_frame, text="背景顏色")
        self.ui_controls['bg_color_button'].pack(side=tk.LEFT)
        self.ui_controls['bg_preview'] = tk.Frame(bg_frame, width=24, height=24, relief=tk.SUNKEN, borderwidth=1)
        self.ui_controls['bg_preview'].pack(side=tk.LEFT, padx=5)

        export_frame = tk.LabelFrame(scrollable_frame, text="圖層匯出區域", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        export_frame.pack(fill=tk.X, padx=10, pady=10)

        self.ui_controls['show_export_box_chk'] = tk.Checkbutton(export_frame, text="顯示/啟用匯出框", command=self.redraw_canvas, bg=CONTROL_PANEL_BG)
        self.ui_controls['show_export_box_chk'].pack(anchor="w")

        entry_frame = tk.Frame(export_frame, bg=CONTROL_PANEL_BG)
        entry_frame.pack(fill=tk.X, pady=5)
        labels = ["X:", "Y:", "寬:", "高:"]
        keys = ['x', 'y', 'w', 'h']
        for i, (label, key) in enumerate(zip(labels, keys)):
            tk.Label(entry_frame, text=label, bg=CONTROL_PANEL_BG).grid(row=i//2, column=(i%2)*2, sticky="w", padx=(0, 2))
            self.export_box_vars[key] = tk.StringVar()
            entry = tk.Entry(entry_frame, textvariable=self.export_box_vars[key], width=6)
            entry.grid(row=i//2, column=(i%2)*2 + 1, sticky="ew", pady=2)
        entry_frame.columnconfigure(1, weight=1)
        entry_frame.columnconfigure(3, weight=1)
        tk.Button(export_frame, text="從輸入更新匯出框", command=self._update_export_box_from_entries).pack(fill=tk.X, pady=(5, 0))
        
        param_frame = tk.LabelFrame(scrollable_frame, text="圖層模擬參數", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        param_frame.pack(fill=tk.X, padx=10, pady=10)

        def add_bar(label, key, frm, from_, to_, resolution, fmt, row):
            tk.Label(frm, text=label, bg=CONTROL_PANEL_BG).grid(row=row, column=0, sticky="w")
            var = tk.DoubleVar() # 變數本身不設定初始值
            self.param_vars[key] = var

            def on_change(val):
                active_layer = self.get_active_layer()
                active_layer.sim_params[key] = float(val)
                if resolution >= 1:
                    val_label.config(text=f"{int(float(val))}")
                else:
                    val_label.config(text=f"{float(val):.3f}".rstrip('0').rstrip('.'))
                if 'arc' in key or 'glow' in key:
                    if hasattr(self, '_preview_job'): self.after_cancel(self._preview_job)
                    self._preview_job = self.after(50, self.preview_simulation)
            
            scale = tk.Scale(frm, variable=var, from_=from_, to=to_, resolution=resolution, orient=tk.HORIZONTAL, length=100, showvalue=0, bg=CONTROL_PANEL_BG, command=on_change)
            scale.grid(row=row, column=1)
            val_label = tk.Label(frm, text="", bg=CONTROL_PANEL_BG, width=6, anchor='w') # 初始為空
            val_label.grid(row=row, column=2)
            # 將UI元件儲存起來以便之後更新
            self.ui_controls[f'scale_{key}'] = scale
            self.ui_controls[f'label_{key}'] = val_label

        add_bar("觸發閾(V/px)", 'arc_threshold_v_pixel', param_frame, 1, 500, 1, "{:.0f}", 0)
        add_bar("分岔機率", 'fork_chance', param_frame, 0, 0.05, 0.001, "{:.3f}", 1)
        add_bar("消散機率", 'path_interruption_chance', param_frame, 0, 0.05, 0.001, "{:.3f}", 2)
        add_bar("步長", 'step_length', param_frame, 1, 20, 1, "{:.0f}", 3)
        add_bar("探測點數量", 'probe_count', param_frame, 3, 40, 1, "{:.0f}", 4)
        add_bar("探測角度(°)", 'probe_angle', param_frame, 30, 180, 5, "{:.0f}", 5)
        add_bar("電場指數", 'field_exponent', param_frame, 1.0, 5.0, 0.1, "{:.1f}", 6)
        add_bar("最終跳躍(px)", 'final_jump_distance', param_frame, 0, 100, 1, "{:.0f}", 7)

        appearance_frame = tk.LabelFrame(scrollable_frame, text="圖層電弧外觀 (可即時預覽)", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        appearance_frame.pack(fill=tk.X, padx=10, pady=10)
        appearance_frame.columnconfigure(1, weight=1)
        tk.Button(appearance_frame, text="電弧顏色", command=self._choose_arc_color).grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        self.ui_controls['arc_color_preview'] = tk.Frame(appearance_frame, width=24, height=24, relief=tk.SUNKEN, borderwidth=1)
        self.ui_controls['arc_color_preview'].grid(row=0, column=2, padx=(5,0), pady=2)
        add_bar("電弧粗細", 'arc_max_thickness', appearance_frame, 1, 20, 0.5, "{:.1f}", 1)
        add_bar("光暈強度", 'arc_glow_strength', appearance_frame, 0.0, 5.0, 0.1, "{:.1f}", 2)
        ttk.Separator(appearance_frame).grid(row=3, columnspan=3, sticky='ew', pady=5)
        add_bar("輪廓 (25%)", 'glow_falloff_1', appearance_frame, 0.0, 1.0, 0.05, "{:.2f}", 4)
        add_bar("輪廓 (50%)", 'glow_falloff_2', appearance_frame, 0.0, 1.0, 0.05, "{:.2f}", 5)
        add_bar("輪廓 (75%)", 'glow_falloff_3', appearance_frame, 0.0, 1.0, 0.05, "{:.2f}", 6)
        add_bar("輪廓 (100%)", 'glow_falloff_4', appearance_frame, 0.0, 1.0, 0.05, "{:.2f}", 7)

        sim_frame = tk.LabelFrame(scrollable_frame, text="模擬控制", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        sim_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(sim_frame, text="執行新模擬", command=self.start_new_simulation).pack(fill=tk.X, pady=3)
        tk.Button(sim_frame, text="預覽上次模擬", command=self.preview_simulation).pack(fill=tk.X, pady=3)
        tk.Button(sim_frame, text="匯出動畫", command=self.dispatch_export_animation).pack(fill=tk.X, pady=3)
        tk.Checkbutton(sim_frame, text="保留圖片檔案", variable=self.keep_image_frames, bg=CONTROL_PANEL_BG).pack(anchor="w", padx=5)
        ttk.Separator(sim_frame, orient='horizontal').pack(fill='x', pady=5)
        io_frame = tk.Frame(sim_frame, bg=CONTROL_PANEL_BG)
        io_frame.pack(fill=tk.X, pady=2)
        tk.Button(io_frame, text="儲存場景", command=self.save_scene).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        tk.Button(io_frame, text="載入場景", command=self.load_scene).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2, 0))
        ttk.Separator(sim_frame, orient='horizontal').pack(fill='x', pady=5)
        tk.Button(sim_frame, text="清除圖層電弧", command=self.clear_simulation).pack(fill=tk.X, pady=3)
        tk.Button(sim_frame, text="清除圖層內容", command=self.clear_active_layer).pack(fill=tk.X, pady=3)

        speed_control_frame = ttk.LabelFrame(scrollable_frame, text="圖層速率曲線")
        speed_control_frame.pack(fill=tk.X, padx=10, pady=10)
        self.speed_control_graph = SpeedControlGraph(speed_control_frame, on_change_callback=self.on_speed_graph_change, height=80)
        self.speed_control_graph.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(scrollable_frame, text="刪除選取", command=self.delete_selected).pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press); self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release); self.canvas.bind("<Double-1>", self.on_canvas_double_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion); self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.bind("<Escape>", self.cancel_creation_mode)

    def on_speed_graph_change(self):
        """速率圖變更時的回呼，將點儲存到作用中圖層。"""
        active_layer = self.get_active_layer()
        active_layer.speed_graph_points = self.speed_control_graph.get_points()
        self.preview_simulation()

    # --- 【新】方法: 更新畫布顯示 (Pillow渲染引擎) ---
    def _render_scene_to_pillow(self, arc_data_for_frame=None, scale=1.0, for_export=False, export_layers=None):
        """
        Renders the scene to a Pillow image.
        - In normal mode, it renders all visible layers. Arc preview is only for the active layer.
        - In export mode, it renders the layers provided in `export_layers`.
        """
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 1 or h < 1: return None
        w_scaled, h_scaled = int(w * scale), int(h * scale)

        layers_to_render = export_layers if for_export else [l for l in self.layers if l.is_visible.get()]

        first_visible_layer = next((layer for layer in layers_to_render), None)
        if not first_visible_layer:
            return Image.new('RGBA', (w_scaled, h_scaled), BACKGROUND_COLOR)

        if for_export and first_visible_layer.is_bg_transparent.get():
            bg_color = (0, 0, 0, 0)
        else:
            bg_color = first_visible_layer.background_color_str.get()

        try: final_image = Image.new('RGBA', (w_scaled, h_scaled), bg_color)
        except ValueError: final_image = Image.new('RGBA', (w_scaled, h_scaled), BACKGROUND_COLOR)

        for layer in layers_to_render:
            is_base_layer = (layer == first_visible_layer)

            # 決定在哪個畫布上繪製
            if is_base_layer and not (for_export and layer.is_bg_transparent.get()):
                layer_canvas = final_image
            else:
                layer_canvas = Image.new('RGBA', (w_scaled, h_scaled), (0,0,0,0))

            layer_draw = ImageDraw.Draw(layer_canvas)

            # 繪製靜態物件
            bottom_images = [img for img in layer.images if img not in layer.top_images]
            if layer.show_images.get():
                for image in bottom_images: image.draw_to_pillow(layer_canvas, scale)
            if layer.show_conductors.get():
                for shape in layer.shapes: shape.draw_to_pillow(layer_draw, scale)
            if layer.show_images.get():
                for image in layer.top_images: image.draw_to_pillow(layer_canvas, scale)

            # 繪製電弧 (預覽模式下只繪製作用中圖層的電弧)
            active_layer = self.get_active_layer()
            current_arc_data = None
            if for_export:
                current_arc_data = arc_data_for_frame.get(layer) if isinstance(arc_data_for_frame, dict) else None
            elif layer == active_layer:
                current_arc_data = arc_data_for_frame

            if current_arc_data:
                glow_layer = Image.new('RGBA', (w_scaled, h_scaled), (0, 0, 0, 0))
                glow_draw = ImageDraw.Draw(glow_layer)
                # 電弧外觀總是取自其所屬圖層的參數
                appearance_params = self._get_layer_appearance_params(layer)
                arc_renderer = ArcRenderer(appearance_params)
                arc_renderer.render_frame_data(current_arc_data, glow_draw, scale)
                layer_canvas = Image.alpha_composite(layer_canvas, glow_layer)

            if not is_base_layer or (for_export and layer.is_bg_transparent.get()):
                final_image = Image.alpha_composite(final_image, layer_canvas)

        # --- 在所有圖層之上繪製UI元素 (僅限非匯出模式) ---
        if not for_export:
            final_draw = ImageDraw.Draw(final_image)
            active_layer = self.get_active_layer()

            if active_layer.show_export_box.get() and scale == 1.0:
                box = active_layer.export_box
                x1, y1, x2, y2 = box['x'], box['y'], box['x'] + box['w'], box['y'] + box['h']
                overlay = Image.new('RGBA', final_image.size, (0,0,0,0))
                draw_overlay = ImageDraw.Draw(overlay)
                draw_overlay.rectangle([x1, y1, x2, y2], fill=(255, 255, 0, 30), outline=(255, 255, 0, 200), width=1)
                r = HANDLE_RADIUS
                handle_x, handle_y = x1 + box['w'], y1 + box['h']
                draw_overlay.rectangle([handle_x - r, handle_y - r, handle_x + r, handle_y + r], fill=HANDLE_COLOR, outline='white')
                final_image = Image.alpha_composite(final_image, overlay)
                final_draw = ImageDraw.Draw(final_image)

            if self.selected_item:
                is_conductor = self.selected_item in active_layer.shapes and active_layer.show_conductors.get()
                is_image = self.selected_item in active_layer.images and active_layer.show_images.get()
                if is_conductor or is_image:
                     self.selected_item.draw_selection_to_pillow(final_draw, scale)

        return final_image

    def redraw_canvas(self, arc_data_for_frame=None):
        """Redraws the entire canvas using the Pillow off-screen rendering engine."""
        scene_image = self._render_scene_to_pillow(arc_data_for_frame, scale=1.0)
        if scene_image is None: return

        self.tk_render_image = ImageTk.PhotoImage(scene_image)
        if not hasattr(self, 'canvas_image_id') or not self.canvas.winfo_exists() or not self.canvas.find_withtag(self.canvas_image_id):
            self.canvas.delete("all")
            self.canvas_image_id = self.canvas.create_image(0, 0, anchor='nw', image=self.tk_render_image)
        else:
            self.canvas.itemconfig(self.canvas_image_id, image=self.tk_render_image)

    def _choose_main_bg_color(self):
        active_layer = self.get_active_layer()
        color_code = colorchooser.askcolor(title="選擇背景顏色", initialcolor=active_layer.background_color_str.get())
        if color_code and color_code[1]:
            active_layer.background_color_str.set(color_code[1])
            self.ui_controls['bg_preview'].config(bg=color_code[1])
            self.canvas.config(bg=color_code[1])
            if active_layer.last_simulation_data: self.preview_simulation()

    def _on_toggle_transparent_bg(self):
        active_layer = self.get_active_layer()
        is_transparent = active_layer.is_bg_transparent.get()
        state = tk.DISABLED if is_transparent else tk.NORMAL
        self.ui_controls['bg_color_button'].config(state=state)
        bg = "#808080" if is_transparent else active_layer.background_color_str.get()
        self.ui_controls['bg_preview'].config(bg=bg)

    def _choose_arc_color(self):
        active_layer = self.get_active_layer()
        color_code = colorchooser.askcolor(title="選擇電弧顏色", initialcolor=active_layer.sim_params['arc_color'])
        if color_code and color_code[1]:
            active_layer.sim_params['arc_color'] = color_code[1]
            self.ui_controls['arc_color_preview'].config(bg=color_code[1])
            self.preview_simulation()

    def _update_export_box_from_entries(self):
        active_layer = self.get_active_layer()
        try:
            x = int(self.export_box_vars['x'].get())
            y = int(self.export_box_vars['y'].get())
            w = int(self.export_box_vars['w'].get())
            h = int(self.export_box_vars['h'].get())
            if w <= 0 or h <= 0:
                messagebox.showwarning("輸入無效", "寬度和高度必須是正數。"); return
            active_layer.export_box = {'x': x, 'y': y, 'w': w, 'h': h}
            self.redraw_canvas()
        except ValueError:
            messagebox.showerror("輸入錯誤", "請確保所有匯出區域的欄位都是有效的整數。")

    def _update_export_box_entries(self):
        active_layer = self.get_active_layer()
        for key, var in self.export_box_vars.items():
            var.set(str(int(active_layer.export_box[key])))

    def _get_export_box_handle_at(self, x, y):
        active_layer = self.get_active_layer()
        if not active_layer.show_export_box.get(): return None
        box = active_layer.export_box
        handle_size = HANDLE_RADIUS * 2
        br_x, br_y = box['x'] + box['w'], box['y'] + box['h']
        if (br_x - handle_size/2 <= x <= br_x + handle_size/2) and \
           (br_y - handle_size/2 <= y <= br_y + handle_size/2):
            return 'br'
        return None

    def _is_in_export_box(self, x, y):
        active_layer = self.get_active_layer()
        if not active_layer.show_export_box.get() or self._get_export_box_handle_at(x,y):
            return False
        box = active_layer.export_box
        return (box['x'] < x < box['x'] + box['w']) and \
               (box['y'] < y < box['y'] + box['h'])

    def on_canvas_right_click(self, event):
        active_layer = self.get_active_layer()
        if self.is_creating_arbitrary_shape: self.cancel_creation_mode(event); return
        item_found = next((item for item in reversed(active_layer.images) if item.contains(event.x, event.y)), None)
        if item_found:
            self.select_item(item_found)
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="移到最上層", command=lambda: item_found.set_layer('front'))
            menu.add_command(label="移到最下層", command=lambda: item_found.set_layer('back'))
            menu.post(event.x_root, event.y_root)
        else: self.cancel_creation_mode(event)

    def cancel_creation_mode(self, event=None):
        self.canvas.config(cursor=""); self.add_shape_mode = None; self.is_creating_rod = False
        self.drag_data.clear(); self.select_item(None)
        if self.is_creating_arbitrary_shape:
            self.is_creating_arbitrary_shape = False
            for item in self.temp_drawing_artifacts: self.canvas.delete(item)
            if self.rubber_band_line_id: self.canvas.delete(self.rubber_band_line_id)
            if self.closing_line_id: self.canvas.delete(self.closing_line_id)
            self.temp_drawing_artifacts.clear(); self.current_polygon_points.clear()
            self.rubber_band_line_id, self.closing_line_id = None, None
        return "break"

    def set_add_mode(self, shape_type):
        self.cancel_creation_mode(); self.add_shape_mode = shape_type
        self.is_creating_rod = (shape_type == "Rod")
        if shape_type == "Arbitrary":
            messagebox.showinfo("繪製提示", "請在畫布上點擊以放置頂點。\n點擊第一個頂點或按兩下來完成形狀。\n按右鍵或 Esc 鍵取消。")
            self.is_creating_arbitrary_shape = True
        self.select_item(None); self.canvas.config(cursor="crosshair")

    def add_image(self):
        self.cancel_creation_mode()
        filepath = filedialog.askopenfilename(title="選擇圖片", filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")])
        if not filepath: return
        try:
            pil_image = Image.open(filepath)
            x, y = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
            image_obj = DecorativeImage(self.canvas, x, y, pil_image, self)
            self.get_active_layer().images.append(image_obj)
            self.select_item(image_obj)
            self.redraw_canvas()
        except Exception as e: messagebox.showerror("圖片載入失敗", f"無法載入圖片檔案：\n{e}")

    def on_canvas_press(self, event):
        active_layer = self.get_active_layer()
        if active_layer.show_export_box.get():
            handle_type = self._get_export_box_handle_at(event.x, event.y)
            if handle_type:
                self.drag_data = {'type': 'export_box_resize', 'handle': handle_type, 'start_x': event.x, 'start_y': event.y}
                return
            if self._is_in_export_box(event.x, event.y):
                self.drag_data = {'type': 'export_box_move', 'start_x': event.x, 'start_y': event.y, 'orig_box': active_layer.export_box.copy()}
                return

        if self.is_creating_arbitrary_shape:
            x, y = event.x, event.y
            if self.current_polygon_points and math.hypot(x - self.current_polygon_points[0][0], y - self.current_polygon_points[0][1]) < HANDLE_RADIUS * 2:
                self.finalize_arbitrary_shape(); return
            if self.current_polygon_points:
                px, py = self.current_polygon_points[-1]
                self.temp_drawing_artifacts.append(self.canvas.create_line(px, py, x, y, fill=SELECTED_OUTLINE_COLOR, width=2))
            self.current_polygon_points.append((x, y))
            self.temp_drawing_artifacts.append(self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=HANDLE_COLOR))
            return
        if self.add_shape_mode:
            if self.is_creating_rod: self.drag_data = {'x1': event.x, 'y1': event.y, 'line_id': None}
            return
        
        all_items = []
        if active_layer.show_images.get(): all_items.extend(active_layer.images)
        if active_layer.show_conductors.get(): all_items.extend(active_layer.shapes)

        if self.selected_item:
            handle_index = self.selected_item.get_handle_at(event.x, event.y)
            if handle_index is not None:
                self.drag_data = {'item': self.selected_item, 'type': 'handle', 'index': handle_index}; return

        item_found = next((item for item in reversed(all_items) if item.contains(event.x, event.y)), None)
        self.select_item(item_found)
        if item_found: self.drag_data = {'item': item_found, 'type': 'body', 'x': event.x, 'y': event.y}

    def on_canvas_motion(self, event):
        if not self.is_creating_arbitrary_shape or not self.current_polygon_points: return
        if self.rubber_band_line_id: self.canvas.delete(self.rubber_band_line_id)
        px, py = self.current_polygon_points[-1]
        self.rubber_band_line_id = self.canvas.create_line(px, py, event.x, event.y, fill=SELECTED_OUTLINE_COLOR, dash=(4,4))
        if self.closing_line_id: self.canvas.delete(self.closing_line_id)
        if len(self.current_polygon_points) > 1:
            sx, sy = self.current_polygon_points[0]
            self.closing_line_id = self.canvas.create_line(event.x, event.y, sx, sy, fill=SELECTED_OUTLINE_COLOR, dash=(4,4))

    def on_canvas_drag(self, event):
        drag_type = self.drag_data.get('type')
        active_layer = self.get_active_layer()

        if drag_type == 'export_box_move':
            dx, dy = event.x - self.drag_data['start_x'], event.y - self.drag_data['start_y']
            orig_box = self.drag_data['orig_box']
            active_layer.export_box['x'] = orig_box['x'] + dx
            active_layer.export_box['y'] = orig_box['y'] + dy
            self._update_export_box_entries()
            self.redraw_canvas()
            return
        elif drag_type == 'export_box_resize':
            dx, dy = event.x - self.drag_data['start_x'], event.y - self.drag_data['start_y']
            active_layer.export_box['w'] = max(20, active_layer.export_box['w'] + dx)
            active_layer.export_box['h'] = max(20, active_layer.export_box['h'] + dy)
            self.drag_data['start_x'], self.drag_data['start_y'] = event.x, event.y
            self._update_export_box_entries()
            self.redraw_canvas()
            return

        if self.is_creating_rod and 'x1' in self.drag_data:
            if self.drag_data.get('line_id'): self.canvas.delete(self.drag_data['line_id'])
            self.drag_data['line_id'] = self.canvas.create_line(self.drag_data['x1'], self.drag_data['y1'], event.x, event.y, fill=SELECTED_OUTLINE_COLOR, width=3, dash=(4,4))
            return

        if 'item' in self.drag_data:
            item = self.drag_data['item']
            if self.drag_data['type'] == 'body':
                dx, dy = event.x - self.drag_data['x'], event.y - self.drag_data['y']
                item.move(dx, dy)
                self.drag_data['x'], self.drag_data['y'] = event.x, event.y
            elif self.drag_data['type'] == 'handle': 
                item.move_handle(self.drag_data['index'], event.x, event.y)
                if active_layer.last_simulation_data:
                    if hasattr(self, '_preview_job'): self.after_cancel(self._preview_job)
                    self._preview_job = self.after(50, self.preview_simulation)

    def on_canvas_release(self, event):
        if self.drag_data.get('type') in ['export_box_move', 'export_box_resize']:
            self.drag_data.clear(); return

        if self.is_creating_arbitrary_shape: return
        self.canvas.config(cursor="")
        if self.add_shape_mode:
            shape = None
            if self.add_shape_mode == "Needle": shape = Needle(self, event.x, event.y)
            elif self.add_shape_mode == "Plate": shape = Plate(self, event.x, event.y)
            elif self.is_creating_rod:
                if self.drag_data.get('line_id'): self.canvas.delete(self.drag_data['line_id'])
                x1, y1 = self.drag_data['x1'], self.drag_data['y1']
                if math.hypot(event.x - x1, event.y - y1) > 10: shape = Rod(self, x1, y1, event.x, event.y)
            if shape: 
                self.get_active_layer().shapes.append(shape)
                self.select_item(shape)
            self.add_shape_mode, self.is_creating_rod = None, False
        self.drag_data.clear()
        self.redraw_canvas()

    def on_canvas_double_click(self, event):
        active_layer = self.get_active_layer()
        if self.is_creating_arbitrary_shape: self.finalize_arbitrary_shape(); return

        if active_layer.show_conductors.get():
            item_found = next((s for s in reversed(active_layer.shapes) if s.contains(event.x, event.y)), None)
            if item_found and hasattr(item_found, 'voltage'):
                self.select_item(item_found)
                ParameterDialog(self, f"設定 {item_found.shape_type} 參數", item_found)

    def finalize_arbitrary_shape(self):
        if not self.is_creating_arbitrary_shape or len(self.current_polygon_points) < 3:
            messagebox.showwarning("創建錯誤", "一個有效的封閉導體至少需要3個頂點。"); self.cancel_creation_mode(); return
        shape = ArbitraryShape(self, self.current_polygon_points.copy())
        self.get_active_layer().shapes.append(shape)
        self.cancel_creation_mode()
        self.select_item(shape)

    def select_item(self, item):
        self.selected_item = item
        self.redraw_canvas()

    def delete_selected(self):
        if not self.selected_item: return
        active_layer = self.get_active_layer()
        item = self.selected_item
        if item in active_layer.shapes: active_layer.shapes.remove(item)
        elif item in active_layer.images:
            active_layer.images.remove(item)
            if item in active_layer.top_images: active_layer.top_images.remove(item)
        self.select_item(None)

    def _get_current_appearance_params(self):
        return self._get_layer_appearance_params(self.get_active_layer())

    def _get_layer_appearance_params(self, layer):
        """從指定圖層獲取電弧外觀參數。"""
        params = {k: v for k, v in layer.sim_params.items() if 'arc' in k or 'glow' in k}
        params['glow_falloff_points'] = [
            (0.0, 1.0), (0.25, layer.sim_params['glow_falloff_1']),
            (0.5, layer.sim_params['glow_falloff_2']), (0.75, layer.sim_params['glow_falloff_3']),
            (1.0, layer.sim_params['glow_falloff_4'])]
        return params

    def start_new_simulation(self):
        self.clear_simulation()
        active_layer = self.get_active_layer()
        if len(active_layer.shapes) < 2:
            messagebox.showwarning("模擬錯誤", "需要至少兩個物體才能進行模擬。"); return
        
        arc_jobs = []
        threshold = active_layer.sim_params['arc_threshold_v_pixel']
        for shape_a, shape_b in itertools.combinations(active_layer.shapes, 2):
            delta_v = abs(shape_a.voltage - shape_b.voltage)
            center_a, center_b = shape_a.get_center(), shape_b.get_center()
            distance = math.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
            if distance > 1.0 and delta_v / distance > threshold:
                source, target = (shape_a, shape_b) if shape_a.voltage > shape_b.voltage else (shape_b, shape_a)
                arc_jobs.append({'source': source, 'target': target})
        
        if arc_jobs:
            simulator = Simulator(active_layer.shapes, active_layer.sim_params)
            canvas_size = (self.canvas.winfo_width(), self.canvas.winfo_height())
            active_layer.last_simulation_data = simulator.run_simulation(arc_jobs, canvas_size)
            self.update_ui_from_active_layer() # 更新UI，特別是速率圖
            if active_layer.last_simulation_data:
                self.preview_simulation()
        else:
            messagebox.showinfo("模擬資訊", "在目前的佈局和電壓設定下，沒有物體之間的電位梯度超過觸發閾值。")
            active_layer.last_simulation_data = None
            self.update_ui_from_active_layer()

    def preview_simulation(self):
        active_layer = self.get_active_layer()
        if not active_layer.last_simulation_data:
            self.clear_simulation(); return

        if self.animation_job: self.after_cancel(self.animation_job)
        self.animation_job = None

        total_frames = len(active_layer.last_simulation_data)
        self.animation_frame_map = self._build_frame_map(active_layer.speed_graph_points, total_frames)
        if not self.animation_frame_map:
            self.redraw_canvas(); return

        self.animation_frame_index = 0
        self.play_simulation_animation()

    def play_simulation_animation(self):
        if self.animation_job: self.after_cancel(self.animation_job)
        self.animation_job = None
        active_layer = self.get_active_layer()

        if self.animation_frame_index >= len(self.animation_frame_map): return
        original_frame_index = self.animation_frame_map[self.animation_frame_index]

        all_segments_to_render = []
        for i in range(original_frame_index + 1):
            if i < len(active_layer.last_simulation_data):
                all_segments_to_render.extend(active_layer.last_simulation_data[i])

        self.redraw_canvas(all_segments_to_render)
        self.animation_frame_index += 1
        self.animation_job = self.after(15, self.play_simulation_animation)

    def clear_simulation(self):
        if self.animation_job: self.after_cancel(self.animation_job)
        self.animation_job = None
        active_layer = self.get_active_layer()
        active_layer.last_simulation_data = None
        self.redraw_canvas()

    def clear_active_layer(self):
        if self.animation_job: self.after_cancel(self.animation_job)
        self.animation_job = None
        active_layer = self.get_active_layer()
        
        self.select_item(None)
        active_layer.shapes.clear()
        active_layer.images.clear()
        active_layer.top_images.clear()
        active_layer.last_simulation_data = None
        self.update_ui_from_active_layer()

    def _create_progress_window(self, title, max_value):
        progress_win = tk.Toplevel(self)
        progress_win.title(title); progress_win.geometry("300x100")
        progress_win.resizable(False, False); progress_win.transient(self); progress_win.grab_set()
        tk.Label(progress_win, text="處理中，請稍候...").pack(pady=10)
        progress_bar = ttk.Progressbar(progress_win, orient="horizontal", length=280, mode="determinate", maximum=max_value)
        progress_bar.pack(pady=5)
        progress_label = tk.Label(progress_win, text=f"0 / {max_value}")
        progress_label.pack()
        progress_win.update()
        return progress_win, progress_bar, progress_label

    def _create_video_from_frames(self, output_dir, num_frames, video_filename, is_transparent=False):
        final_video_name = os.path.basename(video_filename)
        if is_transparent:
            ffmpeg_command = ['ffmpeg','-y','-framerate','24','-start_number','1','-i','frame_%04d.png','-vf','scale=in_color_matrix=bt709:out_color_matrix=bt709,format=yuva444p10le','-c:v','prores_ks','-profile:v','4444','-pix_fmt','yuva444p10le','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-frames:v',str(num_frames),final_video_name]
        else:
            ffmpeg_command = ['ffmpeg','-y','-r','24','-start_number','1','-i','frame_%04d.png','-pix_fmt','yuv420p','-vf','scale=in_color_matrix=bt709:out_color_matrix=bt709','-frames:v',str(num_frames),'-c:v','libx264','-preset','slower','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1','-movflags','faststart',final_video_name]

        encoding_win = tk.Toplevel(self)
        encoding_win.title("影片編碼中"); encoding_win.geometry("350x100")
        encoding_win.resizable(False, False); encoding_win.transient(self); encoding_win.grab_set()
        tk.Label(encoding_win, text=f"正在使用 FFmpeg 編碼影片...\n這可能需要一些時間，請勿關閉主視窗。").pack(pady=10)
        progress_bar = ttk.Progressbar(encoding_win, orient="horizontal", length=330, mode="indeterminate")
        progress_bar.pack(pady=5); progress_bar.start(10); encoding_win.update()
        try:
            result = subprocess.run(ffmpeg_command, cwd=output_dir, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            encoding_win.destroy()
            messagebox.showinfo("影片建立成功", f"影片 '{final_video_name}' 已成功儲存至:\n{output_dir}")
            if not self.keep_image_frames.get():
                delete_msg_win = tk.Toplevel(self)
                delete_msg_win.title("清理中"); delete_msg_win.geometry("300x80")
                delete_msg_win.transient(self); delete_msg_win.grab_set()
                tk.Label(delete_msg_win, text="正在刪除暫存圖片檔案...").pack(pady=10)
                self.update_idletasks()
                try:
                    for i in range(1, num_frames + 1):
                        filepath = os.path.join(output_dir, f"frame_{i:04d}.png")
                        if os.path.exists(filepath): os.remove(filepath)
                except Exception as e: messagebox.showwarning("刪除失敗", f"刪除圖片時發生錯誤：\n{e}")
                finally: delete_msg_win.destroy()
        except FileNotFoundError:
            if encoding_win.winfo_exists(): encoding_win.destroy()
            messagebox.showerror("FFmpeg 錯誤", "找不到 FFmpeg 執行檔。\n請確認 FFmpeg 已安裝並在系統的 PATH 中。")
        except subprocess.CalledProcessError as e:
            if encoding_win.winfo_exists(): encoding_win.destroy()
            error_win = tk.Toplevel(self)
            error_win.title("FFmpeg 執行錯誤"); error_win.geometry("600x400")
            error_win.transient(self); error_win.grab_set()
            error_message = f"FFmpeg 執行時發生錯誤 (返回碼 {e.returncode})。\n\n指令:\n{' '.join(e.cmd)}\n\nFFmpeg 輸出 (Stderr):\n{e.stderr}"
            text_frame = tk.Frame(error_win); text_frame.pack(expand=True, fill="both", padx=5, pady=5)
            text_widget = tk.Text(text_frame, wrap="word", height=15); text_widget.insert("1.0", error_message); text_widget.config(state="disabled")
            scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview); text_widget.config(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y"); text_widget.pack(side="left", expand=True, fill="both")
            tk.Button(error_win, text="關閉", command=error_win.destroy).pack(pady=10)
        except Exception as e:
            if encoding_win.winfo_exists(): encoding_win.destroy()
            messagebox.showerror("未知錯誤", f"處理影片時發生預期外的錯誤:\n{str(e)}")
        finally:
            if encoding_win.winfo_exists(): encoding_win.destroy()

    def dispatch_export_animation(self):
        """處理整個複合動畫匯出流程。"""
        exportable_layers = [layer for layer in self.layers if layer.is_visible.get() and layer.last_simulation_data]
        if not exportable_layers:
            messagebox.showwarning("無資料", "沒有任何可見圖層包含可匯出的模擬資料以供匯出。")
            return

        # 以第一個可見圖層的設定來決定匯出格式
        first_layer = next((layer for layer in self.layers if layer.is_visible.get()), self.get_active_layer())
        is_transparent = first_layer.is_bg_transparent.get()
        default_ext = ".mov" if is_transparent else ".mp4"
        file_types = [("QuickTime Movie", "*.mov"), ("MP4 Video", "*.mp4")] if is_transparent else [("MP4 Video", "*.mp4"), ("QuickTime Movie", "*.mov")]

        video_filepath = filedialog.asksaveasfilename(title="選擇影片儲存路徑與檔名", defaultextension=default_ext, filetypes=file_types)
        if not video_filepath: return

        try:
            parent_dir = os.path.dirname(video_filepath)
            full_filename = os.path.basename(video_filepath)
            base_filename, _ = os.path.splitext(full_filename)
            output_dir = os.path.join(parent_dir, base_filename)
            os.makedirs(output_dir, exist_ok=True)
            final_video_path = os.path.join(output_dir, full_filename)
            scene_zip_path = os.path.join(output_dir, base_filename + ".zip")
        except Exception as e:
            messagebox.showerror("路徑錯誤", f"處理檔案路徑時發生錯誤:\n{e}"); return

        self.save_scene(filepath=scene_zip_path)
        self._export_composite_animation(exportable_layers, output_dir, final_video_path)

    def _export_composite_animation(self, export_layers, output_dir, video_filepath):
        """產生並儲存複合動畫。"""
        # 1. 計算每個圖層的時間線
        layer_timelines = {}
        max_output_frames = 0
        for layer in export_layers:
            total_original = len(layer.last_simulation_data)
            frame_map = self._build_frame_map(layer.speed_graph_points, total_original)
            layer_timelines[layer] = frame_map
            if len(frame_map) > max_output_frames:
                max_output_frames = len(frame_map)

        if max_output_frames == 0:
            messagebox.showinfo("資訊", "根據速率曲線，沒有可匯出的幀。"); return

        # 2. 預先計算所有圖層的累積電弧數據
        cumulative_arc_data = {}
        for layer in export_layers:
            layer_cumulative = []
            cumulative_data = []
            for frame_segments in layer.last_simulation_data:
                cumulative_data.extend(frame_segments)
                layer_cumulative.append(list(cumulative_data))
            cumulative_arc_data[layer] = layer_cumulative

        # 3. 決定渲染比例和是否裁切
        active_layer = self.get_active_layer()
        use_export_box = active_layer.show_export_box.get()
        box = active_layer.export_box
        target_width, target_height = 3840, 2160

        if use_export_box:
            if box['w'] <= 0 or box['h'] <= 0:
                messagebox.showerror("錯誤", "匯出框的寬度和高度必須大於 0。"); return
            render_scale = min(target_width / box['w'], target_height / box['h'])
        else:
            canvas_width, canvas_height = self.canvas.winfo_width(), self.canvas.winfo_height()
            if canvas_width == 0 or canvas_height == 0:
                messagebox.showerror("錯誤", "無法讀取畫布大小。"); return
            render_scale = min(target_width / canvas_width, target_height / canvas_height)

        if render_scale <= 0:
            messagebox.showerror("錯誤", "計算出的縮放比例無效。"); return

        # 4. 主渲染迴圈
        progress_win, progress_bar, progress_label = self._create_progress_window("匯出複合動畫中...", max_output_frames)
        try:
            for i in range(max_output_frames):
                arc_data_for_render = {}
                for layer in export_layers:
                    timeline = layer_timelines[layer]
                    # 如果該圖層動畫較短，則停在最後一幀
                    frame_map_idx = min(i, len(timeline) - 1)
                    if frame_map_idx < 0: continue

                    original_frame_idx = timeline[frame_map_idx]
                    arc_data_for_render[layer] = cumulative_arc_data[layer][original_frame_idx]

                # 渲染完整尺寸的複合圖片
                image_to_save = self._render_scene_to_pillow(
                    arc_data_for_frame=arc_data_for_render,
                    scale=render_scale,
                    for_export=True,
                    export_layers=export_layers
                )
                if image_to_save is None: continue

                # 如果需要，進行裁切
                if use_export_box:
                    crop_x1 = int(box['x'] * render_scale)
                    crop_y1 = int(box['y'] * render_scale)
                    crop_x2 = int((box['x'] + box['w']) * render_scale)
                    crop_y2 = int((box['y'] + box['h']) * render_scale)
                    image_to_save = image_to_save.crop((crop_x1, crop_y1, crop_x2, crop_y2))

                # 儲存最終幀
                filepath = os.path.join(output_dir, f"frame_{i+1:04d}.png")
                image_to_save.save(filepath, 'PNG', dpi=(300, 300))

                progress_bar['value'] = i + 1
                progress_label.config(text=f"{i + 1} / {max_output_frames}")
                progress_win.update()

            progress_win.destroy()
            is_transparent = next((l.is_bg_transparent.get() for l in self.layers if l.is_visible.get()), False)
            self._create_video_from_frames(output_dir, max_output_frames, video_filepath, is_transparent)
        except Exception as e:
            messagebox.showerror("匯出錯誤", f"匯出過程中發生錯誤:\n{e}")
        finally:
            if progress_win.winfo_exists(): progress_win.destroy()

    def _build_frame_map(self, points, total_original_frames):
        if not points or total_original_frames <= 1: return list(range(total_original_frames))
        points.sort(key=lambda p: p[0])
        def get_speed_at_percent(p):
            if p <= points[0][0]: return points[0][1]
            if p >= points[-1][0]: return points[-1][1]
            for i in range(len(points) - 1):
                if points[i][0] <= p <= points[i+1][0]:
                    p1, p2 = points[i], points[i+1]
                    break
            else: return 1.0
            time_range = p2[0] - p1[0]
            if time_range == 0: return p1[1]
            local_percent = (p - p1[0]) / time_range
            return p1[1] + local_percent * (p2[1] - p1[1])

        frame_map, time_in_original_frames = [], 0.0
        while time_in_original_frames < total_original_frames:
            frame_map.append(int(round(time_in_original_frames)))
            current_percent = time_in_original_frames / (total_original_frames -1)
            speed = get_speed_at_percent(current_percent)
            time_in_original_frames += max(0.1, speed) # 確保動畫前進

        final_map = []
        if frame_map:
            final_map.append(frame_map[0])
            for i in range(1, len(frame_map)):
                if frame_map[i] > final_map[-1]:
                    final_map.append(frame_map[i])
        if total_original_frames > 0 and (not final_map or final_map[-1] < total_original_frames - 1):
            final_map.append(total_original_frames - 1)
        return [f for f in final_map if f < total_original_frames]

    def save_scene(self, filepath=None):
        """將 *所有* 圖層儲存到 .zip 檔案。"""
        if filepath is None:
            filepath = filedialog.asksaveasfilename(title="儲存場景檔案", defaultextension=".zip", filetypes=[("放電模擬場景", "*.zip")])
        if not filepath: return

        try:
            image_files = {}
            # 將所有圖層轉換為可序列化的字典
            scene_data = {'layers': []}
            for layer in self.layers:
                layer_dict = layer.to_dict()
                # 收集圖片以便儲存
                for i, img_obj in enumerate(layer.images):
                    img_filename = f"images/image_{id(img_obj)}.png"
                    image_files[img_filename] = img_obj.pil_image_original
                    # 更新字典中的路徑
                    layer_dict['images'][i]['path'] = img_filename
                scene_data['layers'].append(layer_dict)

            # 全域設定
            scene_data['global_settings'] = {'keep_image_frames': self.keep_image_frames.get()}

            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                class NpEncoder(json.JSONEncoder):
                    def default(self, obj):
                        if isinstance(obj, np.integer): return int(obj)
                        if isinstance(obj, np.floating): return float(obj)
                        if isinstance(obj, np.ndarray): return obj.tolist()
                        return super(NpEncoder, self).default(obj)
                zf.writestr('scene.json', json.dumps(scene_data, indent=2, cls=NpEncoder))

                for img_path, pil_img in image_files.items():
                    with io.BytesIO() as buffer:
                        pil_img.save(buffer, format="PNG")
                        zf.writestr(img_path, buffer.getvalue())
        except Exception as e:
            messagebox.showerror("儲存失敗", f"儲存場景時發生錯誤:\n{e}")

    def load_scene(self):
        """從 .zip 檔案載入所有圖層。"""
        filepath = filedialog.askopenfilename(title="載入場景檔案", filetypes=[("放電模擬場景", "*.zip")])
        if not filepath: return
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                if 'scene.json' not in zf.namelist():
                    messagebox.showerror("載入失敗", "無效的場景檔案：找不到 scene.json。"); return

                # 先清除所有現有狀態
                self.clear_all_layers()

                with zf.open('scene.json') as f: scene_data = json.load(f)

                # 載入圖片到記憶體
                image_map = {}
                for name in zf.namelist():
                    if name.startswith('images/'):
                        with zf.open(name) as img_file:
                            img_data = io.BytesIO(img_file.read())
                            pil_image = Image.open(img_data); pil_image.load()
                            image_map[name] = pil_image

                # 重建圖層
                self.layers = [Layer.from_dict(ld, self, image_map) for ld in scene_data.get('layers', [])]
                if not self.layers: self.layers = [Layer()] # 確保至少有一個圖層
                self.active_layer_index = 0

                # 載入全域設定
                global_settings = scene_data.get('global_settings', {})
                self.keep_image_frames.set(global_settings.get('keep_image_frames', False))

                # 更新UI以反映第一個圖層的狀態
                self.update_ui_from_active_layer()
        except Exception as e:
            messagebox.showerror("載入失敗", f"載入場景時發生未預期的錯誤:\n{e}")
            self.clear_all_layers()

    def clear_all_layers(self):
        """清除所有圖層並重設為單一乾淨圖層。"""
        if self.animation_job: self.after_cancel(self.animation_job)
        self.animation_job = None
        self.select_item(None)
        self.layers = [Layer()]
        self.active_layer_index = 0
        self.update_ui_from_active_layer()


if __name__ == "__main__":
    app = App()
    app.mainloop()
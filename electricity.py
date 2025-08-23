import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog, colorchooser
from PIL import Image, ImageTk, ImageDraw
import math
import random
import itertools
import imageio
import numpy as np

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

# --- 幾何物體基底類別 ---
class Shape:
    def __init__(self, canvas, voltage):
        self.canvas = canvas
        self.voltage = voltage
        self.id = None
        self.outline_id = None
        self.handles = []
        self.shape_type = "Shape"

    def draw(self): raise NotImplementedError
    def contains(self, px, py): raise NotImplementedError
    def move(self, dx, dy): raise NotImplementedError
    def get_handle_at(self, x, y): return None
    def move_handle(self, handle_index, new_x, new_y): pass
    def get_center(self): raise NotImplementedError
    def get_emission_points(self, num_points=20): raise NotImplementedError
    
    def select(self):
        self.deselect()
        self.outline_id = self.canvas.create_polygon(
            self.get_outline_points(), outline=SELECTED_OUTLINE_COLOR, 
            width=2, fill='', dash=(4, 4)
        )
        self._create_handles()

    def deselect(self):
        if self.outline_id:
            self.canvas.delete(self.outline_id)
            self.outline_id = None
        self._delete_handles()

    def _create_handles(self): pass
    def _delete_handles(self):
        for handle in self.handles: self.canvas.delete(handle)
        self.handles.clear()

    def update_color(self):
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        self.canvas.itemconfig(self.id, fill=color)

    def update_params(self, **kwargs):
        if 'voltage' in kwargs:
            self.voltage = kwargs['voltage']
            self.update_color()
        self.draw()
        if self.outline_id: self.select()

# --- 各種形狀的具體實現 ---
class Needle(Shape):
    def __init__(self, canvas, x, y, voltage=10000, radius=10):
        super().__init__(canvas, voltage)
        self.x, self.y, self.radius = x, y, radius
        self.shape_type = "Needle"
        self.draw()

    def draw(self):
        if self.id: self.canvas.delete(self.id)
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        self.id = self.canvas.create_oval(
            self.x - self.radius, self.y - self.radius,
            self.x + self.radius, self.y + self.radius,
            fill=color, outline="white", width=1)

    def contains(self, px, py):
        return (px - self.x)**2 + (py - self.y)**2 <= self.radius**2

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.canvas.move(self.id, dx, dy)

    def get_outline_points(self):
        return self.canvas.coords(self.id)
    
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

class Rod(Shape):
    def __init__(self, canvas, x1, y1, x2, y2, voltage=10000, thickness=5):
        super().__init__(canvas, voltage)
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.thickness = thickness
        self.shape_type = "Rod"
        self.draw()

    def draw(self):
        if self.id: self.canvas.delete(self.id)
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        self.id = self.canvas.create_line(
            self.x1, self.y1, self.x2, self.y2, 
            fill=color, width=self.thickness, capstyle=tk.ROUND)

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
        self.canvas.coords(self.id, self.x1, self.y1, self.x2, self.y2)
    
    def get_outline_points(self):
        return (self.x1, self.y1, self.x2, self.y2)

    def _create_handles(self):
        for x, y in [(self.x1, self.y1), (self.x2, self.y2)]:
            h_id = self.canvas.create_oval(x-HANDLE_RADIUS, y-HANDLE_RADIUS, 
                                           x+HANDLE_RADIUS, y+HANDLE_RADIUS,
                                           fill=HANDLE_COLOR, outline='white')
            self.handles.append(h_id)

    def get_handle_at(self, x, y):
        for i, h_id in enumerate(self.handles):
            hx, hy, _, _ = self.canvas.coords(h_id)
            hx += HANDLE_RADIUS; hy += HANDLE_RADIUS
            if (x - hx)**2 + (y - hy)**2 < HANDLE_RADIUS**2:
                return i
        return None

    def move_handle(self, handle_index, new_x, new_y):
        if handle_index == 0:
            self.x1, self.y1 = new_x, new_y
        else:
            self.x2, self.y2 = new_x, new_y
        self.draw()
        self.select()
    
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

class Plate(Shape):
    def __init__(self, canvas, x, y, voltage=0, width=150, height=30):
        super().__init__(canvas, voltage)
        w, h = width/2, height/2
        self.points = [(x-w, y-h), (x+w, y-h), (x+w, y+h), (x-w, y+h)]
        self.shape_type = "Plate"
        self.draw()

    def draw(self):
        if self.id: self.canvas.delete(self.id)
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        flat_points = [coord for point in self.points for coord in point]
        self.id = self.canvas.create_polygon(
            flat_points, fill=color, outline="white", width=1)
        
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
        self.draw()

    def get_outline_points(self):
        return [coord for point in self.points for coord in point]

    def _create_handles(self):
        for x, y in self.points:
            h_id = self.canvas.create_oval(x-HANDLE_RADIUS, y-HANDLE_RADIUS, 
                                           x+HANDLE_RADIUS, y+HANDLE_RADIUS,
                                           fill=HANDLE_COLOR, outline='white')
            self.handles.append(h_id)

    def get_handle_at(self, x, y):
        for i, h_id in enumerate(self.handles):
            hx, hy, _, _ = self.canvas.coords(h_id)
            hx += HANDLE_RADIUS; hy += HANDLE_RADIUS
            if (x - hx)**2 + (y - hy)**2 < HANDLE_RADIUS**2:
                return i
        return None

    def move_handle(self, handle_index, new_x, new_y):
        self.points[handle_index] = (new_x, new_y)
        self.draw()
        self.select()

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

class ArbitraryShape(Shape):
    def __init__(self, canvas, points, voltage=0):
        super().__init__(canvas, voltage)
        self.points = points 
        self.shape_type = "Arbitrary"
        self.draw()

    def draw(self):
        if self.id: self.canvas.delete(self.id)
        color = HV_COLOR if self.voltage >= 0 else GND_COLOR
        flat_points = [coord for point in self.points for coord in point]
        self.id = self.canvas.create_polygon(
            flat_points, fill=color, outline="white", width=1)
        
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
        self.draw()

    def get_outline_points(self):
        return [coord for point in self.points for coord in point]

    def _create_handles(self):
        for x, y in self.points:
            h_id = self.canvas.create_oval(x-HANDLE_RADIUS, y-HANDLE_RADIUS, 
                                           x+HANDLE_RADIUS, y+HANDLE_RADIUS,
                                           fill=HANDLE_COLOR, outline='white')
            self.handles.append(h_id)

    def get_handle_at(self, x, y):
        for i, h_id in enumerate(self.handles):
            hx, hy, _, _ = self.canvas.coords(h_id)
            hx += HANDLE_RADIUS; hy += HANDLE_RADIUS
            if (x - hx)**2 + (y - hy)**2 < HANDLE_RADIUS**2:
                return i
        return None

    def move_handle(self, handle_index, new_x, new_y):
        self.points[handle_index] = (new_x, new_y)
        self.draw()
        self.select()

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
        # 1. 旋轉: expand=True可確保旋轉後圖片不被裁切
        rotated_img = self.pil_image_original.rotate(self.angle, resample=Image.Resampling.BICUBIC, expand=True)

        # 2. 縮放
        w, h = rotated_img.size
        new_size = (int(w * self.scale), int(h * self.scale))
        # 使用LANCZOS以獲得較好的縮放品質
        scaled_img = rotated_img.resize(new_size, Image.Resampling.LANCZOS)

        # 3. 轉換為Tkinter格式並繪製
        self.tk_image = ImageTk.PhotoImage(scaled_img)
        if self.id: self.canvas.delete(self.id)
        self.id = self.canvas.create_image(self.x, self.y, image=self.tk_image, tags="image")

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
        self.canvas.move(self.id, dx, dy)
        if self.outline_id:
            self.canvas.move(self.outline_id, dx, dy)
            for handle in self.handles.values():
                self.canvas.move(handle, dx, dy)

    def select(self):
        self.deselect()

        w, h = self.pil_image_original.size
        w_scaled, h_scaled = w * self.scale / 2, h * self.scale / 2

        # 定義本地座標中的四個角點
        points = [(-w_scaled, -h_scaled), (w_scaled, -h_scaled),
                  (w_scaled, h_scaled), (-w_scaled, h_scaled)]

        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        rotated_points = []
        for p_x, p_y in points:
            # 旋轉角點並加上中心點座標
            world_x = (p_x * cos_a - p_y * sin_a) + self.x
            world_y = (p_x * sin_a + p_y * cos_a) + self.y
            rotated_points.extend([world_x, world_y])

        self.outline_id = self.canvas.create_polygon(
            rotated_points, outline=SELECTED_OUTLINE_COLOR,
            width=2, fill='', dash=(4, 4), tags="selection")
        self._create_handles()

    def deselect(self):
        if self.outline_id:
            self.canvas.delete(self.outline_id)
            self.outline_id = None
        self._delete_handles()

    def _create_handles(self):
        self._delete_handles()

        w, h = self.pil_image_original.size
        w_s, h_s = w * self.scale, h * self.scale

        # 定義控制點在本地座標的位置 (右下角:縮放, 右上角:旋轉)
        handle_positions = {
            'scale': (w_s / 2, h_s / 2),
            'rotate': (w_s / 2, -h_s / 2)
        }

        rad = math.radians(self.angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        for name, (p_x, p_y) in handle_positions.items():
            world_x = (p_x * cos_a - p_y * sin_a) + self.x
            world_y = (p_x * sin_a + p_y * cos_a) + self.y

            h_id = self.canvas.create_oval(world_x - HANDLE_RADIUS, world_y - HANDLE_RADIUS,
                                           world_x + HANDLE_RADIUS, world_y + HANDLE_RADIUS,
                                           fill=HANDLE_COLOR, outline='white', tags="selection")
            self.handles[name] = h_id

    def _delete_handles(self):
        for handle_id in self.handles.values():
            self.canvas.delete(handle_id)
        self.handles.clear()

    def get_handle_at(self, x, y):
        for name, h_id in self.handles.items():
            hx1, hy1, hx2, hy2 = self.canvas.coords(h_id)
            if hx1 <= x <= hx2 and hy1 <= y <= hy2:
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

        self.draw()
        self.select()

    def set_layer(self, layer):
        if layer == 'front':
            self.canvas.tag_raise(self.id)
            self.canvas.tag_raise("selection") # 同時提高選取框和控制點
            self.app.top_images.add(self)
        elif layer == 'back':
            self.canvas.tag_lower(self.id)
            if self in self.app.top_images:
                self.app.top_images.remove(self)

# --- 【新增】電弧彩現器 ---
class ArcRenderer:
    def __init__(self, canvas, appearance_params):
        self.canvas = canvas
        self.params = appearance_params

    def _interpolate_color(self, color1, color2, factor):
        try:
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return color1

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

    def _draw_arc_segment(self, segment_data):
        p1, p2 = segment_data['p1'], segment_data['p2']
        thickness, life = segment_data['thickness'], segment_data['life']

        if thickness < 0.2: return

        life_factor = max(0, min(1, life / self.params['arc_max_life']))
        core_thickness = thickness * (0.2 + life_factor * 0.8)
        if core_thickness < 0.2: return

        segment_color = self._interpolate_color(self.params['arc_color'], "#FFFFFF", life_factor)

        dx, dy = p2[0] - p1[0], p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 1e-6: return
        nx, ny = -dy / length, dx / length

        if self.params['arc_glow_strength'] > 0:
            num_glow_layers = 15
            max_glow_radius = core_thickness / 2 * (1 + self.params['arc_glow_strength'] * 3.0)
            glow_falloff_points = self.params['glow_falloff_points']

            for i in range(num_glow_layers, 0, -1):
                normalized_dist = i / num_glow_layers
                alpha = self._get_glow_alpha_from_profile(normalized_dist, glow_falloff_points)
                if alpha <= 0.01: continue

                layer_color = self._interpolate_color(BACKGROUND_COLOR, self.params['arc_color'], alpha)
                layer_width = max_glow_radius * normalized_dist * 2

                p1a = (p1[0] + nx * layer_width/2, p1[1] + ny * layer_width/2)
                p2a = (p2[0] + nx * layer_width/2, p2[1] + ny * layer_width/2)
                p2b = (p2[0] - nx * layer_width/2, p2[1] - ny * layer_width/2)
                p1b = (p1[0] - nx * layer_width/2, p1[1] - ny * layer_width/2)
                self.canvas.create_polygon(p1a, p2a, p2b, p1b, fill=layer_color, outline="", tags="arc")

        self.canvas.create_line(*p1, *p2, fill=segment_color, width=core_thickness, tags="arc", capstyle=tk.ROUND)

    def render_frame_data(self, frame_data):
        for segment in frame_data:
            self._draw_arc_segment(segment)

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
                    'thickness': self.params['arc_max_thickness'], 'life': self.params['arc_max_life']
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
                thickness, life = arc_data['thickness'], arc_data['life']

                if life <= 0 or thickness < 0.5: continue

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
                        current_frame_segments.append({'p1': current_point, 'p2': closest_point, 'thickness': thickness * 1.5, 'life': life})
                        jump_occurred = True
                
                if jump_occurred: continue

                if any(t.contains(*current_point) for t in self.target_shapes) or \
                   not (0 < current_point[0] < canvas_size[0] and 0 < current_point[1] < canvas_size[1]):
                    continue

                next_point, next_direction = self._get_next_point(current_point, current_direction)
                if next_point is None: continue

                current_frame_segments.append({'p1': current_point, 'p2': next_point, 'thickness': thickness, 'life': life})
                next_active_arcs.append({'current': next_point, 'direction': next_direction, 'thickness': thickness, 'life': life - 1})

                if random.random() < self.params['fork_chance']:
                    fork_point, fork_direction = self._get_next_point(current_point, current_direction)
                    if fork_point:
                        fork_thickness = thickness * 0.7
                        current_frame_segments.append({'p1': current_point, 'p2': fork_point, 'thickness': fork_thickness, 'life': life})
                        next_active_arcs.append({'current': fork_point, 'direction': fork_direction, 'thickness': fork_thickness, 'life': life - 1})

            self.active_arcs = next_active_arcs
            self.simulation_data.append(current_frame_segments)

        return self.simulation_data

# --- 主應用程式 GUI (V10.0 - 影片匯出) ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("進階放電模擬系統 V10.1 (即時速率預覽)")
        self.geometry("1200x800")

        self.shapes, self.images = [], []
        self.selected_item = None
        self.drag_data = {}
        self.top_images = set()

        self.add_shape_mode = None
        self.is_creating_rod = False
        self.is_creating_arbitrary_shape = False
        self.current_polygon_points = []
        self.temp_drawing_artifacts = []
        self.rubber_band_line_id, self.closing_line_id = None, None
        
        self.last_simulation_data = None
        self.animation_job = None
        self.animation_frame_index = 0
        self.arc_renderer = None

        # --- 新增: 分段速率控制的狀態 ---
        self.speed_segments = []
        self.animation_frame_map = []
        self.total_frames = 0

        # --- 新增: 分段速率UI的變數 ---
        self.speed_control_frame = None
        self.segment_listbox = None
        self.start_frame_var = None
        self.end_frame_var = None
        self.speed_var = None

        self.sim_params = {
            'fork_chance': 0.015, 'path_interruption_chance': 0.005, 'step_length': 5,
            'arc_threshold_v_pixel': 150.0, 'probe_count': 15, 'probe_angle': 120,
            'field_exponent': 2.5, 'final_jump_distance': 30.0, 'arc_color': ARC_COLOR,
            'arc_max_thickness': 2.0, 'arc_glow_strength': 0.4, 'arc_max_life': 200,
            'glow_falloff_1': 0.7, 'glow_falloff_2': 0.3, 'glow_falloff_3': 0.1, 'glow_falloff_4': 0.0,
        }
        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Create a container for the scrollable control panel ---
        control_container = tk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2)
        control_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # --- Create a Canvas and a Scrollbar ---
        scroll_canvas = tk.Canvas(control_container, bg=CONTROL_PANEL_BG, highlightthickness=0, width=250)
        scrollbar = ttk.Scrollbar(control_container, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Create a frame inside the canvas to hold the content ---
        scrollable_frame = tk.Frame(scroll_canvas, bg=CONTROL_PANEL_BG)

        # --- Add the frame to a window in the canvas ---
        scrollable_frame_window = scroll_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def configure_scroll_region(event):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))
            # Make the scrollable frame match the canvas width
            scroll_canvas.itemconfig(scrollable_frame_window, width=scroll_canvas.winfo_width())

        def on_mouse_wheel(event):
            # Platform-independent scrolling
            if event.num == 5 or event.delta < 0:
                scroll_canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                scroll_canvas.yview_scroll(-1, "units")

        scrollable_frame.bind("<Configure>", configure_scroll_region)
        # Bind mouse wheel scrolling to the canvas and its children
        self.bind_all("<MouseWheel>", on_mouse_wheel)
        self.bind_all("<Button-4>", on_mouse_wheel)
        self.bind_all("<Button-5>", on_mouse_wheel)


        self.canvas = tk.Canvas(main_frame, bg=BACKGROUND_COLOR, highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- All subsequent frames are packed into the scrollable_frame ---
        add_frame = tk.LabelFrame(scrollable_frame, text="新增物體", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(add_frame, text="針頭", command=lambda: self.set_add_mode("Needle")).pack(fill=tk.X)
        tk.Button(add_frame, text="電棒", command=lambda: self.set_add_mode("Rod")).pack(fill=tk.X)
        tk.Button(add_frame, text="平板", command=lambda: self.set_add_mode("Plate")).pack(fill=tk.X)
        tk.Button(add_frame, text="任意形狀", command=lambda: self.set_add_mode("Arbitrary")).pack(fill=tk.X)
        ttk.Separator(add_frame, orient='horizontal').pack(fill='x', pady=5)
        tk.Button(add_frame, text="新增圖片", command=self.add_image).pack(fill=tk.X)

        param_frame = tk.LabelFrame(scrollable_frame, text="模擬參數", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        param_frame.pack(fill=tk.X, padx=10, pady=10)
        def add_bar(label, key, frm, from_, to_, resolution, fmt, row):
            tk.Label(frm, text=label, bg=CONTROL_PANEL_BG).grid(row=row, column=0, sticky="w")
            var = tk.DoubleVar(value=self.sim_params[key])
            # Reduce scale length slightly to fit better with scrollbar
            scale = tk.Scale(frm, variable=var, from_=from_, to=to_, resolution=resolution, orient=tk.HORIZONTAL, length=100, showvalue=0, bg=CONTROL_PANEL_BG)
            scale.grid(row=row, column=1)
            val_label = tk.Label(frm, text=fmt.format(self.sim_params[key]), bg=CONTROL_PANEL_BG, width=6, anchor='w')
            val_label.grid(row=row, column=2)
            def on_change(val):
                self.sim_params[key] = float(val)
                val_label.config(text=f"{float(val):.1f}")
                if 'arc' in key or 'glow' in key:
                    if hasattr(self, '_preview_job'):
                        self.after_cancel(self._preview_job)
                    self._preview_job = self.after(50, self.preview_simulation)
            if isinstance(resolution, float):
                val_label.config(text=f"{var.get():.1f}")
            scale.config(command=on_change)
        add_bar("觸發閾(V/px)", 'arc_threshold_v_pixel', param_frame, 1, 500, 1, "{:.0f}", 0)
        add_bar("分岔機率", 'fork_chance', param_frame, 0, 0.05, 0.001, "{:.3f}", 1)
        add_bar("消散機率", 'path_interruption_chance', param_frame, 0, 0.05, 0.001, "{:.3f}", 2)
        add_bar("步長", 'step_length', param_frame, 1, 20, 1, "{:.0f}", 3)
        add_bar("探測點數量", 'probe_count', param_frame, 3, 40, 1, "{:.0f}", 4)
        add_bar("探測角度(°)", 'probe_angle', param_frame, 30, 180, 5, "{:.0f}", 5)
        add_bar("電場指數", 'field_exponent', param_frame, 1.0, 5.0, 0.1, "{:.1f}", 6)
        add_bar("最終跳躍(px)", 'final_jump_distance', param_frame, 0, 100, 1, "{:.0f}", 7)

        appearance_frame = tk.LabelFrame(scrollable_frame, text="電弧外觀 (可即時預覽)", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        appearance_frame.pack(fill=tk.X, padx=10, pady=10)
        appearance_frame.columnconfigure(1, weight=1)
        tk.Button(appearance_frame, text="電弧顏色", command=self._choose_arc_color).grid(row=0, column=0, columnspan=2, sticky="ew", pady=2)
        self.arc_color_preview = tk.Frame(appearance_frame, width=24, height=24, bg=self.sim_params['arc_color'], relief=tk.SUNKEN, borderwidth=1)
        self.arc_color_preview.grid(row=0, column=2, padx=(5,0), pady=2)
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
        tk.Button(sim_frame, text="清除電弧", command=self.clear_simulation).pack(fill=tk.X, pady=3)
        tk.Button(sim_frame, text="清除所有", command=self.clear_all).pack(fill=tk.X, pady=3)
        ttk.Separator(sim_frame).pack(fill='x', pady=5)
        tk.Button(sim_frame, text="儲存動畫...", command=self.open_export_dialog).pack(fill=tk.X, pady=3)

        self.speed_control_frame = ttk.LabelFrame(scrollable_frame, text="分段速率控制")
        self.speed_control_frame.pack(fill=tk.X, padx=10, pady=10)
        self._create_speed_control_widgets(self.speed_control_frame)
        self._set_speed_controls_state(tk.DISABLED)

        tk.Button(scrollable_frame, text="刪除選取", command=self.delete_selected).pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press); self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release); self.canvas.bind("<Double-1>", self.on_canvas_double_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion); self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.bind("<Escape>", self.cancel_creation_mode)

    # Most methods from V9.0 are unchanged and omitted for brevity...
    def _choose_arc_color(self):
        color_code = colorchooser.askcolor(title="選擇電弧顏色", initialcolor=self.sim_params['arc_color'])
        if color_code and color_code[1]:
            self.sim_params['arc_color'] = color_code[1]
            self.arc_color_preview.config(bg=color_code[1])
            self.preview_simulation()
    def on_canvas_right_click(self, event):
        if self.is_creating_arbitrary_shape: self.cancel_creation_mode(event); return
        item_found = next((item for item in reversed(self.images) if item.contains(event.x, event.y)), None)
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
            self.is_creating_arbitrary_shape = True
            messagebox.showinfo("繪製提示", "請在畫布上點擊以放置頂點。\n點擊第一個頂點或按兩下來完成形狀。\n按右鍵或 Esc 鍵取消。")
        self.select_item(None); self.canvas.config(cursor="crosshair")
    def add_image(self):
        self.cancel_creation_mode()
        filepath = filedialog.askopenfilename(title="選擇圖片", filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")])
        if not filepath: return
        try:
            pil_image = Image.open(filepath)
            x, y = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
            image_obj = DecorativeImage(self.canvas, x, y, pil_image, self)
            self.images.append(image_obj); self.select_item(image_obj)
        except Exception as e: messagebox.showerror("圖片載入失敗", f"無法載入圖片檔案：\n{e}")
    def raise_top_images(self):
        for img in self.top_images: img.set_layer('front')
    def on_canvas_press(self, event):
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
        if self.selected_item:
            handle_index = self.selected_item.get_handle_at(event.x, event.y)
            if handle_index is not None:
                self.drag_data = {'item': self.selected_item, 'type': 'handle', 'index': handle_index}; return
        all_items = self.images + self.shapes
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
        if self.is_creating_rod and 'x1' in self.drag_data:
            if self.drag_data['line_id']: self.canvas.delete(self.drag_data['line_id'])
            self.drag_data['line_id'] = self.canvas.create_line(self.drag_data['x1'], self.drag_data['y1'], event.x, event.y, fill=SELECTED_OUTLINE_COLOR, width=3, dash=(4,4))
            return
        if 'item' in self.drag_data:
            item = self.drag_data['item']
            if self.drag_data['type'] == 'body':
                dx, dy = event.x - self.drag_data['x'], event.y - self.drag_data['y']
                item.move(dx, dy)
                self.drag_data['x'], self.drag_data['y'] = event.x, event.y
            elif self.drag_data['type'] == 'handle': item.move_handle(self.drag_data['index'], event.x, event.y)
    def on_canvas_release(self, event):
        if self.is_creating_arbitrary_shape: return
        self.canvas.config(cursor="")
        if self.add_shape_mode:
            shape = None
            if self.add_shape_mode == "Needle": shape = Needle(self.canvas, event.x, event.y)
            elif self.add_shape_mode == "Plate": shape = Plate(self.canvas, event.x, event.y)
            elif self.is_creating_rod:
                if self.drag_data.get('line_id'): self.canvas.delete(self.drag_data['line_id'])
                x1, y1 = self.drag_data['x1'], self.drag_data['y1']
                if math.hypot(event.x - x1, event.y - y1) > 10: shape = Rod(self.canvas, x1, y1, event.x, event.y)
            if shape: self.shapes.append(shape); self.select_item(shape)
            self.add_shape_mode, self.is_creating_rod = None, False
        self.drag_data.clear()
    def on_canvas_double_click(self, event):
        if self.is_creating_arbitrary_shape: self.finalize_arbitrary_shape(); return
        item_found = next((s for s in reversed(self.shapes) if s.contains(event.x, event.y)), None)
        if item_found and hasattr(item_found, 'voltage'):
            self.select_item(item_found)
            ParameterDialog(self, f"設定 {item_found.shape_type} 參數", item_found)
    def finalize_arbitrary_shape(self):
        if not self.is_creating_arbitrary_shape or len(self.current_polygon_points) < 3:
            messagebox.showwarning("創建錯誤", "一個有效的封閉導體至少需要3個頂點。"); self.cancel_creation_mode(); return
        shape = ArbitraryShape(self.canvas, self.current_polygon_points.copy())
        self.shapes.append(shape); self.cancel_creation_mode(); self.select_item(shape)
    def select_item(self, item):
        if self.selected_item and self.selected_item != item: self.selected_item.deselect()
        if item and self.selected_item != item: item.select(); self.selected_item = item
        elif not item: self.selected_item = None
    def delete_selected(self):
        if not self.selected_item: return
        item = self.selected_item; item.deselect(); self.canvas.delete(item.id)
        if item in self.shapes: self.shapes.remove(item)
        elif item in self.images:
            self.images.remove(item)
            if item in self.top_images: self.top_images.remove(item)
        self.select_item(None)
    def _get_current_appearance_params(self):
        params = {k: v for k, v in self.sim_params.items() if 'arc' in k or 'glow' in k}
        params['glow_falloff_points'] = [
            (0.0, 1.0), (0.25, self.sim_params['glow_falloff_1']),
            (0.5, self.sim_params['glow_falloff_2']), (0.75, self.sim_params['glow_falloff_3']),
            (1.0, self.sim_params['glow_falloff_4'])]
        return params
    def start_new_simulation(self):
        self.clear_simulation()
        if len(self.shapes) < 2: messagebox.showwarning("模擬錯誤", "需要至少兩個物體才能進行模擬。"); return
        arc_jobs = []
        threshold = self.sim_params['arc_threshold_v_pixel']
        for shape_a, shape_b in itertools.combinations(self.shapes, 2):
            delta_v = abs(shape_a.voltage - shape_b.voltage)
            center_a, center_b = shape_a.get_center(), shape_b.get_center()
            distance = math.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])
            if distance > 1.0 and delta_v / distance > threshold:
                source, target = (shape_a, shape_b) if shape_a.voltage > shape_b.voltage else (shape_b, shape_a)
                arc_jobs.append({'source': source, 'target': target})
        if arc_jobs:
            simulator = Simulator(self.shapes, self.sim_params)
            canvas_size = (self.canvas.winfo_width(), self.canvas.winfo_height())
            self.last_simulation_data = simulator.run_simulation(arc_jobs, canvas_size)

            if self.last_simulation_data:
                self.total_frames = len(self.last_simulation_data)
                self._set_speed_controls_state(tk.NORMAL)
                self._reset_speed_segments() # This will also trigger a preview
            else:
                self.total_frames = 0
                self._set_speed_controls_state(tk.DISABLED)
                self._reset_speed_segments()

        else:
            messagebox.showinfo("模擬資訊", "在目前的佈局和電壓設定下，沒有物體之間的電位梯度超過觸發閾值。")
            self.total_frames = 0
            self._set_speed_controls_state(tk.DISABLED)
            self._reset_speed_segments()

    def preview_simulation(self):
        if not self.last_simulation_data:
            self.clear_simulation()
            return

        self.clear_simulation()
        self.animation_frame_map = self._build_frame_map(self.speed_segments, self.total_frames)
        if not self.animation_frame_map:
            return

        appearance_params = self._get_current_appearance_params()
        self.arc_renderer = ArcRenderer(self.canvas, appearance_params)
        self.animation_frame_index = 0
        self.play_simulation_animation()

    def play_simulation_animation(self):
        if self.animation_frame_index < len(self.animation_frame_map):
            original_frame_index = self.animation_frame_map[self.animation_frame_index]
            if original_frame_index < len(self.last_simulation_data):
                 frame_data = self.last_simulation_data[original_frame_index]
                 self.arc_renderer.render_frame_data(frame_data)
                 self.raise_top_images()
            self.animation_frame_index += 1
            self.animation_job = self.after(15, self.play_simulation_animation)
        else:
            self.animation_job = None

    def clear_simulation(self):
        if self.animation_job: self.after_cancel(self.animation_job); self.animation_job = None
        self.canvas.delete("arc")

    def clear_all(self):
        self.clear_simulation(); self.last_simulation_data = None; self.select_item(None)
        for item in self.shapes + self.images: item.deselect(); self.canvas.delete(item.id)
        self.shapes.clear(); self.images.clear()

        self.total_frames = 0
        self._set_speed_controls_state(tk.DISABLED)
        self._reset_speed_segments()

    # --- 【新增】影片匯出功能 ---
    def open_export_dialog(self):
        if not self.last_simulation_data:
            messagebox.showerror("錯誤", "沒有可以匯出的模擬數據。\n請先『執行新模擬』。")
            return
        VideoExportDialog(self, "匯出動畫", self)

    def _build_frame_map(self, segments, total_original_frames):
        """根據分段速率定義，建立最終的畫格對應列表"""
        frame_map = []
        # 將片段轉換為以0為基底的索引
        processed_segments = [{'start': s['start']-1, 'end': s['end']-1, 'speed': s['speed']} for s in segments]

        for seg in processed_segments:
            num_original_frames = seg['end'] - seg['start'] + 1
            num_new_frames = int(num_original_frames / seg['speed'])
            for i in range(num_new_frames):
                original_index = seg['start'] + int(i * seg['speed'])
                if original_index < total_original_frames:
                    frame_map.append(original_index)
        return frame_map

    def export_video(self, settings, progress_var, status_label):
        filepath = settings['filepath']
        if not filepath:
            messagebox.showerror("錯誤", "未指定檔案路徑。")
            status_label.config(text="錯誤: 未指定路徑")
            return

        frame_map = self._build_frame_map(settings['speed_segments'], len(self.last_simulation_data))
        total_new_frames = len(frame_map)

        if total_new_frames == 0:
            messagebox.showerror("錯誤", "根據目前的分段速率設定，沒有足夠的畫格可以匯出。")
            status_label.config(text="錯誤: 速率設定問題")
            return

        writer = imageio.get_writer(filepath, fps=60, format=settings['format'], codec='libx264' if settings['format'] == 'mp4' else None)
        appearance_params = self._get_current_appearance_params()

        try:
            for i, original_frame_index in enumerate(frame_map):
                frame_data = self.last_simulation_data[original_frame_index]
                bg_color = settings['bg_color']
                img_mode = 'RGBA' if settings['format'] == 'gif' and settings['transparent_bg'] else 'RGB'
                bg = (0,0,0,0) if img_mode == 'RGBA' else bg_color
                img = Image.new(img_mode, (self.canvas.winfo_width(), self.canvas.winfo_height()), bg)
                draw = ImageDraw.Draw(img, 'RGBA')

                if settings['include_conductors']: self._draw_conductors_on_pil(draw)
                if settings['include_images']: self._draw_images_on_pil(img)
                self._draw_arcs_on_pil(draw, frame_data, appearance_params, img.copy())

                final_frame = np.array(img.convert('RGB') if img_mode == 'RGB' else img)
                writer.append_data(final_frame)

                progress = (i + 1) / total_new_frames * 100
                progress_var.set(progress)
                status_label.config(text=f"正在匯出... {i+1}/{total_new_frames}")
                self.update_idletasks()

            messagebox.showinfo("完成", f"動畫已成功儲存至:\n{filepath}")
            status_label.config(text="匯出完成！")
        except Exception as e:
            messagebox.showerror("匯出失敗", f"匯出過程中發生錯誤:\n{e}")
            status_label.config(text="匯出失敗！")
        finally:
            writer.close()

    def _draw_conductors_on_pil(self, draw):
        for shape in self.shapes:
            color = HV_COLOR if shape.voltage >= 0 else GND_COLOR
            if shape.shape_type == "Needle":
                coords = (shape.x - shape.radius, shape.y - shape.radius, shape.x + shape.radius, shape.y + shape.radius)
                draw.ellipse(coords, fill=color, outline="white", width=1)
            elif shape.shape_type == "Rod":
                draw.line((shape.x1, shape.y1, shape.x2, shape.y2), fill=color, width=int(shape.thickness))
            elif shape.shape_type in ["Plate", "Arbitrary"]:
                draw.polygon(shape.points, fill=color, outline="white", width=1)

    def _draw_images_on_pil(self, base_image):
        sorted_images = sorted(self.images, key=lambda i: self.canvas.winfo_children().index(i.id) if i.id in self.canvas.winfo_children() else -1)
        for img_obj in sorted_images:
            if not hasattr(img_obj, 'pil_image_original'): continue
            rotated_img = img_obj.pil_image_original.rotate(img_obj.angle, resample=Image.Resampling.BICUBIC, expand=True)
            w, h = rotated_img.size
            new_size = (int(w * img_obj.scale), int(h * img_obj.scale))
            if new_size[0] < 1 or new_size[1] < 1: continue
            scaled_img = rotated_img.resize(new_size, Image.Resampling.LANCZOS)
            paste_x, paste_y = int(img_obj.x - new_size[0] / 2), int(img_obj.y - new_size[1] / 2)
            if scaled_img.mode == 'RGBA': base_image.paste(scaled_img, (paste_x, paste_y), scaled_img)
            else: base_image.paste(scaled_img, (paste_x, paste_y))

    def _draw_arcs_on_pil(self, draw, frame_data, params, background_img):
        def _interpolate_color(c1, c2, f):
            try:
                c1_rgb = tuple(int(c1.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)); c2_rgb = tuple(int(c2.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                rgb = [int(c1_rgb[i] + (c2_rgb[i] - c1_rgb[i]) * f) for i in range(3)]; return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            except: return c1
        def _get_glow_alpha(dist, points):
            dist = max(0, min(1, dist))
            for i in range(len(points) - 1):
                p1, p2 = points[i], points[i+1]
                if p1[0] <= dist <= p2[0]:
                    r = p2[0] - p1[0]; return p1[1] + ((dist - p1[0]) / r) * (p2[1] - p1[1]) if r != 0 else p1[1]
            return points[-1][1]
        for segment in frame_data:
            p1, p2, thickness, life = segment['p1'], segment['p2'], segment['thickness'], segment['life']
            if thickness < 0.2: continue
            life_factor = max(0, min(1, life / params['arc_max_life'])); core_thickness = thickness * (0.2 + life_factor * 0.8)
            if core_thickness < 0.5: continue
            segment_color = _interpolate_color(params['arc_color'], "#FFFFFF", life_factor)
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]; length = math.hypot(dx, dy)
            if length < 1e-6: continue
            nx, ny = -dy / length, dx / length
            if params['arc_glow_strength'] > 0:
                max_glow_radius = core_thickness / 2 * (1 + params['arc_glow_strength'] * 3.0); glow_points = params['glow_falloff_points']
                for i in range(15, 0, -1):
                    dist = i / 15; alpha = _get_glow_alpha(dist, glow_points)
                    if alpha <= 0.01: continue
                    layer_color_str = _interpolate_color(BACKGROUND_COLOR, params['arc_color'], alpha)
                    layer_color_rgb = (int(layer_color_str[1:3], 16), int(layer_color_str[3:5], 16), int(layer_color_str[5:7], 16))
                    layer_width = max_glow_radius * dist * 2
                    p1a = (p1[0] + nx * layer_width/2, p1[1] + ny * layer_width/2); p2a = (p2[0] + nx * layer_width/2, p2[1] + ny * layer_width/2)
                    p2b = (p2[0] - nx * layer_width/2, p2[1] - ny * layer_width/2); p1b = (p1[0] - nx * layer_width/2, p1[1] - ny * layer_width/2)
                    poly_img = Image.new('RGBA', draw.im.size, (0,0,0,0)); poly_draw = ImageDraw.Draw(poly_img)
                    poly_draw.polygon([p1a, p2a, p2b, p1b], fill=layer_color_rgb + (int(alpha*255*0.5),))
                    draw.im.paste(poly_img, (0,0), poly_img)
            draw.line((p1[0], p1[1], p2[0], p2[1]), fill=segment_color, width=int(core_thickness))

    # --- 【新增】分段速率控制相關方法 ---
    def _create_speed_control_widgets(self, parent_frame):
        """在指定的父框架中建立速率控制UI"""
        list_frame = tk.Frame(parent_frame, bg=CONTROL_PANEL_BG); list_frame.pack(fill=tk.X, pady=2, padx=5)
        self.segment_listbox = tk.Listbox(list_frame, height=3, bg=BACKGROUND_COLOR, fg="white", selectbackground="#0074D9");
        self.segment_listbox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.segment_listbox.bind('<<ListboxSelect>>', self._on_segment_select)

        edit_frame = tk.Frame(parent_frame, bg=CONTROL_PANEL_BG); edit_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(edit_frame, text="從:", bg=CONTROL_PANEL_BG).pack(side=tk.LEFT); self.start_frame_var = tk.StringVar(); tk.Entry(edit_frame, textvariable=self.start_frame_var, width=6).pack(side=tk.LEFT, padx=(0,5))
        tk.Label(edit_frame, text="到:", bg=CONTROL_PANEL_BG).pack(side=tk.LEFT); self.end_frame_var = tk.StringVar(); tk.Entry(edit_frame, textvariable=self.end_frame_var, width=6).pack(side=tk.LEFT, padx=(0,5))
        tk.Label(edit_frame, text="速率:", bg=CONTROL_PANEL_BG).pack(side=tk.LEFT); self.speed_var = tk.StringVar(); tk.Entry(edit_frame, textvariable=self.speed_var, width=5).pack(side=tk.LEFT)

        btn_frame = tk.Frame(parent_frame, bg=CONTROL_PANEL_BG); btn_frame.pack(fill=tk.X, padx=5)
        tk.Button(btn_frame, text="更新", command=self._update_segment).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="新增片段", command=self._add_segment).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="移除片段", command=self._remove_segment).pack(side=tk.LEFT, padx=2)

    def _set_speed_controls_state(self, state):
        """啟用或禁用速率控制UI的所有子元件"""
        # Recursively set state for all children of the frame
        for widget in self.speed_control_frame.winfo_children():
            # Check for specific widget types to configure
            if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                 for sub_widget in widget.winfo_children():
                    if isinstance(sub_widget, (tk.Button, tk.Entry, tk.Listbox)):
                        sub_widget.config(state=state)
            elif isinstance(widget, (tk.Button, tk.Entry, tk.Listbox)):
                widget.config(state=state)

        # Special handling for Listbox background color to indicate disabled state
        if self.segment_listbox:
            self.segment_listbox.config(bg=BACKGROUND_COLOR if state == tk.NORMAL else "#333333")

    def _reset_speed_segments(self):
        """重置分段速率為預設值 (單一段落涵蓋所有畫格)"""
        if self.total_frames > 0:
            self.speed_segments = [{'start': 1, 'end': self.total_frames, 'speed': 1.0}]
        else:
            self.speed_segments = []
        self._refresh_segment_list()

    def _refresh_segment_list(self):
        if not self.segment_listbox: return
        self.segment_listbox.delete(0, tk.END)
        self.speed_segments.sort(key=lambda s: s['start'])

        # 填補空白區域
        filled_segments = []
        last_end = 0
        for seg in self.speed_segments:
            if seg['start'] > last_end + 1:
                filled_segments.append({'start': last_end + 1, 'end': seg['start'] - 1, 'speed': 1.0})
            filled_segments.append(seg)
            last_end = seg['end']
        if self.total_frames > 0 and last_end < self.total_frames:
            filled_segments.append({'start': last_end + 1, 'end': self.total_frames, 'speed': 1.0})
        self.speed_segments = filled_segments

        for seg in self.speed_segments:
            self.segment_listbox.insert(tk.END, f"畫格 {seg['start']}-{seg['end']} @ {seg['speed']:.1f}x")

        # 自動觸發預覽更新
        if self.last_simulation_data:
            if hasattr(self, '_preview_job'): self.after_cancel(self._preview_job)
            self._preview_job = self.after(50, self.preview_simulation)

    def _on_segment_select(self, event):
        selection = event.widget.curselection()
        if not selection: return
        idx = selection[0]
        try:
            seg = self.speed_segments[idx]
            self.start_frame_var.set(str(seg['start']))
            self.end_frame_var.set(str(seg['end']))
            self.speed_var.set(f"{seg['speed']:.1f}")
        except IndexError:
            # This can happen if the listbox is updated while a selection event is pending
            pass

    def _validate_speed_inputs(self):
        try:
            start, end = int(self.start_frame_var.get()), int(self.end_frame_var.get())
            speed = float(self.speed_var.get())
            if not (1 <= start and start <= end and end <= self.total_frames and 0.1 <= speed <= 10.0):
                 raise ValueError("輸入值超出範圍")
            return start, end, speed
        except (ValueError, TypeError):
            messagebox.showerror("輸入錯誤", f"請檢查輸入。\n畫格範圍必須在 [1, {self.total_frames}] 內。\n速率必須是 0.1 到 10.0 之間的數字。")
            return None, None, None

    def _add_segment(self):
        start, end, speed = self._validate_speed_inputs()
        if start is None: return

        # 移除任何與新片段重疊的舊片段
        self.speed_segments = [s for s in self.speed_segments if s['end'] < start or s['start'] > end]
        self.speed_segments.append({'start': start, 'end': end, 'speed': speed})
        self._refresh_segment_list()

    def _update_segment(self):
        selection = self.segment_listbox.curselection()
        if not selection:
            messagebox.showwarning("操作無效", "請先從列表中選擇一個片段進行更新。");
            return

        selected_idx = selection[0]
        start, end, speed = self._validate_speed_inputs()
        if start is None: return

        # 移除舊片段，新增更新後的片段
        self.speed_segments.pop(selected_idx)
        self.speed_segments = [s for s in self.speed_segments if s['end'] < start or s['start'] > end]
        self.speed_segments.append({'start': start, 'end': end, 'speed': speed})
        self._refresh_segment_list()

    def _remove_segment(self):
        selection = self.segment_listbox.curselection()
        if not selection:
            messagebox.showwarning("操作無效", "請先從列表中選擇一個片段進行移除。");
            return
        self.speed_segments.pop(selection[0])
        self._refresh_segment_list()


class VideoExportDialog(simpledialog.Dialog):
    def __init__(self, parent, title, app_ref):
        self.app = app_ref
        super().__init__(parent, title)

    def body(self, master):
        master.pack_configure(padx=10, pady=10)
        path_frame = ttk.LabelFrame(master, text="儲存位置與格式"); path_frame.pack(fill=tk.X, pady=5); path_frame.columnconfigure(1, weight=1)
        self.path_var = tk.StringVar(); tk.Entry(path_frame, textvariable=self.path_var).grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        tk.Button(path_frame, text="瀏覽...", command=self._browse_file).grid(row=0, column=2, padx=5)
        self.format_var = tk.StringVar(value="mp4"); tk.Radiobutton(path_frame, text="MP4", variable=self.format_var, value="mp4", command=self._on_format_change).grid(row=1, column=1, sticky='w', padx=5)
        tk.Radiobutton(path_frame, text="GIF", variable=self.format_var, value="gif", command=self._on_format_change).grid(row=1, column=2, sticky='w', padx=5)
        content_frame = ttk.LabelFrame(master, text="內容與背景"); content_frame.pack(fill=tk.X, pady=5)
        self.include_conductors = tk.BooleanVar(value=True); self.include_images = tk.BooleanVar(value=True)
        tk.Checkbutton(content_frame, text="包含導體", variable=self.include_conductors).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(content_frame, text="包含圖片", variable=self.include_images).pack(side=tk.LEFT, padx=5)
        self.bg_color_var = tk.StringVar(value=BACKGROUND_COLOR); tk.Button(content_frame, text="背景顏色", command=self._choose_bg_color).pack(side=tk.LEFT, padx=10)
        self.bg_preview = tk.Frame(content_frame, width=24, height=24, bg=self.bg_color_var.get(), relief=tk.SUNKEN, borderwidth=1); self.bg_preview.pack(side=tk.LEFT)
        self.transparent_bg = tk.BooleanVar(value=False); self.transparent_check = tk.Checkbutton(content_frame, text="透明背景 (GIF)", variable=self.transparent_bg, state=tk.DISABLED); self.transparent_check.pack(side=tk.LEFT, padx=5)

        progress_frame = ttk.LabelFrame(master, text="進度"); progress_frame.pack(fill=tk.X, pady=10)
        self.status_label = tk.Label(progress_frame, text="準備就緒"); self.status_label.pack(fill=tk.X, padx=5, pady=2)
        self.progress_var = tk.DoubleVar(); progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100); progress_bar.pack(fill=tk.X, padx=5, pady=5)
        return None

    def buttonbox(self):
        box = tk.Frame(self)
        self.ok_button = tk.Button(box, text="開始匯出", width=10, command=self.ok_pressed, default=tk.ACTIVE)
        self.ok_button.pack(side=tk.LEFT, padx=5, pady=5)
        cancel_button = tk.Button(box, text="關閉", width=10, command=self.cancel)
        cancel_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", lambda e: self.ok_pressed())
        box.pack()

    def _browse_file(self):
        fmt = self.format_var.get(); filetypes = [("MP4 video", "*.mp4"), ("GIF animation", "*.gif"), ("All files", "*.*")]; defaultextension = f".{fmt}"
        filepath = filedialog.asksaveasfilename(parent=self, title="儲存為", defaultextension=defaultextension, filetypes=filetypes)
        if filepath: self.path_var.set(filepath)
    def _choose_bg_color(self):
        color_code = colorchooser.askcolor(title="選擇背景顏色", initialcolor=self.bg_color_var.get())
        if color_code and color_code[1]: self.bg_color_var.set(color_code[1]); self.bg_preview.config(bg=color_code[1])
    def _on_format_change(self):
        self.transparent_check.config(state=tk.NORMAL if self.format_var.get() == 'gif' else tk.DISABLED)
        if self.format_var.get() != 'gif': self.transparent_bg.set(False)

    def ok_pressed(self):
        # The app now manages the speed segments. The dialog just uses them.
        # The app's refresh logic already fills gaps, so we can use the segments directly.
        self.settings = {
            'filepath': self.path_var.get(), 'format': self.format_var.get(),
            'include_conductors': self.include_conductors.get(), 'include_images': self.include_images.get(),
            'bg_color': self.bg_color_var.get(), 'transparent_bg': self.transparent_bg.get(),
            'speed_segments': self.app.speed_segments
        }
        self.ok_button.config(state=tk.DISABLED)
        self.app.export_video(self.settings, self.progress_var, self.status_label)
        self.ok_button.config(state=tk.NORMAL)

if __name__ == "__main__":
    app = App()
    app.mainloop()
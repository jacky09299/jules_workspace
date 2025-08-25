import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog, colorchooser
from PIL import Image, ImageTk, ImageDraw
import math
import random
import itertools

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
        thickness_ratio, life = segment_data['thickness_ratio'], segment_data['life']

        base_thickness = self.params['arc_max_thickness'] * thickness_ratio
        if base_thickness < 0.2: return

        life_factor = max(0, min(1, life / self.params['arc_max_life']))
        core_thickness = base_thickness * (0.2 + life_factor * 0.8)
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

# --- 主應用程式 GUI (V10.0 - 影片匯出) ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("進階放電模擬系統 V11.0 (即時顯示控制)")
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
        self.total_frames = 0
        self.speed_control_graph = None

        # --- 新增: 用於UI控制的變數 ---
        self.show_conductors = tk.BooleanVar(value=True)
        self.show_images = tk.BooleanVar(value=True)
        self.background_color_str = tk.StringVar(value=BACKGROUND_COLOR)

        self.sim_params = {
            'fork_chance': 0.015, 'path_interruption_chance': 0.005, 'step_length': 5,
            'arc_threshold_v_pixel': 150.0, 'probe_count': 15, 'probe_angle': 120,
            'field_exponent': 2.5, 'final_jump_distance': 30.0, 'arc_color': ARC_COLOR,
            'arc_max_thickness': 2.0, 'arc_glow_strength': 0.4, 'arc_max_life': 200,
            'glow_falloff_1': 0.7, 'glow_falloff_2': 0.3, 'glow_falloff_3': 0.1, 'glow_falloff_4': 0.0,
        }
        self.create_widgets()
        # 初始更新一次顯示狀態
        self.update_display()

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

        self.canvas = tk.Canvas(main_frame, bg=self.background_color_str.get(), highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        add_frame = tk.LabelFrame(scrollable_frame, text="新增物體", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(add_frame, text="針頭", command=lambda: self.set_add_mode("Needle")).pack(fill=tk.X)
        tk.Button(add_frame, text="電棒", command=lambda: self.set_add_mode("Rod")).pack(fill=tk.X)
        tk.Button(add_frame, text="平板", command=lambda: self.set_add_mode("Plate")).pack(fill=tk.X)
        tk.Button(add_frame, text="任意形狀", command=lambda: self.set_add_mode("Arbitrary")).pack(fill=tk.X)
        ttk.Separator(add_frame, orient='horizontal').pack(fill='x', pady=5)
        tk.Button(add_frame, text="新增圖片", command=self.add_image).pack(fill=tk.X)

        # --- 【新】顯示設定 ---
        display_frame = tk.LabelFrame(scrollable_frame, text="顯示設定", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        display_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Checkbutton(display_frame, text="顯示導體", variable=self.show_conductors, command=self.update_display, bg=CONTROL_PANEL_BG).pack(anchor="w")
        tk.Checkbutton(display_frame, text="顯示圖片", variable=self.show_images, command=self.update_display, bg=CONTROL_PANEL_BG).pack(anchor="w")
        
        bg_frame = tk.Frame(display_frame, bg=CONTROL_PANEL_BG)
        bg_frame.pack(fill='x', pady=(5,0))
        tk.Button(bg_frame, text="背景顏色", command=self._choose_main_bg_color).pack(side=tk.LEFT)
        self.bg_preview = tk.Frame(bg_frame, width=24, height=24, bg=self.background_color_str.get(), relief=tk.SUNKEN, borderwidth=1)
        self.bg_preview.pack(side=tk.LEFT, padx=5)
        
        param_frame = tk.LabelFrame(scrollable_frame, text="模擬參數", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        param_frame.pack(fill=tk.X, padx=10, pady=10)
        def add_bar(label, key, frm, from_, to_, resolution, fmt, row):
            tk.Label(frm, text=label, bg=CONTROL_PANEL_BG).grid(row=row, column=0, sticky="w")
            # 【修改】從 self.sim_params 初始化，確保值被保留
            var = tk.DoubleVar(value=self.sim_params[key])
            scale = tk.Scale(frm, variable=var, from_=from_, to=to_, resolution=resolution, orient=tk.HORIZONTAL, length=100, showvalue=0, bg=CONTROL_PANEL_BG)
            scale.grid(row=row, column=1)
            val_label = tk.Label(frm, text=fmt.format(self.sim_params[key]), bg=CONTROL_PANEL_BG, width=6, anchor='w')
            val_label.grid(row=row, column=2)
            def on_change(val):
                self.sim_params[key] = float(val)
                # 【修改】格式化輸出以避免不必要的 .0
                if resolution >= 1:
                    val_label.config(text=f"{int(float(val))}")
                else:
                    val_label.config(text=f"{float(val):.3f}".rstrip('0').rstrip('.'))

                if 'arc' in key or 'glow' in key:
                    if hasattr(self, '_preview_job'):
                        self.after_cancel(self._preview_job)
                    self._preview_job = self.after(50, self.preview_simulation)
            
            scale.config(command=on_change)
            # 【修改】將 scale 和 label 附加到 var 上，以便可以從外部更新
            var.trace_add("write", lambda *args: on_change(var.get()))
            setattr(var, 'scale_widget', scale)
            setattr(var, 'label_widget', val_label)
            setattr(self, f"var_{key}", var) # 將變數儲存到 self

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

        speed_control_frame = ttk.LabelFrame(scrollable_frame, text="速率曲線控制")
        speed_control_frame.pack(fill=tk.X, padx=10, pady=10)
        self.speed_control_graph = SpeedControlGraph(speed_control_frame, on_change_callback=self.preview_simulation, height=80)
        self.speed_control_graph.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(scrollable_frame, text="刪除選取", command=self.delete_selected).pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press); self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release); self.canvas.bind("<Double-1>", self.on_canvas_double_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion); self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.bind("<Escape>", self.cancel_creation_mode)

    # --- 【新】方法: 更新畫布顯示 ---
    def update_display(self):
        # 更新背景顏色
        self.canvas.config(bg=self.background_color_str.get())
        self.bg_preview.config(bg=self.background_color_str.get())

        # 更新導體可見性
        conductor_state = 'normal' if self.show_conductors.get() else 'hidden'
        for shape in self.shapes:
            self.canvas.itemconfig(shape.id, state=conductor_state)
            # 選取框和控制點也需要同步
            if shape.outline_id:
                self.canvas.itemconfig(shape.outline_id, state=conductor_state)
            for handle in shape.handles:
                self.canvas.itemconfig(handle, state=conductor_state)

        # 更新圖片可見性
        image_state = 'normal' if self.show_images.get() else 'hidden'
        for image in self.images:
            self.canvas.itemconfig(image.id, state=image_state)
            # 選取框和控制點也需要同步
            if image.outline_id:
                self.canvas.itemconfig(image.outline_id, state=image_state)
            for handle in image.handles.values():
                self.canvas.itemconfig(handle, state=image_state)

    # --- 【新】方法: 選擇主畫布背景顏色 ---
    def _choose_main_bg_color(self):
        color_code = colorchooser.askcolor(title="選擇背景顏色", initialcolor=self.background_color_str.get())
        if color_code and color_code[1]:
            self.background_color_str.set(color_code[1])
            self.update_display()

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
            self.images.append(image_obj)
            self.select_item(image_obj)
            self.update_display() # 確保新圖片符合顯示設定
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
        
        # 【修改】點選前先確認物件是否可見
        all_items = []
        if self.show_images.get():
            all_items.extend(self.images)
        if self.show_conductors.get():
            all_items.extend(self.shapes)

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
                # 【新增】拖動控制點時即時預覽電弧
                if 'arc' in self.sim_params:
                    if hasattr(self, '_preview_job'):
                        self.after_cancel(self._preview_job)
                    self._preview_job = self.after(50, self.preview_simulation)

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
            if shape: 
                self.shapes.append(shape)
                self.select_item(shape)
                self.update_display() # 確保新導體符合顯示設定
            self.add_shape_mode, self.is_creating_rod = None, False
        self.drag_data.clear()

    def on_canvas_double_click(self, event):
        if self.is_creating_arbitrary_shape: self.finalize_arbitrary_shape(); return
        # 【修改】只在可見的導體中尋找
        if self.show_conductors.get():
            item_found = next((s for s in reversed(self.shapes) if s.contains(event.x, event.y)), None)
            if item_found and hasattr(item_found, 'voltage'):
                self.select_item(item_found)
                ParameterDialog(self, f"設定 {item_found.shape_type} 參數", item_found)

    def finalize_arbitrary_shape(self):
        if not self.is_creating_arbitrary_shape or len(self.current_polygon_points) < 3:
            messagebox.showwarning("創建錯誤", "一個有效的封閉導體至少需要3個頂點。"); self.cancel_creation_mode(); return
        shape = ArbitraryShape(self.canvas, self.current_polygon_points.copy())
        self.shapes.append(shape)
        self.cancel_creation_mode()
        self.select_item(shape)
        self.update_display() # 確保新導體符合顯示設定

    def select_item(self, item):
        if self.selected_item and self.selected_item != item: self.selected_item.deselect()
        if item and self.selected_item != item: 
            item.select()
            self.selected_item = item
        elif not item: 
            if self.selected_item:
                self.selected_item.deselect()
            self.selected_item = None
        self.update_display() # 確保選取框也更新

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
        # 【修改】執行模擬時，所有UI上的設定值 (sim_params, 顯示與否, 背景色) 都會自然保留
        # 因為它們是 self 的屬性，這個方法不會重置它們
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
                self.speed_control_graph.reset(self.total_frames)
                self.preview_simulation()
            else:
                self.total_frames = 0
                self.speed_control_graph.reset(0)
        else:
            messagebox.showinfo("模擬資訊", "在目前的佈局和電壓設定下，沒有物體之間的電位梯度超過觸發閾值。")
            self.total_frames = 0
            if self.speed_control_graph:
                self.speed_control_graph.reset(0)

    def preview_simulation(self):
        if not self.last_simulation_data:
            self.clear_simulation()
            return

        self.clear_simulation()
        points = self.speed_control_graph.get_points()
        self.animation_frame_map = self._build_frame_map(points, self.total_frames)
        if not self.animation_frame_map:
            return

        appearance_params = self._get_current_appearance_params()
        self.arc_renderer = ArcRenderer(self.canvas, appearance_params)
        self.animation_frame_index = 0
        self.last_preview_frame_index = -1
        self.play_simulation_animation()

    def play_simulation_animation(self):
        if self.animation_frame_index < len(self.animation_frame_map):
            original_frame_index = self.animation_frame_map[self.animation_frame_index]
            frames_to_render = range(self.last_preview_frame_index + 1, original_frame_index + 1)
            for frame_idx_to_draw in frames_to_render:
                if frame_idx_to_draw < len(self.last_simulation_data):
                     frame_data = self.last_simulation_data[frame_idx_to_draw]
                     self.arc_renderer.render_frame_data(frame_data)
            self.last_preview_frame_index = original_frame_index
            self.raise_top_images()
            self.animation_frame_index += 1
            self.animation_job = self.after(15, self.play_simulation_animation)
        else:
            self.animation_job = None

    def clear_simulation(self):
        if self.animation_job: self.after_cancel(self.animation_job); self.animation_job = None
        self.canvas.delete("arc")

    def clear_all(self):
        self.clear_simulation()
        self.last_simulation_data = None
        self.select_item(None)
        for item in self.shapes + self.images: 
            item.deselect()
            self.canvas.delete(item.id)
        self.shapes.clear()
        self.images.clear()
        
        # 重置顯示設定
        self.show_conductors.set(True)
        self.show_images.set(True)
        self.background_color_str.set(BACKGROUND_COLOR)
        self.update_display()

        self.total_frames = 0
        if self.speed_control_graph:
            self.speed_control_graph.reset(0)

    def _build_frame_map(self, points, total_original_frames):
        if not points or total_original_frames == 0: return []
        points.sort(key=lambda p: p[0])
        def get_speed_at_frame(frame_num):
            time_percent = frame_num / total_original_frames
            if time_percent <= points[0][0]: return points[0][1]
            if time_percent >= points[-1][0]: return points[-1][1]
            for i in range(len(points) - 1):
                if points[i][0] <= time_percent <= points[i+1][0]:
                    p1, p2 = points[i], points[i+1]
                    break
            else: return 1.0
            time_range = p2[0] - p1[0]
            if time_range == 0: return p1[1]
            local_percent = (time_percent - p1[0]) / time_range
            speed_range = p2[1] - p1[1]
            return p1[1] + local_percent * speed_range
        frame_map, time_in_original_frames = [], 0.0
        while time_in_original_frames < total_original_frames:
            frame_map.append(int(round(time_in_original_frames)))
            speed = get_speed_at_frame(time_in_original_frames)
            time_in_original_frames += max(0.1, speed)
        final_map, seen = [], set()
        for frame in frame_map:
            if frame < total_original_frames and frame not in seen:
                final_map.append(frame)
                seen.add(frame)
        if total_original_frames > 0 and total_original_frames - 1 not in seen:
            final_map.append(total_original_frames - 1)
        return final_map


if __name__ == "__main__":
    app = App()
    app.mainloop()
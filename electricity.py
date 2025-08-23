import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
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

# --- 模擬器 (V8.0 - 動態消散模型) ---
class Simulator:
    # --- 【修改】 --- 新增 final_jump_distance 參數
    def __init__(self, master, canvas, all_shapes,
                 fork_chance=0.015,
                 path_interruption_chance=0.005,
                 step_length=5,
                 probe_count=15,
                 probe_angle=120,
                 field_exponent=2.0,
                 final_jump_distance=30.0,
                 arc_threshold=150.0): # --- 【修改】 --- 新增 arc_threshold
        self.master = master
        self.canvas = canvas
        self.all_shapes = all_shapes
        self.target_shapes = []
        self.target_points = {} # --- 【新增】 --- 用於緩存目標點位，提高效率
        
        self.active_arcs = []
        self.is_running = False

        self.fork_chance = fork_chance
        self.path_interruption_chance = path_interruption_chance
        self.step_length = step_length
        self.probe_count = probe_count
        self.probe_angle_rad = math.radians(probe_angle)
        self.field_exponent = field_exponent
        self.final_jump_distance = final_jump_distance
        self.arc_threshold = arc_threshold # --- 【新增】 ---

    def _calculate_electric_field_at(self, p_x, p_y):
        total_ex, total_ey = 0.0, 0.0
        
        for shape in self.all_shapes:
            # 使用一個簡化的點電荷模型
            charge_points = shape.get_emission_points()

            if not charge_points: continue
            
            # 簡化處理：將總電壓均分給每個點
            point_voltage = shape.voltage / len(charge_points)

            for (cx, cy) in charge_points:
                dx, dy = p_x - cx, p_y - cy
                dist_sq = dx*dx + dy*dy
                
                if dist_sq < 1.0: continue # 避免在點內部計算導致無窮大
                
                inv_dist_cubed = dist_sq**(-1.5)
                ex = point_voltage * dx * inv_dist_cubed
                ey = point_voltage * dy * inv_dist_cubed
                
                total_ex += ex
                total_ey += ey
                
        return total_ex, total_ey

    def start(self, arc_jobs):
        if not arc_jobs:
            print("警告：沒有符合放電條件的物體配對。")
            return
        
        self.target_shapes = list(set(job['target'] for job in arc_jobs))
        self.active_arcs = []
        
        # --- 【新增】 --- 預先計算所有目標的表面點，避免在迴圈中重複計算
        self.target_points.clear()
        for shape in self.target_shapes:
            self.target_points[shape] = shape.get_emission_points()
        # --- 【新增結束】 ---

        for job in arc_jobs:
            source = job['source']
            possible_starts = source.get_emission_points()
            best_start_point = None
            max_field_strength_sq = -1

            if not possible_starts: continue

            # 從電場最強的點開始放電
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
                    'current': best_start_point, 
                    'direction': initial_direction
                })

        if not self.active_arcs:
            messagebox.showwarning("模擬錯誤", "找不到任何有效的放電起始點。")
            return
            
        self.is_running = True
        self.step()

    def stop(self):
        self.is_running = False

    def _get_next_point(self, current_point, current_direction):
        base_angle = math.atan2(current_direction[1], current_direction[0])
        
        probes = []
        weights = []

        for i in range(self.probe_count):
            angle_offset = (i / (self.probe_count - 1) - 0.5) * self.probe_angle_rad if self.probe_count > 1 else 0
            angle = base_angle + angle_offset
            
            probe_x = current_point[0] + self.step_length * math.cos(angle)
            probe_y = current_point[1] + self.step_length * math.sin(angle)
            
            ex, ey = self._calculate_electric_field_at(probe_x, probe_y)
            
            # 投影電場到探測方向上，作為權重
            field_projection = ex * math.cos(angle) + ey * math.sin(angle)
            
            if field_projection > 0:
                probes.append(((probe_x, probe_y), (math.cos(angle), math.sin(angle))))
                weights.append(field_projection ** self.field_exponent)
        
        if not weights or sum(weights) == 0:
            return None, None # 沒有找到前進方向

        # 加權隨機選擇下一步
        chosen_probe, chosen_direction = random.choices(probes, weights=weights, k=1)[0]
        
        return chosen_probe, chosen_direction

    def step(self):
        if not self.is_running or not self.active_arcs:
            self.stop()
            return

        next_active_arcs = []
        for arc_data in self.active_arcs:
            current_point = arc_data['current']
            current_direction = arc_data['direction']
            
            # --- 【修改】 --- 根據電場強度動態計算中斷機率
            # 電場越弱，電弧越容易在空氣中消散
            ex, ey = self._calculate_electric_field_at(*current_point)
            field_strength = math.hypot(ex, ey)
            
            # 當電場強度為0時，消散機率為 path_interruption_chance
            # 當電場強度增加時，消散機率以指數方式下降
            # 調整分母中的常數可以控制衰減速度 (0.3 是一個經驗值)
            decay_factor = self.arc_threshold * 0.3
            # 避免 arc_threshold 為 0 或過小導致除以零
            if decay_factor < 1e-6:
                dynamic_interruption_chance = 1.0 if field_strength < 1e-6 else 0.0
            else:
                dynamic_interruption_chance = self.path_interruption_chance * math.exp(-field_strength / decay_factor)

            if random.random() < dynamic_interruption_chance:
                continue
            
            # --- 【新增】 --- 最終跳躍邏輯
            jump_occurred = False
            if self.final_jump_distance > 0:
                min_dist_sq = self.final_jump_distance ** 2
                closest_point = None

                for shape in self.target_shapes:
                    for p in self.target_points.get(shape, []): # 使用快取的點
                        dist_sq = (current_point[0] - p[0])**2 + (current_point[1] - p[1])**2
                        if dist_sq < min_dist_sq:
                            min_dist_sq = dist_sq
                            closest_point = p
                
                if closest_point:
                    # 找到了一個在跳躍距離內的點，直接連接並終止此電弧
                    self.canvas.create_line(*current_point, *closest_point, fill=ARC_COLOR, width=3, tags="arc")
                    jump_occurred = True
            
            if jump_occurred:
                continue # 此電弧已完成，處理下一個
            # --- 【新增結束】 ---

            # 如果已經到達目標或超出邊界，則停止
            if any(t.contains(*current_point) for t in self.target_shapes) or \
               not (0 < current_point[0] < self.canvas.winfo_width() and \
                    0 < current_point[1] < self.canvas.winfo_height()):
                continue

            # 正常前進一步
            next_point, next_direction = self._get_next_point(current_point, current_direction)
            
            if next_point is None:
                continue

            self.canvas.create_line(*current_point, *next_point, fill=ARC_COLOR, width=2, tags="arc")
            next_active_arcs.append({'current': next_point, 'direction': next_direction})

            # 隨機分岔
            if random.random() < self.fork_chance:
                fork_point, fork_direction = self._get_next_point(current_point, current_direction)
                if fork_point:
                    self.canvas.create_line(*current_point, *fork_point, fill=ARC_COLOR, width=1, tags="arc")
                    next_active_arcs.append({'current': fork_point, 'direction': fork_direction})

        self.active_arcs = next_active_arcs
        if self.active_arcs:
            self.master.after(10, self.step)
        else:
            self.stop()

# --- 主應用程式 GUI ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # --- 【修改】 --- 更新標題
        self.title("進階放電模擬系統 V8.0 (動態消散模型)")
        self.geometry("1200x800")

        self.shapes, self.selected_shape = [], None
        self.simulator = None
        self.drag_data = {}

        self.add_shape_mode = None
        self.is_creating_rod = False
        self.is_creating_arbitrary_shape = False
        self.current_polygon_points = []
        self.temp_drawing_artifacts = []
        self.rubber_band_line_id = None
        self.closing_line_id = None
        
        # --- 【修改】 --- 新增 final_jump_distance 參數
        self.sim_params = {
            'fork_chance': 0.015,
            'path_interruption_chance': 0.005,
            'step_length': 5,
            'arc_threshold_v_pixel': 150.0,
            'probe_count': 15,
            'probe_angle': 120,
            'field_exponent': 2.5, # 稍微提高預設值以增強導向性
            'final_jump_distance': 30.0 # --- 【新增】 ---
        }

        self.create_widgets()

    def create_widgets(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        control_panel = tk.Frame(main_frame, width=250, bg=CONTROL_PANEL_BG, relief=tk.RIDGE, borderwidth=2)
        control_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        control_panel.pack_propagate(False)

        self.canvas = tk.Canvas(main_frame, bg=BACKGROUND_COLOR, highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        add_frame = tk.LabelFrame(control_panel, text="新增物體", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        add_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(add_frame, text="針頭", command=lambda: self.set_add_mode("Needle")).pack(fill=tk.X)
        tk.Button(add_frame, text="電棒", command=lambda: self.set_add_mode("Rod")).pack(fill=tk.X)
        tk.Button(add_frame, text="平板", command=lambda: self.set_add_mode("Plate")).pack(fill=tk.X)
        tk.Button(add_frame, text="任意形狀", command=lambda: self.set_add_mode("Arbitrary")).pack(fill=tk.X)

        param_frame = tk.LabelFrame(control_panel, text="模擬參數", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        param_frame.pack(fill=tk.X, padx=10, pady=10)

        def add_bar(label, key, frm, from_, to_, resolution, fmt, row):
            tk.Label(frm, text=label, bg=CONTROL_PANEL_BG).grid(row=row, column=0, sticky="w")
            var = tk.DoubleVar(value=self.sim_params[key])
            scale = tk.Scale(frm, variable=var, from_=from_, to=to_, resolution=resolution, orient=tk.HORIZONTAL,
                             length=120, showvalue=0, bg=CONTROL_PANEL_BG)
            scale.grid(row=row, column=1)
            val_label = tk.Label(frm, text=fmt.format(self.sim_params[key]), bg=CONTROL_PANEL_BG, width=6, anchor='w')
            val_label.grid(row=row, column=2)
            def on_change(val):
                self.sim_params[key] = float(val)
                val_label.config(text=fmt.format(float(val)))
            scale.config(command=on_change)
        
        add_bar("觸發閾(V/px)", 'arc_threshold_v_pixel', param_frame, 1, 500, 1, "{:.0f}", 0)
        add_bar("分岔機率", 'fork_chance', param_frame, 0, 0.05, 0.001, "{:.3f}", 1)
        add_bar("消散機率", 'path_interruption_chance', param_frame, 0, 0.05, 0.001, "{:.3f}", 2)
        add_bar("步長", 'step_length', param_frame, 1, 20, 1, "{:.0f}", 3)
        add_bar("探測點數量", 'probe_count', param_frame, 3, 40, 1, "{:.0f}", 4)
        add_bar("探測角度(°)", 'probe_angle', param_frame, 30, 180, 5, "{:.0f}", 5)
        add_bar("電場指數", 'field_exponent', param_frame, 1.0, 5.0, 0.1, "{:.1f}", 6)
        # --- 【新增】 --- 新增UI滑桿
        add_bar("最終跳躍(px)", 'final_jump_distance', param_frame, 0, 100, 1, "{:.0f}", 7)


        sim_frame = tk.LabelFrame(control_panel, text="模擬控制", padx=10, pady=10, bg=CONTROL_PANEL_BG)
        sim_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Button(sim_frame, text="開始模擬", command=self.start_simulation).pack(fill=tk.X, pady=5)
        tk.Button(sim_frame, text="清除電弧", command=self.clear_simulation).pack(fill=tk.X, pady=5)
        tk.Button(sim_frame, text="清除所有", command=self.clear_all).pack(fill=tk.X, pady=5)

        tk.Button(control_panel, text="刪除選取", command=self.delete_selected).pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Double-1>", self.on_canvas_double_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.bind("<Button-3>", self.cancel_creation_mode) 
        self.bind("<Escape>", self.cancel_creation_mode)

    def cancel_creation_mode(self, event=None):
        self.canvas.config(cursor="")
        self.add_shape_mode = None
        self.is_creating_rod = False
        self.drag_data.clear()

        if self.is_creating_arbitrary_shape:
            self.is_creating_arbitrary_shape = False
            for item in self.temp_drawing_artifacts: self.canvas.delete(item)
            if self.rubber_band_line_id: self.canvas.delete(self.rubber_band_line_id)
            if self.closing_line_id: self.canvas.delete(self.closing_line_id)
            self.temp_drawing_artifacts.clear()
            self.current_polygon_points.clear()
            self.rubber_band_line_id = None
            self.closing_line_id = None
        return "break"

    def set_add_mode(self, shape_type):
        self.cancel_creation_mode() 
        self.add_shape_mode = shape_type
        self.is_creating_rod = (shape_type == "Rod")
        if shape_type == "Arbitrary":
            self.is_creating_arbitrary_shape = True
            messagebox.showinfo("繪製提示", "請在畫布上點擊以放置頂點。\n點擊第一個頂點或按兩下來完成形狀。\n按右鍵或 Esc 鍵取消。")
        self.select_shape(None)
        self.canvas.config(cursor="crosshair")
        
    def on_canvas_press(self, event):
        if self.is_creating_arbitrary_shape:
            x, y = event.x, event.y
            if self.current_polygon_points and \
               math.hypot(x - self.current_polygon_points[0][0], y - self.current_polygon_points[0][1]) < HANDLE_RADIUS * 2:
                self.finalize_arbitrary_shape()
                return

            if self.current_polygon_points:
                px, py = self.current_polygon_points[-1]
                l_id = self.canvas.create_line(px, py, x, y, fill=SELECTED_OUTLINE_COLOR, width=2)
                self.temp_drawing_artifacts.append(l_id)

            self.current_polygon_points.append((x, y))
            p_id = self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=HANDLE_COLOR)
            self.temp_drawing_artifacts.append(p_id)
            return
        
        if self.add_shape_mode:
            if self.is_creating_rod:
                self.drag_data = {'x1': event.x, 'y1': event.y, 'line_id': None}
            return

        if self.selected_shape:
            handle_index = self.selected_shape.get_handle_at(event.x, event.y)
            if handle_index is not None:
                self.drag_data = {'item': self.selected_shape, 'type': 'handle', 'index': handle_index}
                return

        shape_found = next((s for s in reversed(self.shapes) if s.contains(event.x, event.y)), None)
        self.select_shape(shape_found)
        if shape_found:
            self.drag_data = {'item': shape_found, 'type': 'body', 'x': event.x, 'y': event.y}

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
            self.drag_data['line_id'] = self.canvas.create_line(
                self.drag_data['x1'], self.drag_data['y1'], event.x, event.y, 
                fill=SELECTED_OUTLINE_COLOR, width=3, dash=(4,4))
            return
            
        if 'item' in self.drag_data:
            item = self.drag_data['item']
            if self.drag_data['type'] == 'body':
                dx, dy = event.x - self.drag_data['x'], event.y - self.drag_data['y']
                item.move(dx, dy)
                if item.outline_id: item.select()
                self.drag_data['x'], self.drag_data['y'] = event.x, event.y
            elif self.drag_data['type'] == 'handle':
                item.move_handle(self.drag_data['index'], event.x, event.y)

    def on_canvas_release(self, event):
        if self.is_creating_arbitrary_shape: return

        self.canvas.config(cursor="")
        if self.add_shape_mode:
            shape = None
            if self.add_shape_mode == "Needle":
                shape = Needle(self.canvas, event.x, event.y)
            elif self.add_shape_mode == "Plate":
                shape = Plate(self.canvas, event.x, event.y)
            elif self.is_creating_rod:
                if self.drag_data.get('line_id'): self.canvas.delete(self.drag_data['line_id'])
                x1, y1 = self.drag_data['x1'], self.drag_data['y1']
                if math.hypot(event.x - x1, event.y - y1) > 10:
                    shape = Rod(self.canvas, x1, y1, event.x, event.y)
            
            if shape: self.shapes.append(shape)
            self.add_shape_mode = None
            self.is_creating_rod = False

        self.drag_data.clear()

    def on_canvas_double_click(self, event):
        if self.is_creating_arbitrary_shape:
            self.finalize_arbitrary_shape()
            return

        shape_found = next((s for s in reversed(self.shapes) if s.contains(event.x, event.y)), None)
        if shape_found:
            self.select_shape(shape_found)
            ParameterDialog(self, f"設定 {shape_found.shape_type} 參數", shape_found)
            
    def finalize_arbitrary_shape(self):
        if not self.is_creating_arbitrary_shape or len(self.current_polygon_points) < 3:
            messagebox.showwarning("創建錯誤", "一個有效的封閉導體至少需要3個頂點。")
            self.cancel_creation_mode()
            return

        shape = ArbitraryShape(self.canvas, self.current_polygon_points.copy())
        self.shapes.append(shape)
        
        self.cancel_creation_mode() 
        self.select_shape(shape) 

    def select_shape(self, shape):
        if self.selected_shape and self.selected_shape != shape:
            self.selected_shape.deselect()
        if shape:
            shape.select()
        self.selected_shape = shape

    def delete_selected(self):
        if self.selected_shape:
            shape = self.selected_shape
            self.select_shape(None)
            shape.deselect()
            self.canvas.delete(shape.id)
            self.shapes.remove(shape)

    def start_simulation(self):
        self.clear_simulation()
        
        if len(self.shapes) < 2:
            messagebox.showwarning("模擬錯誤", "需要至少兩個物體才能進行模擬。")
            return

        arc_jobs = []
        threshold = self.sim_params['arc_threshold_v_pixel']

        for shape_a, shape_b in itertools.combinations(self.shapes, 2):
            delta_v = abs(shape_a.voltage - shape_b.voltage)
            center_a = shape_a.get_center()
            center_b = shape_b.get_center()
            distance = math.hypot(center_a[0] - center_b[0], center_a[1] - center_b[1])

            if distance < 1.0: continue
            potential_gradient = delta_v / distance
            
            if potential_gradient > threshold:
                source, target = (shape_a, shape_b) if shape_a.voltage > shape_b.voltage else (shape_b, shape_a)
                arc_jobs.append({'source': source, 'target': target})

        if arc_jobs:
            # --- 【修改】 --- 傳入新的參數
            self.simulator = Simulator(
                self, self.canvas, self.shapes,
                fork_chance=self.sim_params['fork_chance'],
                path_interruption_chance=self.sim_params['path_interruption_chance'],
                step_length=int(self.sim_params['step_length']),
                probe_count=int(self.sim_params['probe_count']),
                probe_angle=self.sim_params['probe_angle'],
                field_exponent=self.sim_params['field_exponent'],
                final_jump_distance=self.sim_params['final_jump_distance'],
                arc_threshold=self.sim_params['arc_threshold_v_pixel'] # --- 【新增】 ---
            )
            self.simulator.start(arc_jobs)
        else:
            messagebox.showinfo("模擬資訊", "在目前的佈局和電壓設定下，沒有物體之間的電位梯度超過觸發閾值。")


    def clear_simulation(self):
        if self.simulator: self.simulator.stop()
        self.simulator = None
        self.canvas.delete("arc")

    def clear_all(self):
        self.clear_simulation()
        for shape in self.shapes:
            shape.deselect()
            self.canvas.delete(shape.id)
        self.shapes.clear()
        self.select_shape(None)

if __name__ == "__main__":
    app = App()
    app.mainloop()
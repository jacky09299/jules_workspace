import heapq
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk
from src.core.node_base import Node
from src.core.datatypes import DataType
from src.gui.dialogs import PointSelectorDialog
import tkinter as tk

class ImageToGridNode(Node):
    def __init__(self):
        super().__init__("圖片轉方格 (Img->Grid)")
        self.add_input("Image", DataType.IMAGE)
        self.add_output("Grid", DataType.GRID) # 0=Walkable, 1=Obstacle
        self.add_output("Start", DataType.ANY) # Start Point
        self.add_output("End", DataType.ANY)   # End Point
        self.parameters = {
            "threshold": 200, # Higher threshold = Safer (Dark gray is obstacle)
            "filter_radius": 3, # New: MinFilter radius to expand obstacles/remove noise
            "select_points_action": "點選起點/終點 (Select Points)",
            "start_x": 0, "start_y": 0,
            "end_x": 0, "end_y": 0
        }

    def select_points(self):
        # Always attempt to pull latest from upstream
        # This fixes "Stale Image" when user changes input file but hasn't clicked Run
        if len(self.inputs) > 0 and self.inputs[0].connected_ports:
            upstream_node = self.inputs[0].connected_ports[0].node
            print(f"DEBUG ImageToGrid: Auto-refreshing upstream node {upstream_node.title}")
            try:
                upstream_node.execute()
            except Exception as e:
                print(f"Error executing upstream node: {e}")
                # Don't popup error yet, maybe just log? 
                # Or continue and see if we have cached data?
        
        img = self.get_input_value(0)
        
        if img is None:
            print("No image available. Please run graph or connect input.")
            import tkinter.messagebox
            tkinter.messagebox.showwarning("No Image", "No image input found.\nPlease connect an Image Input node and load an image.")
            return

        root = tk._default_root
        dlg = PointSelectorDialog(root, img)
        root.wait_window(dlg)
        
        if dlg.result:
            start, end = dlg.result
            print(f"Dialog Returned: Start={start}, End={end}")
            
            # No resizing, so direct mapping
            gsx, gsy = int(start[0]), int(start[1])
            gex, gey = int(end[0]), int(end[1])
            
            self.parameters["start_x"] = gsx
            self.parameters["start_y"] = gsy
            self.parameters["end_x"] = gex
            self.parameters["end_y"] = gey
            
            print(f"Selected Points (Full Res): Start=({gsx},{gsy}), End=({gex},{gey})")
            print("Parameters updated. Please Click RUN to propagate.")

    def execute(self):
        img = self.get_input_value(0)
        if img is None:
            print("ImageToGrid: No input image.")
            self.set_output_value(0, None)
            self.set_output_value(1, None)
            self.set_output_value(2, None)
            return

        # 1. No Resize - Use Full Resolution
        # 2. Grayscale
        gray = img.convert("L")

        # 3. MinFilter (Erosion) to expand obstacles / count neighbors
        rad = int(self.parameters.get("filter_radius", 3))
        if rad > 0:
            print(f"DEBUG ImageToGrid: Applying MinFilter with radius {rad}")
            gray = gray.filter(ImageFilter.MinFilter(rad))

        # 4. Threshold
        thresh = int(self.parameters["threshold"])
        arr = np.array(gray)
        grid = np.zeros_like(arr, dtype=int)

        # Mark obstacles
        grid[arr < thresh] = 1
        
        w, h = img.size

        self.set_output_value(0, grid)
        
        # Output Start/End
        start_pt = (int(self.parameters.get("start_x", 0)), int(self.parameters.get("start_y", 0)))
        end_pt = (int(self.parameters.get("end_x", 0)), int(self.parameters.get("end_y", 0)))
        
        self.set_output_value(1, start_pt)
        self.set_output_value(2, end_pt)
        
        print(f"Generated Grid {w}x{h}, Obstacles: {np.sum(grid)}")
        print(f"Output Start: {start_pt}, End: {end_pt}")


class AStarNode(Node):
    def __init__(self):
        super().__init__("A* 路徑搜尋 (A-Star)")
        self.add_input("Grid", DataType.GRID)
        self.add_input("Start", DataType.ANY) # Expected tuple (x, y)
        self.add_input("End", DataType.ANY)   # Expected tuple (x, y)

        self.add_output("Path", DataType.PATH)

        self.parameters = {
            "allow_diagonal": False
        }

    def execute(self):
        grid = self.get_input_value(0)
        start_pt = self.get_input_value(1)
        end_pt = self.get_input_value(2)

        if grid is None:
            print("AStar: No grid input.")
            self.set_output_value(0, None)
            return
        
        if start_pt is None or end_pt is None:
            print("AStar: Missing Start or End input.")
            self.set_output_value(0, None)
            return

        rows, cols = grid.shape
        
        # Inputs are (x, y), grid access is (row, col) = (y, x)
        sx, sy = start_pt
        ex, ey = end_pt
        
        sx, sy = int(sx), int(sy)
        ex, ey = int(ex), int(ey)

        # Validate bounds
        if not (0 <= sx < cols and 0 <= sy < rows):
            print(f"Start ({sx},{sy}) out of bounds")
            return
        if not (0 <= ex < cols and 0 <= ey < rows):
            print(f"End ({ex},{ey}) out of bounds")
            return

        start = (sy, sx) # numpy uses (row, col) i.e., (y, x)
        end = (ey, ex)

        if grid[start] == 1:
            print(f"Start {start_pt} is on obstacle!")
            self.set_output_value(0, [])
            return
        if grid[end] == 1:
            print(f"End {end_pt} is on obstacle!")
            self.set_output_value(0, [])
            return

        # Run A*
        path = self.astar(grid, start, end)

        # Convert back to (x, y) for output
        path_xy = [(c, r) for r, c in path]
        self.set_output_value(0, path_xy)
        print(f"AStar found path length: {len(path_xy)}")

    def astar(self, grid, start, end):
        # Heuristic: Manhattan
        def h(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = []
        heapq.heappush(open_set, (0, start))
        came_from = {}

        g_score = {start: 0}
        f_score = {start: h(start, end)}

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == end:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return path[::-1]

            # Neighbors
            neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)] # 4-way
            if self.parameters["allow_diagonal"]:
                neighbors += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

            for dy, dx in neighbors:
                neighbor = (current[0] + dy, current[1] + dx)

                # Check bounds
                if 0 <= neighbor[0] < grid.shape[0] and 0 <= neighbor[1] < grid.shape[1]:
                    if grid[neighbor] == 1: # Obstacle
                        continue

                    # Tentative G
                    # Dist is 1 for straight, 1.414 for diagonal
                    dist = 1 if (dy==0 or dx==0) else 1.414
                    tentative_g = g_score[current] + dist

                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score[neighbor] = tentative_g + h(neighbor, end)
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return [] # No path found

class PathOverlayNode(Node):
    def __init__(self):
        super().__init__("路徑疊圖 (Overlay)")
        self.add_input("Image", DataType.IMAGE)
        self.add_input("Path", DataType.PATH)
        self.add_output("Image", DataType.IMAGE)
        self.parameters = {
            "color": "red",
            "width": 2,
            "scale_x": 1.0, # If path is from resized grid, need to scale up
            "scale_y": 1.0
        }

    def execute(self):
        img = self.get_input_value(0)
        path = self.get_input_value(1)

        if img is None:
            print("Overlay: No base image.")
            self.set_output_value(0, None)
            return

        if not path:
            print("Overlay: No path or empty path.")
            # Pass through original image
            self.set_output_value(0, img)
            return

        # Create copy to draw on
        out_img = img.copy().convert("RGB") # Ensure RGB for colored lines
        draw = ImageDraw.Draw(out_img)
        print(f"DEBUG Overlay: Drawing path of length {len(path)} on image size {img.size}")

        # If the path was generated on a 50x50 grid but image is 500x500, we need to scale the path coordinates
        # Or simpler: The user manually sets scale in parameters.
        # Ideally, we pass metadata, but for MVP, manual param.
        # Wait, we know the resize in previous node.
        # But nodes are decoupled.
        # Let's try to auto-detect? No.
        # Let's use the parameters.

        sx = float(self.parameters["scale_x"])
        sy = float(self.parameters["scale_y"])

        # Also need to consider if grid size was 50x50, how to map to image?
        # Usually it's (img_width / grid_width).
        # User has to adjust this.

        scaled_path = [(x * sx, y * sy) for x, y in path]

        draw.line(scaled_path, fill=self.parameters["color"], width=int(self.parameters["width"]))

        # Draw start/end dots
        if scaled_path:
            r = 3
            start = scaled_path[0]
            end = scaled_path[-1]
            draw.ellipse((start[0]-r, start[1]-r, start[0]+r, start[1]+r), fill="green")
            draw.ellipse((end[0]-r, end[1]-r, end[0]+r, end[1]+r), fill="blue")

        self.set_output_value(0, out_img)
        print("Overlay applied.")

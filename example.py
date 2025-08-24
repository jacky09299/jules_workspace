import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont
import io
import numpy as np

class CanvasExporter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("畫布匯出範例 - 含透明漸層")
        self.root.geometry("800x650")
        
        # 創建畫布
        self.canvas = tk.Canvas(self.root, width=600, height=450, bg='white')
        self.canvas.pack(pady=20)
        
        # 創建一些範例圖形
        self.create_sample_content()
        
        # 匯出按鈕
        export_frame = tk.Frame(self.root)
        export_frame.pack(pady=10)
        
        tk.Button(export_frame, text="匯出高解析度PNG", 
                 command=self.export_high_resolution).pack(side=tk.LEFT, padx=5)
    
    def create_sample_content(self):
        """創建範例內容（包含透明漸層提示）"""
        # 繪製矩形
        self.canvas.create_rectangle(50, 50, 150, 100, fill='red', outline='black', width=2)
        
        # 繪製圓形
        self.canvas.create_oval(200, 50, 300, 150, fill='blue', outline='navy', width=3)
        
        # 繪製線條
        self.canvas.create_line(350, 50, 450, 150, fill='green', width=4)
        
        # 繪製文字
        self.canvas.create_text(300, 200, text="測試文字 Test Text", 
                               font=('Arial', 16, 'bold'), fill='purple')
        
        # 繪製多邊形
        points = [100, 250, 150, 200, 200, 250, 175, 300, 125, 300]
        self.canvas.create_polygon(points, fill='yellow', outline='orange', width=2)
        
        # 繪製弧形
        self.canvas.create_arc(350, 200, 450, 300, start=0, extent=180, 
                              fill='pink', outline='red', width=2)
        
        # 透明漸層區域提示（tkinter無法直接顯示，僅在匯出時生效）
        self.canvas.create_rectangle(470, 50, 570, 150, fill='lightgray', outline='gray', width=1)
        self.canvas.create_text(520, 100, text="透明\n漸層", font=('Arial', 10), fill='black')
        
        self.canvas.create_oval(50, 320, 150, 420, fill='lightblue', outline='blue', width=1)
        self.canvas.create_text(100, 370, text="漸層\n圓形", font=('Arial', 10), fill='darkblue')

    def create_gradient(self, width, height, start_color, end_color, direction='horizontal'):
        """創建漸層圖片"""
        gradient = Image.new('RGBA', (width, height))
        
        # 解析顏色
        if isinstance(start_color, str):
            if start_color.startswith('#'):
                start_color = tuple(int(start_color[i:i+2], 16) for i in (1, 3, 5)) + (255,)
            else:
                # 簡單的顏色名稱轉換
                color_map = {
                    'red': (255, 0, 0, 255), 'green': (0, 255, 0, 255), 'blue': (0, 0, 255, 255),
                    'yellow': (255, 255, 0, 255), 'purple': (128, 0, 128, 255), 'orange': (255, 165, 0, 255),
                    'pink': (255, 192, 203, 255), 'cyan': (0, 255, 255, 255)
                }
                start_color = color_map.get(start_color, (255, 255, 255, 255))
        
        if isinstance(end_color, str):
            if end_color.startswith('#'):
                end_color = tuple(int(end_color[i:i+2], 16) for i in (1, 3, 5)) + (255,)
            else:
                color_map = {
                    'red': (255, 0, 0, 255), 'green': (0, 255, 0, 255), 'blue': (0, 0, 255, 255),
                    'yellow': (255, 255, 0, 255), 'purple': (128, 0, 128, 255), 'orange': (255, 165, 0, 255),
                    'pink': (255, 192, 203, 255), 'cyan': (0, 255, 255, 255), 'transparent': (0, 0, 0, 0)
                }
                end_color = color_map.get(end_color, (255, 255, 255, 0))
        
        for i in range(width if direction == 'horizontal' else height):
            if direction == 'horizontal':
                ratio = i / width
                for j in range(height):
                    r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
                    g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
                    b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
                    a = int(start_color[3] * (1 - ratio) + end_color[3] * ratio)
                    gradient.putpixel((i, j), (r, g, b, a))
            else:  # vertical
                ratio = i / height
                for j in range(width):
                    r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
                    g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
                    b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
                    a = int(start_color[3] * (1 - ratio) + end_color[3] * ratio)
                    gradient.putpixel((j, i), (r, g, b, a))
        
        return gradient

    def create_radial_gradient(self, width, height, center_color, edge_color, center_x=None, center_y=None):
        """創建放射狀漸層"""
        if center_x is None:
            center_x = width // 2
        if center_y is None:
            center_y = height // 2
            
        gradient = Image.new('RGBA', (width, height))
        max_distance = ((width/2)**2 + (height/2)**2)**0.5
        
        # 解析顏色
        if isinstance(center_color, str):
            color_map = {
                'red': (255, 0, 0, 255), 'green': (0, 255, 0, 255), 'blue': (0, 0, 255, 255),
                'yellow': (255, 255, 0, 255), 'purple': (128, 0, 128, 255), 'orange': (255, 165, 0, 255),
                'pink': (255, 192, 203, 255), 'cyan': (0, 255, 255, 255)
            }
            center_color = color_map.get(center_color, (255, 255, 255, 255))
        
        if isinstance(edge_color, str):
            color_map = {
                'red': (255, 0, 0, 255), 'green': (0, 255, 0, 255), 'blue': (0, 0, 255, 255),
                'yellow': (255, 255, 0, 255), 'purple': (128, 0, 128, 255), 'orange': (255, 165, 0, 255),
                'pink': (255, 192, 203, 255), 'cyan': (0, 255, 255, 255), 'transparent': (0, 0, 0, 0)
            }
            edge_color = color_map.get(edge_color, (255, 255, 255, 0))
        
        for x in range(width):
            for y in range(height):
                distance = ((x - center_x)**2 + (y - center_y)**2)**0.5
                ratio = min(distance / max_distance, 1.0)
                
                r = int(center_color[0] * (1 - ratio) + edge_color[0] * ratio)
                g = int(center_color[1] * (1 - ratio) + edge_color[1] * ratio)
                b = int(center_color[2] * (1 - ratio) + edge_color[2] * ratio)
                a = int(center_color[3] * (1 - ratio) + edge_color[3] * ratio)
                
                gradient.putpixel((x, y), (r, g, b, a))
        
        return gradient

    def export_high_resolution(self):
        """方法3：高解析度匯出（含透明漸層）"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
            if not filename:
                return
            
            # 設定縮放比例
            scale = 16
            
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 創建高解析度圖片（支援透明度）
            img = Image.new('RGBA', (canvas_width * scale, canvas_height * scale), (255, 255, 255, 255))
            draw = ImageDraw.Draw(img)
            
            # 按比例放大所有圖形元素
            # 矩形
            draw.rectangle([50*scale, 50*scale, 150*scale, 100*scale], 
                          fill='red', outline='black', width=2*scale)
            
            # 圓形
            draw.ellipse([200*scale, 50*scale, 300*scale, 150*scale], 
                        fill='blue', outline='navy', width=3*scale)
            
            # 線條
            draw.line([350*scale, 50*scale, 450*scale, 150*scale], 
                     fill='green', width=4*scale)
            
            # 文字
            try:
                font = ImageFont.truetype("arial.ttf", 16*scale)
            except:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 16*scale)
                except:
                    font = ImageFont.load_default()
            draw.text((250*scale, 190*scale), "測試文字 Test Text", 
                     fill='purple', font=font)
            
            # 多邊形
            points = [(p*scale) for p in [100, 250, 150, 200, 200, 250, 175, 300, 125, 300]]
            points = [(points[i], points[i+1]) for i in range(0, len(points), 2)]
            draw.polygon(points, fill='yellow', outline='orange', width=2*scale)
            
            # === 透明漸層物體 ===
            
            # 1. 透明漸層矩形（從紅色到透明）
            gradient_rect = self.create_gradient(100*scale, 100*scale, 'red', 'transparent', 'horizontal')
            img.paste(gradient_rect, (470*scale, 50*scale), gradient_rect)
            
            # 2. 放射狀漸層圓形（從藍色中心到透明邊緣）
            gradient_circle = self.create_radial_gradient(100*scale, 100*scale, 'blue', 'transparent')
            
            # 創建圓形遮罩
            mask = Image.new('L', (100*scale, 100*scale), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, 100*scale, 100*scale], fill=255)
            
            # 應用遮罩到漸層
            gradient_circle.putalpha(mask)
            img.paste(gradient_circle, (50*scale, 320*scale), gradient_circle)
            
            # 3. 垂直漸層條（從黃色到紫色，半透明）
            gradient_bar = self.create_gradient(30*scale, 200*scale, 
                                              (255, 255, 0, 180),  # 半透明黃色
                                              (128, 0, 128, 180),   # 半透明紫色
                                              'vertical')
            img.paste(gradient_bar, (250*scale, 250*scale), gradient_bar)
            
            # 4. 對角漸層三角形
            gradient_triangle = self.create_gradient(80*scale, 80*scale, 
                                                   (255, 165, 0, 200),  # 半透明橙色
                                                   (0, 255, 255, 50),    # 很透明的青色
                                                   'horizontal')
            
            # 創建三角形遮罩
            triangle_mask = Image.new('L', (80*scale, 80*scale), 0)
            triangle_draw = ImageDraw.Draw(triangle_mask)
            triangle_points = [(0, 80*scale), (80*scale, 80*scale), (40*scale, 0)]
            triangle_draw.polygon(triangle_points, fill=255)
            
            gradient_triangle.putalpha(triangle_mask)
            img.paste(gradient_triangle, (400*scale, 280*scale), gradient_triangle)
            
            # 5. 多層透明漸層重疊效果
            overlay1 = self.create_gradient(150*scale, 80*scale, 
                                          (255, 0, 0, 100),    # 透明紅色
                                          (0, 0, 255, 100),     # 透明藍色
                                          'horizontal')
            img.paste(overlay1, (300*scale, 350*scale), overlay1)
            
            overlay2 = self.create_gradient(150*scale, 80*scale, 
                                          (0, 255, 0, 100),    # 透明綠色
                                          (255, 255, 0, 100),   # 透明黃色
                                          'vertical')
            # 建立一個臨時圖像來混合
            temp_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
            temp_img.paste(overlay2, (320*scale, 370*scale), overlay2)
            img = Image.alpha_composite(img, temp_img)
            
            # 轉換為RGB並儲存（保持白色背景）
            final_img = Image.new('RGB', img.size, 'white')
            final_img.paste(img, mask=img)
            
            # 儲存高解析度圖片
            final_img.save(filename, 'PNG', dpi=(600, 600))
            messagebox.showinfo("成功", f"含透明漸層的高解析度圖片已匯出至: {filename}")
            
        except Exception as e:
            messagebox.showerror("錯誤", f"匯出失敗: {str(e)}")
    
    def run(self):
        self.root.mainloop()

# 使用範例
if __name__ == "__main__":
    app = CanvasExporter()
    app.run()
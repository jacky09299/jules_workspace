import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

class PointSelectorDialog(tk.Toplevel):
    def __init__(self, parent, image, current_start=None, current_end=None):
        super().__init__(parent)
        self.title("Select Start/End Points")
        self.geometry("800x600")
        
        self.original_image = image
        self.start_point = current_start
        self.end_point = current_end
        
        self.result = None
        
        # UI Layout
        self.create_widgets()
        self.draw_image()
        self.draw_points()

    def create_widgets(self):
        # Toolbar
        toolbar = tk.Frame(self, bg="#f0f0f0")
        toolbar.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        tk.Label(toolbar, text="Left Click: Set Start (Green) | Right Click: Set End (Red)", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)
        
        btn_frame = tk.Frame(toolbar)
        btn_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(btn_frame, text="Confirm", command=self.on_confirm, bg="#ddffdd").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Canvas Area
        self.canvas_frame = tk.Frame(self)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        self.h_bar = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.v_bar = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#333333",
                                xscrollcommand=self.h_bar.set,
                                yscrollcommand=self.v_bar.set)
        
        self.h_bar.config(command=self.canvas.xview)
        self.v_bar.config(command=self.canvas.yview)
        
        self.h_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bindings
        self.canvas.bind("<Button-1>", self.on_click_left)
        self.canvas.bind("<Button-3>", self.on_click_right)

    def draw_image(self):
        if not self.original_image:
            return
            
        self.tk_image = ImageTk.PhotoImage(self.original_image)
        self.canvas.create_image(0, 0, image=self.tk_image, anchor="nw")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def draw_points(self):
        self.canvas.delete("points")
        r = 5
        
        if self.start_point:
            x, y = self.start_point
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#00ff00", outline="black", tags="points")
            self.canvas.create_text(x, y-10, text="Start", fill="#00ff00", font=("Arial", 10, "bold"), tags="points")
            
        if self.end_point:
            x, y = self.end_point
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="#ff0000", outline="black", tags="points")
            self.canvas.create_text(x, y-10, text="End", fill="#ff0000", font=("Arial", 10, "bold"), tags="points")

    def on_click_left(self, event):
        # Set Start
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.start_point = (x, y)
        self.draw_points()

    def on_click_right(self, event):
        # Set End
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        self.end_point = (x, y)
        self.draw_points()

    def on_confirm(self):
        if self.start_point and self.end_point:
            self.result = (self.start_point, self.end_point)
            self.destroy()
        else:
            messagebox.showwarning("Incomplete", "Please select both Start and End points.")

    def on_cancel(self):
        self.result = None
        self.destroy()

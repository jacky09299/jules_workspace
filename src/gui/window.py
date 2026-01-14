import tkinter as tk
from tkinter import ttk, filedialog
from src.gui.canvas import NodeCanvas
from src.gui.properties import PropertyPanel
# We will import modules later when we have them
# from src.core.project import Project

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("模組化演算法面板 (Modular Algorithm Panel)")
        self.geometry("1200x800")

        # Configure grid layout
        self.columnconfigure(1, weight=1) # Canvas takes most space
        self.rowconfigure(0, weight=1)

        # 1. Toolbar (Top)
        self.create_toolbar()

        # 2. Sidebar (Left) - Node Palette
        self.create_sidebar()

        # 3. Canvas (Center)
        self.canvas_frame = tk.Frame(self, bg="#2b2b2b")
        self.canvas_frame.grid(row=0, column=1, sticky="nsew")

        self.node_canvas = NodeCanvas(self.canvas_frame, self)
        self.node_canvas.pack(fill=tk.BOTH, expand=True)

        # 4. Property Panel (Right)
        self.property_panel = PropertyPanel(self)
        self.property_panel.grid(row=0, column=2, sticky="ns", padx=2)

    def create_toolbar(self):
        # Menu bar or top frame
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="開啟專案 (Open)", command=self.open_project)
        file_menu.add_command(label="儲存專案 (Save)", command=self.save_project)
        file_menu.add_separator()
        file_menu.add_command(label="離開 (Exit)", command=self.quit)
        menubar.add_cascade(label="檔案 (File)", menu=file_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="執行 (Run)", command=self.run_graph)
        menubar.add_cascade(label="執行 (Run)", menu=run_menu)

        self.config(menu=menubar)

    def create_sidebar(self):
        sidebar = tk.Frame(self, width=200, bg="#f0f0f0")
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.pack_propagate(False) # Prevent shrinking

        label = tk.Label(sidebar, text="模組庫 (Modules)", font=("Arial", 12, "bold"))
        label.pack(pady=10)

        # List of available nodes
        node_types = [
            ("輸入: 圖片 (Input Image)", "InputImageNode"),
            ("循環: 開始 (Loop Start)", "LoopStartNode"),
            ("循環: 結束 (Loop End)", "LoopEndNode"),
            ("處理: 文字 (String Fmt)", "StringFormatNode"),
            ("轉換: 圖片轉二值 (Img->Grid)", "ImageToGridNode"),
            ("演算法: A* (A-Star)", "AStarNode"),
            ("轉換: 路徑疊圖 (Path Overlay)", "PathOverlayNode"),
            ("執行: 儲存 (Save)", "SaveNode"),
            ("執行: 合併 (Merge)", "MergeFilesNode"),
            ("檢視: 資料 (Viewer)", "DataViewerNode"),
            ("自訂: Python 腳本 (Script)", "CustomScriptNode")
        ]

        for text, node_class_name in node_types:
            btn = ttk.Button(sidebar, text=text, command=lambda n=node_class_name: self.add_node(n))
            btn.pack(fill=tk.X, padx=5, pady=2)

    def add_node(self, node_class_name):
        # Delegate to canvas to add node
        # We need a factory or registry later.
        self.node_canvas.add_node_by_name(node_class_name)

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Project", "*.json")])
        if path:
            from src.core.project import ProjectManager
            pm = ProjectManager(self.node_canvas)
            pm.load_project(path)

    def save_project(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Project", "*.json")])
        if path:
            from src.core.project import ProjectManager
            pm = ProjectManager(self.node_canvas)
            pm.save_project(path)

    def run_graph(self):
        print("Run Graph clicked")
        self.node_canvas.run_graph()

if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()

import tkinter as tk
from src.core.node_base import Node, Port
from src.core.datatypes import DataType

class NodeWidget:
    """
    Visual representation of a Node on the Canvas.
    Drawing is done using Canvas primitives (create_rectangle, etc.)
    but managed by this class.
    """
    def __init__(self, canvas: tk.Canvas, node: Node, x: int, y: int):
        self.canvas = canvas
        self.node = node
        self.x = x
        self.y = y
        self.width = 160
        self.header_height = 30
        self.item_height = 20
        self.height = self.calculate_height()

        self.main_id = None
        self.header_id = None
        self.title_id = None
        self.port_ids = {} # map id -> Port object

        self.draw()

    def calculate_height(self):
        max_ports = max(len(self.node.inputs), len(self.node.outputs))
        return self.header_height + (max_ports * self.item_height) + 10

    def draw(self):
        # Body
        self.main_id = self.canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.height,
            fill="#3c3c3c", outline="#111111", width=2, tags=("node", self.node.id)
        )

        # Header
        self.header_id = self.canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.header_height,
            fill="#555555", outline="#111111", width=1, tags=("node", self.node.id)
        )

        # Title
        self.title_id = self.canvas.create_text(
            self.x + 10, self.y + 15, text=self.node.title, fill="white", anchor="w",
            font=("Arial", 10, "bold"), tags=("node", self.node.id)
        )

        # Inputs
        y_offset = self.header_height + 10
        for port in self.node.inputs:
            self.draw_port(port, self.x, self.y + y_offset, is_input=True)
            y_offset += self.item_height

        # Outputs
        y_offset = self.header_height + 10
        for port in self.node.outputs:
            self.draw_port(port, self.x + self.width, self.y + y_offset, is_input=False)
            y_offset += self.item_height

    def draw_port(self, port: Port, x, y, is_input):
        r = 5
        color = self.get_color_for_type(port.data_type)

        # Socket circle
        pid = self.canvas.create_oval(
            x - r, y - r, x + r, y + r,
            fill=color, outline="black", tags=("port", port.id, self.node.id)
        )
        self.port_ids[pid] = port

        # Label
        label_x = x + 10 if is_input else x - 10
        anchor = "w" if is_input else "e"
        self.canvas.create_text(
            label_x, y, text=port.name, fill="#cccccc", anchor=anchor, font=("Arial", 8),
            tags=("node", self.node.id)
        )

        # Store absolute position for connection drawing
        # We attach it to the port object for convenience
        port.x = x
        port.y = y

    def get_color_for_type(self, data_type: DataType):
        mapping = {
            DataType.ANY: "white",
            DataType.IMAGE: "cyan",
            DataType.GRID: "orange",
            DataType.PATH: "lime",
            DataType.TEXT: "yellow",
            DataType.JSON: "magenta",
            DataType.NUMPY_ARRAY: "purple"
        }
        return mapping.get(data_type, "white")

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.canvas.move(self.node.id, dx, dy) # Move all items with tag=node.id

        # Update port coordinates
        # We need to recalculate them because canvas.move moves visual items, but we store logical x/y
        # actually, canvas.move is relative.
        # Let's just update the logical port positions.
        # Re-calculating logic is tedious, better to just shift them.
        for port in self.node.inputs + self.node.outputs:
             # This is a bit hacky, normally we'd query the canvas coords
             # But we can just track it manually
             port.x += dx
             port.y += dy

    def contains(self, x, y):
        # Helper to check if click is inside (basic AABB)
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

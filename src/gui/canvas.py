import tkinter as tk
from src.gui.node_widget import NodeWidget
# Import Node Registry or Classes (To be implemented)
# For now we will mock them in the add_node method

class NodeCanvas(tk.Canvas):
    def __init__(self, master, main_window):
        super().__init__(master, bg="#2b2b2b", highlightthickness=0)
        self.main_window = main_window

        self.nodes = [] # List of NodeWidget
        self.connections = [] # List of connection tuples or objects

        # Dragging state
        self.drag_data = {"x": 0, "y": 0, "item": None, "type": None}
        self.temp_line = None

        # Binding
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Button-3>", self.on_right_click) # Context menu or properties
        self.bind("<Delete>", self.on_delete_key)
        self.focus_set()

    def add_node_by_name(self, class_name):
        from src.nodes.inputs import InputImageNode
        from src.nodes.outputs import DataViewerNode
        from src.nodes.algorithms import ImageToGridNode, AStarNode, PathOverlayNode
        from src.nodes.execution import SaveNode, CustomScriptNode
        from src.core.node_base import Node
        from src.core.datatypes import DataType

        node = None
        if class_name == "InputImageNode":
            node = InputImageNode()
        elif class_name == "DataViewerNode":
            node = DataViewerNode()
        elif class_name == "ImageToGridNode":
            node = ImageToGridNode()
        elif class_name == "AStarNode":
            node = AStarNode()
        elif class_name == "PathOverlayNode":
            node = PathOverlayNode()
        elif class_name == "SaveNode":
            node = SaveNode()
        elif class_name == "CustomScriptNode":
            node = CustomScriptNode()
        else:
            # Fallback mock for not-yet-implemented nodes
            node = Node(title=class_name)
            node.add_input("In", DataType.ANY)
            node.add_output("Out", DataType.ANY)

        # Create Widget
        widget = NodeWidget(self, node, 50, 50)
        self.nodes.append(widget)

    def on_click(self, event):
        self.focus_set()
        # Check if clicked on a port
        # find_overlapping is better
        items = self.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)

        port_id = None
        node_tag = None

        for item in items:
            tags = self.gettags(item)
            if "port" in tags:
                port_id = tags[1] # standard: port, uuid, node_id
                break
            if "node" in tags:
                node_tag = tags[1]

        if port_id:
            # Start connection
            self.drag_data["type"] = "connection"
            self.drag_data["start_port_id"] = port_id
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.temp_line = self.create_line(event.x, event.y, event.x, event.y, fill="white", dash=(2,2))
            return

        if node_tag:
            # Start moving node
            self.drag_data["type"] = "move"
            self.drag_data["item"] = node_tag
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

            # Find the widget object to show properties
            for nw in self.nodes:
                if nw.node.id == node_tag:
                    self.main_window.property_panel.show_properties(nw)
                    break
            return

        # Clicked on empty space
        self.main_window.property_panel.clear()

    def on_drag(self, event):
        if self.drag_data["type"] == "move":
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]

            # Find the widget and move it
            node_id = self.drag_data["item"]
            for nw in self.nodes:
                if nw.node.id == node_id:
                    nw.move(dx, dy)
                    self.redraw_connections(nw) # Update lines attached to this node
                    break

            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y

        elif self.drag_data["type"] == "connection":
            self.coords(self.temp_line, self.drag_data["x"], self.drag_data["y"], event.x, event.y)

    def on_release(self, event):
        if self.drag_data["type"] == "connection":
            self.delete(self.temp_line)

            # Check if released on a port
            items = self.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
            end_port_id = None
            for item in items:
                tags = self.gettags(item)
                if "port" in tags:
                    end_port_id = tags[1]
                    break

            if end_port_id and end_port_id != self.drag_data["start_port_id"]:
                self.create_connection(self.drag_data["start_port_id"], end_port_id)

        self.drag_data["type"] = None
        self.drag_data["item"] = None

    def on_right_click(self, event):
        # Identify if we clicked on a node
        items = self.find_overlapping(event.x-2, event.y-2, event.x+2, event.y+2)
        node_tag = None
        for item in items:
            tags = self.gettags(item)
            if "node" in tags:
                node_tag = tags[1]
                break

        if node_tag:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="刪除 (Delete)", command=lambda: self.delete_node_by_id(node_tag))
            menu.post(event.x_root, event.y_root)

    def on_delete_key(self, event):
        # Delete currently selected node (active in property panel)
        current_node = self.main_window.property_panel.current_node
        if current_node:
            self.delete_node_by_id(current_node.id)

    def delete_node_by_id(self, node_id):
        # 1. Find NodeWidget
        nw_to_remove = None
        for nw in self.nodes:
            if nw.node.id == node_id:
                nw_to_remove = nw
                break

        if not nw_to_remove: return

        # 2. Remove Connections attached to this node
        # We need to copy the list because we'll be modifying it
        conns_to_remove = []
        for conn in self.connections:
            p1 = conn["p1"]
            p2 = conn["p2"]
            if p1.node.id == node_id or p2.node.id == node_id:
                conns_to_remove.append(conn)

        for conn in conns_to_remove:
            # Visual Remove
            self.delete(conn["line_id"])
            self.connections.remove(conn)
            # Logical Disconnect
            conn["p1"].disconnect(conn["p2"])

        # 3. Remove Node Visuals
        # All items with tag node_id are parts of the node
        self.delete(node_id) # Using the tag to delete all components (rect, text, ports)
        # However, ports have their own unique IDs as tags too, but also share the node_id tag
        # Wait, in NodeWidget.draw(), I used tags=("node", self.node.id)
        # And for ports: tags=("port", port.id, self.node.id)
        # So deleting by tag self.node.id should clear everything.

        # 4. Remove from list
        self.nodes.remove(nw_to_remove)

        # 5. Clear Property Panel if it was selected
        if self.main_window.property_panel.current_node == nw_to_remove.node:
             self.main_window.property_panel.clear()

        print(f"Deleted node {node_id}")

    def create_connection(self, port_id_1, port_id_2):
        # Logic to connect two ports
        # 1. Find the port objects
        p1 = self.find_port_by_id(port_id_1)
        p2 = self.find_port_by_id(port_id_2)

        if not p1 or not p2: return

        # 2. Validate (Input <-> Output)
        if p1.is_output == p2.is_output:
            print("Cannot connect same type ports")
            return

        # 3. Create visual line
        # Use bezier in future, straight for now
        line_id = self.create_line(p1.x, p1.y, p2.x, p2.y, fill="white", width=2)
        self.connections.append({
            "line_id": line_id,
            "p1": p1,
            "p2": p2
        })

        # 4. Logical Connection
        p1.connect(p2)
        print(f"Connected {p1.name} to {p2.name}")

    def redraw_connections(self, node_widget):
        # Update lines for a moved node
        for conn in self.connections:
            p1 = conn["p1"]
            p2 = conn["p2"]

            # Only update if one of the ports belongs to the moved node
            if p1 in node_widget.node.inputs + node_widget.node.outputs or \
               p2 in node_widget.node.inputs + node_widget.node.outputs:
                   self.coords(conn["line_id"], p1.x, p1.y, p2.x, p2.y)

    def find_port_by_id(self, pid):
        for nw in self.nodes:
            for port_id, port in nw.port_ids.items():
                if str(port.id) == str(pid) or str(port_id) == str(pid): # Check both visual ID and logic ID?
                    # The tag stored on canvas item is port.id (UUID)
                    # nw.port_ids keys are canvas item IDs (int)
                    # Wait, in draw_port I did: tags=("port", port.id, ...)
                    # And in find_overlapping I got tags[1] which is port.id
                    # So I am searching by port.id (UUID)
                    if str(port.id) == str(pid):
                        return port
        return None

    def run_graph(self):
        print("Executing Graph...")
        from src.core.engine import ExecutionEngine
        # Collect logical nodes from widgets
        logical_nodes = [nw.node for nw in self.nodes]
        engine = ExecutionEngine(logical_nodes)
        engine.run()

        # Refresh properties if selected
        if self.main_window.property_panel.current_node:
             # Find the widget for current node
             # Rerun show_properties to update values
             for nw in self.nodes:
                 if nw.node == self.main_window.property_panel.current_node:
                     self.main_window.property_panel.show_properties(nw)
                     break

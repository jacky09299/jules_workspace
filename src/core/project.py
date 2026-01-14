import json
from src.core.node_base import Node, Port
from src.core.datatypes import DataType
# We need to import all node classes to instantiate them by name
from src.nodes.inputs import InputImageNode
from src.nodes.outputs import DataViewerNode
from src.nodes.algorithms import ImageToGridNode, AStarNode, PathOverlayNode
from src.nodes.execution import SaveNode, CustomScriptNode
from src.nodes.groups import LoopGroupNode
from src.nodes.proxies import LoopInputProxyNode, LoopOutputProxyNode
from src.nodes.utils import StringFormatNode, MergeFilesNode

class ProjectManager:
    def __init__(self, node_canvas):
        self.canvas = node_canvas

    def save_project(self, filepath):
        data = {
            "nodes": [],
            "connections": []
        }

        # Save Nodes
        for nw in self.canvas.nodes:
            node_data = nw.node.to_dict()
            node_data["ui_x"] = nw.x
            node_data["ui_y"] = nw.y
            data["nodes"].append(node_data)

        # Save Connections
        for conn in self.canvas.connections:
            p1 = conn["p1"] # Usually output (Source)
            p2 = conn["p2"] # Usually input (Target)

            # Identify which is output and which is input
            source = p1 if p1.is_output else p2
            target = p2 if p1.is_output else p1

            conn_data = {
                "source_node_id": source.node.id,
                "source_port_name": source.name,
                "target_node_id": target.node.id,
                "target_port_name": target.name
            }
            data["connections"].append(conn_data)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"Project saved to {filepath}")
        except Exception as e:
            print(f"Failed to save project: {e}")

    def load_project(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Failed to load file: {e}")
            return

        # Clear current canvas
        self.canvas.delete("all")
        self.canvas.nodes = []
        self.canvas.connections = []

        id_to_node_map = {}
        id_to_input_ports = {} 
        id_to_output_ports = {} 

        # 1. Restore Nodes
        for n_data in data["nodes"]:
            cls_name = n_data["type"]

            # Factory
            node = self.create_node_instance(cls_name)
            if not node:
                print(f"Unknown node type: {cls_name}")
                continue

            # Restore state
            node.id = n_data["id"]
            node.title = n_data["title"]
            node.parameters = n_data.get("parameters", {})

            # Restore Group specific fields
            if hasattr(node, "children_ids") and "children_ids" in n_data:
                node.children_ids = n_data["children_ids"]
                node.width = n_data.get("width", 400)
                node.height = n_data.get("height", 300)

            if hasattr(node, "internal_input_node_id"):
                node.internal_input_node_id = n_data.get("internal_input_node_id")
                node.internal_output_node_id = n_data.get("internal_output_node_id")

            # Restore Exposed Parameters
            param_inputs = n_data.get("param_inputs", {})
            sorted_params = sorted(param_inputs.items(), key=lambda item: item[1])
            for param_name, idx in sorted_params:
                if param_name not in node.param_inputs:
                     node.expose_parameter(param_name)

            x = n_data.get("ui_x", 0)
            y = n_data.get("ui_y", 0)

            # Create Widget
            from src.gui.node_widget import NodeWidget
            widget = NodeWidget(self.canvas, node, x, y)
            self.canvas.nodes.append(widget)

            id_to_node_map[node.id] = node

            # Map ports
            for p in node.inputs:
                id_to_input_ports[(node.id, p.name)] = p
            for p in node.outputs:
                id_to_output_ports[(node.id, p.name)] = p

        # 2. Restore Connections
        for c_data in data["connections"]:
            sid = c_data["source_node_id"]
            spn = c_data["source_port_name"]
            tid = c_data["target_node_id"]
            tpn = c_data["target_port_name"]

            # Source is always output, Target is always input (enforced by save_project)
            source_port = id_to_output_ports.get((sid, spn))
            target_port = id_to_input_ports.get((tid, tpn))

            if source_port and target_port:
                try:
                    source_port.connect(target_port)
                    # Visual connect using correct coords
                    line_id = self.canvas.create_line(source_port.x, source_port.y, target_port.x, target_port.y, fill="white", width=2)
                    self.canvas.connections.append({
                        "line_id": line_id,
                        "p1": source_port,
                        "p2": target_port
                    })
                    print(f"Restored connection: {source_port.node.title}.{source_port.name} -> {target_port.node.title}.{target_port.name}")
                except Exception as e:
                    print(f"Error connecting loaded ports: {e}")
            else:
                 # Debug failure
                 s_debug = "Found" if source_port else "Missing"
                 t_debug = "Found" if target_port else "Missing"
                 print(f"Skipping invalid connection: {sid}.{spn} ({s_debug}) -> {tid}.{tpn} ({t_debug})")

    def create_node_instance(self, class_name):
        # Registry
        if class_name == "InputImageNode": return InputImageNode()
        if class_name == "DataViewerNode": return DataViewerNode()
        if class_name == "ImageToGridNode": return ImageToGridNode()
        if class_name == "AStarNode": return AStarNode()
        if class_name == "PathOverlayNode": return PathOverlayNode()
        if class_name == "SaveNode": return SaveNode()
        if class_name == "CustomScriptNode": return CustomScriptNode()
        if class_name == "LoopGroupNode": return LoopGroupNode()
        if class_name == "LoopInputProxyNode": return LoopInputProxyNode()
        if class_name == "LoopOutputProxyNode": return LoopOutputProxyNode()
        if class_name == "StringFormatNode": return StringFormatNode()
        if class_name == "MergeFilesNode": return MergeFilesNode()
        return None

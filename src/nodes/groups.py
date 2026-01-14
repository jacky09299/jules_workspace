from typing import List, Optional
from src.core.node_base import Node
from src.core.datatypes import DataType

class NodeGroup(Node):
    def __init__(self, title: str):
        super().__init__(title)
        self.children_ids: List[str] = [] # IDs of nodes inside this group
        self.width = 400
        self.height = 300
        self.expanded = True

    def add_child(self, node: Node):
        if node.id not in self.children_ids:
            self.children_ids.append(node.id)
            print(f"Group '{self.title}' added child '{node.title}'")

    def remove_child(self, node_id: str):
        if node_id in self.children_ids:
            self.children_ids.remove(node_id)
            print(f"Group '{self.title}' removed child {node_id}")

    def to_dict(self):
        d = super().to_dict()
        d["children_ids"] = self.children_ids
        d["width"] = self.width
        d["height"] = self.height
        return d

class LoopGroupNode(NodeGroup):
    def __init__(self):
        super().__init__("循環群組 (Loop Box)")
        self.add_input("List", DataType.ANY) # Input list
        self.add_output("Collected", DataType.ANY) # Output list

        # We need to identify the special proxy nodes inside
        self.internal_input_node_id: Optional[str] = None
        self.internal_output_node_id: Optional[str] = None

    def execute(self):
        # The execution logic is handled by the Engine specially for Groups.
        # This method might be called if treated as a normal node, but it shouldn't be.
        pass

from src.core.node_base import Node
from src.core.datatypes import DataType

class LoopInputProxyNode(Node):
    def __init__(self):
        super().__init__("迴圈項目 (Item)")
        self.add_output("Item", DataType.ANY)
        self.add_output("Index", DataType.ANY)
        self.current_value = None
        self.current_index = 0
        self.parameters["_no_delete"] = True # Prevent deletion by user

    def execute(self):
        # Just output what was set by the Group
        self.set_output_value(0, self.current_value)
        self.set_output_value(1, self.current_index)

class LoopOutputProxyNode(Node):
    def __init__(self):
        super().__init__("迴圈收集 (Collect)")
        self.add_input("Result", DataType.ANY)
        self.collected_value = None
        self.parameters["_no_delete"] = True

    def execute(self):
        # Capture the input
        self.collected_value = self.get_input_value(0)

from src.core.node_base import Node
from src.core.datatypes import DataType
from PIL import Image

class DataViewerNode(Node):
    def __init__(self):
        super().__init__("資料檢視 (Data Viewer)")
        self.add_input("Data", DataType.ANY)
        self.parameters = {
            "info": "No Data"
        }

    def execute(self):
        data = self.get_input_value(0)

        if data is None:
            self.parameters["info"] = "None"
            return

        if isinstance(data, Image.Image):
            self.parameters["info"] = f"Image: {data.size} {data.mode}"
            # In a real app, we would pop up a window or draw on canvas.
            # For now, just logging.
            print(f"Viewer received Image: {data.size}")
        elif isinstance(data, list):
             self.parameters["info"] = f"List len={len(data)}"
        else:
            self.parameters["info"] = str(data)[:50]

        print(f"Viewer State: {self.parameters['info']}")

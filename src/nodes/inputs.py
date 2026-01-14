from PIL import Image
import numpy as np
import os
from src.core.node_base import Node
from src.core.datatypes import DataType

class InputImageNode(Node):
    def __init__(self):
        super().__init__("輸入圖片 (Input Image)")
        self.add_output("Image", DataType.IMAGE)
        self.parameters = {
            "file_path": "path/to/image.png"
        }
        self.cached_image = None

    def execute(self):
        path = self.parameters.get("file_path")
        if not path or not os.path.exists(path):
            print(f"Error: File not found at {path}")
            self.set_output_value(0, None)
            return

        try:
            img = Image.open(path)
            self.cached_image = img
            self.set_output_value(0, img)
            print(f"Loaded image: {path} ({img.size})")
        except Exception as e:
            print(f"Failed to load image: {e}")
            self.set_output_value(0, None)

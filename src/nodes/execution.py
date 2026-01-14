import os
import json
from PIL import Image
from src.core.node_base import Node
from src.core.datatypes import DataType

class SaveNode(Node):
    def __init__(self):
        super().__init__("儲存檔案 (Save File)")
        self.add_input("Data", DataType.ANY)
        self.parameters = {
            "output_path": "output.txt",
            "format": "TXT" # TXT, JSON, PNG
        }

    def execute(self):
        data = self.get_input_value(0)
        path = self.parameters["output_path"]
        fmt = self.parameters["format"].upper()

        if data is None:
            print("SaveNode: No data to save.")
            import tkinter.messagebox
            tkinter.messagebox.showwarning("Save Warning", "No data to save. Check upstream connections.")
            return

        try:
            abs_path = os.path.abspath(path)
            print(f"DEBUG SaveNode: Attempting to save data type {type(data)} to {abs_path} with format {fmt}")
            
            if fmt == "PNG" or fmt == "JPG":
                if isinstance(data, Image.Image):
                    data.save(path)
                    print(f"Saved image to {path}")
                else:
                    msg = f"Error: Data is not an image, cannot save as {fmt}"
                    print(msg)
                    import tkinter.messagebox
                    tkinter.messagebox.showerror("Save Error", msg)

            elif fmt == "JSON":
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"Saved JSON to {path}")

            else: # TXT or default
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(str(data))
                print(f"Saved Text to {path}")

        except Exception as e:
            msg = f"Failed to save file: {e}"
            print(msg)
            import tkinter.messagebox
            tkinter.messagebox.showerror("Save Error", msg)

class CustomScriptNode(Node):
    def __init__(self):
        super().__init__("自訂腳本 (Script)")
        self.add_input("In1", DataType.ANY)
        self.add_input("In2", DataType.ANY)
        self.add_output("Out", DataType.ANY)

        # Default script doubles the input or prints it
        self.parameters = {
            "code": "out = in1"
        }

    def execute(self):
        in1 = self.get_input_value(0)
        in2 = self.get_input_value(1)

        # Prepare context
        local_scope = {"in1": in1, "in2": in2, "out": None, "print": print, "import": __import__}

        # Security warning: exec() is dangerous.
        # In a local desktop app for a developer tool, it's acceptable but risky.

        code = self.parameters["code"]
        try:
            exec(code, {}, local_scope)
            result = local_scope.get("out")
            self.set_output_value(0, result)
            print("Executed custom script.")
        except Exception as e:
            print(f"Script Error: {e}")
            self.set_output_value(0, None)

from src.core.node_base import Node
from src.core.datatypes import DataType
import os

class StringFormatNode(Node):
    def __init__(self):
        super().__init__("文字處理 (String Format)")
        self.add_input("Base String", DataType.TEXT)
        self.add_output("Result", DataType.TEXT)
        self.parameters = {
            "format": "{}", # Changed default to pure pass-through
            "append": "",
            "prepend": ""
        }

    def execute(self):
        base = self.get_input_value(0)
        if base is None:
            self.set_output_value(0, "")
            return

        base = str(base)
        fmt = self.parameters.get("format", "{}")

        # Simple format logic
        try:
            # If format has {}, use it.
            if "{}" in fmt:
                res = fmt.format(base)
            else:
                res = base # Fallback

            # Append/Prepend
            pre = self.parameters.get("prepend", "")
            app = self.parameters.get("append", "")

            final_res = f"{pre}{res}{app}"
            self.set_output_value(0, final_res)
            print(f"StringFormat: '{base}' -> '{final_res}'")

        except Exception as e:
            print(f"StringFormat Error: {e}")
            self.set_output_value(0, base)

class MergeFilesNode(Node):
    def __init__(self):
        super().__init__("合併檔案 (Merge Files)")
        self.add_input("File List", DataType.ANY) # List of paths
        self.add_output("Merged File", DataType.TEXT) # Path
        self.parameters = {
            "output_path": "merged_output.txt",
            "separator": "\\n---MERGE---\\n"
        }

    def execute(self):
        file_list = self.get_input_value(0)
        out_path = self.parameters["output_path"]
        sep = self.parameters["separator"].replace("\\n", "\n")

        if not file_list or not isinstance(file_list, list):
            print("MergeFiles: Input is not a valid list.")
            return

        print(f"MergeFiles: Merging {len(file_list)} files to {out_path}")

        try:
            with open(out_path, 'w', encoding='utf-8') as outfile:
                for fpath in file_list:
                    if os.path.exists(fpath):
                        with open(fpath, 'r', encoding='utf-8') as infile:
                            outfile.write(infile.read())
                            outfile.write(sep)
                    else:
                        outfile.write(f"Error: File not found {fpath}\n{sep}")

            self.set_output_value(0, out_path)
            print("MergeFiles: Done.")

        except Exception as e:
            print(f"MergeFiles Error: {e}")

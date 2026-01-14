import os
from src.core.node_base import Node
from src.core.datatypes import DataType

class LoopStartNode(Node):
    def __init__(self):
        super().__init__("循環開始 (Loop Start)")
        self.add_output("Current Item", DataType.ANY)
        self.add_output("Index", DataType.ANY) # Integer
        self.add_output("File Name", DataType.TEXT)

        self.parameters = {
            "folder_path": ".",
            "extensions": ".txt,.png,.jpg", # comma separated
            "recursive": False
        }

        self.file_list = []
        self.current_index = -1
        self.is_loop_start = True

    def execute(self):
        # If index is -1, we are starting fresh
        if self.current_index == -1:
            self.scan_files()
            self.current_index = 0

        if 0 <= self.current_index < len(self.file_list):
            item = self.file_list[self.current_index]
            print(f"LoopStart: Emitting item {self.current_index}: {item}")
            self.set_output_value(0, item)
            self.set_output_value(1, self.current_index)
            self.set_output_value(2, os.path.basename(item))
        else:
            print("LoopStart: No items or Finished.")
            self.set_output_value(0, None)

    def scan_files(self):
        path = self.parameters["folder_path"]
        exts = [e.strip().lower() for e in self.parameters["extensions"].split(",")]

        found = []
        if os.path.exists(path) and os.path.isdir(path):
            for f in os.listdir(path):
                if any(f.lower().endswith(e) for e in exts):
                    found.append(os.path.join(path, f))

        found.sort() # Deterministic order
        self.file_list = found
        print(f"LoopStart: Scanned {len(found)} files in {path}")

    def has_more_items(self):
        return self.current_index + 1 < len(self.file_list)

    def advance(self):
        self.current_index += 1
        # No need to call execute here, the engine will loop back and call execute()

    def reset(self):
        self.current_index = -1
        self.file_list = []


class LoopEndNode(Node):
    def __init__(self):
        super().__init__("循環結束 (Loop End)")
        self.add_input("Item", DataType.ANY)
        self.add_output("Collected List", DataType.ANY) # List of items

        self.collected_items = []
        self.is_loop_end = True
        self.loop_start_node = None # Cache

    def execute(self):
        # 1. Collect input
        val = self.get_input_value(0)

        # We need to know if this is a fresh run or mid-loop
        # The Engine controls the loop.
        # But we need to know when to clear 'collected_items'.
        # Implicitly: if we are at index 0 of the loop?
        # Better: get the LoopStart node and ask it.

        start_node = self.get_loop_start_node()
        if start_node:
            if start_node.current_index == 0:
                self.collected_items = [] # Reset on first item

        if val is not None:
            self.collected_items.append(val)
            print(f"LoopEnd: Collected item. Total: {len(self.collected_items)}")

        # While looping, we don't output the full list yet?
        # Or we can, it doesn't hurt.
        # self.set_output_value(0, self.collected_items)

    def finalize(self):
        print(f"LoopEnd: Finalizing. Emitting list of {len(self.collected_items)} items.")
        self.set_output_value(0, self.collected_items)

    def get_loop_start_node(self):
        if self.loop_start_node:
            return self.loop_start_node

        # Traverse upstream to find LoopStartNode
        # BFS or DFS
        visited = set()
        queue = [self]

        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            if hasattr(curr, "is_loop_start") and curr.is_loop_start:
                self.loop_start_node = curr
                return curr

            for port in curr.inputs:
                for connected in port.connected_ports:
                    queue.append(connected.node)

        return None

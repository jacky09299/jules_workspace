# Simple engine to execute the graph
# We need to find roots and traverse
from src.core.node_base import Node
import time

class ExecutionEngine:
    def __init__(self, nodes):
        self.nodes = nodes

    def run(self):
        # 1. Topological Sort
        sorted_nodes = self.topological_sort()
        print(f"DEBUG Engine: Execution Order: {[n.title for n in sorted_nodes]}")

        if not sorted_nodes:
             print("DEBUG Engine: No nodes to execute!")
             return

        # 2. Reset All Nodes (Cleanup from previous runs)
        for node in sorted_nodes:
            if hasattr(node, "reset"):
                node.reset()

        # 3. Sequential Execution with Loop Support
        idx = 0
        loop_counter = 0
        max_loops = 1000 # Safety break

        while idx < len(sorted_nodes):
            node = sorted_nodes[idx]

            # Execute the node
            print(f"DEBUG Engine: Executing {node.title}...")
            try:
                node.execute()
                # print(f"DEBUG Engine: Finished {node.title}")
            except Exception as e:
                print(f"DEBUG Engine: Error executing {node.title}: {e}")
                import traceback
                traceback.print_exc()
                try:
                    import tkinter.messagebox
                    tkinter.messagebox.showerror("Execution Error", f"Error in {node.title}:\n{e}")
                except:
                    pass
                break # Stop execution on error

            # Check for Loop End Logic
            # Duck typing check for LoopEndNode
            if hasattr(node, "is_loop_end") and node.is_loop_end:
                 # It's a Loop End Node. Check if we need to loop back.
                 start_node = node.get_loop_start_node()
                 if start_node:
                     if start_node.has_more_items():
                         print(f"DEBUG Engine: Looping back to {start_node.title}")
                         start_node.advance()

                         # Find index of start_node
                         try:
                             start_idx = sorted_nodes.index(start_node)
                             idx = start_idx
                             loop_counter += 1
                             if loop_counter > max_loops:
                                 print("DEBUG Engine: Safety break, max loops exceeded.")
                                 break
                             continue # Jump back immediately
                         except ValueError:
                             print("Error: Start node not in execution list?")
                     else:
                         # Loop finished.
                         print(f"DEBUG Engine: Loop finished for {start_node.title}")
                         node.finalize() # Collect final results

            idx += 1

    def topological_sort(self):
        # Build dependency graph
        # Node A depends on Node B if A has an input connected to B's output

        deps = {node: [] for node in self.nodes}
        for node in self.nodes:
            for input_port in node.inputs:
                for connected_port in input_port.connected_ports:
                    # connected_port is an OutputPort of another node
                    producer_node = connected_port.node
                    deps[node].append(producer_node)

        # Kahn's algorithm
        result = []

        # Calculate in-degrees
        in_degree = {node: 0 for node in self.nodes}
        for node in self.nodes:
            for parent in deps[node]:
                in_degree[node] += 1

        queue = [n for n in self.nodes if in_degree[n] == 0]

        # Deterministic order for stable tests (sort by title or ID)
        queue.sort(key=lambda n: n.title)

        while queue:
            u = queue.pop(0)
            result.append(u)

            # Find nodes v that depend on u
            # i.e., v has u in deps[v]
            neighbors = []
            for v in self.nodes:
                if u in deps[v]:
                    neighbors.append(v)

            # Sort neighbors for determinism
            neighbors.sort(key=lambda n: n.title)

            for v in neighbors:
                count = deps[v].count(u) # Should be 1 usually
                in_degree[v] -= count
                if in_degree[v] == 0:
                    queue.append(v)

        if len(result) != len(self.nodes):
            print("Cycle detected or graph error!")
            # Return partial result or raw list to avoid crash
            # If cycle, return what we have + remaining
            remaining = [n for n in self.nodes if n not in result]
            return result + remaining

        return result

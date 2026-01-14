# Simple engine to execute the graph
# We need to find roots and traverse
from src.core.node_base import Node

class ExecutionEngine:
    def __init__(self, nodes):
        self.nodes = nodes

    def run(self):
        # 1. Reset all nodes?
        # 2. Find nodes with no connected inputs (Roots)
        # OR just topological sort.

        # Simple approach:
        # Identify nodes that are ready to run (all inputs have data or no inputs)
        # But data is pulled? Or pushed?
        # My node_base `execute` calls `get_input_value` which grabs from connected port.
        # So we just need to execute in topological order.

        sorted_nodes = self.topological_sort()
        print(f"DEBUG Engine: Execution Order: {[n.title for n in sorted_nodes]}")

        if not sorted_nodes:
             print("DEBUG Engine: No nodes to execute!")

        for node in sorted_nodes:
            print(f"DEBUG Engine: Executing {node.title}...")
            try:
                node.execute()
                print(f"DEBUG Engine: Finished {node.title}")
            except Exception as e:
                print(f"DEBUG Engine: Error executing {node.title}: {e}")
                import traceback
                traceback.print_exc()
                import tkinter.messagebox
                tkinter.messagebox.showerror("Execution Error", f"Error in {node.title}:\n{e}")

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
        visited = set()

        # Find nodes with no dependencies within this set (roots)
        # Note: A node might have no inputs at all (InputNode)

        # Wait, Kahn's is better implemented by calculating in-degrees
        in_degree = {node: 0 for node in self.nodes}
        for node in self.nodes:
            for parent in deps[node]:
                in_degree[node] += 1

        queue = [n for n in self.nodes if in_degree[n] == 0]

        while queue:
            u = queue.pop(0)
            result.append(u)

            # Find nodes v that depend on u
            # i.e., v has u in deps[v]
            for v in self.nodes:
                if u in deps[v]:
                    count = deps[v].count(u)
                    in_degree[v] -= count
                    if in_degree[v] == 0:
                        queue.append(v)

        if len(result) != len(self.nodes):
            print("Cycle detected or graph error!")
            # Return partial result or raw list to avoid crash
            return result

        return result

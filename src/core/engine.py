from src.core.node_base import Node
from src.nodes.groups import LoopGroupNode
import time

class ExecutionEngine:
    def __init__(self, nodes):
        self.nodes = nodes

    def run(self, nodes_to_run=None):
        # 0. Allow running a subset (e.g., inside a Group)
        target_nodes = nodes_to_run if nodes_to_run is not None else self.nodes

        # 1. Topological Sort
        sorted_nodes = self.topological_sort(target_nodes)

        # FILTER: If running the main graph (nodes_to_run is None), exclude children of Groups.
        if nodes_to_run is None:
             # Identify all children
             all_children_ids = set()
             for n in self.nodes:
                 if hasattr(n, "children_ids"):
                     all_children_ids.update(n.children_ids)

             print(f"DEBUG Engine: Filtering children. Total children IDs found: {len(all_children_ids)}")
             # Filter
             filtered = [n for n in sorted_nodes if n.id not in all_children_ids]
             sorted_nodes = filtered

        print(f"DEBUG Engine: Execution Order: {[n.title for n in sorted_nodes]}")

        if not sorted_nodes:
             print("DEBUG Engine: No nodes to execute!")
             return

        # 2. Reset All Nodes (Cleanup from previous runs)
        if nodes_to_run is None:
            for node in sorted_nodes:
                if hasattr(node, "reset"):
                    node.reset()

        # 3. Execution
        for node in sorted_nodes:
            print(f"DEBUG Engine: Executing {node.title} (Type: {type(node).__name__})...")
            try:
                # Check for LoopGroupNode
                # We use string check to avoid import issues or just isinstance if robust
                if isinstance(node, LoopGroupNode):
                    self.execute_loop_group(node)
                else:
                    node.execute()
            except Exception as e:
                print(f"DEBUG Engine: Error executing {node.title}: {e}")
                import traceback
                traceback.print_exc()
                break

    def execute_loop_group(self, group_node: LoopGroupNode):
        print(f"DEBUG Engine: Entering Loop Group {group_node.title}")

        # 1. Get Input List
        input_list = group_node.get_input_value(0)
        if input_list is None:
             input_list = []
        elif not isinstance(input_list, list):
             input_list = [input_list]

        # 2. Identify Internal Proxies
        if not group_node.internal_input_node_id or not group_node.internal_output_node_id:
            print("LoopGroup: Internal proxies not linked.")
            return

        input_proxy = next((n for n in self.nodes if n.id == group_node.internal_input_node_id), None)
        output_proxy = next((n for n in self.nodes if n.id == group_node.internal_output_node_id), None)

        if not input_proxy or not output_proxy:
            print("LoopGroup: Could not find proxy nodes in graph.")
            return

        # 3. Identify Subgraph (Children)
        children_nodes = [n for n in self.nodes if n.id in group_node.children_ids]
        if group_node in children_nodes:
            children_nodes.remove(group_node)

        print(f"LoopGroup: Iterating {len(input_list)} items over {len(children_nodes)} children nodes.")

        collected_results = []

        # 4. Loop
        for i, item in enumerate(input_list):
            print(f"LoopGroup: Iteration {i}, Item: {item}")

            # A. Set Proxy Input
            input_proxy.current_value = item
            input_proxy.current_index = i

            # B. Execute Subgraph
            # Pass children_nodes explicitly to run() to avoid filtering them out
            # And prevent recursion loop
            sub_engine = ExecutionEngine(self.nodes)
            sub_engine.run(nodes_to_run=children_nodes)

            # C. Collect Result
            res = output_proxy.collected_value
            collected_results.append(res)
            print(f"LoopGroup: Iteration {i} Result: {res}")

        # 5. Set Group Output
        group_node.set_output_value(0, collected_results)
        print(f"LoopGroup: Finished. Collected {len(collected_results)} items.")


    def topological_sort(self, nodes):
        node_set = set(nodes)
        deps = {node: [] for node in nodes}

        for node in nodes:
            for input_port in node.inputs:
                for connected_port in input_port.connected_ports:
                    producer_node = connected_port.node
                    if producer_node in node_set:
                        deps[node].append(producer_node)

        # Kahn's algorithm
        result = []
        in_degree = {node: 0 for node in nodes}
        for node in nodes:
            for parent in deps[node]:
                in_degree[node] += 1

        queue = [n for n in nodes if in_degree[n] == 0]
        queue.sort(key=lambda n: n.title)

        while queue:
            u = queue.pop(0)
            result.append(u)

            neighbors = []
            for v in nodes:
                if u in deps[v]:
                    neighbors.append(v)
            neighbors.sort(key=lambda n: n.title)

            for v in neighbors:
                count = deps[v].count(u)
                in_degree[v] -= count
                if in_degree[v] == 0:
                    queue.append(v)

        if len(result) != len(nodes):
            # print("Cycle detected or graph error!")
            remaining = [n for n in nodes if n not in result]
            return result + remaining

        return result

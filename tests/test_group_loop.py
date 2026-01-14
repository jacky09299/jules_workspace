import unittest
import os
import shutil
from src.core.engine import ExecutionEngine
from src.nodes.groups import LoopGroupNode
from src.nodes.proxies import LoopInputProxyNode, LoopOutputProxyNode
from src.nodes.utils import StringFormatNode, MergeFilesNode
from src.nodes.execution import SaveNode
from src.core.datatypes import DataType

class TestLoopGroup(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_group_data"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)

        # Input Data
        self.input_list = ["item1", "item2", "item3"]

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_loop_group_execution(self):
        # 1. Create Group
        group = LoopGroupNode()

        # 2. Create Proxies (Manually for test, usually Canvas does this)
        in_proxy = LoopInputProxyNode()
        out_proxy = LoopOutputProxyNode()

        group.add_child(in_proxy)
        group.add_child(out_proxy)
        group.internal_input_node_id = in_proxy.id
        group.internal_output_node_id = out_proxy.id

        # 3. Create Internal Logic
        # Item -> String Format ("_processed") -> Collect
        fmt_node = StringFormatNode()
        fmt_node.parameters["append"] = "_processed"
        group.add_child(fmt_node)

        # Connect: InProxy:0 -> Fmt:0
        in_proxy.outputs[0].connect(fmt_node.inputs[0])

        # Connect: Fmt:0 -> OutProxy:0
        fmt_node.outputs[0].connect(out_proxy.inputs[0])

        # 4. Mock Input for Group

        class ListProvider(LoopInputProxyNode): # Reusing proxy class for simplicity
            def __init__(self, data):
                super().__init__()
                self.title = "Provider"
                self.data = data
            def execute(self):
                self.set_output_value(0, self.data)

        provider = ListProvider(self.input_list)
        provider.outputs[0].connect(group.inputs[0])

        # 5. Run Engine
        # We pass ALL nodes. The engine should filter out children for the top-level run.
        all_nodes = [provider, group, in_proxy, out_proxy, fmt_node]
        engine = ExecutionEngine(all_nodes)

        print("\n--- Starting Loop Group Test ---")
        engine.run()
        print("--- Finished ---")

        # 6. Verify Output
        result = group.outputs[0].value
        print(f"Group Result: {result}")

        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], "item1_processed")
        self.assertEqual(result[2], "item3_processed")

if __name__ == '__main__':
    unittest.main()

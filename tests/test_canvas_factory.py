import unittest
from src.gui.canvas import NodeCanvas
from src.gui.window import MainWindow
import tkinter as tk

class TestCanvasFactory(unittest.TestCase):
    def setUp(self):
        # We need a Tk root for UI classes
        self.root = tk.Tk()
        # Mock MainWindow (duck typing)
        self.window = MainWindow()
        self.window.withdraw() # Hide window
        self.canvas = NodeCanvas(self.root, self.window)

    def tearDown(self):
        self.window.destroy()
        self.root.destroy()

    def test_add_loop_start_node(self):
        self.canvas.add_node_by_name("LoopStartNode")
        self.assertEqual(len(self.canvas.nodes), 1)
        node = self.canvas.nodes[0].node
        self.assertEqual(node.__class__.__name__, "LoopStartNode")
        self.assertEqual(node.title, "循環開始 (Loop Start)")

    def test_add_loop_end_node(self):
        self.canvas.add_node_by_name("LoopEndNode")
        self.assertEqual(len(self.canvas.nodes), 1)
        node = self.canvas.nodes[0].node
        self.assertEqual(node.__class__.__name__, "LoopEndNode")

    def test_add_string_format_node(self):
        self.canvas.add_node_by_name("StringFormatNode")
        self.assertEqual(len(self.canvas.nodes), 1)
        node = self.canvas.nodes[0].node
        self.assertEqual(node.__class__.__name__, "StringFormatNode")

if __name__ == '__main__':
    unittest.main()

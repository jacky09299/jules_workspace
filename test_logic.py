import unittest
import os
import shutil
from src.logic import MarkItDownConverter

class TestMarkItDownConverter(unittest.TestCase):
    def setUp(self):
        self.converter = MarkItDownConverter()
        self.test_file = "test_sample.txt"
        self.output_file = "test_output.md"
        # Ensure test file exists
        if not os.path.exists(self.test_file):
            with open(self.test_file, "w") as f:
                f.write("Hello World")

    def tearDown(self):
        if os.path.exists(self.output_file):
            os.remove(self.output_file)

    def test_convert_file_basic(self):
        # Test basic conversion (text to markdown)
        try:
            content = self.converter.convert_file(self.test_file)
            self.assertIsNotNone(content)
            self.assertTrue(len(content) > 0)
        except Exception as e:
            self.fail(f"Conversion failed: {e}")

    def test_save_output(self):
        content = "# Test Header\n\nBody content."
        self.converter.save_output(content, self.output_file)
        self.assertTrue(os.path.exists(self.output_file))
        with open(self.output_file, "r") as f:
            read_content = f.read()
        self.assertEqual(content, read_content)

    def test_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.converter.convert_file("non_existent_file.txt")

if __name__ == '__main__':
    unittest.main()

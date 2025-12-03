import os
from markitdown import MarkItDown
from openai import OpenAI

class MarkItDownConverter:
    def __init__(self):
        """
        Initialize the MarkItDownConverter.
        """
        self.md = None
        self.last_config = {}

    def _initialize_markitdown(self, doc_intel_endpoint=None, llm_config=None):
        """
        Re-initialize MarkItDown if configuration changes.
        """
        current_config = {
            "doc_intel_endpoint": doc_intel_endpoint,
            "llm_config": llm_config
        }

        # Only re-initialize if configuration is different or not yet initialized
        if self.md is not None and self.last_config == current_config:
            return

        kwargs = {}

        # Configure Azure Document Intelligence
        if doc_intel_endpoint:
            kwargs["docintel_endpoint"] = doc_intel_endpoint

        # Configure LLM if provided
        if llm_config and llm_config.get("api_key"):
            try:
                client = OpenAI(api_key=llm_config["api_key"])
                kwargs["llm_client"] = client
                kwargs["llm_model"] = llm_config.get("model", "gpt-4o")
                if llm_config.get("prompt"):
                    kwargs["llm_prompt"] = llm_config["prompt"]
            except Exception as e:
                raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")

        self.md = MarkItDown(**kwargs)
        self.last_config = current_config

    def convert_file(self, file_path, doc_intel_endpoint=None, llm_config=None):
        """
        Convert a single file to Markdown.

        Args:
            file_path (str): Path to the input file.
            doc_intel_endpoint (str, optional): Azure Document Intelligence Endpoint.
            llm_config (dict, optional): Dictionary with 'api_key', 'model', and 'prompt' for OpenAI.

        Returns:
            str: The converted Markdown content.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            self._initialize_markitdown(doc_intel_endpoint, llm_config)
            result = self.md.convert(file_path)
            return result.text_content
        except Exception as e:
            raise RuntimeError(f"Conversion failed for {file_path}: {str(e)}")

    def save_output(self, content, output_path):
        """
        Save content to a file.
        """
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

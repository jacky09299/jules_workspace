import tkinter as tk
from tkinter import ttk

class PropertyPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, width=250, bg="#e0e0e0")
        self.pack_propagate(False)

        self.header = tk.Label(self, text="屬性 (Properties)", font=("Arial", 12, "bold"), bg="#e0e0e0")
        self.header.pack(pady=10, fill=tk.X)

        self.content_frame = tk.Frame(self, bg="#e0e0e0")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        self.current_node = None

    def show_properties(self, node_widget):
        # Clear previous
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.current_node = node_widget.node
        node = self.current_node

        # Title
        tk.Label(self.content_frame, text=f"Node: {node.title}", bg="#e0e0e0", font=("Arial", 10, "bold")).pack(pady=5)

        # Parameters
        # This is a generic property editor.
        # Ideally, nodes should define their schema.
        # For MVP, we iterate over the 'parameters' dict.

        for key, value in node.parameters.items():
            frame = tk.Frame(self.content_frame, bg="#e0e0e0")
            frame.pack(fill=tk.X, pady=2)

            tk.Label(frame, text=key, bg="#e0e0e0").pack(side=tk.LEFT)

            # Simple entry for everything for now
            # We can improve this with type checking later (e.g., Checkbox for bool)
            var = tk.StringVar(value=str(value))
            entry = tk.Entry(frame, textvariable=var)
            entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

            # Callback to update node parameter
            def update_param(name=key, v=var):
                # Try to convert types if possible
                val = v.get()
                # Basic type inference
                if val.lower() == 'true': val = True
                elif val.lower() == 'false': val = False
                elif val.isdigit(): val = int(val)
                else:
                    try:
                        val = float(val)
                    except ValueError:
                        pass

                node.parameters[name] = val
                print(f"Updated {name} to {val}")

            entry.bind("<FocusOut>", lambda e, n=key, v=var: update_param(n, v))
            entry.bind("<Return>", lambda e, n=key, v=var: update_param(n, v))

    def clear(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.current_node = None

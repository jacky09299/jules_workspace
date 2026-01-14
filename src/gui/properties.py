import tkinter as tk
from tkinter import ttk, filedialog

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

            # Determine if this needs a file picker
            # Convention: keys ending with "_path" get a file picker
            is_file_path = key.endswith("_path")

            var = tk.StringVar(value=str(value))

            if is_file_path:
                entry = tk.Entry(frame, textvariable=var)
                entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

                def pick_file(v=var, k=key):
                    # Check if saving or opening based on key name or node type?
                    # Heuristic: "output_path" is usually save, "file_path" is open
                    if "output" in k:
                        # Save
                        # Determine extension from context? Hard to know here.
                        # Just generic save for now or context aware?
                        # SaveNode uses "format" param but we don't have easy access to other params here linearly.
                        path = filedialog.asksaveasfilename()
                    else:
                        # Open
                        path = filedialog.askopenfilename()

                    if path:
                        v.set(path)
                        update_param(k, v)

                btn = tk.Button(frame, text="...", command=pick_file, width=3)
                btn.pack(side=tk.RIGHT)
            else:
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

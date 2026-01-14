import tkinter as tk
from tkinter import ttk, filedialog
from src.core.datatypes import DataType

class PropertyPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, width=250, bg="#e0e0e0")
        self.pack_propagate(False)

        self.header = tk.Label(self, text="屬性 (Properties)", font=("Arial", 12, "bold"), bg="#e0e0e0")
        self.header.pack(pady=10, fill=tk.X)

        self.content_frame = tk.Frame(self, bg="#e0e0e0")
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=5)

        self.current_node = None
        self.current_node_widget = None

    def show_properties(self, node_widget):
        # Clear previous
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        self.current_node_widget = node_widget
        self.current_node = node_widget.node
        node = self.current_node
        
        # Title
        tk.Label(self.content_frame, text=f"Node: {node.title}", bg="#e0e0e0", font=("Arial", 10, "bold")).pack(pady=5)

        # Parameters
        for key, value in node.parameters.items():
            if key.startswith("_"):
                continue

            frame = tk.Frame(self.content_frame, bg="#e0e0e0", relief=tk.FLAT, borderwidth=1)
            frame.pack(fill=tk.X, pady=2)

            # Check if exposed
            is_exposed = key in node.param_inputs

            # Label (with Right-Click Menu)
            lbl = tk.Label(frame, text=key + (" (Input)" if is_exposed else ""), bg="#e0e0e0", fg="blue" if is_exposed else "black")
            lbl.pack(side=tk.LEFT)

            # Context Menu for Expose/Hide
            menu = tk.Menu(frame, tearoff=0)
            if is_exposed:
                menu.add_command(label="Hide Input Port", command=lambda k=key: self.toggle_expose(k, False))
            else:
                menu.add_command(label="Expose as Input", command=lambda k=key: self.toggle_expose(k, True))

            def show_menu(event, m=menu):
                m.post(event.x_root, event.y_root)

            lbl.bind("<Button-3>", show_menu) # Right click

            # If exposed, we disable the input widget or just indicate it's overridden
            state = "disabled" if is_exposed else "normal"

            # Determine widget type
            is_file_path = key.endswith("_path")
            is_action = key.endswith("_action")

            var = tk.StringVar(value=str(value))

            if is_action:
                method_name = key.replace("_action", "")
                def trigger_action(n=node, m=method_name):
                    if hasattr(n, m):
                        getattr(n, m)()
                        if self.current_node_widget:
                             self.show_properties(self.current_node_widget)
                    else:
                        print(f"Node {n.title} has no method {m}")
                btn = tk.Button(frame, text=value, command=trigger_action, state=state)
                btn.pack(fill=tk.X)

            elif is_file_path:
                entry = tk.Entry(frame, textvariable=var, state=state)
                entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

                def pick_file(v=var, k=key):
                    if "output" in k:
                        path = filedialog.asksaveasfilename()
                    else:
                        path = filedialog.askopenfilename()
                    if path:
                        v.set(path)
                        update_param(k, v)

                btn = tk.Button(frame, text="...", command=pick_file, width=3, state=state)
                btn.pack(side=tk.RIGHT)
                
            else:
                entry = tk.Entry(frame, textvariable=var, state=state)
                entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)

            # Callback to update node parameter
            def update_param(name=key, v=var):
                val = v.get()
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

            if not is_action and state == "normal":
                entry.bind("<FocusOut>", lambda e, n=key, v=var: update_param(n, v))
                entry.bind("<Return>", lambda e, n=key, v=var: update_param(n, v))

    def toggle_expose(self, key, expose):
        node = self.current_node
        if expose:
            node.expose_parameter(key)
        else:
            node.hide_parameter(key)

        # Refresh UI
        self.show_properties(self.current_node_widget)
        # Refresh Node Widget on Canvas (to show new ports)
        if hasattr(self.current_node_widget, "update_visuals"):
            self.current_node_widget.update_visuals()

    def clear(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.current_node = None

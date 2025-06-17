print("Minimal Tkinter Test: SCRIPT EXECUTION STARTED", flush=True)
import tkinter as tk
print("Minimal Tkinter Test: tkinter imported", flush=True)
try:
    root = tk.Tk()
    print("Minimal Tkinter Test: tk.Tk() created", flush=True)
    root.withdraw() # Don't show the window
    print("Minimal Tkinter Test: root withdrawn", flush=True)
    # Perform a simple operation
    label = tk.Label(root, text="Hello")
    print("Minimal Tkinter Test: Label created", flush=True)
    root.update_idletasks() # Process pending operations
    print("Minimal Tkinter Test: root updated", flush=True)
    print("Minimal Tkinter Test: SUCCESS", flush=True)
except Exception as e:
    print(f"Minimal Tkinter Test: EXCEPTION: {e}", flush=True)
    import traceback
    traceback.print_exc()
finally:
    print("Minimal Tkinter Test: FINALLY block reached", flush=True)
print("Minimal Tkinter Test: SCRIPT EXECUTION FINISHED", flush=True)

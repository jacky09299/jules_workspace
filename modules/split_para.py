import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import re

class CSVProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CSV Data Processor")
        self.root.geometry("600x500")
        
        # Variables
        self.input_file_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=os.getcwd())
        self.L_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready to process data")
        self.qubit_d_values = ['1um', '2um', '3um', '4um'] + [f'{i}um' for i in range(5, 151, 5)]


        self.selected_values = {d: tk.BooleanVar(value=True) for d in self.qubit_d_values}
        self.default_thickness = tk.StringVar(value="40")
        
        # Create UI
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input file section
        file_frame = ttk.LabelFrame(main_frame, text="Input/Output Settings", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Input CSV File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.input_file_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self.browse_input_file).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(file_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.output_dir_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)
        
        # Parameters section
        params_frame = ttk.LabelFrame(main_frame, text="Processing Parameters", padding="10")
        params_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(params_frame, text="L Value:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(params_frame, textvariable=self.L_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(params_frame, text="Thickness (t):").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(20,0))
        ttk.Entry(params_frame, textvariable=self.default_thickness, width=10).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(params_frame, text="um").grid(row=0, column=4, sticky=tk.W, pady=5)
        
        # qubit_d values section (checkboxes)
        values_frame = ttk.LabelFrame(main_frame, text="qubit_d Values to Process", padding="10")
        values_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollable canvas for checkboxes
        canvas = tk.Canvas(values_frame)
        scrollbar = ttk.Scrollbar(values_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons for selecting/deselecting all
        buttons_frame = ttk.Frame(scrollable_frame)
        buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(buttons_frame, text="Select All", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Deselect All", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        
        # Add checkboxes for qubit_d values
        values_container = ttk.Frame(scrollable_frame)
        values_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Arrange checkboxes in a grid (3 columns)
        row, col = 0, 0
        for d in self.qubit_d_values:
            ttk.Checkbutton(
                values_container, 
                text=d, 
                variable=self.selected_values[d]
            ).grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1
        
        # Bottom section: Process button and status
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Process Data", command=self.process_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        status_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W, padx=5)
    
    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="Select Input CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.input_file_var.set(filename)
            # Try to extract L value from filename
            try:
                match = re.search(r'L(.+)\.csv', os.path.basename(filename))
                if match:
                    self.L_var.set(match.group(1))
            except:
                pass
    
    def browse_output_dir(self):
        dirname = filedialog.askdirectory(
            title="Select Output Directory"
        )
        if dirname:
            self.output_dir_var.set(dirname)
    
    def select_all(self):
        for var in self.selected_values.values():
            var.set(True)
    
    def deselect_all(self):
        for var in self.selected_values.values():
            var.set(False)
    
    def process_data(self):
        # Get input values
        input_file = self.input_file_var.get()
        output_dir = self.output_dir_var.get()
        L_value = self.L_var.get()
        thickness = self.default_thickness.get()
        
        # Validation
        if not input_file:
            messagebox.showerror("Error", "Please select an input CSV file")
            return
        
        if not L_value:
            messagebox.showerror("Error", "Please enter an L value")
            return
        
        # Filter qubit_d values that are selected
        selected_d_values = [d for d in self.qubit_d_values if self.selected_values[d].get()]
        
        if not selected_d_values:
            messagebox.showerror("Error", "Please select at least one qubit_d value")
            return
        
        # Read the CSV file
        try:
            self.status_var.set(f"Reading file: {input_file}")
            self.root.update()
            data = pd.read_csv(input_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read CSV file: {str(e)}")
            self.status_var.set("Error reading file")
            return
        
        # Process for each selected qubit_d value
        success_count = 0
        error_count = 0
        
        for d in selected_d_values:
            try:
                # Define column names
                freq_col = "Freq [GHz]"
                re_col = f"re(S(1,2)) [] - $qubit_couple_gap='{d}'"
                im_col = f"im(S(1,2)) [] - $qubit_couple_gap='{d}'"
                
                # Check if columns exist
                if re_col not in data.columns or im_col not in data.columns:
                    self.status_var.set(f"Skipping {d}: Missing required columns")
                    self.root.update()
                    error_count += 1
                    continue
                
                # Extract data
                output_data = data[[freq_col, re_col, im_col]].copy()
                output_data.columns = ["Freq [GHz]", "re(S(1,2)) []", "im(S(1,2)) []"]
                
                # Define output filename
                output_file = os.path.join(output_dir, f"filter_N5_63_06_L{L_value}_d{d}_t{thickness}.csv")
                
                # Save to CSV
                output_data.to_csv(output_file, index=False)
                
                success_count += 1
                self.status_var.set(f"Processed: {d} ({success_count}/{len(selected_d_values)})")
                self.root.update()
                
            except Exception as e:
                error_count += 1
                self.status_var.set(f"Error processing {d}: {str(e)}")
                self.root.update()
        
        # Final status
        if error_count == 0:
            self.status_var.set(f"Completed! {success_count} files processed successfully")
            messagebox.showinfo("Success", f"All {success_count} files were processed successfully.")
        else:
            self.status_var.set(f"Completed with errors. {success_count} successful, {error_count} errors")
            messagebox.showwarning("Warning", f"Completed with {error_count} errors. {success_count} files were processed successfully.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CSVProcessorApp(root)
    root.mainloop()
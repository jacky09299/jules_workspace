import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import re

# Configuration: Add physical quantities and corresponding units here
quantity_units = {
    'None': [''],
    'Length': ['pm', 'nm', 'μm', 'mm', 'cm', 'dm', 'm', 'km', 'Mm', 'Gm'],
    'Area': ['nm²', 'μm²', 'mm²', 'cm²', 'm²', 'km²'],
    'Volume': ['nm³', 'μm³', 'mm³', 'cm³', 'm³', 'km³', 'L', 'mL', 'μL', 'nL'],
    'Mass': ['fg', 'pg', 'ng', 'μg', 'mg', 'g', 'kg', 't'],
    'Time': ['fs', 'ps', 'ns', 'μs', 'ms', 's', 'min', 'h', 'day', 'yr'],
    'Frequency': ['Hz', 'kHz', 'MHz', 'GHz', 'THz'],
    'Current': ['fA', 'pA', 'nA', 'μA', 'mA', 'A', 'kA'],
    'Voltage': ['μV', 'mV', 'V', 'kV', 'MV'],
    'Resistance': ['μΩ', 'mΩ', 'Ω', 'kΩ', 'MΩ', 'GΩ'],
    'Conductance': ['μS', 'mS', 'S'],
    'Capacitance': ['aF', 'fF', 'pF', 'nF', 'μF', 'mF', 'F'],
    'Inductance': ['pH', 'nH', 'μH', 'mH', 'H'],
    'Power': ['nW', 'μW', 'mW', 'W', 'kW', 'MW', 'GW'],
    'Energy': ['eV', 'meV', 'keV', 'MeV', 'J', 'kJ', 'MJ', 'Wh', 'kWh'],
    'Pressure': ['Pa', 'kPa', 'MPa', 'GPa', 'bar', 'atm', 'mmHg', 'Torr'],
    'Temperature': ['K', '°C', '°F'],
    'Force': ['μN', 'mN', 'N', 'kN', 'MN'],
    'Magnetic Field': ['nT', 'μT', 'mT', 'T'],
    'Luminous Intensity': ['cd', 'mcd', 'μcd'],
    'Amount of Substance': ['mol', 'mmol', 'μmol', 'nmol'],
    'Data Size': ['bit', 'B', 'kB', 'MB', 'GB', 'TB'],
    # 你可以根據需要繼續擴充
}

class ExcelPlotGUI:
    def __init__(self, master):
        self.master = master
        master.title("Excel Multi-Curve Plot Tool")

        # --- Main layout frames ---
        self.frame_top = tk.Frame(master)
        self.frame_top.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.frame_center = tk.Frame(master)
        self.frame_center.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.frame_left = tk.Frame(self.frame_center)
        self.frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        self.frame_plot = tk.Frame(self.frame_center)
        self.frame_plot.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.frame_bottom = tk.Frame(master)
        self.frame_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        # --- Top controls: Load (左), Plot (左下), 曲線選擇 (右) ---
        frame_left_top = tk.Frame(self.frame_top)
        frame_left_top.pack(side=tk.LEFT, anchor='n')

        self.btn_load = tk.Button(frame_left_top, text="Load Excel", command=self.load_excel)
        self.btn_load.pack(side=tk.TOP, padx=2, anchor='w')

        self.btn_plot = tk.Button(frame_left_top, text="Plot (Scatter)", command=self.plot_data)
        self.btn_plot.pack(side=tk.TOP, padx=2, pady=(2, 6), anchor='w')

        frame_curve = tk.Frame(self.frame_top)
        frame_curve.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(frame_curve, text="Select curves to plot:").pack(anchor='w', padx=2)
        self.listbox = tk.Listbox(frame_curve, selectmode=tk.MULTIPLE, exportselection=False, height=4)
        self.listbox.pack(fill=tk.X, padx=2, expand=True)

        # --- Y axis controls (left, vertically centered) ---
        frame_y = tk.LabelFrame(self.frame_left, text="Y Axis")
        frame_y.pack(anchor='center', pady=0, expand=True)
        tk.Label(frame_y, text="Quantity:").grid(row=0, column=0, sticky='e')
        self.var_y_qty = tk.StringVar()
        self.om_y_qty = tk.OptionMenu(frame_y, self.var_y_qty, *quantity_units.keys(), command=self.update_y_units)
        self.om_y_qty.grid(row=0, column=1, sticky='w')
        tk.Label(frame_y, text="Unit:").grid(row=1, column=0, sticky='e')
        self.var_y_unit = tk.StringVar()
        self.om_y_unit = tk.OptionMenu(frame_y, self.var_y_unit, '')
        self.om_y_unit.grid(row=1, column=1, sticky='w')
        tk.Label(frame_y, text="Custom label:").grid(row=2, column=0, sticky='e')
        self.entry_y_label = tk.Entry(frame_y)
        self.entry_y_label.grid(row=2, column=1, sticky='we')
        self.var_y_use_qty = tk.BooleanVar(value=True)
        self.chk_y_use_qty = tk.Checkbutton(frame_y, text="以Quantity為標籤", variable=self.var_y_use_qty)
        self.chk_y_use_qty.grid(row=3, column=0, columnspan=2, sticky='w')
        self.var_y_add_unit = tk.BooleanVar(value=True)
        self.chk_y_add_unit = tk.Checkbutton(frame_y, text="附加單位", variable=self.var_y_add_unit)
        self.chk_y_add_unit.grid(row=4, column=0, columnspan=2, sticky='w')
        self.var_y_replace_unit = tk.BooleanVar(value=False)
        self.chk_y_replace_unit = tk.Checkbutton(frame_y, text="取代單位", variable=self.var_y_replace_unit)
        self.chk_y_replace_unit.grid(row=5, column=0, columnspan=2, sticky='w')

        # --- Plot area (center) ---
        self.fig, self.ax = plt.subplots(figsize=(6.4, 4.8))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_plot)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        # --- X axis controls (bottom, horizontally centered) ---
        frame_x = tk.LabelFrame(self.frame_bottom, text="X Axis")
        frame_x.pack(anchor='center', pady=0)
        tk.Label(frame_x, text="Quantity:").grid(row=0, column=0, sticky='e')
        self.var_x_qty = tk.StringVar()
        self.om_x_qty = tk.OptionMenu(frame_x, self.var_x_qty, *quantity_units.keys(), command=self.update_x_units)
        self.om_x_qty.grid(row=0, column=1, sticky='w')
        tk.Label(frame_x, text="Unit:").grid(row=0, column=2, sticky='e')
        self.var_x_unit = tk.StringVar()
        self.om_x_unit = tk.OptionMenu(frame_x, self.var_x_unit, '')
        self.om_x_unit.grid(row=0, column=3, sticky='w')
        tk.Label(frame_x, text="Custom label:").grid(row=1, column=0, sticky='e')
        self.entry_x_label = tk.Entry(frame_x)
        self.entry_x_label.grid(row=1, column=1, sticky='we')
        self.var_x_use_qty = tk.BooleanVar(value=False)
        self.chk_x_use_qty = tk.Checkbutton(frame_x, text="以Quantity為標籤", variable=self.var_x_use_qty)
        self.chk_x_use_qty.grid(row=2, column=0, columnspan=2, sticky='w')
        self.var_x_add_unit = tk.BooleanVar(value=True)
        self.chk_x_add_unit = tk.Checkbutton(frame_x, text="附加單位", variable=self.var_x_add_unit)
        self.chk_x_add_unit.grid(row=2, column=2, columnspan=2, sticky='w')
        self.var_x_replace_unit = tk.BooleanVar(value=False)
        self.chk_x_replace_unit = tk.Checkbutton(frame_x, text="取代單位", variable=self.var_x_replace_unit)
        self.chk_x_replace_unit.grid(row=3, column=0, columnspan=4, sticky='w')

        self.df = None

    def load_excel(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx;*.xls")]
        )
        if not file_path:
            return
        try:
            self.df = pd.read_excel(file_path)
        except Exception as e:
            messagebox.showerror("Load Failed", str(e))
            return
        cols = list(self.df.columns)
        self.x_col = cols[0]
        self.curve_cols = cols[1:]
        self.listbox.delete(0, tk.END)
        for i, col in enumerate(self.curve_cols):
            self.listbox.insert(tk.END, col)
            self.listbox.selection_set(i)

        if self.var_x_qty.get() == '':
            default_x_qty = list(quantity_units.keys())[0]
            self.var_x_qty.set(default_x_qty)
            self.update_x_units(default_x_qty)
        if self.var_y_qty.get() == '':
            default_y_qty = list(quantity_units.keys())[0]
            self.var_y_qty.set(default_y_qty)
            self.update_y_units(default_y_qty)

    def update_x_units(self, selected_qty):
        units = quantity_units.get(selected_qty, [])
        menu = self.om_x_unit['menu']
        menu.delete(0, 'end')
        for u in units:
            menu.add_command(label=u, command=lambda value=u: self.var_x_unit.set(value))
        if units:
            self.var_x_unit.set(units[0])
        else:
            self.var_x_unit.set('')

    def update_y_units(self, selected_qty):
        units = quantity_units.get(selected_qty, [])
        menu = self.om_y_unit['menu']
        menu.delete(0, 'end')
        for u in units:
            menu.add_command(label=u, command=lambda value=u: self.var_y_unit.set(value))
        if units:
            self.var_y_unit.set(units[0])
        else:
            self.var_y_unit.set('')

    def plot_data(self):
        if self.df is None:
            messagebox.showwarning("No Data", "Please load an Excel file first.")
            return
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select at least one curve to plot.")
            return

        # ===== 主要修改處 =====
        # 1. 清除整個 Figure，而不只是 Axes
        self.fig.clear()
        # 2. 在清空的 Figure 上重新添加一個 Axes
        self.ax = self.fig.add_subplot(111)
        # =======================

        x = self.df[self.x_col]
        # self.ax.clear()  <-- 不再需要這一行

        for idx in sel:
            col = self.curve_cols[idx]
            y = self.df[col]
            self.ax.scatter(x, y, label=col)

        # --- X axis label logic ---
        x_label_stripped = re.sub(r"\s*\(.*?\)", "", self.x_col).strip()
        x_unit_match = re.search(r"\((.*?)\)", self.x_col)
        x_unit_from_col = x_unit_match.group(1) if x_unit_match else ''
        x_qty = self.var_x_qty.get()
        x_unit = self.var_x_unit.get()
        use_x_qty = self.var_x_use_qty.get()
        add_x_unit = self.var_x_add_unit.get()
        replace_x_unit = self.var_x_replace_unit.get()
        custom_x_label = self.entry_x_label.get().strip()
        if custom_x_label:
            label = custom_x_label
        elif use_x_qty:
            label = x_qty
        else:
            label = x_label_stripped

        if add_x_unit:
            if use_x_qty:
                unit = x_unit
                if unit:
                    self.ax.set_xlabel(f"${label} \\, ({unit})$")
                else:
                    self.ax.set_xlabel(f"${label}$")
            elif replace_x_unit:
                unit = x_unit
                if unit:
                    self.ax.set_xlabel(f"${label} \\, ({unit})$")
                else:
                    self.ax.set_xlabel(f"${label}$")
            else:
                if x_unit_from_col and x_unit and x_unit != x_unit_from_col:
                    self.ax.set_xlabel(f"${label} \\, ({x_unit_from_col})({x_unit})$")
                elif x_unit_from_col and (not x_unit or x_unit == x_unit_from_col):
                    self.ax.set_xlabel(f"${label} \\, ({x_unit_from_col})$")
                elif x_unit and not x_unit_from_col:
                    self.ax.set_xlabel(f"${label} \\, ({x_unit})$")
                else:
                    self.ax.set_xlabel(f"${label}$")
        else:
            # 修正：即使不 append unit，若原欄位有單位仍顯示
            if x_unit_from_col:
                self.ax.set_xlabel(f"${label} \\, ({x_unit_from_col})$")
            else:
                self.ax.set_xlabel(f"${label}$")

        # --- Y axis label logic ---
        y_qty = self.var_y_qty.get()
        y_unit = self.var_y_unit.get()
        use_y_qty = self.var_y_use_qty.get()
        add_y_unit = self.var_y_add_unit.get()
        replace_y_unit = self.var_y_replace_unit.get()
        custom_y_label = self.entry_y_label.get().strip()
        if custom_y_label:
            y_label = custom_y_label
        elif use_y_qty:
            y_label = y_qty
        else:
            y_label = self.curve_cols[sel[0]] if sel else "Y"
            y_label = re.sub(r"\s*\(.*?\)", "", y_label).strip()
        y_unit_from_col = ''
        if sel:
            y_col = self.curve_cols[sel[0]]
            y_unit_match = re.search(r"\((.*?)\)", y_col)
            y_unit_from_col = y_unit_match.group(1) if y_unit_match else ''
        if add_y_unit:
            if use_y_qty:
                unit = y_unit
                if unit:
                    self.ax.set_ylabel(f"${y_label} \\, ({unit})$")
                else:
                    self.ax.set_ylabel(f"${y_label}$")
            elif replace_y_unit:
                unit = y_unit
                if unit:
                    self.ax.set_ylabel(f"${y_label} \\, ({unit})$")
                else:
                    self.ax.set_ylabel(f"${y_label}$")
            else:
                if y_unit_from_col and y_unit and y_unit != y_unit_from_col:
                    self.ax.set_ylabel(f"${y_label} \\, ({y_unit_from_col})({y_unit})$")
                elif y_unit_from_col and (not y_unit or y_unit == y_unit_from_col):
                    self.ax.set_ylabel(f"${y_label} \\, ({y_unit_from_col})$")
                elif y_unit and not y_unit_from_col:
                    self.ax.set_ylabel(f"${y_label} \\, ({y_unit})$")
                else:
                    self.ax.set_ylabel(f"${y_label}$")
        else:
            # 修正：即使不 append unit，若原欄位有單位仍顯示
            if y_unit_from_col:
                self.ax.set_ylabel(f"${y_label} \\, ({y_unit_from_col})$")
            else:
                self.ax.set_ylabel(f"${y_label}$")

        self.ax.set_title(f"${y_label}$ vs ${label}$")
        self.ax.legend()
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.canvas.draw()
        
        # 不要在這裡重新設定畫布大小，也不要用savefig去影響佈局
        # self.fig.set_size_inches(6.4, 4.8) # <-- 移除這行
        self.fig.savefig("plot_figure.png", dpi=150) # 可以增加dpi讓儲存的圖片更清晰

if __name__ == '__main__':
    root = tk.Tk()
    app = ExcelPlotGUI(root)
    root.geometry('800x600')
    root.mainloop()
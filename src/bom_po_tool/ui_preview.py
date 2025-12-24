from __future__ import annotations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from bom_reader import parse_bom
from config import MOUSER_API_KEY
from supplier_api import fetch_mouser_data
from excel_writer import generate_po_file


class App(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self.master.title("BOM Preview (MVP)")
        self.master.geometry("1000x600")

        self.grid(sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.path_var = tk.StringVar(value="")
        self.info_var = tk.StringVar(value="Pick a BOM file to preview parsed parts.")

        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", **pad)
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="BOM file:").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.path_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="Browse…", command=self.pick_file).grid(row=0, column=2)
        ttk.Button(top, text="Check Stock", command=self.run_search).grid(row=0, column=3, padx=5)
        ttk.Button(top, text="Export PO", command=self.export_excel).grid(row=0, column=4, padx=5)

        ttk.Label(self, textvariable=self.info_var).grid(row=1, column=0, sticky="w", **pad)

        # Table
        cols = ("MPN", "Qty", "Description", "Refs","Status", "Stock", "Price")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=200, anchor="w")

        self.tree.column("Qty", width=70, anchor="center")
        self.tree.column("Description", width=450, anchor="w")

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        vsb.grid(row=2, column=1, sticky="ns", pady=(0, 10))

    def pick_file(self):
        path = filedialog.askopenfilename(
            title="Select BOM",
            filetypes=[("BOM files", "*.xlsx *.xlsm *.xls *.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        self.path_var.set(path)
        self.load_and_preview(path)

    def load_and_preview(self, path: str):
        # clear table
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            parts, debug = parse_bom(path)
            self.parts = parts
        except Exception as e:
            messagebox.showerror("Parse error", str(e))
            return

        for p in parts[:500]:  # safety cap for UI
            self.tree.insert("", "end", values=(p.mpn, p.qty, p.description, p.refs))

        self.info_var.set(
            f"Parsed: {debug['rows_parsed']} parts | Skipped: {debug['rows_skipped']} rows"
        )

        # Optional: print column list to console for debugging
        print("Detected columns:", debug["columns"])

    def run_search(self):
        """
        The 'Waiter' takes the order to the 'Chef' (API).
        """
        # 1. Check if we have parts to search
        if not hasattr(self, 'parts') or not self.parts:
            messagebox.showwarning("Warning", "Please load a BOM file first.")
            return

        # 2. Update UI to show we are working
        self.info_var.set("Contacting Mouser... please wait.")
        self.update_idletasks()  # Forces the window to update immediately

        # 3. Call the Chef (Run the API logic)
        # We pass the list of parts and the secret key
        fetch_mouser_data(self.parts, MOUSER_API_KEY)

        # 4. Refresh the table to show the new data
        self.refresh_table()
        self.info_var.set("Search Complete!")

    def refresh_table(self):
        """
        Clears the table and re-draws it with the updated data.
        """
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Re-insert rows with the new Price/Stock info
        for p in self.parts[:500]:
            # Format price nicely (e.g., "$ 0.50")
            price_display = f"${p.unit_price:.2f}" if p.unit_price > 0 else ""

            self.tree.insert("", "end", values=(
                p.mpn,
                p.qty,
                p.description,
                p.refs,
                p.status,  # <--- New
                p.stock_available,  # <--- New
                price_display  # <--- New
            ))

    def export_excel(self):
        """
        Asks user where to save, then runs the generator.
        """
        if not hasattr(self, 'parts') or not self.parts:
            messagebox.showwarning("Warning", "No data to export. Please load a BOM and check stock first.")
            return

        # 1. Ask User: "Where do you want to save this?"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Save Purchase Order"
        )
        if not save_path:
            return  # User cancelled

        # 2. Locate the Template
        # We assume it is in the same folder as the script, or one level up
        import os
        template_name = "template_digikey_mouser_orderer.xlsx"

        # Check current folder
        if os.path.exists(template_name):
            template_path = template_name
        # Check 'src' folder (common issue when running from PyCharm)
        elif os.path.exists(os.path.join("src", "bom_po_tool", template_name)):
            template_path = os.path.join("src", "bom_po_tool", template_name)
        else:
            # Fallback: Ask user to find it manually
            messagebox.showinfo("Template Missing", f"Could not find '{template_name}'.\nPlease select it manually.")
            template_path = filedialog.askopenfilename(title="Select Template File",
                                                       filetypes=[("Excel files", "*.xlsx")])
            if not template_path: return

        # 3. Run the Generator
        try:
            generate_po_file(self.parts, template_path, save_path)

            # Success!
            messagebox.showinfo("Success", f"PO saved to:\n{save_path}")

            # Optional: Open the file automatically for you
            try:
                os.startfile(save_path)
            except:
                pass

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate Excel:\n{str(e)}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

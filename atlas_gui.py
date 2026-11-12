import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import tempfile
import json
import re

# Get the directory where atlas_gui.py is actually located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVEGAME_SCRIPT = os.path.join(BASE_DIR, "savegame_body.py")
HASH_SCRIPT = os.path.join(BASE_DIR, "name32table_hash.py")

class AtlasToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Atlas Fallen Save Game & Hash Utility GUI")
        self.root.geometry("950x700")
        self.root.minsize(800, 600)

        # Style configuration (Modern Dark Theme with vibrant accents)
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Color Palette
        self.bg_color = "#1e1e2f"
        self.panel_color = "#2a2a40"
        self.accent_color = "#ff7b00" # Orange/Gold theme matching Atlas Fallen style
        self.text_color = "#e0e0e0"
        self.btn_bg = "#3d3d5c"
        
        self.root.configure(bg=self.bg_color)
        
        # Configure custom styles
        self.style.configure('.', background=self.bg_color, foreground=self.text_color, font=('Segoe UI', 10))
        self.style.configure('TNotebook', background=self.bg_color, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=self.panel_color, foreground=self.text_color, padding=[12, 8], font=('Segoe UI', 10, 'bold'))
        self.style.map('TNotebook.Tab', background=[('selected', self.accent_color)], foreground=[('selected', '#ffffff')])
        
        self.style.configure('TLabel', background=self.panel_color, foreground=self.text_color)
        self.style.configure('Header.TLabel', background=self.bg_color, foreground=self.accent_color, font=('Segoe UI', 16, 'bold'))
        self.style.configure('SubHeader.TLabel', background=self.panel_color, foreground=self.accent_color, font=('Segoe UI', 11, 'bold'))
        self.style.configure('TCheckbutton', background=self.panel_color, foreground=self.text_color, font=('Segoe UI', 9))
        self.style.map('TCheckbutton', background=[('active', self.panel_color)])
        
        # Main Title
        title_lbl = ttk.Label(root, text="⚔️ Atlas Fallen Save Game & Hash Toolkit ⚔️", style='Header.TLabel')
        title_lbl.pack(pady=12)

        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=15, pady=5)

        # Tabs
        self.tab_savegame = ttk.Frame(self.notebook)
        self.tab_editor = ttk.Frame(self.notebook)
        self.tab_hash = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_savegame, text=" 🛡️ Converter / CLI Wrapper ")
        self.notebook.add(self.tab_editor, text=" 📝 SaveGame JSON Editor ")
        self.notebook.add(self.tab_hash, text=" 🔍 Name32 Hash Tool ")

        self.create_savegame_tab()
        self.create_editor_tab()
        self.create_hash_tab()

        # Bottom Console / Log Output Frame
        console_frame = ttk.Frame(root)
        console_frame.pack(fill='both', expand=False, padx=15, pady=10)
        
        console_lbl = ttk.Label(console_frame, text="Execution Output / Logs:", style='TLabel')
        console_lbl.pack(anchor='w', pady=(0, 2))
        
        self.log_text = tk.Text(console_frame, height=6, bg="#12121a", fg="#00ffcc", insertbackground="white", font=("Consolas", 9), relief="flat")
        self.log_text.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(console_frame, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.loaded_sav_path = None
        self._highlight_job = None
        self.log(f"[Init] Script base directory: {BASE_DIR}")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def create_savegame_tab(self):
        frame = tk.Frame(self.tab_savegame, bg=self.panel_color, bd=2, relief="groove")
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Mode Selection
        ttk.Label(frame, text="Select Operation Mode:", style='SubHeader.TLabel').grid(row=0, column=0, sticky='w', padx=15, pady=10)
        
        self.mode_var = tk.StringVar(value="extract_json")
        modes = [
            ("Extract JSON from .sav", "extract_json"),
            ("Extract Raw Body from .sav", "extract_raw"),
            ("Compose .sav from JSON", "compose_json"),
            ("Compose .sav from Raw Body", "compose_raw")
        ]
        
        mode_frame = ttk.Frame(frame)
        mode_frame.grid(row=1, column=0, columnspan=3, sticky='w', padx=15)
        for idx, (text, val) in enumerate(modes):
            rb = ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=val, command=self.toggle_mode_ui)
            rb.grid(row=idx//2, column=idx%2, sticky='w', padx=10, pady=3)

        # File Inputs
        ttk.Label(frame, text="Input File (.sav / Body / JSON):", style='TLabel').grid(row=2, column=0, sticky='w', padx=15, pady=(15, 5))
        self.ent_input = ttk.Entry(frame, width=50)
        self.ent_input.grid(row=3, column=0, sticky='we', padx=15)
        btn_in = tk.Button(frame, text="Browse...", bg=self.btn_bg, fg=self.text_color, relief="flat", command=self.browse_input)
        btn_in.grid(row=3, column=1, padx=5)

        ttk.Label(frame, text="Output File (.json / .raw / .sav):", style='TLabel').grid(row=4, column=0, sticky='w', padx=15, pady=(15, 5))
        self.ent_output = ttk.Entry(frame, width=50)
        self.ent_output.grid(row=5, column=0, sticky='we', padx=15)
        btn_out = tk.Button(frame, text="Browse...", bg=self.btn_bg, fg=self.text_color, relief="flat", command=self.browse_output)
        btn_out.grid(row=5, column=1, padx=5)

        # Flags & Options Frame
        opt_frame = ttk.LabelFrame(frame, text=" Advanced Options ")
        opt_frame.grid(row=6, column=0, columnspan=2, sticky='we', padx=15, pady=15)

        self.chk_skip_era = tk.BooleanVar()
        self.chk_keep_json = tk.BooleanVar()
        self.chk_compress = tk.BooleanVar(value=True)

        self.cb_era = ttk.Checkbutton(opt_frame, text="--skip-era (Skip game-specific era portion)", variable=self.chk_skip_era)
        self.cb_era.pack(anchor='w', padx=10, pady=3)
        
        self.cb_json = ttk.Checkbutton(opt_frame, text="--keep-inner-json-as-string (Keep inner json raw)", variable=self.chk_keep_json)
        self.cb_json.pack(anchor='w', padx=10, pady=3)
        
        self.cb_comp = ttk.Checkbutton(opt_frame, text="--compress (Compress save contents on compose)", variable=self.chk_compress)
        self.cb_comp.pack(anchor='w', padx=10, pady=3)

        # Execute Button
        btn_run = tk.Button(frame, text="🚀 Run Converter Tool", bg="#ff7b00", fg="#ffffff", font=('Segoe UI', 10, 'bold'), relief="flat", padx=15, pady=8, command=self.run_savegame_script)
        btn_run.grid(row=7, column=0, columnspan=2, pady=15)
        
        frame.columnconfigure(0, weight=1)
        self.toggle_mode_ui()

    def create_editor_tab(self):
        frame = tk.Frame(self.tab_editor, bg=self.panel_color, bd=2, relief="groove")
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Top control bar for Editor
        ctrl_bar = ttk.Frame(frame)
        ctrl_bar.pack(fill='x', padx=15, pady=10)

        btn_open = tk.Button(ctrl_bar, text="📂 Open .sav File", bg="#3d3d5c", fg="#ffffff", font=('Segoe UI', 9, 'bold'), relief="flat", padx=10, pady=5, command=self.editor_open_sav)
        btn_open.pack(side='left', padx=(0, 10))

        btn_save = tk.Button(ctrl_bar, text="💾 Save/Export Back to .sav", bg="#ff7b00", fg="#ffffff", font=('Segoe UI', 9, 'bold'), relief="flat", padx=10, pady=5, command=self.editor_save_sav)
        btn_save.pack(side='left', padx=(0, 10))

        self.lbl_current_file = ttk.Label(ctrl_bar, text="No file loaded.", font=('Segoe UI', 9, 'italic'))
        self.lbl_current_file.pack(side='left', padx=10)

        # JSON Text Editor Area
        editor_frame = ttk.Frame(frame)
        editor_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        self.json_text = tk.Text(editor_frame, bg="#12121a", fg="#d4d4d4", insertbackground="white", font=("Consolas", 10), wrap="none", relief="flat")
        
        y_scroll = ttk.Scrollbar(editor_frame, orient="vertical", command=self.json_text.yview)
        x_scroll = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.json_text.xview)
        
        # Custom vertical scroll handler for lazy area highlighting
        def on_y_scroll(*args):
            y_scroll.set(*args)
            self.schedule_syntax_highlighting()

        self.json_text.configure(yscrollcommand=on_y_scroll, xscrollcommand=x_scroll.set)

        self.json_text.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')

        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        # Configure Syntax Highlighting Tag Colors
        self.json_text.tag_configure("key", foreground="#9cdcfe")       # Light Blue for keys
        self.json_text.tag_configure("string", foreground="#ce9178")    # Orange-Brown for strings
        self.json_text.tag_configure("number", foreground="#b5cea8")    # Light Green for numbers
        self.json_text.tag_configure("boolean", foreground="#569cd6")   # Blue for true/false/null

        # Bind events for lazy non-freezing highlighting
        self.json_text.bind("<KeyRelease>", self.schedule_syntax_highlighting)
        self.json_text.bind("<Configure>", self.schedule_syntax_highlighting)
        self.json_text.bind("<MouseWheel>", self.schedule_syntax_highlighting)

    def schedule_syntax_highlighting(self, event=None):
        if self._highlight_job:
            self.root.after_cancel(self._highlight_job)
        self._highlight_job = self.root.after(150, self.apply_syntax_highlighting)

    def apply_syntax_highlighting(self):
        try:
            # Highlight only the currently visible view block (lazy rendering) to prevent any freezing
            top_index = self.json_text.index("@0,0")
            bottom_index = self.json_text.index(f"@0,{self.json_text.winfo_height()}")
            
            top_line = max(1, int(top_index.split('.')[0]) - 25)
            bottom_line = int(bottom_index.split('.')[0]) + 25
            
            start_idx = f"{top_line}.0"
            end_idx = f"{bottom_line}.end"
            
            for tag in ["key", "string", "number", "boolean"]:
                self.json_text.tag_remove(tag, start_idx, end_idx)

            content = self.json_text.get(start_idx, end_idx)
            
            key_regex = re.compile(r'"([^"\\]|\\.)*"\s*(?=\:)')
            string_regex = re.compile(r'"([^"\\]|\\.)*"\s*(?!\:)')
            number_regex = re.compile(r'\b-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?\b')
            boolean_regex = re.compile(r'\b(true|false|null)\b')

            for match in number_regex.finditer(content):
                self.json_text.tag_add("number", f"{start_idx} + {match.start()} chars", f"{start_idx} + {match.end()} chars")

            for match in boolean_regex.finditer(content):
                self.json_text.tag_add("boolean", f"{start_idx} + {match.start()} chars", f"{start_idx} + {match.end()} chars")

            for match in string_regex.finditer(content):
                self.json_text.tag_add("string", f"{start_idx} + {match.start()} chars", f"{start_idx} + {match.end()} chars")

            for match in key_regex.finditer(content):
                self.json_text.tag_add("key", f"{start_idx} + {match.start()} chars", f"{start_idx} + {match.end()} chars")
        except tk.TclError:
            pass

    def create_hash_tab(self):
        frame = tk.Frame(self.tab_hash, bg=self.panel_color, bd=2, relief="groove")
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Label(frame, text="Name32 Table Hash & Collision Tool", style='SubHeader.TLabel').grid(row=0, column=0, sticky='w', padx=15, pady=15)
        
        ttk.Label(frame, text="Select 'name32 table.bin' dump file:", style='TLabel').grid(row=1, column=0, sticky='w', padx=15, pady=5)
        
        self.ent_bin = ttk.Entry(frame, width=55)
        self.ent_bin.grid(row=2, column=0, sticky='we', padx=15, pady=5)
        btn_bin = tk.Button(frame, text="Browse...", bg=self.btn_bg, fg=self.text_color, relief="flat", command=self.browse_bin)
        btn_bin.grid(row=2, column=1, padx=5)

        btn_hash_run = tk.Button(frame, text="⚡ Run Hash & Check Collisions", bg="#ff7b00", fg="#ffffff", font=('Segoe UI', 10, 'bold'), relief="flat", padx=15, pady=8, command=self.run_hash_script)
        btn_hash_run.grid(row=3, column=0, columnspan=2, pady=25)

        frame.columnconfigure(0, weight=1)

    def toggle_mode_ui(self):
        mode = self.mode_var.get()
        if "extract" in mode:
            self.cb_comp.state(['disabled'])
            self.cb_era.state(['!disabled'])
            self.cb_json.state(['!disabled'])
        else:
            self.cb_comp.state(['!disabled'])
            self.cb_era.state(['disabled'])
            self.cb_json.state(['disabled'])

    def browse_input(self):
        filename = filedialog.askopenfilename(title="Select Input File")
        if filename:
            self.ent_input.delete(0, tk.END)
            self.ent_input.insert(0, filename)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(title="Select Output File")
        if filename:
            self.ent_output.delete(0, tk.END)
            self.ent_output.insert(0, filename)

    def browse_bin(self):
        filename = filedialog.askopenfilename(title="Select name32 table.bin", filetypes=[("Binary files", "*.bin"), ("All files", "*.*")])
        if filename:
            self.ent_bin.delete(0, tk.END)
            self.ent_bin.insert(0, filename)

    def run_savegame_script(self):
        mode = self.mode_var.get()
        infile = self.ent_input.get().strip()
        outfile = self.ent_output.get().strip()

        if not infile or not outfile:
            messagebox.showerror("Error", "Please specify both input and output files.")
            return

        if not os.path.exists(SAVEGAME_SCRIPT):
            messagebox.showerror("Error", f"savegame_body.py not found at:\n{SAVEGAME_SCRIPT}")
            return

        cmd = ["python", SAVEGAME_SCRIPT, mode, infile, outfile]

        if "extract" in mode:
            if self.chk_skip_era.get():
                cmd.append("--skip-era")
            if self.chk_keep_json.get():
                cmd.append("--keep-inner-json-as-string")
        else:
            if self.chk_compress.get():
                cmd.append("--compress")

        self.log(f"\n[Executing] {' '.join(cmd)}")
        threading.Thread(target=self.execute_command, args=(cmd,), daemon=True).start()

    def editor_open_sav(self):
        filename = filedialog.askopenfilename(title="Select Atlas Fallen .sav File", filetypes=[("Save files", "*.sav"), ("All files", "*.*")])
        if not filename:
            return

        if not os.path.exists(SAVEGAME_SCRIPT):
            messagebox.showerror("Error", f"savegame_body.py not found at:\n{SAVEGAME_SCRIPT}")
            return

        self.loaded_sav_path = filename
        self.lbl_current_file.config(text=f"Loaded: {os.path.basename(filename)}")
        self.log(f"\n[Editor] Extracting JSON from {filename} (running in background)...")

        def task():
            temp_json_path = None
            try:
                fd, temp_json_path = tempfile.mkstemp(suffix=".json")
                os.close(fd)

                cmd = ["python", SAVEGAME_SCRIPT, "extract_json", filename, temp_json_path]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    err_msg = stderr.strip() or "Failed to parse save file."
                    self.root.after(0, lambda: messagebox.showerror("Extraction Error", err_msg))
                    self.root.after(0, lambda: self.log(f"[Error] {err_msg}"))
                    if temp_json_path and os.path.exists(temp_json_path):
                        os.remove(temp_json_path)
                    return

                with open(temp_json_path, 'r', encoding='utf8') as f:
                    content = f.read()

                formatted_json = json.dumps(json.loads(content), indent=4)
                
                def update_ui():
                    self.json_text.delete("1.0", tk.END)
                    self.json_text.insert("1.0", formatted_json)
                    self.log(f"[Editor] Successfully loaded JSON into editor.")
                    self.root.after(100, self.apply_syntax_highlighting)

                self.root.after(0, update_ui)
                if temp_json_path and os.path.exists(temp_json_path):
                    os.remove(temp_json_path)
            except Exception as e:
                self.root.after(0, lambda: self.log(f"[Exception] {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                if temp_json_path and os.path.exists(temp_json_path):
                    try:
                        os.remove(temp_json_path)
                    except:
                        pass

        threading.Thread(target=task, daemon=True).start()

    def editor_save_sav(self):
        if not self.loaded_sav_path:
            messagebox.showwarning("Warning", "Please open an initial .sav file first so the header template is available for composition.")
            return

        out_filename = filedialog.asksaveasfilename(title="Export Modified Save File", defaultextension=".sav", filetypes=[("Save files", "*.sav"), ("All files", "*.*")])
        if not out_filename:
            return

        self.log(f"\n[Editor] Composing back to .sav: {out_filename} (running in background)...")

        def task():
            temp_json_path = None
            try:
                raw_text = self.json_text.get("1.0", tk.END)
                try:
                    parsed_json = json.loads(raw_text)
                except json.JSONDecodeError as jde:
                    self.root.after(0, lambda: messagebox.showerror("JSON Syntax Error", f"Invalid JSON format:\n{str(jde)}"))
                    self.root.after(0, lambda: self.log(f"[Error] JSON Decode Error: {str(jde)}"))
                    return

                fd, temp_json_path = tempfile.mkstemp(suffix=".json")
                os.close(fd)
                with open(temp_json_path, 'w', encoding='utf8') as f:
                    json.dump(parsed_json, f, indent=4)

                cmd = ["python", SAVEGAME_SCRIPT, "compose_json", self.loaded_sav_path, temp_json_path, out_filename, "--compress"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    err_msg = stderr.strip() or "Failed to write save file."
                    self.root.after(0, lambda: messagebox.showerror("Composition Error", err_msg))
                    self.root.after(0, lambda: self.log(f"[Error] {err_msg}"))
                else:
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"Successfully exported save file to:\n{out_filename}"))
                    self.root.after(0, lambda: self.log(f"✨ Successfully exported modified save file to {out_filename}"))

                if temp_json_path and os.path.exists(temp_json_path):
                    os.remove(temp_json_path)
            except Exception as e:
                self.root.after(0, lambda: self.log(f"[Exception] {str(e)}"))
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
                if temp_json_path and os.path.exists(temp_json_path):
                    try:
                        os.remove(temp_json_path)
                    except:
                        pass

        threading.Thread(target=task, daemon=True).start()

    def run_hash_script(self):
        binfile = self.ent_bin.get().strip()
        if not binfile:
            messagebox.showerror("Error", "Please select 'name32 table.bin' first.")
            return

        if not os.path.exists(HASH_SCRIPT):
            messagebox.showerror("Error", f"name32table_hash.py not found at:\n{HASH_SCRIPT}")
            return

        self.log(f"\n[Executing Hash Script on {binfile}]")
        
        def run_hash():
            try:
                with open(binfile, 'rb') as f_in, open(os.path.join(BASE_DIR, 'name32 table.bin'), 'wb') as f_out:
                    f_out.write(f_in.read())
                
                process = subprocess.Popen(["python", HASH_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                
                if stdout:
                    self.log(stdout)
                if stderr:
                    self.log(f"[Error] {stderr}")
                self.log("[Done] Hash processing complete.")
            except Exception as e:
                self.log(f"[Exception] {str(e)}")

        threading.Thread(target=run_hash, daemon=True).start()

    def execute_command(self, cmd):
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            
            if stdout:
                self.log(stdout)
            if stderr:
                self.log(f"[Log/Error] {stderr}")
            if process.returncode == 0:
                self.log("✨ Operation completed successfully!")
            else:
                self.log(f"⚠️ Process finished with exit code {process.returncode}")
        except Exception as e:
            self.log(f"[Exception] {str(e)}")

    def browse_input(self):
        filename = filedialog.askopenfilename(title="Select Input File")
        if filename:
            self.ent_input.delete(0, tk.END)
            self.ent_input.insert(0, filename)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(title="Select Output File")
        if filename:
            self.ent_output.delete(0, tk.END)
            self.ent_output.insert(0, filename)

    def browse_bin(self):
        filename = filedialog.askopenfilename(title="Select name32 table.bin", filetypes=[("Binary files", "*.bin"), ("All files", "*.*")])
        if filename:
            self.ent_bin.delete(0, tk.END)
            self.ent_bin.insert(0, filename)

if __name__ == "__main__":
    root = tk.Tk()
    app = AtlasToolGUI(root)
    root.mainloop()
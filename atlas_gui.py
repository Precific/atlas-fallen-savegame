import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import subprocess
import threading
import os
import sys
import tempfile
import json
import re
import bisect

# Determine base directory whether running as script or compiled PyInstaller single .exe
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SAVEGAME_SCRIPT = os.path.join(BASE_DIR, "savegame_body.py")
HASH_SCRIPT = os.path.join(BASE_DIR, "name32table_hash.py")

class AtlasToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Atlas Fallen Save Game & Hash Utility GUI")
        self.root.geometry("1100x820")
        self.root.minsize(950, 720)

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
        self.tab_docs = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_savegame, text=" 🛡️ Converter / CLI Wrapper ")
        self.notebook.add(self.tab_editor, text=" 📝 SaveGame JSON Editor ")
        self.notebook.add(self.tab_hash, text=" 🔍 Name32 Hash Tool ")
        self.notebook.add(self.tab_docs, text=" 📖 Format Specs ")

        self.create_savegame_tab()
        self.create_editor_tab()
        self.create_hash_tab()
        self.create_docs_tab()

        # Bottom Console / Log Output Frame
        console_frame = ttk.Frame(root)
        console_frame.pack(fill='both', expand=False, padx=15, pady=10)
        
        console_lbl = ttk.Label(console_frame, text="Execution Output / Logs:", style='TLabel')
        console_lbl.pack(anchor='w', pady=(0, 2))
        
        self.log_text = tk.Text(console_frame, height=5, bg="#12121a", fg="#00ffcc", insertbackground="white", font=("Consolas", 9), relief="flat")
        self.log_text.pack(side='left', fill='both', expand=True)
        
        scrollbar = ttk.Scrollbar(console_frame, command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.loaded_sav_path = None
        self._highlight_job = None
        self._raw_search_job = None
        self.tree_item_map = {}
        self.root_json_data = {}
        self.raw_match_indices = []
        self.raw_current_match_idx = 0
        self.log(f"[Init] Base directory resolved to: {BASE_DIR}")

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def create_savegame_tab(self):
        frame = ttk.Frame(self.tab_savegame, padding=10)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

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

        self.gui_mode_var = tk.BooleanVar(value=False)
        chk_gui_mode = ttk.Checkbutton(ctrl_bar, text="Switch to GUI Graphical Editor", variable=self.gui_mode_var, command=self.toggle_editor_view)
        chk_gui_mode.pack(side='left', padx=15)

        self.lbl_current_file = ttk.Label(ctrl_bar, text="No file loaded.", font=('Segoe UI', 9, 'italic'))
        self.lbl_current_file.pack(side='left', padx=10)

        # Container Frame for Editor Views
        self.editor_container = ttk.Frame(frame)
        self.editor_container.pack(fill='both', expand=True, padx=15, pady=(0, 15))
        self.editor_container.rowconfigure(0, weight=1)
        self.editor_container.columnconfigure(0, weight=1)

        # --- View 1: Raw JSON Text Editor with Find Toolbar ---
        self.raw_editor_frame = ttk.Frame(self.editor_container)
        self.raw_editor_frame.grid(row=0, column=0, sticky='nsew')
        self.raw_editor_frame.rowconfigure(1, weight=1)
        self.raw_editor_frame.columnconfigure(0, weight=1)

        # Raw Editor Find / Search Bar
        raw_search_bar = ttk.Frame(self.raw_editor_frame)
        raw_search_bar.grid(row=0, column=0, sticky='ew', pady=(0, 6))

        ttk.Label(raw_search_bar, text="🔍 Find in Raw JSON (min 2 chars):", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 6))
        self.raw_search_var = tk.StringVar()
        self.raw_search_var.trace("w", lambda *args: self.schedule_raw_search())
        ent_raw_search = ttk.Entry(raw_search_bar, textvariable=self.raw_search_var, width=30, font=('Consolas', 10))
        ent_raw_search.pack(side='left', padx=(0, 6))

        btn_raw_next = tk.Button(raw_search_bar, text="Next ⬇", bg=self.btn_bg, fg=self.text_color, relief="flat", command=self.raw_find_next, padx=8, pady=2)
        btn_raw_next.pack(side='left', padx=(0, 4))

        btn_raw_prev = tk.Button(raw_search_bar, text="Prev ⬆", bg=self.btn_bg, fg=self.text_color, relief="flat", command=self.raw_find_prev, padx=8, pady=2)
        btn_raw_prev.pack(side='left', padx=(0, 10))

        self.lbl_raw_match_count = ttk.Label(raw_search_bar, text="0 results", font=('Segoe UI', 9, 'italic'))
        self.lbl_raw_match_count.pack(side='left', padx=5)

        # Text Container for Raw Editor
        raw_text_container = ttk.Frame(self.raw_editor_frame)
        raw_text_container.grid(row=1, column=0, sticky='nsew')
        raw_text_container.rowconfigure(0, weight=1)
        raw_text_container.columnconfigure(0, weight=1)

        self.json_text = tk.Text(raw_text_container, bg="#12121a", fg="#d4d4d4", insertbackground="white", font=("Consolas", 10), wrap="none", relief="flat")
        y_scroll = ttk.Scrollbar(raw_text_container, orient="vertical", command=self.json_text.yview)
        x_scroll = ttk.Scrollbar(raw_text_container, orient="horizontal", command=self.json_text.xview)
        
        self.json_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.json_text.grid(row=0, column=0, sticky='nsew')
        y_scroll.grid(row=0, column=1, sticky='ns')
        x_scroll.grid(row=1, column=0, sticky='ew')

        # Syntax & Search Highlight Tags
        self.json_text.tag_configure("key", foreground="#9cdcfe")
        self.json_text.tag_configure("string", foreground="#ce9178")
        self.json_text.tag_configure("number", foreground="#b5cea8")
        self.json_text.tag_configure("boolean", foreground="#569cd6")
        self.json_text.tag_configure("search_match", background="#513511", foreground="#ffffff")
        self.json_text.tag_configure("search_current", background="#ff7b00", foreground="#ffffff")

        self.json_text.bind("<KeyRelease>", self.schedule_syntax_highlighting)
        self.json_text.bind("<Configure>", self.schedule_syntax_highlighting)
        self.json_text.bind("<MouseWheel>", self.schedule_syntax_highlighting)

        # --- View 2: Treeview Graphical Inspector/Editor with Search Bar ---
        self.gui_editor_frame = ttk.Frame(self.editor_container)
        self.gui_editor_frame.grid(row=0, column=0, sticky='nsew')
        self.gui_editor_frame.rowconfigure(1, weight=1)
        self.gui_editor_frame.columnconfigure(0, weight=1)

        # Search / Filter Bar Frame
        search_bar_frame = ttk.Frame(self.gui_editor_frame)
        search_bar_frame.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        
        ttk.Label(search_bar_frame, text="🔍 Search Properties (Zone, Name, Color, etc.):", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.filter_treeview())
        ent_search = ttk.Entry(search_bar_frame, textvariable=self.search_var, width=45, font=('Consolas', 10))
        ent_search.pack(side='left', fill='x', expand=True, padx=(0, 8))
        
        btn_clear_search = tk.Button(search_bar_frame, text="Clear", bg=self.btn_bg, fg=self.text_color, relief="flat", command=lambda: self.search_var.set(""))
        btn_clear_search.pack(side='left')

        # Treeview Widget with Detailed Headers & Fancy JSON Syntax Tags
        tree_container = ttk.Frame(self.gui_editor_frame)
        tree_container.grid(row=1, column=0, sticky='nsew')
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_container, columns=("Type", "Value"), selectmode="browse")
        self.tree.heading("#0", text="Property / Key (Detailed Preview)")
        self.tree.heading("Type", text="Data Type")
        self.tree.heading("Value", text="Current Value")
        self.tree.column("#0", width=420, anchor="w")
        self.tree.column("Type", width=110, anchor="center")
        self.tree.column("Value", width=350, anchor="w")

        # Configure Fancy JSON Theme Colors for Tree View tags
        self.tree.tag_configure("tag_folder", foreground="#dcdcaa")  # Yellowish for folders/containers
        self.tree.tag_configure("tag_key", foreground="#9cdcfe")     # Light Blue for keys
        self.tree.tag_configure("tag_string", foreground="#ce9178")  # Orange/Brown for strings
        self.tree.tag_configure("tag_number", foreground="#b5cea8")  # Light Green for numbers/floats
        self.tree.tag_configure("tag_bool", foreground="#569cd6")    # Blue for booleans

        tree_y_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        tree_x_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_y_scroll.set, xscrollcommand=tree_x_scroll.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        tree_y_scroll.grid(row=0, column=1, sticky='ns')
        tree_x_scroll.grid(row=1, column=0, sticky='ew')

        # Bind the Treeview selection event to dynamically update the property inspector
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_selection)

        # Dynamic Corresponding Type Inspector Frame
        self.inspector_frame = ttk.LabelFrame(self.gui_editor_frame, text=" Selected Property Inspector (Dynamic Type Editor) ")
        self.inspector_frame.grid(row=2, column=0, sticky='ew', pady=(10, 0))
        self.inspector_frame.columnconfigure(1, weight=1)

        self.lbl_inspector_info = ttk.Label(self.inspector_frame, text="Select a property above to edit.", font=('Segoe UI', 9, 'italic'))
        self.lbl_inspector_info.grid(row=0, column=0, columnspan=3, sticky='w', padx=10, pady=8)

        self.raw_editor_frame.tkraise()

    def create_docs_tab(self):
        docs_frame = ttk.Frame(self.tab_docs, padding=10)
        docs_frame.pack(fill='both', expand=True, padx=10, pady=10)
        docs_frame.rowconfigure(1, weight=1)
        docs_frame.columnconfigure(0, weight=1)

        header_lbl = ttk.Label(docs_frame, text="📜 Atlas Fallen Save File Architecture & Specifications", font=('Segoe UI', 11, 'bold'), foreground="#ff7b00")
        header_lbl.grid(row=0, column=0, sticky='w', pady=(0, 8))

        text_container = ttk.Frame(docs_frame)
        text_container.grid(row=1, column=0, sticky='nsew')
        text_container.rowconfigure(0, weight=1)
        text_container.columnconfigure(0, weight=1)

        self.docs_text = tk.Text(text_container, bg="#12121a", fg="#d4d4d4", insertbackground="white", font=("Consolas", 10), wrap="word", relief="flat", padx=10, pady=10)
        docs_y_scroll = ttk.Scrollbar(text_container, orient="vertical", command=self.docs_text.yview)
        
        self.docs_text.configure(yscrollcommand=docs_y_scroll.set)
        self.docs_text.grid(row=0, column=0, sticky='nsew')
        docs_y_scroll.grid(row=0, column=1, sticky='ns')

        # Configure Syntax Highlight Tags for Docs
        self.docs_text.tag_configure("doc_h1", foreground="#ff7b00", font=("Consolas", 12, "bold"))
        self.docs_text.tag_configure("doc_h2", foreground="#4ec9b0", font=("Consolas", 11, "bold"))
        self.docs_text.tag_configure("doc_h3", foreground="#9cdcfe", font=("Consolas", 10, "bold"))
        self.docs_text.tag_configure("doc_code", foreground="#ce9178", background="#2a2a40")
        self.docs_text.tag_configure("doc_keyword", foreground="#569cd6", font=("Consolas", 10, "bold"))

        # Load format-docs.md content dynamically
        docs_path = os.path.join(BASE_DIR, "format-docs.md")
        if os.path.exists(docs_path):
            try:
                with open(docs_path, 'r', encoding='utf-8') as f:
                    docs_content = f.read()
                self.docs_text.insert("1.0", docs_content)
                self.apply_docs_syntax_highlighting()
            except Exception as e:
                self.docs_text.insert("1.0", f"Error loading documentation file:\n{str(e)}")
        else:
            self.docs_text.insert("1.0", "[format-docs.md not found in bundle paths]")

        self.docs_text.configure(state="disabled") # Make read-only viewer

    def apply_docs_syntax_highlighting(self):
        content = self.docs_text.get("1.0", tk.END)
        
        # Regex patterns for Markdown documentation elements
        h1_regex = re.compile(r'^#\s+.*$', re.MULTILINE)
        h2_regex = re.compile(r'^##\s+.*$', re.MULTILINE)
        h3_regex = re.compile(r'^###\s+.*$', re.MULTILINE)
        code_regex = re.compile(r'`([^`]+)`')
        keyword_regex = re.compile(r'\b(uint32_t|int32_t|uint64_t|uint8_t|int8_t|uint16_t|bool|string|binary|vec3|Variant|Name32|Ref|Curve|Rect|Color|Degree|Radian|Rotate|quat|UDim|UVector2)\b')

        for match in h1_regex.finditer(content):
            self.docs_text.tag_add("doc_h1", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")

        for match in h2_regex.finditer(content):
            self.docs_text.tag_add("doc_h2", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")

        for match in h3_regex.finditer(content):
            self.docs_text.tag_add("doc_h3", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")

        for match in code_regex.finditer(content):
            self.docs_text.tag_add("doc_code", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")

        for match in keyword_regex.finditer(content):
            self.docs_text.tag_add("doc_keyword", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")

    def schedule_raw_search(self):
        """Debounces and safeguards raw JSON search so typing is lightning-fast and non-blocking."""
        if self._raw_search_job:
            self.root.after_cancel(self._raw_search_job)
        self._raw_search_job = self.root.after(300, self.perform_raw_search)

    def perform_raw_search(self):
        query = self.raw_search_var.get().strip()
        
        if len(query) < 2:
            self.json_text.tag_remove("search_match", "1.0", tk.END)
            self.json_text.tag_remove("search_current", "1.0", tk.END)
            self.raw_match_indices = []
            if len(query) == 1:
                self.lbl_raw_match_count.config(text="Type at least 2 chars...")
            else:
                self.lbl_raw_match_count.config(text="0 results")
            return

        self.lbl_raw_match_count.config(text="Searching...")

        # Run lightning-fast string lookup in background thread using pure Python index math
        def background_search():
            text_content = self.json_text.get("1.0", tk.END)
            lower_content = text_content.lower()
            lower_query = query.lower()
            
            # Pre-calculate line offsets for O(1) coordinate conversion without calling Tkinter widget methods
            line_offsets = [0]
            curr = 0
            for line in text_content.splitlines(keepends=True):
                curr += len(line)
                line_offsets.append(curr)

            def get_tk_index(char_pos):
                line_idx = bisect.bisect_right(line_offsets, char_pos) - 1
                line_idx = max(0, min(line_idx, len(line_offsets) - 2))
                col_idx = char_pos - line_offsets[line_idx]
                return f"{line_idx + 1}.{col_idx}"

            matches = []
            idx = 0
            while True:
                idx = lower_content.find(lower_query, idx)
                if idx == -1:
                    break
                
                pos = get_tk_index(idx)
                end = get_tk_index(idx + len(query))
                matches.append((pos, end))
                idx += len(query)

            self.root.after(0, lambda: self.apply_raw_search_results(matches))

        threading.Thread(target=background_search, daemon=True).start()

    def apply_raw_search_results(self, matches):
        self.json_text.tag_remove("search_match", "1.0", tk.END)
        self.json_text.tag_remove("search_current", "1.0", tk.END)
        self.raw_match_indices = matches

        count = len(self.raw_match_indices)
        if count > 0:
            self.raw_current_match_idx = 0
            self.highlight_current_raw_match()
        else:
            self.lbl_raw_match_count.config(text="0 results")

    def highlight_current_raw_match(self):
        self.json_text.tag_remove("search_match", "1.0", tk.END)
        self.json_text.tag_remove("search_current", "1.0", tk.END)
        
        if self.raw_match_indices:
            # Highlight a window of matches around the current index for smooth visual context
            start_win = max(0, self.raw_current_match_idx - 30)
            end_win = min(len(self.raw_match_indices), self.raw_current_match_idx + 30)
            for i in range(start_win, end_win):
                p, e = self.raw_match_indices[i]
                self.json_text.tag_add("search_match", p, e)

            # Highlight exact active match and scroll to it
            pos, end = self.raw_match_indices[self.raw_current_match_idx]
            self.json_text.tag_add("search_current", pos, end)
            self.json_text.see(pos)
            self.lbl_raw_match_count.config(text=f"{self.raw_current_match_idx + 1} of {len(self.raw_match_indices):,} results")

    def raw_find_next(self):
        if self.raw_match_indices:
            self.raw_current_match_idx = (self.raw_current_match_idx + 1) % len(self.raw_match_indices)
            self.highlight_current_raw_match()

    def raw_find_prev(self):
        if self.raw_match_indices:
            self.raw_current_match_idx = (self.raw_current_match_idx - 1) % len(self.raw_match_indices)
            self.highlight_current_raw_match()

    def toggle_editor_view(self):
        if self.gui_mode_var.get():
            try:
                raw_text = self.json_text.get("1.0", tk.END).strip()
                if not raw_text:
                    messagebox.showwarning("Warning", "No save JSON loaded to display in GUI mode.")
                    self.gui_mode_var.set(False)
                    return
                json_data = json.loads(raw_text)
                
                self.log("[Editor] Building detailed Treeview structure...")
                self.build_treeview_form(json_data)
                self.gui_editor_frame.tkraise()
                self.log("[Editor] Graphical Editor loaded with full previews and search enabled.")
            except json.JSONDecodeError as jde:
                messagebox.showerror("JSON Error", f"Cannot switch to GUI editor due to invalid JSON syntax:\n{str(jde)}")
                self.gui_mode_var.set(False)
        else:
            try:
                updated_json = self.serialize_treeview_form()
                formatted_json = json.dumps(updated_json, indent=4)
                self.json_text.delete("1.0", tk.END)
                self.json_text.insert("1.0", formatted_json)
                self.apply_syntax_highlighting()
                self.raw_editor_frame.tkraise()
                self.log("[Editor] Synced Treeview changes back to Raw JSON view.")
            except Exception as e:
                messagebox.showerror("Sync Error", f"Failed to serialize tree data back to JSON:\n{str(e)}")

    def get_tree_tag(self, val, data_type):
        if data_type in ("dict", "list"):
            return "tag_folder"
        elif data_type == "bool":
            return "tag_bool"
        elif data_type in ("int", "float"):
            return "tag_number"
        else:
            return "tag_string"

    def build_treeview_form(self, data):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map.clear()
        self.root_json_data = data
        self.populate_tree("", data)

    def populate_tree(self, parent_id, node_data):
        if isinstance(node_data, dict):
            for key, val0 in node_data.items():
                display_label = self.format_preview_label(key, val0)
                dtype = type(val0).__name__
                tag = self.get_tree_tag(val0, dtype)
                
                if isinstance(val0, (dict, list)):
                    node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, f"[{len(val0)} items]"), tags=(tag,))
                    self.tree_item_map[node_id] = (node_data, key, val0)
                    self.populate_tree(node_id, val0)
                else:
                    node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, str(val0)), tags=(tag,))
                    self.tree_item_map[node_id] = (node_data, key, val0)
        elif isinstance(node_data, list):
            for idx, item in enumerate(node_data):
                display_label = f"[{idx}] ➔ {type(item).__name__}"
                dtype = type(item).__name__
                tag = self.get_tree_tag(item, dtype)
                
                if isinstance(item, (dict, list)):
                    node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, f"[{len(item)} items]"), tags=(tag,))
                    self.tree_item_map[node_id] = (node_data, idx, item)
                    self.populate_tree(node_id, item)
                else:
                    node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, str(item)), tags=(tag,))
                    self.tree_item_map[node_id] = (node_data, idx, item)

    def format_preview_label(self, key, val):
        if isinstance(val, dict):
            preview_keys = list(val.keys())[:3]
            preview_str = ", ".join(str(k) for k in preview_keys)
            return f"📂 {key}  ({len(val)} keys: {preview_str}...) "
        elif isinstance(val, list):
            return f"📂 {key}  (List of {len(val)} items)"
        else:
            return f"🏷️ {key}"

    def filter_treeview(self):
        query = self.search_var.get().strip().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.tree_item_map.clear()

        if not query:
            self.populate_tree("", self.root_json_data)
            return

        self.populate_filtered_node("", self.root_json_data, query, force_full=False)

    def node_has_match(self, node_data, query):
        if isinstance(node_data, dict):
            for k, v in node_data.items():
                if query in str(k).lower():
                    return True
                if isinstance(v, (dict, list)):
                    if self.node_has_match(v, query):
                        return True
                elif query in str(v).lower():
                    return True
        elif isinstance(node_data, list):
            for item in node_data:
                if isinstance(item, (dict, list)):
                    if self.node_has_match(item, query):
                        return True
                elif query in str(item).lower():
                    return True
        return False

    def populate_filtered_node(self, parent_id, node_data, query, force_full=False):
        if isinstance(node_data, dict):
            for key, val0 in node_data.items():
                key_match = query in str(key).lower()
                should_force = force_full or key_match
                dtype = type(val0).__name__
                tag = self.get_tree_tag(val0, dtype)
                
                if isinstance(val0, (dict, list)):
                    if should_force or self.node_has_match(val0, query):
                        display_label = self.format_preview_label(key, val0)
                        node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, f"[{len(val0)} items]"), open=False, tags=(tag,))
                        self.tree_item_map[node_id] = (node_data, key, val0)
                        self.populate_filtered_node(node_id, val0, query, force_full=should_force)
                else:
                    val_match = query in str(val0).lower()
                    if should_force or val_match:
                        display_label = f"🏷️ {key}"
                        node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, str(val0)), open=False, tags=(tag,))
                        self.tree_item_map[node_id] = (node_data, key, val0)
        elif isinstance(node_data, list):
            for idx, item in enumerate(node_data):
                dtype = type(item).__name__
                tag = self.get_tree_tag(item, dtype)
                
                if isinstance(item, (dict, list)):
                    if force_full or self.node_has_match(item, query):
                        display_label = f"[{idx}] ➔ {dtype}"
                        node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, f"[{len(item)} items]"), open=False, tags=(tag,))
                        self.tree_item_map[node_id] = (node_data, idx, item)
                        self.populate_filtered_node(node_id, item, query, force_full=force_full)
                else:
                    if force_full or query in str(item).lower():
                        display_label = f"[{idx}] ➔ {dtype}"
                        node_id = self.tree.insert(parent_id, "end", text=display_label, values=(dtype, str(item)), open=False, tags=(tag,))
                        self.tree_item_map[node_id] = (node_data, idx, item)

    def on_tree_selection(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        item_id = selected_items[0]
        vals = self.tree.item(item_id, "values")
        key_name = self.tree.item(item_id, "text")

        for widget in self.inspector_frame.winfo_children():
            widget.destroy()

        if not vals:
            return

        data_type = vals[0]
        val_str = vals[1]

        if (data_type == "str" and len(val_str) > 80) or any(term in key_name.lower() for term in ("binary", "base64", "rest", "image", "blob")):
            messagebox.showwarning("Oops", "Oops you cant edit the binary Base 64 and you should not even try")
            ttk.Label(self.inspector_frame, text="🔒 PROTECTED BINARY / BASE64 DATA (Not Editable)", foreground="#ff5555", font=('Segoe UI', 9, 'bold')).pack(padx=15, pady=12)
            return

        if data_type in ("dict", "list"):
            ttk.Label(self.inspector_frame, text=f"📁 Container Node: {key_name} ({data_type} with {val_str})", font=('Segoe UI', 9, 'italic')).pack(padx=15, pady=12)
            return

        ttk.Label(self.inspector_frame, text=f"Editing Property:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', padx=10, pady=8)
        ttk.Label(self.inspector_frame, text=key_name, font=('Consolas', 9), foreground="#00ffcc").grid(row=0, column=1, sticky='w', padx=5, pady=8)

        if data_type == "bool":
            self.inspect_var = tk.BooleanVar(value=(val_str.lower() in ("true", "1", "yes")))
            chk = ttk.Checkbutton(self.inspector_frame, text="True / False Boolean Switch", variable=self.inspect_var)
            chk.grid(row=1, column=0, columnspan=2, sticky='w', padx=10, pady=8)

        elif data_type in ("int", "float"):
            ttk.Label(self.inspector_frame, text=f"Numeric Value ({data_type}):").grid(row=1, column=0, sticky='w', padx=10, pady=8)
            self.inspect_var = tk.StringVar(value=val_str)
            ent = ttk.Entry(self.inspector_frame, textvariable=self.inspect_var, width=30, font=('Consolas', 10))
            ent.grid(row=1, column=1, sticky='we', padx=10, pady=8)

        elif "color" in key_name.lower() or (data_type == "str" and val_str.startswith("#") and len(val_str) in (4, 7)):
            ttk.Label(self.inspector_frame, text="Color Key Hex/String:").grid(row=1, column=0, sticky='w', padx=10, pady=8)
            self.inspect_var = tk.StringVar(value=val_str)
            ent = ttk.Entry(self.inspector_frame, textvariable=self.inspect_var, width=25, font=('Consolas', 10))
            ent.grid(row=1, column=1, sticky='w', padx=10, pady=8)
            
            btn_color = tk.Button(self.inspector_frame, text="🎨 Pick Color", bg=self.btn_bg, fg=self.text_color, relief="flat", command=lambda: self.pick_color(self.inspect_var))
            btn_color.grid(row=1, column=2, padx=10, pady=8)

        else:
            ttk.Label(self.inspector_frame, text="String Value:").grid(row=1, column=0, sticky='w', padx=10, pady=8)
            self.inspect_var = tk.StringVar(value=val_str)
            ent = ttk.Entry(self.inspector_frame, textvariable=self.inspect_var, width=50, font=('Consolas', 10))
            ent.grid(row=1, column=1, columnspan=2, sticky='we', padx=10, pady=8)

        btn_apply = tk.Button(self.inspector_frame, text="✨ Apply Property Update", bg="#ff7b00", fg="#ffffff", font=('Segoe UI', 9, 'bold'), relief="flat", padx=15, pady=6, command=lambda: self.apply_tree_node_edit(item_id, data_type))
        btn_apply.grid(row=2, column=0, columnspan=3, pady=12)

    def pick_color(self, var):
        color_code = colorchooser.askcolor(title="Select Color Key")
        if color_code[1]:
            var.set(color_code[1])

    def apply_tree_node_edit(self, item_id, data_type):
        new_val = self.inspect_var.get()

        try:
            if data_type == "bool":
                typed_val = bool(new_val)
            elif data_type == "int":
                typed_val = int(new_val)
            elif data_type == "float":
                typed_val = float(new_val)
            else:
                typed_val = str(new_val)
        except ValueError:
            typed_val = new_val

        container_info = self.tree_item_map.get(item_id)
        if container_info:
            container, key_or_idx, _ = container_info
            container[key_or_idx] = typed_val
            
            self.tree.item(item_id, values=(data_type, str(typed_val)))
            self.log(f"[Editor] Successfully updated property '{key_or_idx}' to: {typed_val}")
            messagebox.showinfo("Success", f"Property '{key_or_idx}' updated successfully!")

    def serialize_treeview_form(self):
        return self.root_json_data

    def schedule_syntax_highlighting(self, event=None):
        if self._highlight_job:
            self.root.after_cancel(self._highlight_job)
        self._highlight_job = self.root.after(150, self.apply_syntax_highlighting)

    def apply_syntax_highlighting(self):
        try:
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
        frame = ttk.Frame(self.tab_hash, padding=10)
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

        cmd = [sys.executable, SAVEGAME_SCRIPT, mode, infile, outfile]

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

                cmd = [sys.executable, SAVEGAME_SCRIPT, "extract_json", filename, temp_json_path]
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
                    self.gui_mode_var.set(False)
                    self.raw_editor_frame.tkraise()
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
                if self.gui_mode_var.get():
                    self.root.after(0, lambda: self.gui_mode_var.set(False))
                    self.root.after(0, self.toggle_editor_view)

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

                cmd = [sys.executable, SAVEGAME_SCRIPT, "compose_json", self.loaded_sav_path, temp_json_path, out_filename, "--compress"]
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
                with open(binfile, 'rb') as f_in, open(os.path.join(os.path.dirname(HASH_SCRIPT), 'name32 table.bin'), 'wb') as f_out:
                    f_out.write(f_in.read())
                
                process = subprocess.Popen([sys.executable, HASH_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
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
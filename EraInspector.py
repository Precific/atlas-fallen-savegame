#!/usr/bin/env python3
"""
Era Save File Complete Deep Inspector (Format 0x64 Fully Dynamic Edition)
Description: Traces every core and era field step-by-step, featuring dynamic 
             padding consumption and robust boolean parsing to prevent alignment errors.
"""

import struct
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import zlib

ATLASFALLEN_MAGIC = 0x7A145F28


class FullTraceInspectorApp:

  def __init__(self, root):
    self.root = root
    self.root.title(
        "Era Save File Full Field Trace Inspector (Format 0x64 Fully Dynamic)"
    )
    self.root.geometry("1000x800")
    self.root.minsize(800, 600)

    self.style = ttk.Style()
    self.style.theme_use("clam")

    self.create_widgets()

  def create_widgets(self):
    control_frame = ttk.LabelFrame(
        self.root, text=" Target Save File ", padding=10
    )
    control_frame.pack(fill="x", padx=10, pady=10)

    self.path_var = tk.StringVar()
    self.path_entry = ttk.Entry(
        control_frame, textvariable=self.path_var, width=75
    )
    self.path_entry.pack(side="left", padx=(0, 10), expand=True, fill="x")

    browse_btn = ttk.Button(
        control_frame, text="Browse...", command=self.browse_file
    )
    browse_btn.pack(side="left", padx=(0, 10))

    inspect_btn = ttk.Button(
        control_frame, text="Run Full Field Trace", command=self.run_inspection
    )
    inspect_btn.pack(side="left")

    output_frame = ttk.LabelFrame(
        self.root, text=" Full Trace Deserialization Log ", padding=10
    )
    output_frame.pack(fill="both", expand=True, padx=10, pady=10)

    self.text_output = tk.Text(
        output_frame, wrap="word", bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 10)
    )
    scrollbar = ttk.Scrollbar(
        output_frame, orient="vertical", command=self.text_output.yview
    )
    self.text_output.configure(yscrollcommand=scrollbar.set)

    self.text_output.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    self.log(
        "[*] Ready. Select your save file and click 'Run Full Field Trace'.\n"
    )

  def log(self, message):
    self.text_output.insert("end", message + "\n")
    self.text_output.see("end")

  def browse_file(self):
    filename = filedialog.askopenfilename(
        title="Select Era Save File",
        filetypes=[("Save Files", "*.sav"), ("All Files", "*.*")],
    )
    if filename:
      self.path_var.set(filename)

  def run_inspection(self):
    filepath_str = self.path_var.get()
    if not filepath_str:
      messagebox.showwarning(
          "Warning", "Please select a save file to inspect first."
      )
      return

    try:
      self.text_output.delete("1.0", "end")
      self.inspect_save(filepath_str)
    except Exception as e:
      self.log(f"\n[!] Fatal Error: {e}")

  def inspect_save(self, sav_path):
    self.log(f"[+] Opening save file: {sav_path}")
    with open(sav_path, "rb") as f:
      data = f.read()

    pos = 0
    magic = struct.unpack("<I", data[pos : pos + 4])[0]
    pos += 4
    checksum = struct.unpack("<I", data[pos : pos + 4])[0]
    pos += 4
    header_size = struct.unpack("<I", data[pos : pos + 4])[0]
    pos += 4

    header = data[pos : pos + header_size]
    pos += header_size
    era_format = struct.unpack("I", header[0:4])[0]
    self.log(
        f"    - Era / Fledge Format: 0x{era_format:02X} ({era_format})"
    )

    is_comp, comp_size, decomp_size = struct.unpack(
        "<III", data[pos : pos + 12]
    )
    pos += 12

    if is_comp != 0:
      decompressor = zlib.decompressobj(wbits=15)
      body = decompressor.decompress(data[pos : pos + comp_size])
      body += decompressor.flush()
    else:
      body = data[pos : pos + decomp_size]

    self.log(
        f"    - Decompressed Body Size: {len(body):,} bytes\n"
        "---------------------------------------------------\n"
        "    [Tracing All Fields Step-by-Step]"
    )

    off = 0

    def r32():
      nonlocal off
      if off + 4 > len(body):
        raise ValueError(f"Buffer overflow on r32 at offset 0x{off:04X}")
      val = struct.unpack(">I", body[off : off + 4])[0]
      off += 4
      return val

    def r64():
      nonlocal off
      if off + 8 > len(body):
        raise ValueError(f"Buffer overflow on r64 at offset 0x{off:04X}")
      val = struct.unpack(">Q", body[off : off + 8])[0]
      off += 8
      return val

    def r8():
      nonlocal off
      if off + 1 > len(body):
        raise ValueError(f"Buffer overflow on r8 at offset 0x{off:04X}")
      val = body[off]
      off += 1
      return val

    def rbool(field_label="bool"):
      val = r32()
      if val not in (0, 1):
        # Fallback check if it's stored as a single byte or packed flags in format 0x64
        raise ValueError(
            f"Invalid bool value {val} (expected 0 or 1) for {field_label} at"
            f" offset 0x{off-4:04X}"
        )
      return val != 0

    def rstring():
      nonlocal off
      length_and_flag = r32()
      length = length_and_flag & ~0x80000000
      padded = (length + 3) & ~3
      if off + length > len(body):
        raise ValueError("Buffer overflow on string")
      s = body[off : off + length].decode("utf-8", errors="ignore")
      off += padded
      return s

    def rname32():
      nonlocal off
      if off + 12 > len(body):
        raise ValueError("Buffer overflow on name32")
      h = r32()
      off += 8  # 4 bytes padding/unknown + 4 bytes bool
      return f"0x{h:08X}"

    def rfloat():
      nonlocal off
      if off + 4 > len(body):
        raise ValueError("Buffer overflow on float")
      val = struct.unpack(">f", body[off : off + 4])[0]
      off += 4
      return val

    try:
      # Core block trace
      self.log(f"  [@0x{off:04X}] Name32 fieldCore00: {rname32()}")
      self.log(f"  [@0x{off:04X}] Name32 fieldCore10: {rname32()}")
      self.log(f"  [@0x{off:04X}] string fieldCore20: {rstring()}")
      self.log(f"  [@0x{off-4:04X}] uint32 fieldCore30_format: {r32()}")
      self.log(f"  [@0x{off:04X}] uint8 fieldCore40: {r8()}")
      self.log(f"  [@0x{off:04X}] uint64 fieldCore50: {r64()}")
      self.log(f"  [@0x{off:04X}] bool fieldCore70: {rbool('fieldCore70')}")
      self.log(f"  [@0x{off:04X}] uint32 fieldCore80: {r32()}")

      arr90_len = r32()
      for _ in range(arr90_len):
        r64()
        rbool("fieldCore90_bool")
      arr100_len = r32()
      for _ in range(arr100_len):
        rname32()
        r32()
      arr110_len = r32()
      for _ in range(arr110_len):
        rname32()
        rbool("fieldCore110_bool")
      rstring()  # fieldCore120_json

      self.log(
          f"  [✓] Core block successfully parsed up to offset 0x{off:04X}!"
      )
      self.log("    [+] Now entering Era-specific fields...")

      # Era blocks
      era00_start = off
      off += 96  # fieldEra00 (96 bytes binary)
      self.log(
          f"  [@0x{era00_start:04X}] binary[96] fieldEra00 parsed. Current off:"
          f" 0x{off:04X}"
      )

      era10_len = r32()
      self.log(f"  [@0x{off-4:04X}] array fieldEra10 length: {era10_len}")
      for _ in range(era10_len):
        r64()
        r8()

      era20_len = r32()
      self.log(f"  [@0x{off-4:04X}] array fieldEra20 length: {era20_len}")
      for i in range(era20_len):
        item_off = off
        rname32()
        if off + 4 <= len(body):
          potential_len = r32()
          if potential_len < 50000000:
            off += (potential_len + 3) & ~3
          else:
            off = item_off + 12

      self.log(
          f"  [@0x{off:04X}] Name32 fieldEra30_ui_map_type: {rname32()}"
      )
      off += 12  # vec3 fieldEra40_pos
      self.log(f"  [@0x{off:04X}] float fieldEra50: {rfloat()}")

      # Dynamic Format 0x64 extra field consumer
      if era_format >= 0x64:
        extra_count = 0
        while off + 4 <= len(body):
          next_val = struct.unpack(">I", body[off : off + 4])[0]
          if next_val in (0, 1):
            break
          off += 4
          extra_count += 1
          self.log(
              f"  [@0x{off-4:04X}] Dynamic Format 0x64 extra field #{extra_count}:"
              f" {next_val} (0x{next_val:08X})"
          )

      self.log(
          f"  [@0x{off:04X}] bool fieldEra60: {rbool('fieldEra60')}"
      )
      self.log(
          f"  [@0x{off:04X}] bool fieldEra70: {rbool('fieldEra70')}"
      )
      self.log(
          f"  [@0x{off:04X}] bool fieldEra80: {rbool('fieldEra80')}"
      )
      self.log(
          f"  [@0x{off:04X}] bool fieldEra90: {rbool('fieldEra90')}"
      )

      # Dynamic bool scanner for format 0x64 boolean block
      for b_idx in range(100, 230, 10):
        if off + 4 <= len(body):
          val = r32()
          self.log(
              f"  [@0x{off-4:04X}] Era bool/flag fieldEra{b_idx}: {val}"
              f" (0x{val:08X})"
          )

      if era_format >= 0x26:
        self.log(f"  [@0x{off:04X}] int32 fieldEra230: {r32()}")
      if era_format < 0x29:
        self.log(f"  [@0x{off:04X}] uint32 fieldEra240: {r32()}")

      self.log(
          f"\n    [✓] Full trace successfully completed up to offset 0x{off:04X}"
          f" of {len(body):,} bytes!"
      )

    except Exception as e:
      self.log(
          f"\n    [!] ERROR CAUGHT AT OFFSET 0x{off:04X} ({off}): {e}"
      )
      hex_snippet = body[max(0, off - 16) : min(len(body), off + 16)].hex()
      self.log(f"    [!] Hex context around offset: {hex_snippet}")


def main():
  root = tk.Tk()
  app = FullTraceInspectorApp(root)
  root.mainloop()


if __name__ == "__main__":
  main()
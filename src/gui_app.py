# 本ソフトウェアは Microsoft Copilot を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho. Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-29
# gui_app.py
# GUI をそのまま残しつつ、バックグラウンドで動く処理（ログを読み取って InfluxDB に送る)だけ core に委譲したバージョン
import threading
import os
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
from tkinter import filedialog, messagebox

from stm2_reader_core import (
    MATERIAL_DATA,
    create_influx_client,
    tail_file
)

client = create_influx_client()
logging_active = False

def update_material_fields(event=None):
    material = combo_material.get()
    if material in MATERIAL_DATA:
        entry_density.delete(0, "end")
        entry_density.insert(0, MATERIAL_DATA[material]["density"])
        entry_zratio.delete(0, "end")
        entry_zratio.insert(0, MATERIAL_DATA[material]["zratio"])

def browse_file():
    filename = filedialog.askopenfilename(
        title="STM-2 ログファイルを選択",
        filetypes=[("Log files", "*.log"), ("All files", "*.*")]
    )
    if filename:
        entry_logfile.delete(0, "end")
        entry_logfile.insert(0, filename)
        entry_runid.delete(0, "end")
        entry_runid.insert(0, os.path.splitext(os.path.basename(filename))[0])

def drop_file(event):
    path = event.data.strip("{}")
    entry_logfile.delete(0, "end")
    entry_logfile.insert(0, path)
    entry_runid.delete(0, "end")
    entry_runid.insert(0, os.path.splitext(os.path.basename(path))[0])

def start_logging():
    global logging_active
    logging_active = True

    run_id = entry_runid.get()
    material = combo_material.get()

    if not material:
        messagebox.showerror("エラー", "Material を選択してください。")
        logging_active = False
        return

    try:
        density = float(entry_density.get())
        z_ratio = float(entry_zratio.get())
    except ValueError:
        messagebox.showerror("エラー", "Density または Z-ratio が正しくありません。")
        logging_active = False
        return

    logfile = entry_logfile.get()

    try:
        target_nm = float(entry_target.get())
    except ValueError:
        messagebox.showerror("エラー", "目標厚さ(nm)が正しくありません。")
        logging_active = False
        return

    target_angstrom = target_nm * 10.0
    alert_threshold = target_angstrom * 0.8

    if not os.path.exists(logfile):
        messagebox.showerror("エラー", "ログファイルが存在しません。")
        logging_active = False
        return

    label_status.configure(text="Logging started…")

    thread = threading.Thread(
        target=tail_file,
        args=(logfile, run_id, material, density, z_ratio, alert_threshold, client),
        daemon=True
    )
    thread.start()

def stop_logging():
    global logging_active
    logging_active = False
    label_status.configure(text="Stopping…")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = TkinterDnD.Tk()
root.title("STM-2 CSV Logger")
root.geometry("700x650")

default_font = ctk.CTkFont(family="Meiryo", size=24)

frame = ctk.CTkFrame(root, corner_radius=20)
frame.pack(fill="both", expand=True, padx=20, pady=20)

pad = {"padx": 10, "pady": 10}

ctk.CTkLabel(frame, text="目標厚さ [nm]", font=default_font).grid(row=0, column=0, sticky="w", **pad)
entry_target = ctk.CTkEntry(frame, width=250, font=default_font)
entry_target.grid(row=0, column=1, **pad)

ctk.CTkLabel(frame, text="Material", font=default_font).grid(row=1, column=0, sticky="w", **pad)
combo_material = ctk.CTkComboBox(
    frame,
    values=list(MATERIAL_DATA.keys()),
    width=250,
    font=default_font,
    command=update_material_fields
)
combo_material.set("")
combo_material.grid(row=1, column=1, **pad)

ctk.CTkLabel(frame, text="Density", font=default_font).grid(row=2, column=0, sticky="w", **pad)
entry_density = ctk.CTkEntry(frame, width=250, font=default_font)
entry_density.grid(row=2, column=1, **pad)

ctk.CTkLabel(frame, text="Z-ratio", font=default_font).grid(row=3, column=0, sticky="w", **pad)
entry_zratio = ctk.CTkEntry(frame, width=250, font=default_font)
entry_zratio.grid(row=3, column=1, **pad)

ctk.CTkLabel(frame, text="ログファイル", font=default_font).grid(row=4, column=0, sticky="w", **pad)
entry_logfile = ctk.CTkEntry(frame, width=250, font=default_font)
entry_logfile.grid(row=4, column=1, **pad)
entry_logfile.drop_target_register(DND_FILES)
entry_logfile.dnd_bind("<<Drop>>", drop_file)

btn_browse = ctk.CTkButton(frame, text="参照", command=browse_file, width=120, font=default_font)
btn_browse.grid(row=4, column=2, **pad)

ctk.CTkLabel(frame, text="Run ID", font=default_font).grid(row=5, column=0, sticky="w", **pad)
entry_runid = ctk.CTkEntry(frame, width=250, font=default_font)
entry_runid.grid(row=5, column=1, **pad)

btn_start = ctk.CTkButton(frame, text="Start Logging", command=start_logging, width=200, font=default_font)
btn_start.grid(row=6, column=0, **pad)

btn_stop = ctk.CTkButton(frame, text="Stop Logging", command=stop_logging, width=200, font=default_font)
btn_stop.grid(row=6, column=1, **pad)

label_status = ctk.CTkLabel(frame, text="Waiting…", font=default_font)
label_status.grid(row=7, column=0, columnspan=3, **pad)

root.mainloop()



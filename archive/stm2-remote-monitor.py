# -------------------------------------------------------------
# 本ソフトウェアは Microsoft Copilot を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho. Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-26
#
# pip install influxdb
# pip install customtkinter
# pip install tkinterdnd2
# -------------------------------------------------------------

import time
import threading
from influxdb import InfluxDBClient
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
from tkinter import filedialog, messagebox
import os

# --- 材料データ ---
# MATERIAL_DATA の出典
# 密度（Density）:
#   （株）高純度化学研究所 サポートブック 2022〜 ・Webサイト
# Z-RATIO:
#   ・水晶発振式成膜コントローラ説明書（2005/09/30）p.62〜63
#   ・元素周期表
#   ・INFICON STM-2 説明書 A-1〜
MATERIAL_DATA = {
    "Al":  {"density": 2.699, "zratio": 1.08},
    "Au":  {"density": 19.320, "zratio": 0.381},
    "CaO": {"density": 3.350, "zratio": 1.000},
    "Cr":  {"density": 7.19,  "zratio": 0.305},
    "Cu":  {"density": 8.96,  "zratio": 0.437},
    "Fe":  {"density": 7.874, "zratio": 0.349},
    "Ge":  {"density": 5.323, "zratio": 0.516},
    "Mg":  {"density": 1.740, "zratio": 1.610},
    "Mn":  {"density": 7.44,  "zratio": 0.377},
    "Pb":  {"density": 11.350, "zratio": 1.13},
    "Sn":  {"density": 7.310, "zratio": 0.72},
    "Tb":  {"density": 8.229, "zratio": 0.66},
    "Ti":  {"density": 4.54,  "zratio": 0.628},
}

# --- InfluxDB ---
client = InfluxDBClient(host="localhost", port=8086)
client.switch_database("stm2")

logging_active = False
prev_alert_state = None


# --- CSV 1行パース ---
def parse_csv_line(line):
    parts = [p.strip() for p in line.split(",") if p.strip()]
    if len(parts) != 4:
        return None
    try:
        return {
            "time": float(parts[0]),
            "rate": float(parts[1]),
            "thickness": float(parts[2]),
            "frequency": float(parts[3])
        }
    except ValueError:
        return None


# --- tail 処理 ---
def tail_file(filepath, run_id, material, density, z_ratio, alert_threshold):
    global logging_active, prev_alert_state

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            f.seek(0, 2)

            while logging_active:
                line = f.readline()
                if not line:
                    time.sleep(0.2)
                    continue

                line = line.strip()

                if line.startswith(("Start", "Stop", "Time")):
                    continue

                data = parse_csv_line(line)
                if not data:
                    continue

                json_body = [{
                    "measurement": "stm2",
                    "tags": {
                        "run_id": run_id,
                        "material": material,
                        "density": density,
                        "z_ratio": z_ratio
                    },
                    "fields": {
                        "time": data["time"],
                        "rate": data["rate"],
                        "thickness": data["thickness"],
                        "frequency": data["frequency"]
                    }
                }]

                client.write_points(json_body)

                alert_state = 1 if data["thickness"] >= alert_threshold else 0

                if alert_state != prev_alert_state:
                    client.write_points([{
                        "measurement": "stm2_settings",
                        "tags": {"run_id": run_id},
                        "fields": {"last": alert_state}
                    }])
                    prev_alert_state = alert_state

    except Exception as e:
        messagebox.showerror("エラー", f"ログ読み込み中にエラー:\n{e}")


# --- GUI 操作 ---
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

        run_id = os.path.splitext(os.path.basename(filename))[0]
        entry_runid.delete(0, "end")
        entry_runid.insert(0, run_id)


def drop_file(event):
    path = event.data.strip("{}")
    entry_logfile.delete(0, "end")
    entry_logfile.insert(0, path)

    run_id = os.path.splitext(os.path.basename(path))[0]
    entry_runid.delete(0, "end")
    entry_runid.insert(0, run_id)


def start_logging():
    global logging_active, prev_alert_state
    logging_active = True
    prev_alert_state = None   # ← ここでリセット

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

    client.write_points([{
        "measurement": "stm2_settings",
        "fields": {
            "target_thickness": target_angstrom,
            "alert_threshold": alert_threshold
        }
    }])

    if not os.path.exists(logfile):
        messagebox.showerror("エラー", "ログファイルが存在しません。")
        logging_active = False
        return

    label_status.configure(text="Logging started…")

    thread = threading.Thread(
        target=tail_file,
        args=(logfile, run_id, material, density, z_ratio, alert_threshold),
        daemon=True
    )
    thread.start()


def stop_logging():
    global logging_active
    logging_active = False
    label_status.configure(text="Stopping…")

# --- customtkinter GUI ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = TkinterDnD.Tk()
root.title("STM-2 CSV Logger")
root.geometry("700x650")

default_font = ctk.CTkFont(family="Meiryo", size=24)

frame = ctk.CTkFrame(root, corner_radius=20)
frame.pack(fill="both", expand=True, padx=20, pady=20)

pad = {"padx": 10, "pady": 10}

# --- Target thickness ---  row=0
ctk.CTkLabel(frame, text="目標厚さ [nm]", font=default_font).grid(row=0, column=0, sticky="w", **pad)
entry_target = ctk.CTkEntry(frame, width=250, font=default_font)
entry_target.grid(row=0, column=1, **pad)

# --- Material ---  row=1
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

# --- Density ---  row=2
ctk.CTkLabel(frame, text="Density", font=default_font).grid(row=2, column=0, sticky="w", **pad)
entry_density = ctk.CTkEntry(frame, width=250, font=default_font)
entry_density.grid(row=2, column=1, **pad)

# --- Z-ratio ---  row=3
ctk.CTkLabel(frame, text="Z-ratio", font=default_font).grid(row=3, column=0, sticky="w", **pad)
entry_zratio = ctk.CTkEntry(frame, width=250, font=default_font)
entry_zratio.grid(row=3, column=1, **pad)

# --- Log file ---  row=4
ctk.CTkLabel(frame, text="ログファイル", font=default_font).grid(row=4, column=0, sticky="w", **pad)
entry_logfile = ctk.CTkEntry(frame, width=250, font=default_font)
entry_logfile.grid(row=4, column=1, **pad)

entry_logfile.drop_target_register(DND_FILES)
entry_logfile.dnd_bind("<<Drop>>", drop_file)

btn_browse = ctk.CTkButton(frame, text="参照", command=browse_file, width=120, font=default_font)
btn_browse.grid(row=4, column=2, **pad)

# --- Run ID ---  row=5
ctk.CTkLabel(frame, text="Run ID", font=default_font).grid(row=5, column=0, sticky="w", **pad)
entry_runid = ctk.CTkEntry(frame, width=250, font=default_font)
entry_runid.grid(row=5, column=1, **pad)

# --- Buttons ---  row=6
btn_start = ctk.CTkButton(frame, text="Start Logging", command=start_logging, width=200, font=default_font)
btn_start.grid(row=6, column=0, **pad)

btn_stop = ctk.CTkButton(frame, text="Stop Logging", command=stop_logging, width=200, font=default_font)
btn_stop.grid(row=6, column=1, **pad)

# --- Status ---  row=7
label_status = ctk.CTkLabel(frame, text="Waiting…", font=default_font)
label_status.grid(row=7, column=0, columnspan=3, **pad)
root.mainloop()

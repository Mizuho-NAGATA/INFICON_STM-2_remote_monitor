# -------------------------------------------------------------
# 本ソフトウェアは Microsoft Copilot 、ChatGPT を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho.
# Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-30
#
# pip install influxdb
# pip install customtkinter
# pip install tkinterdnd2
# -------------------------------------------------------------

import time
import threading
import os
import csv
from influxdb import InfluxDBClient
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
from tkinter import filedialog, messagebox

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

# =========================
# InfluxDB
# =========================
client = InfluxDBClient(host="localhost", port=8086)
client.switch_database("stm2")

# =========================
# スレッド制御
# =========================
logging_event = threading.Event()
prev_alert_state = None

# =========================
# GUI スレッド呼び出し用
# =========================
def gui_call(func):
    root.after(0, func)

# =========================
# CSV 1行パース（堅牢版）
# =========================
def parse_csv_line(line):
    try:
        row = next(csv.reader([line]))
        if len(row) != 4:
            return None
        return {
            "time": float(row[0]),
            "rate": float(row[1]),
            "thickness": float(row[2]),
            "frequency": float(row[3]),
        }
    except Exception:
        return None

# =========================
# tail 処理（安全版）
# =========================
def tail_file(filepath, run_id, material, density, z_ratio, alert_threshold):
    global prev_alert_state

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(0, os.SEEK_END)

            while logging_event.is_set():
                line = f.readline()
                if not line:
                    time.sleep(0.2)
                    continue

                line = line.strip()
                if not line or line.startswith(("Start", "Stop", "Time")):
                    continue

                data = parse_csv_line(line)
                if not data:
                    continue

                json_body = [{
                    "measurement": "stm2",
                    "tags": {
                        "run_id": run_id,
                        "material": material,
                    },
                    "fields": {
                        "time": data["time"],
                        "rate": data["rate"],
                        "thickness": data["thickness"],
                        "frequency": data["frequency"],
                        "density": density,
                        "z_ratio": z_ratio,
                    }
                }]

                try:
                    client.write_points(json_body)
                except Exception as e:
                    print(f"InfluxDB write error: {e}")

                alert_state = int(data["thickness"] >= alert_threshold)

                if alert_state != prev_alert_state:
                    try:
                        client.write_points([{
                            "measurement": "stm2_settings",
                            "tags": {"run_id": run_id},
                            "fields": {"alert_state": alert_state}
                        }])
                        prev_alert_state = alert_state
                    except Exception as e:
                        print(f"InfluxDB alert write error: {e}")

    except Exception as e:
        gui_call(lambda: messagebox.showerror(
            "エラー", f"ログ読み込み中にエラー:\n{e}"
        ))

# =========================
# GUI 操作
# =========================
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
    global prev_alert_state
    prev_alert_state = None

    if logging_event.is_set():
        return

    material = combo_material.get()
    if not material:
        messagebox.showerror("エラー", "Material を選択してください。")
        return

    try:
        density = float(entry_density.get())
        z_ratio = float(entry_zratio.get())
        target_nm = float(entry_target.get())
    except ValueError:
        messagebox.showerror("エラー", "数値入力が正しくありません。")
        return

    logfile = entry_logfile.get()
    if not os.path.exists(logfile):
        messagebox.showerror("エラー", "ログファイルが存在しません。")
        return

    run_id = entry_runid.get()
    alert_threshold = target_nm * 0.8

    try:
        client.write_points([{
            "measurement": "stm2_settings",
            "tags": {"run_id": run_id},
            "fields": {
                "target_thickness": target_nm,
                "alert_threshold": alert_threshold
            }
        }])
    except Exception as e:
        messagebox.showerror("エラー", f"InfluxDB 初期化失敗:\n{e}")
        return

    logging_event.set()
    btn_start.configure(state="disabled")
    btn_stop.configure(state="normal")
    label_status.configure(text="Logging started…")

    threading.Thread(
        target=tail_file,
        args=(logfile, run_id, material, density, z_ratio, alert_threshold),
        daemon=True
    ).start()

def stop_logging():
    logging_event.clear()
    btn_start.configure(state="normal")
    btn_stop.configure(state="disabled")
    label_status.configure(text="Stopped")

# =========================
# GUI 構築
# =========================
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
btn_stop.configure(state="disabled")

label_status = ctk.CTkLabel(frame, text="Waiting…", font=default_font)
label_status.grid(row=7, column=0, columnspan=3, **pad)

root.mainloop()



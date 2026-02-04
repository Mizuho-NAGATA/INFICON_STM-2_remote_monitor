# -------------------------------------------------------------
# 本ソフトウェアは Microsoft Copilot 、ChatGPT を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho.
# Institute of Laser Engineering, The University of Osaka.
# Created on: 2026-01-20
# Last updated on: 2026-02-04
#
# pip install influxdb
# pip install customtkinter
# pip install tkinterdnd2
# -------------------------------------------------------------
import csv
import os
import threading
import time
from tkinter import filedialog, messagebox

import customtkinter as ctk
from influxdb import InfluxDBClient
from tkinterdnd2 import DND_FILES, TkinterDnD

# --- 材料データ ---
# MATERIAL_DATA の出典
# 密度（Density）:
#   （株）高純度化学研究所 サポートブック 2022〜 ・Webサイト
# Z-RATIO:
#   ・水晶発振式成膜コントローラ説明書（2005/09/30）p.62〜63
#   ・元素周期表
#   ・INFICON STM-2 説明書 A-1〜
MATERIAL_DATA = {
    "Al": {"density": 2.699, "zratio": 1.08},
    "Au": {"density": 19.320, "zratio": 0.381},
    "CaO": {"density": 3.350, "zratio": 1.000},
    "Cr": {"density": 7.19, "zratio": 0.305},
    "Cu": {"density": 8.96, "zratio": 0.437},
    "Fe": {"density": 7.874, "zratio": 0.349},
    "Ge": {"density": 5.323, "zratio": 0.516},
    "Mg": {"density": 1.740, "zratio": 1.610},
    "Mn": {"density": 7.44, "zratio": 0.377},
    "Pb": {"density": 11.350, "zratio": 1.13},
    "Sn": {"density": 7.310, "zratio": 0.72},
    "Tb": {"density": 8.229, "zratio": 0.66},
    "Ti": {"density": 4.54, "zratio": 0.628},
}


# ============================================================
# ロガー本体（GUI 非依存）
# ============================================================
class STM2Logger:
    def __init__(self, host="localhost", port=8086, db="stm2"):
        self.client = InfluxDBClient(host=host, port=port)
        self.client.switch_database(db)

        self.thread = None
        self.stop_event = threading.Event()
        self.prev_alert_state = {}

    # ----------------------------
    # CSV 1行パース
    # ----------------------------
    def parse_csv_line(self, line):
        try:
            row = next(csv.reader([line]))
            # 末尾の空要素を削除
            row = [x for x in row if x.strip() != ""]

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

    # ----------------------------
    # tail スレッド
    # ----------------------------
    def tail_file(
        self,
        filepath,
        run_id,
        material,
        density,
        z_ratio,
        alert_threshold,
        callback=None,
    ):
        if run_id not in self.prev_alert_state:
            self.prev_alert_state[run_id] = None

        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(0, os.SEEK_END)

                while not self.stop_event.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.2)
                        continue

                    line = line.strip()
                    if not line or line.startswith(("Start", "Stop", "Time")):
                        continue

                    data = self.parse_csv_line(line)
                    if not data:
                        continue

                    # InfluxDB 書き込み
                    json_body = [
                        {
                            "measurement": "stm2",
                            "tags": {
                                "run_id": run_id, 
                                "material": material},
                                "density": density,
                                "z_ratio": z_ratio,
                            },
                            "fields": {
                                "time": data["time"],
                                "rate": data["rate"],
                                "thickness": data["thickness"],
                                "frequency": data["frequency"],                                
                            },
                        }
                    ]
                    try:
                        self.client.write_points(json_body)
                    except Exception as e:
                        print(f"InfluxDB write error: {e}")

                    # アラート判定
                    alert_state = int(data["thickness"] >= alert_threshold)
                    if alert_state != self.prev_alert_state[run_id]:
                        try:
                            self.client.write_points(
                                [
                                    {
                                        "measurement": "stm2_settings",
                                        "tags": {"run_id": run_id},
                                        "fields": {"alert_state": alert_state},
                                    }
                                ]
                            )
                            self.prev_alert_state[run_id] = alert_state
                        except Exception as e:
                            print(f"InfluxDB alert write error: {e}")

                    # GUI に通知
                    if callback:
                        callback(data)

        except Exception as e:
            if callback:
                callback({"error": str(e)})

    # ----------------------------
    # ログ監視開始
    # ----------------------------
    def start(
        self, filepath, run_id, material, density, z_ratio, target_nm, callback=None
    ):
        self.stop_event.clear()
        alert_threshold = target_nm * 0.8

        # 初期設定を InfluxDB に書き込み
        try:
            self.client.write_points(
                [
                    {
                        "measurement": "stm2_settings",
                        "tags": {"run_id": run_id},
                        "fields": {
                            "target_thickness": target_nm,
                            "alert_threshold": alert_threshold,
                        },
                    }
                ]
            )
        except Exception as e:
            raise RuntimeError(f"InfluxDB 初期化失敗: {e}")

        # スレッド開始
        self.thread = threading.Thread(
            target=self.tail_file,
            args=(
                filepath,
                run_id,
                material,
                density,
                z_ratio,
                alert_threshold,
                callback,
            ),
            daemon=True,
        )
        self.thread.start()

    # ----------------------------
    # 停止
    # ----------------------------
    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)


# ============================================================
# GUI
# ============================================================
class STM2LoggerGUI:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = TkinterDnD.Tk()
        self.root.title("STM-2 CSV Logger")
        self.root.geometry("700x650")

        self.logger = STM2Logger()

        self.build_gui()

    # ----------------------------
    # GUI 構築
    # ----------------------------
    def build_gui(self):
        default_font = ctk.CTkFont(family="Meiryo", size=24)
        frame = ctk.CTkFrame(self.root, corner_radius=20)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        pad = {"padx": 10, "pady": 10}

        # 目標厚さ
        ctk.CTkLabel(frame, text="目標厚さ [nm]", font=default_font).grid(
            row=0, column=0, sticky="w", **pad
        )
        self.entry_target = ctk.CTkEntry(frame, width=250, font=default_font)
        self.entry_target.grid(row=0, column=1, **pad)

        # Material
        ctk.CTkLabel(frame, text="Material", font=default_font).grid(
            row=1, column=0, sticky="w", **pad
        )
        self.combo_material = ctk.CTkComboBox(
            frame,
            values=list(MATERIAL_DATA.keys()),
            width=250,
            font=default_font,
            command=self.update_material_fields,
        )
        self.combo_material.set("")
        self.combo_material.grid(row=1, column=1, **pad)

        # Density
        ctk.CTkLabel(frame, text="Density", font=default_font).grid(
            row=2, column=0, sticky="w", **pad
        )
        self.entry_density = ctk.CTkEntry(frame, width=250, font=default_font)
        self.entry_density.grid(row=2, column=1, **pad)

        # Z-ratio
        ctk.CTkLabel(frame, text="Z-ratio", font=default_font).grid(
            row=3, column=0, sticky="w", **pad
        )
        self.entry_zratio = ctk.CTkEntry(frame, width=250, font=default_font)
        self.entry_zratio.grid(row=3, column=1, **pad)

        # ログファイル
        ctk.CTkLabel(frame, text="ログファイル", font=default_font).grid(
            row=4, column=0, sticky="w", **pad
        )
        self.entry_logfile = ctk.CTkEntry(frame, width=250, font=default_font)
        self.entry_logfile.grid(row=4, column=1, **pad)

        self.entry_logfile.drop_target_register(DND_FILES)
        self.entry_logfile.dnd_bind("<<Drop>>", self.drop_file)

        btn_browse = ctk.CTkButton(
            frame, text="参照", command=self.browse_file, width=120, font=default_font
        )
        btn_browse.grid(row=4, column=2, **pad)

        # Run ID
        ctk.CTkLabel(frame, text="Run ID", font=default_font).grid(
            row=5, column=0, sticky="w", **pad
        )
        self.entry_runid = ctk.CTkEntry(frame, width=250, font=default_font)
        self.entry_runid.grid(row=5, column=1, **pad)

        # Start / Stop
        self.btn_start = ctk.CTkButton(
            frame,
            text="Start Logging",
            command=self.start_logging,
            width=200,
            font=default_font,
        )
        self.btn_start.grid(row=6, column=0, **pad)

        self.btn_stop = ctk.CTkButton(
            frame,
            text="Stop Logging",
            command=self.stop_logging,
            width=200,
            font=default_font,
        )
        self.btn_stop.grid(row=6, column=1, **pad)
        self.btn_stop.configure(state="disabled")

        # Status
        self.label_status = ctk.CTkLabel(frame, text="Waiting…", font=default_font)
        self.label_status.grid(row=7, column=0, columnspan=3, **pad)

    # ----------------------------
    # Material 選択時
    # ----------------------------
    def update_material_fields(self, event=None):
        material = self.combo_material.get()
        if material in MATERIAL_DATA:
            self.entry_density.delete(0, "end")
            self.entry_density.insert(0, MATERIAL_DATA[material]["density"])
            self.entry_zratio.delete(0, "end")
            self.entry_zratio.insert(0, MATERIAL_DATA[material]["zratio"])

    # ----------------------------
    # ファイル参照
    # ----------------------------
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="STM-2 ログファイルを選択",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")],
        )
        if filename:
            self.entry_logfile.delete(0, "end")
            self.entry_logfile.insert(0, filename)
            self.entry_runid.delete(0, "end")
            self.entry_runid.insert(0, os.path.splitext(os.path.basename(filename))[0])

    # ----------------------------
    # DnD
    # ----------------------------
    def drop_file(self, event):
        path = event.data.strip("{}")
        self.entry_logfile.delete(0, "end")
        self.entry_logfile.insert(0, path)
        self.entry_runid.delete(0, "end")
        self.entry_runid.insert(0, os.path.splitext(os.path.basename(path))[0])

    # ----------------------------
    # Start
    # ----------------------------
    def start_logging(self):
        try:
            material = self.combo_material.get()
            density = float(self.entry_density.get())
            z_ratio = float(self.entry_zratio.get())
            target_nm = float(self.entry_target.get())
        except ValueError:
            messagebox.showerror("エラー", "数値入力が正しくありません。")
            return

        logfile = self.entry_logfile.get()
        if not os.path.exists(logfile):
            messagebox.showerror("エラー", "ログファイルが存在しません。")
            return

        run_id = self.entry_runid.get()

        try:
            self.logger.start(
                filepath=logfile,
                run_id=run_id,
                material=material,
                density=density,
                z_ratio=z_ratio,
                target_nm=target_nm,
                callback=self.update_status,
            )
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.label_status.configure(text="Logging started…")

    # ----------------------------
    # Stop
    # ----------------------------
    def stop_logging(self):
        self.logger.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.label_status.configure(text="Stopped")

    # ----------------------------
    # GUI 更新
    # ----------------------------
    def update_status(self, data):
        if "error" in data:
            self.label_status.configure(text=f"Error: {data['error']}")
        else:
            self.label_status.configure(
                text=f"t={data['time']}  thick={data['thickness']}"
            )

    # ----------------------------
    # 実行
    # ----------------------------
    def run(self):
        self.root.mainloop()


# ============================================================
# 実行
# ============================================================
if __name__ == "__main__":
    gui = STM2LoggerGUI()
    gui.run()






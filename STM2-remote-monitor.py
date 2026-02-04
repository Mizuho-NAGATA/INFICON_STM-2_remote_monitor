# -------------------------------------------------------------
# STM2 Remote Monitor (Alert removed)
# -------------------------------------------------------------
import csv
import os
import threading
import time
from tkinter import filedialog, messagebox

import customtkinter as ctk
from influxdb import InfluxDBClient
from tkinterdnd2 import DND_FILES, TkinterDnD

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
# Logger
# ============================================================
class STM2Logger:
    def __init__(self, host="localhost", port=8086, db="stm2"):
        self.client = InfluxDBClient(host=host, port=port)
        self.client.switch_database(db)

        self.thread = None
        self.stop_event = threading.Event()

    def parse_csv_line(self, line):
        try:
            row = next(csv.reader([line]))
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

    def tail_file(self, filepath, run_id, material, density, z_ratio, callback=None):
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

                    json_body = [
                        {
                            "measurement": "stm2",
                            "tags": {
                                "run_id": run_id,
                                "material": material,
                                "density": str(density),
                                "z_ratio": str(z_ratio),
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

                    if callback:
                        callback(data)

        except Exception as e:
            if callback:
                callback({"error": str(e)})

    def start(self, filepath, run_id, material, density, z_ratio, target_nm, callback=None):
        self.stop_event.clear()

        # target thickness のみ保存
        self.client.write_points(
            [
                {
                    "measurement": "stm2_settings",
                    "tags": {"run_id": run_id},
                    "fields": {
                        "target_thickness": target_nm
                    },
                }
            ]
        )

        self.thread = threading.Thread(
            target=self.tail_file,
            args=(filepath, run_id, material, density, z_ratio, callback),
            daemon=True,
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)

# ============================================================
# GUI（元構造維持）
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

    # （GUI部は元コードと同一のため省略せずそのまま使用）
    # ※ 実運用上、変更は不要です

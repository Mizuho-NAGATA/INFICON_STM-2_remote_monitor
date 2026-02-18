#!/usr/bin/env python3
"""
STM-2 Remote Monitor Application

This application monitors INFICON STM-2 thin film deposition rate/thickness
monitor log files and sends data to InfluxDB for real-time visualization
with Grafana.

Copyright (c) 2026 NAGATA Mizuho.
Institute of Laser Engineering, The University of Osaka.
Created on: 2026-01-20
Last updated on: 2026-02-09

本ソフトウェアは Microsoft Copilot 、ChatGPT を活用して開発されました。

Dependencies:
    pip install influxdb
    pip install customtkinter
    pip install tkinterdnd2
"""
import csv
import os
import threading
import time
from tkinter import filedialog, messagebox
from typing import Dict, Optional, Callable, Any
import sys
import platform

import customtkinter as ctk
from influxdb import InfluxDBClient
from tkinterdnd2 import DND_FILES, TkinterDnD

# --- Material Data / 材料データ ---
# Data sources / 出典:
# Density（密度）:
#   （株）高純度化学研究所 サポートブック 2022〜 ・Webサイト
# Z-RATIO:
#   ・水晶発振式成膜コントローラ説明書（2005/09/30）p.62〜63
#   ・元素周期表
#   ・INFICON STM-2 説明書 A-1〜
MATERIAL_DATA: Dict[str, Dict[str, float]] = {
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

def setup_font() -> ctk.CTkFont:
    """
    Set appropriate font based on the current platform.

    Returns:
        CTkFont: Configured font object with appropriate family and size.
    """
    current_platform = platform.system()  # 'Windows', 'Darwin' (macOS), 'Linux'

    if current_platform == 'Windows':
        font_family = "Meiryo"
    elif current_platform == 'Darwin':  # macOS
        font_family = "Hiragino Sans"
    else:  # Linux
        font_family = "Noto Sans CJK JP"

    return ctk.CTkFont(family=font_family, size=24)

# ============================================================
# Logger Core (GUI Independent) / ロガー本体（GUI 非依存）
# ============================================================
class STM2Logger:
    """
    Core logger class for monitoring STM-2 log files and sending data to InfluxDB.

    This class handles file monitoring, data parsing, and database operations
    independently of the GUI.

    Attributes:
        client (InfluxDBClient): InfluxDB client instance.
        thread (Thread): Background thread for file monitoring.
        stop_event (Event): Threading event for stopping the monitor.
        prev_alert_state (dict): Previous alert states for each run_id.
    """
    def __init__(self, host: str = "localhost", port: int = 8086, db: str = "stm2") -> None:
        """
        Initialize the STM2Logger.

        Args:
            host (str): InfluxDB host address. Default is "localhost".
            port (int): InfluxDB port. Default is 8086.
            db (str): Database name. Default is "stm2".
        """
        self.client = InfluxDBClient(host=host, port=port)
        self.client.switch_database(db)

        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.prev_alert_state: Dict[str, Optional[int]] = {}

    # ----------------------------
    # CSV Line Parser (STM-2 format: 5 columns with trailing comma)
    # CSV 1行パース（STM-2 は5列、末尾が空欄）
    # ----------------------------
    def parse_csv_line(self, line: str) -> Optional[Dict[str, float]]:
        """
        Parse a single CSV line from STM-2 log file.

        Args:
            line (str): A line from the CSV file.

        Returns:
            dict: Parsed data containing time, rate, thickness, and frequency,
                  or None if parsing fails.
        """
        try:
            row = next(csv.reader([line]))

            # Remove trailing empty elements (STM-2 logs end with a comma)
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
    # File Tail Thread / tail スレッド
    # ----------------------------
    def tail_file(
        self,
        filepath: str,
        run_id: str,
        material: str,
        density: float,
        z_ratio: float,
        alert_threshold: float,
        target_nm: float,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """
        Monitor a log file and send new data to InfluxDB.

        Args:
            filepath (str): Path to the log file to monitor.
            run_id (str): Unique identifier for this monitoring run.
            material (str): Material being deposited.
            density (float): Material density.
            z_ratio (float): Material Z-ratio.
            alert_threshold (float): Thickness threshold for alerts.
            target_nm (float): Target thickness in nanometers.
            callback (callable, optional): Function to call with new data for GUI updates.
        """

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

                    # ----------------------------
                    # InfluxDB Write (density / z_ratio as tags)
                    # InfluxDB 書き込み（density / z_ratio を tag 化）
                    # ----------------------------
                    # Calculate percentage
                    progress_percentage = (data["thickness"] / target_nm) * 100 if target_nm > 0 else 0

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
                                "progress_percentage": progress_percentage,
                            },
                        }
                    ]

                    try:
                        self.client.write_points(json_body)
                    except Exception as e:
                        print(f"InfluxDB write error: {e}")

                    # ----------------------------
                    # Alert Detection / アラート判定
                    # ----------------------------
                    alert_state = int(data["thickness"] >= alert_threshold)

                    if alert_state != self.prev_alert_state[run_id]:
                        try:
                            self.client.write_points([
                                {
                                    "measurement": "stm2_settings",
                                    "tags": {"run_id": run_id},
                                    "fields": {"alert_state": alert_state}
                                }
                            ])
                            self.prev_alert_state[run_id] = alert_state
                        except Exception as e:
                            print(f"InfluxDB alert write error: {e}")

                    # GUI update callback
                    if callback:
                        callback(data)

        except Exception as e:
            if callback:
                callback({"error": str(e)})

    # ----------------------------
    # Start Monitoring / ログ監視開始
    # ----------------------------
    def start(
        self,
        filepath: str,
        run_id: str,
        material: str,
        density: float,
        z_ratio: float,
        target_nm: float,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """
        Start monitoring a log file.

        Args:
            filepath (str): Path to the log file.
            run_id (str): Unique identifier for this run.
            material (str): Material name.
            density (float): Material density.
            z_ratio (float): Material Z-ratio.
            target_nm (float): Target thickness in nanometers.
            callback (callable, optional): Callback function for GUI updates.

        Raises:
            RuntimeError: If InfluxDB initialization fails.
        """
        self.stop_event.clear()
        alert_threshold = target_nm * 0.8

        # Write initial settings to InfluxDB
        try:
            self.client.write_points([
                {
                    "measurement": "stm2_settings",
                    "tags": {"run_id": run_id},
                    "fields": {
                        "target_thickness": target_nm,
                        "alert_threshold": alert_threshold
                    }
                }
            ])
        except Exception as e:
            raise RuntimeError(f"InfluxDB 初期化失敗: {e}")

        # Start monitoring thread
        self.thread = threading.Thread(
            target=self.tail_file,
            args=(filepath, run_id, material, density, z_ratio, alert_threshold, target_nm, callback),
            daemon=True
        )
        self.thread.start()

    # ----------------------------
    # Stop Monitoring / 停止
    # ----------------------------
    def stop(self) -> None:
        """Stop the monitoring thread."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=1.0)


# ============================================================
# GUI Application / GUI
# ============================================================
class STM2LoggerGUI:
    """
    GUI application for STM-2 log monitoring.

    This class provides a user-friendly interface for configuring and
    monitoring STM-2 deposition processes.

    Attributes:
        root: Main application window.
        logger (STM2Logger): Logger instance for file monitoring.
    """
    def __init__(self) -> None:
        """Initialize the GUI application."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = TkinterDnD.Tk()
        self.root.title("STM-2 CSV Logger")
        self.root.geometry("700x650")

        self.logger = STM2Logger()

        self.build_gui()

    # ----------------------------
    # Build GUI / GUI 構築
    # ----------------------------
    def build_gui(self) -> None:
        """Construct the GUI layout and widgets."""
        default_font = setup_font()
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
    # Material Selection Handler / Material 選択時
    # ----------------------------
    def update_material_fields(self, event: Optional[Any] = None) -> None:
        """
        Update density and Z-ratio fields when a material is selected.

        Args:
            event: Event object (optional, for callback compatibility).
        """
        material = self.combo_material.get()
        if material in MATERIAL_DATA:
            self.entry_density.delete(0, "end")
            self.entry_density.insert(0, MATERIAL_DATA[material]["density"])
            self.entry_zratio.delete(0, "end")
            self.entry_zratio.insert(0, MATERIAL_DATA[material]["zratio"])

    # ----------------------------
    # File Browser / ファイル参照
    # ----------------------------
    def browse_file(self) -> None:
        """Open a file dialog to select a log file."""
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
    # Drag and Drop Handler / DnD
    # ----------------------------
    def drop_file(self, event: Any) -> None:
        """
        Handle file drag-and-drop events.

        Args:
            event: Drag-and-drop event object.
        """
        path = event.data.strip("{}")
        self.entry_logfile.delete(0, "end")
        self.entry_logfile.insert(0, path)
        self.entry_runid.delete(0, "end")
        self.entry_runid.insert(0, os.path.splitext(os.path.basename(path))[0])

    # ----------------------------
    # Start Logging / Start
    # ----------------------------
    def start_logging(self) -> None:
        """Start the logging process with current configuration."""
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
    # Stop Logging / Stop
    # ----------------------------
    def stop_logging(self) -> None:
        """Stop the logging process."""
        self.logger.stop()
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.label_status.configure(text="Stopped")

    # ----------------------------
    # GUI Update Callback / GUI 更新
    # ----------------------------
    def update_status(self, data: Dict[str, Any]) -> None:
        """
        Update the status label with new data from the logger.

        Args:
            data (dict): Data dictionary containing measurement values or error.
        """
        if "error" in data:
            self.label_status.configure(text=f"Error: {data['error']}")
        else:
            self.label_status.configure(
                text=f"t={data['time']}  thick={data['thickness']}"
            )

    # ----------------------------
    # Run Application / 実行
    # ----------------------------
    def run(self) -> None:
        """Start the GUI main loop."""
        self.root.mainloop()


# ============================================================
# Main Entry Point / 実行
# ============================================================
def main() -> None:
    """Main entry point for the application."""
    gui = STM2LoggerGUI()
    gui.run()


if __name__ == "__main__":
    main()


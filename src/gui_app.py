# -------------------------------------------------------------
# 本ソフトウェアは Microsoft Copilot、ChatGPT を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho. Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-30
# gui_app.py
# GUI をそのまま残しつつ、バックグラウンドで動く処理（ログを読み取って InfluxDB に送る)だけ core に委譲したバージョン
# -------------------------------------------------------------

import os
import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from stm2_reader_core import MATERIAL_DATA, create_influx_client, tail_file

# =========================
# グローバル変数
# =========================
client = None
logging_event = threading.Event()


# =========================
# GUI スレッド呼び出し用
# =========================
def gui_call(func):
    """GUI スレッドで安全に関数を実行"""
    root.after(0, func)


# =========================
# InfluxDB接続初期化
# =========================
def initialize_influx_client():
    """InfluxDBクライアントを初期化"""
    global client
    try:
        client = create_influx_client()
        return True
    except Exception as e:
        messagebox.showerror("エラー", f"InfluxDB接続失敗:\n{e}")
        return False


# =========================
# GUI 操作関数
# =========================
def update_material_fields(event=None):
    """材料選択時に密度とZ-ratioを自動入力"""
    material = combo_material.get()
    if material in MATERIAL_DATA:
        entry_density.delete(0, "end")
        entry_density.insert(0, MATERIAL_DATA[material]["density"])
        entry_zratio.delete(0, "end")
        entry_zratio.insert(0, MATERIAL_DATA[material]["zratio"])


def browse_file():
    """ファイル参照ダイアログを開く"""
    filename = filedialog.askopenfilename(
        title="STM-2 ログファイルを選択",
        filetypes=[("Log files", "*.log"), ("All files", "*.*")],
    )
    if filename:
        entry_logfile.delete(0, "end")
        entry_logfile.insert(0, filename)
        entry_runid.delete(0, "end")
        entry_runid.insert(0, os.path.splitext(os.path.basename(filename))[0])


def drop_file(event):
    """ドラッグ&ドロップファイル処理"""
    path = event.data.strip("{}")
    entry_logfile.delete(0, "end")
    entry_logfile.insert(0, path)
    entry_runid.delete(0, "end")
    entry_runid.insert(0, os.path.splitext(os.path.basename(path))[0])


def validate_inputs():
    """入力値の検証"""
    errors = []

    # Material選択チェック
    material = combo_material.get()
    if not material:
        errors.append("Materialを選択してください。")

    # 数値入力チェック
    try:
        float(entry_density.get())
    except ValueError:
        errors.append("Densityは数値で入力してください。")

    try:
        float(entry_zratio.get())
    except ValueError:
        errors.append("Z-ratioは数値で入力してください。")

    try:
        target_nm = float(entry_target.get())
        if target_nm <= 0:
            errors.append("目標厚さは正の数値で入力してください。")
    except ValueError:
        errors.append("目標厚さは数値で入力してください。")

    # ファイル存在チェック
    logfile = entry_logfile.get()
    if not logfile:
        errors.append("ログファイルを選択してください。")
    elif not os.path.exists(logfile):
        errors.append("指定されたログファイルが存在しません。")

    # Run ID チェック
    run_id = entry_runid.get().strip()
    if not run_id:
        errors.append("Run IDを入力してください。")

    return errors


def start_logging():
    """ログ監視開始"""
    global client

    # 重複実行防止
    if logging_event.is_set():
        return

    # 入力値検証
    errors = validate_inputs()
    if errors:
        messagebox.showerror("エラー", "\n".join(errors))
        return

    # InfluxDBクライアント初期化
    if client is None:
        if not initialize_influx_client():
            return

    # 入力値取得
    try:
        run_id = entry_runid.get().strip()
        material = combo_material.get()
        density = float(entry_density.get())
        z_ratio = float(entry_zratio.get())
        target_nm = float(entry_target.get())
        logfile = entry_logfile.get()
    except ValueError as e:
        messagebox.showerror("エラー", f"入力値エラー: {e}")
        return

    # アラート閾値計算（目標厚さの80%）
    alert_threshold = target_nm * 0.8

    # 初期設定をInfluxDBに送信
    try:
        client.write_points(
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
        messagebox.showerror("エラー", f"InfluxDB 初期化失敗:\n{e}")
        return

    # UI状態更新
    logging_event.set()
    btn_start.configure(state="disabled")
    btn_stop.configure(state="normal")
    label_status.configure(text="Logging started…")

    # バックグラウンドスレッド開始
    thread = threading.Thread(
        target=tail_file_wrapper,
        args=(logfile, run_id, material, density, z_ratio, alert_threshold, client),
        daemon=True,
    )
    thread.start()


def tail_file_wrapper(
    logfile, run_id, material, density, z_ratio, alert_threshold, client
):
    """tail_file のラッパー関数（エラーハンドリング付き）"""
    try:
        tail_file(
            logfile,
            run_id,
            material,
            density,
            z_ratio,
            alert_threshold,
            client,
            logging_event,
            gui_call,
        )
    except Exception as e:
        gui_call(
            lambda: messagebox.showerror(
                "エラー", f"ログ読み込み中にエラーが発生しました:\n{e}"
            )
        )
        gui_call(lambda: stop_logging())


def stop_logging():
    """ログ監視停止"""
    logging_event.clear()
    btn_start.configure(state="normal")
    btn_stop.configure(state="disabled")
    label_status.configure(text="Stopped")


def on_closing():
    """アプリケーション終了時の処理"""
    logging_event.clear()
    root.destroy()


# =========================
# GUI 構築
# =========================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = TkinterDnD.Tk()
root.title("STM-2 CSV Logger")
root.geometry("700x650")
root.protocol("WM_DELETE_WINDOW", on_closing)

default_font = ctk.CTkFont(family="Meiryo", size=24)

frame = ctk.CTkFrame(root, corner_radius=20)
frame.pack(fill="both", expand=True, padx=20, pady=20)

pad = {"padx": 10, "pady": 10}

# 目標厚さ入力
ctk.CTkLabel(frame, text="目標厚さ [nm]", font=default_font).grid(
    row=0, column=0, sticky="w", **pad
)
entry_target = ctk.CTkEntry(frame, width=250, font=default_font)
entry_target.grid(row=0, column=1, **pad)

# 材料選択
ctk.CTkLabel(frame, text="Material", font=default_font).grid(
    row=1, column=0, sticky="w", **pad
)
combo_material = ctk.CTkComboBox(
    frame,
    values=list(MATERIAL_DATA.keys()),
    width=250,
    font=default_font,
    command=update_material_fields,
)
combo_material.set("")
combo_material.grid(row=1, column=1, **pad)

# 密度入力
ctk.CTkLabel(frame, text="Density", font=default_font).grid(
    row=2, column=0, sticky="w", **pad
)
entry_density = ctk.CTkEntry(frame, width=250, font=default_font)
entry_density.grid(row=2, column=1, **pad)

# Z-ratio入力
ctk.CTkLabel(frame, text="Z-ratio", font=default_font).grid(
    row=3, column=0, sticky="w", **pad
)
entry_zratio = ctk.CTkEntry(frame, width=250, font=default_font)
entry_zratio.grid(row=3, column=1, **pad)

# ログファイル選択
ctk.CTkLabel(frame, text="ログファイル", font=default_font).grid(
    row=4, column=0, sticky="w", **pad
)
entry_logfile = ctk.CTkEntry(frame, width=250, font=default_font)
entry_logfile.grid(row=4, column=1, **pad)
entry_logfile.drop_target_register(DND_FILES)
entry_logfile.dnd_bind("<<Drop>>", drop_file)

btn_browse = ctk.CTkButton(
    frame, text="参照", command=browse_file, width=120, font=default_font
)
btn_browse.grid(row=4, column=2, **pad)

# Run ID入力
ctk.CTkLabel(frame, text="Run ID", font=default_font).grid(
    row=5, column=0, sticky="w", **pad
)
entry_runid = ctk.CTkEntry(frame, width=250, font=default_font)
entry_runid.grid(row=5, column=1, **pad)

# 制御ボタン
btn_start = ctk.CTkButton(
    frame, text="Start Logging", command=start_logging, width=200, font=default_font
)
btn_start.grid(row=6, column=0, **pad)

btn_stop = ctk.CTkButton(
    frame, text="Stop Logging", command=stop_logging, width=200, font=default_font
)
btn_stop.grid(row=6, column=1, **pad)
btn_stop.configure(state="disabled")

# ステータス表示
label_status = ctk.CTkLabel(frame, text="Waiting…", font=default_font)
label_status.grid(row=7, column=0, columnspan=3, **pad)

if __name__ == "__main__":
    root.mainloop()

# -------------------------------------------------------------
# 本ソフトウェアは Microsoft Copilot、ChatGPT を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho. Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-30
# gui_app.py - STM-2 Monitoring System GUI (Enhanced UX Version)
# -------------------------------------------------------------

import datetime
import os
import threading
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from stm2_reader_core import MATERIAL_DATA, create_influx_client, tail_file

# =========================
# グローバル変数
# =========================
client = None
logging_event = threading.Event()
log_messages = []
current_thickness = 0.0
current_rate = 0.0

# =========================
# カラーテーマ
# =========================
COLORS = {
    "primary": "#1f6aa5",
    "secondary": "#2a9d8f",
    "success": "#06d6a0",
    "warning": "#ffd60a",
    "danger": "#e76f51",
    "dark": "#2d3436",
    "light": "#ddd6fe",
}


# =========================
# GUI スレッド呼び出し用
# =========================
def gui_call(func):
    """GUI スレッドで安全に関数を実行"""
    root.after(0, func)


def add_log_message(message, level="INFO"):
    """ログメッセージを追加"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    log_messages.append(log_entry)

    # 最大100件まで保持
    if len(log_messages) > 100:
        log_messages.pop(0)

    # GUI更新
    if "log_text" in globals():
        gui_call(lambda: update_log_display())


def update_log_display():
    """ログ表示を更新"""
    if log_text.winfo_exists():
        log_text.delete("1.0", "end")
        log_text.insert("1.0", "\n".join(log_messages[-20:]))  # 最新20件を表示
        log_text.see("end")


def update_status_display(thickness=None, rate=None):
    """リアルタイム状態表示を更新"""
    global current_thickness, current_rate

    if thickness is not None:
        current_thickness = thickness
        gui_call(lambda: thickness_value_label.configure(text=f"{thickness:.2f} nm"))

        # プログレスバー更新
        try:
            target = float(entry_target.get())
            progress = min(thickness / target * 100, 100)
            gui_call(lambda: progress_var.set(progress))
            gui_call(lambda: progress_label.configure(text=f"{progress:.1f}%"))
        except:
            pass

    if rate is not None:
        current_rate = rate
        gui_call(lambda: rate_value_label.configure(text=f"{rate:.3f} nm/s"))


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
root.title("🔬 STM-2 Monitoring System - Enhanced Edition")
root.geometry("1200x800")
root.protocol("WM_DELETE_WINDOW", on_closing)

# フォント設定
title_font = ctk.CTkFont(family="Meiryo", size=28, weight="bold")
header_font = ctk.CTkFont(family="Meiryo", size=20, weight="bold")
default_font = ctk.CTkFont(family="Meiryo", size=16)
small_font = ctk.CTkFont(family="Meiryo", size=12)

# メインコンテナ
main_container = ctk.CTkFrame(root, corner_radius=20)
main_container.pack(fill="both", expand=True, padx=20, pady=20)

# タイトルエリア
title_frame = ctk.CTkFrame(main_container, height=80, corner_radius=15)
title_frame.pack(fill="x", padx=20, pady=(20, 10))
title_frame.pack_propagate(False)

title_label = ctk.CTkLabel(
    title_frame,
    text="🔬 STM-2 薄膜蒸着 監視システム",
    font=title_font,
    text_color=COLORS["light"],
)
title_label.pack(pady=20)

# タブビュー作成
tabview = ctk.CTkTabview(main_container, width=1120, height=650)
tabview.pack(fill="both", expand=True, padx=20, pady=(0, 20))

# 設定タブ
tabview.add("⚙️ 設定")
# 監視タブ
tabview.add("📊 監視")
# ログタブ
tabview.add("📋 ログ")

# ===== 設定タブのレイアウト =====
settings_frame = tabview.tab("⚙️ 設定")

# 左側：設定入力エリア
input_frame = ctk.CTkFrame(settings_frame, width=550)
input_frame.pack(side="left", fill="y", padx=(20, 10), pady=20)
input_frame.pack_propagate(False)

# 右側：状態表示・制御エリア
control_frame = ctk.CTkFrame(settings_frame, width=480)
control_frame.pack(side="right", fill="y", padx=(10, 20), pady=20)
control_frame.pack_propagate(False)

pad = {"padx": 15, "pady": 8}

# === 左側：設定入力エリア ===
settings_header = ctk.CTkLabel(input_frame, text="📝 測定設定", font=header_font)
settings_header.pack(pady=(20, 15))

# 目標厚さ入力（強調表示）
target_frame = ctk.CTkFrame(input_frame)
target_frame.pack(fill="x", padx=20, pady=10)
ctk.CTkLabel(
    target_frame,
    text="🎯 目標厚さ [nm]",
    font=default_font,
    text_color=COLORS["warning"],
).pack(anchor="w", padx=15, pady=(15, 5))
entry_target = ctk.CTkEntry(
    target_frame, width=400, height=40, font=default_font, placeholder_text="例: 100"
)
entry_target.pack(padx=15, pady=(0, 15))

# 材料選択
material_frame = ctk.CTkFrame(input_frame)
material_frame.pack(fill="x", padx=20, pady=10)
ctk.CTkLabel(material_frame, text="🧪 Material", font=default_font).pack(
    anchor="w", padx=15, pady=(15, 5)
)
combo_material = ctk.CTkComboBox(
    material_frame,
    values=list(MATERIAL_DATA.keys()),
    width=400,
    height=35,
    font=default_font,
    command=update_material_fields,
)
combo_material.set("")
combo_material.pack(padx=15, pady=(0, 15))

# 物性値表示（自動入力）
properties_frame = ctk.CTkFrame(input_frame)
properties_frame.pack(fill="x", padx=20, pady=10)
ctk.CTkLabel(properties_frame, text="⚗️ 物性値（自動入力）", font=default_font).pack(
    anchor="w", padx=15, pady=(15, 5)
)

prop_sub_frame = ctk.CTkFrame(properties_frame)
prop_sub_frame.pack(fill="x", padx=15, pady=(0, 15))

# 密度
density_sub = ctk.CTkFrame(prop_sub_frame)
density_sub.pack(side="left", fill="x", expand=True, padx=(0, 5))
ctk.CTkLabel(density_sub, text="Density", font=small_font).pack(pady=(10, 2))
entry_density = ctk.CTkEntry(density_sub, height=30, font=small_font, state="readonly")
entry_density.pack(fill="x", padx=10, pady=(0, 10))

# Z-ratio
zratio_sub = ctk.CTkFrame(prop_sub_frame)
zratio_sub.pack(side="right", fill="x", expand=True, padx=(5, 0))
ctk.CTkLabel(zratio_sub, text="Z-ratio", font=small_font).pack(pady=(10, 2))
entry_zratio = ctk.CTkEntry(zratio_sub, height=30, font=small_font, state="readonly")
entry_zratio.pack(fill="x", padx=10, pady=(0, 10))

# ログファイル選択
file_frame = ctk.CTkFrame(input_frame)
file_frame.pack(fill="x", padx=20, pady=10)
ctk.CTkLabel(file_frame, text="📄 STM-2 ログファイル", font=default_font).pack(
    anchor="w", padx=15, pady=(15, 5)
)

file_input_frame = ctk.CTkFrame(file_frame)
file_input_frame.pack(fill="x", padx=15, pady=(0, 15))

entry_logfile = ctk.CTkEntry(
    file_input_frame,
    height=35,
    font=default_font,
    placeholder_text="ファイルを選択またはドラッグ&ドロップ",
)
entry_logfile.pack(side="left", fill="x", expand=True, padx=(0, 10))
entry_logfile.drop_target_register(DND_FILES)
entry_logfile.dnd_bind("<<Drop>>", drop_file)

btn_browse = ctk.CTkButton(
    file_input_frame, text="📁 参照", command=browse_file, width=80, height=35
)
btn_browse.pack(side="right")

# Run ID
runid_frame = ctk.CTkFrame(input_frame)
runid_frame.pack(fill="x", padx=20, pady=10)
ctk.CTkLabel(runid_frame, text="🏷️ Run ID（実験識別名）", font=default_font).pack(
    anchor="w", padx=15, pady=(15, 5)
)
entry_runid = ctk.CTkEntry(
    runid_frame,
    width=400,
    height=35,
    font=default_font,
    placeholder_text="自動生成されます",
)
entry_runid.pack(padx=15, pady=(0, 15))

# === 右側：制御・状態表示エリア ===
control_header = ctk.CTkLabel(control_frame, text="🎮 制御パネル", font=header_font)
control_header.pack(pady=(20, 15))

# 制御ボタン
button_frame = ctk.CTkFrame(control_frame)
button_frame.pack(fill="x", padx=20, pady=10)

btn_start = ctk.CTkButton(
    button_frame,
    text="▶️ Start Logging",
    command=start_logging,
    width=180,
    height=50,
    font=header_font,
    fg_color=COLORS["success"],
    hover_color=COLORS["secondary"],
)
btn_start.pack(pady=(15, 10))

btn_stop = ctk.CTkButton(
    button_frame,
    text="⏹️ Stop Logging",
    command=stop_logging,
    width=180,
    height=50,
    font=header_font,
    fg_color=COLORS["danger"],
)
btn_stop.pack(pady=(0, 15))
btn_stop.configure(state="disabled")

# ステータス表示
status_frame = ctk.CTkFrame(control_frame)
status_frame.pack(fill="x", padx=20, pady=10)
ctk.CTkLabel(status_frame, text="📊 システム状態", font=default_font).pack(
    anchor="w", padx=15, pady=(15, 5)
)
label_status = ctk.CTkLabel(
    status_frame, text="⏳ Waiting…", font=default_font, text_color=COLORS["warning"]
)
label_status.pack(padx=15, pady=(0, 15))

# === 監視タブのレイアウト ===
monitor_frame = tabview.tab("📊 監視")

# リアルタイム表示エリア
realtime_frame = ctk.CTkFrame(monitor_frame)
realtime_frame.pack(fill="both", expand=True, padx=20, pady=20)

monitor_header = ctk.CTkLabel(
    realtime_frame, text="📈 リアルタイム監視", font=header_font
)
monitor_header.pack(pady=(20, 15))

# 数値表示パネル
values_container = ctk.CTkFrame(realtime_frame)
values_container.pack(fill="x", padx=20, pady=10)

# 現在の厚さ
thickness_frame = ctk.CTkFrame(values_container, width=250, height=120)
thickness_frame.pack(side="left", padx=10, pady=10)
thickness_frame.pack_propagate(False)
ctk.CTkLabel(
    thickness_frame,
    text="📏 現在の膜厚",
    font=default_font,
    text_color=COLORS["secondary"],
).pack(pady=(15, 5))
thickness_value_label = ctk.CTkLabel(
    thickness_frame, text="0.00 nm", font=title_font, text_color=COLORS["light"]
)
thickness_value_label.pack()

# 成膜レート
rate_frame = ctk.CTkFrame(values_container, width=250, height=120)
rate_frame.pack(side="left", padx=10, pady=10)
rate_frame.pack_propagate(False)
ctk.CTkLabel(
    rate_frame, text="⚡ 成膜レート", font=default_font, text_color=COLORS["secondary"]
).pack(pady=(15, 5))
rate_value_label = ctk.CTkLabel(
    rate_frame, text="0.000 nm/s", font=title_font, text_color=COLORS["light"]
)
rate_value_label.pack()

# 進捗表示
progress_frame = ctk.CTkFrame(values_container, width=250, height=120)
progress_frame.pack(side="right", padx=10, pady=10)
progress_frame.pack_propagate(False)
ctk.CTkLabel(
    progress_frame, text="🎯 進捗", font=default_font, text_color=COLORS["secondary"]
).pack(pady=(15, 5))
progress_var = ctk.DoubleVar()
progress_bar = ctk.CTkProgressBar(progress_frame, variable=progress_var, width=180)
progress_bar.pack(pady=5)
progress_label = ctk.CTkLabel(progress_frame, text="0.0%", font=default_font)
progress_label.pack()

# Grafanaリンク
grafana_frame = ctk.CTkFrame(realtime_frame)
grafana_frame.pack(fill="x", padx=20, pady=20)
ctk.CTkLabel(grafana_frame, text="🌐 Grafana ダッシュボード", font=default_font).pack(
    anchor="w", padx=15, pady=(15, 5)
)


def open_grafana():
    import webbrowser

    try:
        # ローカルIPを取得
        import socket

        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        webbrowser.open(f"http://{local_ip}:3000")
    except:
        webbrowser.open("http://localhost:3000")


grafana_btn = ctk.CTkButton(
    grafana_frame,
    text="🚀 Grafana を開く",
    command=open_grafana,
    width=200,
    height=40,
    fg_color=COLORS["primary"],
)
grafana_btn.pack(padx=15, pady=(0, 15))

# === ログタブのレイアウト ===
log_frame = tabview.tab("📋 ログ")

log_header = ctk.CTkLabel(log_frame, text="📝 システムログ", font=header_font)
log_header.pack(pady=(20, 15))

log_container = ctk.CTkFrame(log_frame)
log_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

log_text = ctk.CTkTextbox(log_container, width=1000, height=400, font=small_font)
log_text.pack(fill="both", expand=True, padx=20, pady=20)

# 初期ログメッセージ
add_log_message("システムが起動しました")
add_log_message("設定を入力して 'Start Logging' をクリックしてください")

# 初期化完了ログ
add_log_message("GUI初期化完了", "SUCCESS")
add_log_message("タブ切り替えで各機能をご利用ください", "INFO")

if __name__ == "__main__":
    root.mainloop()

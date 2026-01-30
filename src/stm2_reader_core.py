# -------------------------------------------------------------
# 本ソフトウェアは Microsoft Copilot、ChatGPT を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho. Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-30
# stm2_reader_core.py
# GUI と CLI の両方から使う「共通ロジック」だけをまとめたファイル
# -------------------------------------------------------------

import csv
import os
import time

from influxdb import InfluxDBClient

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


# =========================
# InfluxDB クライアント作成
# =========================
def create_influx_client():
    """InfluxDBクライアントを作成して接続を確認"""
    host = os.environ.get("INFLUX_HOST", "localhost")
    port = int(os.environ.get("INFLUX_PORT", "8086"))
    db = os.environ.get("INFLUX_DB", "stm2")

    try:
        client = InfluxDBClient(host=host, port=port)

        # 接続確認
        client.ping()

        # データベースが存在しない場合は作成
        databases = client.get_list_database()
        if not any(d["name"] == db for d in databases):
            client.create_database(db)

        client.switch_database(db)
        return client

    except Exception as e:
        raise ConnectionError(f"InfluxDB connection failed: {e}")


# =========================
# CSV 1行パース（堅牢版）
# =========================
def parse_csv_line(line):
    """CSV行を安全にパースして辞書形式で返す"""
    try:
        # csv.readerを使用してより堅牢なパースを実現
        row = next(csv.reader([line]))

        # 4つの値が必要
        if len(row) != 4:
            return None

        return {
            "time": float(row[0]),
            "rate": float(row[1]),
            "thickness": float(row[2]),
            "frequency": float(row[3]),
        }
    except (ValueError, StopIteration, IndexError):
        return None


# =========================
# InfluxDBデータ書き込み（安全版）
# =========================
def write_to_influxdb(client, data_points, max_retries=3, retry_delay=1.0):
    """InfluxDBにデータを安全に書き込む"""
    for attempt in range(max_retries):
        try:
            client.write_points(data_points)
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                print(
                    f"InfluxDB write failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                time.sleep(retry_delay)
            else:
                print(f"InfluxDB write failed after {max_retries} attempts: {e}")
                return False
    return False


# =========================
# tail 処理（安全版）
# =========================
def tail_file(
    filepath,
    run_id,
    material,
    density,
    z_ratio,
    alert_threshold,
    client,
    logging_event=None,
    gui_call=None,
):
    """
    ファイルをtailして新しい行を監視し、InfluxDBに送信

    Args:
        filepath: 監視するログファイルパス
        run_id: 実行ID
        material: 材料名
        density: 密度
        z_ratio: Z比
        alert_threshold: アラート閾値
        client: InfluxDBクライアント
        logging_event: 停止制御用のthreading.Event（オプション）
        gui_call: GUI更新用のコールバック関数（オプション）
    """
    prev_alert_state = None

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            # ファイル末尾に移動
            f.seek(0, os.SEEK_END)

            while True:
                # 停止イベントがセットされていればループを終了
                if logging_event and not logging_event.is_set():
                    break

                line = f.readline()

                # 新しい行がない場合は少し待機
                if not line:
                    time.sleep(0.2)
                    continue

                line = line.strip()

                # 空行やヘッダー行をスキップ
                if not line or line.startswith(("Start", "Stop", "Time")):
                    continue

                # CSV行をパース
                data = parse_csv_line(line)
                if not data:
                    continue

                # メインデータをInfluxDBに送信
                json_body = [
                    {
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
                        },
                    }
                ]

                # データ書き込み
                if not write_to_influxdb(client, json_body):
                    print(
                        f"Failed to write main data for thickness: {data['thickness']}"
                    )

                # アラート状態の確認
                alert_state = int(data["thickness"] >= alert_threshold)

                # アラート状態が変化した場合のみ書き込み
                if alert_state != prev_alert_state:
                    alert_json = [
                        {
                            "measurement": "stm2_settings",
                            "tags": {"run_id": run_id},
                            "fields": {"alert_state": alert_state, "last": alert_state},
                        }
                    ]

                    if write_to_influxdb(client, alert_json):
                        prev_alert_state = alert_state
                        if gui_call:
                            status_msg = "Alert: 80%超過!" if alert_state else "Normal"
                            gui_call(lambda msg=status_msg: print(f"Status: {msg}"))
                    else:
                        print(f"Failed to write alert state: {alert_state}")

    except FileNotFoundError:
        error_msg = f"ログファイルが見つかりません: {filepath}"
        print(error_msg)
        if gui_call:
            gui_call(lambda: print(f"Error: {error_msg}"))

    except PermissionError:
        error_msg = f"ログファイルへのアクセス権限がありません: {filepath}"
        print(error_msg)
        if gui_call:
            gui_call(lambda: print(f"Error: {error_msg}"))

    except Exception as e:
        error_msg = f"ログ読み込み中にエラーが発生しました: {e}"
        print(error_msg)
        if gui_call:
            gui_call(lambda: print(f"Error: {error_msg}"))


# =========================
# 設定初期化（安全版）
# =========================
def initialize_settings(client, run_id, target_thickness, alert_threshold):
    """初期設定をInfluxDBに安全に書き込み"""
    settings_data = [
        {
            "measurement": "stm2_settings",
            "tags": {"run_id": run_id},
            "fields": {
                "target_thickness": target_thickness,
                "alert_threshold": alert_threshold,
                "alert_state": 0,
                "last": 0,
            },
        }
    ]

    return write_to_influxdb(client, settings_data)


# =========================
# ファイル監視状態確認
# =========================
def check_file_accessibility(filepath):
    """ファイルのアクセス可能性を確認"""
    errors = []

    if not filepath:
        errors.append("ファイルパスが指定されていません")
        return errors

    if not os.path.exists(filepath):
        errors.append(f"ファイルが存在しません: {filepath}")
        return errors

    if not os.path.isfile(filepath):
        errors.append(f"指定されたパスはファイルではありません: {filepath}")
        return errors

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            pass
    except PermissionError:
        errors.append(f"ファイルへの読み取り権限がありません: {filepath}")
    except Exception as e:
        errors.append(f"ファイルアクセスエラー: {e}")

    return errors

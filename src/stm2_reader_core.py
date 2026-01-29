# 本ソフトウェアは Microsoft Copilot を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho. Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-29
# stm2_reader_core.py
# GUI と CLI の両方から使う「共通ロジック」だけをまとめたファイル
import time
import os
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

# --- InfluxDB クライアント作成 ---
def create_influx_client():
    host = os.environ.get("INFLUX_HOST", "localhost")
    port = int(os.environ.get("INFLUX_PORT", "8086"))
    db   = os.environ.get("INFLUX_DB", "stm2")

    client = InfluxDBClient(host=host, port=port)
    client.switch_database(db)
    return client

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

# --- tail 処理（GUI 非依存） ---
def tail_file(filepath, run_id, material, density, z_ratio, alert_threshold, client):
    prev_alert_state = None

    with open(filepath, "r", encoding="utf-8") as f:
        f.seek(0, 2)

        while True:
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



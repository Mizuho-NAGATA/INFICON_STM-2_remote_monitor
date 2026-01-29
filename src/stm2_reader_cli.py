# 本ソフトウェアは Microsoft Copilot を活用して開発されました。
# Copyright (c) 2026 NAGATA Mizuho. Institute of Laser Engineering, Osaka University.
# Created on: 2026-01-20
# Last updated on: 2026-01-29
# stm2_reader_cli.py
# Docker コンテナ内で動く「常時監視サービス」

import os
from stm2_reader_core import (
    MATERIAL_DATA,
    create_influx_client,
    tail_file
)

def main():
    material = os.environ.get("MATERIAL", "Al")

    if material not in MATERIAL_DATA:
        raise RuntimeError(f"Unknown material: {material}")

    density = MATERIAL_DATA[material]["density"]
    z_ratio = MATERIAL_DATA[material]["zratio"]

    client = create_influx_client()

    alert_threshold = float(os.environ.get("ALERT_THRESHOLD", "100"))

    # STM-2 が生成するログファイルを tail する
    log_path = os.environ.get("STM2_LOG_PATH", "/app/data/stm2.log")

    tail_file(
        filepath=log_path,
        run_id="docker-run",
        material=material,
        density=density,
        z_ratio=z_ratio,
        alert_threshold=alert_threshold,
        client=client
    )

if __name__ == "__main__":
    main()

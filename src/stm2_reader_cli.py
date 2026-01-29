# stm2_reader_cli.py
# Docker コンテナ内で動く「常時監視サービス」
import os
from pathlib import Path
from stm2_reader_core import (
    MATERIAL_DATA,
    create_influx_client,
    tail_file
)

def main():
    log_dir = Path(os.environ.get("LOG_DIR", "/logs"))
    material = os.environ.get("MATERIAL", "Al")

    if material not in MATERIAL_DATA:
        raise RuntimeError(f"Unknown material: {material}")

    density = MATERIAL_DATA[material]["density"]
    z_ratio = MATERIAL_DATA[material]["zratio"]

    client = create_influx_client()

    log_files = sorted(log_dir.glob("*.log"))
    if not log_files:
        raise RuntimeError("No .log files found in LOG_DIR")

    filepath = log_files[-1]
    run_id = filepath.stem

    alert_threshold = float(os.environ.get("ALERT_THRESHOLD", "100"))

    tail_file(filepath, run_id, material, density, z_ratio, alert_threshold, client)

if __name__ == "__main__":
    main()

"""Acquire the two real datasets used by the ARM-1 reproducibility demo."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ISMN_URL = (
    "https://raw.githubusercontent.com/TUW-GEO/ismn/master/tests/test_data/"
    "Data_seperate_files_20170810_20180809/COSMOS/ARM-1/"
    "COSMOS_COSMOS_ARM-1_sm_0.000000_0.190000_Cosmic-ray-Probe_20170810_20180809.stm"
)
ERA5_URL = (
    "https://archive-api.open-meteo.com/v1/archive?latitude=36.6054&longitude=-97.4878"
    "&start_date=2017-08-10&end_date=2018-08-09"
    "&hourly=temperature_2m,precipitation,et0_fao_evapotranspiration,soil_moisture_0_to_7cm"
    "&models=era5&timezone=UTC"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path, local_source: Path | None = None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    if local_source and local_source.exists():
        shutil.copyfile(local_source, temporary)
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "hydrologic-earth-agent/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as stream:
            shutil.copyfileobj(response, stream)
    temporary.replace(target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--ismn-local", type=Path)
    parser.add_argument("--era5-local", type=Path)
    args = parser.parse_args()
    raw = args.root / "data" / "raw"
    files = [
        ("ISMN", ISMN_URL, raw / "ismn_arm1.stm", args.ismn_local),
        ("ERA5 via Open-Meteo", ERA5_URL, raw / "era5_arm1.json", args.era5_local),
    ]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "files": [],
        "note": "ISMN is the validation target. ERA5 is forcing/baseline; neither is synthetic.",
    }
    for label, url, target, local_source in files:
        download(url, target, local_source)
        manifest["files"].append(
            {"dataset": label, "url": url, "path": str(target.relative_to(args.root)), "bytes": target.stat().st_size, "sha256": sha256(target)}
        )
        print(f"downloaded {label}: {target.name} ({target.stat().st_size:,} bytes)")
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

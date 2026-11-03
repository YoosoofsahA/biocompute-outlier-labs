"""Charts and the disconnect table from a run. Owner: role 5 (Pitch and charts).

    uv run python fresh_eyes/charts.py runs/<timestamp>
    uv run python fresh_eyes/charts.py --fake runs/fake      # writes a fake run first, to test the charts

Writes <run>/summary.png and <run>/summary.json, and prints the lead-time / false-alarm table.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

COLUMNS = ["frame", "t", "is_spoiled", "pulses_total", "response_size", "response_in", "response_out",
           "edge_score", "dish_alarm", "silicon_alarm"]
SPOIL_ONSET, MOULD_ONSET = 0.3, 0.6


def load(path: Path) -> dict[str, np.ndarray]:
    """Read one food's CSV into column arrays."""
    with path.open() as f:
        rows = list(csv.DictReader(f))
    return {col: np.array([float(r[col]) for r in rows]) for col in COLUMNS}


def score(alarms: np.ndarray, spoiled: np.ndarray) -> dict:
    """Lead time (frames from spoilage onset to first alarm) and false alarms (alarms on fresh frames)."""
    onset = int(np.argmax(spoiled)) if spoiled.any() else None
    hits = np.nonzero(alarms.astype(bool) & spoiled.astype(bool))[0]
    return {"lead_frames": int(hits[0] - onset) if onset is not None and len(hits) else None,
            "false_alarms": int((alarms.astype(bool) & ~spoiled.astype(bool)).sum())}


def write_fake(run_dir: Path) -> None:
    """Write a plausible fake run so the charts can be built before the real one exists."""
    rng = np.random.default_rng(0)
    run_dir.mkdir(parents=True, exist_ok=True)
    t = np.r_[np.zeros(40), np.linspace(SPOIL_ONSET, 1.0, 60)]
    response = np.where(t >= SPOIL_ONSET, 20 + 30 * t, 18) + rng.normal(0, 3, t.size)
    edge = np.where(t >= MOULD_ONSET, 50 * (t - MOULD_ONSET), 0) + rng.normal(0, 1, t.size)
    with (run_dir / "banana.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i in range(t.size):
            w.writerow([i, t[i], int(t[i] >= SPOIL_ONSET), 12, int(response[i]), int(response[i] * 0.6),
                        int(response[i] * 0.4), edge[i], int(response[i] > 27), int(edge[i] > 3)])
    meta = {"simulated": True, "fake": True, "foods": {"banana": {"baseline": 18.0, "margin": 1.5}}}
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))


def main() -> None:
    """Build the response chart and the disconnect table for every food in the run."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir", type=Path)
    p.add_argument("--fake", action="store_true")
    args = p.parse_args()
    if args.fake:
        write_fake(args.run_dir)

    meta = json.loads((args.run_dir / "meta.json").read_text())
    foods = list(meta["foods"])
    fig, axes = plt.subplots(len(foods), 1, figsize=(10, 3.5 * len(foods)), squeeze=False)
    summary = {}
    for ax, food in zip(axes[:, 0], foods):
        d = load(args.run_dir / f"{food}.csv")
        info = meta["foods"][food]
        frames, spoiled = d["frame"], d["is_spoiled"]
        hybrid = np.maximum(d["dish_alarm"], d["silicon_alarm"])
        summary[food] = {"hybrid": score(hybrid, spoiled), "dish only": score(d["dish_alarm"], spoiled),
                         "silicon only": score(d["silicon_alarm"], spoiled)}

        signal = info.get("baseline_signal", "response_size")   # real runs alarm on the input electrodes
        ax.plot(frames, d[signal], color="#0F766E", label=f"dish response ({signal})")
        ax.axhline(info["baseline"] * info["margin"], color="#C2410C", ls="--", label="dish alarm threshold")
        for onset, label, colour in ((SPOIL_ONSET, "spoilage onset", "#B45309"), (MOULD_ONSET, "mould onset", "#374151")):
            if (d["t"] >= onset).any():
                ax.axvline(frames[np.argmax(d["t"] >= onset)], color=colour, ls=":", label=label)
        dish_hits = d["dish_alarm"].astype(bool)
        ax.scatter(frames[dish_hits], d[signal][dish_hits], s=12, color="#C2410C", zorder=3)
        tag = "FAKE DATA" if meta.get("fake") else "simulated culture"
        ax.set_title(f"{food}: dish response over frames ({tag})")
        ax.set_xlabel("frame")
        ax.set_ylabel("spikes in 100 ms")
        ax.legend(loc="upper left", fontsize=8)

        print(f"\n{food}")
        print(f"  {'condition':<13} {'lead (frames)':>13} {'false alarms':>13}")
        for cond, s in summary[food].items():
            lead = "never" if s["lead_frames"] is None else s["lead_frames"]
            print(f"  {cond:<13} {lead!s:>13} {s['false_alarms']:>13}")

    fig.tight_layout()
    fig.savefig(args.run_dir / "summary.png", dpi=150)
    (args.run_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {args.run_dir / 'summary.png'}")


if __name__ == "__main__":
    main()

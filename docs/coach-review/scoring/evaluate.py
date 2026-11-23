"""Grade the AG five-view dashboard and its cumulative damage timeline."""

import argparse
import bisect
import hashlib
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


CASE = Path(__file__).resolve().parent
METRICS = ("damage_dealt", "damage_taken")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def integer(value, minimum=0, maximum=None):
    return type(value) is int and minimum <= value and (maximum is None or value <= maximum)


def number(value):
    if type(value) not in (int, Decimal) or not Decimal(value).is_finite():
        raise ValueError("Expected a finite number")
    return Decimal(value)


def check_snapshot(snapshot, players):
    if not isinstance(snapshot, dict) or set(snapshot) != set(players):
        raise ValueError("Each snapshot must identify all five players exactly once")
    for player in players:
        row = snapshot[player]
        if not isinstance(row, dict) or set(row) != set(METRICS):
            raise ValueError(f"{player} must supply both damage fields")
        if not all(integer(value) for value in row.values()):
            raise ValueError(f"{player} has a noninteger or negative value")


def read_timeline(path, rules):
    data = load(path)
    players = rules["players"]
    points = data["points"]
    if not isinstance(points, list) or not points:
        raise ValueError("points must be a nonempty list")
    timestamps, snapshots = [], []
    for point in points:
        timestamp = number(point["t_s"])
        if timestamp < 0 or timestamp >= rules["source_duration_s"]:
            raise ValueError("timestamp is outside the video")
        if timestamps and timestamp <= timestamps[-1]:
            raise ValueError("timestamps must be strictly increasing")
        snapshot = point["players"]
        check_snapshot(snapshot, players)
        if snapshots and any(snapshot[p][m] < snapshots[-1][p][m] for p in players for m in METRICS):
            raise ValueError("cumulative damage decreases")
        timestamps.append(timestamp)
        snapshots.append(snapshot)
    if timestamps[0] != 0 or any(snapshots[0][p][m] for p in players for m in METRICS):
        raise ValueError("The first state must start at zero seconds with zero damage")
    check_snapshot(data["final"], players)
    if snapshots[-1] != data["final"]:
        raise ValueError("final differs from the last state")
    return timestamps, snapshots


def timeline_at(timeline, timestamp):
    timestamps, snapshots = timeline
    index = max(0, bisect.bisect_right(timestamps, timestamp) - 1)
    return snapshots[index]


def expected_board(snapshot, players, metric):
    team = sum(snapshot[player][metric] for player in players)
    ordered = sorted(players, key=lambda player: -snapshot[player][metric])
    return [
        (player, snapshot[player][metric], Decimal(100 * snapshot[player][metric]) / team if team else Decimal(0))
        for player in ordered
    ]


def board_matches(observed, expected):
    if not isinstance(observed, list) or len(observed) != len(expected):
        return False
    try:
        return all(
            row["player"] == player and integer(row["value"]) and row["value"] == value
            and abs(number(row["share_pct"]) - share) <= Decimal("0.05000001")
            for row, (player, value, share) in zip(observed, expected)
        )
    except (KeyError, TypeError, ValueError):
        return False


def grade_final(snapshot, rules):
    results = {}
    for player in rules["players"]:
        results[player] = {}
        for metric in METRICS:
            actual = rules["reference"][player][metric]
            estimate = snapshot[player].get(metric) if snapshot else None
            numerator = 100 * abs(estimate - actual) if estimate is not None else None
            points = next(
                (points for edge, points in rules["damage_bands"] if numerator <= edge * actual), 0
            ) if numerator is not None else 0
            results[player][metric] = {
                "estimate": estimate, "reference": actual, "points": points,
                "relative_error_pct": round(numerator / actual, 4) if numerator is not None else None,
            }
    return results


def playable(path, ffprobe, ffmpeg, rules):
    if not path.is_file():
        return "dashboard.mp4 is missing"
    try:
        probe = subprocess.check_output([
            ffprobe, "-v", "error", "-show_entries", "stream=codec_type:format=duration",
            "-of", "json", str(path),
        ], stderr=subprocess.STDOUT)
        info = json.loads(probe)
        types = {stream["codec_type"] for stream in info["streams"]}
        duration = Decimal(info["format"]["duration"])
        if "video" not in types:
            return "dashboard has no video stream"
        if abs(duration - rules["source_duration_s"]) > rules["duration_tolerance_s"]:
            return "dashboard duration is outside the allowed range"
        subprocess.run([
            ffmpeg, "-v", "error", "-xerror", "-i", str(path),
            "-map", "0:v:0", "-map", "0:a:0?", "-fps_mode", "passthrough",
            "-enc_time_base:v", "demux", "-f", "null", "-",
        ], check=True, capture_output=True)
    except (subprocess.CalledProcessError, ValueError, KeyError, ArithmeticError):
        return "dashboard probing or decoding failed"
    return None


def grade_alignment(samples, rules):
    anchors = rules["alignment_checks"]
    players = set(rules["players"])
    if not isinstance(samples, list) or len(samples) != len(anchors):
        raise ValueError("Expected one clock measurement per sync anchor")

    results = []
    for sample, anchor in zip(samples, anchors):
        try:
            if not isinstance(sample, dict) or set(sample) != players:
                raise ValueError("All five clocks are required")
            timestamps = [number(value) for value in sample.values()]
            if any(value < 0 or value >= rules["source_duration_s"] for value in timestamps):
                raise ValueError("Clock transition is outside the video")
        except ValueError:
            spread = None
        else:
            spread = max(timestamps) - min(timestamps)
        points = 0
        if spread is not None:
            points = int(spread <= Decimal("1.5")) + int(spread <= Decimal("0.5"))
        results.append({
            "phase": anchor["phase"],
            "match_clock": anchor["match_clock"],
            "max_offset_s": float(spread) if spread is not None else None,
            "points": points,
        })
    return results


def grade_inspection(inspection, timeline, rules):
    alignment_checks = grade_alignment(inspection["clock_transition_s"], rules)
    terminal = {}
    if timeline:
        final_snapshot = timeline[1][-1]
        final_time = rules["terminal_sample_s"]
        if timeline_at(timeline, final_time) == final_snapshot:
            terminal = {
                metric: board_matches(
                    inspection["terminal_boards"].get(metric),
                    expected_board(final_snapshot, rules["players"], metric),
                )
                for metric in METRICS
            }

    limits = {"layout": 4, "motion": 3, "audio_readability": 3}
    visual = inspection["visual"]
    if any(not integer(visual[key], 0, cap) for key, cap in limits.items()):
        raise ValueError("Visual ratings are outside the published ranges")
    return {
        "alignment": sum(sample["points"] for sample in alignment_checks),
        "alignment_checks": alignment_checks,
        "terminal_boards_match": terminal,
        "visual": sum(visual[key] for key in limits),
        "visual_breakdown": {key: visual[key] for key in limits},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--inspection", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    rules = load(CASE / "grade/reference.json")
    video = args.submission / "dashboard.mp4"
    error = playable(video, args.ffprobe, args.ffmpeg, rules)
    errors = {"dashboard": error} if error else {}
    timeline = None
    try:
        timeline = read_timeline(args.submission / "timeline.json", rules)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors["timeline"] = str(exc)
    if error:
        observed = {"alignment": 0, "visual": 0}
        timeline = None
    elif args.inspection:
        inspection = load(args.inspection)
        with video.open("rb") as reader:
            digest = hashlib.file_digest(reader, "sha256").hexdigest()
        if inspection["video_sha256"].lower() != digest:
            raise ValueError("Inspection belongs to a different video")
        observed = grade_inspection(inspection, timeline, rules)

    else:
        observed = None

    if timeline and observed is not None:
        terminal = observed["terminal_boards_match"]
        displayed = {
            player: {
                metric: timeline[1][-1][player][metric]
                for metric in METRICS if terminal.get(metric)
            }
            for player in rules["players"]
        }
    else:
        displayed = timeline[1][-1] if timeline else None

    damage = grade_final(displayed, rules)
    damage_points = {
        metric: sum(row[metric]["points"] for row in damage.values())
        for metric in METRICS
    }
    total = None if observed is None else sum(damage_points.values()) + observed["alignment"] + observed["visual"]
    result = {
        "status": "awaiting_video_inspection" if total is None else "graded",
        "total_points": total, "maximum_points": 100,
        "terminal_damage_points": sum(damage_points.values()), "terminal_damage": damage,
        "output_points": damage_points["damage_dealt"], "damage_taken_points": damage_points["damage_taken"],
        "inspection": observed, "gate_errors": errors,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    sys.stdout.buffer.write(output.encode("utf-8"))


if __name__ == "__main__":
    main()

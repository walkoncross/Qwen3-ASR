# coding=utf-8
"""
Compare multiple transcribe_conversation.py output JSON files.
Prints performance metrics and per-utterance transcripts side-by-side for analysis.

Usage:
  python scripts/compare_conversation_results.py results/录音1.conversation*.json
  python scripts/compare_conversation_results.py -i results/ --pattern "录音1.conversation*.json"
"""

import argparse
import glob
import json
import os


def load_result(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def label(path: str) -> str:
    """Short label from filename: model + vad."""
    name = os.path.splitext(os.path.basename(path))[0]
    parts = name.split(".")
    # format: {basename}.conversation.{model}.{vad}.no-aligner
    # find 'conversation' and take next two parts
    try:
        idx = parts.index("conversation")
        return f"{parts[idx+1]}.{parts[idx+2]}"
    except (ValueError, IndexError):
        return name


def print_performance(results: list[tuple[str, dict]]) -> None:
    print("\n" + "=" * 80)
    print("PERFORMANCE METRICS")
    print("=" * 80)
    header = f"{'Combination':<40} {'transcribe_s':>12} {'RTF':>8} {'RTFx':>8} {'vad_s':>8} {'vad_RTFx':>10} {'utterances':>12}"
    print(header)
    print("-" * 100)
    for lbl, d in results:
        convs = d.get("conversations", [])
        print(
            f"{lbl:<40} "
            f"{d.get('transcribe_s', 0):>12.3f} "
            f"{d.get('rtf', 0) or 0:>8.4f} "
            f"{d.get('rtfx', 0) or 0:>8.2f} "
            f"{d.get('vad_s', 0):>8.3f} "
            f"{d.get('vad_rtfx', 0) or 0:>10.1f} "
            f"{len(convs):>12}"
        )


def print_segment_stats(results: list[tuple[str, dict]]) -> None:
    print("\n" + "=" * 80)
    print("SEGMENT STATISTICS")
    print("=" * 80)
    header = f"{'Combination':<40} {'total':>8} {'ch0':>6} {'ch1':>6} {'avg_dur_s':>10} {'min_dur_s':>10} {'max_dur_s':>10}"
    print(header)
    print("-" * 90)
    for lbl, d in results:
        convs = d.get("conversations", [])
        ch0 = [u for u in convs if u["role"] == "channel_0"]
        ch1 = [u for u in convs if u["role"] == "channel_1"]
        durs = [u["end"] - u["start"] for u in convs]
        avg_dur = sum(durs) / len(durs) if durs else 0
        min_dur = min(durs) if durs else 0
        max_dur = max(durs) if durs else 0
        print(
            f"{lbl:<40} "
            f"{len(convs):>8} "
            f"{len(ch0):>6} "
            f"{len(ch1):>6} "
            f"{avg_dur:>10.2f} "
            f"{min_dur:>10.2f} "
            f"{max_dur:>10.2f}"
        )


def print_transcripts(results: list[tuple[str, dict]], max_utterances: int = 0) -> None:
    print("\n" + "=" * 80)
    print("TRANSCRIPTS (sorted by start time)")
    print("=" * 80)

    # Collect all unique (role, start, end) keys across all files to align rows
    # Use the first file as reference timeline
    ref_convs = results[0][1].get("conversations", [])

    col_width = 50
    label_width = 20

    # Print header
    header = f"{'[role][start-end]':<22}"
    for lbl, _ in results:
        short = lbl[:label_width]
        header += f"  {short:<{col_width}}"
    print(header)
    print("-" * (22 + (col_width + 2) * len(results)))

    shown = 0
    for u in ref_convs:
        if max_utterances > 0 and shown >= max_utterances:
            print(f"  ... ({len(ref_convs) - shown} more utterances)")
            break
        role = u["role"]
        start = u["start"]
        end = u["end"]
        row_label = f"[{role}][{start:.1f}-{end:.1f}]"

        row = f"{row_label:<22}"
        for lbl, d in results:
            # find best matching utterance in this file (same role, closest start)
            convs = d.get("conversations", [])
            match = None
            best_dist = 1.0  # 1s tolerance
            for v in convs:
                if v["role"] == role and abs(v["start"] - start) < best_dist:
                    best_dist = abs(v["start"] - start)
                    match = v
            text = (match["text"] if match else "—")
            # truncate for display
            if len(text) > col_width:
                text = text[:col_width - 1] + "…"
            row += f"  {text:<{col_width}}"
        print(row)
        shown += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare multiple transcribe_conversation.py output JSON files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("files", nargs="*", help="JSON result files to compare")
    parser.add_argument("--input-dir", "-i", default=None, help="Directory to search for JSON files")
    parser.add_argument("--pattern", "-p", default="*.conversation*.json", help="Glob pattern when using --input-dir")
    parser.add_argument("--max-utterances", "-n", type=int, default=0, help="Max utterances to print in transcript (0 = all)")
    parser.add_argument("--no-transcript", action="store_true", help="Skip transcript section")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    paths = list(args.files)
    if args.input_dir:
        paths += sorted(glob.glob(os.path.join(args.input_dir, args.pattern)))

    if not paths:
        print("No files specified. Use positional args or --input-dir.")
        return

    paths = sorted(set(paths))
    results = []
    for p in paths:
        if not os.path.isfile(p):
            print(f"[warning] not found: {p}")
            continue
        d = load_result(p)
        results.append((label(p), d))

    if not results:
        print("No valid files loaded.")
        return

    print(f"Loaded {len(results)} result file(s). Audio duration: {results[0][1].get('audio_dur_s', 0):.1f}s")

    print_performance(results)
    print_segment_stats(results)
    if not args.no_transcript:
        print_transcripts(results, args.max_utterances)


if __name__ == "__main__":
    main()

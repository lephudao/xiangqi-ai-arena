#!/usr/bin/env python3
"""
Chạy các trận đấu không cần giao diện, lưu lại toàn bộ dữ liệu để dựng video.

Có hai chặn an toàn bắt buộc, vì mỗi nước đi là một lần gọi API tốn tiền:
- --max-moves: trận không kết thúc thì xử hoà theo giới hạn nước, không chạy vô hạn
- --max-cost-usd: chạm ngưỡng thì dừng sạch và ghi lại tiến độ

Ví dụ:
  venv/bin/python3 scripts/run_matches.py \
      --pairing claude-haiku-4-5:gemini-3.1-pro \
      --pairing claude-haiku-4-5:pikafish \
      --max-moves 140 --max-cost-usd 2.00
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv(".env.local", override=True)

from engine.analysis import PikafishEngine, average_accuracy  # noqa: E402
from engine.referee import MatchReferee  # noqa: E402

OUTPUT_DIR = "data/matches"


def run_match(red_key, black_key, max_moves, cost_budget_left, analysis_engine):
    """Chạy một trận. Trả (bản ghi trận, chi phí đã dùng)."""
    referee = MatchReferee(
        {"model_key": red_key},
        {"model_key": black_key},
        analysis_engine=analysis_engine,
    )
    red_name = referee.red_config["name"]
    black_name = referee.black_config["name"]
    print(f"\n{'=' * 78}\n{red_name} (Đỏ)  vs  {black_name} (Đen)\n{'=' * 78}", flush=True)

    started = time.monotonic()
    stopped_reason = None

    for ply in range(1, max_moves + 1):
        state = referee.step()
        move = state["last_move"]
        evaluation = move.get("evaluation") or {}
        quality = evaluation.get("quality_label", "—")
        cp_loss = evaluation.get("cp_loss")
        flags = []
        # Số lần thử > 1 nghĩa là AI đã đi sai luật và phải chọn lại — thước đo sức mạnh
        attempts = len(move.get("attempts") or [])
        if attempts > 1:
            flags.append(f"SAI LUẬT {attempts - 1} lần")
        if move.get("referee_override"):
            flags.append("TRỌNG TÀI CHỌN THAY")
        if move.get("error"):
            flags.append(f"LỖI: {move['error'][:50]}")
        print(
            f"{ply:3d}. {move['player'][:18]:18s} {move['vi_text']:22s} "
            f"{quality:22s} cp_loss={cp_loss if cp_loss is not None else '—':>6} "
            f"{move['latency_ms'] / 1000:5.1f}s {' '.join(flags)}",
            flush=True,
        )

        if state["game_over"]:
            break

        spent = _match_cost(referee)
        if spent is not None and spent >= cost_budget_left:
            stopped_reason = "cost_budget"
            print(f"    ĐÃ DỪNG: chạm ngân sách chi phí (${spent:.4f})", flush=True)
            break
    else:
        stopped_reason = "move_limit"
        print(f"    ĐÃ DỪNG: đạt giới hạn {max_moves} nước — xử hoà theo giới hạn", flush=True)

    state = referee.get_state()
    record = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "red": {"model_key": red_key, "name": red_name},
        "black": {"model_key": black_key, "name": black_name},
        "total_plies": len(referee.move_logs),
        "result_status": state["result_status"],
        "result_reason": state["result_reason"],
        "winner": state["winner"],
        "stopped_reason": stopped_reason,
        "duration_seconds": round(time.monotonic() - started, 1),
        "stats": state["stats"],
        "moves": referee.move_logs,
    }
    _print_summary(record, referee)
    return record, (_match_cost(referee) or 0.0)


def _match_cost(referee):
    """Chi phí trận tới thời điểm hiện tại; None nếu có model chưa niêm yết giá."""
    stats = referee.stats
    if not all(stats[side]["cost_known"] for side in ('w', 'b')):
        return None
    return stats['w']["cost_usd"] + stats['b']["cost_usd"]


def _print_summary(record, referee):
    print(f"\n--- KẾT QUẢ: {record['result_reason']} "
          f"({record['winner'] or 'không có người thắng'}) "
          f"sau {record['total_plies']} nước, {record['duration_seconds']}s ---")
    for side_label, side_key, stats_key in (("Đỏ ", 'w', "red"), ("Đen", 'b', "black")):
        stats = record["stats"][stats_key]
        accuracy = average_accuracy(referee.evaluations[side_key])
        cost = f"${stats['cost_usd']:.4f}" if stats["cost_known"] else "chưa niêm yết giá"
        print(
            f"  {side_label} {record[stats_key]['name'][:22]:22s} "
            f"accuracy={accuracy if accuracy is None else round(accuracy, 1)}%  "
            f"hay nhất={stats['best_moves']}  sai={stats['mistakes']}  blunder={stats['blunders']}  "
            f"sai luật={stats['illegal_attempts']}  lỗi API={stats['api_errors']}  "
            f"token={stats['tokens_in']}/{stats['tokens_out']}  {cost}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pairing", action="append", required=True,
                        metavar="RED:BLACK", help="cặp đấu, ví dụ claude-haiku-4-5:gemini-3.1-pro")
    parser.add_argument("--max-moves", type=int, default=140,
                        help="giới hạn số nước mỗi trận (mặc định 140)")
    parser.add_argument("--max-cost-usd", type=float, default=2.0,
                        help="tổng ngân sách chi phí cho toàn bộ các trận (mặc định 2 USD)")
    parser.add_argument("--out-dir", default=OUTPUT_DIR)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    # Một tiến trình engine dùng chung cho cả chấm điểm và kỳ thủ Pikafish
    analysis_engine = PikafishEngine()
    if not analysis_engine.is_available:
        print(f"CẢNH BÁO: {analysis_engine.unavailable_reason}\n"
              f"-> Trận vẫn chạy nhưng KHÔNG có điểm chấm chất lượng nước đi.", flush=True)

    total_spent = 0.0
    records = []
    for pairing in args.pairing:
        if ":" not in pairing:
            parser.error(f"cặp đấu '{pairing}' phải có dạng RED:BLACK")
        red_key, black_key = pairing.split(":", 1)

        budget_left = args.max_cost_usd - total_spent
        if budget_left <= 0:
            print(f"\nDỪNG TOÀN BỘ: đã dùng hết ngân sách ${args.max_cost_usd}", flush=True)
            break

        record, spent = run_match(red_key, black_key, args.max_moves, budget_left, analysis_engine)
        total_spent += spent
        records.append(record)

        filename = (f"{datetime.now():%y%m%d-%H%M%S}-"
                    f"{red_key}-vs-{black_key}.json".replace("/", "-"))
        path = os.path.join(args.out_dir, filename)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2)
        print(f"  Đã lưu: {path}  |  tổng chi phí tới lúc này: ${total_spent:.4f}", flush=True)

    analysis_engine.close()
    print(f"\n{'=' * 78}\nXONG {len(records)} trận. Tổng chi phí: ${total_spent:.4f}")
    for record in records:
        print(f"  {record['red']['name']} vs {record['black']['name']}: "
              f"{record['result_reason']} ({record['winner'] or 'hoà'}) "
              f"sau {record['total_plies']} nước")


if __name__ == "__main__":
    main()

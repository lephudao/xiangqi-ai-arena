#!/usr/bin/env python3
"""
Nhập các file trận JSON (do run_matches.py tạo trước khi có cơ sở dữ liệu) vào SQLite.

Nhờ đó những trận đã tốn tiền API chạy trước đây vẫn dùng được cho replay và bảng xếp hạng,
không phải chạy lại.

Cách dùng:
  venv/bin/python3 scripts/import_match_json.py data/matches/*.json
  venv/bin/python3 scripts/import_match_json.py --all
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.storage import DEFAULT_DB_PATH, MatchRepository  # noqa: E402
from engine.xiangqi import XiangqiBoard  # noqa: E402

DEFAULT_GLOB = "data/matches/*.json"


def _replay_fens(moves):
    """
    Tính lại FEN sau mỗi nước.

    File JSON cũ không lưu fen_after, nên phải đi lại các nước trên bàn cờ để dựng lại.
    Đây cũng là một phép kiểm tra: nước nào không đi được nghĩa là dữ liệu cũ có vấn đề.
    """
    board = XiangqiBoard()
    fens = []
    for move in moves:
        success, message = board.push_ucci(move["ucci"])
        if not success:
            raise ValueError(f"nước {move['ucci']} không đi được khi dựng lại: {message}")
        fens.append((board.to_fen(), board.is_in_check()))
    return fens


def import_file(repository, path):
    with open(path, encoding="utf-8") as handle:
        record = json.load(handle)

    moves = record.get("moves", [])
    fens = _replay_fens(moves)

    # ID suy ra từ tên file để nhập lại nhiều lần không tạo bản ghi trùng
    match_id = os.path.splitext(os.path.basename(path))[0][:32]
    repository.create_match(
        {"model_key": record["red"]["model_key"], "name": record["red"]["name"]},
        {"model_key": record["black"]["model_key"], "name": record["black"]["name"]},
        initial_fen=XiangqiBoard().to_fen(),
        match_id=match_id,
    )
    for index, (move, (fen_after, in_check)) in enumerate(zip(moves, fens), start=1):
        repository.append_move(match_id, index, move, fen_after=fen_after,
                               in_check_after=in_check)

    stats = record["stats"]
    for side in ("red", "black"):
        stats[side].setdefault("cost_known", stats[side].get("cost_usd") is not None)

    repository.finish_match(
        match_id,
        {
            "result_status": record["result_status"],
            "result_reason": record["result_reason"],
            "winner_side": _winner_side(record),
            "history_count": record["total_plies"],
        },
        stats,
        stopped_reason=record.get("stopped_reason"),
    )
    return match_id, len(moves), record["result_reason"]


def _winner_side(record):
    if record["result_status"] == "red_win":
        return 'w'
    if record["result_status"] == "black_win":
        return 'b'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="các file JSON cần nhập")
    parser.add_argument("--all", action="store_true", help=f"nhập tất cả {DEFAULT_GLOB}")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    paths = args.paths or (sorted(glob.glob(DEFAULT_GLOB)) if args.all else [])
    if not paths:
        parser.error(f"không có file nào để nhập (dùng --all để lấy {DEFAULT_GLOB})")

    repository = MatchRepository(db_path=args.db)
    imported = 0
    for path in paths:
        try:
            match_id, plies, reason = import_file(repository, path)
        except (KeyError, ValueError) as exc:
            print(f"  BỎ QUA {path}: {exc}")
            continue
        print(f"  ✓ {os.path.basename(path)} -> {match_id} ({plies} nước, {reason})")
        imported += 1

    print(f"\nĐã nhập {imported}/{len(paths)} trận vào {args.db}")
    if repository.leaderboard():
        print("\nBảng xếp hạng hiện tại:")
        for rank, row in enumerate(repository.leaderboard(), start=1):
            print(f"  {rank}. {row['label']:24s} Elo {row['elo']:7.1f}  "
                  f"{row['matches']} trận  {row['wins']}W-{row['draws']}D-{row['losses']}L")
    repository.close()


if __name__ == "__main__":
    main()

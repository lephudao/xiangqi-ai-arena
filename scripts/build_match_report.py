#!/usr/bin/env python3
"""
Xuất báo cáo trận dạng Markdown để viết script video.

Cách dùng:
  scripts/build_match_report.py --list
  scripts/build_match_report.py <match_id> [-o plans/reports/tran.md]
  scripts/build_match_report.py --latest
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.reporting import render_markdown  # noqa: E402
from engine.storage import DEFAULT_DB_PATH, MatchRepository  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("match_id", nargs="?", help="mã trận cần xuất báo cáo")
    parser.add_argument("--list", action="store_true", help="liệt kê các trận đã lưu")
    parser.add_argument("--latest", action="store_true", help="lấy trận mới nhất")
    parser.add_argument("-o", "--output", help="ghi ra file thay vì in ra màn hình")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    repository = MatchRepository(db_path=args.db)
    matches = repository.list_matches(limit=100)

    if args.list or (not args.match_id and not args.latest):
        if not matches:
            print("Chưa có trận nào được lưu.")
            return
        print(f"{'MÃ TRẬN':34s} {'KỲ THỦ':46s} NƯỚC  KẾT QUẢ")
        for match in matches:
            pairing = f"{match['red_name'][:20]} vs {match['black_name'][:20]}"
            print(f"{match['id']:34s} {pairing:46s} {match['total_plies']:4d}  "
                  f"{match['result_reason']}")
        return

    match_id = args.match_id or matches[0]["id"]
    match = repository.get_match(match_id)
    if match is None:
        parser.error(f"không có trận '{match_id}'")

    markdown = render_markdown(match, repository.get_moves(match_id))
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(markdown)
        print(f"Đã ghi báo cáo: {args.output}")
    else:
        print(markdown)
    repository.close()


if __name__ == "__main__":
    main()

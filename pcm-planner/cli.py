#!/usr/bin/env python3
"""
cli.py — inspect and edit a PCM .cdb via the season planner.

Examples:
    python cli.py info      career.cdb
    python cli.py teams     career.cdb
    python cli.py program   career.cdb --team 16
    python cli.py tables    career.cdb
    python cli.py table     career.cdb STA_race --limit 10
"""
import argparse
from pcmdb.schema import Database
from pcmdb.planner import Planner

MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def cmd_info(args):
    db = Database.load(args.file)
    print(f"{args.file}: {len(db.tables)} tables")
    cyc = db["DYN_cyclist"]
    print(f"  riders: {cyc.nrow}   teams: {db['DYN_team'].nrow}   races: {db['STA_race'].nrow}")


def cmd_tables(args):
    db = Database.load(args.file)
    for name in sorted(db.tables):
        t = db[name]
        print(f"  {name:<40} id={t.id:<4} rows={t.nrow:<7} cols={len(t.colnames)}")


def cmd_table(args):
    db = Database.load(args.file)
    t = db[args.name]
    print(f"{args.name}  (id={t.id}, rows={t.nrow})")
    print("cols:", ", ".join(t.colnames))
    for i, row in enumerate(t.rows(limit=args.limit)):
        print(f"  [{i}]", {k: row[k] for k in t.colnames[:8]})


def cmd_teams(args):
    p = Planner.load(args.file)
    for tid, name in p.teams().items():
        if name:
            print(f"  {tid:>4}  {name}")


def cmd_program(args):
    p = Planner.load(args.file)
    prog = p.season_program(args.team)
    print(f"{p.team_name.get(args.team, args.team)} — {len(prog)} races\n")
    for e in prog:
        riders = ", ".join(p.rider_label(c) for c in e.roster[:9])
        date = f"{e.day:02d} {MONTHS[e.month] if 0 <= e.month <= 12 else e.month}"
        print(f"  {date:<7} {e.name[:36]:<36} [{len(e.roster)}] {riders}")


def main():
    ap = argparse.ArgumentParser(description="PCM .cdb planner CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name, fn in [("info", cmd_info), ("tables", cmd_tables),
                     ("teams", cmd_teams)]:
        s = sub.add_parser(name)
        s.add_argument("file")
        s.set_defaults(func=fn)

    s = sub.add_parser("table")
    s.add_argument("file"); s.add_argument("name")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_table)

    s = sub.add_parser("program")
    s.add_argument("file"); s.add_argument("--team", type=int, required=True)
    s.set_defaults(func=cmd_program)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

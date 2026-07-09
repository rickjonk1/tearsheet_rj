#!/usr/bin/env python3
"""
Local app server — stdlib only (no runtime deps, easy to package as a desktop app).

    python -m server.app [career.cdb] [--port 8765]

Serves the web/ SPA and a small JSON API over the loaded career.
"""
import json
import os
import sys
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pcmdb.model import Career, CHARAC_LABELS
from pcmdb import calendar_gen

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
CAREER = None
CAREER_PATH = None


def _team_summary():
    out = []
    for t in CAREER.teams.values():
        riders = [CAREER.riders[r] for r in t["riders"]]
        if not riders:
            continue
        avg = round(sum(r["ability"] for r in riders) / len(riders), 1)
        best = max(riders, key=lambda r: r["ability"])
        out.append({"id": t["id"], "name": t["name"], "riderCount": len(riders),
                    "avgAbility": avg, "topRider": CAREER.rider_label(best["id"]),
                    "topAbility": best["ability"]})
    out.sort(key=lambda x: x["avgAbility"], reverse=True)
    return out


def _program(team_id):
    prog = CAREER.season_program(team_id)
    for e in prog:
        objr = CAREER.objectives_for_race(e["race"])
        e["objectives"] = len(objr & set(e["roster"]))
        e["roster"] = [{"id": rid, "name": CAREER.rider_label(rid),
                        "ability": CAREER.riders[rid]["ability"] if rid in CAREER.riders else 0,
                        "specialty": CAREER.riders[rid]["specialty"] if rid in CAREER.riders else "",
                        "fit": CAREER.race_fit(rid, e["race"]),
                        "obj": rid in objr} for rid in e["roster"]]
    return prog


def _squad(team_id):
    out = []
    for rid in CAREER.teams[team_id]["riders"]:
        r = CAREER.riders[rid]
        out.append({"id": rid, "name": CAREER.rider_label(rid), "ability": r["ability"],
                    "potential": r["potential"], "specialty": r["specialty"],
                    "charac": {CHARAC_LABELS.get(k, k): v for k, v in r["charac"].items()
                               if k in CHARAC_LABELS}})
    out.sort(key=lambda x: x["ability"], reverse=True)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path):
        rel = path.lstrip("/") or "index.html"
        fp = os.path.normpath(os.path.join(WEB, rel))
        if not fp.startswith(WEB) or not os.path.isfile(fp):
            return self._send(404, "not found", "text/plain")
        ext = os.path.splitext(fp)[1]
        ctype = {".html": "text/html", ".css": "text/css", ".js": "application/javascript",
                 ".svg": "image/svg+xml"}.get(ext, "application/octet-stream")
        with open(fp, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/bootstrap":
            return self._send(200, {
                "path": CAREER_PATH,
                "counts": {"riders": len(CAREER.riders), "races": len(CAREER.races),
                           "teams": sum(1 for t in CAREER.teams.values() if t["riders"])},
                "teams": _team_summary(),
            })
        if u.path == "/api/team":
            tid = int(q.get("id", [0])[0])
            return self._send(200, {"id": tid, "name": CAREER.teams[tid]["name"],
                                    "program": _program(tid), "squad": _squad(tid)})
        if u.path == "/api/fit":
            tid = int(q.get("team", [0])[0])
            rid = int(q.get("race", [0])[0])
            fit = {r: CAREER.race_fit(r, rid) for r in CAREER.teams[tid]["riders"]}
            return self._send(200, fit)
        return self._static(u.path)

    def do_POST(self):
        u = urlparse(self.path)
        ln = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(ln) or b"{}")
        if u.path == "/api/roster":
            CAREER.set_roster(int(data["row"]), [int(x) for x in data["riders"]])
            return self._send(200, {"ok": True})
        if u.path == "/api/generate":
            tid = int(data["team"])
            seed = int(data.get("seed", 1))
            variety = float(data.get("variety", 0.15))
            gen = calendar_gen.generate(CAREER, seed=seed, teams=[tid], variety=variety)
            preview = [{"race": e["race"], "name": e["name"], "day": e["day"], "month": e["month"],
                        "leader": CAREER.rider_label(e["leader"]),
                        "roster": [CAREER.rider_label(x) for x in e["roster"]]} for e in gen[tid]]
            if data.get("apply"):
                calendar_gen.apply(CAREER, gen)
            return self._send(200, {"planned": len(preview), "preview": preview})
        if u.path == "/api/generate-all":
            seed = int(data.get("seed", 1))
            variety = float(data.get("variety", 0.15))
            gen = calendar_gen.generate(CAREER, seed=seed, variety=variety)
            changed = calendar_gen.apply(CAREER, gen)
            teams = sum(1 for v in gen.values() if v)
            return self._send(200, {"teams": teams, "rosters": changed})
        if u.path == "/api/objective":
            added = CAREER.toggle_objective(int(data["rider"]), int(data["race"]))
            return self._send(200, {"added": added})
        if u.path == "/api/save":
            out = data.get("path") or CAREER_PATH
            CAREER.save(out)
            return self._send(200, {"ok": True, "path": out})
        return self._send(404, {"error": "unknown"})


def main():
    global CAREER, CAREER_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("career", nargs="?", default=os.environ.get("PCM_CDB", "career.cdb"))
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    CAREER_PATH = args.career
    print(f"Loading {CAREER_PATH} ...")
    CAREER = Career.load(CAREER_PATH)
    print(f"  {len(CAREER.riders)} riders, {len(CAREER.races)} races, "
          f"{sum(1 for t in CAREER.teams.values() if t['riders'])} teams")
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"PCM Planner running at http://127.0.0.1:{args.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()

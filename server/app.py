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


def open_career(path):
    """(Re)load a career .cdb into the module globals."""
    global CAREER, CAREER_PATH
    CAREER = Career.load(path)
    CAREER_PATH = path
    return CAREER


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


def _program(team_id, load=None):
    prog = CAREER.season_program(team_id)
    # race -> set of riders with a scheduling conflict touching that race
    conf_by_race = {}
    if load:
        for c in load["conflicts"]:
            conf_by_race.setdefault(c["a"], set()).add(c["rider"])
            conf_by_race.setdefault(c["b"], set()).add(c["rider"])
    for e in prog:
        objr = CAREER.objectives_for_race(e["race"])
        e["objectives"] = len(objr & set(e["roster"]))
        cr = conf_by_race.get(e["race"], set())
        e["warn"] = len(cr & set(e["roster"]))
        e["roster"] = [{"id": rid, "name": CAREER.rider_label(rid),
                        "ability": CAREER.riders[rid]["ability"] if rid in CAREER.riders else 0,
                        "specialty": CAREER.riders[rid]["specialty"] if rid in CAREER.riders else "",
                        "fit": CAREER.race_fit(rid, e["race"]),
                        "obj": rid in objr, "warn": rid in cr} for rid in e["roster"]]
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
            if CAREER is None:
                return self._send(200, {"path": None, "loaded": False,
                                        "counts": {"riders": 0, "races": 0, "teams": 0}, "teams": []})
            return self._send(200, {
                "path": CAREER_PATH, "loaded": True,
                "counts": {"riders": len(CAREER.riders), "races": len(CAREER.races),
                           "teams": sum(1 for t in CAREER.teams.values() if t["riders"])},
                "teams": _team_summary(),
            })
        if u.path == "/api/team":
            tid = int(q.get("id", [0])[0])
            load = CAREER.team_load(tid)
            return self._send(200, {"id": tid, "name": CAREER.teams[tid]["name"],
                                    "program": _program(tid, load), "squad": _squad(tid)})
        if u.path == "/api/fit":
            tid = int(q.get("team", [0])[0])
            rid = int(q.get("race", [0])[0])
            fit = {r: CAREER.race_fit(r, rid) for r in CAREER.teams[tid]["riders"]}
            busy = sorted(CAREER.race_busy_riders(tid, rid))
            return self._send(200, {"fit": fit, "busy": busy})
        if u.path == "/api/form":
            tid = int(q.get("team", [0])[0])
            return self._send(200, {"year": CAREER.season_year(), "riders": CAREER.team_form(tid)})
        if u.path == "/api/camps":
            month = q.get("month")
            camps = CAREER.camps(int(month[0]) if month else None)
            tid = q.get("team")
            booked = CAREER.team_camps(int(tid[0])) if tid else []
            return self._send(200, {"year": CAREER.season_year(), "camps": camps, "booked": booked})
        if u.path == "/api/load":
            tid = int(q.get("team", [0])[0])
            info = CAREER.team_load(tid)
            rows = []
            for rid in CAREER.teams[tid]["riders"]:
                ld = info["load"].get(rid, {"racedays": 0, "races": 0, "conflicts": 0})
                r = CAREER.riders[rid]
                rows.append({"id": rid, "name": CAREER.rider_label(rid), "ability": r["ability"],
                             "specialty": r["specialty"], "racedays": ld["racedays"],
                             "races": ld["races"], "conflicts": ld["conflicts"],
                             "objectives": len(CAREER.rider_objectives(rid))})
            rows.sort(key=lambda x: x["racedays"], reverse=True)
            return self._send(200, {"riders": rows, "conflicts": len(info["conflicts"])})
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
            plan = gen[tid]["plan"]
            preview = [{"race": e["race"], "name": e["name"], "day": e["day"], "month": e["month"],
                        "leader": CAREER.rider_label(e["leader"]),
                        "roster": [CAREER.rider_label(x) for x in e["roster"]]} for e in plan]
            if data.get("apply"):
                calendar_gen.apply(CAREER, gen)
            return self._send(200, {"planned": len(preview), "preview": preview})
        if u.path == "/api/season-setup":
            tid = int(data["team"])
            seed = int(data.get("seed", 7))
            roles = {tid: {"leaders": [int(x) for x in data.get("leaders", [])] or None,
                           "coleaders": [int(x) for x in data.get("coleaders", [])] or None}}
            gen = calendar_gen.generate(CAREER, seed=seed, teams=[tid], roles=roles)
            res = gen[tid]
            plan_by_race = {p["race"]: p for p in res["plan"]}
            def sched(rid):
                out = []
                for r in res["objectives"].get(rid, []):
                    ra = CAREER.races[r]
                    out.append({"race": r, "name": ra["name"], "day": ra["day"],
                                "month": ra["month"], "pop": ra["popularity"],
                                "fit": CAREER.race_fit(rid, r)})
                out.sort(key=lambda x: (x["month"], x["day"]))
                return out
            captains = []
            for role, rids in (("Leider", res["roles"]["leaders"]),
                               ("Co-leider", res["roles"]["coleaders"])):
                for rid in rids:
                    rr = CAREER.riders[rid]
                    s = sched(rid)
                    gate = 0.90 if role == "Leider" else 0.83
                    captains.append({"id": rid, "name": CAREER.rider_label(rid), "role": role,
                                     "ability": rr["ability"], "specialty": rr["specialty"],
                                     "races": s, "candidates": calendar_gen.candidates_for(CAREER, tid, rid, gate),
                                     "recons": sorted(x for x in CAREER.rider_recon_races(rid) if x),
                                     "days": sum(max(1, CAREER.races[x["race"]]["stages"]) for x in s)})
            if data.get("apply"):
                calendar_gen.apply(CAREER, gen)
            camps = CAREER.team_camps(tid)
            return self._send(200, {"year": CAREER.season_year(), "captains": captains,
                                    "planned": len(res["plan"]),
                                    "domestiques": len(res["roles"]["domestiques"]), "camps": camps})
        if u.path == "/api/season-preview":
            tid = int(data["team"])
            roles = {"leaders": [int(x) for x in data.get("leaders", [])] or None,
                     "coleaders": [int(x) for x in data.get("coleaders", [])] or None}
            captain_races = {int(k): [int(x) for x in v] for k, v in data.get("captains", {}).items()}
            res = calendar_gen.build_from_captains(CAREER, tid, captain_races, roles=roles,
                                                   seed=int(data.get("seed", 7)))
            role_of = {}
            for rid in res["roles"]["leaders"]:
                role_of[rid] = "Leider"
            for rid in res["roles"]["coleaders"]:
                role_of.setdefault(rid, "Co-leider")
            # per-rider races from the plan
            by_rider = {}
            for p in res["plan"]:
                for rid in p["roster"]:
                    by_rider.setdefault(rid, []).append(p["race"])

            def daynum(ra):
                return (ra["month"] - 1) * 31 + ra["day"]

            def peak_set(race_ids):
                races = sorted((CAREER.races[r] for r in race_ids),
                               key=lambda ra: -ra["popularity"])
                chosen = []
                for ra in races:
                    if ra["popularity"] < 55:
                        continue
                    if all(abs(daynum(ra) - daynum(c)) >= 70 for c in chosen):
                        chosen.append(ra)
                    if len(chosen) >= 2:
                        break
                return {ra["id"] for ra in chosen}

            riders = []
            order = {"Leider": 0, "Co-leider": 1, "Knecht": 2}
            for rid in CAREER.teams[tid]["riders"]:
                rc = by_rider.get(rid, [])
                role = role_of.get(rid, "Knecht")
                obj = set(res["objectives"].get(rid, []))
                peaks = peak_set(res["objectives"].get(rid, [])) if role != "Knecht" else set()
                recon = CAREER.rider_recon_races(rid)
                rr = CAREER.riders[rid]
                races = []
                for r in sorted(rc, key=lambda x: (CAREER.races[x]["month"], CAREER.races[x]["day"])):
                    ra = CAREER.races[r]
                    races.append({"race": r, "name": ra["name"], "day": ra["day"], "month": ra["month"],
                                  "pop": ra["popularity"], "leader": r in obj,
                                  "peak": r in peaks, "recon": r in recon})
                riders.append({"id": rid, "name": CAREER.rider_label(rid), "role": role,
                               "ability": rr["ability"], "specialty": rr["specialty"],
                               "days": sum(max(1, CAREER.races[x]["stages"]) for x in rc),
                               "races": races,
                               "candidates": calendar_gen.candidates_for(CAREER, tid, rid,
                                   0.90 if role == "Leider" else 0.83) if role != "Knecht" else []})
            riders.sort(key=lambda x: (order[x["role"]], -x["ability"]))
            return self._send(200, {"year": CAREER.season_year(), "riders": riders,
                                    "camps": CAREER.team_camps(tid), "planned": len(res["plan"])})
        if u.path == "/api/season-apply":
            tid = int(data["team"])
            roles = {"leaders": [int(x) for x in data.get("leaders", [])] or None,
                     "coleaders": [int(x) for x in data.get("coleaders", [])] or None}
            captain_races = {int(k): [int(x) for x in v] for k, v in data.get("captains", {}).items()}
            res = calendar_gen.build_from_captains(CAREER, tid, captain_races, roles=roles,
                                                   seed=int(data.get("seed", 7)))
            changed = calendar_gen.apply(CAREER, {tid: res})
            # dynamic form: peak each captain around their biggest targets
            peaked = 0
            if data.get("peaks", True):
                year = CAREER.season_year()
                for rider, races in res["objectives"].items():
                    # priority order (most prestigious first); set_peaks keeps <=2, >=10 weeks apart
                    big = sorted((CAREER.races[r] for r in races),
                                 key=lambda ra: -ra["popularity"])
                    dates = [year * 10000 + ra["month"] * 100 + ra["day"]
                             for ra in big if ra["popularity"] >= 55]
                    if dates:
                        CAREER.set_peaks(rider, dates); peaked += 1
            if data.get("save"):
                CAREER.save()
            return self._send(200, {"ok": True, "rosters": changed,
                                    "planned": len(res["plan"]), "peaked": peaked})
        if u.path == "/api/generate-all":
            seed = int(data.get("seed", 1))
            variety = float(data.get("variety", 0.15))
            exclude = data.get("exclude")
            teams = None
            if exclude is not None:
                teams = [t for t in CAREER.teams if t != int(exclude)]
            gen = calendar_gen.generate(CAREER, seed=seed, variety=variety, teams=teams)
            changed = calendar_gen.apply(CAREER, gen)
            if data.get("save"):
                CAREER.save()
            return self._send(200, {"teams": sum(1 for v in gen.values() if v["plan"]),
                                    "rosters": changed})
        if u.path == "/api/objective":
            added = CAREER.toggle_objective(int(data["rider"]), int(data["race"]))
            return self._send(200, {"added": added})
        if u.path == "/api/form":
            CAREER.set_form(int(data["rider"]), data["fields"])
            return self._send(200, {"ok": True})
        if u.path == "/api/form-bulk":
            tid = int(data["team"])
            action = data.get("action")
            for r in CAREER.team_form(tid):
                if action == "fresh":
                    CAREER.set_form(r["id"], {"freshness": 100.0, "fatigue": 0.0})
                elif action == "peak":
                    CAREER.set_form(r["id"], {"freshness": 100.0, "fatigue": 0.0, "fit": 99.0, "prepa": 99.0})
            return self._send(200, {"ok": True, "count": len(CAREER.team_form(tid))})
        if u.path == "/api/plan-altitude":
            camp = CAREER.plan_altitude(int(data["team"]), int(data["target"]))
            return self._send(200, {"ok": camp is not None, "camp": camp})
        if u.path == "/api/recon":
            CAREER.set_recon(int(data["rider"]), int(data["race"]), bool(data.get("on", True)))
            return self._send(200, {"ok": True})
        if u.path == "/api/book-camp":
            nid = CAREER.book_camp(int(data["team"]), int(data["stage"]),
                                   int(data["start"]), int(data["end"]))
            return self._send(200, {"ok": True, "id": nid})
        if u.path == "/api/open":
            open_career(data["path"])
            return self._send(200, {"ok": True, "path": CAREER_PATH,
                                    "teams": len(CAREER.teams)})
        if u.path == "/api/save":
            out = data.get("path") or CAREER_PATH
            CAREER.save(out)
            return self._send(200, {"ok": True, "path": out})
        return self._send(404, {"error": "unknown"})


def build_server(port=8765):
    """Create the HTTP server (used by both the CLI and the desktop launcher)."""
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("career", nargs="?", default=os.environ.get("PCM_CDB", "career.cdb"))
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()
    if os.path.isfile(args.career):
        print(f"Loading {args.career} ...")
        open_career(args.career)
        print(f"  {len(CAREER.riders)} riders, {len(CAREER.races)} races, "
              f"{sum(1 for t in CAREER.teams.values() if t['riders'])} teams")
    else:
        print(f"(no career loaded — open one via the UI)")
    srv = build_server(args.port)
    print(f"PCM Planner running at http://127.0.0.1:{args.port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()

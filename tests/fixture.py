"""
fixture.py — builds a synthetic, self-contained career .cdb for the test suite.

Why: every test used to need a real game save at $PCM_CDB. On a fresh machine
(or CI) that file does not exist, so the whole suite either errored or silently
skipped — meaning the editor's write paths were effectively untested.

This module constructs a small but structurally complete career: 2 teams,
16 riders, 6 races with stages, the race class/type lookup tables, the training
and equipment tables. It is written with the real chunk writer, so anything the
editor does to a real save (encode a column, add a blob chunk, replace a table
body) exercises the same code here.

Scope note: because the fixture is produced by our own writer, the round-trip
tests over it prove reader/writer self-consistency, not byte-compatibility with
a file Cyanide produced. That stronger guarantee still needs a real save — the
tests that assert it stay guarded behind $PCM_CDB.
"""
import struct

from pcmdb import cdb

# characteristics every rider row carries (model.py derives specialty from these)
CHARACS = [
    "charac_i_mountain", "charac_i_medium_mountain", "charac_i_hill",
    "charac_i_plain", "charac_i_timetrial", "charac_i_prologue",
    "charac_i_sprint", "charac_i_cobble", "charac_i_acceleration",
    "charac_i_endurance", "charac_i_resistance", "charac_i_recuperation",
    "charac_i_baroudeur", "charac_i_downhilling",
]
WEIGHTS = ["mo_weight", "mm_weight", "val_weight", "rec_weight", "itt_weight",
           "prl_weight", "sp_weight", "pav_weight", "pl_weight"]

YEAR = 2030


# ---------- chunk construction helpers ----------

def _leaf(type_, raw, desc=None):
    ch = cdb.Chunk(type_, desc=desc)
    ch.raw = raw
    return ch


def _container(type_, children, desc=None, array=False):
    ch = cdb.Chunk(type_, desc=desc)
    ch.children = children
    if array:
        ch.is_array = True
        ch.array_count = len(children)
    return ch


def _column(index, name, dtype, values):
    """Build one COLUMN chunk, encoding `values` with the production encoder."""
    from pcmdb.schema import _encode_column
    vbytes, bbytes = _encode_column(dtype, values)
    kids = [
        _leaf(cdb.COLUMN_INDEX, struct.pack("<I", index)),
        _leaf(cdb.COLUMN_DATA_TYPE, struct.pack("<I", dtype)),
        _leaf(cdb.COLUMN_VALUES, vbytes),
    ]
    # a real save carries NO blob chunk when there is nothing in it (an all-empty
    # list/string column is just the 4-byte prefix), so the fixture must not either
    if bbytes is not None and len(bbytes) > 4:
        kids.append(_leaf(cdb.COLUMN_BLOB, bbytes))
    return _container(cdb.COLUMN, kids, desc=name)


def _table(table_id, name, columns):
    """columns: list of (colname, dtype, values). All values equal length."""
    nrow = len(columns[0][2]) if columns else 0
    for cname, _, vals in columns:
        if len(vals) != nrow:
            raise ValueError("column %s has %d values, expected %d" % (cname, len(vals), nrow))
    coldefs = [_column(i, cname, dtype, vals)
               for i, (cname, dtype, vals) in enumerate(columns)]
    kids = [
        _leaf(cdb.TABLE_ID, struct.pack("<i", table_id)),
        _leaf(cdb.TABLE_FLAGS, struct.pack("<I", 0)),
        _leaf(cdb.ROW_COUNT, struct.pack("<I", nrow)),
        _container(cdb.COLUMN_DEFINITIONS, coldefs, array=True),
    ]
    return _container(cdb.TABLE, kids, desc=name)


# ---------- the synthetic career ----------

def _riders():
    """A realistically sized squad: 20 riders per team for rosters of at most 8.

    The surplus matters — with a squad the same size as the roster every rider is
    selected no matter how bad the selection logic is, and tests over squad
    composition prove nothing. Profiles are deliberately distinct so route fit has
    something to discriminate on.
    """
    # (last, first, team, ability, profile) where profile boosts a characteristic
    squad = [
        ("Bergman", 82.0, "charac_i_mountain"),
        ("Alpe", 76.0, "charac_i_mountain"),
        ("Col", 74.0, "charac_i_mountain"),
        ("Klim", 72.0, "charac_i_mountain"),
        ("Kassei", 80.0, "charac_i_cobble"),
        ("Keien", 75.0, "charac_i_cobble"),
        ("Sprinter", 78.0, "charac_i_sprint"),
        ("Snel", 73.0, "charac_i_sprint"),
        ("Chrono", 77.0, "charac_i_timetrial"),
        ("Uurwerk", 72.0, "charac_i_timetrial"),
        ("Heuvel", 76.0, "charac_i_hill"),
        ("Helling", 71.0, "charac_i_hill"),
        ("Vlakte", 74.0, "charac_i_plain"),
        ("Rouleur", 70.0, "charac_i_plain"),
        ("Herstel", 71.0, "charac_i_recuperation"),
        ("Proloog", 70.0, "charac_i_prologue"),
        ("Knecht", 69.0, None),
        ("Helper", 68.0, None),
        ("Steun", 67.0, None),
        ("Jonge", 66.0, None),
    ]
    firsts = ["Jonas", "Wout", "Fabio", "Filippo", "Julian", "Tim", "Koen", "Sam",
              "Egan", "Mathieu", "Jasper", "Remco", "Tadej", "Bert", "Nils", "Loe",
              "Primoz", "Mads", "Biniam", "Kasper"]
    people = []
    for team, suffix in ((1, ""), (2, "sen")):
        for i, (last, ability, prof) in enumerate(squad):
            people.append((last + suffix, firsts[i], team,
                           ability - (0.5 if team == 2 else 0.0), prof))
    n = len(people)
    cols = {
        "IDcyclist": list(range(1, n + 1)),
        "gene_sz_lastname": [p[0] for p in people],
        "gene_sz_firstname": [p[1] for p in people],
        "fkIDteam": [p[2] for p in people],
        "value_f_current_ability": [p[3] for p in people],
        "value_f_potentiel": [p[3] + 2.0 for p in people],
        "gene_i_birthdate": [(YEAR - 27 - (i % 8)) * 10000 + 615 for i in range(n)],
        "fkIDtype_rider": [1 for _ in people],
    }
    # Only the nine characteristics in WEIGHT_TO_CHARAC feed race_fit. Specialists
    # get a low base and a high peak so route fit actually discriminates (a climber
    # must score clearly below his own gate on the cobbled classics); domestiques
    # stay flat and mediocre, which is what makes them fill rosters everywhere.
    for ch in CHARACS:
        cols[ch] = [58 for _ in people]
    fit_characs = ["charac_i_mountain", "charac_i_medium_mountain", "charac_i_hill",
                   "charac_i_recuperation", "charac_i_timetrial", "charac_i_prologue",
                   "charac_i_sprint", "charac_i_cobble", "charac_i_plain"]
    for i, p in enumerate(people):
        if p[4]:
            for ch in fit_characs:
                cols[ch][i] = 45
            cols[p[4]][i] = 88          # the specialty they are known for
        cols["charac_i_endurance"][i] = 65 + (i % 5)
        cols["charac_i_resistance"][i] = 63 + (i % 6)
    order = (["IDcyclist", "gene_sz_lastname", "gene_sz_firstname", "fkIDteam",
              "value_f_current_ability", "value_f_potentiel", "gene_i_birthdate",
              "fkIDtype_rider"] + CHARACS)
    out = []
    for name in order:
        vals = cols[name]
        if name.startswith("gene_sz_"):
            dt = cdb.DT_STRING
        elif name.startswith("value_f_"):
            dt = cdb.DT_FLOAT
        else:
            dt = cdb.DT_INT
        out.append((name, dt, vals))
    return out


# races: (id, name, class, type, popularity, day, month, n_stages)
RACES = [
    (1, "Ronde van Vlaanderen", 1, 3, 78.0, 5, 4, 1),
    (2, "Paris-Roubaix", 1, 3, 80.0, 12, 4, 1),
    (3, "Luik-Bastenaken-Luik", 1, 2, 76.0, 26, 4, 1),
    (4, "Giro d'Italia", 1, 1, 88.0, 8, 5, 21),
    (5, "Tour de France", 1, 1, 95.0, 4, 7, 21),
    (6, "Ronde van Polen", 2, 1, 58.0, 3, 8, 7),
    (7, "Ronde van Burgos", 2, 1, 55.0, 29, 7, 5),   # close after the Tour on purpose
    (8, "Milaan-Sanremo", 1, 3, 74.0, 21, 3, 1),
]
BOTH_TEAMS = [1, 2]


def _stage_rows():
    """One stage row per race (the race's first stage carries its date)."""
    ids, races, days, months, dates = [], [], [], [], []
    for rid, _, _, _, _, day, month, _ in RACES:
        ids.append(rid)          # stage id == race id keeps the fixture readable
        races.append(rid)
        days.append(day)
        months.append(month)
        dates.append(YEAR * 10000 + month * 100 + day)
    return [
        ("IDstage", cdb.DT_INT, ids),
        ("fkIDrace", cdb.DT_INT, races),
        ("gene_i_day", cdb.DT_INT, days),
        ("gene_i_month", cdb.DT_INT, months),
        ("gene_i_computed_date", cdb.DT_INT, dates),
    ]


def _race_type_rows():
    """3 disciplines: 1 = climbing, 2 = hilly, 3 = cobbles."""
    profiles = {
        1: {"mo_weight": 5, "mm_weight": 3, "val_weight": 2, "rec_weight": 3,
            "itt_weight": 2, "prl_weight": 1, "sp_weight": 1, "pav_weight": 0, "pl_weight": 1},
        2: {"mo_weight": 1, "mm_weight": 3, "val_weight": 5, "rec_weight": 2,
            "itt_weight": 1, "prl_weight": 1, "sp_weight": 2, "pav_weight": 0, "pl_weight": 2},
        3: {"mo_weight": 0, "mm_weight": 1, "val_weight": 2, "rec_weight": 1,
            "itt_weight": 1, "prl_weight": 1, "sp_weight": 3, "pav_weight": 5, "pl_weight": 4},
    }
    ids = sorted(profiles)
    cols = [("IDrace_type", cdb.DT_INT, ids)]
    for w in WEIGHTS:
        cols.append((w, cdb.DT_INT, [profiles[i][w] for i in ids]))
    return cols


def build_tree(extra_columns=None):
    """Assemble the whole synthetic database as a chunk tree.

    extra_columns: {table_name: [(colname, dtype, default), ...]} — columns the
    REAL game database has and we have never seen. Used to prove our writers
    preserve what they do not understand instead of zeroing or crashing on it.
    """
    extra_columns = extra_columns or {}
    tables = []
    tid = 0

    def add(name, columns):
        nonlocal tid
        tid += 1
        nrow = len(columns[0][2]) if columns else 0
        for cname, dtype, default in extra_columns.get(name, []):
            columns = list(columns) + [(cname, dtype, [default] * nrow)]
        tables.append(_table(tid, name, columns))

    add("STA_stage", _stage_rows())
    add("STA_race_type", _race_type_rows())
    add("STA_race", [
        ("IDrace", cdb.DT_INT, [r[0] for r in RACES]),
        ("gene_sz_race_name", cdb.DT_STRING, [r[1] for r in RACES]),
        ("fkIDrace_class", cdb.DT_INT, [r[2] for r in RACES]),
        ("fkIDrace_type", cdb.DT_INT, [r[3] for r in RACES]),
        ("gene_f_popularity", cdb.DT_FLOAT, [r[4] for r in RACES]),
        ("fkIDcountry", cdb.DT_INT, [5 for _ in RACES]),
        ("fkIDfirst_stage", cdb.DT_INT, [r[0] for r in RACES]),
        ("gene_i_number_stages", cdb.DT_INT, [r[7] for r in RACES]),
        ("gene_ilist_fkIDteam", cdb.DT_INT_LIST, [list(BOTH_TEAMS) for _ in RACES]),
    ])
    add("STA_race_class", [
        ("IDrace_class", cdb.DT_INT, [1, 2]),
        ("gene_i_min_riders", cdb.DT_INT, [6, 4]),
        ("gene_i_max_riders", cdb.DT_INT, [8, 6]),
    ])
    add("DYN_team", [
        ("IDteam", cdb.DT_INT, [1, 2]),
        ("gene_sz_name", cdb.DT_STRING, ["Team Alpha", "Team Beta"]),
    ])
    add("DYN_cyclist", _riders())

    # every team is entered in every race, rosters start empty
    pairs = [(t, r[0]) for t in BOTH_TEAMS for r in RACES]
    add("DYN_team_race", [
        ("IDteam_race", cdb.DT_INT, list(range(1, len(pairs) + 1))),
        ("fkIDteam", cdb.DT_INT, [p[0] for p in pairs]),
        ("fkIDrace", cdb.DT_INT, [p[1] for p in pairs]),
        ("gene_ilist_roster", cdb.DT_INT_LIST, [[] for _ in pairs]),
    ])

    nrid = 40                      # 2 teams x 20 riders
    add("DYN_cyclist_fitness", [
        ("IDcyclist", cdb.DT_INT, list(range(1, nrid + 1))),
        ("value_f_FIT", cdb.DT_FLOAT, [70.0] * nrid),
        ("value_f_fat_phy", cdb.DT_FLOAT, [20.0] * nrid),
        ("value_f_freshness", cdb.DT_FLOAT, [80.0] * nrid),
        ("value_f_prepa", cdb.DT_FLOAT, [75.0] * nrid),
        ("peak_value", cdb.DT_FLOAT, [1.0] * nrid),
    ])
    # one pre-existing peak in a PAST season: set_peaks must leave it alone
    add("DYN_cyclist_fitpeak_history", [
        ("IDcyclist_fitpeak_history", cdb.DT_INT, [1]),
        ("fkIDcyclist", cdb.DT_INT, [1]),
        ("value_i_date_begin", cdb.DT_INT, [(YEAR - 1) * 10000 + 601]),
        ("value_i_date_end_min", cdb.DT_INT, [(YEAR - 1) * 10000 + 621]),
        ("value_i_date_end_max", cdb.DT_INT, [(YEAR - 1) * 10000 + 621]),
    ])
    add("DYN_cyclist_objective", [
        ("IDcyclist_objective", cdb.DT_INT, [1]),
        ("fkIDcyclist", cdb.DT_INT, [16]),
        ("fkIDrace", cdb.DT_INT, [6]),
    ])
    # real type ids: 3 == MONTAGNE (altitude), 9 == RECONNAISSANCE
    add("STA_training_stages", [
        ("IDtraining_stage", cdb.DT_INT, [1, 2, 3]),
        ("gene_sz_place", cdb.DT_STRING, ["Sierra Nevada", "Teide", "Vlaamse Ardennen"]),
        ("gene_i_stars", cdb.DT_INT, [4, 5, 3]),
        ("fkIDtype_stage", cdb.DT_INT, [3, 3, 4]),
        ("gene_i_opening_month", cdb.DT_INT, [3, 1, 1]),
        ("gene_i_closing_month", cdb.DT_INT, [10, 12, 12]),
    ])
    add("STA_training_stages_state", [
        ("IDtraining_stage_state", cdb.DT_INT, [0, 1]),
        ("CONSTANT", cdb.DT_STRING, ["SCHEDULED", "CANCELLED"]),
    ])
    add("DYN_training_stage_booking", [
        ("IDtraining_stage_booking", cdb.DT_INT, [1]),
        ("fkIDtraining_stage", cdb.DT_INT, [3]),
        ("gene_i_start_date", cdb.DT_INT, [YEAR * 10000 + 210]),
        ("gene_i_end_date", cdb.DT_INT, [YEAR * 10000 + 220]),
        ("fkIDteam", cdb.DT_INT, [2]),
        ("fkIDstate", cdb.DT_INT, [0]),
        ("value_i_efficacite", cdb.DT_INT, [60]),
    ])
    add("DYN_training_stage_recon", [
        ("IDtraining_stage_recon", cdb.DT_INT, [1]),
        ("fkIDcyclist", cdb.DT_INT, [16]),
        ("fkIDstage", cdb.DT_INT, [6]),
    ])

    # frame archetypes, 4 versions each, with the game's default (unbalanced) weights
    frames = [("poly", 2, 3, 1), ("mountain", 0, 3, 1), ("plain", 3, 1, 0),
              ("cobbles", 0, 1, 3), ("tt_flat", 3, 0, 0), ("tt_poly", 3, 1, 0)]
    names, aero, light, conf = [], [], [], []
    for v in range(1, 5):
        for base, a, li, c in frames:
            names.append(base if v == 1 else "%s%d" % (base, v))
            aero.append(a); light.append(li); conf.append(c)
    n = len(names)
    add("STA_equipment_template", [
        ("IDequipment_template", cdb.DT_INT, list(range(1, n + 1))),
        ("fkIDequipment_type", cdb.DT_INT, [1] * n),
        ("gene_i_weight_aero", cdb.DT_INT, aero),
        ("gene_i_weight_light", cdb.DT_INT, light),
        ("gene_i_weight_confort", cdb.DT_INT, conf),
        ("CONSTANT", cdb.DT_STRING, names),
    ])

    tables_chunk = _container(cdb.DATABASE_TABLES, tables, array=True)
    flags = _leaf(cdb.DATABASE_FLAGS, struct.pack("<I", 0))
    return _container(cdb.WRAPPER, [flags, tables_chunk])


def write(path, extra_columns=None):
    """Write the synthetic career to `path` and return it."""
    cdb.save(str(path), build_tree(extra_columns))
    return str(path)

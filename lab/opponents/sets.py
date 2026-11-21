"""Opponent sets. resolve_opps("core,rand10") -> [(label, spec), ...].

Tokens (comma separated):
  core            archetypes + kit bots
  rand<N>         N randomly parameterised archetype bots (rand=0..N-1)
  exploit         exploiter bots aimed at our tendencies
  snap:<name>     a snapshot in lab/snapshots/<name>
  label=path      any bot folder / file spec
  <preset>        a single archetype preset
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARCH = "lab/opponents/archetype.py"
PRESETS = ["station", "maniac", "nit", "tag", "lag", "overfolder", "shover", "trapper", "random", "minraiser"]


def resolve_opps(s):
    out = []
    for tok in s.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok == "core":
            out += [(p, f"{ARCH}::preset={p}") for p in PRESETS]
            out += [("kit_caller", "bots/caller"), ("kit_template", "bots/template")]
        elif tok.startswith("rand") and tok[4:].isdigit():
            out += [(f"rand{k}", f"{ARCH}::rand={k}") for k in range(int(tok[4:]))]
        elif tok == "exploit":
            for p in sorted((ROOT / "lab/opponents/exploiters").glob("*.py")):
                if p.name != "__init__.py":
                    out.append((f"x_{p.stem}", str(p.relative_to(ROOT))))
        elif tok.startswith("snap:"):
            n = tok[5:]
            out.append((n, f"lab/snapshots/{n}"))
        elif "=" in tok and "::" not in tok.split("=", 1)[0]:
            label, spec = tok.split("=", 1)
            out.append((label, spec))
        elif tok in PRESETS:
            out.append((tok, f"{ARCH}::preset={tok}"))
        else:
            raise ValueError(f"unknown opponent token {tok!r}")
    return out

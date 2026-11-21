"""In-process seat: calls a bot's decide() directly (no subprocess), with the
same seeding, action cleaning and timeout semantics as pokercore/sandbox/runner.py.

Bot spec strings:
  "my_bots/redteamers007"                 folder with bot.py
  "lab/opponents/archetype.py::preset=nit"  file + params (module.configure(params) is called after load)
A fresh module object is created per match, so module-level state lasts one match.
"""
import hashlib
import importlib.util
import io
import os
import random
import sys
import time
import contextlib
from pathlib import Path

from pokercore.seats import Seat

ROOT = Path(__file__).resolve().parents[1]
_load_counter = 0


def _derive_seed(*parts) -> int:  # identical to sandbox runner
    digest = hashlib.sha256(":".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _seed_rngs(seed: int):
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed % (2 ** 32))
    except Exception:
        pass


def parse_spec(spec: str):
    path, _, q = spec.partition("::")
    params = {}
    if q:
        for kv in q.split(","):
            k, _, v = kv.partition("=")
            try:
                v = float(v) if "." in v or "e" in v else int(v)
            except ValueError:
                pass
            params[k] = v
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    if p.is_dir():
        p = p / "bot.py"
    return p, params


def load_module(spec: str):
    global _load_counter
    path, params = parse_spec(spec)
    _load_counter += 1
    os.environ["BOT_DATA_DIR"] = str(path.parent / "data")
    mspec = importlib.util.spec_from_file_location(f"bot_{_load_counter}", str(path))
    module = importlib.util.module_from_spec(mspec)
    mspec.loader.exec_module(module)
    if params and hasattr(module, "configure"):
        module.configure(params)
    return module


def clean_action(raw):
    if not isinstance(raw, dict) or "action" not in raw:
        raise ValueError("bad return: " + repr(raw)[:200])
    out = {"action": str(raw["action"])}
    if raw.get("amount") is not None:
        try:
            out["amount"] = int(raw["amount"])
        except (TypeError, ValueError):
            out["amount"] = 0
    if "debug" in raw:
        out["debug"] = raw["debug"]
    return out


class InProcSeat(Seat):
    kind = "bot"

    def __init__(self, name, spec, bot_seed, time_limit_ms=2000, time_factor=2.0,
                 capture_debug=True, enforce_time=True):
        super().__init__(name, time_limit_ms)
        self.spec = spec
        self.bot_seed = bot_seed          # same as BOT_SEED env in the sandbox
        self.time_factor = time_factor    # local seconds * factor ~ half-core sandbox
        self.capture_debug = capture_debug
        self.enforce_time = enforce_time
        self.module = None
        self.think = []                   # emulated ms per decision
        self.timeouts = 0
        self.errors = 0
        self.error_list = []

    def start(self):
        _seed_rngs(_derive_seed(self.bot_seed, "load"))
        self.module = load_module(self.spec)

    def warmup(self):
        _seed_rngs(_derive_seed(self.bot_seed, "warmup"))
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.module.decide({"type": "warmup"})
        except Exception as e:
            return {"ok": False, "error": repr(e)}
        return {"ok": True}

    def request_action(self, state):
        state = dict(state)
        state["time_limit_ms"] = self.time_limit_ms
        _seed_rngs(_derive_seed(self.bot_seed, state.get("hand_num"), len(state.get("action_log") or [])))
        buf = io.StringIO()
        t0 = time.perf_counter()
        try:
            with contextlib.redirect_stdout(buf):
                raw = self.module.decide(state)
            ms = (time.perf_counter() - t0) * 1000 * self.time_factor
            reply = clean_action(raw)
        except Exception as e:
            ms = (time.perf_counter() - t0) * 1000 * self.time_factor
            self.errors += 1
            if len(self.error_list) < 20:
                self.error_list.append(repr(e)[:300])
            reply = {"action": "fold", "error": "exception"}
        self.think.append(ms)
        if self.enforce_time and ms > state.get("time_limit_ms", self.time_limit_ms):
            self.timeouts += 1
            reply = {"action": "fold", "error": "timeout"}
        reply["think_ms"] = ms
        if not self.capture_debug:
            reply.pop("debug", None)
        return reply

    def stop(self):
        self.module = None

    def summary(self):
        n = len(self.think)
        return {"decisions": n, "avg_think_ms": sum(self.think) / n if n else 0,
                "max_think_ms": max(self.think) if n else 0, "timeouts": self.timeouts,
                "errors": self.errors, "restarts": 0, "disabled": False}

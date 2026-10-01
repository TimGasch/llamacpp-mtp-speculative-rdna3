"""Shared utilities for the measurement harness (PROTOCOL §5, §8).

Frozen after Phase 1: changes require the tooling-amendment procedure of PROTOCOL §8.
"""
from __future__ import annotations

import hashlib
import http.client
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "bench"
RESULTS = ROOT / "results"

# ------------------------------------------------------------------ models (PROTOCOL §2)
MODELS = {
    "gemma4-e4b": {
        "path": "models/gemma-4-E4B-it-Q8_0.gguf",
        "sha256": "a2232a649523c36bf530f1dc3614eb8c800645c4227390381c8b05d4d6eee05a",
        # model-recommended sampling (GGUF metadata general.sampling.*)
        "sampling": {"temperature": 1.0, "top_k": 64, "top_p": 0.95, "min_p": 0.0},
    },
    "qwen35-9b": {
        "path": "models/Qwen3.5-9B-Q4_K_M.gguf",
        "sha256": "03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8",
        # Qwen3.5 model card, thinking mode, general tasks
        "sampling": {"temperature": 1.0, "top_k": 20, "top_p": 0.95, "min_p": 0.0, "presence_penalty": 1.5},
    },
}

# Server arguments pinned for EVERY engine (single user, full offload, fixed context).
BASE_SERVER_ARGS = ["-ngl", "99", "-c", "40960", "-np", "1"]
N_PREDICT = 256
GREEDY = {"temperature": 0.0, "top_k": 1}


# ------------------------------------------------------------------ integrity
def sha256_file(path: Path, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def manifest_files() -> list[Path]:
    out = []
    for p in sorted(BENCH.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name != "MANIFEST.sha256":
            out.append(p)
    return out


def manifest_check(allow_unfrozen: bool = False) -> dict:
    """Verify bench/MANIFEST.sha256. Returns info dict embedded in every result file."""
    man = BENCH / "MANIFEST.sha256"
    if not man.exists():
        if allow_unfrozen:
            return {"frozen": False, "manifest_sha256": None, "note": "tooling not yet frozen (Phase 1)"}
        raise SystemExit("bench/MANIFEST.sha256 missing: tooling not frozen")
    expected = {}
    for line in man.read_text(encoding="utf-8").splitlines():
        if line.strip():
            h, rel = line.split(None, 1)
            expected[rel.strip()] = h
    actual = {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in manifest_files()}
    if expected != actual:
        diff = sorted(set(expected.items()) ^ set(actual.items()))
        raise SystemExit(f"TOOLING CHECKSUM MISMATCH — measurement aborted: {diff[:6]}")
    return {"frozen": True, "manifest_sha256": sha256_file(man)}


def model_sha_verified(key: str) -> str:
    """Verify the model file hash (cached by size+mtime to avoid rehashing GBs every run)."""
    m = MODELS[key]
    p = ROOT / m["path"]
    st = p.stat()
    cache_p = RESULTS / ".sha_cache.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    k = f'{m["path"]}|{st.st_size}|{st.st_mtime_ns}'
    if cache.get(k) != m["sha256"]:
        h = sha256_file(p)
        if h != m["sha256"]:
            raise SystemExit(f"MODEL HASH MISMATCH for {key}: {h}")
        cache[k] = h
        cache_p.parent.mkdir(parents=True, exist_ok=True)
        cache_p.write_text(json.dumps(cache, indent=1))
    return m["sha256"]


# ------------------------------------------------------------------ holdout guard (PROTOCOL §7)
def split_dir(split: str, phase3_holdout: bool, who: str) -> Path:
    if split == "holdout":
        if not phase3_holdout:
            raise SystemExit("holdout data is sealed until Phase 3 (pass --phase3-holdout)")
        log = RESULTS / "holdout_access.log"
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()}\t{who}\t{' '.join(sys.argv)}\n")
    return ROOT / "eval" / split


# ------------------------------------------------------------------ engines
def load_engine(name: str) -> dict:
    p = ROOT / "configs" / "engines" / f"{name}.json"
    e = json.loads(p.read_text(encoding="utf-8"))
    e["name"] = name
    e["config_sha256"] = sha256_file(p)
    for k in ("server", "qdump", "bench"):
        if e.get(k):
            exe = ROOT / e[k]
            e[k + "_sha256"] = sha256_file(exe) if exe.exists() else None
    bi = ROOT / e.get("buildinfo", "__none__")
    e["buildinfo"] = bi.read_text(encoding="utf-8") if bi.is_file() else None
    return e


def engine_server_args(engine: dict, model_key: str) -> list[str]:
    args = ["-m", str(ROOT / MODELS[model_key]["path"])] + BASE_SERVER_ARGS
    args += engine.get("extra_args", [])
    args += engine.get("model_extra_args", {}).get(model_key, [])
    return args


# ------------------------------------------------------------------ environment snapshot
def _ps(cmd: str) -> str:
    try:
        return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True,
                              text=True, timeout=60).stdout.strip()
    except Exception as e:  # pragma: no cover
        return f"<error {e}>"


def env_snapshot() -> dict:
    gpu_mem = _ps("(Get-Counter '\\GPU Adapter Memory(*)\\Dedicated Usage').CounterSamples | "
                  "ForEach-Object { '{0}={1:N0}MB' -f $_.InstanceName, ($_.CookedValue/1MB) }")
    procs = _ps("Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 "
                "ProcessName,Id,@{n='WS_MB';e={[int]($_.WorkingSet64/1MB)}} | ConvertTo-Json -Compress")
    return {
        "timestamp": datetime.now().isoformat(),
        "host": platform.node(),
        "python": sys.version,
        "gpu_driver": _ps("(Get-CimInstance Win32_VideoController | Select-Object -First 1).DriverVersion"),
        "power_plan": _ps("powercfg /getactivescheme"),
        "gpu_adapter_dedicated_usage": gpu_mem,
        "top_processes": procs,
        "outer_git_commit": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                                           text=True).stdout.strip(),
        "outer_git_dirty": bool(subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                                               capture_output=True, text=True).stdout.strip()),
    }


def process_vram_mb(pid: int) -> float | None:
    out = _ps(f"(Get-Counter '\\GPU Process Memory(pid_{pid}_*)\\Dedicated Usage' -ErrorAction SilentlyContinue)"
              ".CounterSamples | Measure-Object -Property CookedValue -Sum | ForEach-Object { $_.Sum/1MB }")
    try:
        return round(float(out.replace(",", ".")), 1)
    except ValueError:
        return None


# ------------------------------------------------------------------ server control
class Server:
    def __init__(self, engine: dict, model_key: str, port: int, log_path: Path):
        self.engine, self.model_key, self.port, self.log_path = engine, model_key, port, log_path
        self.args = [str(ROOT / engine["server"])] + engine_server_args(engine, model_key) + \
                    ["--host", "127.0.0.1", "--port", str(port)]
        self.proc = None

    def start(self, timeout: float = 600.0) -> dict:
        self.log_f = open(self.log_path, "w", encoding="utf-8", errors="replace")
        t0 = time.perf_counter()
        self.proc = subprocess.Popen(self.args, stdout=self.log_f, stderr=subprocess.STDOUT,
                                     cwd=str(ROOT / Path(self.engine["server"]).parent))
        while time.perf_counter() - t0 < timeout:
            if self.proc.poll() is not None:
                raise RuntimeError(f"server exited with {self.proc.returncode}; see {self.log_path}")
            try:
                st, _ = self.request("GET", "/health")
                if st == 200:
                    break
            except OSError:
                pass
            time.sleep(0.25)
        else:
            raise RuntimeError("server did not become ready")
        load_s = time.perf_counter() - t0
        _, props = self.request("GET", "/props")
        return {"load_seconds": round(load_s, 3), "props": props, "cmdline": self.args, "pid": self.proc.pid}

    def request(self, method: str, path: str, body: dict | None = None, timeout: float = 600.0):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        c.request(method, path, body=json.dumps(body) if body is not None else None,
                  headers={"Content-Type": "application/json"})
        r = c.getresponse()
        data = r.read()
        c.close()
        try:
            return r.status, json.loads(data)
        except json.JSONDecodeError:
            return r.status, data.decode("utf-8", "replace")

    def stream_completion(self, body: dict, timeout: float = 900.0) -> dict:
        """POST /completion with stream=true; timestamps every SSE event on arrival."""
        body = dict(body, stream=True)
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=timeout)
        payload = json.dumps(body)
        t_send = time.perf_counter_ns()
        c.request("POST", "/completion", body=payload, headers={"Content-Type": "application/json"})
        r = c.getresponse()
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}: {r.read()[:500]!r}")
        events, tokens, probs, final = [], [], [], None
        while True:
            line = r.readline()
            if not line:
                break
            t = time.perf_counter_ns()
            line = line.strip()
            if not line.startswith(b"data: "):
                continue
            obj = json.loads(line[6:])
            toks = obj.get("tokens") or []
            if toks:
                events.append([t - t_send, len(toks)])
                tokens.extend(toks)
            if obj.get("completion_probabilities"):
                probs.extend(obj["completion_probabilities"])
            if obj.get("stop"):
                final = obj
                break
        c.close()
        return {"t_send_ns": t_send, "events": events, "tokens": tokens, "probs": probs,
                "final": {k: final.get(k) for k in ("timings", "tokens_predicted", "tokens_evaluated",
                                                     "stop_type", "stopping_word", "truncated")} if final else None}

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if getattr(self, "log_f", None):
            self.log_f.close()


def derive_request_metrics(rec: dict) -> dict:
    """Primary speed metrics of one request (PROTOCOL §5.2)."""
    ev = rec["events"]
    n_gen = sum(n for _, n in ev)
    out = {"n_gen": n_gen, "ttft_ms": None, "tg_tps": None, "gen_time_s": None, "tg_tokens": None}
    if ev:
        out["ttft_ms"] = ev[0][0] / 1e6
        if len(ev) > 1:
            dt = (ev[-1][0] - ev[0][0]) / 1e9
            ntok = n_gen - ev[0][1]
            out.update(gen_time_s=dt, tg_tokens=ntok, tg_tps=ntok / dt if dt > 0 else None)
    t = (rec.get("final") or {}).get("timings") or {}
    out["pp_tps_engine"] = t.get("prompt_per_second")
    out["tg_tps_engine"] = t.get("predicted_per_second")
    out["n_prompt_engine"] = t.get("prompt_n")
    out["draft_n"] = t.get("draft_n")
    out["draft_n_accepted"] = t.get("draft_n_accepted")
    return out


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def new_session_dir(tag: str) -> Path:
    sid = datetime.now().strftime("%Y%m%d-%H%M%S") + "_" + tag
    d = RESULTS / "raw" / sid
    d.mkdir(parents=True, exist_ok=False)
    return d

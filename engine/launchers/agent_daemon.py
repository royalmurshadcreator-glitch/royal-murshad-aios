"""Background agent daemon - processes file-based and work_queue jobs."""
import sys, json, time, urllib.request, subprocess
from pathlib import Path
from datetime import datetime, timezone

WS = Path(r"D:\01_PROJECTS\AIOS\12_WORKSPACE")
AGENTS = WS / "agents"
LOG_DIR = WS / "LOG"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUNS_LOG = LOG_DIR / "runs.jsonl"
OLLAMA = "http://127.0.0.1:11434/api/generate"
DISPATCHER = r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_leads\aios_agent_dispatcher.py"

def log_run(entry):
    with open(RUNS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def process_file_agents():
    """Watch 12_WORKSPACE/agents/*/IN and process each .txt file via Ollama."""
    if not AGENTS.exists():
        return
    for agent_dir in AGENTS.iterdir():
        if not agent_dir.is_dir():
            continue
        cfg_path = agent_dir / "config.json"
        if not cfg_path.exists():
            continue
        inbox = agent_dir / "IN"
        outbox = agent_dir / "OUT"
        if not inbox.exists():
            continue
        outbox.mkdir(exist_ok=True)
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        model = cfg.get("model", "qwen2.5:3b")
        ext = cfg.get("output_extension", ".md")
        for infile in list(inbox.iterdir()):
            if not infile.is_file() or not infile.name.endswith(".txt"):
                continue
            stem = infile.stem
            outfile = outbox / (stem + ext)
            if outfile.exists():
                continue
            text = infile.read_text(encoding="utf-8", errors="replace")
            start = time.time()
            try:
                body = json.dumps({
                    "model": model,
                    "prompt": text,
                    "stream": False,
                    "options": {"num_predict": 400}
                }).encode()
                req = urllib.request.Request(OLLAMA, data=body, method="POST")
                req.add_header("Content-Type", "application/json")
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                output = data.get("response", "").strip() or "(empty)"
                outfile.write_text(output, encoding="utf-8")
                ms = int((time.time() - start) * 1000)
                log_run({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "agent": agent_dir.name,
                    "input": infile.name,
                    "output": outfile.name,
                    "ok": True,
                    "ms": ms,
                })
                print(f"[daemon] Processed {agent_dir.name}/{infile.name} -> {outfile.name}", flush=True)
            except Exception as e:
                log_run({
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "agent": agent_dir.name,
                    "input": infile.name,
                    "ok": False,
                    "error": str(e),
                })
                print(f"[daemon] FAILED {agent_dir.name}/{infile.name}: {e}", flush=True)

def process_work_queue():
    """Run the work_queue dispatcher once per cycle."""
    try:
        subprocess.run(
            [sys.executable, DISPATCHER],
            capture_output=True, timeout=60,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
    except Exception:
        pass

def main():
    print("[daemon] Agent daemon started", flush=True)
    while True:
        try:
            process_file_agents()
        except Exception as e:
            print(f"[daemon] file_agents error: {e}", flush=True)
        try:
            process_work_queue()
        except Exception as e:
            print(f"[daemon] work_queue error: {e}", flush=True)
        time.sleep(6)

if __name__ == "__main__":
    main()

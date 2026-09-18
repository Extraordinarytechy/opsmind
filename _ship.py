import subprocess, os, glob, sys

REPO = "/mnt/h/JobThisMonth/opsmind"
os.chdir(REPO)
log = []

def run(args, check=False):
    r = subprocess.run(args, cwd=REPO, capture_output=True, text=True, timeout=180)
    log.append(f"$ {' '.join(args)}\n  rc={r.returncode}")
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    if out:
        log.append("  " + out.replace("\n", "\n  "))
    if check and r.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}")
    return r.returncode, out

# 1) tests must pass
rc, _ = run(["python3", "-m", "unittest", "discover", "-s", "tests"])
tests_ok = rc == 0

# 2) YAML parse
yaml_ok = True
try:
    import yaml
    for f in glob.glob("deploy/**/*.yaml", recursive=True) + glob.glob(".github/**/*.yml", recursive=True):
        try:
            list(yaml.safe_load_all(open(f, encoding="utf-8")))
        except Exception as e:
            log.append(f"INVALID YAML {f}: {e}"); yaml_ok = False
except ImportError:
    log.append("pyyaml not available; skipping yaml parse")

log.append(f"\nTESTS_OK={tests_ok} YAML_OK={yaml_ok}")

if not (tests_ok and yaml_ok):
    log.append("ABORT: validation failed, not pushing")
    open(f"{REPO}/_ship_out.txt", "w").write("\n".join(log)); print("done"); sys.exit(0)

# 3) git init + staged commits
if not os.path.isdir(os.path.join(REPO, ".git")):
    run(["git", "init", "-b", "main"], check=True)
run(["git", "config", "user.name", "Ajay Kumar"])
run(["git", "config", "user.email", "ajaykumarsatyam10@gmail.com"])

def commit(paths, msg):
    run(["git", "add"] + paths)
    run(["git", "commit", "-m", msg])

commit([".gitignore", "LICENSE", "README.md", "requirements.txt", "Makefile"],
       "chore: project scaffold, docs and license")
commit(["opsmind", "tests", "examples"],
       "feat: diagnosis engine with pluggable providers and strict contract validation")
commit(["deploy"],
       "feat: kind deploy, sample FastAPI workload, SLO rules and manifests")
commit(["scripts"], "feat: failure-injection script for the demo loop")
commit([".github"], "ci: offline unit tests and yaml manifest validation")
run(["git", "add", "-A"]); run(["git", "commit", "-m", "chore: remaining files"])

# 4) create remote repo and push
desc = ("OpsMind: an AI-assisted incident-response and gated self-healing agent for "
        "Kubernetes (SLO alerting -> evidence-grounded LLM diagnosis -> gated remediation).")
rc, out = run(["gh", "repo", "create", "Extraordinarytechy/opsmind", "--public",
               "--source", ".", "--remote", "origin", "--push", "--description", desc])

# 5) topics
run(["gh", "repo", "edit", "Extraordinarytechy/opsmind",
     "--add-topic", "kubernetes", "--add-topic", "sre", "--add-topic", "aiops",
     "--add-topic", "prometheus", "--add-topic", "incident-response",
     "--add-topic", "python", "--add-topic", "bedrock", "--add-topic", "observability",
     "--add-topic", "devops", "--add-topic", "gitops"])

# 6) verify remote
run(["git", "remote", "-v"])
run(["git", "log", "--oneline"])

open(f"{REPO}/_ship_out.txt", "w").write("\n".join(log))
print("done")

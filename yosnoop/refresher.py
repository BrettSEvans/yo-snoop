import json, subprocess, time
from dataclasses import dataclass, field
from pathlib import Path
from yosnoop.gate import scan, redact

REPOMIX = "repomix@1.18.1"
# Orientation only (~104k tokens on 2026-10-16); code is reached through Serena and file reads
INCLUDE = "*.md,docs/product/01-pm-brief.md,docs/product/04-architecture.md,docs/features/*/01-feature-brief.md"
IGNORE = "**/__tests__/**,**/*.test.*,CHANGELOG.md,821smash.md"


def run_gh(args: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True, cwd=cwd).stdout


def run_repomix(clone: Path, out: Path) -> None:
    subprocess.run(["npx", "-y", REPOMIX, "--compress", "--style", "xml", "--include", INCLUDE, "--ignore", IGNORE,
                    "--output", str(out), str(clone)], check=True, capture_output=True)


def _git(clone: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True, check=True).stdout


def git_facts(clone: Path) -> str:
    branches = _git(clone, "for-each-ref", "--sort=-committerdate", "refs/remotes/origin",
                    "--format=%(refname:short)\t%(committerdate:iso)\t%(subject)")
    log = _git(clone, "log", "--all", "-n", "300", "--date=iso", "--name-only",
               "--format=--- %h %ad %an%n%s")
    return "# Branches (newest first)\n" + branches + "\n# Recent commits, all branches\n" + log


@dataclass
class RefreshReport:
    ok: bool
    clone_age_s: float
    map_blocked: bool = False
    errors: list[str] = field(default_factory=list)


class Refresher:
    def __init__(self, origin: str, knowledge: Path, gh=None, repomix=run_repomix, now=time.time):
        self.origin, self.k, self.repomix, self.now = origin, Path(knowledge), repomix, now
        self.gh = gh or (lambda args: run_gh(args, cwd=self.k / "agent-c"))

    def refresh(self) -> RefreshReport:
        self.k.mkdir(parents=True, exist_ok=True)
        clone, errors = self.k / "agent-c", []
        try:
            if (clone / ".git").exists():
                subprocess.run(["git", "-C", str(clone), "fetch", "-q", "--prune", "origin",
                                "+refs/heads/*:refs/remotes/origin/*"], check=True)
                subprocess.run(["git", "-C", str(clone), "reset", "-q", "--hard", "origin/main"], check=True)
            else:
                subprocess.run(["git", "clone", "-q", self.origin, str(clone)], check=True)
            (self.k / "git-facts.txt").write_text(redact(git_facts(clone)))
            (self.k / "refreshed-at").write_text(str(self.now()))
        except subprocess.CalledProcessError as e:
            errors.append(f"git: {e}")
        try:
            status = {"pull_requests": json.loads(self.gh(["pr", "list", "--state", "all", "--limit", "30", "--json",
                                                           "number,title,state,author,mergedAt,reviewDecision,headRefName"])),
                      "runs": json.loads(self.gh(["run", "list", "--limit", "30", "--json",
                                                  "headBranch,conclusion,status,createdAt,workflowName"]))}
            (self.k / "pr-ci-status.json").write_text(redact(json.dumps(status, indent=1)))
        except Exception as e:
            errors.append(f"gh: {type(e).__name__}")
        blocked, map_path = False, self.k / "repo-map.xml"
        try:
            self.repomix(clone, map_path)
            if scan(map_path.read_text()):
                map_path.unlink(); blocked = True
        except Exception as e:
            errors.append(f"repomix: {type(e).__name__}")
        f = self.k / "refreshed-at"
        age = self.now() - float(f.read_text()) if f.exists() else float("inf")
        return RefreshReport(ok=not errors, clone_age_s=age, map_blocked=blocked, errors=errors)

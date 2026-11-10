#!/usr/bin/env python3
"""Documentation consistency checks. Standard library only; no cluster needed.

Verifies that docs, hints, solutions, tasks and the verifier agree with each other.
Exit 0 if every check passes, 1 otherwise.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.dont_write_bytecode = True
import verify  # noqa: E402

SCENARIOS = ["baseline", "variation-a", "variation-b"]
TOP_DIRS = (
    "scripts",
    "tests",
    "tasks",
    "hints",
    "solutions",
    "lab",
    "worksheets",
    "takeaway",
    "presenter",
    "docs",
    "FAQ",
)
# Vocabulary that would reveal how to solve a task. Must not appear in task briefs.
SPOILER_TERMS = [
    "targetport",
    "target-port",
    "selector",
    "readinessprobe",
    "kubectl expose",
    "kubectl scale",
    "kubectl set",
    "kubectl patch",
    "8080",
    "/healthz",
    "/ready",
    "readiness",
]

failures = []
passes = 0


def check(ok, message):
    global passes
    if ok:
        passes += 1
    else:
        failures.append(message)
        print(f"FAIL: {message}")


def kit_markdown():
    for path in sorted(ROOT.rglob("*.md")):
        rel = path.relative_to(ROOT)
        if any(part.startswith(".") for part in rel.parts):
            continue
        yield path


def fenced_blocks(text):
    """Yield (info_string, body) for each fenced code block."""
    for match in re.finditer(r"^```([^\n]*)\n(.*?)^```$", text, re.S | re.M):
        yield match.group(1).strip(), match.group(2)


def strip_fences(text):
    return re.sub(r"^```[^\n]*\n.*?^```$", "", text, flags=re.S | re.M)


def looks_like_path(token):
    if any(c in token for c in "<>*$…{}|"):
        return False
    return token.split("/")[0] in TOP_DIRS and "/" in token


def clean_token(token):
    return token.strip("`'\"()[],;:.")


# 1. Relative markdown links resolve.
for md in kit_markdown():
    text = md.read_text()
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"^(https?:|mailto:|#)", target):
            continue
        path = target.split("#")[0]
        if not path:
            continue
        resolved = (md.parent / path).resolve()
        check(resolved.exists(), f"{md.relative_to(ROOT)}: broken link -> {target}")

# 2. Paths referenced in code blocks and inline code exist.
for md in kit_markdown():
    text = md.read_text()
    tokens = []
    for info, body in fenced_blocks(text):
        if info.split(" ")[0] in ("bash", "sh", "text", ""):
            for line in body.splitlines():
                if line.lstrip().startswith("#"):
                    continue
                tokens.extend(line.split())
    tokens.extend(re.findall(r"`([^`\n]+)`", strip_fences(text)))
    seen = set()
    for raw in tokens:
        for piece in raw.split():
            token = clean_token(piece)
            if token in seen or not looks_like_path(token):
                continue
            seen.add(token)
            check(
                (ROOT / token).exists(),
                f"{md.relative_to(ROOT)}: referenced path does not exist: {token}",
            )

# 3. Task acceptance criteria match the verifier exactly (ids and text).
for scenario in SCENARIOS:
    task = (ROOT / "tasks" / f"{scenario}.md").read_text()
    documented = re.findall(r"^- \*\*(AC\d+)\*\* — (.+)$", task, re.M)
    expected = [(c.id, c.title) for c in verify.SCENARIOS[scenario]]
    check(
        documented == expected,
        f"tasks/{scenario}.md criteria differ from scripts/lib/verify.py\n"
        f"      task    : {documented}\n      verifier: {expected}",
    )

# 4. Every scenario has 3 hint levels, a solution with a runnable block, and no
#    solution commands in hints.
for scenario in SCENARIOS:
    for level in (1, 2, 3):
        hint = ROOT / "hints" / scenario / f"level-{level}.md"
        check(hint.is_file() and hint.stat().st_size > 100, f"missing/empty {hint.relative_to(ROOT)}")
        if hint.is_file():
            check("```bash solution" not in hint.read_text(), f"{hint.relative_to(ROOT)} contains a solution block")
    solution = ROOT / "solutions" / f"{scenario}.md"
    blocks = [b for i, b in fenced_blocks(solution.read_text()) if i == "bash solution"]
    check(len(blocks) == 1, f"solutions/{scenario}.md needs exactly one `bash solution` block")
    check(
        f"drill-{scenario}" in (blocks[0] if blocks else ""),
        f"solutions/{scenario}.md solution block does not target drill-{scenario}",
    )

# 5. Task briefs contain no solution vocabulary.
for scenario in SCENARIOS:
    task = (ROOT / "tasks" / f"{scenario}.md").read_text().lower()
    for term in SPOILER_TERMS:
        check(term not in task, f"tasks/{scenario}.md leaks solution vocabulary: '{term}'")

# 6. Runbook demo blocks exist and target the baseline namespace.
runbook = (ROOT / "presenter" / "runbook.md").read_text()
for tag in ("demo-mistake", "demo-recover"):
    blocks = [b for i, b in fenced_blocks(runbook) if i == f"bash {tag}"]
    check(len(blocks) == 1, f"presenter/runbook.md needs exactly one `bash {tag}` block")
    check("drill-baseline" in (blocks[0] if blocks else ""), f"runbook {tag} block must target drill-baseline")

# 7. Takeaway Markdown and HTML agree on the workflow and placeholders.
tmd = (ROOT / "takeaway" / "one-page.md").read_text()
thtml = (ROOT / "takeaway" / "one-page.html").read_text()
for word in ("Read", "Orient", "Solve", "Verify", "Review"):
    check(word in tmd and word in thtml, f"takeaway missing step '{word}' in md or html")
for phrase in ("not proof", "timer", "next practice action"):
    check(phrase in tmd.lower() and phrase in thtml.lower(), f"takeaway missing reminder: {phrase}")
REPO_URL = "https://github.com/kubeskills/cka-under-pressure"
QR_PNG = "qr-code-for-cka-under-pressure-talk-kubecon-na-2026.png"
check(
    "PLACEHOLDER" not in tmd and "PLACEHOLDER" not in thtml,
    "takeaway still has a PLACEHOLDER; replace it before printing",
)
check(
    QR_PNG in tmd and QR_PNG in thtml,
    "takeaway must reference the QR code image in both md and html",
)
check((ROOT / "takeaway" / QR_PNG).is_file(), f"takeaway/{QR_PNG} is missing")
check(
    REPO_URL in tmd and REPO_URL in thtml,
    "takeaway must show the repo URL in both md and html",
)
found_urls = set(re.findall(r"https?://[^\s)`<\"']+", tmd + thtml))
check(
    found_urls <= {REPO_URL},
    f"takeaway must not contain URLs other than the repo URL: {sorted(found_urls - {REPO_URL})}",
)

# 8. No unpinned/latest images anywhere in the kit.
for path in list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.sh")) + list(ROOT.rglob("*.py")) + list(kit_markdown()):
    if path == Path(__file__).resolve():
        continue
    if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
        continue
    text = path.read_text()
    check(not re.search(r"image:\s*\S+:latest\b|--image=\S+:latest\b", text), f"{path.relative_to(ROOT)} uses a :latest image")

# 8b. The images the README names are the ones the manifests actually pin.
readme_text = (ROOT / "README.md").read_text()
app_image = verify.read_app_image()
check(app_image in readme_text, f"README must name the app image {app_image}")
node_match = re.search(
    r"image:\s*(kindest/node:[^@\s]+)", (ROOT / "lab" / "kind-cluster.yaml").read_text()
)
check(node_match is not None, "lab/kind-cluster.yaml must pin a kindest/node image")
if node_match:
    node_image = node_match.group(1)
    check(node_image in readme_text, f"README must name the node image {node_image}")

# 9. No exam facts asserted without verification (the kit makes none).
risky = re.compile(r"passing score|domain weight|\d+\s*%\s+of the exam|exam (duration|length|format)|guarantees? (a )?pass", re.I)
negation = re.compile(r"(does not|not|no)\s+guarantee|nothing says", re.I)
# The FAQ is the one place exam facts are allowed, and only in a section that cites an
# official Linux Foundation page with the date it was checked.
verified_source = re.compile(
    r"Sources?\s*\(checked \d{4}-\d{2}-\d{2}\):.*https://(training|docs)\.linuxfoundation\.org/"
)


def verified_sections(lines):
    """Return the set of 0-based line indexes inside a section citing a source."""
    starts = [i for i, ln in enumerate(lines) if ln.startswith("#")] + [len(lines)]
    ok = set()
    for begin, end in zip(starts, starts[1:]):
        if any(verified_source.search(ln) for ln in lines[begin:end]):
            ok.update(range(begin, end))
    return ok


for md in kit_markdown():
    lines = md.read_text().splitlines()
    sourced = verified_sections(lines) if md.parent == ROOT / "FAQ" else set()
    for index, line in enumerate(lines):
        if risky.search(line) and not negation.search(line) and index not in sourced:
            check(
                False,
                f"{md.relative_to(ROOT)}:{index + 1} may assert an unverified exam fact: "
                f"{line.strip()[:80]}",
            )

# 10. Scripts are executable.
for path in sorted((ROOT / "scripts").glob("*.sh")) + sorted((ROOT / "tests").glob("*.sh")):
    check(os.access(path, os.X_OK), f"{path.relative_to(ROOT)} is not executable")

print(f"docs checks: {passes} passed, {len(failures)} failed")
sys.exit(1 if failures else 0)

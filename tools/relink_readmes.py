#!/usr/bin/env python3
"""
relink_readmes.py — move README links from the retired RosterizerTestData
org to RosterizerData.

Every repo in the data org is read through the GitHub CLI (`gh api`), so
the CLI's login does the work and needs write access to the org's repos
for `--apply`. A README naming the retired org is rewritten with one
commit per repo: the org name is swapped and nothing else. Links mangled
on purpose as dev notes stay mangled, only pointed at the new org.

Report (the default): each retired-org link, and whether its rewritten
target exists.

    python3 tools/relink_readmes.py

Apply:

    python3 tools/relink_readmes.py --apply
"""

import argparse
import base64
import json
import re
import subprocess
import urllib.error
import urllib.request

ORG = "RosterizerData"
OLD = "RosterizerTestData"
MESSAGE = "docs: rulebook links follow the data org\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
LINK = re.compile(r"https?://[^\s)\"'<>]*" + OLD + r"[^\s)\"'<>]*")


def gh(*args, body=None):
    """Call `gh api` and parse its JSON answer; a failure raises with gh's own words."""
    run = subprocess.run(["gh", "api", *args], input=body, capture_output=True, text=True)
    if run.returncode != 0:
        raise RuntimeError(run.stderr.strip() or run.stdout.strip() or f"gh api {' '.join(args)} failed")
    return json.loads(run.stdout)


def readme(repo):
    """The repo's README (content, sha, path), or None when it has none."""
    try:
        return gh(f"repos/{ORG}/{repo}/readme")
    except RuntimeError:
        return None


def status_of(url):
    """The HTTP status a HEAD request gets, or ERR when the host cannot be reached."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20) as answer:
            return answer.status
    except urllib.error.HTTPError as error:
        return error.code
    except urllib.error.URLError:
        return "ERR"


def main():
    parser = argparse.ArgumentParser(description="Move README links from the retired org to the data org.")
    parser.add_argument("--apply", action="store_true", help="write one commit per README; without it, report only")
    args = parser.parse_args()

    repos = sorted(repo["name"] for repo in gh(f"orgs/{ORG}/repos?per_page=100"))
    changed = 0
    for repo in repos:
        file = readme(repo)
        if file is None:
            print(f"{repo}: no README")
            continue
        text = base64.b64decode(file["content"]).decode("utf-8")
        mentions = text.count(OLD)
        if not mentions:
            continue
        if not args.apply:
            print(f"{repo}: {mentions} mention(s)")
            for link in sorted(set(LINK.findall(text))):
                target = link.replace(OLD, ORG)
                print(f"  {link}\n    -> {target}  [{status_of(target)}]")
            continue
        body = json.dumps({
            "message": MESSAGE,
            "content": base64.b64encode(text.replace(OLD, ORG).encode("utf-8")).decode("ascii"),
            "sha": file["sha"],
        })
        out = gh("-X", "PUT", f"repos/{ORG}/{repo}/contents/{file['path']}", "--input", "-", body=body)
        sha = ((out.get("commit") or {}).get("sha") or "")[:7] or "no commit?"
        print(f"{repo}: {sha} ({mentions} mention(s))")
        changed += 1

    if args.apply:
        print(f"{len(repos)} repos scanned; {changed} READMEs updated")
    else:
        print(f"{len(repos)} repos scanned; run with --apply to write the commits")


if __name__ == "__main__":
    main()

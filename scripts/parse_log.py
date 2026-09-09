#!/usr/bin/env python3
"""Extract a host fingerprint from an ALPS install log written by LOGGING.md.

Reads the script(1) transcript, finds the Step 1 probe output, and emits JSON
describing the environment plus the CI target that best reproduces it.

Usage: parse_log.py logs/incoming/run.log > fingerprint.json
"""
import json, re, sys

# probe lines are: two spaces, %-24s label, value
PROBE = re.compile(r"^  (\S[^ ]*(?: \S+)*?)\s{2,}(.+?)\s*$")

DOCKER = {
    ("Ubuntu", "24.04"): "ubuntu:24.04",
    ("Ubuntu", "22.04"): "ubuntu:22.04",
    ("Ubuntu", "20.04"): "ubuntu:20.04",
    ("Debian", "12"):    "debian:12",
    ("Rocky Linux", "9"): "rockylinux:9",
    ("Rocky Linux", "8"): "rockylinux:8",
    ("AlmaLinux", "9"):  "almalinux:9",
    ("AlmaLinux", "8"):  "almalinux:8",
}
MACOS_RUNNER = {"15": "macos-15", "14": "macos-14", "26": "macos-26"}


def parse(text):
    text = text.replace("\r", "")
    f = {"probe_found": False, "fields": {}}

    # keep only the probe block so unrelated build output can't match PROBE
    start = text.find("== SYSTEM ==")
    if start == -1:
        return f
    end = text.find("Script done", start)
    block = text[start: end if end != -1 else len(text)]
    f["probe_found"] = True
    f["probe_text"] = block.strip()

    for line in block.splitlines():
        m = PROBE.match(line)
        if m:
            f["fields"].setdefault(m.group(1).strip(), m.group(2).strip())
    v = f["fields"]

    uname = v.get("uname", "")
    f["kernel"] = uname.split()[0] if uname else None
    f["arch"] = uname.split()[1] if len(uname.split()) > 1 else None

    distro = v.get("distro", "")
    if distro:
        parts = distro.rsplit(" ", 1)
        f["distro_name"] = parts[0]
        f["distro_version"] = parts[1] if len(parts) > 1 else None
    f["macos_version"] = v.get("macOS")

    def first_num(s):
        m = re.search(r"\d+(?:\.\d+)*", s or "")
        return m.group(0) if m else None

    f["gcc"] = first_num(v.get("system gcc", ""))
    f["clang"] = first_num(v.get("clang", ""))
    f["cmake"] = first_num(v.get("cmake", ""))
    f["hdf5"] = first_num(v.get("hdf5", ""))
    f["conda_active"] = not v.get("CONDA_PREFIX", "none").startswith("none")

    for k in ("python3.12", "python3.11", "python3"):
        if k in v:
            f["python"] = first_num(v[k])
            break
    else:
        f["python"] = None

    # CI target
    if f["kernel"] == "Darwin":
        major = (f["macos_version"] or "").split(".")[0]
        f["runs_on"] = MACOS_RUNNER.get(major, "macos-latest")
        f["container"] = None
        f["exact"] = major in MACOS_RUNNER
    else:
        key = (f.get("distro_name"), f.get("distro_version"))
        img = DOCKER.get(key)
        if img is None and f.get("distro_version"):
            key = (f.get("distro_name"), f["distro_version"].split(".")[0])
            img = DOCKER.get(key)
        f["runs_on"] = "ubuntu-latest"
        f["container"] = img
        f["exact"] = img is not None

    # failing commands, for the reviewer
    fails = []
    for m in re.finditer(
        r'Script started[^\n]*COMMAND="(.*?)"[^\n]*\n(.*?)\nScript done[^\n]*'
        r'COMMAND_EXIT_CODE="(\d+)"',
        text, re.S):
        if m.group(3) != "0":
            fails.append({"cmd": m.group(1),
                          "exit": int(m.group(3)),
                          "tail": m.group(2).strip()[-1500:]})
    f["failures"] = fails
    f["failure_count"] = len(fails)
    return f


if __name__ == "__main__":
    with open(sys.argv[1], errors="replace") as fh:
        print(json.dumps(parse(fh.read()), indent=2))

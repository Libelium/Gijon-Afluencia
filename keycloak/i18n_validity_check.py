import os
import re
import argparse
from collections import OrderedDict

# --- Configuration ---
# Theme root: every "messages/" folder under it holds messages_<locale>.properties bundles
# (e.g. pidtheme/login/messages, pidtheme/email/messages).
THEME_DIR = "./pidtheme"
# Locales every bundle must provide. 'en' is the reference (source of keys).
EXPECTED_LOCALES = ["en", "es", "ca", "el", "pt"]
REFERENCE_LOCALE = "en"
OUTPUT_FILE = "missing_keys_report.txt"

LINE_RE = re.compile(r"^\s*([^#!=:\s][^=:]*?)\s*[=:](.*)$")
FILE_RE = re.compile(r"^messages_([a-zA-Z][a-zA-Z0-9_-]*)\.properties$")


def parse_properties(path):
    """Return an OrderedDict {key: value} for a .properties file (ignores comments/blanks)."""
    keys = OrderedDict()
    with open(path, encoding="utf-8") as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("!"):
                continue
            m = LINE_RE.match(raw.rstrip("\n"))
            if m:
                keys[m.group(1).strip()] = m.group(2)
    return keys


def find_message_dirs(theme_dir):
    dirs = []
    for root, _, files in os.walk(theme_dir):
        if os.path.basename(root) == "messages" and any(FILE_RE.match(f) for f in files):
            dirs.append(root)
    return sorted(dirs)


def load_bundles(msg_dir):
    bundles = {}
    for fn in os.listdir(msg_dir):
        m = FILE_RE.match(fn)
        if m:
            bundles[m.group(1)] = parse_properties(os.path.join(msg_dir, fn))
    return bundles


def check_dir(msg_dir, fill_missing=False):
    bundles = load_bundles(msg_dir)
    ref_keys = list(bundles.get(REFERENCE_LOCALE, {}).keys())
    # union of all keys (so extra keys in non-en bundles also surface)
    all_keys = OrderedDict((k, True) for k in ref_keys)
    for b in bundles.values():
        for k in b:
            all_keys.setdefault(k, True)
    all_keys = list(all_keys.keys())

    # rows = keys missing in at least one EXPECTED locale
    rows = []
    for key in all_keys:
        present = {loc: (key in bundles.get(loc, {})) for loc in EXPECTED_LOCALES}
        if not all(present.values()):
            rows.append((key, present))

    if fill_missing:
        for loc in EXPECTED_LOCALES:
            path = os.path.join(msg_dir, f"messages_{loc}.properties")
            present = bundles.get(loc, {})
            missing = [k for k in all_keys if k not in present]
            if missing:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"\n# === MISSING (auto-added placeholders) ===\n")
                    for k in missing:
                        f.write(f"{k}=❌\n")
                print(f"  [{loc}] filled {len(missing)} missing key(s) in {os.path.basename(path)}")

    return bundles, all_keys, rows


def main(fill_missing=False):
    msg_dirs = find_message_dirs(THEME_DIR)
    if not msg_dirs:
        print(f"No messages/ folders with bundles found under {THEME_DIR}")
        return

    report_lines = []
    total_missing = 0

    for msg_dir in msg_dirs:
        rel = os.path.relpath(msg_dir, THEME_DIR)
        bundles, all_keys, rows = check_dir(msg_dir, fill_missing)
        present_locales = sorted(bundles.keys())
        missing_locales = [l for l in EXPECTED_LOCALES if l not in bundles]

        header = f"### {rel}  ({len(all_keys)} keys; bundles: {', '.join(present_locales) or 'none'})"
        report_lines.append(header)
        print(header)
        if missing_locales:
            msg = f"  MISSING BUNDLE(S): {', '.join(missing_locales)}"
            report_lines.append(msg)
            print(msg)

        if not rows:
            ok = "  OK — every key present in all expected locales."
            report_lines.append(ok)
            print(ok)
        else:
            # comparison table: Key | en es ca el pt
            cols = ["Key"] + EXPECTED_LOCALES
            table = [cols, ["-" * len(c) for c in cols]]
            for key, present in rows:
                table.append([key] + ["OK" if present[l] else "MISSING" for l in EXPECTED_LOCALES])
            widths = [max(len(str(r[i])) for r in table) for i in range(len(cols))]
            for r in table:
                line = "  " + " | ".join(str(r[i]).ljust(widths[i]) for i in range(len(cols)))
                report_lines.append(line)
                print(line)
            total_missing += len(rows)

        report_lines.append("")
        print("")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(f"Report saved to '{OUTPUT_FILE}'. Total keys missing in >=1 locale: {total_missing}")
    return total_missing


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check that every Keycloak theme message bundle (per messages/ folder) "
                    "has all keys in all expected locales (es,en,ca,el,pt)."
    )
    parser.add_argument(
        "--fill-missing",
        action="store_true",
        help="Append missing keys with a '❌' placeholder to each locale bundle.",
    )
    args = parser.parse_args()
    missing = main(fill_missing=args.fill_missing)
    raise SystemExit(1 if missing else 0)

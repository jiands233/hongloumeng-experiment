"""Read-only audit of the supplied LaTeX corpus; no network or source edits.

Run from any directory with Python 3. Outputs go beside this script.
The normalized comparison is mechanical, not a critical edition.
"""
from pathlib import Path
import collections
import difflib
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1] / "Dream-of-Red-Chamber-master"
EDITIONS = ("紅樓夢庚辰本", "脂硯齋重評石頭記")


def remove_braced_command(text, command):
    pattern = re.compile(r"\\" + command + r"(?:\[[^\]]*\])?\{")
    while match := pattern.search(text):
        pos, depth = match.end(), 1
        while pos < len(text) and depth:
            if text[pos] == "{" and text[pos - 1] != "\\":
                depth += 1
            elif text[pos] == "}" and text[pos - 1] != "\\":
                depth -= 1
            pos += 1
        if depth:
            raise ValueError(f"Unbalanced command {command}")
        text = text[:match.start()] + text[pos:]
    return text


def normalize(text):
    for command in ("footnote", "footnotetext"):
        text = remove_braced_command(text, command)
    text = re.sub(r"\\footnotemark(?:\[[^\]]*\])?", "", text)
    text = re.sub(r"〈[^〉]*〉", "", text)
    # Optional chapter title repeats the mandatory title; remove only that option.
    text = re.sub(r"\\chapter\[[^\]]*\]", r"\\chapter", text)
    return re.sub(r"\s+", "", text)


def main():
    rows, corpus, inventories = [], {}, {}
    for edition in EDITIONS:
        directory = ROOT / edition / "chapters"
        paths = sorted(directory.glob("chapter*.tex"))
        inventories[edition] = {
            "chapter_files": len(paths),
            "missing_numbers": [n for n in range(1, 81) if not (directory / f"chapter{n:02d}.tex").is_file()],
            "main_inputs": re.findall(r"\\input\{chapters/chapter(\d+)\}", (ROOT / edition / "main.tex").read_text()),
        }
        for path in paths:
            data = path.read_bytes()
            text = data.decode("utf-8", errors="strict")
            n = int(path.stem.removeprefix("chapter"))
            corpus[edition, n] = text
            rows.append({
                "path": str(path.relative_to(ROOT.parent)), "chapter": n,
                "edition": edition, "bytes": len(data), "unicode_characters": len(text),
                "lines": len(text.splitlines()), "sha256": hashlib.sha256(data).hexdigest(),
                "chapter_commands": len(re.findall(r"\\chapter(?:\[|\{)", text)),
                "note_commands": len(re.findall(r"\\footnote(?:text)?\{", text)),
                "replacement_characters": text.count("\ufffd"), "square_placeholders": text.count("□"),
                "begin_end_balanced_counts": collections.Counter(re.findall(r"\\begin\{([^}]+)\}", text)) == collections.Counter(re.findall(r"\\end\{([^}]+)\}", text)),
            })
    differences = []
    for n in range(1, 81):
        a, b = [normalize(corpus[e, n]) for e in EDITIONS]
        if a != b:
            changes = []
            for op, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
                if op != "equal":
                    changes.append({"operation": op, "plain": a[i:j][:180], "annotated": b[k:l][:180], "plain_length": j-i, "annotated_length": l-k})
            differences.append({"chapter": n, "changes": changes})
    duplicate_checks = []
    for edition in EDITIONS:
        a, b = [corpus[edition, n] for n in (61, 62)]
        body_a = a.split("\n", 1)[1]
        body_b = b.split("\n", 1)[1]
        start = body_b.index("話說平兒出來吩咐林之孝家的道")
        end = body_b.index("不知端詳，且聽下回分解。", start) + len("不知端詳，且聽下回分解。")
        remaining = body_b[:start] + body_b[end:]
        duplicate_checks.append({
            "edition": edition,
            "chapter62_after_removing_insert_equals_chapter61_body": remaining == body_a,
            "inserted_segment_characters": end-start,
            "chapter61_body_characters": len(body_a),
            "chapter62_insert_starts_line": 2 + body_b[:start].count("\n"),
            "chapter62_insert_ends_line": 2 + body_b[:end].count("\n"),
        })
    appendix = []
    for edition in EDITIONS:
        text = corpus[edition, 67]
        position = text.index(r"\section*{程甲本}")
        appendix.append({"edition": edition, "start_line": text[:position].count("\n")+1, "appendix_characters_including_heading": len(text)-position})
    output = {
        "scope": "File access and mechanical checks only; this JSON does not prove literary reading.",
        "inventories": inventories, "files": rows,
        "normalization": "Remove balanced footnote/footnotetext commands, footnotemark, angle-bracket annotations, optional chapter-title duplicate and whitespace. Retain other inline annotations and all main text.",
        "normalized_differences": differences,
        "chapter62_duplicate_checks": duplicate_checks,
        "chapter67_quarantined_appendix": appendix,
    }
    (OUT / "source-audit.json").write_text(json.dumps(output, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({
        "files": len(rows),
        "inventories": inventories,
        "raw_characters_by_edition": {e: sum(r["unicode_characters"] for r in rows if r["edition"] == e) for e in EDITIONS},
        "normalized_different_chapters": [d["chapter"] for d in differences],
        "duplicate_checks": duplicate_checks, "appendix": appendix,
        "bad_structure_or_encoding": [r["path"] for r in rows if r["chapter_commands"] != 1 or r["replacement_characters"] or not r["begin_end_balanced_counts"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

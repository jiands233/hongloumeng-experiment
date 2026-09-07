"""Assemble only this experimental manuscript; frozen sources stay read-only."""

import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source_path = ROOT / "research/phase2/foreshadowing.json"
    library = json.loads(source_path.read_text())
    evidence = {item["id"]: item for item in library["evidence"]}
    records = []
    for name in ("root_audit.json", "middle_audit.json"):
        records.extend(json.loads((BASE / name).read_text()))
    records.sort(key=lambda item: item["chapter"])
    expected = list(range(81, 121))
    assert [item["chapter"] for item in records] == expected, "Audit chapters missing or duplicated"
    files = sorted((BASE / "chapters").glob("*.md"))
    assert [int(path.stem) for path in files] == expected, "Manuscript chapters missing or extra"
    chapters = []
    seen_titles = set()
    paragraphs = {}
    for item, path in zip(records, files):
        body = path.read_text().strip()
        title, prose = body.split("\n", 1)
        assert title.startswith("# 第") and "回" in title, path
        assert title not in seen_titles, "Duplicate chapter title"
        seen_titles.add(title)
        assert not re.search(r"TODO|TBD|待续写|正文待补|此处省略", prose), path
        count = len(re.findall(r"[\u3400-\u9fff]", prose))
        assert count >= 2000, f"{path.name}: only {count} Chinese characters"
        for paragraph in prose.split("\n\n"):
            if len(paragraph) > 90:
                assert paragraph not in paragraphs, f"Repeated paragraph: {path.name} / {paragraphs.get(paragraph)}"
                paragraphs[paragraph] = path.name
        ids = item["evidence_ids"]
        assert ids and len(ids) == len(set(ids)), path
        assert all(key in evidence for key in ids), f"Unknown F-ID: {path.name}"
        assert all(evidence[key]["contamination"] != "POTENTIAL_CONTAMINATION" for key in ids), path
        layers = {}
        for key in ids:
            layers.setdefault(evidence[key]["layer"], []).append(key)
        if "source_layers" in item:
            supplied = {key: sorted(value) for key, value in item["source_layers"].items() if value}
            assert supplied == {key: sorted(value) for key, value in layers.items()}, f"Layer mismatch: {path.name}"
        item["source_layers"] = layers
        assert item["invented_steps"] and item["continuity_notes"], path
        item.update({
            "chapter_id": f"X-{item['chapter']:03d}",
            "path": str(path.relative_to(BASE)),
            "title": title.removeprefix("# "),
            "sha256": digest(path),
            "chinese_characters_excluding_title": count,
            "status": "EXPERIMENTAL_FICTION_FIRST_DRAFT",
            "evidence_semantics": "约束与创作启发；不是具体续写情节已获原文证明。",
            "evidence_qualifications": [{
                "id": key,
                "layer": evidence[key]["layer"],
                "strength": evidence[key]["strength"],
                "version_refs": evidence[key]["version_refs"],
                "chapter_qualification": evidence[key]["chapter_qualification"],
                "version_details": evidence[key]["version_details"],
                "location": evidence[key]["location"],
            } for key in ids],
        })
        chapters.append(body)
    total = sum(item["chinese_characters_excluding_title"] for item in records)
    audit = {
        "schema_version": 1,
        "canonical_release": "red-chamber-canonical-v1",
        "canonical_dataset_sha256": "a307c6629bb6fbd4a2c1a54560e3c53e4fec435a7017a6d83407bf1c00086a54",
        "phase2_commit": "1f63ca58ae274ffab614d01ba34cd103c8d554e3",
        "phase2_json_sha256": digest(source_path),
        "work_status": "EXPERIMENTAL_FICTION_FIRST_DRAFT",
        "excluded_from_plot_selection": ["F-0349", "F-0350"],
        "training_memory_limit": "未访问禁用语料；本地可追溯性不能证明训练记忆绝对无影响。",
        "chapters": records,
    }
    (BASE / "chapter_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    intro = "# 红楼梦实验续作：第八十一至一百二十回\n\n独立创作的四十回初稿，不是曹雪芹佚稿或原作者结局复原。依据冻结前八十回及 Phase 2 证据库，新情节均为本次创作。\n\n"
    toc = "\n".join(f"- [{item['title']}]({item['path']})" for item in records)
    (BASE / "manuscript.md").write_text(intro + toc + "\n\n---\n\n" + "\n\n---\n\n".join(chapters) + "\n")
    rows = "\n".join(f"| {item['chapter_id']} | [{item['title']}]({item['path']}) | {item['chinese_characters_excluding_title']} |" for item in records)
    report = f"""# 合稿与完整性校验

四十回初稿齐全，81—120逐回连续。正文共 **{total:,}** 汉字，不含回题和标点；每回不少于2000汉字。篇幅属于短章初稿，未冒充通行长篇的等量后四十回。

机器检查通过：40个章号与审计一一对应，F-ID存在且来源层一致，排除F-0349/F-0350，逐回SHA-256、资格与补配条件可查，无占位语和相同长段落复制。篇幅检查仅作完整性下限，场景与衔接另经通读，不是文学质量证明。

运行：`python3 continuation/experimental_v1/build.py`。该命令只读取新正文、创作审计和已发布Phase 2 JSON；只重建本目录的合稿、逐回审计和本校验表。

原文读取边界、独立审阅及污染限制见 [交付说明](completion_report.md)；审阅历史见 [design_review.md](design_review.md)。这些检查不能认证本地批语真伪，也不能证明预训练记忆绝对无影响。

| 章ID | 回目 | 正文汉字数 |
|---|---|---:|
{rows}
"""
    (BASE / "verification.md").write_text(report)
    print(json.dumps({"chapters": len(records), "chinese_characters": total, "min_chapter": min(item["chinese_characters_excluding_title"] for item in records), "status": "pass"}, ensure_ascii=False))


if __name__ == "__main__":
    main()

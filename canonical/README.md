# 红楼梦实验底本 v1

这是从用户提供的本地汇校电子文本生成的固定实验快照，不是“恢复曹雪芹原稿”或“纯庚辰本”的声明。只含第001—080回的可用主文本；正文中的编辑标记不属于小说。

- `chapters/001.md`—`080.md`：唯一默认文学主语料。编号、题目、主体来源、哈希和限制见 `metadata/chapter_manifest.json`。
- `annotations/zhiyan/`：本地有传统批本标签的注释，已与正文及嵌套编按分离；来源标签不是批者鉴定。须显式选择读取，不能冒充正文。
- `annotations/editorial/`：编校、音义、异文说明。现代具体重建或含程本文字的混合按语另存根目录排除区，这里仅留不含情节的指针。
- `annotations/undetermined/`：来源或正文／批语归属不明；不得用作文学推理依据。
- `metadata/provenance.json`：P 编号为处理／缺口记录；N 为脚注容器；A 为外部尖括号编按；E 为从脚注内再剥离的编按；G 为全局上游限制。注释条目保留原标签，不冒充独立脂批条数。
- `metadata/source_map/`：每个正文段落或诗行对应的原文件行范围。P 记录另含精确 Unicode 偏移 `[start,end)`；其中“当前文本”指修复前所见片段，“canonical_replacement”指此次处理结果。被禁材料的当前文本以外置引用保存。
- `metadata/source_snapshot.json`：原始目录及 zip 的逐文件哈希；不移动、不重写原件。
- `metadata/known_issues.md` 与 `timeline_issues.json`：保留未能解决的版本、缺字、叙事矛盾与因果归属限制。
- `metadata/freeze.json`：固定文件集及 SHA-256。任何版本内变化、缺失或额外文件都使验证失败。

正文标记：`〔缺文:P…〕` 为有本地缺文说明，`〔疑缺:P…〕` 为校者怀疑，`□〔缺字:P…〕` 为缺字，`〔待定:P…〕` 为暂时隔离／不可靠字串，`〔补配起:P…〕` 为已有配补开始。不得替标记补写内容。64、67全回和标题整理等限制由 manifest 提供，不向正文插入大段版本评论。

操作入口：在仓库根目录运行 `python3 scripts/verify_canonical.py`；读取一回运行 `python3 scripts/read_canonical.py 62`；明确需要脂批时运行 `python3 scripts/read_canonical.py 5 --layer zhiyan`。生成器仅在冻结前可用，后续不自动再生。

“可信度高”仅意味着本次本地转写／操作可复核，不证明作者归属或手稿真伪。所有故事内部日期保留，不统一年龄或强排年表。

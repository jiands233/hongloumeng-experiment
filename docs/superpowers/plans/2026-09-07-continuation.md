# 四十回实验续作 Implementation Plan

> **For agentic workers:** Use subagent-driven-development for bounded drafting and independent review. Literary dependencies are fixed in the design; controller integrates all prose.

**Goal:** 完成独立目录中的第81—120回连贯小说初稿、合稿和创作审计。

**Architecture:** 冻结 canonical 和 Phase 2 只读。分回正文为源文件，脚本生成合稿和数量核查，创作选择单独记录。

**Tech Stack:** Markdown、JSON、Python 标准库。

## Global Constraints

- 禁止读取 excluded_sources、contamination_sources、research/phase1、原始 zip/来源正文及一切禁用续书、改编、具体重建。
- 原文仅经 scripts/read_canonical.py 读取，开工与完工须验证冻结快照。
- 所有新文学文字是实验创作，不是曹雪芹原文，不得回填 canonical 或 Phase 2。
- 保留正文、脂批和创作的区别，不据 F-0349、F-0350 决定情节。

## Tasks

- [x] 核验底本并核对第80回与主要冲突。
- [x] 建立 continuation/experimental_v1/design.md 与创作边界。
- [x] 根代理写81—90回；分段代理按设计写91—110回，各回完整场景。
- [x] 根代理写111—120回，核对中段交接。
- [x] 独立审阅结构与文本，修正文中越界、人物矛盾和机械重复。
- [x] 生成 manuscript.md、chapter_audit.json、verification.md；重新校验冻结材料。
- 交付末步：仅提交本次新增文件，最终回复给正文入口与实际 Git commit。

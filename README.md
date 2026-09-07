# 红楼梦实验

以冻结的前八十回语料为基础，建立可追溯的未来指向证据库，再在用户明确授权后创作独立的第八十一至一百二十回实验续作。

续作是 AI 生成的小说初稿，不是曹雪芹佚稿，不宣称还原原作者结局。证据审计、创作选择与新写正文分别保存，续文不回填为前八十回证据。

## 阅读入口

- [用户提示词原文](prompts/user_prompts.md)：当前任务全部 5 条可恢复用户消息，包括完整 Phase 2 提示词；另有 [JSON](prompts/user_prompts.json) 可供机器读取。
- [四十回续作合稿](https://github.com/jiands233/hongloumeng-experiment/blob/codex/experimental-continuation/continuation/experimental_v1/manuscript.md)：第 81—120 回，共 40 回、80,969 个汉字，见[续作核查记录](https://github.com/jiands233/hongloumeng-experiment/blob/codex/experimental-continuation/continuation/experimental_v1/verification.md)。
- [Phase 2 审计报告](research/phase2/phase2_report.md)：488 条 F-ID、40 组冲突与反证、52 个未回答问题。
- [证据库 Markdown](research/phase2/foreshadowing.md) / [证据库 JSON](research/phase2/foreshadowing.json)。
- [人物索引](research/phase2/character_evidence_index.md) / [主题索引](research/phase2/theme_evidence_index.md)。
- [冲突库](research/phase2/conflicts.md) / [未解决问题库](research/phase2/unresolved_questions.md)。
- [冻结底本说明](canonical/README.md) / [项目读取规则](AGENTS.md)。

## 项目阶段与分支

| 阶段 | 内容 | 记录 |
| --- | --- | --- |
| Phase 1.5 | 冻结 canonical v1，建立读取器、来源追踪与资格限制 | `1da9e46`、`9044864` |
| Phase 2 | 前八十回未来指向证据审计；正序全文审读与逆序查漏 | `1f63ca5` |
| 实验续作 | 用户另行授权后写作第 81—120 回，保存创作选择与逐回依据 | `a118b35` |

`main` 保存冻结语料与证据审计；`codex/experimental-continuation` 另含实验续作。两个分支均提供本 README 和用户提示词归档。阅读续作时请使用上面的链接，或切换至续作分支。

Phase 1、Phase 1.5 原始提示词未出现在当前可用任务历史中；提示词归档明确标记这一缺口，不以研究报告或后来的摘要替代用户原话。

## 证据与读取边界

正文、脂批、编校信息与不确定材料必须区分。脂批仅称“本地标作某本的批语”，来源未经手稿认证。版本补配及异文敏感处遵守 canonical 元数据中的资格限制。

Phase 2 共收录正文证据 406 条、脂批证据 82 条；强度为 A 131、B 233、C 101、D 23。证据强度与来源层是不同字段。F-0349、F-0350 标记为 `POTENTIAL_CONTAMINATION`，均为 D 级候选，未参与续作剧情选择。能追溯本地引文，不等于能证明模型训练记忆完全没有影响。

后续文学工作先校验冻结底本，再使用显式读取器。禁止将隔离来源、通行续书、影视剧情或现代具体后四十回重建方案作为推理依据；不得顺手修改 canonical v1。完整规则以 [AGENTS.md](AGENTS.md) 和 [canonical 说明](canonical/README.md) 为准，阶段授权按用户后续明确指令更新。

## 本地查阅与校验

在仓库根目录使用 Python 3：

```sh
python3 scripts/verify_canonical.py
python3 scripts/read_canonical.py 1
python3 scripts/read_canonical.py 1 --layer zhiyan
python3 research/phase2/tools/query_evidence.py F-0001
python3 research/phase2/tools/validate_phase2.py
```

[Phase 2 使用说明](research/phase2/README.md) 解释 F-ID、来源定位、关系边与构建输入。续作的[创作选择](https://github.com/jiands233/hongloumeng-experiment/blob/codex/experimental-continuation/continuation/experimental_v1/design.md)和[逐回依据](https://github.com/jiands233/hongloumeng-experiment/blob/codex/experimental-continuation/continuation/experimental_v1/chapter_audit.json)位于独立目录。

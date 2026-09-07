# Phase 2 使用入口

权威交付是本目录下的 `foreshadowing.json` 与同源生成的 Markdown，不是 `work/` 临时摘录。`canonical/` 仍是冻结 v1，文学原文必须经过项目读取器。

```sh
python3 scripts/verify_canonical.py
python3 research/phase2/tools/query_evidence.py F-0001
python3 research/phase2/tools/validate_phase2.py
```

`foreshadowing.json` 顶层 `evidence` 数组按唯一 F-ID 精确索引；`key_to_id` 保留编辑期键映射。每条含原文、来源层、字符偏移、文件哈希、N-ID、人物、主题、其他解释、强度、置信度、版本资格、关联证据和截至80回状态。批语位置以 N-ID 的 `current_text` 为容器，不能把原来源行号当成 canonical 正文行号。

`source_class` 的 A/B 表示正文/脂批；`strength` 的 A/B/C/D 表示预示强度。这两套字母含义独立。编校信息另列 `version_qualifications.json`，不确定原文不进入数据库。

`related_evidence` 包含冲突共引、问题共引及人物主题连续关系，不是统计独立性或因果证明。第22回宝钗补配谜与相同批语不得算两份独立证言。第5回匿名图判的人物字段是有条件的索引归属。A级不保证对象识别、事件机制或时间的确定性。

弱关联可能受到既有模型记忆影响的两条标为 `POTENTIAL_CONTAMINATION`，只能作D级辅助候选。`CLEAR_LOCAL_SUPPORT` 只表示本地文字可追溯，不宣称抹除模型记忆。

`work/` 保存正序摘录、倒查补项和修订输入，以便审计生成过程。文件名有早期计划范围，实际收录范围须以每条 chapter 字段为准。`overrides.json` 覆盖草稿中的错字、未更新状态及排除项；不得直接把草稿当已验证证据。旧 `forward_*.jsonl` 是早期不完整交付日志，完整正序覆盖以 `audit_forward.jsonl` 及 `audit_coverage.json` 为准。

重建仅写 `research/phase2/`：

```sh
python3 research/phase2/tools/build_phase2.py
python3 research/phase2/tools/validate_phase2.py
```

构建会先通过冻结读取器核验数据；出现不匹配即失败。当前F-ID按本次完整集固定，后续修订应新建研究版本并保留映射，不得悄悄重排本交付的ID。

Phase 2 已止于证据审计。Phase 3、结局推演、后四十回规划及续写必须另有用户明确授权。

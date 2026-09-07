# 分段证据提取格式（临时键稍后统一为 F-ID）

输出为 JSON 数组。每条包含：
- key: 唯一稳定临时键，例如 C005-JUDGMENT-DAICHAI
- chapter: 1-80整数
- layer: 正文 / 脂批
- types: 字符串数组
- characters: 简体全名数组（例如贾宝玉、林黛玉、薛宝钗、巧姐、甄士隐；框架石头、神瑛侍者分开）
- quote: canonical 中逐字连续的最短必要引文（不要加省略号拼接；多项证据请拆或quote_segments另列）
- note_id: 脂批必须填 Nxxx-x-xxxx；正文null
- context: 场景、说话人和已发生状态
- direct_meaning: 不含未来具体故事的字面含义
- future_direction: 审慎限定的未来指向
- possible_directions: 可支持的方向数组，不写完整结局或具体后四十回事件方案
- alternatives: 至少一项其他解释数组
- strength: A/B/C/D （A=文字明确预言/承诺未来；不等于某个具体结局已确定）
- confidence: 0-100，衡量该引文确属未来指向的把握，不是剧情发生概率
- version_refs: 相关P/G编号数组；全局G001不可当局部已知校改
- version_note: 局部限制说明，没局部问题写“无已登记的局部问题；全局汇校限制G001仍在”
- themes: T-01 ... T-15数组
- related_keys: 已知本段其他记录key数组（后续可以补）
- status_at_80: unresolved / partially_realized / realized_before_80 / framework / undetermined_at_shard_boundary
- contamination: CLEAR_LOCAL_SUPPORT / POTENTIAL_CONTAMINATION
- remarks: 明确保留不能推出的事情、阐释边界

每段附 coverage.md：每回正序全文与允许脂批实际读到的范围，工具输出截断如何补读，候选排除原因，漏项复核提示。不把自动扫描当阅读全文。代理可在本段末作倒序查漏，记录实际新增或确认结果；主任务另做80→1全局逆查。

只用冻结canonical和白名单读取器。完整读取每回main与允许zhiyan；不得读原始source、zip、excluded_sources、undetermined原文、Phase1旧材料、网络。版本元数据可按P编号读取说明，不打开隔离引用。补配22后段、64/67整回按限制用；50首段和78括号已剥离不能复活，52题名待定禁用。题目19/80及17/18分回有整理限制，不作强未来证据。

读取方式：python3 research/phase2/tools/read_slice.py main 1 1 45 --log forward_01_27.jsonl。它只经已冻结read_canonical取得文本；显示带L行号正文或带#序号和N-ID脂批，首行给总数。大段按≤4000tokens批量递进以免截断。脂批按≤30条一组，长条单读。交付证据应由你实际阅读判断生成，不能把关键词命中模板批量冒充分析。

15主题：T-01贾府衰败，T-02宝玉精神道路，T-03宝黛关系，T-04金玉关系，T-05十二钗命运，T-06政治风险，T-07经济崩坏，T-08婚姻与家族利益，T-09死亡，T-10离散，T-11出家，T-12盛衰循环，T-13太虚幻境，T-14第一回框架闭环，T-15真假/梦幻/石头结构。

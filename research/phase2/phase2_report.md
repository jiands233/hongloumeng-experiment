# Phase 2：前八十回伏笔与未来指向证据审计报告

本阶段只建立证据、分歧和未回答问题。已完成Phase 2后停止，未进行Phase 3命运推演、后四十回规划或正文创作。

- 证据：488条唯一F-ID；A 131、B 233、C 101、D 23。
- 正文：406条；脂批：82条；其他允许材料作为文学F证据：0条。
- 冲突/反证：40组；未解决问题：52个，均未作答。
- 状态：框架待闭合或总括 39；部分已应 / 后续仍开放 83；未闭环 329；80回内已应 / 已落空的比较样本 37。
- 人物关联最丰富：贾宝玉（167）、林黛玉（84）、王熙凤（83）、薛宝钗（59）、袭人（36）、贾母（35）、贾琏（29）、贾探春（27）。计数含被涉及，不等于命运预测可靠度。
- 正序1—80回正文及允许脂批全部审读；逆序80—1回查漏全部完成，逐回决定见audit_log.md。
- 第5回14组图判、14支曲（含引子和收尾）全部建档；正册11单元中钗黛合写，不能误算成少一钗。

证据仍不足的问题包括：宝黛钗关系的具体决策过程；尚未实写的死亡提示所对应的具体方式和时间；政治危机的确切案由及责任；白首双星的对象；巧姐曲中亲属的身份；甄贾两玉的实际交接；三春的单一所指；情榜与框架销号如何展开。明确提示与具体机制之间仍有很大距离。

污染检查：没有访问禁读目录正文、续书、影视或现代具体重建方案，没有联网。逐条检查引文、说话层级和跨回归因，删去过短的“习射”独立条目，并撤回无直接根据的诗句→金玉婚后定向。保留以下POTENTIAL_CONTAMINATION弱候选：[F-0349](foreshadowing.md#f-0349) [F-0350](foreshadowing.md#f-0350)；风险是将射覆物名联想为人物或婚配，没有排除训练记忆影响的客观方法。两条均D级，不得单独推论。其余CLEAR_LOCAL_SUPPORT表示有可回查本地依据，不表示能证明模型从未受记忆影响。

来源资格：canonical v1完整性校验通过，数据集SHA256为 `a307c6629bb6fbd4a2c1a54560e3c53e4fec435a7017a6d83407bf1c00086a54`。64、67回及22后段明确标补配；17/18分回、19/80回目不作独立谶证；第5回保持虎兔；41残批、50隔离开头、52缺题、75缺诗、78待定段均依冻结限制处理。未修改canonical。全局G001限制始终保留。

A/B是来源层，A/B/C/D是证据强度，二者字段独立。C编校只入版本资格表，D不确定材料不读取原文、不入文学证据；强度D不等于来源D。所有批语只称本地所标批本，不鉴定作者。

检索：`python3 research/phase2/tools/query_evidence.py F-0001`。JSON的evidence数组及key_to_id、字符偏移、N-ID、哈希可以机器精确引用；conflicts、unresolved_questions与两类索引也在同一JSON内。关系边不自动代表相互证实。

输出目录：`research/phase2/`。主交付：foreshadowing.md、foreshadowing.json、character_evidence_index.md、theme_evidence_index.md、conflicts.md、unresolved_questions.md、phase2_report.md。辅助：audit_log.md、audit_coverage.json、version_qualifications.json、special_inventory.md、validation.json、tools/。work/是提取与修订输入，不能代替已验证F库。

Git commit：以 `git log -1 --format=%H -- research/phase2/phase2_report.md` 解析本报告所属提交；提交不能在自身内容中写入自己的哈希。实际提交哈希在最终交付消息列出。

质量检查的最终机器结果见validation.json：唯一ID、引文逐字回查、位置哈希、引用完整性、必备索引、两轮覆盖及第5回条目数。

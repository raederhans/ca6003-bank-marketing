# A → B / C / D 交接

A 的可运行材料、来源及许可、质量证据和固定 split 已在本包。未完成的事项明确保留 pending；没有替任何成员签字。

| 接收人 | 现在可使用的文件 | 接收复核 | 后续独立责任 |
| --- | --- | --- | --- |
| B | data/raw、data/splits、outputs/train_profile.csv、train_history_consistency.csv、quality_audit.csv | pending | 仅 train 开放 EDA，核心发现、交叉/分层证据、≤4 主图与解释限制 |
| C | src/data_contract.py、notes/feature_policy.csv、DATA_CONTRACT.md、A Notebook | pending | 复核哨兵/unknown 语义，实现四个 S/U 管线与转换测试，最终 Notebook 总装 |
| D | 固定 split、11 列接口、字段政策 | pending | 统一评估代码、验证与封版后测试、四组差值与分组误差 |
| 全组 | THIRD_PARTY_NOTICES.md、AI_USAGE.md、QA.md | pending | 人工理解/审阅、真实贡献记录、引用、最终视频与提交 |

训练集的调查入口（n=27,126，全部来自本机实际运行）：

- pdays=-1：22,235；pdays=0：0。真实零天数在语义上仍需与 -1 区分。
- job=unknown：179；education=unknown：1,100。
- balance<0：2,280；保留原始值。
- pdays>=0 且 poutcome=unknown：5。不能把所有 unknown 解释为此前没联系；具体原因尚不确定。
- pdays=-1 与 previous=0 在训练记录中一致；这不证明数据采集过程或客户身份完整。
- 训练集完整 17 列的精确重复组成员：0。允许的 11 列相同且标签不一致的记录另列在质量审计，不能机械合并。

分位数、异常例子和分母见 outputs；开放式发现仍由 B 完成。**未根据测试集结果选择任何准备方案。**

交接核查步骤：按 README 从项目环境运行 `scripts/validate_project.py`，核对 4 份原始文件哈希、精确拆分、train 审计、policy；再运行 `scripts/validate_notebook.py` 检查干净内核。逐条读 5 行“contacted + unknown”的原始训练记录并由 C 确认语义。记录复核日期、真实姓名、发现和处置；不要将自动化执行者写成人工 reviewer。

项目仍需完成 B/C/D 工作、C 整合后的完整新内核 Run All、四人视频、课程提交及互评；A 包通过不代表这些已完成。

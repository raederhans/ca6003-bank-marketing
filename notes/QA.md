# QA 与复现记录

`outputs/validation.json` 是实际验证结果与执行时间的权威记录；`outputs/environment.json` 记录数据管线运行环境。验证产物未形成前不能把本说明当作通过凭证。

项目脚本 `scripts/validate_project.py` 是只读检查：原始字节、精确 split 顺序/覆盖、字典/字段政策、接口对齐与禁用字段、test 默认封存、训练审计复算、预定格式检查、split 行数和哈希篡改拒绝。无模型拟合。独立 QA 可以运行它，不需修改项目。

`scripts/validate_notebook.py` 创建项目内临时 kernel 配置，在干净 Python 内核运行 A 章；成功后保存执行过的 Notebook 及运行 JSON。未使用全局 kernel 注册；.local 不上传。

作者复现流程还会在仅含源码/配置的临时目录独立从官方 URL 重新下载、生成拆分/审计，并逐文件比较哈希；该目录不复用仓库数据，不覆盖桌面项目。关键结果纳入 validation.json。

QA 输出不等于人工审核。学生复核、C 语义确认和 B/C/D 接收仍为 pending。test 仅用于预先规定的格式/范围、覆盖检查，不执行自由探索或模型评价。

Library 手册正文已通过支持的读取方式核对。官方本地传输流程在 Windows 文件属性步骤失败，未保留伪称成功的 PDF，也未绕过该流程。项目 references/ 仅存本地来源索引，并已忽略；课件、手册 PDF、Library 传输令牌与辅助工具不属于上传清单。

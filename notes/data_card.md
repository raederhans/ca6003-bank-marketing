# Data source card / 数据来源卡

Dataset: UCI Bank Marketing, legacy bank-full.csv; dataset ID 222.

Source: https://archive.ics.uci.edu/dataset/222/bank+marketing
Download: https://archive.ics.uci.edu/static/public/222/bank+marketing.zip

Actual acquisition UTC: 2026-10-12T09:30:28.154035+00:00
Acquisition method: official HTTPS download

Path: outer bank-marketing.zip → bank.zip → bank-full.csv + bank-names.txt. Original bytes retained.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| data/source/bank-marketing.zip | 1023843 | `e0bf5f5de5b846e2f18e9d90606637267d46dfa260e0f17bb12e605db5efbeb4` |
| data/source/bank.zip | 579043 | `99d7e8eb12401ed278b793984423915411ea8df099e1795f9fefe254f513fe5e` |
| data/raw/bank-full.csv | 4610348 | `d1513ec63b385506f7cfce9f2c5caa9fe99e7ba4e8c3fa264b3aaf0f849ed32d` |
| data/raw/bank-names.txt | 3864 | `3899a77082573ed676a7dfce3765a5307915c7f11b1fe2f6f55fd3c5467c12f7` |

实际读取：45,211 行 × 17 列（16 原始输入 + y），分号分隔，keep_default_na=False；原始字段与行序保留。

本研究使用 11 个字段；5 个当前活动字段按联系前时点排除。具体政策和复核状态见 feature_policy.csv。

原始数据用于准备选择的离线比较，不是可部署客户名单系统。缺少客户 ID、完整时间戳和快照日期，无法验证客户级独立性或所有输入的真实时点可用性。随机划分不验证未来表现。

许可：UCI 当前页面于 2026-10-12 核验为 CC BY 4.0：https://creativecommons.org/licenses/by/4.0/。保留作者、来源、许可链接与修改声明；不表示 UCI 或作者背书。

署名：Moro, S., Rita, P., & Cortez, P. (2014). Bank Marketing [Dataset]. UCI. https://doi.org/10.24432/C5K306。旧版 bank-names.txt 另要求引用 Moro, Laureano & Cortez (2011) CRISP-DM 论文；完整引文见 THIRD_PARTY_NOTICES.md。

本项目增加 row_id、拆分及审计表；原始字节未改。原包包含其他数据变体，但本管线只提取并使用锁定的 bank-full.csv 与说明文件。不要换成 bank-additional-full.csv、抽样 bank.csv 或 static/public/222/data.csv。

数据页的多版本说明可能混合字段数量/类别；以本文件头与同包 bank-names.txt 为依据。pdays=-1 的旧版语义不能替换成新版 999；unknown 保留为文字类别。

运行环境见 outputs/environment.json；全部依赖版本见 requirements.lock.txt。数据锁与代码保存在同一仓库；二次运行须校验而非重写 raw/split。

Student reviewer: pending. C semantic reviewer: pending.

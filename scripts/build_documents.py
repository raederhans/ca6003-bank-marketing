"""Build A's documentation tables and executable data chapter from local evidence."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import nbformat

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.data_contract import CATEGORIES, EXPECTED_COLUMNS, FEATURES, NUMERIC

DEFINITIONS = {
    "age": ("Client age", "years", "Positive integer; no arbitrary age trimming"),
    "job": ("Type of job", "category", "unknown is a literal category; U applies here"),
    "marital": ("Marital status", "category", "divorced includes divorced or widowed in the source documentation"),
    "education": ("Education category", "category", "Legacy primary/secondary/tertiary/unknown; U applies here"),
    "default": ("Has credit in default?", "yes/no", "Do not infer default amount or date"),
    "balance": ("Average yearly balance", "EUR", "Negative and extreme values are not automatically errors"),
    "housing": ("Has housing loan?", "yes/no", "Retain original categories"),
    "loan": ("Has personal loan?", "yes/no", "Retain original categories"),
    "contact": ("Last contact communication type", "category", "Current campaign contact process; excluded"),
    "day": ("Day of month of last contact", "1-31", "Not day_of_week; incomplete calendar information"),
    "month": ("Month of last contact", "category", "No year/complete timestamp; excluded"),
    "duration": ("Last contact duration", "seconds", "Known after the call; unavailable to contact-before selection"),
    "campaign": ("Number of contacts in the current campaign for this client", "count", "Includes last contact; excluded by project timing policy"),
    "pdays": ("Days since last contact in a previous campaign", "days or -1 state", "-1 means not previously contacted; 0 is distinct; do not use 999 sentinel"),
    "previous": ("Number of contacts before the current campaign for this client", "count", "Nonnegative; high counts trigger investigation rather than deletion"),
    "poutcome": ("Outcome of previous marketing campaign", "category", "unknown is not always no prior contact; U must not change this field"),
    "y": ("Has the client subscribed a term deposit?", "yes/no", "Target only: yes=1 no=0"),
}


def write_csv(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_tables():
    dictionary, policy = [], []
    for field in EXPECTED_COLUMNS:
        meaning, unit, special = DEFINITIONS[field]
        role = "input" if field in FEATURES else "target" if field == "y" else "excluded"
        timing = ("Assumed available before current campaign contact; exact snapshots unverified" if role == "input" else
                  "Observed response after current campaign; target only" if role == "target" else
                  "Current/last-contact or campaign process; conservatively unavailable before contact")
        dictionary.append({"field": field, "storage_type": "integer" if field in NUMERIC else "string", "meaning": meaning,
                           "unit": unit, "documented_categories": "|".join(CATEGORIES.get(field, [])),
                           "special_semantics": special, "role": role,
                           "source": "data/raw/bank-names.txt; UCI dataset 222"})
        policy.append({"field": field, "role": role, "allowed_in_X": role == "input", "prediction_time": timing,
                       "reason": special, "policy_basis": "team manual pre-contact research design", "owner": "A", "reviewer": "pending"})
    policy.append({"field": "row_id", "role": "tracking_only", "allowed_in_X": False,
                   "prediction_time": "Assigned from zero-based original row position", "reason": "Not a customer ID or feature; preserve original order",
                   "policy_basis": "fixed split tracking contract", "owner": "A", "reviewer": "pending"})
    write_csv(ROOT / "notes/data_dictionary.csv", dictionary)
    write_csv(ROOT / "notes/feature_policy.csv", policy)


def build_source_card():
    provenance = json.loads((ROOT / "data/source/provenance.json").read_text(encoding="utf-8"))
    lines = ["# Data source card / 数据来源卡", "", "Dataset: UCI Bank Marketing, legacy bank-full.csv; dataset ID 222.",
             "", "Source: https://archive.ics.uci.edu/dataset/222/bank+marketing",
             "Download: https://archive.ics.uci.edu/static/public/222/bank+marketing.zip",
             "", f"Actual acquisition UTC: {provenance['acquired_utc']}",
             f"Acquisition method: {provenance['acquisition']}",
             "", "Path: outer bank-marketing.zip → bank.zip → bank-full.csv + bank-names.txt. Original bytes retained.",
             "", "| Artifact | Bytes | SHA-256 |", "| --- | ---: | --- |"]
    for name, artifact in provenance["artifacts"].items():
        lines.append(f"| {name} | {artifact['bytes']} | `{artifact['sha256']}` |")
    lines.extend(["", "实际读取：45,211 行 × 17 列（16 原始输入 + y），分号分隔，keep_default_na=False；原始字段与行序保留。",
                  "", "本研究使用 11 个字段；5 个当前活动字段按联系前时点排除。具体政策和复核状态见 feature_policy.csv。",
                  "", "原始数据用于准备选择的离线比较，不是可部署客户名单系统。缺少客户 ID、完整时间戳和快照日期，无法验证客户级独立性或所有输入的真实时点可用性。随机划分不验证未来表现。",
                  "", "许可：UCI 当前页面于 2026-10-12 核验为 CC BY 4.0：https://creativecommons.org/licenses/by/4.0/。保留作者、来源、许可链接与修改声明；不表示 UCI 或作者背书。",
                  "", "署名：Moro, S., Rita, P., & Cortez, P. (2014). Bank Marketing [Dataset]. UCI. https://doi.org/10.24432/C5K306。旧版 bank-names.txt 另要求引用 Moro, Laureano & Cortez (2011) CRISP-DM 论文；完整引文见 THIRD_PARTY_NOTICES.md。",
                  "", "本项目增加 row_id、拆分及审计表；原始字节未改。原包包含其他数据变体，但本管线只提取并使用锁定的 bank-full.csv 与说明文件。不要换成 bank-additional-full.csv、抽样 bank.csv 或 static/public/222/data.csv。",
                  "", "数据页的多版本说明可能混合字段数量/类别；以本文件头与同包 bank-names.txt 为依据。pdays=-1 的旧版语义不能替换成新版 999；unknown 保留为文字类别。",
                  "", "运行环境见 outputs/environment.json；全部依赖版本见 requirements.lock.txt。数据锁与代码保存在同一仓库；二次运行须校验而非重写 raw/split。",
                  "", "Student reviewer: pending. C semantic reviewer: pending.", ""])
    (ROOT / "notes/data_card.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_notebook():
    md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
    cells = [md("""# CA6003 — A: Data foundation and governance

研究问题：特殊值语义与未知信息处理如何影响银行营销分类的可靠性？

本章交付来源、字段政策、训练分区质量审计与固定划分。B 负责开放式发现，C 负责 S/U 四组预处理与 Notebook 总装，D 负责模型和评估。这里没有拟合模型或学习填补、缩放参数。

场景：历史记录层面的**联系前**离线名单筛选。缺少客户唯一 ID 和特征快照时间，不能证明客户级独立性或真实上线可用性；随机划分不代表未来泛化或因果营销效果。"""),
        md("""## 1. Provenance, license and scope

仅使用 legacy `bank-full.csv`：45,211 行、16 个原始输入 + y。外 ZIP → bank.zip → 原始 CSV/说明。拒绝 bank-additional、bank.csv 抽样版和更改列名/分隔符的 data.csv。

来源：[UCI Bank Marketing](https://archive.ics.uci.edu/dataset/222/bank+marketing)，许可：[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。数据作者 Moro、Rita、Cortez；数据引用 DOI [10.24432/C5K306](https://doi.org/10.24432/C5K306)。旧版说明另要求引用 Moro、Laureano、Cortez (2011)，详见仓库 THIRD_PARTY_NOTICES.md。

原始字节不修改；row_id、划分及审计是本项目增加的派生成果。署名不表示作者或 UCI 背书。

在仓库根目录或 notebooks/ 下打开本章。所有路径相对项目，不下载个人资料。若尚未准备数据，先运行 `python scripts/prepare_data.py`。"""),
        code("""from pathlib import Path
import hashlib, json, sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
ROOT = Path.cwd().resolve()
if not (ROOT / 'config/dataset_lock.json').is_file():
    ROOT = ROOT.parent
assert (ROOT / 'config/dataset_lock.json').is_file(), 'Open from repository root or notebooks/'
sys.path.insert(0, str(ROOT))
lock = json.loads((ROOT / 'config/dataset_lock.json').read_text(encoding='utf-8'))
for relative, expected in lock['artifacts'].items():
    data = (ROOT / relative).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected['sha256'], relative
    assert 'bytes' not in expected or len(data) == expected['bytes'], relative
provenance = json.loads((ROOT / 'data/source/provenance.json').read_text(encoding='utf-8'))
print('Acquired UTC:', provenance['acquired_utc'])
print('Raw SHA-256:', lock['artifacts']['data/raw/bank-full.csv']['sha256'])
print('All four pinned source artifacts verified')"""),
        md("""## 2. Read without semantic cleaning and freeze the exact split

`keep_default_na=False` 保留文字 unknown 和原空字符串；显式空值由审计单独检查。`row_id=np.arange(len(raw))` 对应原始数据行的 0-based 位置，不是客户标识，也不进入 X。两次 stratified split 严格使用 random_state=42；第二次必须使用 y.iloc[dev]。Manifest 按原始 row_id 排序，JSON 另保留 split 返回顺序。"""),
        code("""raw = pd.read_csv(ROOT / 'data/raw/bank-full.csv', sep=';', keep_default_na=False)
assert list(raw.columns) == lock['columns'] and raw.shape == (45211, 17)
y = raw['y'].map({'no': 0, 'yes': 1})
assert not y.isna().any()
ids = np.arange(len(raw))
dev, test = train_test_split(ids, test_size=.20, stratify=y, random_state=42)
train, val = train_test_split(dev, test_size=.25, stratify=y.iloc[dev], random_state=42)
splits = {'train': train, 'val': val, 'test': test}
assert len(set(train) & set(val)) == 0
assert len(set(dev) & set(test)) == 0
assert set(np.concatenate(list(splits.values()))) == set(ids)
assignment = pd.Series('', index=ids, name='split')
for name, positions in splits.items():
    assignment.loc[positions] = name
manifest = assignment.rename_axis('row_id').reset_index()
pd.testing.assert_frame_equal(manifest, pd.read_csv(ROOT / 'data/splits/split_manifest.csv'))
saved = json.loads((ROOT / 'data/splits/split_indices.json').read_text(encoding='utf-8'))
assert all(np.array_equal(splits[name], saved[name]) for name in splits)
raw.index.name = 'row_id'
print('Shape:', raw.shape, 'split sizes:', {k: len(v) for k,v in splits.items()})"""),
        md("""以下表仅对 train 展示标签分布；val/test 只显示预定行数覆盖信息，其标签统计保持空白。开放 profiling 仅使用 train。封存是团队流程约束，原始 CSV 本身仍包含全部记录。"""),
        code("""display(pd.read_csv(ROOT / 'outputs/split_summary.csv'))
format_checks = pd.read_csv(ROOT / 'outputs/format_checks.csv')
assert format_checks.n_violations.sum() == 0
print('Predeclared holdout format checks passed:', len(format_checks))"""),
        md("""## 3. Dictionary and prediction-time policy

11 个输入：age、job、marital、education、default、balance、housing、loan、pdays、previous、poutcome。

duration 是通话后信息；campaign、contact、day、month 也按保守的联系前时点排除。这是小组研究设计，而非 UCI 或课程强制限制。reviewer 保留 pending，待真实成员复核。"""),
        code("""dictionary = pd.read_csv(ROOT / 'notes/data_dictionary.csv', keep_default_na=False)
policy = pd.read_csv(ROOT / 'notes/feature_policy.csv', keep_default_na=False)
assert dictionary.field.tolist() == lock['columns']
allowed = policy.loc[policy.role.eq('input'), 'field'].tolist()
assert allowed == lock['allowed_features']
assert not set(allowed) & {'y', 'row_id', 'duration', 'campaign', 'contact', 'day', 'month'}
display(dictionary)
display(policy[['field', 'role', 'prediction_time', 'reviewer']])"""),
        md("""## 4. Training-only quality evidence

本单元使用仓库内 `src/audit.py` 的审计函数（随本章一起提交，非个人外部脚本）。C 总装最终单一提交 Notebook 时，应将所需函数内联或按课程允许方式打包。

区分 NaN/空串、unknown、pdays=-1。pdays=-1 是此前未联系；pdays=0 是实际间隔。负余额、高联系次数、匹配记录不自动等于错误。STOP 级规则只有 n_affected>0 才阻塞；INVESTIGATE 表示待人工调查，不执行删除。"""),
        code("""from src.audit import profile_train, audit_train
training = raw.loc[np.sort(train)].copy()
profile = profile_train(training)
audit = audit_train(training)
saved_audit = pd.read_csv(ROOT / 'outputs/quality_audit.csv', keep_default_na=False)
pd.testing.assert_frame_equal(audit, saved_audit)
assert audit.partition.eq('train').all()
assert audit.loc[audit.severity.eq('STOP'), 'n_affected'].sum() == 0
display(profile)
display(audit.loc[audit.n_affected.gt(0), ['check_id','field','n_affected','example_row_ids','severity','decision']])
print('No source rows dropped. No imputer/scaler/model fitted.')"""),
        md("""## 5. History consistency handoff

以下训练分区交叉计数用于检查语义与向 B 提供调查入口。观察是计数本身；不能据此补造联系史、解释 unknown 的真实生成原因或声称因果。B 仍须独立完成其核心发现、分层证据与限制。"""),
        code("""history = pd.read_csv(ROOT / 'outputs/train_history_consistency.csv')
assert history.partition.eq('train').all() and history.n.sum() == len(training)
display(history)
summary = json.loads((ROOT / 'outputs/audit_summary.json').read_text(encoding='utf-8'))
print(json.dumps(summary, indent=2))"""),
        md("""## 6. B / C / D interface and remaining reviews

- B：只用 train；保留 row_id 作证据定位，建立实际发现与分母。
- C：复用固定 X/y 和 11 列政策，实现四个 S/U 开关；只在 fit 分区学习填补、编码、缩放。U 只改变 job/education，poutcome 不变；S 区分 -1/0/正天数。
- D：相同原始行和划分、固定模型与阈值；规则冻结后重拟合 train+val，再对 test 一次性预定评估。

以下只加载 train/val 验证接口。D 最终阶段可显式 allow_test=True；这不是访问控制，也不代表现在可以查看 test 结果。"""),
        code("""from src.data_contract import load_partition
X_train, y_train = load_partition('train')
X_val, y_val = load_partition('val')
assert X_train.index.equals(y_train.index)
assert X_train.columns.tolist() == allowed
assert np.array_equal(X_train.index, train)
print('Training:', X_train.shape, 'Validation:', X_val.shape)
try:
    load_partition('test')
except ValueError as exc:
    print(str(exc))"""),
        md("""## 7. GenAI declaration and review status

工具：OpenAI Codex（本任务 AI 编程辅助）。用途：起草 A 的下载/哈希校验、读取与固定拆分、审计、文档和 Notebook；根据本地运行结果修正。所有数值来自实际脚本，不采用手册示例作为已运行结果。实际验证见 outputs/validation.json 与 notes/QA.md：字节哈希、划分复算、训练审计复算、接口防泄漏检查、离线复跑、干净内核执行。

**学生人工复核：pending。C 的语义复核：pending。B/C/D 接收签字：pending。** 自动化检查不等于学生已理解并独立验证。成员须核对代码、字段时点与结论，填写真实姓名/贡献，保留 AI 使用声明；不把生成内容当作已完成的人工工作。

此 A 包不是完整课程提交；B 的发现、C 的四组管线/最终 Notebook、D 的模型结果及全组视频仍待完成。

参考：UCI 数据页与 data/raw/bank-names.txt；[scikit-learn 数据泄漏说明](https://scikit-learn.org/stable/common_pitfalls.html)；项目 notes/data_card.md、notes/DATA_CONTRACT.md、THIRD_PARTY_NOTICES.md。""")]
    for index, cell in enumerate(cells):
        cell.id = f"a-governance-{index:02d}"
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                                      "language_info": {"name": "python", "version": "3.12"}})
    path = ROOT / "notebooks/A_data_foundation.ipynb"
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.validate(nb)
    path.write_text(nbformat.writes(nb) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    build_tables()
    build_source_card()
    build_notebook()
    print("Created 17-field dictionary, 18-row feature policy, and A notebook")

# B / C / D 数据契约 v1

## 不可变公共对象

1. `raw`：`bank-full.csv`，SHA-256 `d1513ec63b385506f7cfce9f2c5caa9fe99e7ba4e8c3fa264b3aaf0f849ed32d`。`pd.read_csv(..., sep=';', keep_default_na=False)`。45,211 × 17；原始字段、行序和值不变。
2. `row_id`：0 到 45,210 的原始数据行位置。第一条记录是 0；不是带表头的文本行号，更不是客户 ID。只作为 DataFrame index 或追踪列，绝不进入 X。
3. `split_manifest.csv`：两列 row_id/split，按 row_id 升序。每行恰好属于 train、val 或 test，互不重叠、完整覆盖。`split_indices.json` 保留 sklearn 两次拆分返回的数组顺序；loader 使用该顺序。不要依赖 CSV 按 split 排序。
4. `feature_policy.csv`：17 个原始字段 + row_id；11 个输入，5 个当前营销过程字段排除，y 目标，row_id 追踪。reviewer=pending 必须由真实成员更新。

任何变更都需要全组重新确认版本。不能为了改善模型分数重新划分。

## 精确拆分

```python
y = raw['y'].map({'no': 0, 'yes': 1})
ids = np.arange(len(raw))
dev, test = train_test_split(ids, test_size=.20, stratify=y, random_state=42)
train, val = train_test_split(dev, test_size=.25, stratify=y.iloc[dev], random_state=42)
```

大小：train=27,126，val=9,042，test=9,043。随机分层用于同一历史数据分布下的准备对照，不能表述为时间外推。验证脚本逐元素复算数组；不是仅比较 seed 或集合大小。

## 读取接口

从项目根目录执行，或在 Notebook 第一单元将项目根目录加入 sys.path：

```python
from src.data_contract import load_partition
X_train, y_train = load_partition('train')
X_val, y_val = load_partition('val')
# 仅 D 在实验规则冻结后的最终阶段执行：
# X_test, y_test = load_partition('test', allow_test=True)
```

X 保留原始 11 列类型与值，列顺序固定：age、job、marital、education、default、balance、housing、loan、pdays、previous、poutcome。X/y 的 index 都为同一 row_id，顺序与 split_indices 一致。y 是 int64，yes=1、no=0。`load_partition('test')` 默认报错；显式开关只是操作提醒，原始数据始终可读，不能当作安全隔离。

`load_partition` 会重新验证原始哈希与拆分。建模时不要 reset_index 后误把 row_id 加入模型。预测应以 row_id 对齐回原数据；不要单凭位置合并不同顺序的结果。

## 特殊值规则及责任

| 观察 | A 的处置 | 下游责任 |
| --- | --- | --- |
| pdays=-1 | 保留；此前未联系状态 | C 的 S 将状态与真实非负间隔分开；覆盖 -1/0/正数边界 |
| pdays=0 | 与 -1 区分，即使训练集中没有实例 | C 使用合成边界例验证转换，不删或合并 |
| job/education=unknown | 保留文字类别 | C 的 U 比较保留类别 vs 训练众数填补 |
| poutcome=unknown | 保留，不按 U 改动 | B/C 检查其与联系史的组合，不能直接等同从未联系 |
| 真正空值、pdays<-1、非法类别 | 预定 STOP 检查；本包无命中 | 先回 A 核查版本/解析，不能自动凑合修复 |
| 负余额、长尾、特征重复/标签冲突 | 保留并记录训练证据 | B/C 人工调查；不能从特征相同推定同一客户 |

开放 profiling、分位数及例行语义调查只对 train 生成。test 仅执行事先约定的字段、类别、数值域、覆盖检查；这些检查不用于挑选模型/处理方案/阈值/分组。

## 边界与后续

C 实现 `build_pipeline(use_s,use_u)` 四组；A 未代做。所有学习步骤只能在当前 fit 数据上学习，验证与测试只 transform/predict。开发使用 train；规则冻结后 D 可按手册重拟合 train+val 的 80%，再执行预先确定的 test 评估。`poutcome`、`previous` 与 S 的潜在冗余是要解释的限制，不能因为效果小而换范围。

D 负责统一模型、指标、阈值、组别和结果。B 负责真实的非显而易见发现及分层解释。A 的质量计数不替代 B 的发现，也不是模型性能结果。保留全部原始行，四组必须用同一行集、顺序和划分。

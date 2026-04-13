# fucai3d-research

[![License](https://img.shields.io/github/license/Aioneas/fucai3d-research)](./LICENSE)
[![Repo Size](https://img.shields.io/github/repo-size/Aioneas/fucai3d-research)](https://github.com/Aioneas/fucai3d-research)
[![Last Commit](https://img.shields.io/github/last-commit/Aioneas/fucai3d-research)](https://github.com/Aioneas/fucai3d-research/commits/main)
[![Stars](https://img.shields.io/github/stars/Aioneas/fucai3d-research?style=social)](https://github.com/Aioneas/fucai3d-research)

> 中国福利彩票 3D（福彩3D）历史数据工程、特征构建、walk-forward 回测、娱乐性推荐与 skill 封装项目。

---

## ⚠️ 重要声明（请先阅读）

本仓库仅用于：
- 数据工程实践
- 统计分析与回测方法展示
- 教育与研究归档

**不构成任何投注建议、投资建议或收益承诺。**

彩票具备显著随机性与长期负期望特征，任何推荐/模拟/排序都仅供娱乐参考。请理性娱乐，量力而行，远离沉迷。  
更多说明见 [`docs/DISCLAIMER.md`](./docs/DISCLAIMER.md)。

---

## 项目快照（Snapshot）

| 维度 | 数值 |
|---|---:|
| 官方接口全历史记录数 | **4597** |
| 全历史区间 | **2013-01-02 ~ 2026-04-12** |
| 两年样本记录数 | **702** |
| 特征列数 | **86** |
| 回测方式 | Walk-forward（样本外） |
| 测试集大小 | 500 期 |
| 最优参数 | window=360, half_life=120 |

---

## 回测核心结果（样本外）

> 测试集：`2024296 ~ 2026092`（500 期）

| 指标 | 结果 | 随机基线 |
|---|---:|---:|
| Exact Top1 | 0.00% | 0.10% |
| Exact Top5 | 0.60% | 0.50% |
| Exact Top10 | 1.60% | 1.00% |
| Exact Top20 | 3.40% | 2.00% |
| Exact Top50 | 5.20% | 5.00% |
| 组选 Top20 | 12.40% | - |
| 和值 Top3 | 21.20% | - |
| 跨度 Top3 | 43.20% | - |
| 组三/组六/豹子 Top1 | 74.80% | - |

**理性结论：** 结构层面的统计参考有一定信息量，但严格样本外下并未显示稳定、可持续、可依赖的精确命中优势。

---

## 数据资产（Data Assets）

### 1) 两年数据集（`data/2y/`）
- 区间：`2024-04-13 ~ 2026-04-13`
- 记录数：`702`

| 文件 | 说明 |
|---|---|
| [`history_official_2y_full.json`](./data/2y/history_official_2y_full.json) | 两年全字段历史 |
| [`history_official_2y_features.json`](./data/2y/history_official_2y_features.json) | 两年特征（JSON） |
| [`history_official_2y_features.csv`](./data/2y/history_official_2y_features.csv) | 两年特征（CSV） |
| [`history_official_2y_summary.json`](./data/2y/history_official_2y_summary.json) | 两年数据摘要 |

### 2) 全历史数据集（`data/all/`）
- 请求区间：`2004-01-01 ~ 2026-04-13`
- 当前官方接口实际可得：`2013-01-02 ~ 2026-04-12`
- 记录数：`4597`

| 文件 | 说明 |
|---|---|
| [`history_official_all_full.json`](./data/all/history_official_all_full.json) | 全历史全字段 |
| [`history_official_all_features.json`](./data/all/history_official_all_features.json) | 全历史特征（JSON） |
| [`history_official_all_features.csv`](./data/all/history_official_all_features.csv) | 全历史特征（CSV） |
| [`history_official_all_train.json`](./data/all/history_official_all_train.json) | 训练输入历史 |
| [`history_official_all_summary.json`](./data/all/history_official_all_summary.json) | 全历史数据摘要 |

### 3) 原始抓取转储（`data/raw/`）
用于复盘 browser 会话抓取过程：
- [`official_api_2y_browser_dump.txt`](./data/raw/official_api_2y_browser_dump.txt)
- [`official_api_all_browser_dump.txt`](./data/raw/official_api_all_browser_dump.txt)
- [`fetch_config_2y.json`](./data/raw/fetch_config_2y.json)

---

## 报告与输出（Reports）

| 文件 | 说明 |
|---|---|
| [`backtest_walkforward_report.md`](./reports/backtest_walkforward_report.md) | 回测结论摘要 |
| [`backtest_walkforward_summary.json`](./reports/backtest_walkforward_summary.json) | 回测完整指标 |
| [`backtest_latest500_predictions.jsonl`](./reports/backtest_latest500_predictions.jsonl) | 最近500期预测样本 |
| [`forecast_next7days_entertainment.md`](./reports/forecast_next7days_entertainment.md) | 未来7天娱乐推荐 |
| [`forecast_next7days_entertainment.json`](./reports/forecast_next7days_entertainment.json) | 7天推荐结构化结果 |

---

## 方法流程（Method Pipeline）

```mermaid
flowchart TD
    A[中国福彩网官方接口] --> B[browser会话抓取]
    B --> C[原始结构化转储]
    C --> D[历史数据解析与去重]
    D --> E[2Y数据集构建]
    D --> F[ALL数据集构建]
    E --> G[86列特征工程]
    F --> G
    G --> H[walk-forward 回测]
    H --> I[评估报告与指标]
    G --> J[7天娱乐性递推推荐]
    J --> K[可读报告/JSON输出]
```

---

## 快速开始（Quick Start）

> 环境：Python 3（脚本主要使用标准库）

```bash
# 1) 两年数据构建
python3 scripts/build_fucai3d_dataset.py

# 2) 全历史数据构建
python3 scripts/build_fucai3d_all_dataset.py

# 3) walk-forward 回测
python3 scripts/fucai3d_backtest_walkforward.py

# 4) 未来7天娱乐推荐
python3 scripts/fucai3d_forecast_next7days.py
```

---

## 目录结构

```text
fucai3d-research/
├── data/
│   ├── raw/       # browser 抓取原始转储
│   ├── 2y/        # 两年数据/特征/摘要
│   └── all/       # 全历史数据/特征/摘要
├── reports/       # 回测结果与推荐输出
├── scripts/       # 构建、回测、推荐脚本
├── skill/         # Minis skill 封装
├── docs/          # 免责声明等文档
├── LICENSE
└── README.md
```

---

## Skill 集成

仓库内包含 minis skill：
- [`skill/fucai3d-latest/SKILL.md`](./skill/fucai3d-latest/SKILL.md)

配套本地推荐器：
- [`scripts/recommender.py`](./scripts/recommender.py)

---

## 风险与解释边界

- 回测不是未来保证。
- 结构指标命中高于精确号码命中并不等于可稳定盈利。
- 切勿将本项目任何结果用于“必胜”叙事。
- 若仅用于娱乐，请严格设置预算上限与止损边界。

---

## 致谢

- 数据来源：中国福彩网公开接口（以抓取时返回结果为准）
- 项目定位：个人研究归档与工程实践

---

## License

[MIT](./LICENSE)

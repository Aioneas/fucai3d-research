# fucai3d-research

中国福利彩票 3D（福彩3D）公开历史数据整理、特征工程、walk-forward 回测、娱乐性推荐与技能封装项目。

> ⚠️ **重要提示 / 温馨提示**  
> 本仓库仅用于**数据工程、统计分析、回测实验、教育展示与个人研究归档**。  
> 彩票具备明显随机性与长期负期望特征，**不应被视为投资、稳定盈利工具或致富路径**。  
> 本仓库中的任何“推荐 / 模拟 / 预测 / 排名”都仅供娱乐参考，**不构成任何投注建议**。  
> **理性娱乐，量力而行，远离沉迷。**

---

## 项目内容

本项目包含：

- 中国福彩网官方接口抓取与整理
- 福彩3D 历史数据落库
- 两年训练集与全历史训练集构建
- 86 列特征工程
- walk-forward 样本外回测
- 未来 7 天娱乐性递推推荐
- Minis skill 封装（`fucai3d-latest`）

---

## 数据范围

### 两年数据集
- 区间：`2024-04-13 ~ 2026-04-13`
- 记录数：`702`
- 目录：[`data/2y/`](./data/2y/)

### 全历史数据集（当前官方接口可得）
- 请求区间：`2004-01-01 ~ 2026-04-13`
- 实际返回首期：`2013-01-02`
- 实际返回末期：`2026-04-12`
- 记录数：`4597`
- 目录：[`data/all/`](./data/all/)

说明：当前中国福彩网官方接口在本次抓取中实际能返回到 `2013-01-02`，更早历史如需补齐需换用其他数据源。

---

## 目录结构

```text
fucai3d-research/
├── data/
│   ├── raw/       # browser 抓取原始结构化转储
│   ├── 2y/        # 两年数据、特征与摘要
│   └── all/       # 全历史数据、特征与摘要
├── reports/       # 回测结果、预测输出、Markdown 报告
├── scripts/       # 数据构建、回测、预测、推荐脚本
├── skill/         # Minis skill 封装
└── docs/          # 说明、免责声明
```

---

## 主要文件

### 数据
- `data/2y/history_official_2y_full.json`：两年全字段历史
- `data/2y/history_official_2y_features.json`：两年 86 列特征
- `data/all/history_official_all_full.json`：全历史全字段
- `data/all/history_official_all_features.json`：全历史 86 列特征
- `data/all/history_official_all_train.json`：推荐器训练历史

### 报告
- `reports/backtest_walkforward_report.md`：walk-forward 回测报告
- `reports/backtest_walkforward_summary.json`：详细指标
- `reports/backtest_latest500_predictions.jsonl`：最近 500 期预测样本
- `reports/forecast_next7days_entertainment.md`：未来 7 天娱乐推荐

### 脚本
- `scripts/build_fucai3d_dataset.py`：两年数据构建
- `scripts/build_fucai3d_all_dataset.py`：全历史数据构建
- `scripts/fucai3d_backtest_walkforward.py`：回测脚本
- `scripts/fucai3d_forecast_next7days.py`：7天娱乐推荐脚本
- `scripts/recommender.py`：本地推荐器

---

## 回测摘要

基于 `4597` 期全历史、walk-forward 方式进行样本外验证：

- 测试集：`500` 期
- 最优参数：`window=360, half_life=120`

测试集结果：

- Exact Top1：`0/500 = 0.00%`
- Exact Top5：`3/500 = 0.60%`
- Exact Top10：`8/500 = 1.60%`
- Exact Top20：`17/500 = 3.40%`
- Exact Top50：`26/500 = 5.20%`
- 组选 Top20：`12.40%`
- 和值 Top3：`21.20%`
- 跨度 Top3：`43.20%`
- 组三/组六/豹子 Top1：`74.80%`

### 理性结论

历史统计与特征工程可以在**结构层面**提供一些娱乐性参考，但从严格样本外结果看，**并未证明存在稳定、可持续、足以依靠其长期盈利的优势**。

---

## 复现方式

本项目脚本主要基于 Python 标准库，可直接运行：

```bash
python3 scripts/build_fucai3d_dataset.py
python3 scripts/build_fucai3d_all_dataset.py
python3 scripts/fucai3d_backtest_walkforward.py
python3 scripts/fucai3d_forecast_next7days.py
```

说明：
- 当前设备环境下，shell 直连中国福彩网官方接口可能返回 `403`
- 因此原始抓取优先通过 browser 会话完成，再落地为本地转储

---

## 公开说明

本仓库为个人公开研究归档，包含：
- 数据整理成果
- 分析与回测成果
- 项目脚本
- skill 封装

未公开任何凭据、Cookie、令牌或其他敏感信息。

---

## License

MIT

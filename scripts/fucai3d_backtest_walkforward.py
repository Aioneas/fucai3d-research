#!/usr/bin/env python3
import json
import math
from collections import Counter
from pathlib import Path

FEATURES_PATH = Path('/var/minis/shared/fucai3d/history_official_all_features.json')
OUT_SUMMARY = Path('/var/minis/shared/fucai3d/backtest_walkforward_summary.json')
OUT_PRED = Path('/var/minis/shared/fucai3d/backtest_latest500_predictions.jsonl')
OUT_REPORT = Path('/var/minis/shared/fucai3d/backtest_walkforward_report.md')

REPEAT_TYPES = ['豹子', '组三', '组六']
SUM_VALUES = list(range(28))
SPAN_VALUES = list(range(10))


def bitmask(digits):
    m = 0
    for d in digits:
        m |= 1 << int(d)
    return m


def repeat_type_triplet(triplet):
    n = len(set(triplet))
    if n == 1:
        return '豹子'
    if n == 2:
        return '组三'
    return '组六'


def build_candidates():
    out = []
    for a in range(10):
        for b in range(10):
            for c in range(10):
                digits = (a, b, c)
                number = f'{a}{b}{c}'
                out.append({
                    'digits': digits,
                    'number': number,
                    'sorted_number': ''.join(map(str, sorted(digits))),
                    'sum': a + b + c,
                    'span': max(digits) - min(digits),
                    'repeat_type': repeat_type_triplet(digits),
                })
    return out


CANDIDATES = build_candidates()


def load_rows():
    rows = json.loads(FEATURES_PATH.read_text(encoding='utf-8'))
    out = []
    for r in rows:
        hot = tuple(int(x) for x in r['prev30_hot_digits'])
        cold = tuple(int(x) for x in r['prev30_cold_digits'])
        out.append({
            'issue': r['issue'],
            'date': r['date'],
            'number': r['number'],
            'sorted_number': ''.join(map(str, sorted(r['digits']))),
            'digits': tuple(r['digits']),
            'd1': int(r['d1']),
            'd2': int(r['d2']),
            'd3': int(r['d3']),
            'sum': int(r['sum']),
            'span': int(r['span']),
            'repeat_type': r['repeat_type'],
            'month': int(r['month']),
            'weekday_num': int(r['weekday_num']),
            'prev_sum': int(r['prev_sum']) if r['prev_sum'] is not None else 0,
            'prev_span': int(r['prev_span']) if r['prev_span'] is not None else 0,
            'prev_repeat_type': r['prev_repeat_type'] or 'NONE',
            'hot_digits': hot,
            'cold_digits': cold,
            'hot_mask': bitmask(hot),
            'cold_mask': bitmask(cold),
            'prev30_freqs': tuple(int(r[f'prev30_digit_{i}_freq']) for i in range(10)),
        })
    return out


def similarity(cur, past, age, half_life):
    sim = 0.05
    if cur['month'] == past['month']:
        sim += 0.35
    if cur['weekday_num'] == past['weekday_num']:
        sim += 0.35
    if cur['prev_repeat_type'] == past['prev_repeat_type']:
        sim += 1.10
    sim += 0.95 / (1.0 + abs(cur['prev_sum'] - past['prev_sum']))
    sim += 0.70 / (1.0 + abs(cur['prev_span'] - past['prev_span']))
    sim += 0.22 * ((cur['hot_mask'] & past['hot_mask']).bit_count())
    sim += 0.12 * ((cur['cold_mask'] & past['cold_mask']).bit_count())
    l1 = 0
    for a, b in zip(cur['prev30_freqs'], past['prev30_freqs']):
        l1 += abs(a - b)
    sim += 2.20 / (1.0 + l1 / 8.0)
    recency = 1.0 / (1.0 + age / float(half_life))
    return sim * recency


def rank_candidates(rows, idx, window, half_life):
    cur = rows[idx]
    start = max(0, idx - window)
    pos_counts = [[0.7] * 10 for _ in range(3)]
    repeat_counts = {k: 0.5 for k in REPEAT_TYPES}
    sum_counts = [0.15] * 28
    span_counts = [0.15] * 10

    for j in range(start, idx):
        past = rows[j]
        w = similarity(cur, past, idx - j, half_life)
        pos_counts[0][past['d1']] += w
        pos_counts[1][past['d2']] += w
        pos_counts[2][past['d3']] += w
        repeat_counts[past['repeat_type']] += w
        sum_counts[past['sum']] += w
        span_counts[past['span']] += w

    pos_logs = []
    for counts in pos_counts:
        total = sum(counts)
        pos_logs.append([math.log(c / total) for c in counts])
    total_repeat = sum(repeat_counts.values())
    repeat_logs = {k: math.log(v / total_repeat) for k, v in repeat_counts.items()}
    total_sum = sum(sum_counts)
    sum_logs = [math.log(v / total_sum) for v in sum_counts]
    total_span = sum(span_counts)
    span_logs = [math.log(v / total_span) for v in span_counts]

    recent_numbers = {rows[j]['number'] for j in range(max(0, idx - 30), idx)}
    hot_mask = cur['hot_mask']
    cold_mask = cur['cold_mask']

    scored = []
    for cand in CANDIDATES:
        a, b, c = cand['digits']
        score = pos_logs[0][a] + pos_logs[1][b] + pos_logs[2][c]
        score += 0.75 * repeat_logs[cand['repeat_type']]
        score += 0.20 * sum_logs[cand['sum']]
        score += 0.10 * span_logs[cand['span']]
        if cand['number'] in recent_numbers:
            score -= 1.15
        score += 0.035 * ((hot_mask >> a) & 1)
        score += 0.035 * ((hot_mask >> b) & 1)
        score += 0.035 * ((hot_mask >> c) & 1)
        score += 0.010 * ((cold_mask >> a) & 1)
        score += 0.010 * ((cold_mask >> b) & 1)
        score += 0.010 * ((cold_mask >> c) & 1)
        scored.append((score, cand['number'], cand['sorted_number']))
    scored.sort(key=lambda x: x[0], reverse=True)

    top50 = scored[:50]
    pred_pos = [max(range(10), key=lambda d: pos_logs[p][d]) for p in range(3)]
    top_sums = sorted(range(28), key=lambda s: sum_logs[s], reverse=True)[:3]
    top_spans = sorted(range(10), key=lambda s: span_logs[s], reverse=True)[:3]
    top_repeat = max(REPEAT_TYPES, key=lambda k: repeat_logs[k])
    return {
        'top50': top50,
        'pred_pos': pred_pos,
        'top_sums': top_sums,
        'top_spans': top_spans,
        'top_repeat': top_repeat,
    }


def empty_metrics(total):
    return {
        'total': total,
        'exact_top1': 0,
        'exact_top5': 0,
        'exact_top10': 0,
        'exact_top20': 0,
        'exact_top50': 0,
        'group_top20': 0,
        'sum_top3': 0,
        'span_top3': 0,
        'repeat_top1': 0,
        'position_hits': 0,
        'top1_two_pos_hits': 0,
        'top1_any_pos_hits': 0,
    }


def finalize_metrics(m):
    total = m['total']
    out = dict(m)
    for k in ['exact_top1', 'exact_top5', 'exact_top10', 'exact_top20', 'exact_top50', 'group_top20', 'sum_top3', 'span_top3', 'repeat_top1', 'top1_two_pos_hits', 'top1_any_pos_hits']:
        out[k + '_rate'] = round(m[k] / total, 6)
    out['position_digit_accuracy'] = round(m['position_hits'] / (total * 3), 6)
    return out


def evaluate(rows, start, end, config, save_predictions=False):
    m = empty_metrics(end - start)
    preds = []
    for idx in range(start, end):
        pred = rank_candidates(rows, idx, config['window'], config['half_life'])
        row = rows[idx]
        actual = row['number']
        actual_sorted = row['sorted_number']
        top_numbers = [x[1] for x in pred['top50']]
        top_sorted = [x[2] for x in pred['top50']]
        top1 = top_numbers[0]
        if actual == top_numbers[0]:
            m['exact_top1'] += 1
        if actual in top_numbers[:5]:
            m['exact_top5'] += 1
        if actual in top_numbers[:10]:
            m['exact_top10'] += 1
        if actual in top_numbers[:20]:
            m['exact_top20'] += 1
        if actual in top_numbers[:50]:
            m['exact_top50'] += 1
        if actual_sorted in top_sorted[:20]:
            m['group_top20'] += 1
        if row['sum'] in pred['top_sums']:
            m['sum_top3'] += 1
        if row['span'] in pred['top_spans']:
            m['span_top3'] += 1
        if row['repeat_type'] == pred['top_repeat']:
            m['repeat_top1'] += 1
        pos_hit = sum(1 for a, b in zip(row['digits'], pred['pred_pos']) if a == b)
        m['position_hits'] += pos_hit
        top1_pos_hits = sum(1 for a, b in zip(row['digits'], tuple(int(ch) for ch in top1)) if a == b)
        if top1_pos_hits >= 2:
            m['top1_two_pos_hits'] += 1
        if top1_pos_hits >= 1:
            m['top1_any_pos_hits'] += 1
        if save_predictions:
            preds.append({
                'issue': row['issue'],
                'date': row['date'],
                'actual': actual,
                'actual_sum': row['sum'],
                'actual_span': row['span'],
                'actual_repeat_type': row['repeat_type'],
                'pred_top10': top_numbers[:10],
                'pred_top3_sums': pred['top_sums'],
                'pred_top3_spans': pred['top_spans'],
                'pred_repeat_type': pred['top_repeat'],
                'pred_pos_digits': pred['pred_pos'],
            })
    return finalize_metrics(m), preds


def objective(m):
    return (
        m['exact_top20_rate'],
        m['exact_top10_rate'],
        m['exact_top5_rate'],
        m['group_top20_rate'],
        m['position_digit_accuracy'],
    )


def main():
    rows = load_rows()
    n = len(rows)
    val_size = 500
    test_size = 500
    val_start = n - val_size - test_size
    val_end = n - test_size
    test_start = n - test_size
    configs = [
        {'window': 180, 'half_life': 60},
        {'window': 180, 'half_life': 180},
        {'window': 360, 'half_life': 120},
        {'window': 360, 'half_life': 360},
        {'window': 720, 'half_life': 180},
        {'window': 720, 'half_life': 540},
        {'window': 1080, 'half_life': 360},
        {'window': 1440, 'half_life': 540},
    ]

    grid = []
    best = None
    best_cfg = None
    for cfg in configs:
        metrics, _ = evaluate(rows, val_start, val_end, cfg, save_predictions=False)
        grid.append({'config': cfg, 'validation_metrics': metrics})
        if best is None or objective(metrics) > objective(best):
            best = metrics
            best_cfg = cfg

    test_metrics, preds = evaluate(rows, test_start, n, best_cfg, save_predictions=True)
    recent1000_start = max(best_cfg['window'], n - 1000)
    recent1000_metrics, _ = evaluate(rows, recent1000_start, n, best_cfg, save_predictions=False)

    OUT_PRED.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in preds), encoding='utf-8')
    summary = {
        'dataset': {
            'records': n,
            'first_issue': rows[0]['issue'],
            'last_issue': rows[-1]['issue'],
            'first_date': rows[0]['date'],
            'last_date': rows[-1]['date'],
        },
        'split': {
            'validation_start_issue': rows[val_start]['issue'],
            'validation_end_issue': rows[val_end - 1]['issue'],
            'test_start_issue': rows[test_start]['issue'],
            'test_end_issue': rows[-1]['issue'],
            'validation_size': val_size,
            'test_size': test_size,
        },
        'grid_search': grid,
        'selected_config': best_cfg,
        'validation_best_metrics': best,
        'test_metrics': test_metrics,
        'recent1000_metrics': recent1000_metrics,
        'random_exact_baseline': {
            'exact_top1_rate': 0.001,
            'exact_top5_rate': 0.005,
            'exact_top10_rate': 0.01,
            'exact_top20_rate': 0.02,
            'exact_top50_rate': 0.05,
        },
        'prediction_file': str(OUT_PRED),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    test = test_metrics
    base = summary['random_exact_baseline']
    md = []
    md.append('# 福彩3D walk-forward 回测报告')
    md.append('')
    md.append(f'- 数据量：{n} 期')
    md.append(f'- 时间范围：{rows[0]["date"]} ~ {rows[-1]["date"]}')
    md.append(f'- 验证集：{val_size} 期（{rows[val_start]["issue"]} ~ {rows[val_end-1]["issue"]}）')
    md.append(f'- 测试集：{test_size} 期（{rows[test_start]["issue"]} ~ {rows[-1]["issue"]}）')
    md.append(f'- 选中参数：window={best_cfg["window"]}, half_life={best_cfg["half_life"]}')
    md.append('')
    md.append('## 测试集结果')
    md.append('')
    md.append(f'- Exact Top1：{test["exact_top1"]}/{test_size} = {test["exact_top1_rate"]:.2%}（随机基线 {base["exact_top1_rate"]:.2%}）')
    md.append(f'- Exact Top5：{test["exact_top5"]}/{test_size} = {test["exact_top5_rate"]:.2%}（随机基线 {base["exact_top5_rate"]:.2%}）')
    md.append(f'- Exact Top10：{test["exact_top10"]}/{test_size} = {test["exact_top10_rate"]:.2%}（随机基线 {base["exact_top10_rate"]:.2%}）')
    md.append(f'- Exact Top20：{test["exact_top20"]}/{test_size} = {test["exact_top20_rate"]:.2%}（随机基线 {base["exact_top20_rate"]:.2%}）')
    md.append(f'- Exact Top50：{test["exact_top50"]}/{test_size} = {test["exact_top50_rate"]:.2%}（随机基线 {base["exact_top50_rate"]:.2%}）')
    md.append(f'- 组选 Top20：{test["group_top20"]}/{test_size} = {test["group_top20_rate"]:.2%}')
    md.append(f'- 和值 Top3：{test["sum_top3"]}/{test_size} = {test["sum_top3_rate"]:.2%}')
    md.append(f'- 跨度 Top3：{test["span_top3"]}/{test_size} = {test["span_top3_rate"]:.2%}')
    md.append(f'- 组三/组六/豹子 Top1：{test["repeat_top1"]}/{test_size} = {test["repeat_top1_rate"]:.2%}')
    md.append(f'- 单个位置数字准确率：{test["position_digit_accuracy"]:.2%}')
    md.append(f'- Top1 至少命中 1 位：{test["top1_any_pos_hits"]}/{test_size} = {test["top1_any_pos_hits_rate"]:.2%}')
    md.append(f'- Top1 至少命中 2 位：{test["top1_two_pos_hits"]}/{test_size} = {test["top1_two_pos_hits_rate"]:.2%}')
    md.append('')
    md.append('## 结论')
    md.append('')
    md.append('- 该模型为基于历史窗口与相似特征的娱乐性 walk-forward 模拟。')
    md.append('- 若 Exact TopN 未显著高于随机基线，说明在严格样本外测试下没有稳定可利用优势。')
    md.append('- 结构类指标（和值/跨度/组三组六）通常比精确三位数组合更容易取得较高命中，但不等于具备真实预测能力。')
    OUT_REPORT.write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

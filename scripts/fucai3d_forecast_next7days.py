#!/usr/bin/env python3
import importlib.util
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

BACKTEST_SCRIPT = '/var/minis/workspace/fucai3d_backtest_walkforward.py'
OUT_JSON = Path('/var/minis/shared/fucai3d/forecast_next7days_entertainment.json')
OUT_MD = Path('/var/minis/shared/fucai3d/forecast_next7days_entertainment.md')
CFG = {'window': 360, 'half_life': 120}

spec = importlib.util.spec_from_file_location('f3d_backtest', BACKTEST_SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

rows = mod.load_rows()
sim_rows = [dict(r) for r in rows]
last_actual = sim_rows[-1]
start_date = date.fromisoformat(last_actual['date']) + timedelta(days=1)
last_issue = int(last_actual['issue'])


def topk_digits(counter, reverse=True, k=3):
    items = sorted(((d, counter.get(d, 0)) for d in range(10)), key=lambda kv: ((-kv[1], kv[0]) if reverse else (kv[1], kv[0])))
    return tuple(d for d, _ in items[:k])


def make_context_rows(sim_rows):
    window_rows = sim_rows[-30:]
    c = Counter()
    for r in window_rows:
        c.update(r['digits'])
    hot = topk_digits(c, True, 3)
    cold = topk_digits(c, False, 3)
    return c, hot, cold


def unique_group_from_top50(top50, limit=12):
    seen = set()
    out = []
    for _, _, group in top50:
        if group not in seen:
            seen.add(group)
            out.append(group)
            if len(out) >= limit:
                break
    return out

predictions = []
for step in range(7):
    d = start_date + timedelta(days=step)
    issue = str(last_issue + step + 1)
    freq_counter, hot, cold = make_context_rows(sim_rows)
    prev = sim_rows[-1]
    cur = {
        'issue': issue,
        'date': d.isoformat(),
        'month': d.month,
        'weekday_num': d.isoweekday(),
        'prev_sum': prev['sum'],
        'prev_span': prev['span'],
        'prev_repeat_type': prev['repeat_type'],
        'hot_digits': hot,
        'cold_digits': cold,
        'hot_mask': mod.bitmask(hot),
        'cold_mask': mod.bitmask(cold),
        'prev30_freqs': tuple(freq_counter.get(i, 0) for i in range(10)),
        'number': None,
        'sorted_number': None,
        'digits': (),
        'd1': None,
        'd2': None,
        'd3': None,
        'sum': None,
        'span': None,
        'repeat_type': None,
    }
    sim_rows.append(cur)
    pred = mod.rank_candidates(sim_rows, len(sim_rows) - 1, CFG['window'], CFG['half_life'])
    top10 = [x[1] for x in pred['top50'][:10]]
    top5 = top10[:5]
    group12 = unique_group_from_top50(pred['top50'], 12)
    primary = top10[0]
    digits = tuple(int(ch) for ch in primary)
    sim_rows[-1].update({
        'number': primary,
        'sorted_number': ''.join(map(str, sorted(digits))),
        'digits': digits,
        'd1': digits[0],
        'd2': digits[1],
        'd3': digits[2],
        'sum': sum(digits),
        'span': max(digits) - min(digits),
        'repeat_type': mod.repeat_type_triplet(digits),
    })
    predictions.append({
        'sim_issue': issue,
        'date': d.isoformat(),
        'weekday_num': d.isoweekday(),
        'prev_context_assumed_from': prev['issue'],
        'primary_pick': primary,
        'top5_exact': top5,
        'top10_exact': top10,
        'group12': group12,
        'sum_top3': pred['top_sums'],
        'span_top3': pred['top_spans'],
        'repeat_type_top1': pred['top_repeat'],
        'hot_digits_current_window': list(hot),
        'cold_digits_current_window': list(cold),
        'simulation_note': '第2天起采用前一天主推1号递推更新上下文，仅供娱乐参考。',
    })

summary = {
    'basis': '基于4597期官方历史、walk-forward最优参数(window=360, half_life=120)的递推娱乐推荐',
    'latest_actual_issue': last_actual['issue'],
    'latest_actual_date': last_actual['date'],
    'latest_actual_number': last_actual['number'],
    'selected_config': CFG,
    'predictions': predictions,
}
OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

lines = []
lines.append('# 福彩3D 未来7天娱乐推荐')
lines.append('')
lines.append(f'- 基础数据：4597期官方历史（{rows[0]["date"]} ~ {rows[-1]["date"]}）')
lines.append(f'- 最新实绩：第{last_actual["issue"]}期 {last_actual["date"]} 开奖号 {" ".join(last_actual["number"])}')
lines.append(f'- 模型参数：window={CFG["window"]}, half_life={CFG["half_life"]}')
lines.append('- 说明：第2天起按“前一天主推1号”递推上下文，越往后娱乐性越强。')
lines.append('')
for item in predictions:
    lines.append(f'## {item["date"]}（模拟第{item["sim_issue"]}期）')
    lines.append(f'- 主推1号：{" ".join(item["primary_pick"])}')
    lines.append(f'- 精选5组：' + ' / '.join(' '.join(x) for x in item['top5_exact']))
    lines.append(f'- 组选12码：' + ' / '.join(item['group12']))
    lines.append(f'- 和值Top3：' + ' / '.join(str(x) for x in item['sum_top3']))
    lines.append(f'- 跨度Top3：' + ' / '.join(str(x) for x in item['span_top3']))
    lines.append(f'- 组态倾向：{item["repeat_type_top1"]}')
    lines.append(f'- 近窗热号：' + ' '.join(str(x) for x in item['hot_digits_current_window']))
    lines.append(f'- 近窗冷号：' + ' '.join(str(x) for x in item['cold_digits_current_window']))
    lines.append('')
lines.append('> 仅基于历史统计与滚动相似期做娱乐性模拟，不构成预测建议。')
OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))

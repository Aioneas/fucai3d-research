#!/usr/bin/env python3
import argparse
import json
import os
import random
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_HISTORY = ROOT / 'data/all/history_official_all_train.json'
DEFAULT_SHARED_HISTORY = Path('/var/minis/shared/fucai3d/history.json')
HISTORY_PATH = Path(os.environ.get(
    'FUCAI3D_HISTORY_PATH',
    str(DEFAULT_REPO_HISTORY if DEFAULT_REPO_HISTORY.exists() else DEFAULT_SHARED_HISTORY),
))


def ensure_parent():
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_history():
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_history(records):
    ensure_parent()
    HISTORY_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')


def norm_issue(issue):
    digits = ''.join(ch for ch in str(issue) if ch.isdigit())
    if not digits:
        raise ValueError('issue must contain digits')
    return digits


def norm_date(date_str):
    value = str(date_str).strip().replace('/', '-')
    return datetime.fromisoformat(value[:10]).date().isoformat()


def norm_number(number):
    digits = ''.join(ch for ch in str(number) if ch.isdigit())
    if len(digits) != 3:
        raise ValueError('digits must be exactly 3 numbers')
    return digits


def sort_records(records):
    records.sort(key=lambda x: int(x['issue']))
    return records


def update_record(issue, date_str, number):
    issue = norm_issue(issue)
    date_str = norm_date(date_str)
    number = norm_number(number)
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    records = load_history()
    entry = {
        'issue': issue,
        'date': date_str,
        'number': number,
        'digits': [int(ch) for ch in number],
        'updated_at': now,
    }
    status = 'created'
    for idx, item in enumerate(records):
        if str(item.get('issue')) == issue:
            old_number = ''.join(str(d) for d in item.get('digits', [])) if item.get('digits') else str(item.get('number', ''))
            old_date = str(item.get('date', ''))
            if old_number == number and old_date == date_str:
                status = 'existing'
                entry = {
                    'issue': issue,
                    'date': date_str,
                    'number': number,
                    'digits': [int(ch) for ch in number],
                    'updated_at': item.get('updated_at', now),
                }
            else:
                status = 'corrected'
            records[idx] = entry
            sort_records(records)
            save_history(records)
            return {
                'status': status,
                'issue': issue,
                'date': date_str,
                'number': number,
                'history_size': len(records),
                'history_path': str(HISTORY_PATH),
            }
    records.append(entry)
    sort_records(records)
    save_history(records)
    return {
        'status': status,
        'issue': issue,
        'date': date_str,
        'number': number,
        'history_size': len(records),
        'history_path': str(HISTORY_PATH),
    }


def frequencies(window_records):
    counter = Counter()
    for item in window_records:
        number = item.get('number') or ''.join(str(d) for d in item.get('digits', []))
        for ch in str(number):
            if ch.isdigit():
                counter[int(ch)] += 1
    return {d: counter.get(d, 0) for d in range(10)}


def weighted_pick(rng, weights):
    total = sum(weights)
    if total <= 0:
        return rng.randrange(10)
    point = rng.random() * total
    acc = 0.0
    for idx, weight in enumerate(weights):
        acc += weight
        if point <= acc:
            return idx
    return 9


def make_weights(freq_map, mode):
    values = [freq_map[d] for d in range(10)]
    maxf = max(values) if values else 0
    meanf = (sum(values) / len(values)) if values else 0
    weights = []
    for d in range(10):
        f = freq_map[d]
        if mode == 'cold':
            w = 1.0 + (maxf - f) * 1.25
        elif mode == 'hot':
            w = 1.0 + f * 1.15
        else:
            w = 1.0 + abs(meanf - f) * 0.15
        weights.append(max(w, 0.1))
    return weights


def candidate_score(candidate, mode, freq_map, recent_numbers, recent_sums, recent_pairs, recent_triplets):
    tup = tuple(candidate)
    if tup in recent_numbers:
        return -9999
    score = 0.0
    s = sum(candidate)
    if s not in recent_sums:
        score += 2.2
    else:
        score -= 1.2
    pair_hits = 0
    for pair in ((candidate[0], candidate[1]), (candidate[1], candidate[2])):
        if pair in recent_pairs:
            pair_hits += 1
    score -= pair_hits * 0.9
    if tup not in recent_triplets:
        score += 0.8
    unique_digits = len(set(candidate))
    score += unique_digits * 0.2
    freq_sum = sum(freq_map[d] for d in candidate)
    if mode == 'cold':
        score -= freq_sum * 0.35
    elif mode == 'hot':
        score += freq_sum * 0.35
    else:
        score -= abs(freq_sum - (sum(freq_map.values()) / 10.0) * 3) * 0.08
    return score


def generate_group(rng, count, mode, freq_map, recent_records, used):
    recent_numbers = set()
    recent_sums = set()
    recent_pairs = set()
    recent_triplets = set()
    for item in recent_records:
        number = item.get('number') or ''.join(str(d) for d in item.get('digits', []))
        digits = tuple(int(ch) for ch in str(number) if ch.isdigit())
        if len(digits) != 3:
            continue
        recent_numbers.add(digits)
        recent_triplets.add(digits)
        recent_sums.add(sum(digits))
        recent_pairs.add((digits[0], digits[1]))
        recent_pairs.add((digits[1], digits[2]))
    weights = make_weights(freq_map, mode)
    picks = []
    attempts = 0
    while len(picks) < count and attempts < 800:
        attempts += 1
        cand = [weighted_pick(rng, weights) for _ in range(3)]
        tup = tuple(cand)
        if tup in used:
            continue
        if tup in recent_numbers and attempts < 500:
            continue
        score = candidate_score(cand, mode, freq_map, recent_numbers, recent_sums, recent_pairs, recent_triplets)
        if score < -20:
            continue
        picks.append((score, tup))
        used.add(tup)
    picks.sort(key=lambda x: x[0], reverse=True)
    result = [list(item[1]) for item in picks[:count]]
    while len(result) < count:
        cand = (rng.randrange(10), rng.randrange(10), rng.randrange(10))
        if cand in used or cand in recent_numbers:
            continue
        used.add(cand)
        result.append(list(cand))
    return result


def bundle(count):
    count = int(count)
    records = sort_records(load_history())
    window = records[-30:]
    freq_map = frequencies(window)
    sorted_hot = [d for d, _ in sorted(freq_map.items(), key=lambda kv: (-kv[1], kv[0]))]
    sorted_cold = [d for d, _ in sorted(freq_map.items(), key=lambda kv: (kv[1], kv[0]))]
    seed_material = ''.join(item.get('number', '') for item in records[-10:]) or 'fucai3d'
    seed = int.from_bytes(seed_material.encode('utf-8'), 'little') % (2 ** 32)
    rng = random.Random(seed ^ int(datetime.now(UTC).timestamp()))
    used = set()
    basic = generate_group(rng, max(count, 1), 'basic', freq_map, window, used)
    cold = generate_group(rng, 3, 'cold', freq_map, window, used)
    hot = generate_group(rng, 3, 'hot', freq_map, window, used)
    return {
        'history_path': str(HISTORY_PATH),
        'history_size': len(records),
        'window_size': len(window),
        'basic_recommendations': [' '.join(map(str, x)) for x in basic],
        'cold_preference': [' '.join(map(str, x)) for x in cold],
        'hot_mix': [' '.join(map(str, x)) for x in hot],
        'recent_30_frequency': {str(k): v for k, v in freq_map.items()},
        'hot_digits': sorted_hot[:5],
        'cold_digits': sorted_cold[:5],
        'note': '仅基于历史排除规则与简单频率偏好生成的娱乐推荐，不构成预测建议。',
    }


def main():
    parser = argparse.ArgumentParser(description='福彩3D本地历史与娱乐推荐工具')
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_update = sub.add_parser('update', help='写入或修正一期结果')
    p_update.add_argument('issue')
    p_update.add_argument('date')
    p_update.add_argument('digits')

    p_bundle = sub.add_parser('bundle', help='生成推荐与冷热统计')
    p_bundle.add_argument('count', nargs='?', default='5')

    args = parser.parse_args()
    if args.cmd == 'update':
        out = update_record(args.issue, args.date, args.digits)
    elif args.cmd == 'bundle':
        out = bundle(args.count)
    else:
        raise SystemExit('unknown command')
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

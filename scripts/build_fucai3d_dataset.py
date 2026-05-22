#!/usr/bin/env python3
import csv
import json
import os
import re
from collections import Counter, deque
from datetime import UTC, datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get('FUCAI3D_2Y_SOURCE', str(ROOT / 'data/raw/official_api_2y_browser_dump.txt')))
OUT_DIR = Path(os.environ.get('FUCAI3D_OUTPUT_DIR', str(ROOT / 'data/2y')))
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FULL = OUT_DIR / 'history_official_2y_full.json'
OUT_FEATURES = OUT_DIR / 'history_official_2y_features.json'
OUT_FEATURES_CSV = OUT_DIR / 'history_official_2y_features.csv'
OUT_TRAIN = OUT_DIR / 'history.json'
OUT_JSONL = OUT_DIR / 'history_official_2y_full.jsonl'
OUT_SUMMARY = OUT_DIR / 'history_official_2y_summary.json'

U_RE = re.compile(r'\\U([0-9A-Fa-f]{4})')
KV_RE = re.compile(r'^([A-Za-z0-9_]+)\s*=\s*(.*?)\s*;$')
PRIMES = {2, 3, 5, 7}
WEEK_MAP = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7, '天': 7}


def decode_u(text):
    text = str(text)
    return U_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


def parse_scalar(raw):
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return decode_u(raw[1:-1])
    if re.fullmatch(r'-?\d+', raw):
        return int(raw)
    return decode_u(raw)


def parse_offload(text):
    records = []
    in_result = False
    in_record = False
    in_prizegrades = False
    in_pg_obj = False
    record = None
    pg = None

    for line in text.splitlines():
        s = line.strip()
        if not in_result:
            if s.startswith('result: ('):
                in_result = True
            continue

        if not in_record:
            if s == '{':
                in_record = True
                record = {}
            elif s == ')':
                break
            continue

        if in_prizegrades:
            if not in_pg_obj:
                if s == '{':
                    in_pg_obj = True
                    pg = {}
                elif s in (');', ')'):
                    in_prizegrades = False
                continue
            else:
                if s in ('},', '}'):
                    record.setdefault('prizegrades', []).append(pg)
                    pg = None
                    in_pg_obj = False
                    continue
                m = KV_RE.match(s)
                if m:
                    key, raw = m.groups()
                    pg[key] = parse_scalar(raw)
                continue

        if s.startswith('prizegrades'):
            record['prizegrades'] = []
            in_prizegrades = True
            continue

        if s in ('},', '}'):
            records.append(record)
            record = None
            in_record = False
            continue

        m = KV_RE.match(s)
        if m:
            key, raw = m.groups()
            record[key] = parse_scalar(raw)

    return records


def repeat_type(digits):
    unique_count = len(set(digits))
    if unique_count == 1:
        return '豹子'
    if unique_count == 2:
        return '组三'
    return '组六'


def ac_value(digits):
    diffs = {abs(digits[i] - digits[j]) for i in range(3) for j in range(i + 1, 3)}
    return len(diffs) - 2


def build_feature_rows(records_full):
    rows = []
    prev = None
    window = deque(maxlen=30)

    for item in records_full:
        digits = item['digits']
        d1, d2, d3 = digits
        dt = date.fromisoformat(item['date'])
        total_sum = sum(digits)
        digit_counter = Counter(digits)
        prev30_counter = Counter()
        for w in window:
            prev30_counter.update(w['digits'])
        hot_prev30 = [d for d, _ in sorted(((d, prev30_counter.get(d, 0)) for d in range(10)), key=lambda kv: (-kv[1], kv[0]))[:3]]
        cold_prev30 = [d for d, _ in sorted(((d, prev30_counter.get(d, 0)) for d in range(10)), key=lambda kv: (kv[1], kv[0]))[:3]]
        prev30_sums = [sum(w['digits']) for w in window]
        prev30_spans = [max(w['digits']) - min(w['digits']) for w in window]
        prev30_repeat_counter = Counter(repeat_type(w['digits']) for w in window)
        route_counts = Counter(d % 3 for d in digits)
        odd_count = sum(d % 2 for d in digits)
        big_count = sum(d >= 5 for d in digits)
        prime_count = sum(d in PRIMES for d in digits)
        features = {
            'issue': item['issue'],
            'date': item['date'],
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'weekday_cn': item['week'],
            'weekday_num': WEEK_MAP.get(item['week'], 0),
            'day_of_year': dt.timetuple().tm_yday,
            'name': item['name'],
            'number': item['number'],
            'red': item['red'],
            'd1': d1,
            'd2': d2,
            'd3': d3,
            'digits': item['digits'],
            'sorted_digits': sorted(digits),
            'sorted_number': ''.join(str(x) for x in sorted(digits)),
            'unique_count': len(set(digits)),
            'repeat_type': repeat_type(digits),
            'has_pair': len(set(digits)) <= 2,
            'has_triple': len(set(digits)) == 1,
            'sum': total_sum,
            'sum_tail': total_sum % 10,
            'span': max(digits) - min(digits),
            'max_digit': max(digits),
            'min_digit': min(digits),
            'odd_count': odd_count,
            'even_count': 3 - odd_count,
            'big_count': big_count,
            'small_count': 3 - big_count,
            'prime_count': prime_count,
            'non_prime_count': 3 - prime_count,
            'route0_count': route_counts.get(0, 0),
            'route1_count': route_counts.get(1, 0),
            'route2_count': route_counts.get(2, 0),
            'route_pattern': ''.join(str(d % 3) for d in digits),
            'odd_even_pattern': ''.join('O' if d % 2 else 'E' for d in digits),
            'big_small_pattern': ''.join('B' if d >= 5 else 'S' for d in digits),
            'prime_pattern': ''.join('P' if d in PRIMES else 'N' for d in digits),
            'adjacent_consecutive_count': sum(1 for a, b in zip(digits, digits[1:]) if abs(a - b) == 1),
            'adjacent_same_count': sum(1 for a, b in zip(digits, digits[1:]) if a == b),
            'ac_value': ac_value(digits),
            'sales': item['sales'],
            'sales_wan': round(item['sales'] / 10000.0, 4),
            'has_video': bool(item['videoLink']),
            'detailsLink': item['detailsLink'],
            'videoLink': item['videoLink'],
            'prev_issue': prev['issue'] if prev else None,
            'prev_number': prev['number'] if prev else None,
            'prev_sum': sum(prev['digits']) if prev else None,
            'prev_span': (max(prev['digits']) - min(prev['digits'])) if prev else None,
            'prev_repeat_type': repeat_type(prev['digits']) if prev else None,
            'issue_gap_from_prev': (int(item['issue']) - int(prev['issue'])) if prev else None,
            'day_gap_from_prev': (dt - date.fromisoformat(prev['date'])).days if prev else None,
            'sales_delta_from_prev': (item['sales'] - prev['sales']) if prev else None,
            'same_position_hits_prev': sum(1 for a, b in zip(digits, prev['digits']) if a == b) if prev else None,
            'shared_digits_prev': len(set(digits) & set(prev['digits'])) if prev else None,
            'prev30_window_size': len(window),
            'prev30_hot_digits': hot_prev30,
            'prev30_cold_digits': cold_prev30,
            'prev30_sum_avg': round(sum(prev30_sums) / len(prev30_sums), 4) if prev30_sums else None,
            'prev30_span_avg': round(sum(prev30_spans) / len(prev30_spans), 4) if prev30_spans else None,
            'prev30_repeat_baozi': prev30_repeat_counter.get('豹子', 0),
            'prev30_repeat_zusan': prev30_repeat_counter.get('组三', 0),
            'prev30_repeat_zuliu': prev30_repeat_counter.get('组六', 0),
            'updated_at': item['updated_at'],
        }
        for n in range(10):
            features[f'digit_{n}_count'] = digit_counter.get(n, 0)
            features[f'prev30_digit_{n}_freq'] = prev30_counter.get(n, 0)
        rows.append(features)
        window.append(item)
        prev = item
    return rows


def main():
    if not SRC.exists():
        raise SystemExit(
            f'source dump not found: {SRC}\n'
            'Set FUCAI3D_2Y_SOURCE=/path/to/official_api_2y_browser_dump.txt if your dump lives elsewhere.'
        )
    text = SRC.read_text(encoding='utf-8')
    raw_records = parse_offload(text)
    if len(raw_records) < 600:
        raise SystemExit(f'parsed too few records: {len(raw_records)}')

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    full = []
    for r in raw_records:
        red = str(r.get('red', ''))
        digits = [int(x) for x in red.split(',') if str(x).strip() != '']
        if len(digits) != 3:
            continue
        date_raw = str(r.get('date', ''))
        date_clean = date_raw.split('(')[0]
        full.append({
            'source': 'cwl.gov.cn official API',
            'source_endpoint': 'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice',
            'name': str(r.get('name', '')),
            'issue': str(r.get('code', '')),
            'date': date_clean,
            'date_raw': date_raw,
            'week': str(r.get('week', '')),
            'number': ''.join(str(x) for x in digits),
            'red': red,
            'digits': digits,
            'blue': str(r.get('blue', '')),
            'blue2': str(r.get('blue2', '')),
            'sales': int(r.get('sales', 0) or 0),
            'poolmoney': str(r.get('poolmoney', '')),
            'content': str(r.get('content', '')),
            'addmoney': str(r.get('addmoney', '')),
            'addmoney2': str(r.get('addmoney2', '')),
            'msg': str(r.get('msg', '')),
            'z2add': str(r.get('z2add', '')),
            'm2add': str(r.get('m2add', '')),
            'detailsLink': 'https://www.cwl.gov.cn' + str(r.get('detailsLink', '')) if str(r.get('detailsLink', '')).startswith('/') else str(r.get('detailsLink', '')),
            'videoLink': 'https://www.cwl.gov.cn' + str(r.get('videoLink', '')) if str(r.get('videoLink', '')).startswith('/') else str(r.get('videoLink', '')),
            'prizegrades': r.get('prizegrades', []),
            'updated_at': now,
        })

    full = sorted({r['issue']: r for r in full}.values(), key=lambda x: int(x['issue']))
    features = build_feature_rows(full)
    train = [
        {
            'issue': r['issue'],
            'date': r['date'],
            'number': r['number'],
            'digits': r['digits'],
            'updated_at': r['updated_at'],
        }
        for r in full
    ]

    OUT_FULL.write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding='utf-8')
    OUT_FEATURES.write_text(json.dumps(features, ensure_ascii=False, indent=2), encoding='utf-8')
    OUT_TRAIN.write_text(json.dumps(train, ensure_ascii=False, indent=2), encoding='utf-8')
    OUT_JSONL.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in full), encoding='utf-8')

    csv_rows = []
    for row in features:
        flat = {}
        for k, v in row.items():
            if isinstance(v, (list, dict)):
                flat[k] = json.dumps(v, ensure_ascii=False)
            else:
                flat[k] = v
        csv_rows.append(flat)
    with OUT_FEATURES_CSV.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)

    summary = {
        'source': '中国福彩网官方接口',
        'endpoint': 'https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice',
        'lottery': '福彩3D',
        'range': {'dayStart': '2024-04-13', 'dayEnd': '2026-04-13'},
        'total_records': len(full),
        'first_issue': full[0]['issue'] if full else None,
        'last_issue': full[-1]['issue'] if full else None,
        'first_date': full[0]['date'] if full else None,
        'last_date': full[-1]['date'] if full else None,
        'train_history_path': str(OUT_TRAIN),
        'full_history_path': str(OUT_FULL),
        'features_path': str(OUT_FEATURES),
        'features_csv_path': str(OUT_FEATURES_CSV),
        'jsonl_path': str(OUT_JSONL),
        'feature_columns': len(csv_rows[0]) if csv_rows else 0,
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

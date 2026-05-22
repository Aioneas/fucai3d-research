#!/usr/bin/env python3
import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import build_fucai3d_dataset as base

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get('FUCAI3D_ALL_SOURCE', str(ROOT / 'data/raw/official_api_all_browser_dump.txt')))
OUT_DIR = Path(os.environ.get('FUCAI3D_ALL_OUTPUT_DIR', str(ROOT / 'data/all')))
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_FULL = OUT_DIR / 'history_official_all_full.json'
OUT_FEATURES = OUT_DIR / 'history_official_all_features.json'
OUT_FEATURES_CSV = OUT_DIR / 'history_official_all_features.csv'
OUT_TRAIN = OUT_DIR / 'history_official_all_train.json'
OUT_JSONL = OUT_DIR / 'history_official_all_full.jsonl'
OUT_SUMMARY = OUT_DIR / 'history_official_all_summary.json'


def main():
    if not SRC.exists():
        raise SystemExit(
            f'source dump not found: {SRC}\n'
            'Set FUCAI3D_ALL_SOURCE=/path/to/official_api_all_browser_dump.txt if your dump lives elsewhere.'
        )

    text = SRC.read_text(encoding='utf-8')
    raw_records = base.parse_offload(text)
    if len(raw_records) < 3000:
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
    features = base.build_feature_rows(full)
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
        'requested_dayStart': '2004-01-01',
        'requested_dayEnd': '2026-04-13',
        'actual_total_records': len(full),
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

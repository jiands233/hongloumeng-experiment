#!/usr/bin/env python3
"""Retrieve exactly one frozen Phase 2 F-ID as JSON."""
import argparse
import json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('id')
a=p.parse_args()
data=json.loads((Path(__file__).resolve().parents[1]/'foreshadowing.json').read_text())
row=next((r for r in data['evidence'] if r['id']==a.id),None)
if row is None:p.error('Unknown F-ID')
print(json.dumps(row,ensure_ascii=False,indent=2))

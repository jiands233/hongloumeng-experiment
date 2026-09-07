#!/usr/bin/env python3
"""Compact slices derived only from the frozen allowlisted reader.
Use: read_slice.py main 1 1 40 OR zhiyan 1 1 40.
Coverage records count delivered source lines / allowed note records, not understanding.
"""
from pathlib import Path
import argparse,subprocess,sys,json,hashlib
ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser();p.add_argument('layer',choices=['main','zhiyan']);p.add_argument('chapter',type=int,choices=range(1,81));p.add_argument('start',type=int);p.add_argument('end',type=int);p.add_argument('--log',required=True);a=p.parse_args()
if a.start<1 or a.end<a.start:p.error('invalid range')
raw=subprocess.check_output([sys.executable,str(ROOT/'scripts/read_canonical.py'),str(a.chapter),'--layer',a.layer],cwd=ROOT,text=True)
header,end=json.JSONDecoder().raw_decode(raw);rest=raw[end:].lstrip()
if a.layer=='main':items=rest.splitlines()
else:items=json.loads(rest.split('\n',1)[1])
if a.start>len(items)+1:p.error('start exceeds content')
stop=min(a.end,len(items));selected=items[a.start-1:stop]
print(json.dumps({'chapter':a.chapter,'layer':a.layer,'total':len(items),'shown':[a.start,stop],'qualification':header},ensure_ascii=False))
for i,item in enumerate(selected,a.start):
 if a.layer=='main':print(f'L{i}: {item}')
 else:print(f"#{i} {item['id']} | {item['current_text']}")
log=ROOT/'research/phase2/work'/a.log
if log.parent!=ROOT/'research/phase2/work':p.error('log must be a filename')
record={'chapter':a.chapter,'layer':a.layer,'start':a.start,'end':stop,'total':len(items),'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'note':'delivered only; operator must recover any truncated output'}
with log.open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')

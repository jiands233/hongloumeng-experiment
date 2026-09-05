#!/usr/bin/env python3
"""Allowlisted reader. No arbitrary paths, raw source, pending layer or excluded bodies."""
import argparse
import json
import sys
sys.dont_write_bytecode = True
from verify_canonical import ROOT, check_integrity


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('chapter',type=int,choices=range(1,81),metavar='1..80')
    parser.add_argument('--layer',choices=['main','zhiyan'],default='main')
    args=parser.parse_args()
    check_integrity()
    manifest=json.loads((ROOT/'canonical/metadata/chapter_manifest.json').read_text())
    row=manifest[args.chapter-1]
    print(json.dumps({'chapter':row['chapter'],'title':row['title'],'layer':args.layer,
          'completeness':row['completeness'],'contains_supplement':row['contains_supplement'],
          'confidence':row['confidence'],'notes':row['notes']},ensure_ascii=False,indent=2))
    if args.layer=='main':
        print((ROOT/row['path']).read_text())
    else:
        annotations=json.loads((ROOT/f'canonical/annotations/zhiyan/{args.chapter:03d}.json').read_text())
        allowed=[r for r in annotations if r['allowed_for_inference']=='commentary_only_explicit_opt_in']
        print('以下为本地标记的批语，仅作批语证据；不等于正文事实或批者鉴定。')
        print(json.dumps(allowed,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

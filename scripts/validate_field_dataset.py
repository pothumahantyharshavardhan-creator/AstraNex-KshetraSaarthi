"""Evaluate expert-labelled field predictions; never invent missing ground truth."""
from __future__ import annotations
import argparse, csv, json
from collections import Counter,defaultdict
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('csv_path')
    ap.add_argument('--output', default='validation/field_validation_report.json')
    args=ap.parse_args()
    p=Path(args.csv_path)
    rows=list(csv.DictReader(p.open(newline='',encoding='utf-8')))
    required={'sample_id','crop','true_label','predicted_label','confidence','split','location_state','capture_condition'}
    headers=set(rows[0].keys()) if rows else set(next(csv.reader(p.open(newline='',encoding='utf-8')), []))
    missing=required-headers
    if missing: raise SystemExit('Missing required columns: '+', '.join(sorted(missing)))
    if not rows:
        report={'status':'empty_dataset','samples':0,'accuracy':None,'balanced_accuracy':None,'coverage':None,'abstention_rate':None,'classes':[],'per_class':{},'confusion_matrix':{},'splits':{},'scope':'Expert-labelled field samples only. No synthetic labels are accepted as field validation.'}
        out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2)); return 0
    labels=sorted({r['true_label'] for r in rows})
    n=len(rows); correct=sum(r['true_label']==r['predicted_label'] for r in rows)
    per={}; matrix={x:{y:0 for y in labels} for x in labels}
    for r in rows: matrix[r['true_label']][r['predicted_label']]=matrix.get(r['true_label'],{}).get(r['predicted_label'],0)+1
    for lab in labels:
        tp=matrix[lab].get(lab,0); fp=sum(matrix[t].get(lab,0) for t in labels if t!=lab); fn=sum(matrix[lab].get(t,0) for t in labels if t!=lab)
        prec=tp/(tp+fp) if tp+fp else 0; rec=tp/(tp+fn) if tp+fn else 0; f1=2*prec*rec/(prec+rec) if prec+rec else 0
        per[lab]={'support':sum(matrix[lab].values()),'precision':round(prec,4),'recall':round(rec,4),'f1':round(f1,4)}
    balanced=sum(v['recall'] for v in per.values())/len(per) if per else 0
    abstained=sum(str(r['predicted_label']).strip().lower() in {'unknown','uncertain','abstain','needs_verification'} for r in rows)
    report={'status':'field_validated' if n else 'empty_dataset','samples':n,'accuracy':round(correct/n,4) if n else None,'balanced_accuracy':round(balanced,4) if per else None,'coverage':round((n-abstained)/n,4) if n else None,'abstention_rate':round(abstained/n,4) if n else None,'classes':labels,'per_class':per,'confusion_matrix':matrix,'splits':dict(Counter(r['split'] for r in rows)),'scope':'Expert-labelled field samples only. No synthetic labels are accepted as field validation.'}
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())

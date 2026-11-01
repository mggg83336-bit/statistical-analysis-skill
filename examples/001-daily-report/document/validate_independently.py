#!/usr/bin/env python3
"""Independent CSV-to-SQL audit. Does not import or execute case/run_case.py."""
import argparse, csv, hashlib, json, re, sqlite3
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


def amount_cents(value):
    s=value.strip().replace('CNY','').replace('¥','').replace('￥','').replace('元','').replace(',','').strip()
    if not s:return None
    v=Decimal(s)
    if not v.is_finite() or v < 0 or v*100 != (v*100).to_integral_value():raise ValueError('Invalid CNY amount')
    return int(v*100)


def date_iso(value):
    numbers=re.findall(r'\d+',value)
    if len(numbers)!=3:raise ValueError('Invalid date')
    a,b,c=map(int,numbers)
    y,m,d=(a,b,c) if len(numbers[0])==4 else (c,b,a)
    from datetime import date
    return date(y,m,d).isoformat()


def audit(case_dir):
    truth_path=case_dir/'truth.json';truth=json.loads(truth_path.read_text())
    files=sorted((case_dir/'raw_csv').glob('input_*.csv'))
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE raw(source TEXT PRIMARY KEY,file_index INT,row_no INT,oid TEXT,day TEXT,cents INT,paid INT,refunded INT,valid INT,signature TEXT,bucket TEXT)')
    hashes={};by_key=defaultdict(list)
    for file_index,path in enumerate(files,1):
        hashes[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.reader(f);next(reader)
            for row_no,values in enumerate(reader,2):
                assert len(values)==5
                oid,day,amount,pay,refund=[x.strip() for x in values]
                oid=oid.upper();day=date_iso(day);cents=amount_cents(amount)
                paid={'已支付':1,'paid':1,'付款成功':1,'待支付':0,'pending':0,'未付款':0}.get(pay)
                refunded={'未退款':0,'no':0,'否':0,'已退款':1,'yes':1,'是':1}.get(refund)
                valid=int(bool(oid) and cents is not None and paid is not None and refunded is not None)
                source=f'F{file_index}-R{row_no:02d}'
                key=oid or '__MISSING__'+source
                sig=json.dumps([day,cents,paid,refunded,'CNY'],ensure_ascii=False)
                db.execute('INSERT INTO raw VALUES(?,?,?,?,?,?,?,?,?,?,?)',(source,file_index,row_no,oid,day,cents,paid,refunded,valid,sig,key))
    # Database aggregation and window ranks are independent of the production dictionary reducer.
    sql='''WITH groups AS (
      SELECT bucket,COUNT(DISTINCT signature) AS variants,MIN(valid) AS complete FROM raw GROUP BY bucket
    ), ranked AS (
      SELECT raw.*,groups.variants,groups.complete,ROW_NUMBER() OVER(PARTITION BY bucket ORDER BY file_index,row_no) AS seq
      FROM raw JOIN groups USING(bucket)
    ) SELECT *, CASE
      WHEN variants>1 OR complete=0 THEN '待确认'
      WHEN seq>1 THEN '完全重复'
      WHEN day<>? THEN '非报表日'
      WHEN refunded=1 THEN '退款单列'
      WHEN paid<>1 THEN '待支付'
      ELSE '纳入日报' END AS disposition FROM ranked ORDER BY file_index,row_no'''
    rows=[dict(r) for r in db.execute(sql,(truth['report_date'],))]
    counts=Counter(r['disposition'] for r in rows)
    keep=[r for r in rows if r['disposition']=='纳入日报']
    checks=[]
    def check(name,actual,expected):
        passed=actual==expected
        checks.append({'name':name,'passed':passed,'actual':actual,'expected':expected})
    check('raw files',len(files),truth['raw_file_count'])
    check('all original rows assigned exactly once',len(rows),truth['raw_row_count'])
    check('unique original row locators',len({r['source'] for r in rows}),len(rows))
    check('row dispositions partition raw rows',sum(counts.values()),len(rows))
    check('disposition counts',dict(counts),truth['row_disposition_counts'])
    check('included unique IDs',sorted(r['oid'] for r in keep),truth['included_order_ids'])
    check('included IDs unique',len({r['oid'] for r in keep}),len(keep))
    check('included order count',len(keep),truth['included_unique_order_count'])
    check('included cents',sum(r['cents'] for r in keep),truth['included_amount_cents'])
    check('included rules',all(r['day']==truth['report_date'] and r['paid']==1 and r['refunded']==0 and r['valid']==1 and r['variants']==1 for r in keep),True)
    check('clean unique order count',sum(r['seq']==1 and r['complete']==1 and r['variants']==1 for r in rows),truth['clean_unique_order_count'])
    check('refund unique count',counts['退款单列'],truth['refund_unique_order_count'])
    check('refund cents',sum(r['cents'] for r in rows if r['disposition']=='退款单列'),truth['refund_amount_cents'])
    check('pending unique count',counts['待支付'],truth['pending_unique_order_count'])
    check('pending cents',sum(r['cents'] for r in rows if r['disposition']=='待支付'),truth['pending_amount_cents'])
    check('outside date count',counts['非报表日'],truth['outside_report_date_count'])
    check('outside date cents',sum(r['cents'] for r in rows if r['disposition']=='非报表日'),truth['outside_report_date_amount_cents'])
    check('duplicate excess count',counts['完全重复'],truth['duplicate_excess_row_count'])
    check('duplicate excess cents',sum(r['cents'] for r in rows if r['disposition']=='完全重复'),truth['duplicate_excess_amount_cents'])
    conflict=[r for r in rows if r['variants']>1]
    check('conflict IDs',sorted({r['oid'] for r in conflict}),truth['conflict_order_ids'])
    check('conflict raw rows',len(conflict),truth['conflict_raw_row_count'])
    check('missing key raw rows',sum(r['valid']==0 for r in rows),truth['missing_key_row_count'])
    check('naive baseline cents',sum(r['cents'] or 0 for r in rows),truth['naive_sum_contrast']['amount_cents'])
    check('naive baseline is explicitly wrong',truth['naive_sum_contrast']['amount_cents']!=sum(r['cents'] for r in keep),True)
    with (case_dir/'row_disposition.csv').open(encoding='utf-8-sig',newline='') as f:
        claimed={r['source_id']:r for r in csv.DictReader(f)}
    check('production disposition IDs',sorted(claimed),sorted(r['source'] for r in rows))
    check('every original row production disposition',[claimed[r['source']]['disposition'] for r in rows],[r['disposition'] for r in rows])
    sources=defaultdict(list)
    for r in rows:sources[r['oid'] or '__MISSING__'+r['source']].append(r['source'])
    mapped=json.loads((case_dir/'source_mappings.json').read_text())
    for m in mapped:
        k=m['order_id'] or '__MISSING__'+m['source_ids'][0]
        check('source mapping '+k,sorted(m['source_ids']),sorted(sources[k]))
    combos=defaultdict(lambda:{'count':0,'amount_cents':0,'order_ids':[]})
    for r in keep:
        combo='+'.join(sorted({chr(64+int(re.match(r'F(\d+)',s).group(1))) for s in sources[r['oid']]}))
        combos[combo]['count']+=1;combos[combo]['amount_cents']+=r['cents'];combos[combo]['order_ids'].append(r['oid'])
    for g in truth['report_fields']['source_combinations']:
        actual=combos[g['label']];actual['order_ids'].sort()
        check('source combination '+g['label'],actual,{k:g[k] for k in ['count','amount_cents','order_ids']})
    check('mutually exclusive source totals',sum(g['count'] for g in combos.values()),len(keep))
    check('mutually exclusive source cents',sum(g['amount_cents'] for g in combos.values()),sum(r['cents'] for r in keep))
    return {'passed':all(c['passed'] for c in checks),'method':'Independently read the three raw CSV files; normalize raw text then SQLite grouped signatures and ROW_NUMBER. No import or execution of production analysis.','truth_sha256':hashlib.sha256(truth_path.read_bytes()).hexdigest(),'raw_csv_sha256':hashes,'checks':checks,'independent_row_dispositions':[{k:r[k] for k in ['source','oid','day','cents','disposition']} for r in rows],'naive_baseline':'Wrong comparison only, not a success result.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,default=Path('work/episode-001/case'));p.add_argument('--out',type=Path,default=Path('work/episode-001/document/validation.json'));a=p.parse_args()
    result=audit(a.case);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':result['passed'],'checks':len(result['checks']),'out':str(a.out)},ensure_ascii=False))
    if not result['passed']:raise SystemExit(1)

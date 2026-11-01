#!/usr/bin/env python3
"""Generate the one-page synthetic report from truth.json.

Dependency: python-docx. Run from the project root, for example:
  python generate_report.py --truth case/truth.json --out outputs/report.docx
All displayed business numbers and dates come from the supplied truth file.
This renders validated results; it does not analyze new order data.
"""
import argparse, hashlib, json
from pathlib import Path
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Cm, Pt, RGBColor


def money(cents):
    sign='-' if cents<0 else ''
    a=abs(int(cents));return f'{sign}¥{a//100:,}.{a%100:02d}'


def generate(truth_path,out_path):
    t=json.loads(truth_path.read_text(encoding='utf-8'))
    fields=t['report_fields'];counts=t['row_disposition_counts']
    trace=next(x for x in fields['trace_examples'] if x['order_id']==t['included_order_ids'][0])
    conflict=fields['conflict_example']
    d=Document();s=d.sections[0]
    s.page_width=Inches(8.5);s.page_height=Inches(11)
    s.top_margin=Cm(1.7);s.bottom_margin=Cm(1.7);s.left_margin=Cm(2);s.right_margin=Cm(2)
    s.header_distance=Cm(.7);s.footer_distance=Cm(.7)
    def setfont(r,size=11,bold=False,color='000000'):
        r.font.name='Times New Roman';r.font.size=Pt(size);r.font.bold=bold;r.font.color.rgb=RGBColor.from_string(color)
        rf=r._r.get_or_add_rPr().find(qn('w:rFonts'))
        if rf is None:rf=OxmlElement('w:rFonts');r._r.get_or_add_rPr().insert(0,rf)
        for k,v in [('ascii','Times New Roman'),('hAnsi','Times New Roman'),('eastAsia','Songti SC')]:rf.set(qn('w:'+k),v)
        for k in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:rf.attrib.pop(qn('w:'+k),None)
    for name,size,bold in [('Normal',11,False),('Title',22,True),('Heading 1',13,True),('Heading 2',12,True)]:
        st=d.styles[name];st.font.name='Times New Roman';st.font.size=Pt(size);st.font.bold=bold;st.font.color.rgb=RGBColor(0,0,0)
        rf=OxmlElement('w:rFonts');rf.set(qn('w:ascii'),'Times New Roman');rf.set(qn('w:hAnsi'),'Times New Roman');rf.set(qn('w:eastAsia'),'Songti SC');st.element.get_or_add_rPr().append(rf)
        pf=st.paragraph_format;pf.line_spacing=1.12;pf.space_after=Pt(5)
        if name.startswith('Heading'):pf.space_before=Pt(9);pf.space_after=Pt(4);pf.keep_with_next=True
        if name=='Title':pf.space_after=Pt(5)
        ppr=st.element.find(qn('w:pPr'))
        if ppr is not None:
            for e in list(ppr):
                if e.tag in [qn('w:pBdr'),qn('w:shd')]:ppr.remove(e)
    texts={}
    def p(text,size=11,bold=False,style=None,key=None):
        x=d.add_paragraph(style=style);setfont(x.add_run(text),size,bold)
        if key:texts[key]=text
        return x
    def heading(text):return p(text,13,True,'Heading 1')
    p('可核对订单日报',22,True,'Title')
    p(f"报告日 {t['report_date']}  ｜  合成演示数据  订单快照非财务凭证",10,key='date_notice')
    p(t['metric_label'],12,True,key='metric_label')
    metric=d.add_paragraph();metric.paragraph_format.space_after=Pt(8)
    amount_text=money(t['included_amount_cents']);count_text=f"    {t['included_unique_order_count']} 单唯一订单"
    setfont(metric.add_run(amount_text),25,True);setfont(metric.add_run(count_text),12,True)
    texts['amount']=amount_text;texts['order_count']=count_text.strip()
    p(f"仅纳入订单日期为 {t['report_date']}、已支付且未退款、关键字段完整且无同ID冲突的唯一订单。",key='inclusion_rule')
    heading('原始记录处理去向')
    p(f"{t['raw_file_count']} 份快照共 {t['raw_row_count']} 行，每个原始行仅归入以下一类。",key='raw_range')
    labels=[('纳入日报','满足口径的保留行'),('完全重复','规范内容相同，不重复计金额'),('待确认','缺关键字段或同ID内容冲突'),('退款单列','已退款，不纳入主指标'),('待支付','尚未支付，不纳入主指标'),('非报表日','订单日期不同，不纳入主指标')]
    rows=[[name,str(counts[name]),why] for name,why in labels]
    rows.append(['合计',str(sum(counts.values())),'各类原始行回加，与输入行数一致'])
    table=d.add_table(rows=1,cols=3);table.alignment=WD_TABLE_ALIGNMENT.CENTER;table.autofit=False
    widths=[3.3,2.5,11.79]
    for col,w in zip(table.columns,widths):col.width=Cm(w)
    for cell,txt in zip(table.rows[0].cells,['处理去向','原始行数','处理原则']):cell.text=txt
    for row in rows:
        for cell,txt in zip(table.add_row().cells,row):cell.text=txt
    pr=table._tbl.tblPr;borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    pr.append(borders);mar=OxmlElement('w:tblCellMar')
    for side,val in [('top',65),('bottom',65),('left',90),('right',90)]:
        e=OxmlElement('w:'+side);e.set(qn('w:w'),str(val));e.set(qn('w:type'),'dxa');mar.append(e)
    pr.append(mar)
    for i,row in enumerate(table.rows):
        row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        if i==0:row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for j,(cell,w) in enumerate(zip(row.cells,widths)):
            cell.width=Cm(w);cell.vertical_alignment=WD_ALIGN_VERTICAL.CENTER
            sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'243D50' if i==0 else ('F3F6F8' if i%2==0 else 'FFFFFF'));cell._tc.get_or_add_tcPr().append(sh)
            for para in cell.paragraphs:
                para.alignment=WD_ALIGN_PARAGRAPH.CENTER if j==1 else WD_ALIGN_PARAGRAPH.LEFT
                para.paragraph_format.line_spacing=1.05;para.paragraph_format.space_after=Pt(0)
                for r in para.runs:setfont(r,11,i==0 or i==len(table.rows)-1,'FFFFFF' if i==0 else '000000')
    heading('异常摘要')
    conflict_amounts=' 与 '.join(money(r['amount_cents']) for r in conflict['records'])
    p(f"{conflict['order_id']} 的快照金额为 {conflict_amounts}，{t['conflict_raw_row_count']} 行均待确认，不选最新；另 {t['missing_key_row_count']} 行缺关键字段，合计 {t['exception_raw_row_count']} 行待确认。退款 {t['refund_unique_order_count']} 单共 {money(t['refund_amount_cents'])} 单列，未计入主金额。",key='exceptions')
    heading('源行追溯一例')
    sources='；'.join(f"{r['file']}／{r['sheet']}第{r['row']}行" for r in trace['source_records'])
    p(f"{trace['order_id']}  {money(trace['amount_cents'])}：{sources}。规范内容相同，仅计 {int(trace['counted_once'])} 笔；来源定位全部保留。",key='trace')
    counts_per_file='、'.join(str(x['data_row_count']) for x in fields['raw_file_rows'])
    p(f"数据范围：{t['raw_file_count']} 份合成快照，分别含 {counts_per_file} 行，币种均为 {t['currency']}。同ID内容完全一致才去重；冲突或缺字段待确认。该金额不是财务收入或税务结论。",key='scope')
    d.core_properties.title='可核对订单日报';d.core_properties.subject='合成订单快照的可核对日报';d.core_properties.author=''
    out_path.parent.mkdir(parents=True,exist_ok=True);d.save(out_path)
    return {'truth_sha256':hashlib.sha256(truth_path.read_bytes()).hexdigest(),'business_text':texts,'out':str(out_path)}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--truth',type=Path,default=Path('work/episode-001/case/truth.json'));ap.add_argument('--out',type=Path,default=Path('outputs/第001期_可核对日报.docx'));ap.add_argument('--facts-out',type=Path,default=Path('work/episode-001/document/report_facts.json'));a=ap.parse_args()
    facts=generate(a.truth,a.out);a.facts_out.parent.mkdir(parents=True,exist_ok=True);a.facts_out.write_text(json.dumps(facts,ensure_ascii=False,indent=2));print(str(a.out))

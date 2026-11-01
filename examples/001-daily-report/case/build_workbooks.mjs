import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const here = path.dirname(fileURLToPath(import.meta.url));
const outputDir = process.argv[2] ? path.resolve(process.argv[2]) : here;
const payload = JSON.parse(await fs.readFile(path.join(here, 'workbook_payload.json'), 'utf8'));
await fs.mkdir(outputDir, {recursive:true});
const previews = path.join(here, 'previews');
await fs.mkdir(previews,{recursive:true});
const log = [];
const colors = {ink:'#273C2F',green:'#49614F',pale:'#ECF1E8',line:'#D7DFD2',amber:'#FFF0D9',red:'#A54632'};
const font = 'Arial';
function formatBase(sheet, range, widths) {
  sheet.showGridLines = false;
  const r=sheet.getRange(range);
  r.format.font={name:font,size:11,color:colors.ink};
  r.format.verticalAlignment='center';
  r.format.rowHeight=25;
  r.format.wrapText=false;
  widths.forEach((width,i)=>sheet.getRangeByIndexes(0,i,1,1).format.columnWidthPx=width);
}
function header(sheet,range,fill=colors.green) {
  sheet.getRange(range).format={fill,font:{name:font,size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:30};
}
function stripes(sheet,start,end,lastCol){
  sheet.getRange(`A${start}:${lastCol}${end}`).format.fill='#FFFFFF';
  for(let row=start;row<=end;row+=2) sheet.getRange(`A${row}:${lastCol}${row}`).format.fill='#F1F4ED';
}
async function render(wb,sheetName,range,filename){
  const img=await wb.render({sheetName,range,scale:1.7,format:'png'});
  await fs.writeFile(path.join(previews,filename),new Uint8Array(await img.arrayBuffer()));
  log.push({event:'render',sheet:sheetName,range,file:filename});
}
async function save(wb,filename){
  const blob=await SpreadsheetFile.exportXlsx(wb);
  await blob.save(path.join(outputDir,filename));
  const inspectDir=path.join(here,'export-inspects');
  await fs.mkdir(inspectDir,{recursive:true});
  try { await fs.rename(path.join(outputDir,filename+'.inspect.ndjson'),path.join(inspectDir,filename+'.inspect.ndjson')); }
  catch (error) { if(error.code!=='ENOENT') throw error; }
  log.push({event:'export',file:filename});
}

for (let i=0;i<3;i++){
  const raw=payload.raw.files[i], wb=Workbook.create(), s=wb.worksheets.add(raw.sheet);
  s.getRange('A1:E11').values=[raw.headers,...raw.rows];
  formatBase(s,'A1:E13',[165,180,150,130,130]);
  header(s,'A1:E1',['#596C60','#806D57','#607782'][i]);
  s.getRange('A13').values=[['全部为合成演示数据。金额与日期保留原始文本格式。']];
  s.getRange('A13:E13').format.font={name:font,size:10,color:'#677668',italic:true};
  s.freezePanes.freezeRows(1);
  stripes(s,2,11,'E');
  wb.recalculate();
  await render(wb,raw.sheet,'A1:E13',['input_a.png','input_b.png','input_c.png'][i]);
  await save(wb,raw.filename);
}

const wb=Workbook.create();
const summary=wb.worksheets.add('日报概览');
const detail=wb.worksheets.add('标准明细');
const exceptions=wb.worksheets.add('异常原始');
const detailStart=5, detailEnd=detailStart+payload.clean.length-1;
const exceptionStart=5, exceptionEnd=exceptionStart+payload.exceptions.length-1;
formatBase(summary,'A1:D23',[415,175,28,490]);
summary.tabColor=colors.green;
summary.getRange('A2').values=[['10月31日订单日报']];
summary.getRange('A2:D2').format.font={name:font,size:16,bold:true,color:colors.ink};
summary.getRange('A2:D2').format.rowHeight=32;
summary.getRange('A3').values=[['报表日期']];
summary.getRange('B3').values=[[new Date('2026-10-31T00:00:00Z')]];
summary.getRange('B3').setNumberFormat('yyyy-mm-dd');
summary.getRange('B3').format.fill=colors.amber;
summary.getRange('D3').values=[['全部为合成演示数据 · CNY']];
summary.getRange('A5:A16').values=[['纳入日报订单金额（演示口径）'],['纳入日报唯一订单数'],[''],['退款单列金额'],['退款唯一订单数'],[''],['原始记录行数'],['完全重复多余行'],['同ID冲突订单数'],['待确认原始行'],['待支付订单数'],['非报表日订单数']];
summary.getRange('B5').formulas=[[`=ROUND(SUM('标准明细'!G${detailStart}:G${detailEnd}),2)`]];
summary.getRange('B6').formulas=[[`=COUNTIFS('标准明细'!F${detailStart}:F${detailEnd},"纳入日报")`]];
summary.getRange('B8').formulas=[[`=SUMIFS('标准明细'!C${detailStart}:C${detailEnd},'标准明细'!F${detailStart}:F${detailEnd},"退款单列")`]];
summary.getRange('B9').formulas=[[`=COUNTIFS('标准明细'!F${detailStart}:F${detailEnd},"退款单列")`]];
summary.getRange('B11').values=[[payload.truth.raw_row_count]];
summary.getRange('B12').formulas=[[`=SUM('标准明细'!H${detailStart}:H${detailEnd})-COUNTA('标准明细'!A${detailStart}:A${detailEnd})`]];
summary.getRange('B13').values=[[payload.truth.conflict_order_count]];
summary.getRange('B14').formulas=[[`=COUNTA('异常原始'!A${exceptionStart}:A${exceptionEnd})`]];
summary.getRange('B15').formulas=[[`=COUNTIFS('标准明细'!F${detailStart}:F${detailEnd},"待支付")`]];
summary.getRange('B16').formulas=[[`=COUNTIFS('标准明细'!F${detailStart}:F${detailEnd},"非报表日")`]];
summary.getRange('A5:B6').format.fill=colors.pale;
summary.getRange('A5:B6').format.rowHeight=34;
summary.getRange('A5:B5').format.font={name:font,size:16,bold:true,color:colors.ink};
summary.getRange('B5').setNumberFormat('"¥"#,##0.00');
summary.getRange('B8').setNumberFormat('"¥"#,##0.00');
summary.getRange('B6:B16').format.horizontalAlignment='right';
summary.getRange('B5:B16').format.horizontalAlignment='right';
summary.getRange('B6:B6').setNumberFormat('0');
summary.getRange('D5').values=[['本期处理规则']];
summary.getRange('D5').format.font={name:font,size:13,bold:true,color:colors.green};
summary.getRange('D7:D10').values=[['统一字段、日期与金额文本'],['同ID完全相同，保留一份和全部来源'],['同ID内容冲突，整单待确认，不擅选最新'],['只纳入报表日、已支付、未退款的有效唯一订单']];
summary.getRange('D12').values=[['每条原始记录都有去向，详情见随附CSV。']];
summary.getRange('D14').values=[['OD-009：两份快照金额为500与550元']];
summary.getRange('D15').values=[['整单待确认。两行均不纳入本期金额。']];
summary.getRange('D14:D15').format.font={name:font,size:11,color:colors.red};
summary.getRange('A18').values=[['错误对照：原始快照金额直接相加']];
summary.getRange('B18').values=[[payload.truth.naive_sum_contrast.amount_cents/100]];
summary.getRange('B18').setNumberFormat('"¥"#,##0.00');
summary.getRange('A18:B18').format.fill='#FBE9DF';
summary.getRange('A19').values=[['故意错误口径，忽略重复、状态、日期及待确认行。']];
summary.getRange('A19:D19').format.font={name:font,size:10,color:colors.red};
summary.getRange('A21').values=[['本演示按订单快照口径计算，不作财务收入或税务结论。']];
summary.getRange('A21:D21').format.font={name:font,size:10,color:'#68766A',italic:true};

formatBase(detail,`A1:I${detailEnd+2}`,[115,125,115,100,95,130,135,100,265]);
detail.getRange('A2').values=[['标准订单明细']];
detail.getRange('A2:I2').format.font={name:font,size:16,bold:true,color:colors.ink};
detail.getRange('A3').values=[[`规范化后${payload.clean.length}条完整、无同ID冲突的唯一订单。所有合并来源均保留。`]];
detail.getRange('A3:I3').format.font={name:font,size:10,color:'#68766A',italic:true};
detail.getRange('A4:I4').values=[['订单ID','订单日期','金额(CNY)','支付状态','退款状态','去向','纳入日报金额','来源记录数','全部来源编号']];
header(detail,'A4:I4');
const detailValues=payload.clean.map(r=>[r.order_id,new Date(r.order_date+'T00:00:00Z'),r.amount_cents/100,r.payment_status,r.refund_status,null,null,r.source_ids.length,r.source_ids.join(' / ')]);
detail.getRange(`A${detailStart}:I${detailEnd}`).values=detailValues;
detail.getRange(`B${detailStart}:B${detailEnd}`).setNumberFormat('yyyy-mm-dd');
detail.getRange(`C${detailStart}:C${detailEnd}`).setNumberFormat('#,##0.00');
detail.getRange(`G${detailStart}:G${detailEnd}`).setNumberFormat('#,##0.00');
detail.getRange(`F${detailStart}`).formulas=[[`=IF(OR(A${detailStart}="",B${detailStart}="",C${detailStart}="",NOT(ISNUMBER(C${detailStart})),C${detailStart}<0),"待确认",IF(B${detailStart}<>'日报概览'!$B$3,"非报表日",IF(E${detailStart}="已退款","退款单列",IF(D${detailStart}<>"已支付","待支付","纳入日报"))))`]];
detail.getRange(`F${detailStart}:F${detailEnd}`).fillDown();
detail.getRange(`G${detailStart}`).formulas=[[`=IF(F${detailStart}="纳入日报",C${detailStart},0)`]];
detail.getRange(`G${detailStart}:G${detailEnd}`).fillDown();
detail.getRange(`C${detailStart}:C${detailEnd}`).format.horizontalAlignment='right';
detail.getRange(`G${detailStart}:H${detailEnd}`).format.horizontalAlignment='right';
detail.getRange(`D${detailStart}:F${detailEnd}`).format.horizontalAlignment='center';
detail.getRange(`H${detailStart}:H${detailEnd}`).format.horizontalAlignment='center';
stripes(detail,detailStart,detailEnd,'I');
detail.getRange(`F${detailStart}:F${detailEnd}`).conditionalFormats.add('containsText',{text:'待确认',format:{fill:colors.amber,font:{color:colors.red,bold:true}}});
detail.getRange(`F${detailStart}:F${detailEnd}`).conditionalFormats.add('containsText',{text:'退款',format:{fill:'#FBE9DF',font:{color:colors.red}}});
detail.freezePanes.freezeRows(4);
detail.freezePanes.freezeColumns(1);

formatBase(exceptions,`A1:H${exceptionEnd+2}`,[115,120,150,145,110,100,330,180]);
exceptions.getRange('A2').values=[['异常原始记录']];
exceptions.getRange('A2:H2').format.font={name:font,size:16,bold:true,color:colors.ink};
exceptions.getRange('A3').values=[[`${payload.exceptions.length}行均待确认。原始文本保留，不自动补金额或选择冲突快照。`]];
exceptions.getRange('A3:H3').format.font={name:font,size:10,color:'#68766A',italic:true};
exceptions.getRange('A4:H4').values=[['来源编号','原始订单ID','原始日期','原始金额文本','原支付状态','原退款状态','待确认原因','文件与行']];
header(exceptions,'A4:H4','#856A4E');
exceptions.getRange(`A${exceptionStart}:H${exceptionEnd}`).values=payload.exceptions.map(r=>{const vals=Object.values(r.original);return [r.source_id,vals[0],vals[1],vals[2],vals[3],vals[4],r.reason,`${r.source_file} #${r.source_row}`];});
stripes(exceptions,exceptionStart,exceptionEnd,'H');
exceptions.freezePanes.freezeRows(4);

wb.recalculate();
const baseline=summary.getRange('B5').values[0][0];
if(Math.abs(Number(baseline)-payload.truth.included_amount_cents/100)>0.000001) throw new Error(`Baseline mismatch: ${baseline}`);
const original=detail.getRange('C5').values[0][0];
detail.getRange('C5').values=[[Number(original)+1]];
wb.recalculate();
const changed=summary.getRange('B5').values[0][0];
if(Math.abs(Number(changed)-Number(baseline)-1)>0.000001) throw new Error(`Recalc failed ${changed}`);
detail.getRange('C5').values=[[null]];
wb.recalculate();
const blankAmountTotal=summary.getRange('B5').values[0][0];
const blankAmountDisposition=detail.getRange('F5').values[0][0];
if(blankAmountDisposition!=='待确认'||Math.abs(Number(blankAmountTotal)-(Number(baseline)-Number(original)))>0.000001) throw new Error('Blank amount incorrectly included');
detail.getRange('C5').values=[[original]];
wb.recalculate();
log.push({event:'formula_input_change_test',input:'标准明细!C5',baseline,changed,expectedDelta:1,blankAmountTotal,blankAmountDisposition,restored:summary.getRange('B5').values[0][0],passed:true});
const inspect=await wb.inspect({kind:'table',range:'日报概览!A3:B18',include:'values,formulas',tableMaxRows:16,tableMaxCols:2,maxChars:7000});
await fs.writeFile(path.join(here,'artifact-inspect.ndjson'),inspect.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:100},summary:'formula error scan'});
await fs.writeFile(path.join(here,'artifact-errors.ndjson'),errors.ndjson);
await render(wb,'日报概览','A1:D23','summary.png');
await render(wb,'标准明细',`A1:I${detailEnd+1}`,'detail.png');
await render(wb,'异常原始',`A1:H${exceptionEnd+2}`,'exceptions.png');
await save(wb,'04_订单日报.xlsx');
await fs.writeFile(path.join(here,'artifact-run-log.json'),JSON.stringify({executed_at:new Date().toISOString(),events:log},null,2));
console.log(JSON.stringify({outputs:4,baseline,changed,previews,log:log.length}));

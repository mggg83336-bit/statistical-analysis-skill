"""Real local MarkItDown conversion, with outbound socket connections blocked."""
from pathlib import Path
import hashlib, importlib.metadata, json, platform, re, socket, time
from markitdown import MarkItDown

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def forbidden(*args,**kwargs):raise RuntimeError('Network connection blocked in this local-only demonstration')
socket.socket.connect=forbidden
socket.create_connection=forbidden
md=MarkItDown(enable_plugins=False)
out=HERE/'converted';out.mkdir(exist_ok=True)
records=[]
for name in ['report.docx','report-text.pdf','report-scan.pdf']:
    p=HERE/'inputs'/name;start=time.perf_counter()
    try:
        result=md.convert_local(str(p))
        content=result.markdown if hasattr(result,'markdown') else result.text_content
        error=None
    except Exception as e:
        content='';error=f'{type(e).__name__}: {e}'
    elapsed=time.perf_counter()-start
    output=out/(p.name.replace('.','-')+'.md');output.write_text(content,encoding='utf-8')
    row={'input':f'inputs/{name}','input_sha256':sha(p),'output':f'converted/{output.name}','output_sha256':sha(output),'text_characters':len(content.strip()),'elapsed_seconds':round(elapsed,6),'contains_amount_3041_20':bool(re.search(r'3,?041\.20',content)),'contains_order_OD001':'OD-001' in content,'has_markdown_table_separator':bool(re.search(r'\|\s*:?-{2,}',content)),'error':error}
    records.append(row)
    print(json.dumps(row,ensure_ascii=False),flush=True)
report={'tool':'Microsoft MarkItDown','package_version':importlib.metadata.version('markitdown'),'python':platform.python_version(),'platform':platform.system()+' '+platform.machine(),'local_files_only':True,'outbound_network_blocked':True,'plugins_enabled':False,'llm_client_supplied':False,'azure_conversion_enabled':False,'synthetic':True,'records':records,'limits':'This demonstrates three specific files in the basic local route, not arbitrary file formats, layout fidelity, OCR, or LLM understanding.'}
(HERE/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert records[0]['error'] is None and records[0]['contains_amount_3041_20'] and records[0]['has_markdown_table_separator']
assert records[1]['error'] is None and records[1]['contains_amount_3041_20']
assert not records[2]['contains_amount_3041_20'] and records[2]['text_characters']==0

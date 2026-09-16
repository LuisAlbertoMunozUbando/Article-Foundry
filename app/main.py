from __future__ import annotations
import json, os, re, shutil, sqlite3, subprocess, uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent.parent
DB=Path(os.getenv('ARTICLE_FOUNDRY_DB', ROOT/'data/article_foundry.db'))
ART=Path(os.getenv('ARTICLE_FOUNDRY_ARTIFACTS', ROOT/'data/artifacts'))
LLM=os.getenv('ARTICLE_FOUNDRY_LLM_BASE_URL','http://127.0.0.1:8001/v1').rstrip('/')
KEY=os.getenv('ARTICLE_FOUNDRY_LLM_API_KEY','local')
MODEL=os.getenv('ARTICLE_FOUNDRY_LLM_MODEL','')
DB.parent.mkdir(parents=True,exist_ok=True); ART.mkdir(parents=True,exist_ok=True)

LANGUAGES={'es':'Spanish','en':'English','fr':'French','it':'Italian','de':'German','ja':'Japanese','zh':'Mandarin Chinese','he':'Hebrew','ar':'Arabic','ru':'Russian','ko':'Korean'}
NON_LATIN={'ja','zh','he','ar','ru','ko'}
app=FastAPI(title='Article Foundry',version='0.3.1')

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,title TEXT,author TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS fragments(id TEXT PRIMARY KEY,project_id TEXT,text TEXT,keywords TEXT,kind TEXT,summary TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS relations(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT,a TEXT,b TEXT,label TEXT,score REAL);
  CREATE TABLE IF NOT EXISTS concepts(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT,name TEXT,parent TEXT,UNIQUE(project_id,name));
  CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,project_id TEXT,fragment_id TEXT,raw TEXT,source_type TEXT,citekey TEXT,bibtex TEXT,created TEXT);''')
init()

class ProjectIn(BaseModel):
 title:str='Untitled project'; author:str='Prof. Alberto Munoz'
class FragmentIn(BaseModel):
 text:str=Field(min_length=1); keywords:list[str]=[]; interface_language:str='es'
class SourceIn(BaseModel):
 raw:str=Field(min_length=1); fragment_id:str|None=None
class CompileIn(BaseModel):
 mode:Literal['divulgacion','ieee','patent']='divulgacion'; title:str|None=None; author:str|None=None; interface_language:str='es'; output_language:str|None=None

def jload(s):
 try:return json.loads(s)
 except:return []

def tex(s:str)->str:
 s=str(s or '')
 for a,b in [('\\','\\textbackslash{}'),('&','\\&'),('%','\\%'),('$','\\$'),('#','\\#'),('_','\\_'),('{','\\{'),('}','\\}')]:s=s.replace(a,b)
 return s

def bib_escape(s:str)->str:return str(s).replace('\\','\\textbackslash{}').replace('{','\\{').replace('}','\\}')

def fallback_keywords(text):
 ws=re.findall(r'[^\W_]{4,}',text.lower(),re.UNICODE); out=[]
 for w in ws:
  if w not in out:out.append(w)
 return out[:8]

def normalize_source(raw:str):
 s=raw.strip(); now=date.today().isoformat(); sid=uuid.uuid4().hex[:8]
 m=re.match(r'@\w+\s*\{\s*([^,\s]+)',s,re.I|re.S)
 if m:return 'bibtex',m.group(1),s
 doi=re.search(r'(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)',s,re.I)
 if doi:
  d=doi.group(1).rstrip('.,;'); key='doi_'+re.sub(r'[^A-Za-z0-9]+','_',d)[-40:].strip('_')
  return 'doi',key,f'@misc{{{key},\n  title={{{bib_escape(d)}}},\n  url={{https://doi.org/{d}}},\n  note={{Accessed {now}}}\n}}'
 if re.match(r'https?://',s,re.I):
  key='web_'+sid; return 'url',key,f'@misc{{{key},\n  title={{{bib_escape(s)}}},\n  url={{{s}}},\n  note={{Accessed {now}}}\n}}'
 key='ref_'+sid; return 'citation',key,f'@misc{{{key},\n  title={{{bib_escape(s[:180])}}},\n  note={{{bib_escape(s)}}}\n}}'

async def chat_json(system:str,user:str,max_tokens=1200):
 model=MODEL; headers={'Authorization':f'Bearer {KEY}'}
 async with httpx.AsyncClient(timeout=120) as h:
  if not model:
   r=await h.get(f'{LLM}/models',headers=headers); r.raise_for_status(); model=r.json()['data'][0]['id']
  r=await h.post(f'{LLM}/chat/completions',headers=headers,json={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':user}],'temperature':0.15,'max_tokens':max_tokens}); r.raise_for_status()
  raw=r.json()['choices'][0]['message']['content'].strip(); raw=re.sub(r'^```json\s*|\s*```$','',raw,flags=re.I|re.S).strip(); return json.loads(raw)

async def llm_json(text,user_keywords,language):
 lang=LANGUAGES.get(language,'Spanish')
 prompt=f'''The input fragment may be written in ANY language. Analyze its meaning. Return ONLY valid JSON with keys summary, kind, keywords, concepts, relationships. kind is one of idea,evidence,method,result,claim,background,application,risk. Write summary, keywords, concepts and relationship labels in {lang}. Preserve proper nouns and technical terms where appropriate. Maximum 8 keywords and 6 concepts. User keywords: {user_keywords}\nFRAGMENT:\n{text}'''
 try:return await chat_json('You are a multilingual research knowledge architect. Output strict JSON only.',prompt,700)
 except Exception:
  ks=user_keywords or fallback_keywords(text); return {'summary':text[:280],'kind':'idea','keywords':ks,'concepts':ks[:5],'relationships':[]}

async def compose_document(mode,title,frags,language):
 lang=LANGUAGES.get(language,'Spanish'); corpus='\n\n'.join(f"FRAGMENT {i+1}: {f['text']}" for i,f in enumerate(frags)) or 'No content yet.'
 structures={'divulgacion':'popular-science article: engaging opening, central idea, explanation, evidence/connections, implications, conclusion','ieee':'IEEE-style scientific paper: abstract, introduction, related work/context, methodology or approach when supported, results/evidence when supported, discussion, conclusion','patent':'patent-oriented technical document: technical field, background, technical problem, summary of invention, detailed description, embodiments, claims draft, abstract'}
 prompt=f'''Create a coherent {structures[mode]} using ONLY the supplied fragments as factual content. Do not invent experiments, results, citations, inventors, dates, or claims of novelty not supported by the fragments. Translate or rewrite the supplied material as needed so ALL narrative output is in {lang}. Return ONLY JSON: {{"title":"...","abstract":"...","sections":[{{"heading":"...","body":"..."}}]}}. Keep the requested title semantically unless translation is appropriate. Requested title: {title}\n\n{corpus}'''
 try:return await chat_json('You are a careful multilingual scientific, technical and editorial writer. Output strict JSON only.',prompt,3000)
 except Exception:return {'title':title,'abstract':'','sections':[{'heading':'Content','body':'\n\n'.join(f['text'] for f in frags) or 'Content pending.'}]}

@app.get('/api/health')
def health():return {'ok':True,'service':'article-foundry','version':'0.3.1','db':str(DB)}

@app.get('/api/system/llm')
async def llm_status():
 try:
  async with httpx.AsyncClient(timeout=4) as h:
   r=await h.get(f'{LLM}/models',headers={'Authorization':f'Bearer {KEY}'}); r.raise_for_status(); return {'ok':True,'base_url':LLM,'models':[x['id'] for x in r.json().get('data',[])]}
 except Exception as e:return {'ok':False,'base_url':LLM,'error':str(e)}

@app.get('/api/projects')
def list_projects():
 with conn() as c:rows=c.execute('''SELECT p.id,p.title,p.author,p.created,COUNT(DISTINCT f.id) fragment_count,COUNT(DISTINCT s.id) source_count FROM projects p LEFT JOIN fragments f ON f.project_id=p.id LEFT JOIN sources s ON s.project_id=p.id GROUP BY p.id,p.title,p.author,p.created ORDER BY p.created DESC''').fetchall()
 return [dict(r) for r in rows]

@app.post('/api/projects')
def create_project(p:ProjectIn):
 i=str(uuid.uuid4()); now=datetime.now().isoformat(timespec='seconds')
 with conn() as c:c.execute('INSERT INTO projects VALUES(?,?,?,?)',(i,p.title,p.author,now))
 return {'id':i,'title':p.title,'author':p.author,'created':now}

@app.delete('/api/projects/{pid}')
def delete_project(pid:str):
 with conn() as c:
  p=c.execute('SELECT title FROM projects WHERE id=?',(pid,)).fetchone()
  if not p:raise HTTPException(404,'Project not found')
  for table in ('sources','relations','concepts','fragments'):c.execute(f'DELETE FROM {table} WHERE project_id=?',(pid,))
  c.execute('DELETE FROM projects WHERE id=?',(pid,))
 out=ART/pid
 if out.exists() and out.is_dir():shutil.rmtree(out)
 return {'ok':True,'id':pid,'title':p['title']}

@app.get('/api/projects/{pid}')
def get_project(pid:str):
 with conn() as c:
  p=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
  if not p:raise HTTPException(404,'Project not found')
  fs=[dict(x) for x in c.execute('SELECT * FROM fragments WHERE project_id=? ORDER BY created',(pid,))]
  for f in fs:f['keywords']=jload(f['keywords'])
  return {'project':dict(p),'fragments':fs,'concepts':[dict(x) for x in c.execute('SELECT name,parent FROM concepts WHERE project_id=? ORDER BY name',(pid,))],'relations':[dict(x) for x in c.execute('SELECT a,b,label,score FROM relations WHERE project_id=?',(pid,))],'sources':[dict(x) for x in c.execute('SELECT * FROM sources WHERE project_id=? ORDER BY created',(pid,))]}

@app.post('/api/projects/{pid}/fragments')
async def add_fragment(pid:str,f:FragmentIn):
 analysis=await llm_json(f.text,f.keywords,f.interface_language); fid=str(uuid.uuid4()); ks=analysis.get('keywords') or f.keywords or fallback_keywords(f.text)
 with conn() as c:
  if not c.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone():raise HTTPException(404,'Project not found')
  prior=list(c.execute('SELECT id,keywords FROM fragments WHERE project_id=?',(pid,)))
  c.execute('INSERT INTO fragments VALUES(?,?,?,?,?,?,?)',(fid,pid,f.text,json.dumps(ks,ensure_ascii=False),analysis.get('kind','idea'),analysis.get('summary',''),datetime.now().isoformat(timespec='seconds')))
  for concept in analysis.get('concepts',ks[:5]):c.execute('INSERT OR IGNORE INTO concepts(project_id,name,parent) VALUES(?,?,?)',(pid,str(concept),None))
  low={str(x).lower() for x in ks}
  for q in prior:
   old={str(x).lower() for x in jload(q['keywords'])}; overlap=len(low&old)/max(1,len(low|old))
   if overlap>0:c.execute('INSERT INTO relations(project_id,a,b,label,score) VALUES(?,?,?,?,?)',(pid,q['id'],fid,'shared concepts',round(overlap,3)))
 return {'id':fid,'analysis':analysis,'keywords':ks}

@app.post('/api/projects/{pid}/sources')
def add_source(pid:str,s:SourceIn):
 stype,key,bib=normalize_source(s.raw); sid=str(uuid.uuid4()); now=datetime.now().isoformat(timespec='seconds')
 with conn() as c:
  if not c.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone():raise HTTPException(404,'Project not found')
  if s.fragment_id and not c.execute('SELECT 1 FROM fragments WHERE id=? AND project_id=?',(s.fragment_id,pid)).fetchone():raise HTTPException(404,'Fragment not found')
  c.execute('INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)',(sid,pid,s.fragment_id,s.raw,stype,key,bib,now))
 return {'id':sid,'source_type':stype,'citekey':key,'bibtex':bib,'created':now}

@app.delete('/api/projects/{pid}/sources/{sid}')
def delete_source(pid:str,sid:str):
 with conn() as c:
  r=c.execute('DELETE FROM sources WHERE id=? AND project_id=?',(sid,pid))
  if r.rowcount==0:raise HTTPException(404,'Source not found')
 return {'ok':True}

def latex_document(mode,author,doc,has_sources,language):
 title=tex(doc.get('title') or 'Untitled'); abstract=tex(doc.get('abstract') or ''); sections=doc.get('sections') or []; unicode_mode=language in NON_LATIN
 pre='\\documentclass[conference]{IEEEtran}\n' if mode=='ieee' else '\\documentclass[11pt]{article}\n\\usepackage[margin=1in]{geometry}\n'
 if unicode_mode:pre+='\\usepackage{fontspec}\n% Compile this file with XeLaTeX for full Unicode support.\n'
 else:pre+='\\usepackage[utf8]{inputenc}\n\\usepackage[T1]{fontenc}\n'
 pre+='\\usepackage{url}\n'
 if mode=='ieee':pre+=f'\\title{{{title}}}\n\\author{{\\IEEEauthorblockN{{{tex(author)}}}}}\n'
 else:pre+=f'\\title{{{title}}}\n\\author{{{tex(author)}}}\n\\date{{{date.today().isoformat()}}}\n'
 body='\\begin{document}\n\\maketitle\n'
 if abstract:body+=f'\\begin{{abstract}}\n{abstract}\n\\end{{abstract}}\n'
 for s in sections:body+=f"\\section{{{tex(s.get('heading',''))}}}\n{tex(s.get('body',''))}\n"
 if has_sources:body+='\\nocite{*}\n\\bibliographystyle{IEEEtran}\n\\bibliography{references}\n'
 return pre+body+'\\end{document}\n'

@app.post('/api/projects/{pid}/compile')
async def compile_project(pid:str,req:CompileIn):
 with conn() as c:
  p=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
  if not p:raise HTTPException(404,'Project not found')
  fs=[dict(x) for x in c.execute('SELECT * FROM fragments WHERE project_id=? ORDER BY created',(pid,))]
  sources=[dict(x) for x in c.execute('SELECT * FROM sources WHERE project_id=? ORDER BY created',(pid,))]
 language=req.output_language or req.interface_language or 'es'; title=req.title or p['title']; author=req.author or p['author']; doc=await compose_document(req.mode,title,fs,language)
 out=ART/pid; out.mkdir(parents=True,exist_ok=True); stem=f'{req.mode}-{language}-{date.today().isoformat()}'; tp=out/f'{stem}.tex'; bp=out/'references.bib'
 tp.write_text(latex_document(req.mode,author,doc,bool(sources),language),encoding='utf-8'); bp.write_text('\n\n'.join(s['bibtex'] for s in sources),encoding='utf-8')
 pdf=None; engine=(shutil.which('xelatex') if language in NON_LATIN else None) or shutil.which('latexmk') or shutil.which('pdflatex')
 if engine and not (language in NON_LATIN and Path(engine).name not in ('xelatex','latexmk')):
  try:
   cmd=[engine,'-pdf','-interaction=nonstopmode','-halt-on-error',tp.name] if Path(engine).name=='latexmk' else [engine,'-interaction=nonstopmode','-halt-on-error',tp.name]
   subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,check=False)
   if sources and shutil.which('bibtex'):
    subprocess.run(['bibtex',stem],cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60,check=False); subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,check=False); subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120,check=False)
   candidate=out/f'{stem}.pdf'; pdf=candidate.name if candidate.exists() else None
  except Exception:pass
 return {'tex':tp.name,'pdf':pdf,'bib':bp.name,'language':language,'tex_url':f'/api/projects/{pid}/artifacts/{tp.name}','pdf_url':f'/api/projects/{pid}/artifacts/{pdf}' if pdf else None,'bib_url':f'/api/projects/{pid}/artifacts/{bp.name}','latex':tp.read_text(encoding='utf-8'),'bibtex':bp.read_text(encoding='utf-8')}

@app.get('/api/projects/{pid}/artifacts/{name}')
def artifact(pid:str,name:str):
 if '/' in name or '..' in name:raise HTTPException(400,'Invalid filename')
 p=ART/pid/name
 if not p.exists():raise HTTPException(404,'Artifact not found')
 media={'pdf':'application/pdf','tex':'application/x-tex','bib':'text/plain'}.get(p.suffix.lower().lstrip('.'),'application/octet-stream')
 headers={'Content-Disposition':f'inline; filename="{p.name}"'} if p.suffix.lower()=='.pdf' else {}
 return FileResponse(p,media_type=media,headers=headers)

@app.get('/',response_class=HTMLResponse)
def index():
 html=(ROOT/'static/index.html').read_text(encoding='utf-8')
 return HTMLResponse(html.replace('</body>','<script src="/patch.js?v=031"></script></body>'))

app.mount('/',StaticFiles(directory=ROOT/'static',html=True),name='static')

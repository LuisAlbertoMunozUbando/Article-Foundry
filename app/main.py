from __future__ import annotations
import json, os, re, shutil, sqlite3, subprocess, uuid
from datetime import date, datetime
from pathlib import Path
from typing import Literal
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent.parent
DB=Path(os.getenv('ARTICLE_FOUNDRY_DB', ROOT/'data/article_foundry.db'))
ART=Path(os.getenv('ARTICLE_FOUNDRY_ARTIFACTS', ROOT/'data/artifacts'))
LLM=os.getenv('ARTICLE_FOUNDRY_LLM_BASE_URL','http://127.0.0.1:8001/v1').rstrip('/')
KEY=os.getenv('ARTICLE_FOUNDRY_LLM_API_KEY','local')
MODEL=os.getenv('ARTICLE_FOUNDRY_LLM_MODEL','')
DB.parent.mkdir(parents=True,exist_ok=True); ART.mkdir(parents=True,exist_ok=True)

app=FastAPI(title='Article Foundry',version='0.1.1')

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,title TEXT,author TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS fragments(id TEXT PRIMARY KEY,project_id TEXT,text TEXT,keywords TEXT,kind TEXT,summary TEXT,created TEXT);
  CREATE TABLE IF NOT EXISTS relations(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT,a TEXT,b TEXT,label TEXT,score REAL);
  CREATE TABLE IF NOT EXISTS concepts(id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT,name TEXT,parent TEXT,UNIQUE(project_id,name));''')
init()

class ProjectIn(BaseModel):
 title:str='Untitled project'; author:str='Prof. Alberto Munoz'
class FragmentIn(BaseModel):
 text:str=Field(min_length=1); keywords:list[str]=[]
class CompileIn(BaseModel):
 mode:Literal['divulgacion','ieee','patent']='divulgacion'; title:str|None=None; author:str|None=None

def jload(s):
 try:return json.loads(s)
 except:return []
def tex(s:str)->str:
 for a,b in [('\\','\\textbackslash{}'),('&','\\&'),('%','\\%'),('$','\\$'),('#','\\#'),('_','\\_'),('{','\\{'),('}','\\}')]: s=s.replace(a,b)
 return s

def fallback_keywords(text):
 stop=set('para como desde sobre entre donde cuando porque este esta esto una unos unas del las los con por que sus son fue han mas muy sin al se su un el la y en de'.split())
 ws=re.findall(r'[A-Za-zÀ-ÿ0-9-]{4,}',text.lower())
 out=[]
 for w in ws:
  if w not in stop and w not in out:out.append(w)
 return out[:8]

async def llm_json(text,user_keywords):
 prompt=f'''Analyze this knowledge fragment for Article Foundry. Return ONLY valid JSON with keys summary (string), kind (one of idea,evidence,method,result,claim,background,application,risk), keywords (array max 8), concepts (array max 6), relationships (array of short semantic relation labels). User keywords: {user_keywords}\nFRAGMENT:\n{text}'''
 try:
  model=MODEL
  headers={'Authorization':f'Bearer {KEY}'}
  async with httpx.AsyncClient(timeout=90) as h:
   if not model:
    r=await h.get(f'{LLM}/models',headers=headers); r.raise_for_status(); model=r.json()['data'][0]['id']
   r=await h.post(f'{LLM}/chat/completions',headers=headers,json={'model':model,'messages':[{'role':'system','content':'You are a precise research knowledge architect. Output strict JSON only.'},{'role':'user','content':prompt}],'temperature':0.1,'max_tokens':700}); r.raise_for_status()
   raw=r.json()['choices'][0]['message']['content']; raw=re.sub(r'^```json|```$','',raw.strip()).strip(); return json.loads(raw)
 except Exception:
  ks=user_keywords or fallback_keywords(text)
  return {'summary':text[:280],'kind':'idea','keywords':ks,'concepts':ks[:5],'relationships':[]}

@app.get('/api/health')
def health(): return {'ok':True,'service':'article-foundry','db':str(DB)}
@app.get('/api/system/llm')
async def llm_status():
 try:
  async with httpx.AsyncClient(timeout=4) as h:
   r=await h.get(f'{LLM}/models',headers={'Authorization':f'Bearer {KEY}'}); r.raise_for_status()
   return {'ok':True,'base_url':LLM,'models':[x['id'] for x in r.json().get('data',[])]}
 except Exception as e:return {'ok':False,'base_url':LLM,'error':str(e)}

@app.get('/api/projects')
def list_projects():
 with conn() as c:
  rows=c.execute('''SELECT p.id,p.title,p.author,p.created,COUNT(f.id) AS fragment_count
                    FROM projects p LEFT JOIN fragments f ON f.project_id=p.id
                    GROUP BY p.id,p.title,p.author,p.created
                    ORDER BY p.created DESC''').fetchall()
 return [dict(r) for r in rows]

@app.post('/api/projects')
def create_project(p:ProjectIn):
 i=str(uuid.uuid4()); now=datetime.now().isoformat(timespec='seconds')
 with conn() as c:c.execute('INSERT INTO projects VALUES(?,?,?,?)',(i,p.title,p.author,now))
 return {'id':i,'title':p.title,'author':p.author,'created':now}

@app.get('/api/projects/{pid}')
def get_project(pid:str):
 with conn() as c:
  p=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
  if not p:raise HTTPException(404,'Project not found')
  fs=[dict(x) for x in c.execute('SELECT * FROM fragments WHERE project_id=? ORDER BY created',(pid,))]
  for f in fs:f['keywords']=jload(f['keywords'])
  concepts=[dict(x) for x in c.execute('SELECT name,parent FROM concepts WHERE project_id=? ORDER BY name',(pid,))]
  rel=[dict(x) for x in c.execute('SELECT a,b,label,score FROM relations WHERE project_id=?',(pid,))]
 return {'project':dict(p),'fragments':fs,'concepts':concepts,'relations':rel}

@app.post('/api/projects/{pid}/fragments')
async def add_fragment(pid:str,f:FragmentIn):
 analysis=await llm_json(f.text,f.keywords); fid=str(uuid.uuid4()); ks=analysis.get('keywords') or f.keywords or fallback_keywords(f.text)
 with conn() as c:
  if not c.execute('SELECT 1 FROM projects WHERE id=?',(pid,)).fetchone():raise HTTPException(404,'Project not found')
  prior=list(c.execute('SELECT id,keywords FROM fragments WHERE project_id=?',(pid,)))
  c.execute('INSERT INTO fragments VALUES(?,?,?,?,?,?,?)',(fid,pid,f.text,json.dumps(ks,ensure_ascii=False),analysis.get('kind','idea'),analysis.get('summary',''),datetime.now().isoformat(timespec='seconds')))
  for concept in analysis.get('concepts',ks[:5]): c.execute('INSERT OR IGNORE INTO concepts(project_id,name,parent) VALUES(?,?,?)',(pid,str(concept),None))
  low={x.lower() for x in ks}
  for q in prior:
   old=jload(q['keywords']); overlap=len(low & {x.lower() for x in old})/max(1,len(low|{x.lower() for x in old}))
   if overlap>0:c.execute('INSERT INTO relations(project_id,a,b,label,score) VALUES(?,?,?,?,?)',(pid,q['id'],fid,'shared concepts',round(overlap,3)))
 return {'id':fid,'analysis':analysis,'keywords':ks}

def latex_document(mode,title,author,frags):
 body='\n\n'.join(tex(f['text']) for f in frags) or 'Contenido pendiente.'
 if mode=='ieee':
  return f'''\\documentclass[conference]{{IEEEtran}}\n\\usepackage[utf8]{{inputenc}}\n\\title{{{tex(title)}}}\n\\author{{\\IEEEauthorblockN{{{tex(author)}}}}}\n\\begin{{document}}\\maketitle\n\\begin{{abstract}}Documento generado incrementalmente por Article Foundry.\\end{{abstract}}\n\\section{{Introduction}}\n{body}\n\\section{{Discussion}}\nLa estructura se refinara conforme se incorporen nuevos fragmentos.\n\\section{{Conclusion}}\nTrabajo en progreso.\n\\end{{document}}'''
 if mode=='patent':
  secs=['Technical Field','Background','Summary of the Invention','Detailed Description','Embodiments','Claims','Abstract']
 else: secs=['La idea central','Por que importa','Evidencia y conexiones','Implicaciones','Conclusion']
 chunks=[f'\\section{{{s}}}\n{body if i==0 else "Seccion en construccion a partir de la taxonomia viva."}' for i,s in enumerate(secs)]
 return f'''\\documentclass[11pt]{{article}}\n\\usepackage[utf8]{{inputenc}}\n\\usepackage[T1]{{fontenc}}\n\\usepackage[spanish]{{babel}}\n\\usepackage[margin=1in]{{geometry}}\n\\title{{{tex(title)}}}\n\\author{{{tex(author)}}}\n\\date{{{date.today().isoformat()}}}\n\\begin{{document}}\\maketitle\n{chr(10).join(chunks)}\n\\end{{document}}'''

@app.post('/api/projects/{pid}/compile')
def compile_project(pid:str,req:CompileIn):
 with conn() as c:
  p=c.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
  if not p:raise HTTPException(404,'Project not found')
  fs=[dict(x) for x in c.execute('SELECT * FROM fragments WHERE project_id=? ORDER BY created',(pid,))]
 title=req.title or p['title']; author=req.author or p['author']; out=ART/pid; out.mkdir(parents=True,exist_ok=True)
 stem=f'{req.mode}-{date.today().isoformat()}'; tp=out/f'{stem}.tex'; tp.write_text(latex_document(req.mode,title,author,fs),encoding='utf-8')
 pdf=None; engine=shutil.which('latexmk') or shutil.which('pdflatex')
 if engine:
  cmd=[engine,'-pdf','-interaction=nonstopmode','-halt-on-error',tp.name] if Path(engine).name=='latexmk' else [engine,'-interaction=nonstopmode','-halt-on-error',tp.name]
  try:
   subprocess.run(cmd,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60,check=True); candidate=out/f'{stem}.pdf'; pdf=candidate.name if candidate.exists() else None
  except Exception: pass
 return {'tex':tp.name,'pdf':pdf,'tex_url':f'/api/projects/{pid}/artifacts/{tp.name}','pdf_url':f'/api/projects/{pid}/artifacts/{pdf}' if pdf else None,'latex':tp.read_text(encoding='utf-8')}

@app.get('/api/projects/{pid}/artifacts/{name}')
def artifact(pid:str,name:str):
 if '/' in name or '..' in name:raise HTTPException(400,'Invalid filename')
 p=ART/pid/name
 if not p.exists():raise HTTPException(404,'Artifact not found')
 return FileResponse(p)

app.mount('/',StaticFiles(directory=ROOT/'static',html=True),name='static')

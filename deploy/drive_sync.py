#!/usr/bin/env python3
from __future__ import annotations
import json, os, shutil, sqlite3, subprocess, sys, tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(os.getenv('ARTICLE_FOUNDRY_DB', ROOT/'data/article_foundry.db'))
ART = Path(os.getenv('ARTICLE_FOUNDRY_ARTIFACTS', ROOT/'data/artifacts'))
EXPORT = Path(os.getenv('ARTICLE_FOUNDRY_DRIVE_EXPORT', ROOT/'data/drive-export'))
REMOTE = os.getenv('ARTICLE_FOUNDRY_RCLONE_REMOTE','').strip()
REMOTE_FOLDER = os.getenv('ARTICLE_FOUNDRY_DRIVE_FOLDER','Article Foundry').strip('/')


def safe_name(s:str)->str:
    keep=''.join(ch if ch.isalnum() or ch in ' .-_()[]' else '_' for ch in (s or 'Untitled'))
    return keep.strip().replace('  ',' ')[:120] or 'Untitled'


def snapshot_db(dst:Path):
    dst.parent.mkdir(parents=True,exist_ok=True)
    src=sqlite3.connect(DB)
    out=sqlite3.connect(dst)
    with out:
        src.backup(out)
    out.close(); src.close()


def export_projects():
    EXPORT.mkdir(parents=True,exist_ok=True)
    db_copy=EXPORT/'article_foundry.db'
    snapshot_db(db_copy)
    c=sqlite3.connect(db_copy); c.row_factory=sqlite3.Row
    projects=list(c.execute('SELECT * FROM projects ORDER BY created'))
    manifest={'generated':datetime.now().isoformat(timespec='seconds'),'projects':[]}
    for p in projects:
        pid=p['id']; folder=EXPORT/'projects'/safe_name(p['title'])
        folder.mkdir(parents=True,exist_ok=True)
        fragments=[dict(r) for r in c.execute('SELECT * FROM fragments WHERE project_id=? ORDER BY created',(pid,))]
        sources=[dict(r) for r in c.execute('SELECT * FROM sources WHERE project_id=? ORDER BY created',(pid,))]
        concepts=[dict(r) for r in c.execute('SELECT name,parent FROM concepts WHERE project_id=? ORDER BY name',(pid,))]
        relations=[dict(r) for r in c.execute('SELECT a,b,label,score FROM relations WHERE project_id=?',(pid,))]
        data={'project':dict(p),'fragments':fragments,'concepts':concepts,'relations':relations,'sources':sources}
        (folder/'project.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        (folder/'references.bib').write_text('\n\n'.join(s.get('bibtex','') for s in sources),encoding='utf-8')
        art=ART/pid
        if art.exists():
            for f in art.iterdir():
                if f.is_file() and f.suffix.lower() in {'.pdf','.tex','.bib','.log','.aux','.bbl','.blg'}:
                    shutil.copy2(f,folder/f.name)
        manifest['projects'].append({'id':pid,'title':p['title'],'created':p['created'],'folder':str(folder.relative_to(EXPORT))})
    c.close()
    (EXPORT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')


def sync_drive():
    if not REMOTE:
        raise SystemExit('ARTICLE_FOUNDRY_RCLONE_REMOTE is not set')
    if not shutil.which('rclone'):
        raise SystemExit('rclone is not installed')
    target=f'{REMOTE}:{REMOTE_FOLDER}'
    cmd=['rclone','copy',str(EXPORT),target,'--create-empty-src-dirs','--fast-list','--transfers','4','--checkers','8']
    subprocess.run(cmd,check=True)
    print(f'Synced {EXPORT} -> {target}')


if __name__=='__main__':
    export_projects()
    sync_drive()

// Article Foundry UI behavior patch
(() => {
  const FLAGS = {es:'🇲🇽',en:'🇬🇧',fr:'🇫🇷',it:'🇮🇹',de:'🇩🇪',ja:'🇯🇵',zh:'🇨🇳',he:'🇮🇱',ar:'🇦🇪',ru:'🇷🇺',ko:'🇰🇷'};
  const NON_LATIN = new Set(['ja','zh','he','ar','ru','ko']);
  let selectedOutputLang = localStorage.getItem('af_output_lang') || null;

  function activeProjectId(){
    for(const b of Array.from(document.querySelectorAll('#projectTabs .ptab.active'))){
      const m=(b.getAttribute('onclick')||'').match(/selectProject\('([^']+)'\)/);
      if(m) return m[1];
    }
    try{return project||null}catch(_){return null}
  }
  function effectiveUILang(){
    try{if(uiLang)return uiLang}catch(_){}
    return localStorage.getItem('af_ui')||document.documentElement.lang||'es';
  }
  function effectiveOutputLang(){return selectedOutputLang||effectiveUILang()}

  // Keep the flag OUTSIDE #compilerLabel. applyLang() rewrites compilerLabel.textContent,
  // so an embedded flag was being erased every time the UI language refreshed.
  const compilerLabel=document.getElementById('compilerLabel');
  let compilerFlag=document.getElementById('compilerFlag');
  if(compilerLabel && !compilerFlag){
    const wrap=document.createElement('div');
    wrap.style.display='flex';
    wrap.style.alignItems='center';
    wrap.style.gap='7px';
    wrap.style.marginBottom='11px';
    compilerLabel.parentNode.insertBefore(wrap,compilerLabel);
    wrap.appendChild(compilerLabel);
    compilerLabel.style.margin='0';
    compilerFlag=document.createElement('span');
    compilerFlag.id='compilerFlag';
    compilerFlag.style.fontSize='20px';
    compilerFlag.style.lineHeight='1';
    compilerFlag.setAttribute('aria-label','Output language');
    wrap.appendChild(compilerFlag);
  }
  function updateCompilerFlag(){
    if(compilerFlag) compilerFlag.textContent=FLAGS[effectiveOutputLang()]||'';
  }
  function setSelectedOutput(lang){
    selectedOutputLang=lang||null;
    if(selectedOutputLang)localStorage.setItem('af_output_lang',selectedOutputLang);
    else localStorage.removeItem('af_output_lang');
    try{if(typeof outLang!=='undefined')outLang=selectedOutputLang}catch(_){}
    updateCompilerFlag();
  }

  document.addEventListener('click',e=>{
    const btn=e.target.closest('#outFlags button,#outFlags .flag');
    if(!btn)return;
    const oc=btn.getAttribute('onclick')||'';
    const m=oc.match(/setOut\((?:'|")?([a-z]{2}|null)(?:'|")?\)/i);
    if(m){setSelectedOutput(m[1]==='null'?null:m[1]);return;}
    const txt=(btn.textContent||'').trim();
    const lang=Object.keys(FLAGS).find(k=>txt.includes(FLAGS[k]));
    if(lang)setSelectedOutput(lang);
  },true);

  const oldSetOut=window.setOut;
  if(typeof oldSetOut==='function'){
    window.setOut=function(lang){
      setSelectedOutput(lang);
      const r=oldSetOut.apply(this,arguments);
      setTimeout(updateCompilerFlag,0);
      return r;
    };
  }
  const oldSetUI=window.setUI;
  if(typeof oldSetUI==='function')window.setUI=function(){const r=oldSetUI.apply(this,arguments);setTimeout(updateCompilerFlag,0);return r;};
  const oldApplyLang=window.applyLang;
  if(typeof oldApplyLang==='function')window.applyLang=function(){const r=oldApplyLang.apply(this,arguments);setTimeout(updateCompilerFlag,0);return r;};

  const oldAddFragment=window.addFragment;
  window.addFragment=async function(){
    const text=document.getElementById('text')?.value.trim()||'';
    if(text==='.'){
      document.getElementById('text').value='';
      const status=document.getElementById('opstatus');
      const lang=effectiveOutputLang();
      if(status)status.textContent=`Sin entrada nueva → generando ${FLAGS[lang]||''}…`;
      const result=await window.compileDoc();
      if(status)status.textContent=result?`✓ Documento generado ${FLAGS[result.language]||''}`:'⚠ No se pudo generar el documento';
      return;
    }
    return oldAddFragment.apply(this,arguments);
  };

  window.addSource=async function(){
    const raw=document.getElementById('sourceRaw')?.value.trim()||'';
    const pid=activeProjectId(); if(!pid||!raw)return;
    const sourceStatus=document.getElementById('sourceStatus');
    try{
      const state=await api(`/api/projects/${pid}`); let fragmentId=null;
      try{if(lastFragment&&(state.fragments||[]).some(f=>f.id===lastFragment))fragmentId=lastFragment}catch(_){}
      const x=await api(`/api/projects/${pid}/sources`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({raw,fragment_id:fragmentId})});
      if(sourceStatus)sourceStatus.textContent='✓ '+x.citekey;
      document.getElementById('sourceRaw').value='';
      try{await refresh()}catch(_){if(window.selectProject)await window.selectProject(pid)}
      try{projects=await api('/api/projects');renderTabs()}catch(_){}
    }catch(e){if(sourceStatus)sourceStatus.textContent=e.message}
  };

  window.compileDoc=async function(){
    const pid=activeProjectId(); if(!pid)return null;
    const lang=effectiveOutputLang();
    const status=document.getElementById('compileStatus'),paper=document.getElementById('paper'),latexEl=document.getElementById('latex'),texHolder=document.getElementById('texdl'),bibHolder=document.getElementById('bibdl'),pdfHolder=document.getElementById('pdfdl');
    if(status)status.textContent=`Generando ${FLAGS[lang]||''}…`;
    if(paper)paper.innerHTML='<div class="by" style="padding-top:70px">Generating new PDF…</div>';
    if(pdfHolder)pdfHolder.innerHTML='';
    try{
      const state=await api(`/api/projects/${pid}`),p=state.project||{};
      let currentMode='divulgacion'; try{currentMode=editorial||currentMode}catch(_){}
      const requestedTitle=document.getElementById('docTitle')?.value||p.title||'Untitled';
      const x=await api(`/api/projects/${pid}/compile`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:currentMode,title:requestedTitle,author:p.author||'Prof. Alberto Muñoz',interface_language:effectiveUILang(),output_language:lang})});
      if(latexEl)latexEl.textContent=x.latex||'';
      if(texHolder){texHolder.innerHTML='';const b=document.createElement('button');b.textContent='.tex';b.onclick=()=>downloadArtifact(x.tex_url,x.tex);texHolder.appendChild(b)}
      if(bibHolder){bibHolder.innerHTML='';const b=document.createElement('button');b.textContent='.bib';b.onclick=()=>downloadArtifact(x.bib_url,x.bib);bibHolder.appendChild(b)}
      if(x.pdf_url){
        const rev=x.revision||Date.now().toString(),sep=x.pdf_url.includes('?')?'&':'?',previewUrl=`${x.pdf_url}${sep}_afrev=${encodeURIComponent(rev)}#toolbar=1`;
        if(paper){paper.innerHTML='';const iframe=document.createElement('iframe');iframe.src=previewUrl;iframe.title='PDF preview';iframe.style.width='100%';iframe.style.height='760px';iframe.style.border='0';paper.appendChild(iframe)}
        if(pdfHolder){const b=document.createElement('button');b.textContent='Descargar PDF';b.onclick=()=>downloadArtifact(x.pdf_url,x.pdf);pdfHolder.appendChild(b)}
        if(status)status.textContent=`✓ ${FLAGS[x.language]||''} ${window.LANG?.[x.language]?.[1]||x.language}`;
      }else{
        if(paper)paper.innerHTML='<div class="by" style="padding-top:70px">No PDF was produced. LaTeX is available.</div>';
        if(status)status.textContent=NON_LATIN.has(lang)?`✓ LaTeX generado ${FLAGS[lang]} · PDF requiere XeLaTeX.`:'LaTeX generado, pero la compilación PDF falló.';
      }
      setSelectedOutput(x.language||lang);
      return x;
    }catch(e){
      if(paper)paper.innerHTML='<div class="by" style="padding-top:70px">Compilation failed.</div>';
      if(status)status.textContent=e.message;
      return null;
    }
  };

  const text=document.getElementById('text');
  if(text)text.placeholder='Pega texto aquí en cualquier idioma… o escribe . para generar sin agregar texto nuevo';
  updateCompilerFlag();
})();

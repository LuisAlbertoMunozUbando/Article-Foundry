// Article Foundry UI behavior patch
(() => {
  const FLAGS = {
    es:'🇲🇽', en:'🇬🇧', fr:'🇫🇷', it:'🇮🇹', de:'🇩🇪',
    ja:'🇯🇵', zh:'🇨🇳', he:'🇮🇱', ar:'🇦🇪', ru:'🇷🇺', ko:'🇰🇷'
  };
  const NON_LATIN = new Set(['ja','zh','he','ar','ru','ko']);
  let selectedOutputLang = localStorage.getItem('af_output_lang') || null;

  function activeProjectId() {
    const buttons = Array.from(document.querySelectorAll('#projectTabs .ptab.active'));
    for (const b of buttons) {
      const oc = b.getAttribute('onclick') || '';
      const m = oc.match(/selectProject\('([^']+)'\)/);
      if (m) return m[1];
    }
    try { return project || null; } catch (_) { return null; }
  }

  function effectiveUILang() {
    try { if (uiLang) return uiLang; } catch (_) {}
    return localStorage.getItem('af_ui') || document.documentElement.lang || 'es';
  }

  function effectiveOutputLang() {
    return selectedOutputLang || effectiveUILang();
  }

  const oldAddFragment = window.addFragment;
  window.addFragment = async function () {
    const text = document.getElementById('text')?.value.trim() || '';
    if (text === '.') {
      document.getElementById('text').value = '';
      const status = document.getElementById('opstatus');
      if (status) status.textContent = 'Sin entrada nueva → generando documento…';
      await window.compileDoc();
      if (status) status.textContent = '✓ Documento generado con la memoria actual';
      return;
    }
    return oldAddFragment.apply(this, arguments);
  };

  const compilerLabel = document.getElementById('compilerLabel');
  const outputLabelBase = compilerLabel?.textContent || 'Compilador editorial';

  function updateCompilerFlag() {
    if (!compilerLabel) return;
    const clean = compilerLabel.textContent.replace(/\s+(🇲🇽|🇬🇧|🇫🇷|🇮🇹|🇩🇪|🇯🇵|🇨🇳|🇮🇱|🇦🇪|🇷🇺|🇰🇷)$/u, '');
    compilerLabel.textContent = `${clean || outputLabelBase} ${FLAGS[effectiveOutputLang()] || ''}`.trim();
  }

  const oldSetOut = window.setOut;
  window.setOut = function (lang) {
    selectedOutputLang = lang || null;
    if (selectedOutputLang) localStorage.setItem('af_output_lang', selectedOutputLang);
    else localStorage.removeItem('af_output_lang');
    const result = oldSetOut.apply(this, arguments);
    setTimeout(updateCompilerFlag, 0);
    return result;
  };

  const oldSetUI = window.setUI;
  window.setUI = function () {
    const result = oldSetUI.apply(this, arguments);
    setTimeout(updateCompilerFlag, 0);
    return result;
  };

  const oldApplyLang = window.applyLang;
  window.applyLang = function () {
    const result = oldApplyLang.apply(this, arguments);
    setTimeout(updateCompilerFlag, 0);
    return result;
  };

  // Keep source insertion attached to the project actually selected in the UI.
  window.addSource = async function () {
    const raw = document.getElementById('sourceRaw')?.value.trim() || '';
    const pid = activeProjectId();
    if (!pid || !raw) return;
    const sourceStatus = document.getElementById('sourceStatus');
    try {
      const state = await api(`/api/projects/${pid}`);
      let fragmentId = null;
      try {
        if (lastFragment && (state.fragments || []).some(f => f.id === lastFragment)) fragmentId = lastFragment;
      } catch (_) {}
      const x = await api(`/api/projects/${pid}/sources`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({raw, fragment_id:fragmentId})
      });
      if (sourceStatus) sourceStatus.textContent = '✓ ' + x.citekey;
      document.getElementById('sourceRaw').value = '';
      try { await refresh(); } catch (_) { if (window.selectProject) await window.selectProject(pid); }
      try { projects = await api('/api/projects'); renderTabs(); } catch (_) {}
    } catch (e) {
      if (sourceStatus) sourceStatus.textContent = e.message;
    }
  };

  // Compile from the project selected NOW, not from a stale preview/project state.
  window.compileDoc = async function () {
    const pid = activeProjectId();
    if (!pid) return;

    const lang = effectiveOutputLang();
    const status = document.getElementById('compileStatus');
    const paper = document.getElementById('paper');
    const latexEl = document.getElementById('latex');
    const texHolder = document.getElementById('texdl');
    const bibHolder = document.getElementById('bibdl');
    const pdfHolder = document.getElementById('pdfdl');

    if (status) status.textContent = `Generando ${FLAGS[lang] || ''}…`;
    if (paper) paper.innerHTML = '<div class="by" style="padding-top:70px">Generating new PDF…</div>';
    if (pdfHolder) pdfHolder.innerHTML = '';

    try {
      const state = await api(`/api/projects/${pid}`);
      const p = state.project || {};
      let currentMode = 'divulgacion';
      try { currentMode = editorial || currentMode; } catch (_) {}
      const requestedTitle = document.getElementById('docTitle')?.value || p.title || 'Untitled';

      const x = await api(`/api/projects/${pid}/compile`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          mode:currentMode,
          title:requestedTitle,
          author:p.author || 'Prof. Alberto Muñoz',
          interface_language:effectiveUILang(),
          output_language:lang
        })
      });

      if (latexEl) latexEl.textContent = x.latex || '';

      if (texHolder) {
        texHolder.innerHTML = '';
        const b = document.createElement('button');
        b.textContent = '.tex';
        b.onclick = () => downloadArtifact(x.tex_url, x.tex);
        texHolder.appendChild(b);
      }
      if (bibHolder) {
        bibHolder.innerHTML = '';
        const b = document.createElement('button');
        b.textContent = '.bib';
        b.onclick = () => downloadArtifact(x.bib_url, x.bib);
        bibHolder.appendChild(b);
      }

      if (x.pdf_url) {
        const rev = x.revision || Date.now().toString();
        const sep = x.pdf_url.includes('?') ? '&' : '?';
        const previewUrl = `${x.pdf_url}${sep}_afrev=${encodeURIComponent(rev)}#toolbar=1`;
        if (paper) {
          paper.innerHTML = '';
          const iframe = document.createElement('iframe');
          iframe.src = previewUrl;
          iframe.title = 'PDF preview';
          iframe.style.width = '100%';
          iframe.style.height = '760px';
          iframe.style.border = '0';
          paper.appendChild(iframe);
        }
        if (pdfHolder) {
          const b = document.createElement('button');
          b.textContent = 'Descargar PDF';
          b.title = 'Descargar PDF';
          b.onclick = () => downloadArtifact(x.pdf_url, x.pdf);
          pdfHolder.appendChild(b);
        }
        if (status) status.textContent = `✓ ${FLAGS[x.language] || ''} ${LANG?.[x.language]?.[1] || x.language}`;
      } else {
        if (paper) paper.innerHTML = '<div class="by" style="padding-top:70px">No PDF was produced. LaTeX is available.</div>';
        if (status) {
          status.textContent = NON_LATIN.has(lang)
            ? `✓ LaTeX generado en ${FLAGS[lang]} · PDF requiere XeLaTeX (texlive-xetex).`
            : `LaTeX generado, pero la compilación PDF falló. Revisa el LaTeX o el log de TeX.`;
        }
      }
      updateCompilerFlag();
    } catch (e) {
      if (paper) paper.innerHTML = '<div class="by" style="padding-top:70px">Compilation failed.</div>';
      if (status) status.textContent = e.message;
    }
  };

  const text = document.getElementById('text');
  if (text) text.placeholder = 'Pega texto aquí en cualquier idioma… o escribe . para generar sin agregar texto nuevo';

  updateCompilerFlag();
})();

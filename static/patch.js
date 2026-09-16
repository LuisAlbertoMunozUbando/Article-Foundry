// Article Foundry UI behavior patch
(() => {
  const FLAGS = {
    es:'🇲🇽', en:'🇬🇧', fr:'🇫🇷', it:'🇮🇹', de:'🇩🇪',
    ja:'🇯🇵', zh:'🇨🇳', he:'🇮🇱', ar:'🇦🇪', ru:'🇷🇺', ko:'🇰🇷'
  };
  const NON_LATIN = new Set(['ja','zh','he','ar','ru','ko']);
  let selectedOutputLang = localStorage.getItem('af_output_lang') || null;

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

  function effectiveUILang() {
    return localStorage.getItem('af_ui') || document.documentElement.lang || 'es';
  }

  function effectiveOutputLang() {
    return selectedOutputLang || effectiveUILang();
  }

  function updateCompilerFlag() {
    if (!compilerLabel) return;
    const clean = compilerLabel.textContent.replace(/\s+(🇲🇽|🇬🇧|🇫🇷|🇮🇹|🇩🇪|🇯🇵|🇨🇳|🇮🇱|🇦🇪|🇷🇺|🇰🇷)$/u, '');
    const base = clean || outputLabelBase;
    compilerLabel.textContent = `${base} ${FLAGS[effectiveOutputLang()] || ''}`.trim();
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

  const oldCompile = window.compileDoc;
  window.compileDoc = async function () {
    const status = document.getElementById('compileStatus');
    const lang = effectiveOutputLang();
    if (status) status.textContent = `Generando salida ${FLAGS[lang] || ''}…`;

    await oldCompile.apply(this, arguments);

    const paper = document.getElementById('paper');
    const iframe = paper?.querySelector('iframe');
    if (iframe) {
      const raw = iframe.getAttribute('src') || iframe.src || '';
      if (raw) {
        try {
          const u = new URL(raw, window.location.origin);
          u.searchParams.set('_afrev', Date.now().toString());
          iframe.src = u.pathname + u.search + u.hash;
        } catch (_) {
          iframe.src = raw + (raw.includes('?') ? '&' : '?') + '_afrev=' + Date.now();
        }
      }
      iframe.setAttribute('title', 'PDF preview');
      iframe.style.width = '100%';
      iframe.style.height = '760px';
      iframe.style.border = '0';
    }

    const pdfHolder = document.getElementById('pdfdl');
    const btn = pdfHolder?.querySelector('button');
    if (btn) {
      btn.textContent = 'Descargar PDF';
      btn.title = 'Descargar PDF';
    } else if (status && NON_LATIN.has(lang)) {
      status.textContent = `✓ LaTeX generado en ${FLAGS[lang]} · Para PDF local en este idioma instala XeLaTeX (texlive-xetex) en el Spark.`;
    }

    updateCompilerFlag();
  };

  const text = document.getElementById('text');
  if (text) text.placeholder = 'Pega texto aquí en cualquier idioma… o escribe . para generar sin agregar texto nuevo';

  updateCompilerFlag();
})();

// Article Foundry UI behavior patch: '.' means generate without adding a fragment.
(() => {
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

  const oldCompile = window.compileDoc;
  window.compileDoc = async function () {
    await oldCompile.apply(this, arguments);
    const paper = document.getElementById('paper');
    const iframe = paper?.querySelector('iframe');
    if (iframe) {
      // The artifact endpoint is inline. This iframe only displays the PDF.
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
    }
  };

  const compilerLabel = document.getElementById('compilerLabel');
  const updateCompilerFlag = () => {
    if (!compilerLabel || !window.LANG) return;
    const base = (window.T?.[window.uiLang]?.compiler) || compilerLabel.dataset.base || compilerLabel.textContent.replace(/\s+[🇦-🇿]{2}$/u, '');
    compilerLabel.dataset.base = base;
    const effectiveLang = window.outLang || window.uiLang || 'es';
    const flag = window.LANG?.[effectiveLang]?.[0] || '';
    compilerLabel.textContent = `${base} ${flag}`.trim();
  };

  const oldSetOut = window.setOut;
  window.setOut = function (lang) {
    const result = oldSetOut.apply(this, arguments);
    setTimeout(updateCompilerFlag, 0);
    return result;
  };

  const oldSetUI = window.setUI;
  window.setUI = function (lang) {
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

  const text = document.getElementById('text');
  if (text) text.placeholder = 'Pega texto aquí en cualquier idioma… o escribe . para generar sin agregar texto nuevo';

  updateCompilerFlag();
})();

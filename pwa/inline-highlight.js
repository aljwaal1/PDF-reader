(() => {
  const NativeUtterance = window.SpeechSynthesisUtterance;
  if (!NativeUtterance || window.__pdfInlineSpeechHighlight) return;
  window.__pdfInlineSpeechHighlight = true;

  let pdfjs = null;
  let pdf = null;
  let pageNumber = 0;
  let items = [];
  let itemCursor = 0;
  let preparing = null;

  const style = document.createElement('style');
  style.textContent = `
    #pdfWordHighlight{position:absolute;z-index:8;pointer-events:none;border-radius:5px;background:rgba(255,224,72,.62);box-shadow:0 0 0 2px rgba(91,95,239,.28),0 2px 8px rgba(0,0,0,.12);transition:left .07s linear,top .07s linear,width .07s linear,height .07s linear;display:none}
    #readingCard{display:none!important}
    .presets{display:none!important}
    @media(max-width:720px){.readerMain{padding-bottom:108px!important}.bottom{padding:5px 6px calc(5px + env(safe-area-inset-bottom))!important}.rate{grid-template-columns:34px 42px 1fr 34px!important}.actions .btn,.navBtn{height:34px!important;min-height:34px!important}.page{margin:0!important}}
  `;
  document.head.appendChild(style);

  function currentPageNumber() {
    const value = document.getElementById('page')?.textContent || '';
    const match = value.match(/(\d+)\s*\/\s*(\d+)/);
    return match ? Number(match[1]) : 0;
  }

  async function loadCurrentFile() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('pdf-reader', 1);
      req.onerror = () => reject(req.error);
      req.onsuccess = () => {
        const db = req.result;
        const tx = db.transaction('books');
        const get = tx.objectStore('books').get('current');
        get.onsuccess = () => { db.close(); resolve(get.result); };
        get.onerror = () => { db.close(); reject(get.error); };
      };
    });
  }

  async function preparePage(force = false) {
    if (preparing) return preparing;
    preparing = (async () => {
      const p = currentPageNumber();
      const canvas = document.querySelector('#pdfWrap canvas');
      if (!p || !canvas) return;
      if (!force && p === pageNumber && items.length) return;
      if (!pdfjs) {
        pdfjs = await import('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.8.69/pdf.min.mjs');
        pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.8.69/pdf.worker.min.mjs';
      }
      if (!pdf) {
        const file = await loadCurrentFile();
        if (!file) return;
        pdf = await pdfjs.getDocument({data: await file.arrayBuffer()}).promise;
      }
      const page = await pdf.getPage(p);
      const tc = await page.getTextContent();
      const rect = canvas.getBoundingClientRect();
      const base = page.getViewport({scale: 1});
      const scale = rect.width / base.width;
      const viewport = page.getViewport({scale});
      items = tc.items.filter(x => x.str && x.str.trim()).map(x => {
        const t = pdfjs.Util.transform(viewport.transform, x.transform);
        const fontHeight = Math.max(8, Math.hypot(t[2], t[3]));
        return {
          str: x.str,
          norm: x.str.toLocaleLowerCase(),
          left: t[4],
          top: t[5] - fontHeight,
          width: Math.max(5, x.width * scale),
          height: fontHeight * 1.12,
        };
      });
      pageNumber = p;
      itemCursor = 0;
    })().catch(() => {}).finally(() => { preparing = null; });
    return preparing;
  }

  function overlay() {
    const wrap = document.getElementById('pdfWrap');
    if (!wrap) return null;
    let el = document.getElementById('pdfWordHighlight');
    if (!el) {
      el = document.createElement('div');
      el.id = 'pdfWordHighlight';
      wrap.appendChild(el);
    }
    return el;
  }

  async function highlightWord(rawWord) {
    const word = String(rawWord || '').replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '').toLocaleLowerCase();
    if (!word) return;
    await preparePage();
    if (!items.length) return;

    let found = -1;
    for (let i = itemCursor; i < items.length; i++) {
      if (items[i].norm.includes(word)) { found = i; break; }
    }
    if (found < 0) {
      for (let i = 0; i < itemCursor; i++) {
        if (items[i].norm.includes(word)) { found = i; break; }
      }
    }
    if (found < 0) return;
    itemCursor = found;
    const item = items[found];
    const idx = item.norm.indexOf(word);
    const ratioStart = Math.max(0, idx) / Math.max(1, item.str.length);
    const ratioWidth = Math.max(word.length / Math.max(1, item.str.length), .08);
    const canvas = document.querySelector('#pdfWrap canvas');
    const wrap = document.getElementById('pdfWrap');
    const el = overlay();
    if (!canvas || !wrap || !el) return;
    const cr = canvas.getBoundingClientRect();
    const wr = wrap.getBoundingClientRect();
    el.style.left = `${cr.left - wr.left + item.left + item.width * ratioStart}px`;
    el.style.top = `${cr.top - wr.top + item.top}px`;
    el.style.width = `${Math.max(12, item.width * ratioWidth)}px`;
    el.style.height = `${Math.max(12, item.height)}px`;
    el.style.display = 'block';
  }

  function hideHighlight() {
    const el = document.getElementById('pdfWordHighlight');
    if (el) el.style.display = 'none';
  }

  window.SpeechSynthesisUtterance = function(text) {
    const utterance = new NativeUtterance(text);
    utterance.addEventListener('start', () => { itemCursor = 0; preparePage(true); });
    utterance.addEventListener('boundary', e => {
      if (typeof e.charIndex !== 'number') return;
      const source = String(text || '');
      const word = e.charLength ? source.substr(e.charIndex, e.charLength) : source.slice(e.charIndex).split(/\s/)[0];
      highlightWord(word);
    });
    utterance.addEventListener('end', hideHighlight);
    utterance.addEventListener('error', hideHighlight);
    return utterance;
  };
  window.SpeechSynthesisUtterance.prototype = NativeUtterance.prototype;

  const observer = new MutationObserver(() => {
    if (document.querySelector('#pdfWrap canvas')) preparePage(true);
  });
  observer.observe(document.documentElement, {subtree: true, childList: true});
})();

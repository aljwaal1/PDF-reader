from pathlib import Path

index = Path('pwa/index.html')
s = index.read_text(encoding='utf-8')

# Keep existing v18 fixes and add page-aware translation behavior.
# When page changes, never leave translation from the previous page visible.
old_nav = "$('prev').onclick=async()=>{if(state.pdf&&state.page>1){stopSpeech(true);state.page--;await renderPage()}};$('next').onclick=async()=>{if(state.pdf&&state.page<state.pdf.numPages){stopSpeech(true);state.page++;await renderPage()}};"
new_nav = "$('prev').onclick=async()=>{if(state.pdf&&state.page>1){stopSpeech(true);$('translation').textContent='';state.page--;await renderPage();const cached=state.translations.get(state.page);$('translation').textContent=cached||'اضغط «ترجمة» لعرض ترجمة هذه الصفحة.'}};$('next').onclick=async()=>{if(state.pdf&&state.page<state.pdf.numPages){stopSpeech(true);$('translation').textContent='';state.page++;await renderPage();const cached=state.translations.get(state.page);$('translation').textContent=cached||'اضغط «ترجمة» لعرض ترجمة هذه الصفحة.'}};"
if old_nav in s:
    s = s.replace(old_nav, new_nav, 1)
elif new_nav not in s:
    raise SystemExit('page navigation marker not found')

# Also make every render page-aware, including resize/continuous reading.
old_tail = "localStorage.lastPage=String(state.page);applyLayout()}catch{if(seq===state.renderSeq){$('readerStatus').textContent='تعذر عرض الصفحة';$('pdfWrap').innerHTML='<div class=\"loading\">تعذر عرض هذه الصفحة.</div>'}}}"
new_tail = "localStorage.lastPage=String(state.page);const cachedTranslation=state.translations.get(state.page);$('translation').textContent=cachedTranslation||'اضغط «ترجمة» لعرض ترجمة هذه الصفحة.';applyLayout()}catch{if(seq===state.renderSeq){$('readerStatus').textContent='تعذر عرض الصفحة';$('pdfWrap').innerHTML='<div class=\"loading\">تعذر عرض هذه الصفحة.</div>'}}}"
if old_tail in s:
    s = s.replace(old_tail, new_tail, 1)
elif new_tail not in s:
    raise SystemExit('render translation marker not found')

index.write_text(s, encoding='utf-8')

sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
if "pdf-reader-pwa-v18" in w:
    w = w.replace("pdf-reader-pwa-v18", "pdf-reader-pwa-v19", 1)
elif "pdf-reader-pwa-v19" not in w:
    raise SystemExit('service worker cache marker not found')
sw.write_text(w, encoding='utf-8')

print('Applied PWA v19 page-aware translation clearing and cache restore')

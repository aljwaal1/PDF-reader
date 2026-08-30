from pathlib import Path

index = Path('pwa/index.html')
s = index.read_text(encoding='utf-8')

# PWA v20: sentence-by-sentence live translation during speech + automatic next page.

# 1) Add auto-next/live translation state.
old_state = "const state={pdf:null,page:1,file:null,text:'',words:[],translations:new Map(),renderSeq:0,resizeTimer:null,speechSession:0,speaking:false,utterance:null,offset:0,pausedOffset:0,continuous:false,holdTimer:null,holdTriggered:false};"
new_state = "const state={pdf:null,page:1,file:null,text:'',words:[],translations:new Map(),renderSeq:0,resizeTimer:null,speechSession:0,speaking:false,utterance:null,offset:0,pausedOffset:0,continuous:false,autoNext:true,liveTranslationPage:0,liveTranslationParts:[],holdTimer:null,holdTriggered:false};"
if old_state in s:
    s = s.replace(old_state, new_state, 1)
elif new_state not in s:
    raise SystemExit('state marker not found')

# 2) Add visible auto-next toggle beside the layout selector.
old_toolbar = "<div class=\"toolbar\"><select id=\"layoutSelect\"><option value=\"pdf\" selected>PDF فقط</option><option value=\"translation\">الترجمة فقط</option><option value=\"below\">الترجمة أسفل الصفحة</option><option value=\"side\">جنبًا إلى جنب</option></select></div>"
new_toolbar = "<div class=\"toolbar\"><select id=\"layoutSelect\"><option value=\"pdf\" selected>PDF فقط</option><option value=\"translation\">الترجمة فقط</option><option value=\"below\">الترجمة أسفل الصفحة</option><option value=\"side\">جنبًا إلى جنب</option></select><button id=\"autoNextBtn\" class=\"btn\" title=\"الانتقال تلقائيًا للصفحة التالية\">⏭ تلقائي ✓</button></div>"
if old_toolbar in s:
    s = s.replace(old_toolbar, new_toolbar, 1)
elif new_toolbar not in s:
    raise SystemExit('toolbar marker not found')

# 3) Make toolbar items sit neatly next to each other.
old_css = ".toolbar{display:flex;justify-content:flex-start;margin-bottom:7px}"
new_css = ".toolbar{display:flex;justify-content:flex-start;align-items:center;gap:6px;margin-bottom:7px}"
if old_css in s:
    s = s.replace(old_css, new_css, 1)
elif new_css not in s:
    raise SystemExit('toolbar css marker not found')

# 4) Persistent translation storage per PDF file.
old_dbget = "async function dbGet(k){const db=await openDb();const v=await new Promise((ok,fail)=>{const r=db.transaction('books').objectStore('books').get(k);r.onsuccess=()=>ok(r.result);r.onerror=()=>fail(r.error)});db.close();return v}"
new_dbget = old_dbget + "\nfunction translationStoreKey(){const f=state.file;return f?`translations:${f.name}:${f.size}:${f.lastModified||0}`:''}\nasync function loadSavedTranslations(){const key=translationStoreKey();state.translations.clear();if(!key)return;try{const saved=await dbGet(key);if(saved&&typeof saved==='object')for(const [p,v] of Object.entries(saved))if(typeof v==='string'&&v.trim())state.translations.set(Number(p),v)}catch{}}\nasync function savePageTranslation(page,text){if(!text||!text.trim())return;state.translations.set(page,text);const key=translationStoreKey();if(!key)return;try{await dbPut(key,Object.fromEntries(state.translations))}catch{}}"
if "function translationStoreKey()" not in s:
    if old_dbget not in s:
        raise SystemExit('dbGet marker not found')
    s = s.replace(old_dbget, new_dbget, 1)

# 5) Load saved translations when reopening a book instead of clearing them.
old_load = "state.page=Math.min(Math.max(1,start),state.pdf.numPages);state.translations.clear();await renderPage()"
new_load = "state.page=Math.min(Math.max(1,start),state.pdf.numPages);await loadSavedTranslations();await renderPage()"
if old_load in s:
    s = s.replace(old_load, new_load, 1)
elif new_load not in s:
    raise SystemExit('load translations marker not found')

# 6) Sentence-sized speech chunks. Prefer punctuation, then fall back safely.
old_chunk = "function chunkEnd(start,max=220){const hard=Math.min(state.text.length,start+max);if(hard>=state.text.length)return hard;const sample=state.text.slice(start,hard);let cut=Math.max(sample.lastIndexOf('. '),sample.lastIndexOf('? '),sample.lastIndexOf('! '));if(cut<70)cut=sample.lastIndexOf(' ');return start+(cut>35?cut+1:sample.length)}"
new_chunk = "function chunkEnd(start,max=280){const rest=state.text.slice(start);if(!rest)return start;const limit=Math.min(rest.length,max),sample=rest.slice(0,limit);const m=sample.match(/^.{20,}?[.!?](?:\\s|$)/);if(m)return start+m[0].trimEnd().length;let cut=Math.max(sample.lastIndexOf('. '),sample.lastIndexOf('? '),sample.lastIndexOf('! '));if(cut<60)cut=sample.lastIndexOf(' ');return start+(cut>30?cut+1:sample.length)}"
if old_chunk in s:
    s = s.replace(old_chunk, new_chunk, 1)
elif new_chunk not in s:
    raise SystemExit('chunk marker not found')

# 7) Auto advance works for normal reading when enabled and for continuous mode.
old_advance = "async function advanceContinuous(){if(!state.continuous||!state.pdf)return;while(state.continuous&&state.page<state.pdf.numPages){state.page++;await renderPage(true);if(!state.continuous)return;if(state.text.trim()){speakFrom(0,true);return}}stopSpeech(true)}"
new_advance = "async function advanceContinuous(){if((!state.continuous&&!state.autoNext)||!state.pdf)return;while((state.continuous||state.autoNext)&&state.page<state.pdf.numPages){state.pausedOffset=0;state.offset=0;state.liveTranslationPage=0;state.liveTranslationParts=[];$('translation').textContent='';state.page++;await renderPage(true);if(!state.continuous&&!state.autoNext)return;if(state.text.trim()){speakFrom(0,state.continuous);return}}stopSpeech(true)}"
if old_advance in s:
    s = s.replace(old_advance, new_advance, 1)
elif new_advance not in s:
    raise SystemExit('advance marker not found')

# 8) Replace speech loop: translate each sentence, append Arabic progressively,
# save the completed page, then advance automatically when enabled.
old_speak_start = "function speakFrom(offset=0,keepContinuous=false){if(!('speechSynthesis'in window)||!state.text){if(keepContinuous)advanceContinuous();return}stopSpeech(false,keepContinuous);const session=state.speechSession,start=Math.max(0,Math.min(offset,state.text.length));state.offset=start;const runChunk=()=>{"
new_speak_start = "function speakFrom(offset=0,keepContinuous=false){if(!('speechSynthesis'in window)||!state.text){if(keepContinuous||state.autoNext)advanceContinuous();return}stopSpeech(false,keepContinuous);const session=state.speechSession,start=Math.max(0,Math.min(offset,state.text.length));state.offset=start;const speechPage=state.page;if(state.liveTranslationPage!==speechPage||start===0){state.liveTranslationPage=speechPage;state.liveTranslationParts=[];$('translation').textContent=''}if($('layoutSelect').value==='pdf'){$('layoutSelect').value='below';applyLayout()}const runChunk=async()=>{"
if old_speak_start in s:
    s = s.replace(old_speak_start, new_speak_start, 1)
elif new_speak_start not in s:
    raise SystemExit('speak start marker not found')

old_finish = "if(state.offset>=state.text.length){clearHighlight();if(state.continuous){advanceContinuous();return}stopSpeech(true);return}"
new_finish = "if(state.offset>=state.text.length){clearHighlight();const completed=state.liveTranslationPage===speechPage?state.liveTranslationParts.join('\\n\\n').trim():'';if(completed)await savePageTranslation(speechPage,completed);if(state.continuous||state.autoNext){advanceContinuous();return}stopSpeech(true);return}"
if old_finish in s:
    s = s.replace(old_finish, new_finish, 1)
elif new_finish not in s:
    raise SystemExit('speech finish marker not found')

old_chunk_decl = "const end=chunkEnd(state.offset),chunk=state.text.slice(state.offset,end).trim();if(!chunk){state.offset=end;runChunk();return}const baseOffset=state.offset,u=new SpeechSynthesisUtterance(chunk);"
new_chunk_decl = "const end=chunkEnd(state.offset),chunk=state.text.slice(state.offset,end).trim();if(!chunk){state.offset=end;runChunk();return}const baseOffset=state.offset;try{const ar=await translateChunk(chunk);if(session!==state.speechSession||state.page!==speechPage)return;if(ar&&ar.trim()){state.liveTranslationParts.push(ar.trim());$('translation').textContent=state.liveTranslationParts.join('\\n\\n');await savePageTranslation(speechPage,state.liveTranslationParts.join('\\n\\n'))}}catch{}if(session!==state.speechSession||state.page!==speechPage)return;const u=new SpeechSynthesisUtterance(chunk);"
if old_chunk_decl in s:
    s = s.replace(old_chunk_decl, new_chunk_decl, 1)
elif new_chunk_decl not in s:
    raise SystemExit('speech chunk translation marker not found')

# 9) Manual full-page translation now persists too.
old_manual_save = "state.translations.set(state.page,result);$('translation').textContent=result;"
new_manual_save = "await savePageTranslation(state.page,result);$('translation').textContent=result;"
if old_manual_save in s:
    s = s.replace(old_manual_save, new_manual_save, 1)
elif new_manual_save not in s:
    raise SystemExit('manual translation save marker not found')

# 10) Auto-next toggle behavior.
old_layout_handler = "function applyLayout(){const m=$('layoutSelect').value;$('layout').classList.toggle('side',m==='side');$('pdfPanel').classList.toggle('hidden',m==='translation');$('translationPanel').classList.toggle('hidden',m==='pdf')}$('layoutSelect').onchange=applyLayout;"
new_layout_handler = old_layout_handler + "\n$('autoNextBtn').onclick=()=>{state.autoNext=!state.autoNext;$('autoNextBtn').textContent=state.autoNext?'⏭ تلقائي ✓':'⏭ تلقائي';$('autoNextBtn').classList.toggle('primary',state.autoNext)};$('autoNextBtn').classList.toggle('primary',state.autoNext);"
if "$('autoNextBtn').onclick" not in s:
    if old_layout_handler not in s:
        raise SystemExit('layout handler marker not found')
    s = s.replace(old_layout_handler, new_layout_handler, 1)

index.write_text(s, encoding='utf-8')

# 11) Force fresh PWA shell.
sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
if "pdf-reader-pwa-v19" in w:
    w = w.replace("pdf-reader-pwa-v19", "pdf-reader-pwa-v20", 1)
elif "pdf-reader-pwa-v20" not in w:
    raise SystemExit('service worker cache marker not found')
sw.write_text(w, encoding='utf-8')

print('Applied PWA v20 live sentence translation, persistence, and auto-next reading')

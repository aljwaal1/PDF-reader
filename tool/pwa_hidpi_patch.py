from pathlib import Path

index = Path('pwa/index.html')
s = index.read_text(encoding='utf-8')

# 1) Keep the iOS-safe PDF.js output transform introduced in v17.
old_render = "const base=pg.getViewport({scale:1}),maxW=Math.max(280,$('pdfWrap').clientWidth-6),scale=Math.min(1.8,maxW/base.width),vp=pg.getViewport({scale}),nativeDpr=Math.max(1,window.devicePixelRatio||1),dpr=Math.min(nativeDpr,2);"
if old_render not in s:
    raise SystemExit('v17 render marker not found')

# 2) Force PDF.js internal glyph rendering on iOS/Safari. Some PDFs with embedded
# subset fonts render with missing/spaced glyphs through Safari FontFace. The
# internal renderer avoids that path while other platforms keep normal fonts.
old_load = "state.pdf=await pdfjsLib.getDocument({data}).promise;"
new_load = "const isIOS=/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);state.pdf=await pdfjsLib.getDocument({data,disableFontFace:isIOS,useSystemFonts:!isIOS}).promise;"
if old_load in s:
    s = s.replace(old_load, new_load, 1)
elif new_load not in s:
    raise SystemExit('PDF load marker not found')

# 3) Add reading-position state.
old_state = "const state={pdf:null,page:1,file:null,text:'',words:[],translations:new Map(),renderSeq:0,resizeTimer:null,speechSession:0,speaking:false,utterance:null,offset:0,continuous:false,holdTimer:null,holdTriggered:false};"
new_state = "const state={pdf:null,page:1,file:null,text:'',words:[],translations:new Map(),renderSeq:0,resizeTimer:null,speechSession:0,speaking:false,utterance:null,offset:0,pausedOffset:0,continuous:false,holdTimer:null,holdTriggered:false};"
if old_state in s:
    s = s.replace(old_state, new_state, 1)
elif new_state not in s:
    raise SystemExit('state marker not found')

# 4) Status now tells the user exactly where reading stopped.
old_status = "function updateStatus(){if(!state.pdf)return;$('readerStatus').textContent=state.continuous?`قراءة مستمرة • الصفحة ${state.page} من ${state.pdf.numPages}`:`الصفحة ${state.page} من ${state.pdf.numPages}`}"
new_status = "function updateStatus(){if(!state.pdf)return;const pct=state.text.length?Math.max(0,Math.min(100,Math.round((state.offset/state.text.length)*100))):0;const pos=state.offset>0&&state.offset<state.text.length?` • وصلت ${pct}% من الصفحة`:'';$('readerStatus').textContent=state.continuous?`قراءة مستمرة • الصفحة ${state.page} من ${state.pdf.numPages}${pos}`:`الصفحة ${state.page} من ${state.pdf.numPages}${pos}`}"
if old_status in s:
    s = s.replace(old_status, new_status, 1)
elif new_status not in s:
    raise SystemExit('status marker not found')

# 5) Stop remembers the current offset when the user pauses.
old_stop = "function stopSpeech(resetOffset=false,keepContinuous=false){state.speechSession++;try{speechSynthesis.cancel()}catch{}state.speaking=false;state.utterance=null;if(resetOffset)state.offset=0;if(!keepContinuous)state.continuous=false;resetSpeakButton();clearHighlight();updateStatus()}"
new_stop = "function stopSpeech(resetOffset=false,keepContinuous=false){state.speechSession++;try{speechSynthesis.cancel()}catch{}state.speaking=false;state.utterance=null;if(resetOffset){state.offset=0;state.pausedOffset=0}else if(state.offset>0&&state.offset<state.text.length){state.pausedOffset=state.offset}if(!keepContinuous)state.continuous=false;resetSpeakButton();clearHighlight();updateStatus()}"
if old_stop in s:
    s = s.replace(old_stop, new_stop, 1)
elif new_stop not in s:
    raise SystemExit('stopSpeech marker not found')

# 6) Boundary callbacks continuously update the visible progress position.
old_boundary = "u.onboundary=e=>{if(session!==state.speechSession||typeof e.charIndex!=='number')return;state.offset=Math.min(end,baseOffset+e.charIndex);drawWord(wordAt(state.offset))};"
new_boundary = "u.onboundary=e=>{if(session!==state.speechSession||typeof e.charIndex!=='number')return;state.offset=Math.min(end,baseOffset+e.charIndex);state.pausedOffset=state.offset;drawWord(wordAt(state.offset));updateStatus()};"
if old_boundary in s:
    s = s.replace(old_boundary, new_boundary, 1)
elif new_boundary not in s:
    raise SystemExit('speech boundary marker not found')

# 7) Resume exactly from the paused position.
old_single = "function startSinglePage(){state.continuous=false;state.offset=0;speakFrom(0,false)}"
new_single = "function startSinglePage(){state.continuous=false;const resume=state.pausedOffset>0&&state.pausedOffset<state.text.length?state.pausedOffset:0;state.offset=resume;speakFrom(resume,false)}"
if old_single in s:
    s = s.replace(old_single, new_single, 1)
elif new_single not in s:
    raise SystemExit('single-page start marker not found')

old_cont = "function startContinuous(){if(!state.pdf)return;state.continuous=true;state.offset=0;updateStatus();if(state.text.trim())speakFrom(0,true);else advanceContinuous()}"
new_cont = "function startContinuous(){if(!state.pdf)return;state.continuous=true;const resume=state.pausedOffset>0&&state.pausedOffset<state.text.length?state.pausedOffset:0;state.offset=resume;updateStatus();if(state.text.trim())speakFrom(resume,true);else advanceContinuous()}"
if old_cont in s:
    s = s.replace(old_cont, new_cont, 1)
elif new_cont not in s:
    raise SystemExit('continuous start marker not found')

# 8) Reset the local offset on an explicit page change.
old_nav = "$('prev').onclick=async()=>{if(state.pdf&&state.page>1){state.page--;await renderPage()}};$('next').onclick=async()=>{if(state.pdf&&state.page<state.pdf.numPages){state.page++;await renderPage()}};"
new_nav = "$('prev').onclick=async()=>{if(state.pdf&&state.page>1){stopSpeech(true);state.page--;await renderPage()}};$('next').onclick=async()=>{if(state.pdf&&state.page<state.pdf.numPages){stopSpeech(true);state.page++;await renderPage()}};"
if old_nav in s:
    s = s.replace(old_nav, new_nav, 1)
elif new_nav not in s:
    raise SystemExit('navigation marker not found')

index.write_text(s, encoding='utf-8')

# 9) Bump cache to v18.
sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
if "pdf-reader-pwa-v17" in w:
    w = w.replace("pdf-reader-pwa-v17", "pdf-reader-pwa-v18", 1)
elif "pdf-reader-pwa-v18" not in w:
    raise SystemExit('service worker cache marker not found')
sw.write_text(w, encoding='utf-8')

print('Applied PWA v18 iOS font fallback, resume reading, and position indicator')

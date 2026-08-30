from pathlib import Path

# Keep speech independent from translation latency on both PWA and Android.
# This patch intentionally lets TTS start immediately while translation queues in parallel.

# ---------- PWA ----------
index = Path('pwa/index.html')
s = index.read_text(encoding='utf-8')

old = "const baseOffset=state.offset;try{const ar=await translateChunk(chunk);if(session!==state.speechSession||state.page!==speechPage)return;if(ar&&ar.trim()){state.liveTranslationParts.push(ar.trim());$('translation').textContent=state.liveTranslationParts.join('\\n\\n');await savePageTranslation(speechPage,state.liveTranslationParts.join('\\n\\n'))}}catch{}if(session!==state.speechSession||state.page!==speechPage)return;const u=new SpeechSynthesisUtterance(chunk);"
new = "const baseOffset=state.offset;state.translationQueue=(state.translationQueue||Promise.resolve()).then(async()=>{try{const ar=await translateChunk(chunk);if(session!==state.speechSession)return;if(ar&&ar.trim()){state.liveTranslationParts.push(ar.trim());const full=state.liveTranslationParts.join('\\n\\n');if(state.page===speechPage)$('translation').textContent=full;await savePageTranslation(speechPage,full)}}catch{}});if(session!==state.speechSession||state.page!==speechPage)return;const u=new SpeechSynthesisUtterance(chunk);"
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('PWA blocking translation marker not found')

old_start = "if(state.liveTranslationPage!==speechPage||start===0){state.liveTranslationPage=speechPage;state.liveTranslationParts=[];$('translation').textContent=''}"
new_start = "if(state.liveTranslationPage!==speechPage||start===0){state.liveTranslationPage=speechPage;state.liveTranslationParts=[];state.translationQueue=Promise.resolve();$('translation').textContent=''}else if(!state.translationQueue){state.translationQueue=Promise.resolve()}"
if old_start in s:
    s = s.replace(old_start, new_start, 1)
elif new_start not in s:
    raise SystemExit('PWA translation queue start marker not found')

old_finish = "if(state.offset>=state.text.length){clearHighlight();clearReadingPosition(speechPage);const completed=state.liveTranslationPage===speechPage?state.liveTranslationParts.join('\\n\\n').trim():'';if(completed)await savePageTranslation(speechPage,completed);if(state.continuous||state.autoNext){advanceContinuous();return}stopSpeech(true);return}"
new_finish = "if(state.offset>=state.text.length){clearHighlight();clearReadingPosition(speechPage);try{await(state.translationQueue||Promise.resolve())}catch{}const completed=state.liveTranslationPage===speechPage?state.liveTranslationParts.join('\\n\\n').trim():'';if(completed)await savePageTranslation(speechPage,completed);if(state.continuous||state.autoNext){advanceContinuous();return}stopSpeech(true);return}"
if old_finish in s:
    s = s.replace(old_finish, new_finish, 1)
elif new_finish not in s:
    raise SystemExit('PWA translation queue finish marker not found')

index.write_text(s, encoding='utf-8')

sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
if "pdf-reader-pwa-v21" in w:
    w = w.replace("pdf-reader-pwa-v21", "pdf-reader-pwa-v22", 1)
elif "pdf-reader-pwa-v22" not in w:
    raise SystemExit('PWA v21 cache marker not found')
sw.write_text(w, encoding='utf-8')

# ---------- Android ----------
main = Path('lib/main.dart')
a = main.read_text(encoding='utf-8')
old_android = "    await _tts.setSpeechRate(_speechRate);\n    await _translateSentenceAt(actualOffset);\n    await _tts.speak(remaining);"
new_android = "    await _tts.setSpeechRate(_speechRate);\n    _translateSentenceAt(actualOffset);\n    await _tts.speak(remaining);"
if old_android in a:
    a = a.replace(old_android, new_android, 1)
elif new_android not in a:
    raise SystemExit('Android blocking translation marker not found')
main.write_text(a, encoding='utf-8')

print('Applied non-blocking speech fix: PWA v22 + Android')

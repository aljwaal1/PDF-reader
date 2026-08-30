from pathlib import Path

# Android: compact fixed reading HUD; PWA: fixed HUD above controls.

# ---------- Android ----------
p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

start = s.find('  Widget _readingCard() {')
end = s.find('\n  Widget _pdfView() {', start)
if start < 0 or end < 0:
    raise SystemExit('Android readingCard block not found')

new_card = r'''  Widget _readingCard() {
    if (_spokenText.isEmpty || (!_speaking && _spokenWord.isEmpty)) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    final bounds = _sentenceBounds(_spokenStart);
    final sentenceStart = bounds.$1;
    final sentenceEnd = bounds.$2;
    final wordStart = _spokenStart.clamp(sentenceStart, sentenceEnd);
    final wordEnd = _spokenEnd.clamp(wordStart, sentenceEnd);
    final before = _spokenText.substring(sentenceStart, wordStart);
    final current = wordEnd > wordStart ? _spokenText.substring(wordStart, wordEnd) : (_spokenWord.isEmpty ? '…' : _spokenWord);
    final after = _spokenText.substring(wordEnd, sentenceEnd);

    return Material(
      elevation: 8,
      borderRadius: BorderRadius.circular(16),
      color: Colors.white.withValues(alpha: .98),
      child: Container(
        constraints: const BoxConstraints(maxHeight: 154),
        padding: const EdgeInsets.fromLTRB(12, 9, 12, 9),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: scheme.outlineVariant)),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(width: 7, height: 7, decoration: BoxDecoration(color: scheme.primary, shape: BoxShape.circle)),
                const SizedBox(width: 7),
                const Expanded(child: Text('القراءة الآن', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Colors.black54))),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(99)),
                  child: Text(current.trim().isEmpty ? '…' : current.trim(), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: scheme.primary)),
                ),
              ],
            ),
            const SizedBox(height: 5),
            Directionality(
              textDirection: TextDirection.ltr,
              child: Text.rich(
                TextSpan(
                  style: const TextStyle(fontSize: 15.5, height: 1.35, color: Color(0xFF252633)),
                  children: [
                    TextSpan(text: before, style: const TextStyle(color: Color(0xFF777B88))),
                    TextSpan(text: current, style: TextStyle(fontWeight: FontWeight.w900, color: const Color(0xFF3033A8), backgroundColor: scheme.primaryContainer)),
                    TextSpan(text: after),
                  ],
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (_currentSentenceTranslation.isNotEmpty) ...[
              const SizedBox(height: 5),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
                decoration: BoxDecoration(color: scheme.secondaryContainer.withValues(alpha: .7), borderRadius: BorderRadius.circular(10)),
                child: Directionality(
                  textDirection: TextDirection.rtl,
                  child: Text(_currentSentenceTranslation, maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right, style: const TextStyle(fontSize: 14.5, height: 1.35, fontWeight: FontWeight.w700)),
                ),
              ),
            ],
            const SizedBox(height: 5),
            ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: _readingProgress, minHeight: 3, backgroundColor: scheme.surfaceContainerHighest)),
          ],
        ),
      ),
    );
  }
'''
s = s[:start] + new_card + s[end:]

old_body = '      body: Column(children: [Expanded(child: _body()), _readingCard()]),\n'
new_body = '''      body: Stack(
        children: [
          Positioned.fill(child: _body()),
          if (_spokenText.isNotEmpty && (_speaking || _spokenWord.isNotEmpty))
            Positioned(left: 8, right: 8, bottom: 8, child: _readingCard()),
        ],
      ),
'''
if old_body in s:
    s = s.replace(old_body, new_body, 1)
elif new_body not in s:
    raise SystemExit('Android body marker not found')

p.write_text(s, encoding='utf-8')

# ---------- PWA ----------
p = Path('pwa/index.html')
s = p.read_text(encoding='utf-8')

css_marker = '.pageBadge{position:fixed;z-index:41;'
hud_css = '''.readingHud{position:fixed;z-index:45;left:50%;bottom:calc(62px + env(safe-area-inset-bottom));transform:translateX(-50%);width:min(850px,calc(100% - 12px));background:rgba(255,255,255,.98);border:1px solid var(--line);border-radius:16px;padding:8px 11px;box-shadow:0 8px 28px rgba(18,25,45,.16);-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px)}.hudTop{display:flex;align-items:center;gap:7px;margin-bottom:4px}.hudDot{width:7px;height:7px;border-radius:50%;background:var(--accent);flex:none}.hudLabel{font-size:10.5px;font-weight:850;color:var(--muted)}.hudWord{margin-inline-start:auto;max-width:42%;padding:3px 8px;border-radius:99px;background:var(--accentSoft);color:var(--accent);font-weight:900;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;direction:ltr}.hudEnglish{direction:ltr;text-align:left;font-size:15px;line-height:1.35;font-weight:650;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.hudEnglish mark{background:#ffe889;color:#252633;border-radius:3px;padding:0 2px}.hudArabic{margin-top:5px;background:#f2f4ff;border-radius:9px;padding:5px 8px;direction:rtl;text-align:right;font-size:14.5px;line-height:1.35;font-weight:700;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}@media(max-width:700px){.readingHud{bottom:calc(60px + env(safe-area-inset-bottom));padding:7px 9px}.hudEnglish{font-size:14px}.hudArabic{font-size:13.5px}}'''
if hud_css not in s:
    if css_marker not in s:
        raise SystemExit('PWA CSS marker not found')
    s = s.replace(css_marker, hud_css + css_marker, 1)

html_marker = '<div id="pageBadge" class="pageBadge">0 / 0</div>'
hud_html = '<div id="readingHud" class="readingHud hidden"><div class="hudTop"><span class="hudDot"></span><span class="hudLabel">القراءة الآن</span><span id="hudWord" class="hudWord">…</span></div><div id="hudEnglish" class="hudEnglish"></div><div id="hudArabic" class="hudArabic hidden"></div></div>'
if hud_html not in s:
    if html_marker not in s:
        raise SystemExit('PWA HTML marker not found')
    s = s.replace(html_marker, hud_html + html_marker, 1)

state_old = "holdTimer:null,holdTriggered:false};"
state_new = "holdTimer:null,holdTriggered:false,hudChunkStart:-1,hudChunk:'',hudArabic:''};"
if state_old in s:
    s = s.replace(state_old, state_new, 1)
elif state_new not in s:
    raise SystemExit('PWA state marker not found')

fn_marker = 'function clearHighlight(){document.querySelector(\'.wordHighlightLayer\')?.replaceChildren()}\n'
hud_fns = r'''function escapeHtml(v){return String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function updateReadingHud(pos=state.offset){const hud=$('readingHud');if(!hud||!state.hudChunk)return;hud.classList.remove('hidden');const w=wordAt(pos);const wordText=w?state.text.slice(w.start,w.end):'';$('hudWord').textContent=wordText||'…';let chunk=state.hudChunk,local=Math.max(0,Math.min(chunk.length,pos-state.hudChunkStart));let a=local,b=local;if(w){a=Math.max(0,w.start-state.hudChunkStart);b=Math.min(chunk.length,w.end-state.hudChunkStart)}$('hudEnglish').innerHTML=escapeHtml(chunk.slice(0,a))+(b>a?'<mark>'+escapeHtml(chunk.slice(a,b))+'</mark>':'')+escapeHtml(chunk.slice(b));const ar=$('hudArabic');if(state.hudArabic){ar.textContent=state.hudArabic;ar.classList.remove('hidden')}else{ar.textContent='';ar.classList.add('hidden')}}
function setReadingHud(chunk,start){state.hudChunk=chunk||'';state.hudChunkStart=start;state.hudArabic='';updateReadingHud(start)}
function hideReadingHud(){state.hudChunk='';state.hudChunkStart=-1;state.hudArabic='';$('readingHud')?.classList.add('hidden')}
'''
if hud_fns not in s:
    if fn_marker not in s:
        raise SystemExit('PWA function marker not found')
    s = s.replace(fn_marker, fn_marker + hud_fns, 1)

old_stop = "resetSpeakButton();clearHighlight();updateStatus()}"
new_stop = "resetSpeakButton();clearHighlight();hideReadingHud();updateStatus()}"
if old_stop in s:
    s = s.replace(old_stop, new_stop, 1)
elif new_stop not in s:
    raise SystemExit('PWA stopSpeech marker not found')

chunk_old = "const baseOffset=state.offset;state.translationQueue="
chunk_new = "const baseOffset=state.offset;setReadingHud(chunk,baseOffset);state.translationQueue="
if chunk_old in s:
    s = s.replace(chunk_old, chunk_new, 1)
elif chunk_new not in s:
    raise SystemExit('PWA chunk HUD marker not found')

ar_old = "if(state.page===speechPage)$('translation').textContent=full;await savePageTranslation(speechPage,full)"
ar_new = "if(state.page===speechPage){$('translation').textContent=full;if(state.hudChunkStart===baseOffset){state.hudArabic=ar.trim();updateReadingHud(state.offset)}}await savePageTranslation(speechPage,full)"
if ar_old in s:
    s = s.replace(ar_old, ar_new, 1)
elif ar_new not in s:
    raise SystemExit('PWA Arabic HUD marker not found')

boundary_old = "drawWord(wordAt(state.offset));updateStatus()"
boundary_new = "drawWord(wordAt(state.offset));updateReadingHud(state.offset);updateStatus()"
if boundary_old in s:
    s = s.replace(boundary_old, boundary_new, 1)
elif boundary_new not in s:
    raise SystemExit('PWA boundary HUD marker not found')

p.write_text(s, encoding='utf-8')

# Bump SW cache to force the new HUD to appear immediately on installed PWA.
sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
import re
m = re.search(r"pdf-reader-pwa-v(\d+)", w)
if m:
    n = int(m.group(1))
    w = w.replace(m.group(0), f'pdf-reader-pwa-v{n+1}', 1)
sw.write_text(w, encoding='utf-8')

print('Applied compact fixed reading HUD to Android and PWA')

from pathlib import Path

# ============================================================
# PWA v21 — persistent reading position + automatic visual follow
# ============================================================
index = Path('pwa/index.html')
s = index.read_text(encoding='utf-8')

old_saved = "async function savePageTranslation(page,text){if(!text||!text.trim())return;state.translations.set(page,text);const key=translationStoreKey();if(!key)return;try{await dbPut(key,Object.fromEntries(state.translations))}catch{}}"
new_saved = old_saved + "\nfunction readingPositionKey(page=state.page){const f=state.file;return f?`reading-position:${f.name}:${f.size}:${f.lastModified||0}:${page}`:''}\nfunction saveReadingPosition(){const key=readingPositionKey();if(!key)return;const pos=Math.max(0,Math.min(state.text.length,state.pausedOffset||state.offset||0));try{localStorage.setItem(key,String(pos))}catch{}}\nfunction restoreReadingPosition(){const key=readingPositionKey();if(!key||!state.text)return;let pos=0;try{pos=Number(localStorage.getItem(key)||0)}catch{}if(Number.isFinite(pos)&&pos>0&&pos<state.text.length){state.pausedOffset=pos;state.offset=pos}else{state.pausedOffset=0;state.offset=0}}\nfunction clearReadingPosition(page=state.page){const key=readingPositionKey(page);if(key)try{localStorage.removeItem(key)}catch{}}"
if "function readingPositionKey(" not in s:
    if old_saved not in s: raise SystemExit('PWA translation persistence marker not found')
    s = s.replace(old_saved, new_saved, 1)

old_draw = "const r=wordRect(word);if(!r)return;const s=stage.getBoundingClientRect(),padX=1.5,padY=.5,box=document.createElement('div');box.className='wordHighlight';Object.assign(box.style,{left:`${r.left-s.left-padX}px`,top:`${r.top-s.top-padY}px`,width:`${r.right-r.left+padX*2}px`,height:`${r.bottom-r.top+padY*2}px`});layer.append(box)}"
new_draw = "const r=wordRect(word);if(!r)return;const s=stage.getBoundingClientRect(),padX=1.5,padY=.5,box=document.createElement('div');box.className='wordHighlight';Object.assign(box.style,{left:`${r.left-s.left-padX}px`,top:`${r.top-s.top-padY}px`,width:`${r.right-r.left+padX*2}px`,height:`${r.bottom-r.top+padY*2}px`});layer.append(box);const vh=window.innerHeight||document.documentElement.clientHeight;if(r.top<vh*.18||r.bottom>vh*.76)requestAnimationFrame(()=>box.scrollIntoView({behavior:'smooth',block:'center',inline:'nearest'}))}"
if old_draw in s:
    s = s.replace(old_draw, new_draw, 1)
elif "scrollIntoView({behavior:'smooth'" not in s:
    raise SystemExit('PWA drawWord marker not found')

old_render_tail = "localStorage.lastPage=String(state.page);const cachedTranslation=state.translations.get(state.page);$('translation').textContent=cachedTranslation||'اضغط «ترجمة» لعرض ترجمة هذه الصفحة.';applyLayout()"
new_render_tail = "localStorage.lastPage=String(state.page);restoreReadingPosition();const cachedTranslation=state.translations.get(state.page);$('translation').textContent=cachedTranslation||'اضغط «ترجمة» لعرض ترجمة هذه الصفحة.';updateStatus();applyLayout()"
if old_render_tail in s:
    s = s.replace(old_render_tail, new_render_tail, 1)
elif new_render_tail not in s:
    raise SystemExit('PWA render position marker not found')

old_boundary = "state.offset=Math.min(end,baseOffset+e.charIndex);state.pausedOffset=state.offset;drawWord(wordAt(state.offset));updateStatus()"
new_boundary = "state.offset=Math.min(end,baseOffset+e.charIndex);state.pausedOffset=state.offset;saveReadingPosition();drawWord(wordAt(state.offset));updateStatus()"
if old_boundary in s:
    s = s.replace(old_boundary, new_boundary, 1)
elif new_boundary not in s:
    raise SystemExit('PWA boundary marker not found')

old_finish = "if(state.offset>=state.text.length){clearHighlight();const completed=state.liveTranslationPage===speechPage?state.liveTranslationParts.join('\\n\\n').trim():'';if(completed)await savePageTranslation(speechPage,completed);if(state.continuous||state.autoNext){advanceContinuous();return}stopSpeech(true);return}"
new_finish = "if(state.offset>=state.text.length){clearHighlight();clearReadingPosition(speechPage);const completed=state.liveTranslationPage===speechPage?state.liveTranslationParts.join('\\n\\n').trim():'';if(completed)await savePageTranslation(speechPage,completed);if(state.continuous||state.autoNext){advanceContinuous();return}stopSpeech(true);return}"
if old_finish in s:
    s = s.replace(old_finish, new_finish, 1)
elif new_finish not in s:
    raise SystemExit('PWA finish marker not found')

old_stop = "if(resetOffset){state.offset=0;state.pausedOffset=0}else if(state.offset>0&&state.offset<state.text.length){state.pausedOffset=state.offset}"
new_stop = "if(resetOffset){state.offset=0;state.pausedOffset=0}else if(state.offset>0&&state.offset<state.text.length){state.pausedOffset=state.offset;saveReadingPosition()}"
if old_stop in s:
    s = s.replace(old_stop, new_stop, 1)
elif new_stop not in s:
    raise SystemExit('PWA stop marker not found')

index.write_text(s, encoding='utf-8')

sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
if "pdf-reader-pwa-v20" in w:
    w = w.replace("pdf-reader-pwa-v20", "pdf-reader-pwa-v21", 1)
elif "pdf-reader-pwa-v21" not in w:
    raise SystemExit('PWA cache marker not found')
sw.write_text(w, encoding='utf-8')

# ============================================================
# Android — guided sentence reading, live Arabic, resume, auto-next
# ============================================================
main = Path('lib/main.dart')
a = main.read_text(encoding='utf-8')

old_fields = "  int _speechOffset = 0;\n  TranslationLayout _layout = TranslationLayout.pdfOnly;"
new_fields = "  int _speechOffset = 0;\n  int _resumeOffset = 0;\n  int _lastSentenceStart = -1;\n  bool _autoNext = true;\n  bool _translatingSentence = false;\n  String _currentSentenceTranslation = '';\n  final Map<int, Map<int, String>> _sentenceTranslations = {};\n  TranslationLayout _layout = TranslationLayout.pdfOnly;"
if old_fields in a:
    a = a.replace(old_fields, new_fields, 1)
elif new_fields not in a:
    raise SystemExit('Android fields marker not found')

old_completion = "    _tts.setCompletionHandler(() {\n      if (mounted) setState(() => _speaking = false);\n    });"
new_completion = "    _tts.setCompletionHandler(() {\n      _handleSpeechComplete();\n    });"
if old_completion in a:
    a = a.replace(old_completion, new_completion, 1)
elif new_completion not in a:
    raise SystemExit('Android completion marker not found')

old_progress = "      setState(() {\n        _spokenWord = word;\n        _spokenStart = absoluteStart;\n        _spokenEnd = absoluteEnd;\n      });"
new_progress = "      setState(() {\n        _spokenWord = word;\n        _spokenStart = absoluteStart;\n        _spokenEnd = absoluteEnd;\n        _resumeOffset = absoluteStart;\n      });\n      _saveReadingOffset(_page, absoluteStart);\n      _translateSentenceAt(absoluteStart);"
if old_progress in a:
    a = a.replace(old_progress, new_progress, 1)
elif new_progress not in a:
    raise SystemExit('Android progress marker not found')

marker = "  Future<void> _translatePage() async {"
helpers = """  String _positionKey(int page) => 'readingOffset:${widget.filePath}:$page';
  String _translationKey(int page) => 'pageTranslation:${widget.filePath}:$page';

  Future<void> _saveReadingOffset(int page, int offset) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_positionKey(page), offset);
  }

  Future<int> _loadReadingOffset(int page) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_positionKey(page)) ?? 0;
  }

  Future<void> _clearReadingOffset(int page) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_positionKey(page));
  }

  Future<void> _saveTranslation(int page, String text) async {
    if (text.trim().isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_translationKey(page), text);
  }

  Future<void> _restorePageState(int page) async {
    final prefs = await SharedPreferences.getInstance();
    final savedTranslation = prefs.getString(_translationKey(page));
    final offset = prefs.getInt(_positionKey(page)) ?? 0;
    if (!mounted || page != _page) return;
    setState(() {
      _resumeOffset = offset;
      _currentSentenceTranslation = '';
      _lastSentenceStart = -1;
      if (savedTranslation != null && savedTranslation.trim().isNotEmpty) {
        _translations[page] = savedTranslation;
      }
    });
  }

  Future<void> _translateSentenceAt(int position) async {
    if (_spokenText.isEmpty || _translatingSentence) return;
    final bounds = _sentenceBounds(position);
    final start = bounds.$1;
    final end = bounds.$2;
    if (end <= start || start == _lastSentenceStart) return;
    final sentence = _spokenText.substring(start, end).trim();
    if (sentence.isEmpty) return;
    _lastSentenceStart = start;
    _translatingSentence = true;
    try {
      final translated = await _translator.translateText(sentence);
      final pageMap = _sentenceTranslations.putIfAbsent(_page, () => <int, String>{});
      pageMap[start] = translated;
      final keys = pageMap.keys.toList()..sort();
      final full = keys.map((key) => pageMap[key]!).join('\\n\\n');
      if (!mounted) return;
      setState(() {
        _currentSentenceTranslation = translated;
        _translations[_page] = full;
      });
      await _saveTranslation(_page, full);
    } catch (_) {
      // Keep reading even if one sentence cannot be translated.
    } finally {
      _translatingSentence = false;
    }
  }

  Future<void> _startSpeechFrom(int offset) async {
    final text = await _extractCurrentPage();
    if (text.isEmpty) {
      _showMessage('لا يوجد نص إنجليزي قابل للقراءة في هذه الصفحة.');
      return;
    }
    final safeOffset = offset.clamp(0, text.length);
    final source = text.substring(safeOffset);
    final remaining = source.trimLeft();
    final actualOffset = safeOffset + (source.length - remaining.length);
    if (remaining.isEmpty) return;
    if (!mounted) return;
    setState(() {
      _spokenText = text;
      _speechOffset = actualOffset;
      _resumeOffset = actualOffset;
      _spokenStart = actualOffset;
      _spokenEnd = actualOffset;
      _spokenWord = '';
      _speaking = true;
      _lastSentenceStart = -1;
    });
    await _tts.setSpeechRate(_speechRate);
    await _translateSentenceAt(actualOffset);
    await _tts.speak(remaining);
  }

  Future<void> _handleSpeechComplete() async {
    if (!mounted) return;
    final completedPage = _page;
    await _clearReadingOffset(completedPage);
    setState(() {
      _speaking = false;
      _resumeOffset = 0;
    });
    if (_autoNext && completedPage < _pageCount) {
      await _go(completedPage + 1, keepAutoReading: true);
      await Future<void>.delayed(const Duration(milliseconds: 220));
      if (mounted && _page == completedPage + 1) await _startSpeechFrom(_resumeOffset);
    }
  }

"""
if "Future<void> _translateSentenceAt(" not in a:
    if marker not in a: raise SystemExit('Android translate marker not found')
    a = a.replace(marker, helpers + marker, 1)

old_translate_save = "          _translations[_page] = translated;\n          if (_layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;"
new_translate_save = "          _translations[_page] = translated;\n          if (_layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;\n          _saveTranslation(_page, translated);"
if old_translate_save in a:
    a = a.replace(old_translate_save, new_translate_save, 1)
elif new_translate_save not in a:
    raise SystemExit('Android full translation save marker not found')

start_toggle = a.find("  Future<void> _toggleSpeech() async {")
end_toggle = a.find("\n  int _restartOffset()", start_toggle)
if start_toggle < 0 or end_toggle < 0:
    raise SystemExit('Android toggle speech block not found')
new_toggle = """  Future<void> _toggleSpeech() async {
    if (_speaking) {
      final resume = _restartOffset();
      await _tts.stop();
      await _saveReadingOffset(_page, resume);
      if (mounted) setState(() {
        _speaking = false;
        _resumeOffset = resume;
      });
      return;
    }
    final saved = _resumeOffset > 0 ? _resumeOffset : await _loadReadingOffset(_page);
    await _startSpeechFrom(saved);
  }
"""
a = a[:start_toggle] + new_toggle + a[end_toggle:]

old_go_sig = "  Future<void> _go(int nextPage) async {"
new_go_sig = "  Future<void> _go(int nextPage, {bool keepAutoReading = false}) async {"
if old_go_sig in a:
    a = a.replace(old_go_sig, new_go_sig, 1)
elif new_go_sig not in a:
    raise SystemExit('Android go signature marker not found')

old_go_state = "      _speechOffset = 0;\n      _showTranscript = false;"
new_go_state = "      _speechOffset = 0;\n      _resumeOffset = 0;\n      _spokenText = '';\n      _currentSentenceTranslation = '';\n      _lastSentenceStart = -1;\n      _showTranscript = false;"
if old_go_state in a:
    a = a.replace(old_go_state, new_go_state, 1)
elif new_go_state not in a:
    raise SystemExit('Android go reset marker not found')

old_go_tail = "    await _pdfController.goToPage(pageNumber: nextPage, anchor: PdfPageAnchor.top);\n  }"
new_go_tail = "    await _pdfController.goToPage(pageNumber: nextPage, anchor: PdfPageAnchor.top);\n    await _restorePageState(nextPage);\n  }"
if old_go_tail in a:
    a = a.replace(old_go_tail, new_go_tail, 1)
elif new_go_tail not in a:
    raise SystemExit('Android go tail marker not found')

old_page_changed = "            setState(() => _page = pageNumber);\n            _savePage(pageNumber);"
new_page_changed = "            setState(() {\n              _page = pageNumber;\n              _currentSentenceTranslation = '';\n              _lastSentenceStart = -1;\n            });\n            _savePage(pageNumber);\n            _restorePageState(pageNumber);"
if old_page_changed in a:
    a = a.replace(old_page_changed, new_page_changed, 1)
elif new_page_changed not in a:
    raise SystemExit('Android page changed marker not found')

old_reading_after = "            const SizedBox(height: 7),\n            ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: _readingProgress, minHeight: 4, backgroundColor: scheme.surfaceContainerHighest)),"
new_reading_after = "            if (_currentSentenceTranslation.isNotEmpty) ...[\n              const SizedBox(height: 8),\n              Directionality(\n                textDirection: TextDirection.rtl,\n                child: Container(\n                  width: double.infinity,\n                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),\n                  decoration: BoxDecoration(color: scheme.secondaryContainer.withValues(alpha: .55), borderRadius: BorderRadius.circular(10)),\n                  child: Text(_currentSentenceTranslation, style: const TextStyle(fontSize: 15, height: 1.55, fontWeight: FontWeight.w600)),\n                ),\n              ),\n            ],\n            const SizedBox(height: 7),\n            ClipRRect(borderRadius: BorderRadius.circular(99), child: LinearProgressIndicator(value: _readingProgress, minHeight: 4, backgroundColor: scheme.surfaceContainerHighest)),"
if old_reading_after in a:
    a = a.replace(old_reading_after, new_reading_after, 1)
elif "_currentSentenceTranslation.isNotEmpty" not in a:
    raise SystemExit('Android reading translation UI marker not found')

old_actions = "        actions: [PopupMenuButton<TranslationLayout>(tooltip: 'طريقة عرض الترجمة', icon: const Icon(Icons.view_quilt_outlined, size: 22), initialValue: _layout, onSelected: (value) => setState(() => _layout = value), itemBuilder: (_) => TranslationLayout.values.map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value)))).toList())],"
new_actions = "        actions: [IconButton(tooltip: _autoNext ? 'الانتقال التلقائي مفعّل' : 'الانتقال التلقائي متوقف', onPressed: () => setState(() => _autoNext = !_autoNext), icon: Icon(_autoNext ? Icons.skip_next_rounded : Icons.skip_next_outlined, color: _autoNext ? scheme.primary : null)), PopupMenuButton<TranslationLayout>(tooltip: 'طريقة عرض الترجمة', icon: const Icon(Icons.view_quilt_outlined, size: 22), initialValue: _layout, onSelected: (value) => setState(() => _layout = value), itemBuilder: (_) => TranslationLayout.values.map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value)))).toList())],"
if old_actions in a:
    a = a.replace(old_actions, new_actions, 1)
elif new_actions not in a:
    raise SystemExit('Android appbar actions marker not found')

main.write_text(a, encoding='utf-8')

print('Applied PWA v21 and Android guided-reading enhancements')

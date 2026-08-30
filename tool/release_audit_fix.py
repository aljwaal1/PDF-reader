from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Remove accidental duplicates from repeated patch application.
s = s.replace("          _saveTranslation(_page, translated);\n          _saveTranslation(_page, translated);", "          _saveTranslation(_page, translated);", 1)
translation_card = """            if (_currentSentenceTranslation.isNotEmpty) ...[
              const SizedBox(height: 8),
              Directionality(
                textDirection: TextDirection.rtl,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(color: scheme.secondaryContainer.withValues(alpha: .55), borderRadius: BorderRadius.circular(10)),
                  child: Text(_currentSentenceTranslation, style: const TextStyle(fontSize: 15, height: 1.55, fontWeight: FontWeight.w600)),
                ),
              ),
            ],
"""
s = s.replace(translation_card + translation_card, translation_card, 1)

# Replace the fragile global completion callback with per-speech run tokens.
s = s.replace("  bool _translatingSentence = false;\n", "  int _speechRunToken = 0;\n  Future<void> _sentenceTranslationQueue = Future<void>.value();\n", 1)
s = s.replace("""    _tts.setCompletionHandler(() {
      _handleSpeechComplete();
    });
""", "", 1)

# Translation model preparation is shared instead of racing the first sentence.
s = s.replace("  TranslationLayout _layout = TranslationLayout.pdfOnly;", "  Future<void>? _translationSetup;\n  TranslationLayout _layout = TranslationLayout.pdfOnly;", 1)
s = s.replace("    _prepareTranslationModels();", "    _translationSetup = _prepareTranslationModels();", 1)

old_extract = """  Future<String> _extractCurrentPage() async {
    if (_pageText.containsKey(_page)) return _pageText[_page]!;
    if (!_pdfController.isReady || _page < 1 || _page > _pdfController.pages.length) return '';
    final pageText = await _pdfController.pages[_page - 1].loadText();
    final text = _cleanText(pageText?.fullText ?? '');
    _pageText[_page] = text;
    return text;
  }
"""
new_extract = """  Future<String> _extractCurrentPage({int? pageNumber}) async {
    final targetPage = pageNumber ?? _page;
    if (_pageText.containsKey(targetPage)) return _pageText[targetPage]!;
    if (!_pdfController.isReady || targetPage < 1 || targetPage > _pdfController.pages.length) return '';
    final pageText = await _pdfController.pages[targetPage - 1].loadText();
    final text = _cleanText(pageText?.fullText ?? '');
    _pageText[targetPage] = text;
    return text;
  }
"""
if old_extract in s:
    s = s.replace(old_extract, new_extract, 1)
elif new_extract not in s:
    raise SystemExit('extractCurrentPage audit marker not found')

start = s.find("  Future<void> _translateSentenceAt(int position) async {")
end = s.find("\n  Future<void> _startSpeechFrom", start)
if start < 0 or end < 0:
    raise SystemExit('translateSentence block not found')
new_sentence = """  Future<void> _translateSentenceAt(int position) {
    if (_spokenText.isEmpty) return Future<void>.value();
    final sourceText = _spokenText;
    final page = _page;
    final bounds = _sentenceBounds(position);
    final sentenceStart = bounds.$1;
    final sentenceEnd = bounds.$2;
    if (sentenceEnd <= sentenceStart || sentenceStart == _lastSentenceStart) return Future<void>.value();
    final sentence = sourceText.substring(sentenceStart, sentenceEnd).trim();
    if (sentence.isEmpty) return Future<void>.value();
    _lastSentenceStart = sentenceStart;
    _sentenceTranslationQueue = _sentenceTranslationQueue.then((_) async {
      try {
        await (_translationSetup ??= _prepareTranslationModels());
        final translated = await _translator.translateText(sentence);
        final pageMap = _sentenceTranslations.putIfAbsent(page, () => <int, String>{});
        pageMap[sentenceStart] = translated;
        final keys = pageMap.keys.toList()..sort();
        final full = keys.map((key) => pageMap[key]!).join('\\n\\n');
        await _saveTranslation(page, full);
        if (!mounted || page != _page || sourceText != _spokenText) return;
        setState(() {
          _currentSentenceTranslation = translated;
          _translations[page] = full;
        });
      } catch (_) {
        // Speech must never depend on translation availability.
      }
    });
    return _sentenceTranslationQueue;
  }
"""
s = s[:start] + new_sentence + s[end:]

start = s.find("  Future<void> _startSpeechFrom(int offset) async {")
end = s.find("\n  Future<void> _handleSpeechComplete", start)
if start < 0 or end < 0:
    raise SystemExit('startSpeech block not found')
new_start_speech = """  Future<void> _startSpeechFrom(int offset) async {
    final pageAtStart = _page;
    final text = await _extractCurrentPage(pageNumber: pageAtStart);
    if (!mounted || pageAtStart != _page) return;
    if (text.isEmpty) {
      _showMessage('لا يوجد نص إنجليزي قابل للقراءة في هذه الصفحة.');
      return;
    }
    final safeOffset = offset.clamp(0, text.length);
    final source = text.substring(safeOffset);
    final remaining = source.trimLeft();
    final actualOffset = safeOffset + (source.length - remaining.length);
    if (remaining.isEmpty) return;
    final runToken = ++_speechRunToken;
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
    await _tts.setLanguage('en-US');
    await _tts.setSpeechRate(_speechRate);
    await _tts.awaitSpeakCompletion(true);
    _translateSentenceAt(actualOffset);
    final result = await _tts.speak(remaining);
    if (!mounted || runToken != _speechRunToken || pageAtStart != _page) return;
    if (result == 1) {
      await _handleSpeechComplete(pageAtStart, runToken);
    } else {
      setState(() => _speaking = false);
      _showMessage('تعذر تشغيل الصوت. تحقق من إعدادات تحويل النص إلى كلام (TTS).');
    }
  }
"""
s = s[:start] + new_start_speech + s[end:]

start = s.find("  Future<void> _handleSpeechComplete() async {")
end = s.find("\n  Future<void> _translatePage", start)
if start < 0 or end < 0:
    raise SystemExit('speech complete block not found')
new_complete = """  Future<void> _handleSpeechComplete(int completedPage, int runToken) async {
    if (!mounted || runToken != _speechRunToken || completedPage != _page) return;
    await _clearReadingOffset(completedPage);
    if (!mounted || runToken != _speechRunToken) return;
    setState(() {
      _speaking = false;
      _resumeOffset = 0;
    });
    if (_autoNext && completedPage < _pageCount) {
      await _go(completedPage + 1);
      await Future<void>.delayed(const Duration(milliseconds: 180));
      if (mounted && _page == completedPage + 1) await _startSpeechFrom(_resumeOffset);
    }
  }
"""
s = s[:start] + new_complete + s[end:]

# Page translation is tied to the page where the request started.
start = s.find("  Future<void> _translatePage() async {")
end = s.find("\n  Future<void> _toggleSpeech", start)
if start < 0 or end < 0:
    raise SystemExit('translatePage block not found')
new_translate_page = """  Future<void> _translatePage() async {
    final targetPage = _page;
    if (_translations.containsKey(targetPage)) {
      if (mounted) setState(() {
        if (_layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;
      });
      return;
    }
    setState(() => _busy = true);
    try {
      final text = await _extractCurrentPage(pageNumber: targetPage);
      if (text.isEmpty) {
        _showMessage('لم يتم العثور على نص قابل للاستخراج في هذه الصفحة.');
        return;
      }
      await (_translationSetup ??= _prepareTranslationModels());
      final translated = await _translator.translateText(text);
      await _saveTranslation(targetPage, translated);
      if (mounted) {
        setState(() {
          _translations[targetPage] = translated;
          if (_page == targetPage && _layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;
        });
      }
    } catch (_) {
      _showMessage('تعذر ترجمة الصفحة. تحقق من الاتصال عند تنزيل نموذج الترجمة لأول مرة.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
"""
s = s[:start] + new_translate_page + s[end:]

# Manual stop invalidates the current utterance so it can never trigger auto-next.
s = s.replace("""      final resume = _restartOffset();
      await _tts.stop();
      await _saveReadingOffset(_page, resume);""", """      final resume = _restartOffset();
      ++_speechRunToken;
      await _tts.stop();
      await _saveReadingOffset(_page, resume);""", 1)

start = s.find("  Future<void> _setRate(double value) async {")
end = s.find("\n  Future<void> _savePage", start)
if start < 0 or end < 0:
    raise SystemExit('setRate block not found')
new_rate = """  Future<void> _setRate(double value) async {
    final rate = value.clamp(.25, 1.0).toDouble();
    final wasSpeaking = _speaking && _spokenText.isNotEmpty;
    final resumeAt = wasSpeaking ? _restartOffset() : 0;
    if (mounted) setState(() => _speechRate = rate);
    if (!wasSpeaking) {
      await _tts.setSpeechRate(rate);
      return;
    }
    ++_speechRunToken;
    await _tts.stop();
    if (!mounted || resumeAt >= _spokenText.length) return;
    await _startSpeechFrom(resumeAt);
  }
"""
s = s[:start] + new_rate + s[end:]

s = s.replace("  Future<void> _go(int nextPage, {bool keepAutoReading = false}) async {", "  Future<void> _go(int nextPage) async {", 1)
s = s.replace("""    if (!_pdfController.isReady || nextPage < 1 || nextPage > _pageCount) return;
    await _tts.stop();""", """    if (!_pdfController.isReady || nextPage < 1 || nextPage > _pageCount) return;
    ++_speechRunToken;
    await _tts.stop();""", 1)

# Swiping pages manually must stop speech from the old page.
old_page_changed = """          onPageChanged: (pageNumber) {
            if (pageNumber == null) return;
            setState(() {
              _page = pageNumber;
              _currentSentenceTranslation = '';
              _lastSentenceStart = -1;
            });
            _savePage(pageNumber);
            _restorePageState(pageNumber);
          },
"""
new_page_changed = """          onPageChanged: (pageNumber) {
            if (pageNumber == null) return;
            final changed = pageNumber != _page;
            if (changed) {
              ++_speechRunToken;
              _tts.stop();
            }
            setState(() {
              _page = pageNumber;
              if (changed) {
                _speaking = false;
                _spokenText = '';
                _spokenWord = '';
                _spokenStart = 0;
                _spokenEnd = 0;
                _speechOffset = 0;
                _resumeOffset = 0;
              }
              _currentSentenceTranslation = '';
              _lastSentenceStart = -1;
            });
            _savePage(pageNumber);
            _restorePageState(pageNumber);
          },
"""
if old_page_changed in s:
    s = s.replace(old_page_changed, new_page_changed, 1)
elif new_page_changed not in s:
    raise SystemExit('pageChanged audit marker not found')

s = s.replace("""          onViewerReady: (document, controller) {
            if (mounted) setState(() => _pageCount = controller.pageCount);
          },""", """          onViewerReady: (document, controller) {
            if (mounted) {
              setState(() => _pageCount = controller.pageCount);
              _restorePageState(_page);
            }
          },""", 1)

s = s.replace("""  void dispose() {
    _tts.stop();""", """  void dispose() {
    ++_speechRunToken;
    _tts.stop();""", 1)

p.write_text(s, encoding='utf-8')
print('Applied release audit fixes: speech lifecycle, translation page affinity, duplicate cleanup')

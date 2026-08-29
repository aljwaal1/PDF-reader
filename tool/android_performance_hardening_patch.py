from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Keep heavyweight structured PDF text bounded. PdfPageText contains character
# geometry and can become expensive in long books if every visited page remains
# strongly referenced for the entire reader session.
s = s.replace(
    '  final Map<int, PdfPageText> _structuredText = {};\n',
    '  final Map<int, PdfPageText> _structuredText = {};\n'
    '  final List<int> _structuredTextLru = <int>[];\n'
    '  final List<int> _pageTextLru = <int>[];\n'
    '  SharedPreferences? _prefs;\n'
    '  Future<void>? _translationModelsFuture;\n'
    '  bool _translationModelsReady = false;\n',
    1,
)

# Serialize model preparation. Page translation and selected-text translation
# can otherwise race and ask ML Kit to inspect/download the same models twice.
old_models = '''  Future<void> _prepareTranslationModels() async {
    try {
      for (final language in [TranslateLanguage.english, TranslateLanguage.arabic]) {
        final code = language.bcpCode;
        if (!await _modelManager.isModelDownloaded(code)) {
          await _modelManager.downloadModel(code, isWifiRequired: false);
        }
      }
    } catch (_) {}
  }
'''
new_models = '''  Future<void> _prepareTranslationModels() async {
    if (_translationModelsReady) return;
    final inFlight = _translationModelsFuture;
    if (inFlight != null) {
      await inFlight;
      return;
    }
    final future = _downloadTranslationModels();
    _translationModelsFuture = future;
    try {
      await future;
      _translationModelsReady = true;
    } finally {
      _translationModelsFuture = null;
    }
  }

  Future<void> _downloadTranslationModels() async {
    for (final language in [TranslateLanguage.english, TranslateLanguage.arabic]) {
      final code = language.bcpCode;
      if (!await _modelManager.isModelDownloaded(code)) {
        await _modelManager.downloadModel(code, isWifiRequired: false);
      }
    }
  }
'''
if old_models not in s:
    raise SystemExit('translation model preparation marker not found')
s = s.replace(old_models, new_models, 1)

# Small LRU caches preserve instant back/forward navigation while ensuring long
# books cannot grow geometry/text caches without bound.
marker = '  Future<String> _extractCurrentPage() async {\n'
helpers = '''  void _cacheStructuredPage(PdfPageText pageText) {
    final page = pageText.pageNumber;
    _structuredText[page] = pageText;
    _structuredTextLru.remove(page);
    _structuredTextLru.add(page);
    while (_structuredTextLru.length > 8) {
      final oldest = _structuredTextLru.removeAt(0);
      if (oldest != _page && oldest != _highlighterPageText?.pageNumber) {
        _structuredText.remove(oldest);
      }
    }
  }

  void _cachePageText(int page, String text) {
    _pageText[page] = text;
    _pageTextLru.remove(page);
    _pageTextLru.add(page);
    while (_pageTextLru.length > 24) {
      final oldest = _pageTextLru.removeAt(0);
      if (oldest != _page) _pageText.remove(oldest);
    }
  }

'''
if marker not in s:
    raise SystemExit('extractCurrentPage marker not found')
s = s.replace(marker, helpers + marker, 1)

s = s.replace(
    '''      _structuredText[_page] = pageText;
      _pageText[_page] = text;
''',
    '''      _cacheStructuredPage(pageText);
      _cachePageText(_page, text);
''',
    1,
)

# Reuse the SharedPreferences instance instead of reopening it on every page
# transition (continuous reading can move through many pages quickly).
old_save = '''  Future<void> _savePage(int page) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('lastBook', widget.filePath);
    await prefs.setInt('lastPage', page);
  }
'''
new_save = '''  Future<void> _savePage(int page) async {
    final prefs = _prefs ??= await SharedPreferences.getInstance();
    await prefs.setString('lastBook', widget.filePath);
    await prefs.setInt('lastPage', page);
  }
'''
if old_save not in s:
    raise SystemExit('savePage marker not found')
s = s.replace(old_save, new_save, 1)

# Track the last selected character so a moving finger searches a small nearby
# window first. This turns most highlighter updates from a full-page scan into a
# tiny local scan and makes marker mode substantially smoother on older phones.
s = s.replace(
    '  bool _highlighterResolving = false;\n',
    '  bool _highlighterResolving = false;\n  int _highlighterLastIndex = -1;\n',
    1,
)

old_point = r'''  Future<(PdfPageText, int)?> _highlighterPointAt(Offset globalPosition) async {
    if (!_pdfController.isReady || _highlighterResolving) return null;
    _highlighterResolving = true;
    try {
      final local = _pdfController.globalToLocal(globalPosition);
      if (local == null) return null;
      final hit = _pdfController.getPdfPageHitTestResult(local, useDocumentLayoutCoordinates: false);
      if (hit == null) return null;
      final pageText = await hit.page.loadStructuredText();
      if (pageText.fullText.isEmpty || pageText.charRects.isEmpty) return null;

      var best = -1;
      var bestDistance = double.infinity;
      // A wide PDF-coordinate margin makes a finger stroke forgiving even when
      // the text is small or the PDF is zoomed out.
      for (var i = 0; i < pageText.charRects.length; i++) {
        final rect = pageText.charRects[i];
        if (rect.containsPoint(hit.offset, margin: 7)) {
          best = i;
          break;
        }
        final distance = rect.distanceSquaredTo(hit.offset);
        if (distance < bestDistance) {
          bestDistance = distance;
          best = i;
        }
      }
      if (best < 0) return null;
      return (pageText, best.clamp(0, pageText.fullText.length));
    } catch (_) {
      return null;
    } finally {
      _highlighterResolving = false;
    }
  }
'''
new_point = r'''  Future<(PdfPageText, int)?> _highlighterPointAt(Offset globalPosition) async {
    if (!_pdfController.isReady || _highlighterResolving) return null;
    _highlighterResolving = true;
    try {
      final local = _pdfController.globalToLocal(globalPosition);
      if (local == null) return null;
      final hit = _pdfController.getPdfPageHitTestResult(local, useDocumentLayoutCoordinates: false);
      if (hit == null) return null;

      var pageText = _structuredText[hit.page.pageNumber];
      if (pageText == null) {
        pageText = await hit.page.loadStructuredText();
        _cacheStructuredPage(pageText);
      } else {
        _structuredTextLru.remove(pageText.pageNumber);
        _structuredTextLru.add(pageText.pageNumber);
      }
      if (pageText.fullText.isEmpty || pageText.charRects.isEmpty) return null;

      var best = -1;
      var bestDistance = double.infinity;

      void inspect(int from, int to) {
        final start = from.clamp(0, pageText!.charRects.length);
        final end = to.clamp(start, pageText.charRects.length);
        for (var i = start; i < end; i++) {
          final rect = pageText.charRects[i];
          if (rect.containsPoint(hit.offset, margin: 8)) {
            best = i;
            bestDistance = 0;
            return;
          }
          final distance = rect.distanceSquaredTo(hit.offset);
          if (distance < bestDistance) {
            bestDistance = distance;
            best = i;
          }
        }
      }

      // Most pan events move only a few characters. Search locally first.
      if (_highlighterLastIndex >= 0 && _highlighterPageText?.pageNumber == pageText.pageNumber) {
        inspect(_highlighterLastIndex - 180, _highlighterLastIndex + 181);
      }
      // If the local result is not convincingly near the finger (for example a
      // quick jump to another line), fall back to a full scan once.
      if (best < 0 || bestDistance > 900) {
        best = -1;
        bestDistance = double.infinity;
        inspect(0, pageText.charRects.length);
      }
      if (best < 0) return null;
      _highlighterLastIndex = best;
      return (pageText, best.clamp(0, pageText.fullText.length));
    } catch (_) {
      return null;
    } finally {
      _highlighterResolving = false;
    }
  }
'''
if old_point not in s:
    raise SystemExit('highlighter point marker not found')
s = s.replace(old_point, new_point, 1)

s = s.replace(
    '''    _highlighterPageText = point.$1;
    _highlighterStart = point.$2;
    _highlighterEnd = point.$2;
''',
    '''    _highlighterPageText = point.$1;
    _highlighterStart = point.$2;
    _highlighterEnd = point.$2;
    _highlighterLastIndex = point.$2;
''',
    1,
)

# Reset local-search state whenever a stroke/session ends.
s = s.replace(
    '''      _highlighterEnd = null;
      return;
    }
''',
    '''      _highlighterEnd = null;
      _highlighterLastIndex = -1;
      return;
    }
''',
    1,
)
s = s.replace(
    '''      _highlighterEnd = null;
    }
  }

  Future<void> _toggleHighlighterMode() async {''',
    '''      _highlighterEnd = null;
      _highlighterLastIndex = -1;
    }
  }

  Future<void> _toggleHighlighterMode() async {''',
    1,
)
s = s.replace(
    '''      _highlighterEnd = null;
    });
''',
    '''      _highlighterEnd = null;
      _highlighterLastIndex = -1;
    });
''',
    1,
)

# Release references explicitly when leaving the reader. This is cheap and
# helps Android reclaim large PDF geometry promptly after closing a big book.
s = s.replace(
    '''  void dispose() {
    _tts.stop();
    _translator.close();
    super.dispose();
  }
''',
    '''  void dispose() {
    _continuousReading = false;
    _structuredText.clear();
    _structuredTextLru.clear();
    _pageText.clear();
    _pageTextLru.clear();
    _translations.clear();
    _translationBlocks.clear();
    _manualSelections.clear();
    _tts.stop();
    _translator.close();
    super.dispose();
  }
''',
    1,
)

p.write_text(s, encoding='utf-8')
print('Applied Android performance, cache, and highlighter hardening')

from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

s = s.replace('    _prepareTranslationModels();\n', '    _initTts();\n', 1)
s = s.replace('  bool _showTranscript = false;\n', '  bool _showTranscript = false;\n  bool _ttsReady = false;\n  final Map<int, PdfPageText> _structuredText = {};\n', 1)

needle = '  Future<void> _prepareTranslationModels() async {\n'
insert = '''  Future<void> _initTts() async {
    try {
      final engine = await _tts.getDefaultEngine;
      if (engine is String && engine.isNotEmpty) await _tts.setEngine(engine);
      var languageResult = await _tts.setLanguage('en-US');
      if (languageResult != 1) languageResult = await _tts.setLanguage('en-GB');
      if (languageResult != 1) languageResult = await _tts.setLanguage('en');
      await _tts.setSpeechRate(_speechRate);
      await _tts.setVolume(1.0);
      await _tts.setPitch(1.0);
      await _tts.setQueueMode(0);
      _ttsReady = languageResult == 1;
    } catch (_) {
      _ttsReady = false;
    }
  }

'''
if needle not in s:
    raise SystemExit('prepareTranslationModels marker not found')
s = s.replace(needle, insert + needle, 1)

old_extract = '''  Future<String> _extractCurrentPage() async {
    if (_pageText.containsKey(_page)) return _pageText[_page]!;
    if (!_pdfController.isReady || _page < 1 || _page > _pdfController.pages.length) return '';
    final pageText = await _pdfController.pages[_page - 1].loadText();
    final text = _cleanText(pageText?.fullText ?? '');
    _pageText[_page] = text;
    return text;
  }
'''
new_extract = '''  Future<String> _extractCurrentPage() async {
    if (_pageText.containsKey(_page)) return _pageText[_page]!;
    if (!_pdfController.isReady || _page < 1 || _page > _pdfController.pages.length) return '';
    try {
      final pageText = await _pdfController.pages[_page - 1].loadStructuredText();
      final text = pageText.fullText;
      _structuredText[_page] = pageText;
      _pageText[_page] = text;
      return text;
    } catch (_) {
      return '';
    }
  }
'''
if old_extract not in s:
    raise SystemExit('extractCurrentPage marker not found')
s = s.replace(old_extract, new_extract, 1)

needle2 = "        return;\n      }\n      final translated = await _translator.translateText(text);"
repl2 = "        return;\n      }\n      await _prepareTranslationModels();\n      final translated = await _translator.translateText(_cleanText(text));"
if needle2 not in s:
    raise SystemExit('translation call marker not found')
s = s.replace(needle2, repl2, 1)

needle = "  Future<void> _toggleSpeech() async {\n    if (_speaking) {"
repl = "  Future<void> _toggleSpeech() async {\n    if (!_ttsReady) await _initTts();\n    if (!_ttsReady) {\n      _showMessage('لا يتوفر صوت إنجليزي جاهز على هذا الهاتف. تحقق من إعدادات تحويل النص إلى كلام (TTS).');\n      return;\n    }\n    if (_speaking) {"
if needle not in s:
    raise SystemExit('toggleSpeech marker not found')
s = s.replace(needle, repl, 1)

marker = '  int _restartOffset() {\n'
highlight = '''  Future<void> _highlightCurrentWord(int start, int end) async {
    final pageText = _structuredText[_page];
    if (pageText == null || pageText.fullText.isEmpty || !_pdfController.isReady) return;
    final maxIndex = pageText.fullText.length - 1;
    final a = start.clamp(0, maxIndex);
    final b = (end > start ? end - 1 : start).clamp(a, maxIndex);
    try {
      final range = PdfTextSelectionRange.fromPoints(
        PdfTextSelectionPoint(pageText, a),
        PdfTextSelectionPoint(pageText, b),
      );
      await _pdfController.textSelectionDelegate.setTextSelectionPointRange(range);
    } catch (_) {}
  }

  Future<void> _clearWordHighlight() async {
    if (!_pdfController.isReady) return;
    try {
      await _pdfController.textSelectionDelegate.clearTextSelection();
    } catch (_) {}
  }

'''
if marker not in s:
    raise SystemExit('restartOffset marker not found')
s = s.replace(marker, highlight + marker, 1)

old_progress = '''      setState(() {
        _spokenWord = word;
        _spokenStart = absoluteStart;
        _spokenEnd = absoluteEnd;
      });
'''
new_progress = '''      setState(() {
        _spokenWord = word;
        _spokenStart = absoluteStart;
        _spokenEnd = absoluteEnd;
      });
      _highlightCurrentWord(absoluteStart, absoluteEnd);
'''
if old_progress not in s:
    raise SystemExit('TTS progress marker not found')
s = s.replace(old_progress, new_progress, 1)

needle = "    await _tts.setSpeechRate(_speechRate);\n    await _tts.speak(text);"
repl = "    await _tts.setSpeechRate(_speechRate);\n    final result = await _tts.speak(text, focus: true);\n    if (result != 1 && mounted) {\n      setState(() => _speaking = false);\n      await _clearWordHighlight();\n      _showMessage('تعذر تشغيل الصوت. تأكد من وجود محرك تحويل النص إلى كلام (TTS) وتفعيل صوت إنجليزي في إعدادات الهاتف.');\n    }"
if needle not in s:
    raise SystemExit('speak marker not found')
s = s.replace(needle, repl, 1)
s = s.replace('    await _tts.speak(remaining);\n', '    await _tts.speak(remaining, focus: true);\n', 1)

s = s.replace(
    "      await _tts.stop();\n      if (mounted) setState(() => _speaking = false);\n      return;",
    "      await _tts.stop();\n      await _clearWordHighlight();\n      if (mounted) setState(() => _speaking = false);\n      return;",
    1,
)
s = s.replace(
    '    await _tts.stop();\n    setState(() {\n      _speaking = false;',
    '    await _tts.stop();\n    await _clearWordHighlight();\n    if (!mounted) return;\n    setState(() {\n      _speaking = false;',
    1,
)

s = s.replace('  Widget _readingCard() {\n', '  // ignore: unused_element\n  Widget _readingCard() {\n', 1)
s = s.replace('      body: Column(children: [Expanded(child: _body()), _readingCard()]),\n', '      body: _body(),\n', 1)

start = s.find('      bottomNavigationBar: SafeArea(\n')
end_marker = '      ),\n    );\n  }\n}\n'
if start == -1:
    raise SystemExit('bottomNavigationBar start not found')
end = s.find(end_marker, start)
if end == -1:
    raise SystemExit('bottomNavigationBar end not found')
end += len('      ),\n')
compact = '''      bottomNavigationBar: SafeArea(
        top: false,
        child: Container(
          decoration: BoxDecoration(color: Colors.white, border: Border(top: BorderSide(color: scheme.outlineVariant))),
          padding: const EdgeInsets.fromLTRB(6, 5, 6, 6),
          child: Directionality(
            textDirection: TextDirection.rtl,
            child: Row(
              children: [
                Expanded(child: OutlinedButton.icon(onPressed: _page > 1 ? () => _go(_page - 1) : null, icon: const Icon(Icons.chevron_right_rounded, size: 18), label: const Text('السابق'), style: OutlinedButton.styleFrom(minimumSize: const Size(0, 40), padding: const EdgeInsets.symmetric(horizontal: 4)))),
                const SizedBox(width: 4),
                Expanded(child: FilledButton.tonalIcon(onPressed: _toggleSpeech, icon: Icon(_speaking ? Icons.stop_rounded : Icons.play_arrow_rounded, size: 19), label: Text(_speaking ? 'إيقاف' : 'قراءة'), style: FilledButton.styleFrom(minimumSize: const Size(0, 40), padding: const EdgeInsets.symmetric(horizontal: 4)))),
                const SizedBox(width: 4),
                SizedBox(width: 62, child: OutlinedButton(onPressed: () { const rates = <double>[.25, .35, .4, .45, .5, .6, .75, 1.0]; var index = rates.indexWhere((value) => (value - _speechRate).abs() < .001); index = index < 0 ? 3 : (index + 1) % rates.length; _setRate(rates[index]); }, style: OutlinedButton.styleFrom(minimumSize: const Size(0, 40), padding: EdgeInsets.zero), child: Text('${visibleRate.toStringAsFixed(1)}x', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)))),
                const SizedBox(width: 4),
                SizedBox(width: 48, child: FilledButton.tonal(onPressed: _busy ? null : _translatePage, style: FilledButton.styleFrom(minimumSize: const Size(0, 40), padding: EdgeInsets.zero), child: _busy ? const SizedBox(width: 15, height: 15, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.translate_rounded, size: 18))),
                const SizedBox(width: 4),
                Expanded(child: FilledButton.icon(onPressed: _page < _pageCount ? () => _go(_page + 1) : null, icon: const Icon(Icons.chevron_left_rounded, size: 18), label: const Text('التالي'), style: FilledButton.styleFrom(minimumSize: const Size(0, 40), padding: const EdgeInsets.symmetric(horizontal: 4)))),
              ],
            ),
          ),
        ),
      ),
'''
s = s[:start] + compact + s[end:]

p.write_text(s, encoding='utf-8')
print('Applied hardened Android 8 reader runtime patch')

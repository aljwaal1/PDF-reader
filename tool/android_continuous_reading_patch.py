from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Continuous-reading state. The guard prevents duplicate completion callbacks
# from advancing more than one page.
s = s.replace(
    '  bool _ttsReady = false;\n',
    '  bool _ttsReady = false;\n  bool _continuousReading = false;\n  bool _advancingContinuous = false;\n',
    1,
)

# Keep character offsets intact while preventing header/footer page numbers from
# being spoken. Masking with spaces preserves pdfrx highlight coordinates.
marker = '  int _restartOffset() {\n'
helpers = r'''  String _speechTextForPage(String text) {
    if (text.isEmpty) return text;
    final chars = text.split('');
    final pageValue = '$_page';
    final expression = RegExp('(?:Page\\s*)?${RegExp.escape(pageValue)}', caseSensitive: false);

    void maskRange(int from, int to) {
      if (from >= to) return;
      final section = text.substring(from, to);
      for (final match in expression.allMatches(section)) {
        final start = from + match.start;
        final end = from + match.end;
        final before = start > 0 ? text[start - 1] : '';
        final after = end < text.length ? text[end] : '';
        final beforeIsDigit = before.isNotEmpty && RegExp(r'\d').hasMatch(before);
        final afterIsDigit = after.isNotEmpty && RegExp(r'\d').hasMatch(after);
        if (beforeIsDigit || afterIsDigit) continue;
        for (var i = start; i < end; i++) {
          chars[i] = ' ';
        }
      }
    }

    // Page numbers normally live in the header/footer. Do not touch numbers in
    // the body (years, examples, quantities, equations, etc.).
    final edge = text.length < 120 ? text.length : 120;
    maskRange(0, edge);
    if (text.length > edge) maskRange(text.length - edge, text.length);
    return chars.join();
  }

  Future<void> _advanceContinuousReading() async {
    if (!_continuousReading || _advancingContinuous || !mounted) return;
    _advancingContinuous = true;
    try {
      var nextPage = _page + 1;
      while (_continuousReading && mounted && nextPage <= _pageCount) {
        await _clearWordHighlight();
        await _pdfController.goToPage(pageNumber: nextPage, anchor: PdfPageAnchor.top);
        if (!mounted || !_continuousReading) return;
        setState(() {
          _page = nextPage;
          _speaking = false;
          _spokenWord = '';
          _spokenStart = 0;
          _spokenEnd = 0;
          _speechOffset = 0;
        });
        await _savePage(nextPage);
        await Future<void>.delayed(const Duration(milliseconds: 140));
        if (!mounted || !_continuousReading) return;

        final raw = await _extractCurrentPage();
        final speechText = _speechTextForPage(raw);
        if (speechText.trim().isEmpty) {
          nextPage++;
          continue;
        }
        _advancingContinuous = false;
        await _toggleSpeech(continuous: true);
        return;
      }

      if (mounted) {
        setState(() {
          _continuousReading = false;
          _speaking = false;
          _spokenWord = '';
        });
      }
      await _clearWordHighlight();
    } finally {
      _advancingContinuous = false;
    }
  }

'''
if marker not in s:
    raise SystemExit('restartOffset marker not found for continuous reading patch')
s = s.replace(marker, helpers + marker, 1)

# Regular tap = one page. Long press will pass continuous:true.
s = s.replace(
    '  Future<void> _toggleSpeech() async {\n',
    '  Future<void> _toggleSpeech({bool continuous = false}) async {\n',
    1,
)

old_stop = '''    if (_speaking) {
      await _tts.stop();
      await _clearWordHighlight();
      if (mounted) setState(() => _speaking = false);
      return;
    }
    final text = await _extractCurrentPage();
    if (text.isEmpty) {
      _showMessage('لا يوجد نص إنجليزي قابل للقراءة في هذه الصفحة.');
      return;
    }
    setState(() {
      _spokenText = text;
'''
new_stop = '''    if (_speaking) {
      _continuousReading = false;
      _advancingContinuous = false;
      await _tts.stop();
      await _clearWordHighlight();
      if (mounted) setState(() => _speaking = false);
      return;
    }
    _continuousReading = continuous;
    final rawText = await _extractCurrentPage();
    final text = _speechTextForPage(rawText);
    if (text.trim().isEmpty) {
      if (_continuousReading) {
        await _advanceContinuousReading();
      } else {
        _showMessage('لا يوجد نص إنجليزي قابل للقراءة في هذه الصفحة.');
      }
      return;
    }
    setState(() {
      _spokenText = text;
'''
if old_stop not in s:
    raise SystemExit('toggleSpeech body marker not found')
s = s.replace(old_stop, new_stop, 1)

# Manual page changes always terminate continuous playback.
s = s.replace(
    '  Future<void> _go(int nextPage) async {\n    if (!_pdfController.isReady || nextPage < 1 || nextPage > _pageCount) return;\n',
    '  Future<void> _go(int nextPage) async {\n    if (!_pdfController.isReady || nextPage < 1 || nextPage > _pageCount) return;\n    _continuousReading = false;\n    _advancingContinuous = false;\n',
    1,
)

# Replace the production completion handler: never replay the same page; in
# continuous mode advance exactly once to the next readable page.
old_completion = '''    _tts.setCompletionHandler(() {
      _clearWordHighlight();
      if (mounted) {
        setState(() {
          _speaking = false;
          _spokenWord = '';
        });
      }
    });
'''
new_completion = '''    _tts.setCompletionHandler(() async {
      await _clearWordHighlight();
      if (!mounted) return;
      setState(() {
        _speaking = false;
        _spokenWord = '';
      });
      if (_continuousReading) {
        await _advanceContinuousReading();
      }
    });
'''
if old_completion not in s:
    raise SystemExit('production TTS completion marker not found')
s = s.replace(old_completion, new_completion, 1)

# Errors/cancels must terminate the continuous session so it cannot restart by
# itself after the engine reports a late callback.
s = s.replace(
    '''    _tts.setErrorHandler((message) {
      _clearWordHighlight();
      if (!mounted) return;
''',
    '''    _tts.setErrorHandler((message) {
      _continuousReading = false;
      _advancingContinuous = false;
      _clearWordHighlight();
      if (!mounted) return;
''',
    1,
)
s = s.replace(
    '''    _tts.setCancelHandler(() {
      _clearWordHighlight();
''',
    '''    _tts.setCancelHandler(() {
      _clearWordHighlight();
''',
    1,
)

# Long press on the existing Read control enables continuous reading. No extra
# dock button is added, preserving the compact UI.
old_button = '''                      Expanded(
                        child: FilledButton(
                          onPressed: _toggleSpeech,
                          style: FilledButton.styleFrom(minimumSize: Size(0, buttonHeight), padding: const EdgeInsets.symmetric(horizontal: 4)),
                          child: Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [Icon(_speaking ? Icons.stop_rounded : Icons.play_arrow_rounded, size: 20), if (!compact) ...[const SizedBox(width: 4), Text(_speaking ? 'إيقاف' : 'قراءة')]]),
                        ),
                      ),
'''
new_button = '''                      Expanded(
                        child: GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onLongPress: _speaking ? null : () => _toggleSpeech(continuous: true),
                          child: FilledButton(
                            onPressed: _toggleSpeech,
                            style: FilledButton.styleFrom(minimumSize: Size(0, buttonHeight), padding: const EdgeInsets.symmetric(horizontal: 4)),
                            child: Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [Icon(_continuousReading && _speaking ? Icons.all_inclusive_rounded : (_speaking ? Icons.stop_rounded : Icons.play_arrow_rounded), size: 20), if (!compact) ...[const SizedBox(width: 4), Text(_speaking ? (_continuousReading ? 'مستمر' : 'إيقاف') : 'قراءة')]]),
                          ),
                        ),
                      ),
'''
if old_button not in s:
    raise SystemExit('reader button marker not found')
s = s.replace(old_button, new_button, 1)

p.write_text(s, encoding='utf-8')
print('Applied Android continuous reading + page-number speech suppression patch')

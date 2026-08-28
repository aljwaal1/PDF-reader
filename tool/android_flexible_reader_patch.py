from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Flexible selection/translation state. Keep page translation cache for backward
# compatibility, while also storing aligned source/Arabic blocks.
s = s.replace(
    '  final Map<int, String> _translations = {};\n',
    "  final Map<int, String> _translations = {};\n"
    "  final Map<int, List<(String, String)>> _translationBlocks = {};\n"
    "  final List<String> _manualSelections = <String>[];\n"
    "  List<(String, String)> _selectedTranslationBlocks = <(String, String)>[];\n"
    "  String _currentManualSelection = '';\n"
    "  bool _selectionBusy = false;\n"
    "  bool _speakingManualSelection = false;\n",
    1,
)

# Do not let programmatic word highlighting overwrite the user's manual
# selection state. Manual selection is captured only when normal TTS is idle.
old_progress = '''    _tts.setProgressHandler((text, start, end, word) {
      if (!mounted) return;
      final absoluteStart = (_speechOffset + start).clamp(0, _spokenText.length);
      final absoluteEnd = (_speechOffset + end).clamp(0, _spokenText.length);
      setState(() {
        _spokenWord = word;
        _spokenStart = absoluteStart;
        _spokenEnd = absoluteEnd;
      });
      _highlightCurrentWord(absoluteStart, absoluteEnd);
    });
'''
new_progress = '''    _tts.setProgressHandler((text, start, end, word) {
      if (!mounted) return;
      final absoluteStart = (_speechOffset + start).clamp(0, _spokenText.length);
      final absoluteEnd = (_speechOffset + end).clamp(0, _spokenText.length);
      setState(() {
        _spokenWord = word;
        _spokenStart = absoluteStart;
        _spokenEnd = absoluteEnd;
      });
      if (!_speakingManualSelection) {
        _highlightCurrentWord(absoluteStart, absoluteEnd);
      }
    });
'''
if old_progress not in s:
    raise SystemExit('progress handler marker not found')
s = s.replace(old_progress, new_progress, 1)

# Helper functions for paragraph-aligned translation and ordered manual
# selections. Paragraphs are kept short enough for ML Kit while preserving
# natural sentence boundaries where possible.
marker = '  Future<void> _translatePage() async {\n'
helpers = r'''  List<String> _splitParagraphs(String raw) {
    final normalized = raw.replaceAll('\r\n', '\n').replaceAll('\r', '\n').trim();
    if (normalized.isEmpty) return const <String>[];
    final initial = normalized
        .split(RegExp(r'\n\s*\n+'))
        .map((part) => part.replaceAll(RegExp(r'[ \t]+'), ' ').replaceAll(RegExp(r'\n+'), ' ').trim())
        .where((part) => part.isNotEmpty)
        .toList();
    final source = initial.length > 1
        ? initial
        : normalized
            .split(RegExp(r'\n+'))
            .map((line) => line.replaceAll(RegExp(r'\s+'), ' ').trim())
            .where((line) => line.isNotEmpty)
            .toList();
    final out = <String>[];
    var buffer = '';
    void flush() {
      final value = buffer.trim();
      if (value.isNotEmpty) out.add(value);
      buffer = '';
    }
    for (final part in source) {
      if (part.length > 520) {
        flush();
        var rest = part;
        while (rest.length > 520) {
          var cut = rest.lastIndexOf('. ', 520);
          if (cut < 180) cut = rest.lastIndexOf('? ', 520);
          if (cut < 180) cut = rest.lastIndexOf('! ', 520);
          if (cut < 180) cut = rest.lastIndexOf(' ', 520);
          if (cut < 120) cut = 520;
          out.add(rest.substring(0, cut + (cut < rest.length && rest[cut] != ' ' ? 1 : 0)).trim());
          rest = rest.substring(cut + 1).trim();
        }
        if (rest.isNotEmpty) out.add(rest);
        continue;
      }
      final candidate = buffer.isEmpty ? part : '$buffer $part';
      if (candidate.length > 430 && buffer.isNotEmpty) {
        flush();
        buffer = part;
      } else {
        buffer = candidate;
      }
    }
    flush();
    return out;
  }

  Future<List<(String, String)>> _translateBlocks(List<String> source) async {
    await _prepareTranslationModels();
    final result = <(String, String)>[];
    for (final block in source) {
      final clean = _cleanText(block);
      if (clean.isEmpty) continue;
      final translated = await _translator.translateText(clean);
      result.add((clean, translated));
    }
    return result;
  }

  void _captureManualSelection(PdfTextSelection selection) {
    if (!mounted || (_speaking && !_speakingManualSelection)) return;
    String text;
    try {
      text = selection.getSelectedText().trim();
    } catch (_) {
      text = '';
    }
    if (text == _currentManualSelection) return;
    setState(() => _currentManualSelection = text);
  }

  Future<void> _addCurrentSelection() async {
    final text = _cleanText(_currentManualSelection);
    if (text.isEmpty) return;
    setState(() {
      _manualSelections.add(text);
      _currentManualSelection = '';
      _selectedTranslationBlocks = <(String, String)>[];
    });
    await _clearWordHighlight();
  }

  Future<void> _clearManualSelections() async {
    if (_speakingManualSelection) await _tts.stop();
    _speakingManualSelection = false;
    if (!mounted) return;
    setState(() {
      _manualSelections.clear();
      _currentManualSelection = '';
      _selectedTranslationBlocks = <(String, String)>[];
      _selectionBusy = false;
      _speaking = false;
      _spokenWord = '';
    });
    await _clearWordHighlight();
  }

  List<String> get _orderedSelectionText {
    final out = <String>[..._manualSelections];
    final current = _cleanText(_currentManualSelection);
    if (current.isNotEmpty) out.add(current);
    return out;
  }

  Future<void> _speakManualSelections() async {
    final parts = _orderedSelectionText;
    if (parts.isEmpty) {
      _showMessage('ظلّل نصًا أولًا، ويمكنك إضافة أكثر من تحديد بالترتيب.');
      return;
    }
    if (!_ttsReady) await _initTts();
    if (!_ttsReady) {
      _showMessage('لا يتوفر صوت إنجليزي جاهز على هذا الهاتف. تحقق من إعدادات تحويل النص إلى كلام (TTS).');
      return;
    }
    _continuousReading = false;
    _advancingContinuous = false;
    await _tts.stop();
    final text = parts.join('\n\n');
    if (!mounted) return;
    setState(() {
      _speakingManualSelection = true;
      _spokenText = text;
      _spokenStart = 0;
      _spokenEnd = 0;
      _spokenWord = '';
      _speechOffset = 0;
      _speaking = true;
    });
    await _tts.setSpeechRate(_speechRate);
    final result = await _tts.speak(text, focus: true);
    if (result != 1 && mounted) {
      setState(() {
        _speaking = false;
        _speakingManualSelection = false;
      });
      _showMessage('تعذر تشغيل قراءة النص المحدد.');
    }
  }

  Future<void> _translateManualSelections() async {
    final parts = _orderedSelectionText;
    if (parts.isEmpty || _selectionBusy) {
      if (parts.isEmpty) _showMessage('ظلّل النص الذي تريد ترجمته أولًا.');
      return;
    }
    setState(() => _selectionBusy = true);
    try {
      final blocks = await _translateBlocks(parts);
      if (!mounted) return;
      setState(() {
        _selectedTranslationBlocks = blocks;
        _layout = TranslationLayout.bottomSheet;
      });
    } catch (_) {
      _showMessage('تعذرت ترجمة النص المحدد. حاول مرة أخرى.');
    } finally {
      if (mounted) setState(() => _selectionBusy = false);
    }
  }

'''
if marker not in s:
    raise SystemExit('translatePage marker not found')
s = s.replace(marker, helpers + marker, 1)

# Translate the current page paragraph-by-paragraph, retaining both the English
# source and its exact Arabic counterpart.
old_translate = '''      await _prepareTranslationModels();
      final translated = await _translator.translateText(_cleanText(text));
      if (mounted) {
        setState(() {
          _translations[_page] = translated;
          if (_layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;
        });
      }
'''
new_translate = '''      final paragraphs = _splitParagraphs(text);
      final blocks = await _translateBlocks(paragraphs);
      if (mounted) {
        setState(() {
          _translationBlocks[_page] = blocks;
          _translations[_page] = blocks.map((block) => block.$2).join('\\n\\n');
          _selectedTranslationBlocks = <(String, String)>[];
          if (_layout == TranslationLayout.pdfOnly) _layout = TranslationLayout.bottomSheet;
        });
      }
'''
if old_translate not in s:
    raise SystemExit('page translation implementation marker not found')
s = s.replace(old_translate, new_translate, 1)

# Normal page reading always exits manual-selection speech mode.
s = s.replace(
    '    _continuousReading = continuous;\n',
    '    _continuousReading = continuous;\n    _speakingManualSelection = false;\n',
    1,
)

# Completion/error/cancel must also reset manual speech mode.
s = s.replace(
    '''      setState(() {
        _speaking = false;
        _spokenWord = '';
      });
      if (_continuousReading) {''',
    '''      setState(() {
        _speaking = false;
        _speakingManualSelection = false;
        _spokenWord = '';
      });
      if (_continuousReading) {''',
    1,
)
s = s.replace(
    '''      setState(() {
        _speaking = false;
        _spokenWord = '';
      });
      _showMessage('تعذر تشغيل القراءة الصوتية.''',
    '''      setState(() {
        _speaking = false;
        _speakingManualSelection = false;
        _spokenWord = '';
      });
      _showMessage('تعذر تشغيل القراءة الصوتية.''',
    1,
)

# Suppress pdfrx's default AdaptiveTextSelectionToolbar. It intermittently
# crashes on some Android contexts because MaterialLocalizations is unavailable
# to that overlay. We use our own selection controls instead.
old_params = '''        params: PdfViewerParams(
          margin: 2,
          onViewerReady: (document, controller) {'''
new_params = '''        params: PdfViewerParams(
          margin: 2,
          buildContextMenu: (context, params) => null,
          textSelectionParams: PdfTextSelectionParams(
            showContextMenuAutomatically: false,
            onTextSelectionChange: _captureManualSelection,
          ),
          onViewerReady: (document, controller) {'''
if old_params not in s:
    raise SystemExit('PdfViewerParams marker not found')
s = s.replace(old_params, new_params, 1)

# Present source and translation together, paragraph-by-paragraph.
old_pane = '''  Widget _translationPane() {
    final text = _translations[_page];
    return Container(
      color: Theme.of(context).colorScheme.surface,
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 20),
      child: Directionality(
        textDirection: TextDirection.rtl,
        child: text == null
            ? Center(child: _busy ? const CircularProgressIndicator() : FilledButton.icon(onPressed: _translatePage, icon: const Icon(Icons.translate), label: const Text('ترجمة الصفحة الحالية')))
            : SingleChildScrollView(child: SelectableText(text, style: const TextStyle(fontSize: 16.5, height: 1.72, letterSpacing: .05))),
      ),
    );
  }
'''
new_pane = '''  Widget _translationPane() {
    final selected = _selectedTranslationBlocks;
    final pageBlocks = _translationBlocks[_page] ?? const <(String, String)>[];
    final blocks = selected.isNotEmpty ? selected : pageBlocks;
    final title = selected.isNotEmpty ? 'ترجمة التحديدات حسب ترتيبها' : 'ترجمة الصفحة $_page • فقرة بفقرة';
    return Container(
      color: Theme.of(context).colorScheme.surface,
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 18),
      child: Directionality(
        textDirection: TextDirection.rtl,
        child: blocks.isEmpty
            ? Center(child: _busy ? const CircularProgressIndicator() : FilledButton.icon(onPressed: _translatePage, icon: const Icon(Icons.translate), label: const Text('ترجمة الصفحة الحالية')))
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(4, 2, 4, 10),
                    child: Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Colors.black54)),
                  ),
                  Expanded(
                    child: ListView.separated(
                      itemCount: blocks.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 9),
                      itemBuilder: (context, index) {
                        final block = blocks[index];
                        return Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13), border: Border.all(color: Theme.of(context).colorScheme.outlineVariant)),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Directionality(textDirection: TextDirection.ltr, child: SelectableText(block.$1, style: const TextStyle(fontSize: 14.5, height: 1.5, fontWeight: FontWeight.w600))),
                              const SizedBox(height: 8),
                              Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                              const SizedBox(height: 8),
                              SelectableText(block.$2, style: const TextStyle(fontSize: 16, height: 1.65)),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
      ),
    );
  }
'''
if old_pane not in s:
    raise SystemExit('translationPane marker not found')
s = s.replace(old_pane, new_pane, 1)

# Compact manual-selection action bar. The user can add multiple independent
# highlights one-by-one; their order is preserved for reading and translation.
marker2 = '  Widget _body() {\n'
selection_bar = '''  Widget _selectionBar() {
    final hasCurrent = _cleanText(_currentManualSelection).isNotEmpty;
    final count = _manualSelections.length + (hasCurrent ? 1 : 0);
    if (count == 0 && !_selectionBusy) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: scheme.surfaceContainerLow,
      child: SafeArea(
        top: false,
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
          child: Row(
            children: [
              Expanded(child: Text(count == 1 ? 'تحديد واحد جاهز' : '$count تحديدات بالترتيب', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800), overflow: TextOverflow.ellipsis)),
              if (hasCurrent) ...[
                TextButton.icon(onPressed: _addCurrentSelection, icon: const Icon(Icons.add_rounded, size: 17), label: const Text('إضافة'), style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 7))),
              ],
              IconButton(onPressed: _selectionBusy ? null : _speakManualSelections, tooltip: 'قراءة المحدد', icon: const Icon(Icons.volume_up_rounded, size: 20)),
              IconButton(onPressed: _selectionBusy ? null : _translateManualSelections, tooltip: 'ترجمة المحدد', icon: _selectionBusy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.translate_rounded, size: 20)),
              IconButton(onPressed: _clearManualSelections, tooltip: 'مسح التحديدات', icon: const Icon(Icons.close_rounded, size: 20)),
            ],
          ),
        ),
      ),
    );
  }

'''
if marker2 not in s:
    raise SystemExit('body marker not found')
s = s.replace(marker2, selection_bar + marker2, 1)

# Keep PDF dominant, but expose the manual-selection controls only when needed.
s = s.replace(
    '      body: _body(),\n',
    '      body: Column(children: [Expanded(child: _body()), _selectionBar()]),\n',
    1,
)

# On page changes, keep queued selections (so multi-page selection workflows are
# possible) but clear the transient current selection and any stale page result.
s = s.replace(
    '''            if (pageNumber == null || !mounted) return;
            setState(() => _page = pageNumber);''',
    '''            if (pageNumber == null || !mounted) return;
            setState(() {
              _page = pageNumber;
              _currentManualSelection = '';
              if (_selectedTranslationBlocks.isEmpty) {
                // Page translation is resolved from the page-indexed cache.
              }
            });''',
    1,
)

p.write_text(s, encoding='utf-8')
print('Applied Android flexible selection + paragraph translation patch')

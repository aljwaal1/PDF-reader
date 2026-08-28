from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Highlighter-mode state: one-finger drag selects text like a marker. Each
# completed stroke is immediately saved into the ordered manual selections.
s = s.replace(
    '  bool _speakingManualSelection = false;\n',
    '  bool _speakingManualSelection = false;\n'
    '  bool _highlighterMode = false;\n'
    '  PdfPageText? _highlighterPageText;\n'
    '  int? _highlighterStart;\n'
    '  int? _highlighterEnd;\n'
    '  bool _highlighterResolving = false;\n',
    1,
)

# Add robust pointer-to-character hit testing. pdfrx gives us the page hit in
# PDF coordinates; we choose the character under/nearest the finger with a
# generous margin so selection feels like a physical highlighter rather than a
# precision needle.
marker = '  Future<void> _addCurrentSelection() async {\n'
helpers = r'''  Future<(PdfPageText, int)?> _highlighterPointAt(Offset globalPosition) async {
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

  Future<void> _beginHighlighterStroke(Offset globalPosition) async {
    if (!_highlighterMode) return;
    final point = await _highlighterPointAt(globalPosition);
    if (point == null || !_highlighterMode) return;
    _highlighterPageText = point.$1;
    _highlighterStart = point.$2;
    _highlighterEnd = point.$2;
    final p = PdfTextSelectionPoint(point.$1, point.$2);
    await _pdfController.textSelectionDelegate.setTextSelectionPointRange(PdfTextSelectionRange.fromPoints(p, p));
  }

  Future<void> _updateHighlighterStroke(Offset globalPosition) async {
    if (!_highlighterMode || _highlighterPageText == null || _highlighterStart == null) return;
    final point = await _highlighterPointAt(globalPosition);
    if (point == null || !_highlighterMode) return;
    // A single marker stroke stays on one page. Start a new stroke for another
    // page; this avoids accidental cross-page jumps while dragging.
    if (point.$1.pageNumber != _highlighterPageText!.pageNumber) return;
    _highlighterEnd = point.$2;
    final start = _highlighterStart!;
    final end = _highlighterEnd!;
    final a = PdfTextSelectionPoint(_highlighterPageText!, start);
    final b = PdfTextSelectionPoint(_highlighterPageText!, end);
    await _pdfController.textSelectionDelegate.setTextSelectionPointRange(PdfTextSelectionRange.fromPoints(a, b));
  }

  Future<void> _finishHighlighterStroke() async {
    if (!_highlighterMode || _highlighterPageText == null || _highlighterStart == null || _highlighterEnd == null) {
      _highlighterPageText = null;
      _highlighterStart = null;
      _highlighterEnd = null;
      return;
    }
    try {
      final selected = _cleanText(await _pdfController.textSelectionDelegate.getSelectedText());
      if (selected.isNotEmpty && mounted) {
        setState(() {
          _manualSelections.add(selected);
          _currentManualSelection = '';
          _selectedTranslationBlocks = <(String, String)>[];
        });
        _showMessage('تم حفظ التحديد ${_manualSelections.length}. مرّر القلم مرة أخرى لإضافة مقطع جديد.');
      }
    } catch (_) {
      // Keep the viewer usable even for unusual PDFs that do not expose copyable text.
    } finally {
      _highlighterPageText = null;
      _highlighterStart = null;
      _highlighterEnd = null;
    }
  }

  Future<void> _toggleHighlighterMode() async {
    if (_speaking) await _tts.stop();
    if (!mounted) return;
    final next = !_highlighterMode;
    setState(() {
      _highlighterMode = next;
      _continuousReading = false;
      _advancingContinuous = false;
      _speaking = false;
      _spokenWord = '';
      _highlighterPageText = null;
      _highlighterStart = null;
      _highlighterEnd = null;
    });
    await _pdfController.textSelectionDelegate.clearTextSelection();
    if (next) {
      _showMessage('قلم التحديد مفعّل: مرّر إصبعك فوق النص مباشرة.');
    }
  }

'''
if marker not in s:
    raise SystemExit('manual selection marker not found')
s = s.replace(marker, helpers + marker, 1)

# Replace the handle-based configuration with marker-friendly selection. The
# custom gesture layer owns touch selection; no tiny handles or native menu.
start = s.find('          textSelectionParams: PdfTextSelectionParams(\n')
if start == -1:
    raise SystemExit('textSelectionParams start not found')
end = s.find('          ),\n          onViewerReady:', start)
if end == -1:
    raise SystemExit('textSelectionParams end not found')
end += len('          ),\n')
selection_params = '''          textSelectionParams: PdfTextSelectionParams(
            enableSelectionHandles: false,
            showContextMenuAutomatically: false,
            onTextSelectionChange: _captureManualSelection,
          ),
'''
s = s[:start] + selection_params + s[end:]

# Wrap the PDF viewer with a transparent highlighter gesture surface only while
# marker mode is active. In normal mode it is completely absent, so scrolling,
# zooming and page navigation keep their existing behavior.
old_view = '''      child: PdfViewer.file(
        widget.filePath,
        controller: _pdfController,
        initialPageNumber: widget.initialPage,
        params: PdfViewerParams(
'''
new_view = '''      child: Stack(
        children: [
          Positioned.fill(
            child: PdfViewer.file(
              widget.filePath,
              controller: _pdfController,
              initialPageNumber: widget.initialPage,
              params: PdfViewerParams(
'''
if old_view not in s:
    raise SystemExit('PdfViewer.file wrapper marker not found')
s = s.replace(old_view, new_view, 1)

# Close the new Positioned/PdfViewer wrappers and add the gesture layer.
old_close = '''        ),
      ),
    );
  }

  Widget _translationPane() {'''
new_close = '''              ),
            ),
          ),
          if (_highlighterMode)
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onPanStart: (details) => _beginHighlighterStroke(details.globalPosition),
                onPanUpdate: (details) => _updateHighlighterStroke(details.globalPosition),
                onPanEnd: (_) => _finishHighlighterStroke(),
                onPanCancel: _finishHighlighterStroke,
                child: const ColoredBox(color: Colors.transparent),
              ),
            ),
        ],
      ),
    );
  }

  Widget _translationPane() {'''
if old_close not in s:
    raise SystemExit('pdf view close marker not found')
s = s.replace(old_close, new_close, 1)

# Add an always-visible marker toggle to the reader app bar. It has a selected
# background when active so the user always knows whether a swipe will scroll
# the PDF or highlight text.
old_actions = '''        actions: [
          PopupMenuButton<TranslationLayout>(
'''
new_actions = '''        actions: [
          IconButton(
            tooltip: _highlighterMode ? 'إيقاف قلم التحديد' : 'قلم التحديد',
            onPressed: _toggleHighlighterMode,
            style: IconButton.styleFrom(
              backgroundColor: _highlighterMode ? scheme.primaryContainer : Colors.transparent,
              foregroundColor: _highlighterMode ? scheme.onPrimaryContainer : scheme.onSurfaceVariant,
            ),
            icon: Icon(_highlighterMode ? Icons.format_color_highlight_rounded : Icons.draw_outlined, size: 21),
          ),
          PopupMenuButton<TranslationLayout>(
'''
if old_actions not in s:
    raise SystemExit('app bar actions marker not found')
s = s.replace(old_actions, new_actions, 1)

# When manually navigating pages, leave marker mode enabled (like a real tool)
# but clear any incomplete stroke so the next drag starts cleanly.
s = s.replace(
    '    _continuousReading = false;\n    _advancingContinuous = false;\n',
    '    _continuousReading = false;\n    _advancingContinuous = false;\n    _highlighterPageText = null;\n    _highlighterStart = null;\n    _highlighterEnd = null;\n',
    1,
)

p.write_text(s, encoding='utf-8')
print('Applied Android marker-style drag highlighter mode')

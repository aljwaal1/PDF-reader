from pathlib import Path
import re

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Refine the existing visual language only: restrained Material 3 palette,
# consistent controls and surfaces. No product functionality is added here.
s = s.replace(
    "        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF5B5FEF)),\n        scaffoldBackgroundColor: const Color(0xFFF5F6FA),\n        cardTheme: const CardThemeData(margin: EdgeInsets.zero),",
    "        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4056A1), brightness: Brightness.light),\n        scaffoldBackgroundColor: const Color(0xFFF7F8FB),\n        appBarTheme: const AppBarTheme(backgroundColor: Colors.white, foregroundColor: Color(0xFF171A22), surfaceTintColor: Colors.transparent, elevation: 0, scrolledUnderElevation: .5, centerTitle: false),\n        cardTheme: const CardThemeData(margin: EdgeInsets.zero, elevation: 0, color: Colors.white, surfaceTintColor: Colors.transparent),\n        dividerTheme: const DividerThemeData(color: Color(0xFFE5E7EE), thickness: 1),\n        snackBarTheme: const SnackBarThemeData(behavior: SnackBarBehavior.floating, elevation: 2),\n        progressIndicatorTheme: const ProgressIndicatorThemeData(strokeWidth: 2.4),\n        filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(minimumSize: const Size(0, 44), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)))),\n        outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(minimumSize: const Size(0, 44), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)))),\n        iconButtonTheme: IconButtonThemeData(style: IconButton.styleFrom(minimumSize: const Size(44, 44), tapTargetSize: MaterialTapTargetSize.padded)),",
    1,
)

# First launch/loading should feel deliberate rather than abrupt.
s = s.replace(
    "          return const Scaffold(body: Center(child: CircularProgressIndicator()));",
    "          return const Scaffold(body: Center(child: SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 2.4))));",
    1,
)

# Calm the home screen and remove visual duplication while keeping the same actions.
s = s.replace(
    "                  Container(width: 46, height: 46, decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(15)), child: Icon(Icons.auto_stories_rounded, color: scheme.primary)),",
    "                  Container(width: 44, height: 44, decoration: BoxDecoration(color: scheme.primaryContainer.withValues(alpha: .72), borderRadius: BorderRadius.circular(13)), child: Icon(Icons.auto_stories_rounded, size: 23, color: scheme.primary)),",
    1,
)
s = s.replace(
    "                  const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('قارئ الكتب', style: TextStyle(fontSize: 23, fontWeight: FontWeight.w900)), SizedBox(height: 2), Text('اقرأ • استمع • ترجم', style: TextStyle(color: Colors.black54, fontWeight: FontWeight.w500))])),",
    "                  const Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('قارئ الكتب', style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800, letterSpacing: -.2)), SizedBox(height: 2), Text('اقرأ • استمع • ترجم', style: TextStyle(fontSize: 12.5, color: Colors.black54, fontWeight: FontWeight.w500))])),",
    1,
)
s = s.replace(
    "                    decoration: BoxDecoration(gradient: LinearGradient(colors: [scheme.primaryContainer, scheme.secondaryContainer]), borderRadius: BorderRadius.circular(24)),",
    "                    decoration: BoxDecoration(color: Colors.white, border: Border.all(color: scheme.outlineVariant), borderRadius: BorderRadius.circular(20)),",
    1,
)
s = s.replace("                  borderRadius: BorderRadius.circular(24),", "                  borderRadius: BorderRadius.circular(20),", 1)

# Replace the nested 'continue' action inside a tappable card with a quiet affordance.
s = s.replace(
    "const SizedBox(height: 12), FilledButton.icon(onPressed: _continueReading, icon: const Icon(Icons.play_arrow_rounded), label: const Text('متابعة'))",
    "const SizedBox(height: 12), Row(children: [Icon(Icons.play_arrow_rounded, size: 18, color: scheme.primary), const SizedBox(width: 5), Text('متابعة القراءة', style: TextStyle(fontWeight: FontWeight.w700, color: scheme.primary))])",
    1,
)

# Remove the old feature-chip section and its now-unused helper entirely.
s = s.replace(
    "              const SizedBox(height: 24),\n              Text('كل ما تحتاجه أثناء القراءة', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),\n              const SizedBox(height: 10),\n              Wrap(spacing: 7, runSpacing: 7, children: [_featureChip(Icons.volume_up_rounded, 'قراءة صوتية'), _featureChip(Icons.translate_rounded, 'ترجمة عربية'), _featureChip(Icons.speed_rounded, 'سرعة مرنة'), _featureChip(Icons.visibility_rounded, 'متابعة الكلمة')]),",
    "              const SizedBox(height: 16),",
    1,
)
s = re.sub(
    r"\n  Widget _featureChip\(IconData icon, String label\) \{.*?\n  \}\n\n  @override\n  Widget build\(BuildContext context\)",
    "\n  @override\n  Widget build(BuildContext context)",
    s,
    count=1,
    flags=re.S,
)
s = s.replace(
    "      floatingActionButton: _lastBook == null ? null : FloatingActionButton.extended(onPressed: _importing ? null : _pickPdf, icon: const Icon(Icons.add_rounded), label: const Text('كتاب جديد')),\n",
    "",
    1,
)

# Keep the PDF visually dominant with a neutral reading surface.
s = s.replace("      color: const Color(0xFFE9ECF2),", "      color: const Color(0xFFF0F1F4),", 1)
s = s.replace("          margin: 3,", "          margin: 2,", 1)

# Calm and tighten the translation surface without changing translation behavior.
s = s.replace(
    "      padding: const EdgeInsets.all(14),",
    "      padding: const EdgeInsets.fromLTRB(18, 16, 18, 20),",
    1,
)
s = s.replace(
    "SelectableText(text, style: const TextStyle(fontSize: 17, height: 1.8))",
    "SelectableText(text, style: const TextStyle(fontSize: 16.5, height: 1.72, letterSpacing: .05))",
    1,
)
s = s.replace("                  elevation: 8,", "                  elevation: 2,", 1)
s = s.replace("borderRadius: const BorderRadius.vertical(top: Radius.circular(18))", "borderRadius: const BorderRadius.vertical(top: Radius.circular(22))", 1)

# Runtime hardening for existing TTS/PDF behavior: clear stale highlight and handle engine errors.
old_completion = '''    _tts.setCompletionHandler(() {
      if (mounted) setState(() => _speaking = false);
    });
'''
new_completion = '''    _tts.setCompletionHandler(() {
      _clearWordHighlight();
      if (mounted) {
        setState(() {
          _speaking = false;
          _spokenWord = '';
        });
      }
    });
    _tts.setErrorHandler((message) {
      _clearWordHighlight();
      if (!mounted) return;
      setState(() {
        _speaking = false;
        _spokenWord = '';
      });
      _showMessage('تعذر تشغيل القراءة الصوتية. تحقق من إعدادات تحويل النص إلى كلام في الهاتف.');
    });
    _tts.setCancelHandler(() {
      _clearWordHighlight();
      if (mounted) {
        setState(() {
          _speaking = false;
          _spokenWord = '';
        });
      }
    });
'''
if old_completion not in s:
    raise SystemExit('TTS completion marker not found')
s = s.replace(old_completion, new_completion, 1)

# Prevent a late PDF callback from touching a disposed screen.
s = s.replace(
    "          onPageChanged: (pageNumber) {\n            if (pageNumber == null) return;\n            setState(() => _page = pageNumber);",
    "          onPageChanged: (pageNumber) {\n            if (pageNumber == null || !mounted) return;\n            setState(() => _page = pageNumber);",
    1,
)

# Cleaner app bar with a restrained information hierarchy.
old_appbar = '''      appBar: AppBar(
        toolbarHeight: 48,
        titleSpacing: 0,
        title: Text(_pageCount == 0 ? 'PDF Reader' : 'الصفحة $_page / $_pageCount', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
        actions: [PopupMenuButton<TranslationLayout>(tooltip: 'طريقة عرض الترجمة', icon: const Icon(Icons.view_quilt_outlined, size: 22), initialValue: _layout, onSelected: (value) => setState(() => _layout = value), itemBuilder: (_) => TranslationLayout.values.map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value)))).toList())],
      ),
'''
new_appbar = '''      appBar: AppBar(
        toolbarHeight: 54,
        titleSpacing: 2,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('PDF Reader', style: TextStyle(fontSize: 14.5, fontWeight: FontWeight.w800, letterSpacing: .05)),
            if (_pageCount > 0) Text('الصفحة $_page من $_pageCount', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: scheme.onSurfaceVariant)),
          ],
        ),
        actions: [
          PopupMenuButton<TranslationLayout>(
            tooltip: 'طريقة عرض الترجمة',
            icon: const Icon(Icons.view_quilt_outlined, size: 21),
            initialValue: _layout,
            onSelected: (value) => setState(() => _layout = value),
            itemBuilder: (_) => TranslationLayout.values.map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value)))).toList(),
          ),
          const SizedBox(width: 2),
        ],
      ),
'''
if old_appbar not in s:
    raise SystemExit('Android app bar marker not found')
s = s.replace(old_appbar, new_appbar, 1)

# Replace only the existing bottom controls with a compact responsive dock.
start = s.find('      bottomNavigationBar: SafeArea(\n')
end_marker = '      ),\n    );\n  }\n}\n'
if start == -1:
    raise SystemExit('bottomNavigationBar start not found')
end = s.find(end_marker, start)
if end == -1:
    raise SystemExit('bottomNavigationBar end not found')
end += len('      ),\n')

dock = '''      bottomNavigationBar: SafeArea(
        top: false,
        child: Material(
          color: Colors.white,
          elevation: 1,
          surfaceTintColor: Colors.transparent,
          child: Container(
            decoration: const BoxDecoration(border: Border(top: BorderSide(color: Color(0xFFE5E7EE)))),
            padding: const EdgeInsets.fromLTRB(8, 7, 8, 8),
            child: Directionality(
              textDirection: TextDirection.rtl,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final compact = constraints.maxWidth < 390;
                  final gap = compact ? 4.0 : 6.0;
                  final smallWidth = compact ? 52.0 : 60.0;
                  final translateWidth = compact ? 42.0 : 46.0;
                  final buttonHeight = compact ? 40.0 : 42.0;
                  return Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _page > 1 ? () => _go(_page - 1) : null,
                          style: OutlinedButton.styleFrom(minimumSize: Size(0, buttonHeight), padding: const EdgeInsets.symmetric(horizontal: 4), side: BorderSide(color: scheme.outlineVariant)),
                          child: compact ? const Icon(Icons.chevron_right_rounded, size: 21) : const Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [Icon(Icons.chevron_right_rounded, size: 19), SizedBox(width: 2), Text('السابق')]),
                        ),
                      ),
                      SizedBox(width: gap),
                      Expanded(
                        child: FilledButton(
                          onPressed: _toggleSpeech,
                          style: FilledButton.styleFrom(minimumSize: Size(0, buttonHeight), padding: const EdgeInsets.symmetric(horizontal: 4)),
                          child: Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [Icon(_speaking ? Icons.stop_rounded : Icons.play_arrow_rounded, size: 20), if (!compact) ...[const SizedBox(width: 4), Text(_speaking ? 'إيقاف' : 'قراءة')]]),
                        ),
                      ),
                      SizedBox(width: gap),
                      SizedBox(
                        width: smallWidth,
                        child: OutlinedButton(
                          onPressed: () {
                            const rates = <double>[.25, .35, .4, .45, .5, .6, .75, 1.0];
                            var index = rates.indexWhere((value) => (value - _speechRate).abs() < .001);
                            index = index < 0 ? 3 : (index + 1) % rates.length;
                            _setRate(rates[index]);
                          },
                          style: OutlinedButton.styleFrom(minimumSize: Size(0, buttonHeight), padding: EdgeInsets.zero, side: BorderSide(color: scheme.outlineVariant)),
                          child: Text('${visibleRate.toStringAsFixed(1)}x', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
                        ),
                      ),
                      SizedBox(width: gap),
                      SizedBox(
                        width: translateWidth,
                        child: FilledButton.tonal(
                          onPressed: _busy ? null : _translatePage,
                          style: FilledButton.styleFrom(minimumSize: Size(0, buttonHeight), padding: EdgeInsets.zero),
                          child: _busy ? const SizedBox(width: 15, height: 15, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.translate_rounded, size: 18),
                        ),
                      ),
                      SizedBox(width: gap),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _page < _pageCount ? () => _go(_page + 1) : null,
                          style: OutlinedButton.styleFrom(minimumSize: Size(0, buttonHeight), padding: const EdgeInsets.symmetric(horizontal: 4), side: BorderSide(color: scheme.outlineVariant)),
                          child: compact ? const Icon(Icons.chevron_left_rounded, size: 21) : const Row(mainAxisAlignment: MainAxisAlignment.center, mainAxisSize: MainAxisSize.min, children: [Icon(Icons.chevron_left_rounded, size: 19), SizedBox(width: 2), Text('التالي')]),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ),
      ),
'''
s = s[:start] + dock + s[end:]

p.write_text(s, encoding='utf-8')
print('Applied production-grade Android UI refinement')

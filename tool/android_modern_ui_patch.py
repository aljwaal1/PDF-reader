from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

# Refine the existing visual language only: calmer Material 3 palette and surfaces.
s = s.replace(
    "        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF5B5FEF)),\n        scaffoldBackgroundColor: const Color(0xFFF5F6FA),\n        cardTheme: const CardThemeData(margin: EdgeInsets.zero),",
    "        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4658A9), brightness: Brightness.light),\n        scaffoldBackgroundColor: const Color(0xFFF7F8FB),\n        appBarTheme: const AppBarTheme(backgroundColor: Colors.white, surfaceTintColor: Colors.transparent, elevation: 0, scrolledUnderElevation: 0.5),\n        cardTheme: const CardThemeData(margin: EdgeInsets.zero, elevation: 0),\n        dividerTheme: const DividerThemeData(color: Color(0xFFE5E7EE), thickness: 1),\n        filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)))),\n        outlinedButtonTheme: OutlinedButtonThemeData(style: OutlinedButton.styleFrom(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)))),",
    1,
)

# Make first launch/loading less visually abrupt without changing startup behavior.
s = s.replace(
    "          return const Scaffold(body: Center(child: CircularProgressIndicator()));",
    "          return const Scaffold(body: Center(child: SizedBox(width: 28, height: 28, child: CircularProgressIndicator(strokeWidth: 2.4))));",
    1,
)

# Calm the home screen: same actions and information, less visual duplication/noise.
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
s = s.replace(
    "              const SizedBox(height: 24),\n              Text('كل ما تحتاجه أثناء القراءة', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),\n              const SizedBox(height: 10),\n              Wrap(spacing: 7, runSpacing: 7, children: [_featureChip(Icons.volume_up_rounded, 'قراءة صوتية'), _featureChip(Icons.translate_rounded, 'ترجمة عربية'), _featureChip(Icons.speed_rounded, 'سرعة مرنة'), _featureChip(Icons.visibility_rounded, 'متابعة الكلمة')]),",
    "              const SizedBox(height: 16),",
    1,
)
s = s.replace(
    "      floatingActionButton: _lastBook == null ? null : FloatingActionButton.extended(onPressed: _importing ? null : _pickPdf, icon: const Icon(Icons.add_rounded), label: const Text('كتاب جديد')),\n",
    "",
    1,
)

# Keep the PDF visually dominant with a neutral reading background.
s = s.replace("      color: const Color(0xFFE9ECF2),", "      color: const Color(0xFFF0F1F4),", 1)
s = s.replace("          margin: 3,", "          margin: 2,", 1)

# Calm and tighten the translation surface without changing translation behavior.
s = s.replace(
    "      padding: const EdgeInsets.all(14),",
    "      padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),",
    1,
)
s = s.replace(
    "SelectableText(text, style: const TextStyle(fontSize: 17, height: 1.8))",
    "SelectableText(text, style: const TextStyle(fontSize: 16.5, height: 1.72, letterSpacing: .05))",
    1,
)
s = s.replace("                  elevation: 8,", "                  elevation: 3,", 1)
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

# Cleaner, more information-dense top bar.
old_appbar = '''      appBar: AppBar(
        toolbarHeight: 48,
        titleSpacing: 0,
        title: Text(_pageCount == 0 ? 'PDF Reader' : 'الصفحة $_page / $_pageCount', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
        actions: [PopupMenuButton<TranslationLayout>(tooltip: 'طريقة عرض الترجمة', icon: const Icon(Icons.view_quilt_outlined, size: 22), initialValue: _layout, onSelected: (value) => setState(() => _layout = value), itemBuilder: (_) => TranslationLayout.values.map((value) => PopupMenuItem(value: value, child: Text(_layoutName(value)))).toList())],
      ),
'''
new_appbar = '''      appBar: AppBar(
        toolbarHeight: 52,
        titleSpacing: 2,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('PDF Reader', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, letterSpacing: .1)),
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
        ],
      ),
'''
if old_appbar not in s:
    raise SystemExit('Android app bar marker not found')
s = s.replace(old_appbar, new_appbar, 1)

# Replace only the existing bottom controls with a balanced compact dock.
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
          elevation: 2,
          surfaceTintColor: Colors.transparent,
          child: Container(
            decoration: const BoxDecoration(border: Border(top: BorderSide(color: Color(0xFFE5E7EE)))),
            padding: const EdgeInsets.fromLTRB(8, 7, 8, 8),
            child: Directionality(
              textDirection: TextDirection.rtl,
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _page > 1 ? () => _go(_page - 1) : null,
                      icon: const Icon(Icons.chevron_right_rounded, size: 19),
                      label: const Text('السابق'),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(0, 42),
                        padding: const EdgeInsets.symmetric(horizontal: 5),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        side: BorderSide(color: scheme.outlineVariant),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: _toggleSpeech,
                      icon: Icon(_speaking ? Icons.stop_rounded : Icons.play_arrow_rounded, size: 20),
                      label: Text(_speaking ? 'إيقاف' : 'قراءة'),
                      style: FilledButton.styleFrom(
                        minimumSize: const Size(0, 42),
                        padding: const EdgeInsets.symmetric(horizontal: 5),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  SizedBox(
                    width: 60,
                    child: OutlinedButton(
                      onPressed: () {
                        const rates = <double>[.25, .35, .4, .45, .5, .6, .75, 1.0];
                        var index = rates.indexWhere((value) => (value - _speechRate).abs() < .001);
                        index = index < 0 ? 3 : (index + 1) % rates.length;
                        _setRate(rates[index]);
                      },
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(0, 42),
                        padding: EdgeInsets.zero,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        side: BorderSide(color: scheme.outlineVariant),
                      ),
                      child: Text('${visibleRate.toStringAsFixed(1)}x', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
                    ),
                  ),
                  const SizedBox(width: 6),
                  SizedBox(
                    width: 46,
                    child: FilledButton.tonal(
                      onPressed: _busy ? null : _translatePage,
                      style: FilledButton.styleFrom(
                        minimumSize: const Size(0, 42),
                        padding: EdgeInsets.zero,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      child: _busy
                          ? const SizedBox(width: 15, height: 15, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Icon(Icons.translate_rounded, size: 18),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: _page < _pageCount ? () => _go(_page + 1) : null,
                      icon: const Icon(Icons.chevron_left_rounded, size: 19),
                      label: const Text('التالي'),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(0, 42),
                        padding: const EdgeInsets.symmetric(horizontal: 5),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        side: BorderSide(color: scheme.outlineVariant),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
'''
s = s[:start] + dock + s[end:]

p.write_text(s, encoding='utf-8')
print('Applied hardened focused Android UI refinement')

from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

old = '''  void _captureManualSelection(PdfTextSelection selection) {
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
'''
new = '''  void _captureManualSelection(PdfTextSelection selection) {
    if (!mounted || (_speaking && !_speakingManualSelection)) return;
    () async {
      String text;
      try {
        text = (await selection.getSelectedText()).trim();
      } catch (_) {
        text = '';
      }
      if (!mounted || (_speaking && !_speakingManualSelection) || text == _currentManualSelection) return;
      setState(() => _currentManualSelection = text);
    }();
  }
'''
if old not in s:
    raise SystemExit('manual selection callback marker not found')
s = s.replace(old, new, 1)
s = s.replace('separatorBuilder: (_, __) => const SizedBox(height: 9),', 'separatorBuilder: (context, index) => const SizedBox(height: 9),', 1)

p.write_text(s, encoding='utf-8')
print('Fixed async pdfrx selection callback and analyzer lint')

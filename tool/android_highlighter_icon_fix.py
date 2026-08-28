from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')
old = "Icons.format_color_highlight_rounded"
new = "Icons.highlight_alt_rounded"
if old not in s:
    raise SystemExit('highlighter icon marker not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Fixed Android highlighter icon compatibility')

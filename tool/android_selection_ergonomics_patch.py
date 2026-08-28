from pathlib import Path

p = Path('lib/main.dart')
s = p.read_text(encoding='utf-8')

old = '''          textSelectionParams: PdfTextSelectionParams(
            showContextMenuAutomatically: false,
            onTextSelectionChange: _captureManualSelection,
          ),
'''
new = '''          textSelectionParams: PdfTextSelectionParams(
            enableSelectionHandles: true,
            showContextMenuAutomatically: false,
            buildSelectionHandle: (context, anchor, state) {
              final scheme = Theme.of(context).colorScheme;
              final dragging = state == PdfViewerTextSelectionAnchorHandleState.dragging;
              return SizedBox(
                width: 48,
                height: 48,
                child: Center(
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 90),
                    width: dragging ? 26 : 22,
                    height: dragging ? 26 : 22,
                    decoration: BoxDecoration(
                      color: scheme.primary,
                      shape: BoxShape.circle,
                      border: Border.all(color: Colors.white, width: 3),
                      boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 5, offset: Offset(0, 2))],
                    ),
                    child: const Icon(Icons.drag_indicator_rounded, size: 13, color: Colors.white),
                  ),
                ),
              );
            },
            magnifier: const PdfViewerSelectionMagnifierParams(
              enabled: true,
              magnifierSizeThreshold: 88,
            ),
            onTextSelectionChange: _captureManualSelection,
          ),
'''
if old not in s:
    raise SystemExit('selection params marker not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Applied larger touch-friendly Android selection handles')

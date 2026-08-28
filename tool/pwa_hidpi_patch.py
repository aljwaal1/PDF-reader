from pathlib import Path

index = Path('pwa/index.html')
s = index.read_text(encoding='utf-8')

old = "const base=pg.getViewport({scale:1}),maxW=Math.max(280,$('pdfWrap').clientWidth-6),scale=Math.min(1.8,maxW/base.width),vp=pg.getViewport({scale}),dpr=Math.min(devicePixelRatio||1,2);"
new = "const base=pg.getViewport({scale:1}),maxW=Math.max(280,$('pdfWrap').clientWidth-6),scale=Math.min(1.8,maxW/base.width),vp=pg.getViewport({scale}),cssPixels=Math.max(1,vp.width*vp.height),nativeDpr=Math.max(1,window.devicePixelRatio||1),memorySafe=Math.sqrt(12000000/cssPixels),dpr=Math.max(1,Math.min(nativeDpr*1.5,3,memorySafe));"
if old not in s:
    raise SystemExit('render scale marker not found')
s = s.replace(old, new, 1)

old2 = "const ctx=canvas.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);await pg.render({canvasContext:ctx,viewport:vp}).promise;"
new2 = "const ctx=canvas.getContext('2d',{alpha:false});ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.setTransform(dpr,0,0,dpr,0,0);await pg.render({canvasContext:ctx,viewport:vp}).promise;"
if old2 not in s:
    raise SystemExit('canvas context marker not found')
s = s.replace(old2, new2, 1)

index.write_text(s, encoding='utf-8')

sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
if "pdf-reader-pwa-v14" in w:
    w = w.replace("pdf-reader-pwa-v14", "pdf-reader-pwa-v15", 1)
elif "pdf-reader-pwa-v15" not in w:
    raise SystemExit('service worker cache marker not found')
sw.write_text(w, encoding='utf-8')

print('Applied PWA HiDPI rendering quality patch and bumped cache to v15')

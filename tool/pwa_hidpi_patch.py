from pathlib import Path

index = Path('pwa/index.html')
s = index.read_text(encoding='utf-8')

# Safari/iOS can show clipped or spaced glyphs when a fractional high-DPI
# scale is pre-applied directly to the 2D context. Use PDF.js' supported
# output transform instead and keep the backing-store scale stable.
old = "const base=pg.getViewport({scale:1}),maxW=Math.max(280,$('pdfWrap').clientWidth-6),scale=Math.min(1.8,maxW/base.width),vp=pg.getViewport({scale}),cssPixels=Math.max(1,vp.width*vp.height),nativeDpr=Math.max(1,window.devicePixelRatio||1),memorySafe=Math.sqrt(12000000/cssPixels),dpr=Math.max(1,Math.min(nativeDpr*1.5,3,memorySafe));"
new = "const base=pg.getViewport({scale:1}),maxW=Math.max(280,$('pdfWrap').clientWidth-6),scale=Math.min(1.8,maxW/base.width),vp=pg.getViewport({scale}),nativeDpr=Math.max(1,window.devicePixelRatio||1),dpr=Math.min(nativeDpr,2);"
if old not in s:
    raise SystemExit('current HiDPI render scale marker not found')
s = s.replace(old, new, 1)

old2 = "const ctx=canvas.getContext('2d',{alpha:false});ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.setTransform(dpr,0,0,dpr,0,0);await pg.render({canvasContext:ctx,viewport:vp}).promise;"
new2 = "const ctx=canvas.getContext('2d',{alpha:false});ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';const outputTransform=dpr===1?null:[dpr,0,0,dpr,0,0];await pg.render({canvasContext:ctx,viewport:vp,transform:outputTransform}).promise;"
if old2 not in s:
    raise SystemExit('current canvas rendering marker not found')
s = s.replace(old2, new2, 1)

index.write_text(s, encoding='utf-8')

sw = Path('pwa/sw.js')
w = sw.read_text(encoding='utf-8')
if "pdf-reader-pwa-v16" in w:
    w = w.replace("pdf-reader-pwa-v16", "pdf-reader-pwa-v17", 1)
elif "pdf-reader-pwa-v17" not in w:
    raise SystemExit('service worker cache marker not found')
sw.write_text(w, encoding='utf-8')

print('Applied iOS-safe PDF.js rendering fix and bumped PWA cache to v17')

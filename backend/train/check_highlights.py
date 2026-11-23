import fitz
doc = fitz.open(r'C:\Users\godbl\.gemini\antigravity\brain\8e70e024-6c5c-468c-9d3f-35004567699d\.user_uploaded\media_1795169193050_93475352.pdf')
for pno in [65,67,68,69]:
    page = doc[pno-1]
    drawings = page.get_drawings()
    yd = [d for d in drawings if d.get('fill') and len(d['fill'])>=3 and d['fill'][0] > 0.8 and d['fill'][1] > 0.8 and d['fill'][2] < 0.3]
    print(f'=== PAGE {pno} - Yellow highlights: {len(yd)} ===')
    for d in yd:
        r = d.get('rect')
        print(f'  rect={r}')
        # find text near this rect
        words = page.get_text('words')
        nearby = [w for w in words if w[1] >= r.y0-2 and w[3] <= r.y1+2]
        print(f'  nearby_words={[w[4] for w in nearby[:20]]}')
    print()

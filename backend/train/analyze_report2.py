import fitz
doc = fitz.open(r'C:\Users\godbl\.gemini\antigravity\brain\8e70e024-6c5c-468c-9d3f-35004567699d\.user_uploaded\media_1795169193050_93475352.pdf')
pages_of_interest = [28,32,33,37,38,39,40,41,42,43,44,45,46,47,57,60,63,65,67,68,69,71]
for pno in pages_of_interest:
    page = doc[pno-1]
    text = page.get_text()
    print(f'=== PAGE {pno} ===')
    print(text[:4000])
    print()

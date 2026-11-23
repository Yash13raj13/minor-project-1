import fitz
doc = fitz.open(r'C:\Users\godbl\.gemini\antigravity\brain\8e70e024-6c5c-468c-9d3f-35004567699d\.user_uploaded\media_1795169193050_93475352.pdf')
pages_of_interest = [57,58,59,60,61,62,63,64,65,66,67,68,69,70,71]
for pno in pages_of_interest:
    page = doc[pno-1]
    text = page.get_text()
    print(f'=== PAGE {pno} ===')
    print(text)
    print()

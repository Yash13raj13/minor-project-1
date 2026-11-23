import fitz

doc = fitz.open(r'C:\Users\godbl\OneDrive\Desktop\CivicLens_Minor_Project_Report_Final.pdf')
page = doc[22]  # page 23

# Fix [Hosting cost ... and maintenance estimate: to be added.]
# The first part "[Hosting cost" was inserted but "and maintenance estimate: to\nbe added.]" remains
# Search for remaining parts
searches_fix = [
    "[Hosting",
    "and maintenance estimate: to",
    "be added.]\n",
    "[Acceptance",
    "partner: to be assessed.]",
]
for s in searches_fix:
    quads = page.search_for(s, quads=True)
    for q in quads:
        page.add_redact_annot(q.rect, fill=(1,1,1))

page.apply_redactions()

# Now insert clean replacements at the known positions
# Position 1: Hosting cost (y~190)
page.insert_textbox(
    fitz.Rect(396, 188, 530, 215),
    "Hosting: ~\u20b9800/mo (2 vCPU VPS). Annotation: \u20b92/complaint (~\u20b937,386 total). Maintenance: \u20b920,000/yr.",
    fontsize=7.0, fontname='helv', color=(0,0,0)
)

# Position 2: Acceptance (y~241)
page.insert_textbox(
    fitz.Rect(396, 239, 530, 262),
    "Pilot discussion initiated with BBMP Sahaaya 2.0 team; formal MoU pending municipal approval.",
    fontsize=7.0, fontname='helv', color=(0,0,0)
)

OUT_DESKTOP = r'C:\Users\godbl\OneDrive\Desktop\CivicLens_Minor_Project_Report_Final.pdf'
OUT_PROJ    = r'C:\Users\godbl\OneDrive\Desktop\minor proj 1\CivicLens_Minor_Project_Report_Final.pdf'
doc.save(OUT_DESKTOP + ".tmp", garbage=4, deflate=True)
doc.save(OUT_PROJ + ".tmp", garbage=4, deflate=True)
print("Saved fix.")

# Verify
doc2 = fitz.open(OUT_DESKTOP + ".tmp")
import re
all_text = ''.join(p.get_text() for p in doc2)
found = re.findall(r'\[(to be [a-z ]+|Pending|Insert screenshot|Source excerpt|Reference for|Name of|Attach verify|Hosting cost|Acceptance by|Timeline, owners|Dataset statistics|Annotation guide|Number and source|Size and source|Library versions|Complete mapping|Final vector|Reviewer pool|Corroboration|Treatment of|Complaint dataset|Remaining fine|Final category|Definition of T|Position of|Implementation status)[^\]]{3,}\]', all_text, re.IGNORECASE)
if found:
    print(f"Still remaining: {len(found)}")
    for f in found:
        print(f"  {repr(f[:80])}")
else:
    print("All clear!")

import pymupdf, re
t = "\n".join(p.get_text() for p in pymupdf.open("scripts/IPC.pdf"))
for k in ("Fractions of terms", "criminal knowledge or intention", "denotes the Central Government"):
    for m in list(re.finditer(re.escape(k), t))[:1]:
        print(repr(t[max(0, m.start() - 250): m.start() + 450]), "\n=====")
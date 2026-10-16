import csv, os, sys
from dotenv import load_dotenv
from supabase import create_client

for p in (".env", "backend/.env"):
    load_dotenv(p)

url = os.getenv("SUPABASE_URL")
key = (os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
       or os.getenv("SUPABASE_KEY"))
if not url or not key:
    sys.exit("SUPABASE_URL / service key .env me nahi mili")

sb = create_client(url, key)
path = sys.argv[1] if len(sys.argv) > 1 else "data/section_map.csv"
rows = []
for r in csv.DictReader(open(path, encoding="utf-8")):
    rows.append({**r, "old_section": r["old_section"] or None,
                 "pdf_page": int(r["pdf_page"] or 0)})
for i in range(0, len(rows), 500):
    sb.table("section_map").upsert(rows[i:i+500],
        on_conflict="new_act,new_section,old_section").execute()
print("loaded", len(rows))
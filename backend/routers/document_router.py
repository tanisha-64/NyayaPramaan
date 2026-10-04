
"""

Document Router — THE CORE FIX:

1. Classification now runs on the FULL Gemini-extracted text (not a short

   local preview), so genuine scanned/old judgments are no longer

   falsely rejected.

2. Heavy page-by-page chunking/embedding runs as a background task, so

   large (100+ page) documents respond fast instead of blocking the request.

3. Summary + timeline are generated synchronously (fast, one Gemini call

   each) so the user gets a usable response quickly.

"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks

import tempfile

import os



from ai_core.rag.document_reader import read_case_file_with_gemini

from ai_core.rag.summarizer import summarize_case

from ai_core.timeline.extractor import extract_timeline

from ai_core.rag.vector_store import get_supabase_client

from ai_core.rag.document_chunker import chunk_and_index_pdf

from ai_core.rag.document_classifier import classify_document, REJECTION_MESSAGE

from backend.db.supabase_storage import upload_case_file

from backend.auth.supabase_auth import get_current_user



router = APIRouter()





def _background_index_pages(tmp_path: str, case_id: str, suffix: str):

    """Runs AFTER the response has been sent -- indexes pages for Q&A."""

    try:

        if suffix.lower() == ".pdf":

            chunk_and_index_pdf(tmp_path, case_id)

    except Exception as e:

        print(f"[document_router] Background indexing failed for {case_id}: {e}")

    finally:

        if os.path.exists(tmp_path):

            os.remove(tmp_path)





@router.post("/upload")

async def upload_case(background_tasks: BackgroundTasks, file: UploadFile = File(...), user=Depends(get_current_user)):

    file_bytes = await file.read()

    suffix = os.path.splitext(file.filename)[1]



    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:

        tmp.write(file_bytes)

        tmp_path = tmp.name



    # 1. Read the FULL document via Gemini FIRST -- reliable even for

    #    scanned/old judgments (unlike a short raw-pypdf preview).

    case_text = read_case_file_with_gemini(tmp_path)



    # 2. Classify on the FULL extracted text.

    classification = classify_document(case_text[:4000])

    if not classification["is_legal_relevant"]:

        os.remove(tmp_path)

        raise HTTPException(status_code=422, detail=REJECTION_MESSAGE)



    # 3. Store original file + create case record.

    file_url = upload_case_file(file_bytes, file.filename)

    client = get_supabase_client()

    result = client.table("cases").insert({

        "user_id": user.id, "filename": file.filename,

        "case_text": case_text, "summary": "",

    }).execute()

    case_id = result.data[0]["id"]



    # 4. Fast synchronous summary + timeline (one Gemini/Groq call each).

    summary = summarize_case(case_text)

    timeline = extract_timeline(case_text)

    client.table("cases").update({"summary": summary}).eq("id", case_id).execute()



    # 5. SLOW part (page-by-page embedding) -> background, response returns now.

    background_tasks.add_task(_background_index_pages, tmp_path, case_id, suffix)



    return {

        "case_id": case_id,

        "file_url": file_url,

        "filename": file.filename,

        "summary": summary,

        "timeline": timeline,

        "document_type": classification["document_type"],

    }





@router.delete("/{case_id}")

def delete_document(case_id: str, user=Depends(get_current_user)):

    client = get_supabase_client()

    client.table("document_chunks").delete().eq("case_id", case_id).execute()

    client.table("cases").delete().eq("id", case_id).eq("user_id", user.id).execute()

    return {"deleted": case_id}


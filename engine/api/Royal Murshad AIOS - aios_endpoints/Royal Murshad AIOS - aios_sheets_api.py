from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional, List
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_sheets")
import aios_sheets as s

router = APIRouter(prefix="/api/sheets", tags=["sheets"])

class CreateReq(BaseModel):
    name: str
    description: str = ""
    rows: Optional[List[List]] = None

class UpdateReq(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rows: Optional[List[List]] = None

class ImportReq(BaseModel):
    csv_text: str

@router.get("/stats")
def _stats(): return s.stats()

@router.get("/list")
def _list(): return s.list_sheets()

@router.get("/sheet/{sid}")
def _get(sid: str): return s.get(sid)

@router.post("/create")
def _create(req: CreateReq): return s.create(req.name, req.description, req.rows)

@router.post("/update/{sid}")
def _update(sid: str, req: UpdateReq):
    return s.update(sid, req.name, req.description, req.rows)

@router.post("/delete/{sid}")
def _delete(sid: str): return s.delete(sid)

@router.get("/export/{sid}.xlsx")
def _export(sid: str):
    r = s.export_xlsx(sid)
    if not r.get("ok"):
        return r
    fname = r["name"].replace(" ", "_") + ".xlsx"
    return Response(content=r["data"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'})

@router.post("/import-csv/{sid}")
def _import(sid: str, req: ImportReq): return s.import_csv(sid, req.csv_text)

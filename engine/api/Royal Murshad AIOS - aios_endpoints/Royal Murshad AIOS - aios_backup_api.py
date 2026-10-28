from fastapi import APIRouter
from pydantic import BaseModel
import sys
sys.path.insert(0, r"D:\01_PROJECTS\AIOS\06_TOOLS\aios_backup")
import aios_backup as b

router = APIRouter(prefix="/api/backup", tags=["backup"])

class BackupReq(BaseModel):
    source: str
    tag: str = ""

class RestoreReq(BaseModel):
    encrypted_file: str
    dest: str

@router.get("/stats")
def _stats(): return b.stats()

@router.get("/list")
def _list(): return b.list_backups()

@router.post("/run")
def _run(req: BackupReq): return b.backup_folder(req.source, req.tag or None)

@router.post("/restore")
def _restore(req: RestoreReq): return b.restore(req.encrypted_file, req.dest)

@router.post("/rotate")
def _rotate(keep: int = 7): return b.rotate(keep)

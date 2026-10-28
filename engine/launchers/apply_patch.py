import pathlib

p = pathlib.Path(r'D:\01_PROJECTS\Royal Murshad AIOS\18_ENV\launchers\aios_backend_launcher.py')
text = p.read_text(encoding='utf-8')

old = """for p in (LEADS, SERVER_DIR, r'D:\01_PROJECTS\Royal Murshad AIOS', AIOS, os.path.join(SERVER_DIR, 'royal_shim')):
    if p and p not in sys.path:
        sys.path.insert(0, p)"""

new = """MEM_PATH = r'D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 04_MEMORY\Royal Murshad AIOS - aios_memory'
for p in (LEADS, SERVER_DIR, r'D:\01_PROJECTS\Royal Murshad AIOS', AIOS, os.path.join(SERVER_DIR, 'royal_shim'), MEM_PATH):
    if p and p not in sys.path:
        sys.path.insert(0, p)

# Patch the DB module before master server loads it
import pathlib as _pathlib
try:
    import aios_chat_db
    aios_chat_db.ROOT = _pathlib.Path(r'D:\01_PROJECTS\Royal Murshad AIOS\Royal Murshad AIOS - 04_MEMORY\Royal Murshad AIOS - aios_memory')
    aios_chat_db.DATA_DIR = aios_chat_db.ROOT / 'Royal Murshad AIOS - data'
    aios_chat_db.CHAT_DB = aios_chat_db.DATA_DIR / 'Royal Murshad AIOS - chat.db'
    print(f'[wrapper] Patched aios_chat_db to use {aios_chat_db.CHAT_DB}')
except Exception as e:
    print(f'[wrapper] WARNING: Could not pre-patch aios_chat_db: {e}', file=sys.stderr)"""

if old in text:
    text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')
    print('PATCH APPLIED SUCCESSFULLY.')
else:
    print('ERROR: Target string not found. No changes made.')

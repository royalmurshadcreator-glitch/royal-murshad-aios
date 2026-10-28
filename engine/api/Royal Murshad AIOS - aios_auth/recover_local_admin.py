"""Offline password recovery for a local Royal Murshad AIOS administrator."""

import getpass
import importlib.util
from pathlib import Path


AUTH_SOURCE = Path(__file__).with_name("Royal Murshad AIOS - aios_auth.py")
spec = importlib.util.spec_from_file_location("royal_local_auth", AUTH_SOURCE)
if spec is None or spec.loader is None:
    raise SystemExit("Local auth implementation could not be loaded")
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


def main() -> int:
    print("Reset a local administrator password using local machine access.")
    username = input("Administrator username: ").strip()
    password = getpass.getpass("New administrator password (16 or more characters): ")
    confirmation = getpass.getpass("Confirm new password: ")
    if password != confirmation:
        print("Passwords did not match; no account was changed.")
        return 2
    result = auth.recover_local_admin(username, password)
    if not result.get("ok"):
        print("Recovery was not completed: " + str(result.get("error", "unknown error")))
        return 1
    print("Password reset. All existing local sessions were invalidated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

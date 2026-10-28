"""Explicit local-only first administrator provisioning for Royal Murshad AIOS."""

import getpass
import importlib.util
from pathlib import Path
import sys


AUTH_SOURCE = Path(__file__).with_name("Royal Murshad AIOS - aios_auth.py")
spec = importlib.util.spec_from_file_location("royal_local_auth", AUTH_SOURCE)
if spec is None or spec.loader is None:
    raise SystemExit("Local auth implementation could not be loaded")
auth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auth)


def main() -> int:
    print("Create the first Royal Murshad AIOS administrator on this machine.")
    print("Credentials are entered interactively and are not saved in this script or command line.")
    username = input("Administrator username: ").strip()
    password = getpass.getpass("Administrator password (16 or more characters): ")
    confirmation = getpass.getpass("Confirm administrator password: ")
    if password != confirmation:
        print("Passwords did not match; no account was created.")
        return 2
    result = auth.provision_first_admin(username, password)
    if not result.get("ok"):
        print("Provisioning was not completed: " + str(result.get("error", "unknown error")))
        return 1
    print("Local administrator created. Store the password in your approved password manager.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

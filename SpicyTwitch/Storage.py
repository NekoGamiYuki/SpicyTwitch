# Imports-----------------------------------------------------------------------
import os
import platform

# Setup storage directory ------------------------------------------------------
# This sets up the storage directory based on the OS it is being run on.
# TODO: Add support for BSD, specifically FreeBSD.
os_name = platform.system()
if os_name == "Darwin" or os_name == "Windows":  # NOTE: Darwin is Mac OS
    primary_storage_directory = os.path.join(
        os.path.expanduser('~'), "Documents", "SpicyTwitch"
    )
elif os_name == "Linux":  # I'd like to interject for a moment...
    primary_storage_directory = os.path.join(
        os.path.expanduser('~'), ".config", "spicytwitch"
    )
else:
    # TODO: Consider placing storage in same directory as file and warning user.
    #       of storage issue?
    raise RuntimeError("Unsupported/Untested OS is being run.")


if not os.path.exists(primary_storage_directory):
    os.makedirs(primary_storage_directory)

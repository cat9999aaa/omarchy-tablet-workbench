"""A failed publisher call is not proof that the original UI was restored."""
import hashlib

def verify_plugins_restored(originals, read_manifest, read_version):
    if not originals:return False
    try:
        return all(hashlib.sha256(read_manifest(name)).hexdigest()==old['sha256']
                   and read_version(name)==old['version']
                   for name,old in originals.items())
    except (OSError,ValueError,KeyError,RuntimeError):
        return False

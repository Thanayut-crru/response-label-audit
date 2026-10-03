"""How the released files were renamed from the procedure's former name to RDFL.

The rename is a byte-level substitution applied to text files and to paths. It is the only
difference between a released file and the file it came from, with one documented exception
(ADJUSTMENTS) that keeps the random streams of the published run unchanged. The checker
tools/verify_release.py applies these same rules to the archived originals.
"""
from pathlib import PurePosixPath

RULES = ((b'FPA', b'RDFL'), (b'fpa', b'rdfl'))
TEXT_SUFFIXES = {'.py', '.md', '.json', '.csv', '.txt'}

# 07_power_analysis.py seeds each bootstrap with len(comparator); the renamed comparator name is
# one character longer per occurrence, so the length used at the time of the analysis is restored.
ADJUSTMENTS = {
    'scripts/07_power_analysis.py': [(
        b'+ len(comparator) + len(name))',
        b"+ len(comparator) - comparator.count('RDFL') + len(name))  # seed uses the pre-rename name length",
    )],
}


def rename_bytes(data):
    for old, new in RULES:
        data = data.replace(old, new)
    return data


def rename_path(relative):
    return rename_bytes(str(PurePosixPath(relative)).encode('utf-8')).decode('utf-8')


def released_bytes(relative, data):
    """The released content of a file whose original is `data` at original path `relative`."""
    if PurePosixPath(relative).suffix.lower() not in TEXT_SUFFIXES:
        return data
    data = rename_bytes(data)
    for old, new in ADJUSTMENTS.get(rename_path(relative), []):
        assert data.count(old) == 1, (relative, old)
        data = data.replace(old, new)
    return data

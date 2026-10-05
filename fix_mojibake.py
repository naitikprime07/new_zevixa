"""Repair double-encoded (latin-1 mojibake) UTF-8 characters across the site.

The offline clone stored some UTF-8 bytes as latin-1, so real characters like
'»', a non-breaking space, and '×' became garbage like 'Â»', 'Â ', 'Ã—'.
This decodes those clusters back to the intended characters. Operates on site/.
"""
import glob
import os
import re

ROOT = "site"

# A mojibake cluster = a UTF-8 lead byte + its continuation byte(s), each
# currently sitting as a separate latin-1 code point.
MOJI = re.compile(
    "[\u00c2-\u00df][\u0080-\u00bf]"
    "|[\u00e0-\u00ef][\u0080-\u00bf]{2}"
    "|[\u00f0-\u00f4][\u0080-\u00bf]{3}"
)


def repair(match):
    s = match.group(0)
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    return fixed if fixed != s else s


def process(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new = MOJI.sub(repair, text)
    if new != text:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        return len(text) and MOJI.subn(repair, text)[1]
    return 0


def main():
    total = 0
    for p in glob.glob(os.path.join(ROOT, "**", "*.html"), recursive=True):
        n = process(p)
        if n:
            print("fixed %2d  %s" % (n, p))
            total += n
    print("Total clusters repaired:", total)


if __name__ == "__main__":
    main()

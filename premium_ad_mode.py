#!/usr/bin/env python3
"""
Toggle the PREMIUM page ad units between LIVE and Google TEST inventory.

Only the ad-unit PATHS change. Sizes, div IDs, layout, scripts, structure:
everything else is left exactly as-is.

Usage:
  python premium_ad_mode.py test   # repoint to Google test ad units (ads always fill)
  python premium_ad_mode.py live   # restore your real /21753324030/pixoria.fyi_* units

A one-time backup (premium_live_ads.html.bak at repo root) is taken on the first
'test' run so 'live' can restore the pristine original.
"""

import os
import sys
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(ROOT, "site", "premium", "index.html")
BACKUP = os.path.join(ROOT, "premium_live_ads.html.bak")

# live path -> Google test path
LIVE_TO_TEST = [
    ("/21753324030/pixoria.fyi_Floating", "/21775744923/example/banner"),
    ("/21753324030/pixoria.fyi_Bottom", "/21775744923/example/banner"),
    ("/21753324030/pixoria.fyi_Center_Content", "/21775744923/example/banner"),
    ("/21753324030/pixoria.fyi_Interstitial", "/21775744923/example/interstitial"),
    # Video/outstream: repoint to Google's official IMA sample tag (single_ad_samples,
    # linear). This is documented to always return a real video test creative, whereas
    # an ad-hoc path like /example/outstream often returns no fill. The appended
    # cust_params selects the linear sample; it rides along the existing query string.
    ("/21753324030/pixoria.fyi_outstream_VAST_1",
     "/21775744923/external/single_ad_samples&cust_params=sample_ct%3Dlinear"),
]


def to_test():
    with open(TARGET, "r", encoding="utf-8") as f:
        t = f.read()
    # snapshot pristine original once
    if not os.path.exists(BACKUP) and "21753324030" in t:
        shutil.copyfile(TARGET, BACKUP)
        print("Saved original live-ads backup ->", os.path.basename(BACKUP))
    n = 0
    for live, test in LIVE_TO_TEST:
        c = t.count(live)
        if c:
            t = t.replace(live, test)
            n += c
    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(t)
    print("Switched to TEST ad units: %d path(s) replaced." % n)
    print("Remaining live '/21753324030' refs:", t.count("21753324030"))


def to_live():
    if not os.path.exists(BACKUP):
        print("No backup found; nothing to restore.")
        return
    shutil.copyfile(BACKUP, TARGET)
    print("Restored ORIGINAL live ad units from backup.")


def main():
    mode = (sys.argv[1] if len(sys.argv) > 1 else "test").lower()
    if mode == "test":
        to_test()
    elif mode == "live":
        to_live()
    else:
        print("Unknown mode '%s'. Use: test | live" % mode)


if __name__ == "__main__":
    main()

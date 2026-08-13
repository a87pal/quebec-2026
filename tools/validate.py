#!/usr/bin/env python3
"""Safety net for any scripted edit of a guide.

Checks tag balance, duplicate ids, that every href="#..." resolves, and diffs
the prose against a baseline to catch content silently dropped by a bad slice.

The baseline defaults to the last commit, so this works with no setup:
    git show HEAD:destinations/<slug>/guide.html

Hard failures (unbalanced tags, duplicate ids, dead anchors) exit non-zero so
CI can gate on them. The prose diff is advisory - expect a handful of false
positives from sentences whose neighbours changed. Look at the list, don't
just read the count.

Usage:  python3 tools/validate.py [--dest SLUG] [--baseline REF|PATH]
"""
import collections, io, os, re, subprocess, sys

import _dest

TAGS = ("section", "div", "details", "summary", "article", "table", "tbody", "thead",
        "ul", "ol", "li", "p", "span", "a", "h2", "h3", "h4", "h5", "td", "tr", "th",
        "main", "svg", "g", "text", "nav", "button")


def read_baseline(dest, ref):
    """Baseline from a git ref (default) or a plain file path."""
    if os.path.exists(ref):
        return io.open(ref, encoding="utf-8").read(), ref
    rel = os.path.relpath(dest.guide, _dest.ROOT)
    spec = "%s:%s" % (ref, rel)
    try:
        out = subprocess.run(["git", "-C", _dest.ROOT, "show", spec],
                             capture_output=True, check=True)
        return out.stdout.decode("utf-8"), spec
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, spec


def textof(t):
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()


# --- structural checks, shared with build.py -------------------------------
def tag_balance(html):
    """[(tag, opens, closes)] for every tag type that does not balance."""
    out = []
    for tag in TAGS:
        o = len(re.findall(r"<%s[\s>]" % tag, html))
        c = len(re.findall(r"</%s>" % tag, html))
        if o != c:
            out.append((tag, o, c))
    return out


def duplicate_ids(html):
    return sorted(k for k, v in collections.Counter(re.findall(r'\sid="([^"]+)"', html)).items() if v > 1)


def dead_links(html):
    """Internal href="#..." targets with no matching id."""
    return sorted({h for h in re.findall(r'href="#([^"]+)"', html) if ('id="%s"' % h) not in html})


def structural_problems(html):
    """One-line summaries of every hard failure. Empty means structurally sound."""
    out = []
    for tag, o, c in tag_balance(html):
        out.append("unbalanced <%s> (%d open, %d close)" % (tag, o, c))
    for i in duplicate_ids(html):
        out.append('duplicate id="%s"' % i)
    for h in dead_links(html):
        out.append('dead internal link href="#%s"' % h)
    return out


def main():
    def extra(ap):
        ap.add_argument('--baseline', default='HEAD',
                        help='git ref or file path to diff prose against (default: HEAD)')
    dest, args = _dest.from_args('Validate a guide after scripted edits.', extra)

    if not os.path.exists(dest.guide):
        sys.exit('error: %s not found' % dest.guide)
    new = io.open(dest.guide, encoding="utf-8").read()
    fatal = []

    print("=== tag balance ===")
    unbalanced = tag_balance(new)
    for tag, o, c in unbalanced:
        print("  UNBALANCED %-8s open=%d close=%d" % (tag, o, c))
    print("  all balanced" if not unbalanced else "  %d unbalanced" % len(unbalanced))
    if unbalanced:
        fatal.append("%d unbalanced tag type(s)" % len(unbalanced))

    print("\n=== outline ===")
    for m in re.finditer(r'<section class="part[^"]*" id="([^"]+)">|<h2>(.*?)</h2>|<div class="subsec" id="([^"]+)">|<h3>(.*?)</h3>', new):
        if m.group(1):   print("PART  #%s" % m.group(1))
        elif m.group(2): print("  h2   %s" % m.group(2)[:70])
        elif m.group(3): print("  SUB  #%s" % m.group(3))
        elif m.group(4): print("    h3 %s" % m.group(4)[:70])

    print("\n=== nav ===")
    navm = re.search(r"<nav>\n(.*?)\n</nav>", new, re.S)
    if navm:
        links = re.findall(r'href="#([^"]+)">([^<]+)<', navm.group(1))
        print("  ", links)
        miss = [h for h, _ in links if ('id="%s"' % h) not in new]
        print("   unresolved:", miss or "none")
        if miss:
            fatal.append("%d unresolved nav anchor(s)" % len(miss))
    else:
        print("   no <nav> block")

    print("\n=== all internal links resolve ===")
    miss = dead_links(new)
    print("   ", miss or "all resolve")
    if miss:
        fatal.append("%d dead internal link(s)" % len(miss))

    print("\n=== days ===")
    print("   collapsed day details:", len(re.findall(r'<details class="day dayd" id="day-', new)))
    print("   leftover <article id=\"day-:", len(re.findall(r'<article id="day-', new)))
    print("   day-by-day table drawer:", 'id="daytable"' in new)
    print("   open-by-default details:", len(re.findall(r'<details[^>]*\sopen', new)))

    print("\n=== duplicate ids ===")
    d = duplicate_ids(new)
    print("   ", d or "none")
    if d:
        fatal.append("%d duplicate id(s)" % len(d))

    # Drawer order per part, so a bad slice that reshuffles or drops a level-1
    # drawer shows up as a changed line. No part id is hardcoded here - which
    # one holds the drawers is the guide's business, not the engine's.
    print("\n=== level-1 drawers, by part ===")
    parts = list(re.finditer(r'<section class="part[^"]*" id="([^"]+)">', new))
    for k, m in enumerate(parts):
        end = parts[k + 1].start() if k + 1 < len(parts) else len(new)
        drawers = re.findall(r'<details class="l1" id="([^"]+)">', new[m.start():end])
        if drawers:
            print("   #%-12s %s" % (m.group(1), drawers))

    print("\n=== content preserved ===")
    old, spec = read_baseline(dest, args.baseline)
    if old is None:
        print("   no baseline at %s - skipping (first commit?)" % spec)
    else:
        o, n = textof(old), textof(new)
        os_ = set(s.strip() for s in re.split(r"(?<=[.!?]) ", o) if len(s.strip()) > 40)
        ns_ = set(s.strip() for s in re.split(r"(?<=[.!?]) ", n) if len(s.strip()) > 40)
        lost = sorted(os_ - ns_)
        print("   baseline %s" % spec)
        print("   old %d / new %d / dropped %d" % (len(os_), len(ns_), len(lost)))
        for s in lost[:25]:
            print("     - " + s[:140])

    if fatal:
        sys.exit("\nFAILED: " + "; ".join(fatal))
    print("\nOK")


if __name__ == '__main__':
    main()

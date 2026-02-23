#!/usr/bin/env python3
import argparse
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import unquote

TEXT_EXTS = {".html", ".css", ".js", ".json", ".xml", ".txt", ".webmanifest", ".md"}
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".mp4", ".webm", ".woff", ".woff2", ".ttf", ".otf", ".pdf"}

ASSET_DIRS = {"img", "cards", "icons", "socials", "vids", "Documents"}

# Matches:
#  - href="..."
#  - src='...'
#  - url(...)
#  - JSON strings containing paths (we treat as plain text replacement)
HREFSRC_RE = re.compile(r"""(?P<attr>\b(?:href|src)\s*=\s*["'])(?P<val>[^"']+)(?P<end>["'])""", re.IGNORECASE)
CSSURL_RE  = re.compile(r"""(?P<pre>url\(\s*["']?)(?P<val>[^"')]+)(?P<end>["']?\s*\))""", re.IGNORECASE)

SKIP_PREFIXES = ("http:", "https:", "mailto:", "tel:", "#", "data:", "javascript:")

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def kebab(s: str) -> str:
    s = unquote(s)
    s = s.replace("_", "-")
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"[^a-zA-Z0-9.\-\/]+", "-", s)
    s = re.sub(r"-{2,}", "-", s)
    return s.strip("-")

def is_text_file(p: Path) -> bool:
    return p.suffix.lower() in TEXT_EXTS

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", errors="ignore")

def safe_rel_to_root(site_root: Path, current_file: Path, ref: str) -> str:
    """
    Convert a reference into a root-absolute path where possible.
    This avoids /about/img/... type bugs on Netlify clean URLs.
    """
    ref = ref.strip()
    if not ref or ref.startswith(SKIP_PREFIXES) or ref.startswith("${"):
        return ref

    # Already root absolute
    if ref.startswith("/"):
        return ref

    # Normalize accidental ..// segments
    ref = re.sub(r"^\.\.//+", "/", ref)

    # If it is a bare filename like 967A4321.jpg, assume it is in root
    if "/" not in ref and ref.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".mp4", ".webm", ".pdf", ".css", ".js")):
        return "/" + ref

    # Resolve relative path against current file, then convert to root-absolute
    abs_target = (current_file.parent / ref).resolve()
    try:
        rel = abs_target.relative_to(site_root.resolve())
    except Exception:
        return ref

    return "/" + rel.as_posix()

def normalise_internal_links(ref: str) -> str:
    """
    Normalise internal page routes to clean URLs.
    Leaves external links untouched.
    """
    ref = ref.strip()
    if not ref or ref.startswith(SKIP_PREFIXES) or ref.startswith("${"):
        return ref

    # Only normalise site-internal
    if ref.startswith("http:") or ref.startswith("https:"):
        return ref

    # Collapse duplicate slashes
    ref = re.sub(r"//+", "/", ref)

    # Home
    if ref in {"index.html", "/index.html"}:
        return "/"

    # Map old pages if present
    legacy = {
        "/team.html": "/team/",
        "/events.html": "/events/",
        "/about.html": "/about/",
        "team.html": "/team/",
        "events.html": "/events/",
        "about.html": "/about/",
    }
    if ref in legacy:
        return legacy[ref]

    # Specific legacy event pages into /events/
    if ref in {"events-tech-mixer.html", "/events-tech-mixer.html", "events/ctc-deliveroo-mixer.html", "/events/ctc-deliveroo-mixer.html"}:
        return "/events/"

    # Ensure section folders end with /
    if ref in {"/about", "/events", "/team"}:
        return ref + "/"

    return ref

def plan_renames(site_root: Path, rename_assets: bool) -> dict:
    """
    Plan file renames for case fixes and optional kebab-case normalization.
    Returns map old_rel -> new_rel (posix).
    """
    mapping = {}

    for p in site_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(site_root).as_posix()
        parts = rel.split("/")

        # Do not rename dotfiles or Netlify control files
        if parts[-1].startswith(".") or parts[-1] in {"_redirects", "_headers"}:
            continue

        # Keep Documents as-is (PDF names often intentional)
        if parts[0] == "Documents":
            continue

        # Keep page folder index.html names as-is
        if parts[-1].lower() == "index.html":
            continue

        # Only normalise assets by default
        is_asset = parts[0] in ASSET_DIRS or p.suffix.lower() in BINARY_EXTS
        if not is_asset and not rename_assets:
            continue

        # Fix extension casing, common JPG/JPEG cases
        name = parts[-1]
        stem, ext = os.path.splitext(name)
        ext_lower = ext.lower()

        # Build new filename
        new_stem = kebab(stem)
        new_name = new_stem + ext_lower

        # If nothing changes, skip
        if new_name == name:
            continue

        new_parts = parts[:-1] + [new_name]
        new_rel = "/".join(new_parts)

        # Avoid collisions
        if new_rel in mapping.values():
            # If collision, skip kebab change, only fix extension
            new_name2 = stem + ext_lower
            new_rel2 = "/".join(parts[:-1] + [new_name2])
            if new_rel2 != rel and new_rel2 not in mapping.values():
                mapping[rel] = new_rel2
            continue

        mapping[rel] = new_rel

    return mapping

def apply_renames(build_root: Path, rename_map: dict, dry_run: bool) -> None:
    """
    Apply renames inside build_root based on mapping (old_rel -> new_rel).
    """
    # Do deeper paths first so we do not rename parent directories mid-walk
    items = sorted(rename_map.items(), key=lambda kv: kv[0].count("/"), reverse=True)

    for old_rel, new_rel in items:
        old_p = build_root / old_rel
        new_p = build_root / new_rel
        if not old_p.exists():
            continue
        if dry_run:
            print(f"[DRY] RENAME {old_rel} -> {new_rel}")
            continue
        new_p.parent.mkdir(parents=True, exist_ok=True)
        old_p.rename(new_p)

def update_references_in_text(build_root: Path, rename_map: dict, dry_run: bool) -> None:
    """
    Update href/src/url references across all text files to:
      - root-absolute
      - cleaned internal routes
      - renamed file targets
    """
    # Build replacement dictionary for quick substitution
    # We replace both relative and root-absolute occurrences when possible.
    repl = {}

    for old_rel, new_rel in rename_map.items():
        old_abs = "/" + old_rel
        new_abs = "/" + new_rel
        repl[old_abs] = new_abs
        repl[old_rel] = new_rel

    for p in build_root.rglob("*"):
        if not p.is_file():
            continue
        if not is_text_file(p):
            continue

        txt = read_text(p)
        original = txt

        # Update href/src
        def _hs(m):
            pre, val, end = m.group("attr"), m.group("val"), m.group("end")
            v = val.strip()

            # First, normalise internal links
            v = normalise_internal_links(v)

            # Then, convert to root-absolute for local assets/pages
            v = safe_rel_to_root(build_root, p, v)

            # Then, apply rename mapping if applicable
            if v in repl:
                v = repl[v]

            return pre + v + end

        txt = HREFSRC_RE.sub(_hs, txt)

        # Update CSS url(...)
        def _cu(m):
            pre, val, end = m.group("pre"), m.group("val"), m.group("end")
            v = val.strip()

            if v.startswith(("http:", "https:", "data:")) or v.startswith("${"):
                return pre + v + end

            v = safe_rel_to_root(build_root, p, v)
            if v in repl:
                v = repl[v]
            return pre + v + end

        txt = CSSURL_RE.sub(_cu, txt)

        # Also replace any raw string occurrences that exactly match old path tokens
        # This helps with JSON blocks, OG images, etc.
        for k, v in repl.items():
            txt = txt.replace(k, v)

        if txt != original:
            if dry_run:
                print(f"[DRY] UPDATE {p.relative_to(build_root).as_posix()}")
            else:
                write_text(p, txt)

def ensure_netlify_structure(build_root: Path, dry_run: bool) -> None:
    """
    Ensure required files exist and folder pages are correct.
    """
    required = [
        "index.html",
        "_redirects",
        "_headers",
        "robots.txt",
        "sitemap.xml",
        "llms.txt",
        "schema.json",
        "feed.xml",
        "feed.json",
        "manifest.webmanifest",
        "sw.js",
        "offline.html",
        "about/index.html",
        "events/index.html",
        "team/index.html",
    ]
    missing = [r for r in required if not (build_root / r).exists()]
    if missing:
        print("Missing required files:")
        for m in missing:
            print("  -", m)
        if not dry_run:
            print("Build continues, but deploy will be incomplete until you add them.")

def tidy_redirects(build_root: Path, dry_run: bool) -> None:
    """
    Make sure _redirects includes common legacy routes.
    """
    redirects = build_root / "_redirects"
    if not redirects.exists():
        return
    s = read_text(redirects).splitlines()

    required_lines = [
        "/about.html    /about/    301",
        "/events.html   /events/   301",
        "/team.html     /team/     301",
        "/events-tech-mixer.html    /events/    301",
        "/events/ctc-deliveroo-mixer.html    /events/    301",
    ]

    existing = set(line.strip() for line in s if line.strip() and not line.strip().startswith("#"))
    changed = False
    for line in required_lines:
        if line not in existing:
            s.append(line)
            changed = True

    if changed:
        out = "\n".join(s).rstrip() + "\n"
        if dry_run:
            print("[DRY] UPDATE _redirects (add common redirects)")
        else:
            write_text(redirects, out)

def copy_site(src: Path, dst: Path, dry_run: bool) -> None:
    if dst.exists():
        raise RuntimeError(f"Build output already exists: {dst}")
    if dry_run:
        print(f"[DRY] COPY {src} -> {dst}")
        return
    shutil.copytree(src, dst)

def main():
    ap = argparse.ArgumentParser(description="Organise and normalise a Netlify static site (assets, links, filenames).")
    ap.add_argument("site_root", help="Path to your site folder")
    ap.add_argument("--out", default=None, help="Output build folder. Default is <site_root>__CLEAN")
    ap.add_argument("--dry-run", action="store_true", help="Print actions without writing changes")
    ap.add_argument("--rename-assets", action="store_true", help="Rename assets to kebab-case + lowercase extensions")
    ap.add_argument("--keep-out", action="store_true", help="Do not delete existing out folder if it exists")
    args = ap.parse_args()

    site_root = Path(args.site_root).expanduser().resolve()
    if not site_root.exists():
        print("Site root not found:", site_root)
        sys.exit(1)

    out = Path(args.out).expanduser().resolve() if args.out else Path(str(site_root) + "__CLEAN")
    if out.exists():
        if args.keep_out:
            print("Output folder already exists and --keep-out is set:", out)
            sys.exit(1)
        if args.dry_run:
            print(f"[DRY] Would remove existing output folder: {out}")
        else:
            shutil.rmtree(out)

    print("Site root:", site_root)
    print("Build out:", out)
    print("Dry run:", args.dry_run)
    print("Rename assets:", args.rename_assets)

    # Copy original into build output
    copy_site(site_root, out, args.dry_run)

    # Plan and apply renames
    rename_map = plan_renames(site_root=out, rename_assets=args.rename_assets)
    if rename_map:
        print(f"Planned renames: {len(rename_map)}")
        apply_renames(out, rename_map, args.dry_run)
    else:
        print("No renames planned.")

    # Update references across build output
    update_references_in_text(out, rename_map, args.dry_run)

    # Ensure required structure and redirects
    ensure_netlify_structure(out, args.dry_run)
    tidy_redirects(out, args.dry_run)

    # Final simple audit: list non-root references in html/css
    print("\nFinal audit: non-root local refs (excluding ${...})")
    bad = set()
    href_src = re.compile(r'''(?:href|src)\s*=\s*["']([^"']+)["']''', re.I)
    css_url  = re.compile(r'''url\(\s*["']?([^"')]+)["']?\s*\)''', re.I)

    for p in out.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in {".html", ".css"}:
            continue
        s = read_text(p)
        if p.suffix.lower() == ".html":
            for m in href_src.finditer(s):
                v = m.group(1).strip()
                if v.startswith(SKIP_PREFIXES) or v.startswith("/") or v.startswith("${"):
                    continue
                bad.add(f"{p.relative_to(out).as_posix()}\t{v}")
        else:
            for m in css_url.finditer(s):
                v = m.group(1).strip()
                if v.startswith(("http:", "https:", "data:")) or v.startswith("/"):
                    continue
                bad.add(f"{p.relative_to(out).as_posix()}\t{v}")

    for line in sorted(bad):
        print(line)

    if not bad:
        print("OK. No non-root local refs found (excluding templates).")

    print("\nDone.")

if __name__ == "__main__":
    main()
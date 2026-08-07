"""Deck I/O: backup, selective reads, XML patching, surgical writing, validate.

A .pptx is a ZIP and ~99% of these decks is `ppt/media/`, which PowerPoint stores
*uncompressed* because PNG/JPG are already compressed. So:

  * reading is random-access - pull only the parts a slide actually needs
  * writing streams the original archive into a new one, copying untouched
    entries as raw bytes and substituting only what changed

Measured on the Desktop deck: 31.2s (unpack-all + repack-all) -> 0.5s.

Reading uses ElementTree (parse only - never re-serialised, which would rewrite
namespace prefixes and corrupt the package). Writing is exact string surgery on
the original XML, scoped to a single shape's <a:xfrm>.
"""

import datetime
import glob
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import xml.sax.saxutils as saxutils
import zipfile
import xml.etree.ElementTree as ET

from PIL import Image

from . import config

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
R_EMBED = "{%s}embed" % NS["r"]
R_ID = "{%s}id" % NS["r"]


# --------------------------------------------------------------------------
# backup / locking
# --------------------------------------------------------------------------

def backup(deck_name):
    """Copy the live deck into its Backups folder, then prune to BACKUP_KEEP."""
    spec = config.DECKS[deck_name]
    os.makedirs(spec["backups"], exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    base = os.path.splitext(os.path.basename(spec["pptx"]))[0]
    dest = os.path.join(spec["backups"], "%s_%s.pptx" % (base, stamp))
    shutil.copy2(spec["pptx"], dest)

    existing = sorted(glob.glob(os.path.join(spec["backups"], base + "_*.pptx")),
                      key=os.path.getmtime, reverse=True)
    for stale in existing[config.BACKUP_KEEP:]:
        os.remove(stale)
    return dest


def powerpoint_running():
    """PowerPoint holds an exclusive lock on the live file; writes fail if open."""
    if sys.platform == "win32":
        try:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq POWERPNT.EXE"],
                                 capture_output=True, text=True, timeout=30)
            return "POWERPNT" in out.stdout.upper()
        except Exception:
            return False
    # Cross-platform fallback: Office (Windows and Mac) drops a "~$<name>"
    # sibling lock file next to any document currently open for editing.
    try:
        for spec in config.DECKS.values():
            pptx_path = spec["pptx"]
            lock_path = os.path.join(
                os.path.dirname(pptx_path), "~$" + os.path.basename(pptx_path))
            if os.path.exists(lock_path):
                return True
        return False
    except Exception:
        return False


def fingerprint(path):
    st = os.stat(path)
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


# --------------------------------------------------------------------------
# selective reading
# --------------------------------------------------------------------------

class DeckReader(object):
    """Random-access view of a deck. Only reads the parts it is asked for.

    Normally reads the registered live file for `deck_name`, but `path` can
    point at a staged intermediate file instead - new-slide creation chains
    through one (duplicate the template -> read the staged result -> apply
    further changes on top of it), and none of that should touch the live
    deck until the final write.
    """

    def __init__(self, deck_name, path=None):
        self.deck_name = deck_name
        self.path = path or config.DECKS[deck_name]["pptx"]
        self._zip = zipfile.ZipFile(self.path)
        self._slide_order = None

    def close(self):
        self._zip.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def read(self, part):
        return self._zip.read(part)

    def read_text(self, part):
        return self._zip.read(part).decode("utf-8")

    def has(self, part):
        try:
            self._zip.getinfo(part)
            return True
        except KeyError:
            return False

    def open_image(self, media_name):
        """Decode a media part straight from the archive - never hits disk."""
        part = "ppt/media/" + media_name
        try:
            data = self._zip.read(part)
        except KeyError:
            return None
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            return img
        except Exception:
            return None          # .wdp / .emf and friends

    def media_bytes(self, media_name):
        try:
            return self._zip.read("ppt/media/" + media_name)
        except KeyError:
            return None

    def slide_order(self):
        """Display order -> ppt/slides/slideN.xml. Order is NOT always slideN.xml."""
        if self._slide_order is not None:
            return self._slide_order
        pres = ET.fromstring(self.read("ppt/presentation.xml"))
        rels = ET.fromstring(self.read("ppt/_rels/presentation.xml.rels"))
        target = {rel.get("Id"): rel.get("Target") for rel in rels}
        ordered = []
        for sld in pres.find("p:sldIdLst", NS):
            tgt = target[sld.get(R_ID)].replace("../", "").lstrip("/")
            if not tgt.startswith("ppt/"):
                tgt = "ppt/" + tgt
            ordered.append(tgt)
        self._slide_order = ordered
        return ordered

    def slide_part(self, slide_number):
        order = self.slide_order()
        if not 1 <= int(slide_number) <= len(order):
            return None
        return order[int(slide_number) - 1]

    def parse_slide(self, slide_part):
        """Pictures, red marking boxes and text for one slide - 2 parts read."""
        root = ET.fromstring(self.read(slide_part))
        rels_part = "%s/_rels/%s.rels" % (os.path.dirname(slide_part),
                                          os.path.basename(slide_part))
        media = {}
        if self.has(rels_part):
            for rel in ET.fromstring(self.read(rels_part)):
                tgt = rel.get("Target")
                if "/media/" in tgt or tgt.startswith("../media/"):
                    media[rel.get("Id")] = os.path.basename(tgt)
        return _parse_slide_tree(root, media, slide_part)


def _xfrm(sppr):
    node = sppr.find("a:xfrm", NS) if sppr is not None else None
    if node is None:
        return None
    off, ext = node.find("a:off", NS), node.find("a:ext", NS)
    if off is None or ext is None:
        return None
    return {
        "x": int(off.get("x")), "y": int(off.get("y")),
        "cx": int(ext.get("cx")), "cy": int(ext.get("cy")),
        "rot": int(node.get("rot") or 0),
        "flip": bool(node.get("flipH") or node.get("flipV")),
    }


def _is_red(sppr):
    """A marking box is an unfilled rectangle with a red outline."""
    ln = sppr.find("a:ln", NS)
    if ln is None:
        return False
    for clr in ln.iter("{%s}srgbClr" % NS["a"]):
        val = (clr.get("val") or "").upper()
        if len(val) == 6:
            r, g, b = int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16)
            if r >= 190 and g <= 70 and b <= 70:
                return True
    return False


def _walk(node, group_depth=0):
    for child in node:
        tag = child.tag.split("}")[-1]
        if tag == "grpSp":
            for item in _walk(child, group_depth + 1):
                yield item
        elif tag in ("sp", "pic"):
            yield child, group_depth


def _parse_slide_tree(root, media, slide_part):
    tree = root.find("p:cSld/p:spTree", NS)
    pictures, boxes, texts, text_shapes = [], [], [], []
    for el, depth in _walk(tree):
        tag = el.tag.split("}")[-1]
        cnv = el.find(".//p:cNvPr", NS)
        shape_id = cnv.get("id") if cnv is not None else None
        name = cnv.get("name") if cnv is not None else ""
        if tag == "pic":
            frame = _xfrm(el.find("p:spPr", NS))
            blip = el.find(".//a:blip", NS)
            rid = blip.get(R_EMBED) if blip is not None else None
            src = el.find(".//a:srcRect", NS)
            if frame and rid and rid in media:
                pictures.append({
                    "id": shape_id, "name": name, "rid": rid,
                    "media": media[rid], "frame": frame,
                    "cropped": src is not None and bool(src.attrib),
                    "grouped": depth > 0,
                })
        else:
            sppr = el.find("p:spPr", NS)
            is_marking_box = sppr is not None and _is_red(sppr)
            shape_text = [t.text.strip() for t in el.iter("{%s}t" % NS["a"])
                         if t.text and t.text.strip()]
            if is_marking_box:
                frame = _xfrm(sppr)
                if frame:
                    boxes.append({"id": shape_id, "name": name,
                                  "frame": frame, "grouped": depth > 0})
            elif shape_text:
                # title/instruction/step-label shapes: kept with their frame so
                # layout.py can check a new box or a longer sentence doesn't
                # land on top of one.
                frame = _xfrm(sppr)
                if frame:
                    text_shapes.append({
                        "id": shape_id, "name": name, "frame": frame,
                        "text": " ".join(shape_text), "grouped": depth > 0,
                    })
            texts.extend(shape_text)
    return {"path": slide_part, "pictures": pictures, "boxes": boxes,
           "text": texts, "text_shapes": text_shapes}


def build_index(deck_name, force=False):
    """Inventory every slide's pictures and boxes. Cached per deck fingerprint.

    Only slide XML and rels are read - a couple of MB - never the media that
    makes up the bulk of the file.
    """
    spec = config.DECKS[deck_name]
    cache_file = os.path.join(config.STATE_DIR, "index_%s.json" % deck_name)
    fp = fingerprint(spec["pptx"])

    if not force and os.path.exists(cache_file):
        with open(cache_file, encoding="utf-8") as fh:
            cached = json.load(fh)
        if cached.get("fingerprint") == fp:
            return cached

    with DeckReader(deck_name) as reader:
        slides = {str(n): reader.parse_slide(part)
                  for n, part in enumerate(reader.slide_order(), start=1)}

    index = {"deck": deck_name, "fingerprint": fp, "slides": slides}
    os.makedirs(config.STATE_DIR, exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=1)
    return index


# --------------------------------------------------------------------------
# patching (pure functions on XML text)
# --------------------------------------------------------------------------

def patch_shape_xfrm(xml, shape_id, x, y, cx, cy):
    """Rewrite one shape's <a:off>/<a:ext>, scoped to that shape's own block."""
    pattern = re.compile(r"<p:sp>(?:(?!</p:sp>).)*?"
                         r'<p:cNvPr id="%s"(?:(?!</p:sp>).)*?</p:sp>'
                         % re.escape(str(shape_id)), re.S)
    match = pattern.search(xml)
    if not match:
        raise KeyError("shape id %s not found" % shape_id)
    block = match.group()
    new_block, count = re.subn(
        r'<a:off x="-?\d+" y="-?\d+"/><a:ext cx="\d+" cy="\d+"/>',
        '<a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/>' % (x, y, cx, cy),
        block, count=1)
    if count != 1:
        raise ValueError("no xfrm to patch in shape %s" % shape_id)
    return xml[:match.start()] + new_block + xml[match.end():]


# --------------------------------------------------------------------------
# surgical write
# --------------------------------------------------------------------------

def write_with_changes(deck_name, dest_path, changes, additions=None, source_path=None):
    """Stream a deck into a new archive, substituting `changes` and appending
    `additions`.

    `changes` maps part name -> bytes and every key must already exist in the
    source (a typo'd part name is a real error, not a new file - this is the
    routine screenshot-swap path). `additions` is the opposite: a genuinely new
    part (e.g. a fresh media file for a duplicated slide's own screenshot) that
    must NOT already exist, kept as a separate argument so the two mistakes
    cannot be confused with each other.

    `source_path` overrides the registered live file - used when chaining off
    an intermediate staged file (new-slide creation reads the deck through
    add_slide.py's output before any of *this* module's changes are applied).

    Untouched entries keep their original compression, so the ~146MB of
    already-compressed media is a plain byte copy, not a pointless
    decompress/recompress cycle.
    """
    src = source_path or config.DECKS[deck_name]["pptx"]
    pending = dict(changes)
    additions = dict(additions or {})
    if os.path.exists(dest_path):
        os.remove(dest_path)

    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dest_path, "w") as zout:
        for info in zin.infolist():
            if info.filename in additions:
                raise KeyError("part already exists in the deck, cannot be "
                               "added as new: %s" % info.filename)
            data = pending.pop(info.filename, None)
            if data is None:
                data = zin.read(info.filename)
            out_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            out_info.compress_type = info.compress_type
            out_info.external_attr = info.external_attr
            out_info.internal_attr = info.internal_attr
            out_info.create_system = info.create_system
            zout.writestr(out_info, data)
        for name, data in additions.items():
            zout.writestr(name, data)
    if pending:
        raise KeyError("parts not present in the deck: %s" % ", ".join(sorted(pending)))
    return dest_path


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate(pptx_path, original_path=None):
    """Run the pptx skill's validator, forcing UTF-8.

    Without PYTHONUTF8 the validator reports spurious 'charmap codec' failures on
    almost every part of these decks - confirmed by running it against an
    untouched original and getting identical errors.
    """
    script = _find_validator()
    if not script:
        return True, "validator not found - skipped"
    cmd = [sys.executable, script, pptx_path]
    if original_path:
        cmd += ["--original", original_path]
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()[-3000:]


def _find_validator():
    return _find_pptx_script("office", "validate.py")


def _find_pptx_script(*parts):
    search_roots = [os.environ.get("APPDATA", "")]
    if sys.platform == "darwin":
        search_roots.append(os.path.expanduser("~/Library/Application Support"))
    elif sys.platform.startswith("linux"):
        search_roots.append(os.environ.get(
            "XDG_CONFIG_HOME", os.path.expanduser("~/.config")))
    for root in search_roots:
        if not root:
            continue
        roots = glob.glob(os.path.join(
            root, "Claude", "local-agent-mode-sessions",
            "skills-plugin", "*", "*", "skills", "pptx", "scripts", *parts))
        if roots:
            return roots[0]
    return None


# --------------------------------------------------------------------------
# duplicating a slide (new-tutorial-slide creation)
# --------------------------------------------------------------------------

def duplicate_slide(deck_name, template_slide_path):
    """Duplicate a slide via the pptx skill's add_slide.py, appended at the end.

    That script does the structural bookkeeping a new slide needs - a fresh
    <p:sldId>, [Content_Types].xml entry, presentation.xml.rels relationship -
    correctly and atomically; reimplementing it here would be redundant and
    risky in exactly the way its own docs warn against ("never hand-copy a
    slide file"). It reads the live deck read-only and writes a separate staged
    copy; the live file is not touched until this tool's own validate-then-write
    step at the very end.

    Returns (staged_pptx_path, new_slide_part) - e.g.
    (".../work/Desktop_newslide.pptx", "ppt/slides/slide171.xml").
    """
    script = _find_pptx_script("add_slide.py")
    if not script:
        raise RuntimeError("pptx skill's add_slide.py not found")
    template_file = os.path.basename(template_slide_path)
    live = config.DECKS[deck_name]["pptx"]
    os.makedirs(config.WORK_DIR, exist_ok=True)
    staged = os.path.join(config.WORK_DIR, "%s_newslide.pptx" % deck_name)

    proc = subprocess.run([sys.executable, script, live, template_file, "-o", staged],
                         capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError("add_slide.py failed:\n" + proc.stdout + proc.stderr)
    match = re.search(r"Created (ppt/slides/slide\d+\.xml)", proc.stdout)
    if not match:
        raise RuntimeError("could not find the new slide's name in add_slide.py's "
                           "output:\n" + proc.stdout)
    return staged, match.group(1)


# --------------------------------------------------------------------------
# media: giving a duplicated slide's pictures their own files
# --------------------------------------------------------------------------

def next_media_names(reader, count, ext):
    """Unique ppt/media/ filenames, so a duplicated slide's screenshot can be
    replaced without touching the media file its template still shares it
    with (duplicate_slide copies the slide XML + rels, not the images - a
    fresh slide initially *points at* the template's picture files)."""
    existing = [os.path.basename(n) for n in reader._zip.namelist()
               if n.startswith("ppt/media/")]
    nums = [int(m.group(1)) for n in existing
           if (m := re.match(r"image(\d+)\.", n))]
    start = (max(nums) + 1) if nums else 1
    return ["image%d.%s" % (start + i, ext.lstrip(".")) for i in range(count)]


def repoint_picture_rel(xml_rels, rid, new_media_name):
    """Rewrite one relationship's Target to a new media filename."""
    pattern = re.compile(
        r'(<Relationship\b[^>]*\bId="%s"[^>]*\bTarget=")[^"]*(")' % re.escape(rid))
    new_xml, count = pattern.subn(r"\g<1>../media/%s\g<2>" % new_media_name, xml_rels, count=1)
    if count != 1:
        raise KeyError("relationship %s not found" % rid)
    return new_xml


# --------------------------------------------------------------------------
# text: reading and rewriting paragraph runs, preserving formatting
# --------------------------------------------------------------------------

def _shape_block(xml, shape_id):
    pattern = re.compile(r"<p:sp>(?:(?!</p:sp>).)*?"
                         r'<p:cNvPr id="%s"(?:(?!</p:sp>).)*?</p:sp>'
                         % re.escape(str(shape_id)), re.S)
    match = pattern.search(xml)
    if not match:
        raise KeyError("shape id %s not found" % shape_id)
    return match


def _extract_element(text, tag, search_from=0):
    """Find a complete `<tag ...>...</tag>` or self-closing `<tag .../>` element.

    A non-greedy `.*?(?:/>|</tag>)` regex looks tempting but is wrong whenever
    the element has a self-closing child of its own (`<a:rPr ...><a:latin
    .../></a:rPr>` is exactly this shape) - it stops at the child's `/>`
    instead of the real closing tag, silently truncating the element and
    leaving the XML unbalanced. This walks the actual tag boundary instead.

    Returns (full_element_text, start, end) or None if not found.
    """
    start = text.find("<%s" % tag, search_from)
    if start == -1:
        return None
    open_end = text.index(">", start)
    if text[open_end - 1] == "/":
        return text[start:open_end + 1], start, open_end + 1
    close_tag = "</%s>" % tag
    close = text.index(close_tag, open_end)
    end = close + len(close_tag)
    return text[start:end], start, end


def _t_element(text):
    """<a:t> for `text`, preserving significant leading/trailing whitespace
    (OOXML strips it on load unless xml:space="preserve" is set)."""
    escaped = saxutils.escape(text)
    preserve = ' xml:space="preserve"' if text != text.strip() else ""
    return "<a:t%s>%s</a:t>" % (preserve, escaped)


def read_paragraphs(xml, shape_id):
    """This shape's paragraphs, each as {ppr, runs:[{text, rpr, bold}]}.

    `rpr`/`ppr` are the raw run/paragraph-properties XML, kept verbatim so a
    rewrite can reuse them - color, font, size all live there, and copying the
    XML block rather than describing it is what keeps formatting intact.
    """
    block = _shape_block(xml, shape_id).group()
    txbody = re.search(r"<p:txBody>(.*)</p:txBody>", block, re.S)
    if not txbody:
        return []
    paragraphs = []
    for p_match in re.finditer(r"<a:p>(.*?)</a:p>", txbody.group(1), re.S):
        p_xml = p_match.group(1)
        ppr_found = _extract_element(p_xml, "a:pPr")
        ppr = ppr_found[0] if ppr_found else ""
        runs = []
        for r_match in re.finditer(r"<a:r>(.*?)</a:r>", p_xml, re.S):
            r_xml = r_match.group(1)
            rpr_found = _extract_element(r_xml, "a:rPr")
            rpr = rpr_found[0] if rpr_found else ""
            t_match = re.search(r"<a:t\b[^>]*>(.*?)</a:t>", r_xml, re.S)
            text = html.unescape(t_match.group(1)) if t_match else ""
            runs.append({"text": text, "rpr": rpr, "bold": 'b="1"' in rpr})
        paragraphs.append({"ppr": ppr, "runs": runs})
    return paragraphs


def rewrite_paragraph(xml, shape_id, para_index, new_segments):
    """Replace one paragraph's text, rebuilding runs from `new_segments`
    (list of (text, bold) tuples) using the *existing* bold/regular run
    templates found in that same paragraph - so color/font/size are inherited
    exactly rather than re-specified and risking drift.
    """
    paragraphs = read_paragraphs(xml, shape_id)
    if para_index >= len(paragraphs):
        raise IndexError("shape %s has %d paragraph(s), asked for index %d"
                         % (shape_id, len(paragraphs), para_index))
    target = paragraphs[para_index]
    bold_rpr = next((r["rpr"] for r in target["runs"] if r["bold"]), "")
    reg_rpr = next((r["rpr"] for r in target["runs"] if not r["bold"]), "")
    new_p = build_paragraph_xml(target["ppr"], new_segments, bold_rpr, reg_rpr)

    match = _shape_block(xml, shape_id)
    block = match.group()
    txbody = re.search(r"<p:txBody>(.*)</p:txBody>", block, re.S)
    p_matches = list(re.finditer(r"<a:p>.*?</a:p>", txbody.group(1), re.S))
    span = p_matches[para_index]
    new_body = txbody.group(1)[:span.start()] + new_p + txbody.group(1)[span.end():]
    new_block = block[:txbody.start(1)] + new_body + block[txbody.end(1):]
    return xml[:match.start()] + new_block + xml[match.end():]


def build_paragraph_xml(ppr, new_segments, bold_rpr="", reg_rpr=""):
    """<a:p> XML for `new_segments` ((text, bold) tuples), reusing rpr templates."""
    runs_xml = "".join(
        "<a:r>%s%s</a:r>" % (bold_rpr if bold else reg_rpr, _t_element(text))
        for text, bold in new_segments)
    return "<a:p>%s%s</a:p>" % (ppr, runs_xml)


def insert_paragraph_after(xml, shape_id, after_para_index, new_segments, template_para_index=None):
    """Insert a new paragraph (e.g. a new ToC line) into a text shape, without
    disturbing any existing paragraph - this is an *addition*, unlike
    rewrite_paragraph which replaces one paragraph in place.

    Formatting is copied from an existing paragraph (`template_para_index`,
    default: the one it's inserted after) the same way rewrite_paragraph does -
    reuse the real rPr/pPr XML rather than re-describing it.
    """
    paragraphs = read_paragraphs(xml, shape_id)
    if after_para_index >= len(paragraphs):
        raise IndexError("shape %s has %d paragraph(s), asked to insert after %d"
                         % (shape_id, len(paragraphs), after_para_index))
    template = paragraphs[template_para_index if template_para_index is not None else after_para_index]
    bold_rpr = next((r["rpr"] for r in template["runs"] if r["bold"]), "")
    reg_rpr = next((r["rpr"] for r in template["runs"] if not r["bold"]), "")
    new_p = build_paragraph_xml(template["ppr"], new_segments, bold_rpr, reg_rpr)

    match = _shape_block(xml, shape_id)
    block = match.group()
    txbody = re.search(r"<p:txBody>(.*)</p:txBody>", block, re.S)
    p_matches = list(re.finditer(r"<a:p>.*?</a:p>", txbody.group(1), re.S))
    insert_at = p_matches[after_para_index].end()
    new_body = txbody.group(1)[:insert_at] + new_p + txbody.group(1)[insert_at:]
    new_block = block[:txbody.start(1)] + new_body + block[txbody.end(1):]
    return xml[:match.start()] + new_block + xml[match.end():]


def estimate_text_width_emu(text, font_size_pt, bold=False):
    """Rough rendered width, for a fit check - not a substitute for actually
    looking at the rendered slide (no LibreOffice on this machine), just a
    conservative early warning before that visual check.
    """
    avg_char_width_pt = font_size_pt * (0.56 if bold else 0.52)
    return int(len(text) * avg_char_width_pt * 12700)

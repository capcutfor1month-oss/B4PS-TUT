"""Safe PPT Engine: deterministic, non-destructive primitives for reading,
inspecting, and controlled-mutating .pptx files, built on python-pptx.

Flow: inspect -> safe working copy -> controlled mutation -> save -> reopen
-> validate -> original always preserved.

This module describes deck *structure* only - it assigns no semantic
meaning to any shape (e.g. "this is the instructional red box"). That is
future Documentation Intelligence work, not this layer.

Every public function that touches a real path raises a typed SafeDeckError
subclass on failure rather than letting a bare library exception surface, so
callers (including the CLI) get one clear, actionable reason.
"""

import hashlib
import os
import shutil
import tempfile

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.exc import PackageNotFoundError


class SafeDeckError(Exception):
    """Base for all typed Safe PPT Engine failures."""


class DeckSourceError(SafeDeckError):
    """Input .pptx is missing, empty, or not a valid package."""


class OutputPathError(SafeDeckError):
    """Requested output path is unsafe: same as input, or already exists
    without explicit overwrite."""


class MutationError(SafeDeckError):
    """A controlled mutation could not be applied as requested (bad target,
    unsupported shape, etc.) - raised before anything is written out."""


class ValidationError(SafeDeckError):
    """Generated output failed post-save reopen/content validation."""


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_deck(path):
    """Open `path` read-only into memory as a python-pptx Presentation.

    Never modifies `path`. Never falls back to any other file - a bad path
    always fails, it is never silently substituted. Raises DeckSourceError
    with a clear reason on any failure.
    """
    if not os.path.exists(path):
        raise DeckSourceError("PPTX not found: %s" % path)
    if os.path.getsize(path) == 0:
        raise DeckSourceError("PPTX is empty (0 bytes): %s" % path)
    try:
        return Presentation(path)
    except PackageNotFoundError as exc:
        raise DeckSourceError("Not a valid .pptx package: %s (%s)" % (path, exc))
    except Exception as exc:
        # python-pptx / the underlying zip layer can raise a variety of
        # exception types on a corrupt package; normalize them all to one
        # typed, actionable failure rather than leaking the internal type.
        raise DeckSourceError("Could not open .pptx: %s (%s: %s)"
                               % (path, type(exc).__name__, exc))


# --------------------------------------------------------------------------
# inspection
# --------------------------------------------------------------------------

def _shape_type_name(shape):
    try:
        return str(shape.shape_type)
    except Exception:
        return "UNKNOWN"


def _shape_text(shape):
    if not shape.has_text_frame:
        return None
    return shape.text_frame.text


def _shape_info(shape, z_order):
    return {
        "shape_index": z_order,
        "z_order": z_order,
        "shape_id": shape.shape_id,
        "name": shape.name,
        "shape_type": _shape_type_name(shape),
        "left": shape.left,
        "top": shape.top,
        "width": shape.width,
        "height": shape.height,
        "has_text_frame": shape.has_text_frame,
        "text": _shape_text(shape),
        "has_image": shape.shape_type == MSO_SHAPE_TYPE.PICTURE,
    }


def inspect_deck(path):
    """Deterministic structural inspection of the deck at `path`.

    Describes what exists - slide/shape counts, dimensions, position, text
    presence, image presence, z-order, and stable identifiers where the
    format provides them (shape_id). Assigns no semantic meaning. Repeated
    calls on the same file produce an equal result (no timestamps, temp
    paths, or random IDs).
    """
    prs = load_deck(path)
    slides = []
    for slide_index, slide in enumerate(prs.slides):
        shapes = [_shape_info(shape, z) for z, shape in enumerate(slide.shapes)]
        slides.append({
            "slide_index": slide_index,
            "shape_count": len(shapes),
            "shapes": shapes,
        })
    return {
        "path": os.path.abspath(path),
        "slide_count": len(slides),
        "slide_width": prs.slide_width,
        "slide_height": prs.slide_height,
        "slides": slides,
    }


# --------------------------------------------------------------------------
# safe working copy / output-path safety
# --------------------------------------------------------------------------

def _assert_safe_output_path(input_path, output_path, overwrite):
    in_abs = os.path.abspath(input_path)
    out_abs = os.path.abspath(output_path)
    if in_abs == out_abs:
        raise OutputPathError(
            "Output path must not resolve to the input path: %s" % output_path)
    if os.path.exists(out_abs) and not overwrite:
        raise OutputPathError(
            "Output path already exists (pass overwrite=True to replace it "
            "deliberately): %s" % output_path)


def create_working_copy(path):
    """A private staging copy in a fresh temp location. All mutation work
    happens here - never on the original, and never directly at the
    caller's requested output path - so a failed or partial mutation can
    never corrupt either. Caller is responsible for removing the returned
    path when done.
    """
    load_deck(path)  # validate before copying anything
    fd, staged = tempfile.mkstemp(prefix="b4ps_engine_", suffix=".pptx")
    os.close(fd)
    shutil.copy2(path, staged)
    return staged


def _publish_atomically(staged_path, output_path):
    """Place a validated, already-saved staged file at `output_path`
    without ever leaving a partially-written file there: copy into a temp
    file in the same directory (same filesystem, so the final rename is
    atomic), then `os.replace` it into place. If the copy is interrupted,
    only the temp file is left behind - `output_path` itself is either
    absent/unchanged or the complete new file, never a partial one.
    """
    out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp_out = tempfile.mkstemp(prefix=".b4ps_publish_", suffix=".pptx", dir=out_dir)
    os.close(fd)
    try:
        shutil.copy2(staged_path, tmp_out)
        os.replace(tmp_out, output_path)
    except Exception:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
        raise


# --------------------------------------------------------------------------
# controlled mutation
# --------------------------------------------------------------------------

def _resolve_shape(prs, slide_index, shape_index):
    if not 0 <= slide_index < len(prs.slides):
        raise MutationError("slide_index %d out of range (deck has %d slide(s))"
                             % (slide_index, len(prs.slides)))
    slide = prs.slides[slide_index]
    shapes = list(slide.shapes)
    if not 0 <= shape_index < len(shapes):
        raise MutationError("shape_index %d out of range (slide %d has %d shape(s))"
                             % (shape_index, slide_index, len(shapes)))
    return shapes[shape_index]


def validate_mutated_output(output_path, expected_slide_count, slide_index,
                             shape_index, expected_text):
    """Reopen `output_path` from scratch and confirm: it is still a valid
    PPTX package, slide count is unchanged, and the targeted shape's text
    now matches what was requested. Returns (ok, detail)."""
    try:
        prs = load_deck(output_path)
    except DeckSourceError as exc:
        return False, "generated output failed to reopen: %s" % exc
    if len(prs.slides) != expected_slide_count:
        return False, ("slide count changed: expected %d, got %d"
                        % (expected_slide_count, len(prs.slides)))
    try:
        shape = _resolve_shape(prs, slide_index, shape_index)
    except MutationError as exc:
        return False, "targeted shape missing after save: %s" % exc
    if not shape.has_text_frame or shape.text_frame.text != expected_text:
        return False, "mutation did not persist as expected"
    return True, "ok"


def set_shape_text(input_path, output_path, slide_index, shape_index, new_text,
                    overwrite=False):
    """Controlled mutation primitive: set one explicitly targeted shape's
    text-frame text. Targeting is deterministic by (slide_index,
    shape_index) only - no fuzzy or semantic matching.

    Never mutates `input_path`. Stages the change on a private working
    copy, validates the saved result by reopening it, and only then places
    it at `output_path`. On any failure, nothing is written to
    `output_path` and `input_path` is left untouched.
    """
    _assert_safe_output_path(input_path, output_path, overwrite)
    before_hash = file_sha256(input_path)

    staged = create_working_copy(input_path)
    try:
        prs = Presentation(staged)
        shape = _resolve_shape(prs, slide_index, shape_index)
        if not shape.has_text_frame:
            raise MutationError(
                "shape %d on slide %d has no text frame - cannot set text"
                % (shape_index, slide_index))
        shape.text_frame.text = new_text
        expected_slide_count = len(prs.slides)
        prs.save(staged)

        ok, detail = validate_mutated_output(
            staged, expected_slide_count, slide_index, shape_index, new_text)
        if not ok:
            raise ValidationError(detail)

        _publish_atomically(staged, output_path)
    finally:
        if os.path.exists(staged):
            os.remove(staged)

    if file_sha256(input_path) != before_hash:
        # Defensive invariant check - this should be structurally
        # impossible given the staged-copy design above, but source
        # preservation is the core safety guarantee, so it is verified
        # explicitly rather than only assumed.
        raise SafeDeckError(
            "input file changed during mutation - safety invariant violated: %s"
            % input_path)

    return output_path


# --------------------------------------------------------------------------
# geometry mutation (move / resize / atomic left+top+width+height)
# --------------------------------------------------------------------------
#
# Coordinates and dimensions are all in EMU (English Metric Units) - the
# native integer unit python-pptx and the underlying OOXML format use
# throughout (914400 EMU = 1 inch). No other unit is accepted or converted
# here; callers convert if they have inches/points/pixels.

def _validate_coordinate(value, name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise MutationError("%s must be an integer EMU value, got %r" % (name, value))
    if value < 0:
        raise MutationError("%s must be >= 0 EMU, got %d" % (name, value))


def _validate_dimension(value, name):
    if not isinstance(value, int) or isinstance(value, bool):
        raise MutationError("%s must be an integer EMU value, got %r" % (name, value))
    if value <= 0:
        raise MutationError("%s must be > 0 EMU, got %d" % (name, value))


def _apply_geometry(shape, geometry):
    """Apply an already-validated {attr: value} geometry dict to `shape`.
    Only the given attributes are touched - e.g. a move (left/top only)
    never assigns width/height, so it cannot change them even indirectly."""
    for key, value in geometry.items():
        setattr(shape, key, value)


def validate_geometry_output(output_path, expected_slide_count, slide_index,
                              shape_index, expected_geometry):
    """Reopen `output_path` and confirm slide count is unchanged, the
    targeted shape is still resolvable, and every geometry attribute that
    was requested now matches exactly. Returns (ok, detail)."""
    try:
        prs = load_deck(output_path)
    except DeckSourceError as exc:
        return False, "generated output failed to reopen: %s" % exc
    if len(prs.slides) != expected_slide_count:
        return False, ("slide count changed: expected %d, got %d"
                        % (expected_slide_count, len(prs.slides)))
    try:
        shape = _resolve_shape(prs, slide_index, shape_index)
    except MutationError as exc:
        return False, "targeted shape missing after save: %s" % exc
    for key, expected_value in expected_geometry.items():
        actual = getattr(shape, key)
        if actual != expected_value:
            return False, ("%s mismatch after save: expected %r, got %r"
                            % (key, expected_value, actual))
    return True, "ok"


def _run_geometry_mutation(input_path, output_path, slide_index, shape_index,
                            geometry, overwrite):
    """Shared staged-copy -> mutate -> save -> validate -> atomic-publish
    flow for every geometry primitive below. `geometry` values must already
    be validated by the caller before this runs, so nothing here can raise
    a validation error after the working copy has been staged - only a
    genuinely unexpected condition (bad index, save failure) can.
    """
    _assert_safe_output_path(input_path, output_path, overwrite)
    before_hash = file_sha256(input_path)

    staged = create_working_copy(input_path)
    try:
        prs = Presentation(staged)
        shape = _resolve_shape(prs, slide_index, shape_index)
        _apply_geometry(shape, geometry)
        expected_slide_count = len(prs.slides)
        expected_geometry = {
            "left": shape.left, "top": shape.top,
            "width": shape.width, "height": shape.height,
        }
        prs.save(staged)

        ok, detail = validate_geometry_output(
            staged, expected_slide_count, slide_index, shape_index, expected_geometry)
        if not ok:
            raise ValidationError(detail)

        _publish_atomically(staged, output_path)
    finally:
        if os.path.exists(staged):
            os.remove(staged)

    if file_sha256(input_path) != before_hash:
        raise SafeDeckError(
            "input file changed during mutation - safety invariant violated: %s"
            % input_path)

    return output_path


def move_shape(input_path, output_path, slide_index, shape_index, left, top,
               overwrite=False):
    """Controlled mutation: set one explicitly targeted shape's position
    (left, top), in EMU. Width and height are never touched - verified by
    the post-save validation, which re-checks left/top only, leaving
    width/height to whatever the file already had.

    Never mutates `input_path`. On any failure (bad index, invalid
    coordinate, save/validation failure) nothing is written to
    `output_path`.
    """
    _validate_coordinate(left, "left")
    _validate_coordinate(top, "top")
    return _run_geometry_mutation(input_path, output_path, slide_index, shape_index,
                                  {"left": left, "top": top}, overwrite)


def resize_shape(input_path, output_path, slide_index, shape_index, width, height,
                 overwrite=False):
    """Controlled mutation: set one explicitly targeted shape's size
    (width, height), in EMU. Setting width/height on a python-pptx shape
    does not itself move left/top - position is left untouched, and a
    dedicated regression test confirms that behavior explicitly rather
    than assuming it.

    Never mutates `input_path`. On any failure nothing is written to
    `output_path`.
    """
    _validate_dimension(width, "width")
    _validate_dimension(height, "height")
    return _run_geometry_mutation(input_path, output_path, slide_index, shape_index,
                                  {"width": width, "height": height}, overwrite)


def set_shape_geometry(input_path, output_path, slide_index, shape_index,
                       left, top, width, height, overwrite=False):
    """Atomic geometry update: left, top, width, and height are all set
    together as one operation - the primitive future red-box relocation
    will use. All four values are validated *before* the working copy is
    even staged, so an invalid value fails cleanly with nothing written
    anywhere and no shape attribute touched, even in memory. Either the
    complete requested geometry is applied, saved, and verified, or the
    whole operation raises and `output_path` is left untouched.
    """
    _validate_coordinate(left, "left")
    _validate_coordinate(top, "top")
    _validate_dimension(width, "width")
    _validate_dimension(height, "height")
    return _run_geometry_mutation(
        input_path, output_path, slide_index, shape_index,
        {"left": left, "top": top, "width": width, "height": height}, overwrite)


# --------------------------------------------------------------------------
# picture replacement
# --------------------------------------------------------------------------

def _validate_image_file(path):
    if not os.path.exists(path):
        raise MutationError("replacement image not found: %s" % path)
    if os.path.getsize(path) == 0:
        raise MutationError("replacement image is empty (0 bytes): %s" % path)
    try:
        with Image.open(path) as img:
            img.verify()
    except Exception as exc:
        raise MutationError(
            "replacement image is not a valid/readable image: %s (%s: %s)"
            % (path, type(exc).__name__, exc))


def validate_picture_replacement(output_path, expected_slide_count, slide_index,
                                  shape_index, expected_geometry, expected_image_bytes):
    """Reopen `output_path` and confirm: slide count unchanged, the target
    shape is still resolvable and is still a picture, its frame geometry
    exactly matches what was expected, and its image payload now matches
    the replacement image's bytes exactly. Returns (ok, detail)."""
    try:
        prs = load_deck(output_path)
    except DeckSourceError as exc:
        return False, "generated output failed to reopen: %s" % exc
    if len(prs.slides) != expected_slide_count:
        return False, ("slide count changed: expected %d, got %d"
                        % (expected_slide_count, len(prs.slides)))
    try:
        shape = _resolve_shape(prs, slide_index, shape_index)
    except MutationError as exc:
        return False, "targeted shape missing after save: %s" % exc
    if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
        return False, "targeted shape is no longer a picture after save"
    for key, expected_value in expected_geometry.items():
        actual = getattr(shape, key)
        if actual != expected_value:
            return False, ("%s mismatch after save: expected %r, got %r"
                            % (key, expected_value, actual))
    if shape.image.blob != expected_image_bytes:
        return False, "image payload does not match the replacement image after save"
    return True, "ok"


def replace_picture(input_path, output_path, slide_index, shape_index, image_path,
                    overwrite=False):
    """Controlled mutation: replace a picture shape's embedded image.

    Default (and currently only) geometry behavior: the shape's existing
    left/top/width/height frame is preserved exactly, regardless of the
    replacement image's own pixel dimensions or aspect ratio - the new
    image is placed into the unchanged frame exactly as PowerPoint's own
    blipFill model renders it. This primitive does not compute, apply, or
    guess any new cropping; it does not touch `a:srcRect` at all, so any
    crop already present on the shape is left exactly as-is (preserved by
    construction, not by special-casing it).

    Only the picture's image relationship (`p:blipFill/a:blip/@r:embed`) is
    repointed at a newly-added image part - this is the smallest reliable
    OOXML-level operation for this, isolated entirely behind this function;
    no other code in this module or its callers touches raw OOXML for
    image handling.

    Rejects a target shape that is not a picture, and a replacement image
    that is missing, empty, or unreadable - before anything is staged.
    Never mutates `input_path`. On any failure nothing is written to
    `output_path`.
    """
    _validate_image_file(image_path)
    _assert_safe_output_path(input_path, output_path, overwrite)
    before_hash = file_sha256(input_path)
    with open(image_path, "rb") as fh:
        new_image_bytes = fh.read()

    staged = create_working_copy(input_path)
    try:
        prs = Presentation(staged)
        shape = _resolve_shape(prs, slide_index, shape_index)
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
            raise MutationError(
                "shape %d on slide %d is not a picture (shape_type=%s) - "
                "cannot replace its image"
                % (shape_index, slide_index, _shape_type_name(shape)))

        expected_geometry = {
            "left": shape.left, "top": shape.top,
            "width": shape.width, "height": shape.height,
        }
        slide_part = shape.part
        _new_image_part, new_rId = slide_part.get_or_add_image_part(image_path)
        shape._pic.blipFill.blip.rEmbed = new_rId

        expected_slide_count = len(prs.slides)
        prs.save(staged)

        ok, detail = validate_picture_replacement(
            staged, expected_slide_count, slide_index, shape_index,
            expected_geometry, new_image_bytes)
        if not ok:
            raise ValidationError(detail)

        _publish_atomically(staged, output_path)
    finally:
        if os.path.exists(staged):
            os.remove(staged)

    if file_sha256(input_path) != before_hash:
        raise SafeDeckError(
            "input file changed during mutation - safety invariant violated: %s"
            % input_path)

    return output_path

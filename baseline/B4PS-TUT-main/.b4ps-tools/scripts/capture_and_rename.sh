#!/bin/bash
# B4PS dedicated screenshot capture: prompts for deck + slide number right after
# capture, saves straight into the correct Source/<Desktop|Mobile>/Screenshots/
# folder as Slide_N.png (or Slide_N_b.png etc). Does not touch normal
# Cmd+Shift+4/5 screenshots or their default save location.

set -euo pipefail

# This script lives at <project root>/.b4ps-tools/scripts/, so the project
# root is two levels up from here - resolved at run time instead of a
# hardcoded per-machine path, so the script works from any checkout location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TMP_FILE="${TMPDIR:-/tmp}/b4ps_capture_$$.png"

cleanup() { rm -f "$TMP_FILE"; }
trap cleanup EXIT

# 1. Interactive area capture (same underlying tool as Cmd+Shift+4).
#    -i = interactive selection, user drags a region or clicks a window.
screencapture -i "$TMP_FILE"

# If the user hit Escape / cancelled the selection, no file is written.
if [ ! -s "$TMP_FILE" ]; then
  exit 0
fi

# 2. Deck: this hotkey captures the Mac's own screen, so it's always the
#    Desktop deck's screenshots (Mobile screenshots come from a phone/
#    simulator, not this flow) — no prompt needed.
DECK="Desktop"

# 3. Ask for slide number (and optional suffix). Note: this dialog can force a
#    Space switch away from a true-fullscreen app (macOS can't render a modal
#    dialog inside an exclusive fullscreen Space) — restored by explicit user
#    request despite that tradeoff. Avoid native fullscreen (use a
#    maximized/zoomed window instead) to sidestep it entirely.
SLIDE_INPUT=$(osascript -e '
  set theInput to text returned of (display dialog "Slide number (add a letter for a 2nd/3rd picture on the same slide, e.g. \"148\" or \"148b\"):" default answer "" with title "B4PS Screenshot — Desktop")
  return theInput
') || exit 0

SLIDE_INPUT=$(echo "$SLIDE_INPUT" | tr -d '[:space:]')
if [ -z "$SLIDE_INPUT" ]; then
  osascript -e 'display notification "No slide number entered — screenshot discarded." with title "B4PS Screenshot"'
  exit 0
fi

# Split leading digits (slide number) from an optional trailing letter suffix.
NUM=$(echo "$SLIDE_INPUT" | grep -oE '^[0-9]+' || true)
SUFFIX=$(echo "$SLIDE_INPUT" | grep -oE '[a-zA-Z]+$' || true)

if [ -z "$NUM" ]; then
  osascript -e 'display alert "Could not find a slide number in that input — screenshot discarded." as critical'
  exit 1
fi

if [ -n "$SUFFIX" ]; then
  FILENAME="Slide_${NUM}_${SUFFIX}.png"
else
  FILENAME="Slide_${NUM}.png"
fi

DEST_DIR="${PROJECT_ROOT}/Source/${DECK}/Screenshots"
mkdir -p "$DEST_DIR"
DEST_PATH="${DEST_DIR}/${FILENAME}"

# 4. Warn before overwriting an existing queued screenshot.
if [ -f "$DEST_PATH" ]; then
  OVERWRITE=$(osascript -e '
    set theChoice to button returned of (display dialog "'"$FILENAME"'" & " already exists in the '"$DECK"' Screenshots folder. Overwrite it?" buttons {"Cancel", "Overwrite"} default button "Cancel" with title "B4PS Screenshot" with icon caution)
    return theChoice
  ') || exit 0
  if [ "$OVERWRITE" != "Overwrite" ]; then
    osascript -e 'display notification "Cancelled — existing file kept." with title "B4PS Screenshot"'
    exit 0
  fi
fi

mv "$TMP_FILE" "$DEST_PATH"

osascript -e 'display notification "Saved as '"$FILENAME"'" with title "B4PS Screenshot — '"$DECK"'"'

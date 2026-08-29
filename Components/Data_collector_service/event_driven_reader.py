import re
import time
import uiautomation as auto
from helper import execute_save2db_and_delete
from dotenv import load_dotenv

load_dotenv()

OBJ_REPLACEMENT_RUN = re.compile(r'(\ufffc\s*){2,}')  # icon-only buttons, no label
SNAPSHOT_TEXT_TYPES = {'TextControl', 'GroupControl', 'ListItemControl', 'DocumentControl', 'HyperlinkControl'}

NOISE_FOCUS_TYPES = {
    'ButtonControl', 'MenuControl', 'MenuItemControl', 'ToolBarControl',
    'TitleBarControl', 'ScrollBarControl', 'TabItemControl', 'SeparatorControl',
    'ThumbControl', 'ProgressBarControl', 'StatusBarControl', 'TrayControl',
}
IGNORE_CLASSNAMES = {'Shell_TrayWnd'}

MAX_LIM = 12
MAX_ANCESTOR_HOPS = 20
MIN_SNAPSHOT_ENTRIES = 6
SAVE_RETRY_COOLDOWN = 30
counter = 0
_last_save_attempt = 0


def save(text):
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")


def clean_text(text):
    if not text:
        return text
    return OBJ_REPLACEMENT_RUN.sub('', text).strip()


def get_control_text(control):
    texts = []
    value = None
    try:
        vp = control.GetValuePattern()
        if vp and vp.Value:
            value = vp.Value
            texts.append(value)
    except Exception:
        pass
    try:
        tp = control.GetTextPattern()
        if tp:
            content = tp.DocumentRange.GetText(-1)
            if content and content != value:  # TextPattern often mirrors ValuePattern
                texts.append(content)
    except Exception:
        pass
    return [t for t in (clean_text(t) for t in texts) if t]


def get_identity(control):
    try:
        runtime_id = control.GetRuntimeId()
    except Exception:
        runtime_id = None
    try:
        name = control.Name
    except Exception:
        name = None
    try:
        control_type = control.ControlTypeName
    except Exception:
        control_type = None
    try:
        class_name = control.ClassName
    except Exception:
        class_name = None
    return (runtime_id, name, control_type, class_name)


def get_top_level_window(control):
    node = control
    seen = 0
    while node and seen < 50:
        try:
            if node.ControlTypeName == 'WindowControl':
                return node
            parent = node.GetParentControl()
        except Exception:
            parent = None
        if not parent:
            return node
        node = parent
        seen += 1
    return node


def collect_text_entries(root, focused_id, win_center_x, max_lines, max_depth, max_fragments=400):
    """Walk the tree and grab raw text fragments with their screen position.
    We do NOT treat each fragment as its own line: syntax-highlighted code
    editors and rich-text panes (Zed, Claude.ai responses) render every
    token/run as a separate leaf element, so a naive one-entry-per-control
    walk produces useless single-word fragments in tree order rather than
    reading order. Instead we collect raw fragments here and merge them into
    real lines afterward, using their row position."""
    fragments = []
    try:
        walker = auto.WalkControl(root, includeTop=False, maxDepth=max_depth)
    except Exception:
        return []


    try:
        for ctrl, depth in walker:
            if len(fragments) >= max_fragments:
                break
            try:
                if focused_id and ctrl.GetRuntimeId() == focused_id:
                    continue
                if ctrl.ControlTypeName not in SNAPSHOT_TEXT_TYPES:
                    continue
            except Exception:
                continue
            texts = get_control_text(ctrl)
            candidate = clean_text(ctrl.Name or (texts[0] if texts else ''))
            if not candidate:
                continue
            try:
                cr = ctrl.BoundingRectangle
            except Exception:
                cr = None
            if not cr:
                continue
            width = cr.right - cr.left
            height = cr.bottom - cr.top
            if width <= 0 or height <= 0:
                continue
            fragments.append({'text': candidate, 'top': cr.top, 'left': cr.left, 'right': cr.right})
    except Exception:
        pass

    return merge_fragments_into_lines(fragments, win_center_x, max_lines)


def merge_fragments_into_lines(fragments, win_center_x, max_lines, row_tolerance=6):
    """Reconstruct real lines from scattered token/run fragments by grouping
    them into rows (by vertical position) and joining left-to-right within
    each row — turning ['import', 're'] into 'import re', and a dozen
    bold/code-span runs of one sentence back into that one sentence."""
    if not fragments:
        return []

    fragments = sorted(fragments, key=lambda f: (f['top'], f['left']))
    rows = [[fragments[0]]]
    for frag in fragments[1:]:
        if abs(frag['top'] - rows[-1][-1]['top']) <= row_tolerance:
            rows[-1].append(frag)
        else:
            rows.append([frag])

    entries, seen_lines = [], set()
    for row in rows:
        row.sort(key=lambda f: f['left'])
        pieces = []
        for f in row:
            t = f['text']
            if pieces and t in pieces[-1]:
                continue
            if pieces and pieces[-1] in t:
                pieces[-1] = t
                continue
            pieces.append(t)
        line = re.sub(r'\s+', ' ', ' '.join(pieces)).strip()
        if not line or line in seen_lines:
            continue
        seen_lines.add(line)
        side = ''
        if win_center_x is not None:
            avg_center = sum((f['left'] + f['right']) / 2 for f in row) / len(row)
            side = 'right' if avg_center > win_center_x else 'left'
        entries.append({'text': line, 'side': side})
        if len(entries) >= max_lines:
            break
    return entries


def get_window_snapshot(focused_control, max_lines=60, max_depth=40):
    """Climb outward from the focused control (not the whole top-level
    window) one ancestor at a time, stopping as soon as a container
    yields real text. This lands on the panel actually holding the
    focused field — e.g. the open conversation thread — instead of a
    sibling panel like a sidebar chat list, which would otherwise get
    walked first and exhaust max_lines before the real content."""
    try:
        focused_id = focused_control.GetRuntimeId()
    except Exception:
        focused_id = None

    window = get_top_level_window(focused_control)
    win_center_x = None
    if window:
        try:
            r = window.BoundingRectangle
            win_center_x = (r.left + r.right) / 2 if r else None
        except Exception:
            pass

    current = focused_control
    best = []
    for _ in range(MAX_ANCESTOR_HOPS):
        try:
            parent = current.GetParentControl()
        except Exception:
            parent = None
        if not parent:
            break
        current = parent

        try:
            entries = collect_text_entries(current, focused_id, win_center_x, max_lines, max_depth)
        except Exception:

            break

        if len(entries) > len(best):
            best = entries
        if len(entries) >= MIN_SNAPSHOT_ENTRIES:
            return entries

        try:
            is_window = current.ControlTypeName == 'WindowControl'
        except Exception:
            is_window = True  # stale — stop climbing
        if is_window:
            break
    return best


def is_meaningful_focus(control):
    """Denylist-based: only reject known UI-chrome types. Everything else
    is treated as potentially worth capturing, since we can't predict every
    custom control type an app might use for its input/content areas."""
    try:
        control_type = control.ControlTypeName
        class_name = control.ClassName
    except Exception:
        return False
    if control_type in NOISE_FOCUS_TYPES:
        return False
    if class_name in IGNORE_CLASSNAMES:
        return False
    return True


def describe(control):
    global counter, _last_save_attempt

    try:
        if not is_meaningful_focus(control):
            return

        texts = get_control_text(control)
        label = clean_text(control.Name) or (texts[0] if texts else None)


        if label:
            save(f"You're typing/reading in: {label}")
        else:
            save("You're focused on a text field (no label)")

        if texts and label not in texts:
            save(f"It currently contains: {texts[0]}")

        counter += 1
        print(counter)
        snapshot = get_window_snapshot(control)
        if snapshot:
            save("Text visible around it:")
            for e in snapshot:
                where = f"({e['side']}) " if e['side'] else ''
                save(f"  - {where}{e['text']}")

        save('---')
    except Exception:

        return

    if counter > MAX_LIM:
        now = time.time()
        if now - _last_save_attempt < SAVE_RETRY_COOLDOWN:
            return  # tried recently and it failed — don't hammer the API every focus change
        _last_save_attempt = now
        try:
            print("==========SAVING TO DB")
            success = execute_save2db_and_delete()
            if success:
                counter = 0
        except Exception as e:

            print(f" save2db failed, will retry in {SAVE_RETRY_COOLDOWN}s: {e}")


def watch(poll_seconds=0.3):
    last_identity = None
    while True:
        try:
            control = auto.GetFocusedControl()
        except Exception:
            control = None
        if control:
            identity = get_identity(control)
            if identity != last_identity:
                describe(control)
                last_identity = identity
        time.sleep(poll_seconds)


if __name__ == '__main__':
    try:
        watch()
    except KeyboardInterrupt:
        pass

# save locally for about 25 context switches (and if user uses goldfish)
# it uses this context and the context at the time user presses on screen, then answers

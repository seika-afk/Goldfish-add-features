import time
import uiautomation as auto

def get_current_context():
    """Return a dict describing what's currently on screen."""
    window = auto.GetForegroundControl()
    if not window:
        return None

    texts = []
    def collect(control, depth=0, max_depth=6):
        if depth > max_depth:
            return
        if control.Name:
            texts.append(control.Name)
        for child in control.GetChildren():
            collect(child, depth + 1, max_depth)

    collect(window)

    return {
        'app_name': window.Name,
        'class_name': window.ClassName,
        'visible_text': texts,
    }

def watch(poll_seconds=2):
    last_app = None
    while True:
        ctx = get_current_context()
        if ctx and ctx['app_name'] != last_app:
            print(f"\n--- Switched to: {ctx['app_name']} ---")
            print(ctx['visible_text'][:10])  # first 10 text fragments
            last_app = ctx['app_name']
        time.sleep(poll_seconds)

if __name__ == '__main__':
    watch()

import keyboard
import uiautomation as auto
from Data_collector_service.event_drive_reader import get_control_text, clean_text
import asyncio
import json

from agent import call_agent

def get_active_window_content(control, texts=None):
    """Recursively walk every child of the window and collect text."""
    if texts is None:
        texts = []

    control_texts = get_control_text(control)
    name = control.Name
    automation_id = getattr(control, "AutomationId", "")

    if control_texts or name or automation_id:
        texts.append({
            "name": name,
            "class_name": control.ClassName,
            "control_type": control.ControlTypeName,
            "automation_id": automation_id,
            "content": control_texts,
        })

    try:
        for child in control.GetChildren():
            get_active_window_content(child, texts)
    except Exception:
        pass

    return texts

def get_current_context():
    focused = auto.GetFocusedControl()
    if not focused:
        return None

    try:
        window = focused.GetTopLevelControl()
    except Exception:
        window = focused

    window_content = get_active_window_content(window)

    context = {
        "focused_name": focused.Name,
        "focused_class_name": focused.ClassName,
        "focused_control_type": focused.ControlTypeName,
        "focused_automation_id": getattr(focused, "AutomationId", ""),
        "focused_content": get_control_text(focused),
        "window_content": window_content,
        "control_ref": focused,  # keep a live reference so we can type into it later
    }
    return context

def ctx_to_string(ctx):
    serializable = {k: v for k, v in ctx.items() if k != "control_ref"}
    return json.dumps(serializable, ensure_ascii=False, indent=2)

def type_into_control(control, text):
    try:
        control.SendKeys(text, interval=0.01)
    except Exception as e:
        print(f"Failed to send keys: {e}")

async def on_hotkey():
    ctx = get_current_context()
    if not ctx:
        print("No focused control found.")
        return

    print("Captured focused control:", ctx["focused_name"], ctx["focused_control_type"])
    print(f"Collected {len(ctx['window_content'])} elements from window")

    answer = await call_agent(ctx_to_string(ctx))

    type_into_control(ctx["control_ref"], answer)

def on_hotkey_sync():
    asyncio.run(on_hotkey())

keyboard.add_hotkey('right alt', on_hotkey_sync)

try:
    keyboard.wait()
except KeyboardInterrupt:
    print("\nStopped listening.")

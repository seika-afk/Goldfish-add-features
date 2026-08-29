import keyboard
import uiautomation as auto
import logging
import asyncio

from agent import call_agent
import json


print("======== KEYREADER STARTED")


def clean_text(value):
    """Normalize text read from a Windows UI Automation control."""
    return " ".join(str(value or "").split())


def get_control_text(control):
    """Return the best available visible/value text for a UI Automation control."""
    values = [getattr(control, "Name", "")]

    try:
        values.append(control.GetValuePattern().Value)
    except Exception:
        pass

    try:
        values.append(control.GetLegacyIAccessiblePattern().Value)
    except Exception:
        pass

    return clean_text(" ".join(filter(None, values)))

def ctx_to_string(ctx):
    serializable = {k: v for k, v in ctx.items() if k != "control_ref"}
    serialized = json.dumps(serializable, ensure_ascii=False, indent=2)
    return serialized
def get_current_context():
    control = auto.GetFocusedControl()
    if not control:
        return None

    texts = get_control_text(control)
    context = {
        "name": control.Name,
        "class_name": control.ClassName,
        "control_type": control.ControlTypeName,
        "automation_id": getattr(control, "AutomationId", ""),
        "content": texts,
        "control_ref": control,  # keep a live reference so we can type into it later
    }
    return context

def type_into_control(control, text):
    """Type text into a control at the current cursor position."""
    print(f"[key_reader] Sending generated text (characters={len(text)})")
    try:
        control.SendKeys(text, interval=0.01)
        print("[key_reader] Generated text sent successfully")
    except Exception as e:
        print(f"Failed to send keys: {e}")

async def on_hotkey():
    print("======Right Alt hotkey triggered")
    ctx = get_current_context()
    if not ctx:
        print("No focused control found.")
        return

    print("Captured context:", ctx["name"], ctx["control_type"])
    print("Content:", ctx["content"])

    print(" Requesting agent completion")
    answer =await call_agent(ctx_to_string(ctx))
    print(f"Agent completion received (characters={len(answer)})")

    type_into_control(ctx["control_ref"], answer)


def on_hotkey_sync():
    """Run the async handler in keyboard's worker thread.

    The keyboard package calls this function from its own thread. Windows UI
    Automation is COM-based, so that thread needs its own initializer before
    calling ``GetFocusedControl``.
    """
    try:
        with auto.UIAutomationInitializerInThread():
            asyncio.run(on_hotkey())
    except Exception:
        print("[key_reader] Right Alt hotkey handler failed; see the traceback above.")

print("[key_reader] Registering Right Alt hotkey")
# directly so the handler starts as soon as the key is pressed.
keyboard.on_press_key('right alt', lambda _event: on_hotkey_sync())

try:
    print("[key_reader] Waiting for keyboard events")
    keyboard.wait()
except KeyboardInterrupt:
    print("\nStopped listening.")

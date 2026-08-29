import keyboard
import uiautomation as auto
from Data_collector_service.event_drive_reader import control_text ,clean_text
import asyncio

from agent import call_agent
import json

def ctx_to_string(ctx):
    serializable = {k: v for k, v in ctx.items() if k != "control_ref"}
    return json.dumps(serializable, ensure_ascii=False, indent=2)
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
    try:
        control.SendKeys(text, interval=0.01)
    except Exception as e:
        print(f"Failed to send keys: {e}")

async def on_hotkey():
    ctx = get_current_context()
    if not ctx:
        print("No focused control found.")
        return

    print("Captured context:", ctx["name"], ctx["control_type"])
    print("Content:", ctx["content"])

    answer =await call_agent(ctx_to_string(ctx))

    type_into_control(ctx["control_ref"], answer)

keyboard.add_hotkey('right alt', on_hotkey)

try:
    keyboard.wait()
except KeyboardInterrupt:
    print("\nStopped listening.")

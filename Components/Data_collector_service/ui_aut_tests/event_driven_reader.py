import uiautomation as auto

def on_focus_changed(sender):
    print(f'Focus changed to: {sender.Name} ({sender.ControlTypeName})')

auto.AddAutomationEventHandler(
    auto.EventId.AutomationFocusChanged,
    None,
    auto.TreeScope.Element,
    None
)

# check `automation.py -h` output and the /demos folder for the current signature
# for AutomationFocusChangedEventHandler.

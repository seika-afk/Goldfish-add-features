import uiautomation as auto

control = auto.GetFocusedControl()
print(control.Name)          # visible label/text of the control
print(control.ClassName)
print(control.ControlTypeName)

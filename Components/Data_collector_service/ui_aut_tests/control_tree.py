import uiautomation as auto

def dump_control_tree(control, depth=0):
    indent = '  ' * depth
    print(f'{indent}{control.ControlTypeName} | Name="{control.Name}"')
    for child in control.GetChildren():
        dump_control_tree(child, depth + 1)

window = auto.GetForegroundControl()
dump_control_tree(window)

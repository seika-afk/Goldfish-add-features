import re
import time
import uiautomation as auto
from helper import execute_save2db_and_delete

OBJ_REPLACEMENT_RUN = re.compile(r'(\ufffc\s*){2,}')  # icon-only buttons, no label
MAX_LIM=25
counter=0


def save(text):
    with open("log.txt","a",encoding="utf-8")as f:
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
    return (runtime_id, control.Name, control.ControlTypeName, control.ClassName)


def describe(control):
    global counter
    texts = get_control_text(control)
    automation_id = ''
    try:
        automation_id = control.AutomationId
    except Exception:
        pass
    if not control.Name and not texts and not automation_id:
        return
    save(f'Name: {control.Name}')
    save(f'ClassName: {control.ClassName}')
    save(f'ControlType: {control.ControlTypeName}')
    save(f'AutomationId: {automation_id}')
    counter+=1
    for t in texts:
        if t != control.Name:
            save(f'Content: {t}')
    save('---')
    if counter>MAX_LIM:
        success = execute_save2db_and_delete()
        if success:
            counter = 0

def watch(poll_seconds=0.3):
    last_identity = None
    while True:
        control = auto.GetFocusedControl()
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


#save locally for about 25 context switches (and if user uses goldfish )
#  it uses this context and the context at the time user presses on screen , then  answers

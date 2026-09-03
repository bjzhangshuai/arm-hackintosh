"""Explicitly acknowledged keyboard events for an already selected guest UI.

QEMU ui/input.c::qmp_send_key can silently discard keys while GDB stops a VM.
qmp_input_send_event instead rejects the entire batch with 'VM not running'.
Retry only that explicit, pre-delivery rejection. Never resume or reset a VM.
The caller must enforce the isolated-debug environment and exact QMP identity.
"""
import time

from tools.qmp_screendump import QMPError


def key_event(key, down):
    return {'type': 'key', 'data': {'key': {'type': 'qcode', 'data': key}, 'down': down}}


def accepted_events(client, events, *, sleep=time.sleep, attempts=80):
    if attempts < 1:
        raise ValueError('attempts must be positive')
    for attempt in range(attempts):
        try:
            client.execute('input-send-event', {'events': events})
            return
        except QMPError as error:
            # QEMU rejects before sending any event in this specific case.
            # Unknown/transport failures have uncertain delivery: never retry.
            if "'desc': 'VM not running'" not in str(error) or attempt + 1 == attempts:
                raise
            sleep(0.05)


def press(client, keys, *, sleep=time.sleep):
    down = [key_event(key, True) for key in keys]
    up = [key_event(key, False) for key in reversed(keys)]
    accepted_events(client, down, sleep=sleep)
    sleep(0.15)
    accepted_events(client, up, sleep=sleep)
    sleep(0.15)


def text_keys(text):
    simple = {' ': 'spc', '-': 'minus', '/': 'slash', '.': 'dot',
              '=': 'equal', '_': 'minus'}
    shifted = {':': 'semicolon', '>': 'dot', '&': '7', '_': 'minus'}
    result = []
    for char in text:
        if 'a' <= char <= 'z' or '0' <= char <= '9':
            result.append([char])
        elif 'A' <= char <= 'Z':
            result.append(['shift', char.lower()])
        elif char in shifted:
            result.append(['shift', shifted[char]])
        elif char in simple:
            result.append([simple[char]])
        else:
            raise ValueError(f'unsupported character {char!r}; no input sent')
    return result


def type_text(client, text, *, clear=False, sleep=time.sleep):
    keys = text_keys(text)  # validate the complete string before any input
    if clear:
        press(client, ['ctrl', 'u'], sleep=sleep)
    for combination in keys:
        press(client, combination, sleep=sleep)
    # Deliberately does not press Enter; the caller controls execution.

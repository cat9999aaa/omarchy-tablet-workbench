"""Pure device capability classification. No device identity leaves this layer."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DeviceFacts:
    key_bits: frozenset[int]
    abs_bits: frozenset[int]
    sw_bits: frozenset[int]
    virtual: bool
    usb_parent: bool
    bluetooth_parent: bool
    input_bus: int
    properties: dict[str, str]


def parse_bitmap(text: str, word_bits: int) -> frozenset[int]:
    if word_bits not in (32, 64) or not isinstance(text, str):
        raise ValueError('invalid bitmap')
    words = text.split()
    if not words or any(not re.fullmatch(r'[0-9a-fA-F]+', w) or
                        len(w) > word_bits // 4 for w in words):
        raise ValueError('invalid bitmap')
    return frozenset(i * word_bits + bit for i, word in enumerate(reversed(words))
                     for bit in range(word_bits) if int(word, 16) & (1 << bit))


def classify(facts: DeviceFacts) -> dict:
    keyboard = 'none'
    if {16, 30, 44, 28, 57} <= facts.key_bits:
        keyboard = 'unclassified'
        if facts.virtual:
            keyboard = 'virtual'
        elif facts.properties.get('ID_INPUT_KEYBOARD') == '1':
            usb = (facts.input_bus == 3 and facts.usb_parent and
                   facts.properties.get('ID_BUS') == 'usb')
            bluetooth = (facts.input_bus == 5 and facts.bluetooth_parent and
                         facts.properties.get('ID_BUS') == 'bluetooth')
            if usb or bluetooth:
                keyboard = 'physical'
    return {'keyboard': keyboard, 'touch': {53, 54} <= facts.abs_bits,
            'tablet_switch': 1 in facts.sw_bits}


def aggregate(items: list[dict], complete: bool, reason_code: str,
              sample_duration_ms: float) -> dict:
    unknown = sum(item['keyboard'] == 'unclassified' for item in items)
    present = any(item['keyboard'] == 'physical' for item in items)
    keyboard = (True if present else None if unknown else False) if complete else None
    health = 'observed' if complete and keyboard is not None else 'unknown'
    if not complete and reason_code not in ('device_changed', 'read_timeout', 'read_cancelled'):
        health = 'error'
    return {'schema_version': 1, 'complete': complete, 'health': health,
            'reason_code': ('unclassified_keyboard' if keyboard is None else 'observed')
            if complete else reason_code,
            'physical_keyboard_present': keyboard,
            'touch_present': any(item['touch'] for item in items) if complete else None,
            'tablet_switch_capability': any(item['tablet_switch'] for item in items) if complete else None,
            'excluded_virtual_count': sum(item['keyboard'] == 'virtual' for item in items),
            'unclassified_keyboard_count': unknown, 'sample_duration_ms': sample_duration_ms}

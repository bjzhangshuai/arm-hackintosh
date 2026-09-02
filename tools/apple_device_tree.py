#!/usr/bin/env python3
"""Strict helpers for Apple's flattened DeviceTree byte stream."""

from __future__ import annotations

from dataclasses import dataclass
import struct


PROPERTY_NAME_BYTES = 32
PROPERTY_HEADER_BYTES = 36
MAX_NODE_DEPTH = 128


class AppleDeviceTreeError(ValueError):
    """Raised when a flattened Apple DeviceTree is malformed or unsafe to edit."""


def _align4(value: int) -> int:
    return (value + 3) & ~3


def _encode_property(name: str, value: bytes, *, secure: bool) -> bytes:
    try:
        encoded_name = name.encode("ascii")
    except UnicodeEncodeError as error:
        raise AppleDeviceTreeError("new property name is not ASCII") from error
    if not encoded_name or len(encoded_name) >= PROPERTY_NAME_BYTES:
        raise AppleDeviceTreeError("new property name must contain 1 through 31 bytes")
    if len(value) > 0x7FFFFFFF:
        raise AppleDeviceTreeError("new property value is too large")

    padded_value = value + b"\0" * (_align4(len(value)) - len(value))
    return (
        encoded_name.ljust(PROPERTY_NAME_BYTES, b"\0")
        + struct.pack("<I", len(value) | (0x80000000 if secure else 0))
        + padded_value
    )


@dataclass(frozen=True)
class PropertySpan:
    name: str
    header_offset: int
    value_offset: int
    length: int
    padded_length: int
    secure: bool
    value: bytes


@dataclass(frozen=True)
class NodeSpan:
    name: str
    start: int
    properties_end: int
    end: int
    properties: tuple[PropertySpan, ...]
    children: tuple["NodeSpan", ...]

    def property(self, name: str) -> PropertySpan:
        matches = [item for item in self.properties if item.name == name]
        if len(matches) != 1:
            raise AppleDeviceTreeError(
                f"node {self.name!r} has {len(matches)} properties named {name!r}"
            )
        return matches[0]


def _decode_name(raw: bytes, *, role: str) -> str:
    encoded = raw.split(b"\0", 1)[0]
    if not encoded:
        raise AppleDeviceTreeError(f"{role} is empty")
    try:
        return encoded.decode("ascii")
    except UnicodeDecodeError as error:
        raise AppleDeviceTreeError(f"{role} is not ASCII") from error


def _parse_node(data: bytes, offset: int, depth: int) -> NodeSpan:
    if depth > MAX_NODE_DEPTH:
        raise AppleDeviceTreeError("DeviceTree nesting exceeds the safety limit")
    if offset < 0 or offset + 8 > len(data):
        raise AppleDeviceTreeError(f"truncated node header at offset {offset}")

    start = offset
    property_count, child_count = struct.unpack_from("<II", data, offset)
    offset += 8
    properties: list[PropertySpan] = []

    for index in range(property_count):
        if offset + PROPERTY_HEADER_BYTES > len(data):
            raise AppleDeviceTreeError(
                f"truncated property {index} header at offset {offset}"
            )
        name = _decode_name(
            data[offset : offset + PROPERTY_NAME_BYTES], role="property name"
        )
        encoded_length = struct.unpack_from("<I", data, offset + 32)[0]
        secure = bool(encoded_length & 0x80000000)
        length = encoded_length & 0x7FFFFFFF
        padded_length = _align4(length)
        value_offset = offset + PROPERTY_HEADER_BYTES
        value_end = value_offset + padded_length
        if value_end > len(data):
            raise AppleDeviceTreeError(
                f"property {name!r} at offset {offset} exceeds the DeviceTree"
            )
        properties.append(
            PropertySpan(
                name=name,
                header_offset=offset,
                value_offset=value_offset,
                length=length,
                padded_length=padded_length,
                secure=secure,
                value=data[value_offset : value_offset + length],
            )
        )
        offset = value_end

    properties_end = offset
    node_names = [item for item in properties if item.name == "name"]
    if len(node_names) != 1:
        raise AppleDeviceTreeError(
            f"node at offset {start} has {len(node_names)} name properties"
        )
    node_name = _decode_name(node_names[0].value, role="node name")

    children: list[NodeSpan] = []
    for _ in range(child_count):
        child = _parse_node(data, offset, depth + 1)
        children.append(child)
        offset = child.end

    return NodeSpan(
        name=node_name,
        start=start,
        properties_end=properties_end,
        end=offset,
        properties=tuple(properties),
        children=tuple(children),
    )


def parse_device_tree(data: bytes, *, allow_zero_padding: bool = False) -> NodeSpan:
    if not data:
        raise AppleDeviceTreeError("DeviceTree is empty")
    root = _parse_node(data, 0, 0)
    if root.end != len(data):
        trailing = data[root.end :]
        if not allow_zero_padding or any(trailing):
            raise AppleDeviceTreeError(
                f"DeviceTree has {len(data) - root.end} trailing bytes"
            )
    return root


def find_node(root: NodeSpan, path: str) -> NodeSpan:
    pieces = [piece for piece in path.split("/") if piece]
    if not pieces or pieces[0] != root.name:
        raise AppleDeviceTreeError(
            f"path {path!r} does not start at root {root.name!r}"
        )
    current = root
    for piece in pieces[1:]:
        matches = [child for child in current.children if child.name == piece]
        if len(matches) != 1:
            raise AppleDeviceTreeError(
                f"node {current.name!r} has {len(matches)} children named {piece!r}"
            )
        current = matches[0]
    return current


def memory_map_region(
    data: bytes, property_name: str, *, allow_zero_padding: bool = False
) -> tuple[int, int]:
    root = parse_device_tree(data, allow_zero_padding=allow_zero_padding)
    memory_map = find_node(root, "/device-tree/chosen/memory-map")
    item = memory_map.property(property_name)
    if item.length != 16:
        raise AppleDeviceTreeError(
            f"memory-map property {property_name!r} has length {item.length}, expected 16"
        )
    return struct.unpack("<QQ", item.value)


def replace_property_value_in_place(
    data: bytes,
    *,
    node_path: str,
    name: str,
    value: bytes,
) -> bytes:
    """Replace one property's bytes without changing any DeviceTree offset."""
    root = parse_device_tree(data)
    node = find_node(root, node_path)
    item = node.property(name)
    if len(value) != item.length:
        raise AppleDeviceTreeError(
            f"in-place property {name!r} requires {item.length} bytes, got {len(value)}"
        )

    updated = bytearray(data)
    updated[item.value_offset : item.value_offset + item.length] = value
    result = bytes(updated)
    reparsed = parse_device_tree(result)
    reparsed_item = find_node(reparsed, node_path).property(name)
    if reparsed_item.header_offset != item.header_offset or reparsed.end != root.end:
        raise AppleDeviceTreeError("in-place property replacement changed DeviceTree layout")
    return result


def insert_property(
    data: bytes,
    *,
    node_path: str,
    name: str,
    value: bytes,
    capacity: int,
    secure: bool = False,
) -> bytes:
    root = parse_device_tree(data)
    node = find_node(root, node_path)
    if any(item.name == name for item in node.properties):
        raise AppleDeviceTreeError(
            f"node {node_path!r} already contains property {name!r}"
        )

    record = _encode_property(name, value, secure=secure)
    required = len(data) + len(record)
    if capacity < len(data) or required > capacity:
        raise AppleDeviceTreeError(
            f"DeviceTree property requires {required} bytes but capacity is {capacity}"
        )

    updated = bytearray(data[: node.properties_end] + record + data[node.properties_end :])
    property_count = struct.unpack_from("<I", updated, node.start)[0]
    struct.pack_into("<I", updated, node.start, property_count + 1)
    result = bytes(updated)
    parse_device_tree(result)
    return result


def replace_property_exact_span(
    data: bytes,
    *,
    node_path: str,
    old_name: str,
    replacements: tuple[tuple[str, bytes, bool], ...],
) -> bytes:
    return replace_properties_exact_span(
        data,
        node_path=node_path,
        old_names=(old_name,),
        replacements=replacements,
    )


def replace_zero_filled_property_with_prefix(
    data: bytes,
    *,
    node_path: str,
    old_name: str,
    new_name: str,
    prefix: bytes,
) -> bytes:
    """Reuse one zero placeholder without changing its record or value size."""

    root = parse_device_tree(data)
    old_property = find_node(root, node_path).property(old_name)
    if old_property.secure:
        raise AppleDeviceTreeError(
            f"zero-placeholder property {old_name!r} is unexpectedly secure"
        )
    if any(old_property.value):
        raise AppleDeviceTreeError(
            f"zero-placeholder property {old_name!r} contains nonzero data"
        )
    if not prefix:
        raise AppleDeviceTreeError("zero-placeholder replacement prefix is empty")
    if len(prefix) > old_property.length:
        raise AppleDeviceTreeError(
            f"zero-placeholder replacement prefix requires {len(prefix)} bytes "
            f"but {old_name!r} has {old_property.length}"
        )
    value = prefix + bytes(old_property.length - len(prefix))
    result = replace_property_exact_span(
        data,
        node_path=node_path,
        old_name=old_name,
        replacements=((new_name, value, False),),
    )
    replacement = find_node(parse_device_tree(result), node_path).property(new_name)
    if (
        replacement.header_offset != old_property.header_offset
        or replacement.length != old_property.length
        or replacement.value != value
    ):
        raise AppleDeviceTreeError("zero-placeholder replacement changed DeviceTree layout")
    return result


def replace_properties_exact_span(
    data: bytes,
    *,
    node_path: str,
    old_names: tuple[str, ...],
    replacements: tuple[tuple[str, bytes, bool], ...],
) -> bytes:
    """Replace contiguous properties without moving any following DT byte.

    Each replacement tuple is ``(name, value, secure)``.  The encoded records
    must consume exactly the old records' byte span.  This is intended for a
    live Apple DeviceTree whose firmware-created internal pointers must remain
    valid across the edit.
    """
    if not old_names:
        raise AppleDeviceTreeError("exact-span old property list is empty")
    if len(set(old_names)) != len(old_names):
        raise AppleDeviceTreeError("exact-span old property names are not unique")
    if not replacements:
        raise AppleDeviceTreeError("exact-span replacement list is empty")

    root = parse_device_tree(data)
    node = find_node(root, node_path)
    old_properties = tuple(node.property(name) for name in old_names)
    property_indices = tuple(node.properties.index(item) for item in old_properties)
    expected_indices = tuple(
        range(property_indices[0], property_indices[0] + len(old_properties))
    )
    if property_indices != expected_indices:
        raise AppleDeviceTreeError("exact-span old properties are not contiguous")
    old_start = old_properties[0].header_offset
    old_end = old_properties[-1].value_offset + old_properties[-1].padded_length
    old_span = old_end - old_start

    replacement_names = [name for name, _, _ in replacements]
    if len(set(replacement_names)) != len(replacement_names):
        raise AppleDeviceTreeError("exact-span replacement names are not unique")
    old_name_set = set(old_names)
    existing_names = {
        item.name for item in node.properties if item.name not in old_name_set
    }
    collisions = sorted(existing_names.intersection(replacement_names))
    if collisions:
        raise AppleDeviceTreeError(
            f"exact-span replacement collides with existing properties: {collisions}"
        )

    records = b"".join(
        _encode_property(name, value, secure=secure)
        for name, value, secure in replacements
    )
    if len(records) != old_span:
        raise AppleDeviceTreeError(
            f"exact-span replacement requires {old_span} bytes but encodes {len(records)}"
        )

    updated = bytearray(data)
    updated[old_start:old_end] = records
    property_count = struct.unpack_from("<I", updated, node.start)[0]
    new_property_count = property_count - len(old_properties) + len(replacements)
    if not 0 <= new_property_count <= 0xFFFFFFFF:
        raise AppleDeviceTreeError("exact-span replacement property count overflows")
    struct.pack_into("<I", updated, node.start, new_property_count)

    result = bytes(updated)
    reparsed = parse_device_tree(result)
    if len(result) != len(data) or reparsed.end != root.end:
        raise AppleDeviceTreeError("exact-span replacement changed DeviceTree extent")
    return result

#!/usr/bin/env python3
"""
trace2json.py — Convert Xcode Instruments .trace files to JSON for analysis.

Runs xctrace export under the hood to extract metadata and table data,
resolves id/ref deduplication, and outputs a single self-contained JSON file.

Usage:
    python3 trace2json.py <file.trace> [--output path.json] [--limit 5000] [--schemas time-sample,syscall,...]
"""

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from typing import Any

# Default schemas to export (in priority order), if present in the trace
DEFAULT_SCHEMAS = [
    "time-sample",
    "os-signpost-arg",
    "syscall",
    "context-switch",
    "thread-narrative",
    "virtual-memory",
    "thread-info",
    "os-log-arg",
]

MAX_BACKTRACE_FRAMES = 20


def run_xctrace(args: list[str]) -> str:
    """Run xctrace with given args and return stdout."""
    cmd = ["xctrace", "export"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"xctrace failed: {result.stderr.strip()}")
    return result.stdout


def parse_toc(trace_path: str) -> dict:
    """Export and parse the table of contents."""
    xml_str = run_xctrace(["--input", trace_path, "--toc"])
    root = ET.fromstring(xml_str)

    metadata: dict[str, Any] = {
        "device": {},
        "process": {},
        "available_schemas": [],
        "warnings": [],
    }

    # Parse device info
    device = root.find(".//device")
    if device is not None:
        metadata["device"] = {
            "name": device.get("name", ""),
            "os-version": device.get("os-version", ""),
            "device-type": device.get("device-type", ""),
            "platform": device.get("platform", ""),
        }

    # Parse process info
    process = root.find(".//process")
    if process is not None:
        metadata["process"] = {
            "name": process.get("name", ""),
            "pid": process.get("pid", ""),
        }

    # Discover available schemas
    schemas = []
    for table in root.findall(".//data/table"):
        schema = table.get("schema", "")
        if schema and schema not in schemas:
            schemas.append(schema)
    metadata["available_schemas"] = schemas

    return metadata


def resolve_refs(registry: dict[str, Any], element: ET.Element) -> Any:
    """Resolve an element, handling id/ref deduplication."""
    ref = element.get("ref")
    if ref is not None:
        return registry.get(ref)

    eid = element.get("id")
    value = parse_element(registry, element)

    if eid is not None:
        registry[eid] = value

    return value


def parse_element(registry: dict[str, Any], element: ET.Element) -> Any:
    """Parse a single XML element into a Python value."""
    tag = element.tag

    # Sentinel = null
    if tag == "sentinel":
        return None

    # Backtrace
    if tag == "backtrace":
        frames = []
        for frame in element.findall("frame")[:MAX_BACKTRACE_FRAMES]:
            f: dict[str, Any] = {
                "name": frame.get("name", ""),
                "addr": frame.get("addr", ""),
            }
            binary = frame.find("binary")
            if binary is not None:
                f["binary"] = binary.get("name", "")
            frames.append(f)
        return frames

    # Duration / timestamp types — return structured value
    if tag in (
        "duration",
        "duration-on-core",
        "duration-waiting",
        "time",
        "start",
        "start-time",
        "end-time",
        "sample-time",
    ):
        fmt = element.get("fmt", "")
        text = element.text or ""
        try:
            raw = int(text.strip()) if text.strip() else 0
        except ValueError:
            raw = 0
        return {"value": raw, "fmt": fmt}

    # Thread / process — nested structured object
    if tag in ("thread", "process"):
        obj: dict[str, Any] = {}
        for k, v in element.attrib.items():
            if k not in ("id", "ref"):
                obj[k] = v
        # Recurse into children
        for child in element:
            child_val = resolve_refs(registry, child)
            if child_val is not None:
                obj[child.tag] = child_val
        return obj

    # Generic element with children (e.g., row wrapper elements)
    if len(element) > 0:
        obj = {}
        for k, v in element.attrib.items():
            if k not in ("id", "ref"):
                obj[k] = v
        for child in element:
            child_val = resolve_refs(registry, child)
            if child_val is not None:
                obj[child.tag] = child_val
        return obj

    # Leaf element — return text or fmt
    fmt = element.get("fmt")
    text = (element.text or "").strip()

    if fmt and text:
        # Numeric with formatted display
        try:
            return {"value": int(text), "fmt": fmt}
        except ValueError:
            try:
                return {"value": float(text), "fmt": fmt}
            except ValueError:
                return fmt
    elif fmt:
        return fmt
    elif text:
        return text

    # Fallback: return attributes as dict, or empty string
    attrs = {k: v for k, v in element.attrib.items() if k not in ("id", "ref")}
    return attrs if attrs else ""


def parse_schema_header(root: ET.Element) -> list[str]:
    """Extract column mnemonics from the schema header."""
    columns = []
    schema = root.find(".//schema")
    if schema is not None:
        for col in schema.findall("col"):
            mnemonic = col.findtext("mnemonic", "")
            columns.append(mnemonic)
    return columns


def export_table(trace_path: str, schema: str, limit: int) -> dict | None:
    """Export a single table and return parsed data."""
    xpath = f'/trace-toc/run/data/table[@schema="{schema}"]'
    try:
        xml_str = run_xctrace(["--input", trace_path, "--xpath", xpath])
    except RuntimeError as e:
        return {"error": str(e), "rows": [], "row_count": 0}

    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        return {"error": f"XML parse error: {e}", "rows": [], "row_count": 0}

    columns = parse_schema_header(root)
    registry: dict[str, Any] = {}
    rows: list[dict] = []
    total_rows = 0

    for row_elem in root.findall(".//row"):
        total_rows += 1
        if len(rows) >= limit:
            continue  # Keep counting but stop collecting

        row: dict[str, Any] = {}
        children = list(row_elem)
        for i, child in enumerate(children):
            # Use column mnemonic if available, otherwise tag name
            key = columns[i] if i < len(columns) else child.tag
            value = resolve_refs(registry, child)
            if value is not None:
                row[key] = value
        if row:
            rows.append(row)

    result: dict[str, Any] = {
        "row_count": len(rows),
        "total_row_count": total_rows,
        "rows": rows,
    }

    if total_rows > limit:
        result["truncated"] = True

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Convert Xcode Instruments .trace files to JSON"
    )
    parser.add_argument("trace", help="Path to .trace file")
    parser.add_argument(
        "--output", "-o", help="Output JSON path (default: <trace>.json)"
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=5000,
        help="Max rows per table (default: 5000)",
    )
    parser.add_argument(
        "--schemas",
        "-s",
        help="Comma-separated schemas to export (default: auto-detect from priority list)",
    )
    args = parser.parse_args()

    trace_path = os.path.abspath(args.trace)
    if not os.path.exists(trace_path):
        print(f"Error: {trace_path} does not exist", file=sys.stderr)
        sys.exit(1)

    # Default output path
    output_path = args.output or trace_path.rsplit(".", 1)[0] + ".json"

    print(f"Exporting TOC from {os.path.basename(trace_path)}...")
    try:
        metadata = parse_toc(trace_path)
    except Exception as e:
        print(f"Error reading TOC: {e}", file=sys.stderr)
        sys.exit(1)

    available = metadata["available_schemas"]
    print(f"Found {len(available)} schemas: {', '.join(available)}")

    # Determine which schemas to export
    if args.schemas:
        requested = [s.strip() for s in args.schemas.split(",")]
    else:
        # Use default priority list, filtered to what's available
        requested = [s for s in DEFAULT_SCHEMAS if s in available]
        # Also add any available schemas not in the default list
        for s in available:
            if s not in requested:
                requested.append(s)

    tables: dict[str, Any] = {}
    for schema in requested:
        if schema not in available:
            metadata["warnings"].append(f"Schema '{schema}' not found in trace")
            continue

        print(f"  Exporting {schema}...")
        try:
            table_data = export_table(trace_path, schema, args.limit)
            if table_data is not None:
                tables[schema] = table_data
                rc = table_data.get("row_count", 0)
                tc = table_data.get("total_row_count", 0)
                if table_data.get("truncated"):
                    msg = f"Schema '{schema}' truncated: {rc}/{tc} rows"
                    metadata["warnings"].append(msg)
                    print(f"    {rc}/{tc} rows (truncated)")
                elif table_data.get("error"):
                    print(f"    Error: {table_data['error']}")
                else:
                    print(f"    {rc} rows")
        except Exception as e:
            msg = f"Schema '{schema}' export failed: {e}"
            metadata["warnings"].append(msg)
            print(f"    Failed: {e}")

    output = {"metadata": metadata, "tables": tables}

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\nWrote {output_path} ({size_mb:.1f} MB)")
    if metadata["warnings"]:
        print(f"Warnings ({len(metadata['warnings'])}):")
        for w in metadata["warnings"]:
            print(f"  - {w}")


if __name__ == "__main__":
    main()

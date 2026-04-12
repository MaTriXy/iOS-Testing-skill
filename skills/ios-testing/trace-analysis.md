# Xcode Instruments Trace (.trace) File Analysis Reference

You can read and analyze `.trace` files directly using the `trace2json.py` script or the `xctrace` CLI tool. This lets you diagnose performance issues, CPU bottlenecks, memory leaks, and more — without requiring the user to open Instruments.

## Quick Start — trace2json.py (Preferred)

The `trace2json.py` script exports all trace data to a single JSON file, which Claude can read directly. This is faster and requires only one shell command.

### Locate the Script

```bash
# The script lives alongside this skill file
SCRIPT=$(find ~/.claude -name "trace2json.py" -path "*/ios-testing/*" 2>/dev/null | head -1)
```

### Usage

```bash
python3 "$SCRIPT" /path/to/file.trace [--output path.json] [--limit 5000] [--schemas time-sample,syscall,...]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--output`, `-o` | `<trace>.json` | Output JSON file path |
| `--limit`, `-l` | `5000` | Max rows per table (prevents huge output) |
| `--schemas`, `-s` | auto | Comma-separated schemas to export. Default: exports all available schemas, prioritizing common ones |

### JSON Structure

```json
{
  "metadata": {
    "device": {"name": "...", "os-version": "...", "device-type": "...", "platform": "..."},
    "process": {"name": "...", "pid": "..."},
    "available_schemas": ["time-sample", "syscall", ...],
    "warnings": ["Schema 'foo' truncated: 5000/23456 rows", ...]
  },
  "tables": {
    "time-sample": {
      "row_count": 5000,
      "total_row_count": 23456,
      "truncated": true,
      "rows": [
        {
          "time": {"value": 123456789, "fmt": "1.23 s"},
          "thread": {"name": "main", "tid": "0x1234"},
          "backtrace": [
            {"name": "functionName", "addr": "0x1234", "binary": "MyApp"},
            {"name": "callerName", "addr": "0x5678", "binary": "UIKitCore"}
          ]
        }
      ]
    }
  }
}
```

**Key details:**
- All `id`/`ref` deduplication is resolved inline — the JSON is self-contained
- Backtraces are flat arrays of frames (max 20 per backtrace)
- Durations/timestamps: `{"value": <nanoseconds>, "fmt": "1.23 s"}`
- `null` values (XML sentinels) are omitted
- Each table reports `row_count` (exported) vs `total_row_count` (in trace)
- Truncation and export failures are recorded in `metadata.warnings`

### Default Schema Priority

When `--schemas` is not specified, the script exports these schemas first (if present), then any remaining schemas found in the trace:

1. `time-sample` — CPU time samples with call stacks
2. `os-signpost-arg` — Signpost intervals (SwiftUI, App Launch, custom)
3. `syscall` — System calls with duration and backtraces
4. `context-switch` — Thread scheduling events
5. `thread-narrative` — High-level thread activity summary
6. `virtual-memory` — Page faults, memory pressure
7. `thread-info` — Thread names and types
8. `os-log-arg` — OS log messages

## Analysis Workflow

When a user provides a `.trace` file:

### 1. Export to JSON

```bash
SCRIPT=$(find ~/.claude -name "trace2json.py" -path "*/ios-testing/*" 2>/dev/null | head -1)
python3 "$SCRIPT" /path/to/file.trace
```

### 2. Read and Analyze

Use the Read tool to open the JSON file. Check `metadata` first for device/process info and warnings, then examine relevant tables.

### 3. What to Look For

**CPU/Performance (`time-sample`)**:
- Hot call stacks — functions appearing repeatedly in backtraces
- Main thread blocked or running heavy computation
- Threads stuck in `Blocked` or `Wait` states

**Scheduling (`context-switch`, `thread-narrative`)**:
- Frequent preemptions
- Long blocked durations (contention)
- Priority inversions

**System Calls (`syscall`)**:
- High wait time vs CPU time (I/O bound)
- Frequent short-duration syscalls in tight loops
- Failed syscalls (non-zero errno)

**Memory (`virtual-memory`)**:
- Page faults, memory pressure events
- Large allocation patterns

**Signposts (`os-signpost-arg`)**:
- Long-duration intervals (slow operations)
- SwiftUI body evaluation times
- Custom app signpost performance

### 4. Suggest Improvements

After identifying issues, suggest specific code changes:
- Move heavy work off the main thread
- Reduce lock contention (use actors, or finer-grained locks)
- Batch I/O operations to reduce syscall overhead
- Add caching to reduce redundant computation
- Use `os_signpost` to instrument suspected slow code paths

---

## Manual Workflow (Fallback)

If `trace2json.py` is unavailable or you need to inspect a specific schema interactively, use `xctrace` directly.

### .trace File Structure

A `.trace` file is a directory bundle containing:

```
MyTrace.trace/
├── corespace/                  # Core data stores (binary, indexed)
│   ├── MANIFEST.plist
│   └── currentRun/core/stores/ # Indexed bulk data stores
├── instrument_data/            # Per-instrument run data (zipped)
│   └── <UUID>/run_data/1.run.zip
├── symbols/                    # Symbol archives for symbolication
│   ├── MANIFEST.plist
│   └── stores/*.symbolsarchive
├── Trace1.run/
│   └── RunIssues.storedata     # Issues found during recording
├── form.template               # Template definition used for recording
├── open.creq                   # Compatibility requirements (plist)
├── shared_data/                # Shared recording metadata
└── UI_state_metadata.bin       # Instruments UI state
```

### Step 1: Export the Table of Contents

```bash
xctrace export --input /path/to/file.trace --toc
```

This returns XML describing:
- **Target device** and OS version
- **Profiled process** (name, PID)
- **All data tables** with their `schema` names

### Step 2: Identify Available Schemas

Common schemas by template type:

| Instruments Template | Key Schemas |
|---------------------|-------------|
| **Time Profiler** | `time-sample` |
| **CPU Profiler** | `time-sample`, `gcd-perf-event` |
| **CPU Counters** | `kdebug-counters-with-time-sample`, `CounterMetricByThread`, `CounterMetricByCore`, `CoreTypeByProcess` |
| **System Trace** | `context-switch`, `syscall`, `thread-narrative`, `virtual-memory`, `thread-info` |
| **Allocations** | `time-sample` (+ allocation-specific tables) |
| **Leaks** | Leak detection tables |
| **App Launch** | `time-sample`, `os-signpost-arg` |
| **SwiftUI** | `os-signpost-arg`, `time-sample` |
| **Swift Concurrency** | `os-signpost-arg`, `time-sample` |
| **Animation Hitches** | `os-signpost-arg`, hitch-related tables |
| **Network** | Network activity tables |
| **Power Profiler** | Power/energy tables |
| **Metal System Trace** | GPU scheduling and shader tables |
| **File Activity** | File I/O tables |
| **Logging** | `os-log-arg` |

### Step 3: Export Table Data

```bash
xctrace export --input /path/to/file.trace \
  --xpath '/trace-toc/run/data/table[@schema="time-sample"]'
```

### Common Export Commands

```bash
# CPU time samples
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="time-sample"]'

# System calls
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="syscall"]'

# Context switches
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="context-switch"]'

# Thread narrative
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="thread-narrative"]'

# Virtual memory
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="virtual-memory"]'

# Signposts
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="os-signpost-arg"]'

# OS log messages
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="os-log-arg"]'

# Thread info
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="thread-info"]'
```

### Understanding the XML Output

#### Schema Header

```xml
<schema name="time-sample">
  <col><mnemonic>time</mnemonic><name>Timestamp</name><engineering-type>sample-time</engineering-type></col>
  <col><mnemonic>thread</mnemonic><name>Thread</name><engineering-type>thread</engineering-type></col>
  <!-- ... -->
</schema>
```

#### Row Data

- **`id` and `ref` attributes**: `id="N"` defines a value; `ref="N"` references it (deduplication). Always resolve refs when parsing.
- **`fmt` attribute**: Human-readable formatted value.
- **`<sentinel/>`**: Null/missing value.
- **Nested elements**: Threads contain process info, backtraces contain frames.

#### Backtrace Frames

```xml
<backtrace id="14">
  <frame name="kevent_id" addr="0x18261da75">
    <binary name="libsystem_kernel.dylib" UUID="..." path="/usr/lib/system/libsystem_kernel.dylib"/>
  </frame>
  <frame name="_dispatch_kq_poll" addr="0x10194b9b8">
    <binary name="libdispatch.dylib" UUID="..." path="/usr/lib/system/introspection/libdispatch.dylib"/>
  </frame>
</backtrace>
```

#### Duration Values

```xml
<duration id="8" fmt="2.17 µs">2167</duration>
<duration-on-core id="9" fmt="2.17 µs">2167</duration-on-core>
<duration-waiting id="78" fmt="200.76 ms">200763625</duration-waiting>
```

## Available Instruments Templates

- **Activity Monitor** — Overall system activity
- **Allocations** — Memory allocation tracking and leak detection
- **Animation Hitches** — UI fluidity and frame drop detection
- **App Launch** — Launch time profiling
- **Audio System Trace** — Audio pipeline analysis
- **CPU Counters** — Hardware performance counters (cycles, instructions, bottlenecks)
- **CPU Profiler** — CPU usage with call stacks
- **Core ML** — ML model inference performance
- **Data Persistence** — Core Data and file I/O
- **File Activity** — File system operations
- **Game Memory** — Game-specific memory analysis
- **Game Performance / Overview** — Game frame rate and GPU
- **Leaks** — Memory leak detection
- **Logging** — os_log message capture
- **Metal System Trace** — GPU command scheduling and shaders
- **Network** — Network request tracing
- **Power Profiler** — Energy and power impact
- **Processor Trace** — Low-level CPU instruction tracing
- **RealityKit Trace** — AR/VR performance
- **Swift Concurrency** — Task and actor scheduling
- **SwiftUI** — View body evaluation and rendering
- **System Trace** — Thread scheduling, syscalls, VM, interrupts
- **Tailspin** — Lightweight always-on system trace
- **Time Profiler** — Statistical CPU sampling

## Tips

- **Large traces**: Use `--limit` with `trace2json.py` to cap rows. For manual export, pipe through `head -N`.
- **XPath limitations**: Some complex schemas crash `xctrace`. The script handles this gracefully with try/except. For manual use, fall back to simpler schema queries.
- **Multiple runs**: A trace can contain multiple runs. For manual export, use `/trace-toc/run[@number="1"]/data/table[...]`.
- **Symbolication**: Backtraces include symbolicated names when symbol archives are present. If frames show only addresses, symbols may be missing.
- **Custom instruments**: Third-party instruments may add schemas not listed above. Always check the TOC (or `metadata.available_schemas` in JSON).

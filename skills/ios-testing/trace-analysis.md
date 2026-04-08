# Xcode Instruments Trace (.trace) File Analysis Reference

You can read and analyze `.trace` files directly using the `xctrace` CLI tool. This lets you diagnose performance issues, CPU bottlenecks, memory leaks, and more — without requiring the user to open Instruments.

## .trace File Structure

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

## Reading Traces with xctrace

### Step 1: Export the Table of Contents

Always start by exporting the TOC to discover what data the trace contains:

```bash
xctrace export --input /path/to/file.trace --toc
```

This returns XML describing:
- **Target device** and OS version
- **Profiled process** (name, PID)
- **All data tables** with their `schema` names — these are what you query

### Step 2: Identify Available Schemas

Extract the schema names from the TOC output. Common schemas by template type:

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

Export a specific table by schema name using XPath:

```bash
xctrace export --input /path/to/file.trace \
  --xpath '/trace-toc/run/data/table[@schema="time-sample"]'
```

The output is XML with a `<schema>` header describing columns, followed by `<row>` elements.

### Common Export Commands

```bash
# CPU time samples (call stacks, thread states, core assignment)
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="time-sample"]'

# System calls with duration, CPU time, wait time, and backtraces
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="syscall"]'

# Context switches (thread scheduling events)
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="context-switch"]'

# Thread narrative (high-level thread activity summary)
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="thread-narrative"]'

# Virtual memory events
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="virtual-memory"]'

# os_signpost intervals (Points of Interest, SwiftUI, custom signposts)
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="os-signpost-arg"]'

# OS log messages
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="os-log-arg"]'

# Thread info (thread names, types)
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="thread-info"]'

# Dynamic library loads
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="dyld-library-load"]'
```

## Understanding the XML Output

### Schema Header

Each exported table starts with a `<schema>` element listing the columns:

```xml
<schema name="time-sample">
  <col><mnemonic>time</mnemonic><name>Timestamp</name><engineering-type>sample-time</engineering-type></col>
  <col><mnemonic>thread</mnemonic><name>Thread</name><engineering-type>thread</engineering-type></col>
  <col><mnemonic>core-index</mnemonic><name>Core Index</name><engineering-type>core</engineering-type></col>
  <col><mnemonic>thread-state</mnemonic><name>Thread State</name><engineering-type>thread-state</engineering-type></col>
  <!-- ... -->
</schema>
```

### Row Data

Rows contain typed elements matching the schema. Key patterns:

- **`id` and `ref` attributes**: Elements with `id="N"` define a value; elements with `ref="N"` reference a previously defined value (deduplication). Always resolve refs when parsing.
- **`fmt` attribute**: Human-readable formatted value (use this for display).
- **`<sentinel/>`**: Represents a null/missing value for that column.
- **Nested elements**: Threads contain process info, backtraces contain frame lists, etc.

### Backtrace Frames

Call stacks appear as `<backtrace>` elements with `<frame>` children:

```xml
<backtrace id="14">
  <frame name="kevent_id" addr="0x18261da75">
    <binary name="libsystem_kernel.dylib" UUID="..." path="/usr/lib/system/libsystem_kernel.dylib"/>
  </frame>
  <frame name="_dispatch_kq_poll" addr="0x10194b9b8">
    <binary name="libdispatch.dylib" UUID="..." path="/usr/lib/system/introspection/libdispatch.dylib"/>
  </frame>
  <!-- ... more frames ... -->
</backtrace>
```

### Duration Values

Durations are in nanoseconds (raw value) with a `fmt` attribute for human-readable form:

```xml
<duration id="8" fmt="2.17 µs">2167</duration>
<duration-on-core id="9" fmt="2.17 µs">2167</duration-on-core>
<duration-waiting id="78" fmt="200.76 ms">200763625</duration-waiting>
```

## Analysis Workflow

When a user provides a `.trace` file, follow this workflow:

### 1. Discover Contents

```bash
xctrace export --input /path/to/file.trace --toc
```

From the TOC, identify:
- What app was profiled (process name and PID)
- What device and OS (simulator vs physical)
- Which instrument schemas are available

### 2. Export Relevant Tables

Based on the user's concern, export the most relevant tables. For large traces, pipe through `head` to sample first:

```bash
xctrace export --input file.trace \
  --xpath '/trace-toc/run/data/table[@schema="time-sample"]' | head -500
```

### 3. Analyze and Report

Look for these common issues in the data:

**CPU/Performance (time-sample, CPU Counters)**:
- Threads spending excessive time in specific functions (hot call stacks)
- Main thread blocked or running heavy computation
- Threads stuck in `Blocked` or `Wait` states
- High instruction delivery/processing bottleneck ratios (CPU Counters)

**Scheduling (context-switch, thread-narrative)**:
- Frequent preemptions ("balanced off CPU to optimize performance")
- Long blocked durations with lock/event IDs (contention)
- Threads going idle unexpectedly
- Priority inversions (low-priority thread holding resource needed by high-priority)

**System Calls (syscall)**:
- Syscalls with high `Wait Time` vs `CPU Time` (I/O bound)
- Frequent short-duration syscalls in tight loops
- Failed syscalls (non-zero errno)

**Memory (virtual-memory)**:
- Page faults, memory pressure events
- Large allocation patterns

**Signposts (os-signpost-arg)**:
- Long-duration signpost intervals (slow operations)
- SwiftUI body evaluation times
- Custom app signpost performance

### 4. Suggest Improvements

After identifying issues, suggest specific code changes:
- Move heavy work off the main thread
- Reduce lock contention (use actors, or finer-grained locks)
- Batch I/O operations to reduce syscall overhead
- Add caching to reduce redundant computation
- Use `os_signpost` to instrument suspected slow code paths for future profiling

## Available Instruments Templates

These are the standard templates available for recording traces:

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

- **Large traces**: The XML output can be very large. Use `head -N` to sample, or redirect to a file for parsing.
- **XPath limitations**: The `--xpath` flag supports basic XPath. If a query crashes (some complex swift-table schemas can), fall back to exporting the TOC and using simpler schema queries.
- **Multiple runs**: A trace can contain multiple runs. Use `/trace-toc/run[@number="1"]/data/table[...]` to target a specific run.
- **Symbolication**: Exported backtraces include symbolicated frame names when symbol archives are present in the trace bundle. If frames show only addresses, the symbols may be missing.
- **Custom instruments**: Third-party or custom instrument packages may add schemas not listed above. Always check the TOC first.

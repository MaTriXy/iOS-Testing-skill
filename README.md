# @ioloro/ios-testing

A Claude Code skill for writing correct, modern iOS and macOS tests using Swift Testing, XCTest, and XCUITest — and for analyzing Instruments .trace files directly in the terminal.

## What it does

This skill teaches Claude when and how to use each Apple testing framework:

- **Swift Testing** — default for all new unit and integration tests (`@Test`, `#expect`, `@Suite`, parameterized tests)
- **XCTest** — performance benchmarks (`measure {}`, `XCTClockMetric`, `XCTCPUMetric`, `XCTMemoryMetric`, `XCTStorageMetric`), energy/power measurement (`XCTOSSignpostMetric`)
- **XCUITest** — UI automation, accessibility audits, animation hitch testing, scroll performance, screenshot capture
- **Instruments .trace analysis** — export and analyze Time Profiler, System Trace, Allocations, and other trace data without leaving the terminal

## Examples

Here are things you can ask Claude to do with this skill installed:

### Writing tests

- "Write tests for my UserService class"
- "Add parameterized tests for all the edge cases in this parser"
- "Convert these XCTest tests to Swift Testing"
- "Test that this function throws ValidationError.tooShort for empty input"
- "Write a test that verifies the notification fires when data updates"

### Performance and energy

- "Add a performance test that measures CPU and memory for this sort operation"
- "Write a test that measures my app's launch time"
- "Set up signpost-based measurement for my image processing pipeline"
- "Add scroll deceleration hitch testing for my collection view"

### UI testing

- "Write UI tests for the login flow"
- "Add accessibility audits for contrast and dynamic type on every screen"
- "Set up screenshot capture across light mode, dark mode, and all themes"
- "Write tests that handle Sign In with Apple and permission dialogs on real devices"
- "Generate an HTML gallery from my test screenshots"

### Trace file analysis

- "Analyze this .trace file and tell me why the app is slow"
- "Look at the time-sample data and find the hottest call stacks"
- "Check the syscall table for I/O bottlenecks"
- "What's blocking the main thread in this System Trace?"

## Why

AI models frequently:
- Default to XCTest when Swift Testing should be used
- Mix `XCTAssertEqual` with `#expect` in the same file
- Use bare `measure {}` instead of specific `XCTMetric` subclasses
- Skip parameterized tests in favor of copy-pasted test functions
- Forget about performance, power, and animation testing entirely
- Can't analyze .trace files without manual xctrace export/XML parsing

This skill fixes all of that.

## Install

```bash
npm install -g @ioloro/ios-testing
```

## What's included

| File | Covers |
|------|--------|
| `SKILL.md` | Framework selection rules, critical rules, decision tree |
| `swift-testing.md` | `@Test`, `@Suite`, `#expect`, `#require`, parameterized tests, traits, tags, async patterns, `confirmation()`, exit tests, attachments, custom scoping traits |
| `xctest.md` | `measure {}`, all `XCTMetric` subclasses, manual measurement, signpost-based energy testing, baselines, power profiling |
| `xcuitest.md` | Element queries, waiting patterns, launch config, scroll/animation performance, hitch metrics, accessibility audits, screenshot capture, multi-variant screenshot testing, real device testing, screenshot extraction and review website generation, page object pattern |
| `trace-analysis.md` | Instruments .trace file structure, JSON export workflow, all common schemas by template, XML format reference, analysis patterns |
| `trace2json.py` | Python 3 script that exports .trace files to self-contained JSON — resolves id/ref deduplication, flattens backtraces, caps output size |

### Highlights

- **Trace file analysis** — `trace2json.py` exports any .trace file to JSON in one command, then Claude reads and analyzes it directly
- **Multi-variant screenshot pipeline** — capture every screen across themes, appearances, and user types with structured naming
- **Screenshot review website** — automatically generates an HTML gallery grouping screenshots by screen with side-by-side variant comparison
- **Real device testing** — UDID-based destinations, signing setup, fresh install for NUX/onboarding capture
- **System sheet handling** — dismiss Sign In with Apple, TCC prompts, and notification banners on real devices
- **Accessibility audits** — automated contrast, hit region, dynamic type, and text clipping checks (iOS 17+)
- **Animation hitch testing** — `XCTOSSignpostMetric` sub-metrics for scroll deceleration, dragging, navigation transitions
- **Parameterized tests** — tuples, `CaseIterable`, cartesian products, `zip()` patterns
- **Exit tests** — process crash verification (Swift 6.2+)
- **Energy/power measurement** — `os_signpost` instrumentation with `XCTOSSignpostMetric` for CPU, memory, and power correlation
- **Page object pattern** — encapsulated screen interactions for maintainable UI tests

## License

MIT

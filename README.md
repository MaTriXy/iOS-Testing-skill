# @ioloro/ios-testing

A Claude Code skill for writing correct, modern iOS and macOS tests using Swift Testing, XCTest, and XCUITest.

## What it does

This skill teaches Claude (and other AI) when and how to use each Apple testing framework:

- **Swift Testing** — default for all new unit and integration tests (`@Test`, `#expect`, `@Suite`, parameterized tests)
- **XCTest** — performance benchmarks (`measure {}`, `XCTClockMetric`, `XCTCPUMetric`, `XCTMemoryMetric`, `XCTStorageMetric`), energy/power measurement (`XCTOSSignpostMetric`)
- **XCUITest** — UI automation, accessibility audits, animation hitch testing, scroll performance

## Why

AI models frequently:
- Default to XCTest when Swift Testing should be used
- Mix `XCTAssertEqual` with `#expect` in the same file
- Use bare `measure {}` instead of specific `XCTMetric` subclasses
- Skip parameterized tests in favor of copy-pasted test functions
- Forget about performance, power, and animation testing entirely

This skill fixes all of that.

## Install

```bash
# Via npm
npm install -g @ioloro/ios-testing

# Then enable in Claude Code
/plugin install @ioloro/ios-testing
```

## What's included

| File | Covers |
|------|--------|
| `SKILL.md` | Framework selection rules, critical rules, decision tree |
| `swift-testing.md` | `@Test`, `@Suite`, `#expect`, `#require`, parameterized tests, traits, tags, async patterns, `confirmation()`, exit tests, attachments, custom scoping traits |
| `xctest.md` | `measure {}`, all `XCTMetric` subclasses, manual measurement, signpost-based energy testing, baselines, power profiling |
| `xcuitest.md` | Element queries, waiting patterns, launch config, scroll/animation performance, hitch metrics, accessibility audits, screenshot capture, multi-variant screenshot testing, real device testing, screenshot extraction and review website generation, page object pattern |

### Highlights

- **Multi-variant screenshot pipeline** — capture every screen across themes, appearances, and user types with structured naming
- **Screenshot review website** — automatically generates an HTML gallery grouping screenshots by screen with side-by-side variant comparison, and opens it in the browser
- **Real device testing** — UDID-based destinations, signing setup, fresh install for NUX/onboarding capture
- **Accessibility audits** — automated contrast, hit region, dynamic type, and text clipping checks (iOS 17+)
- **Animation hitch testing** — `XCTOSSignpostMetric` sub-metrics for scroll deceleration, dragging, navigation transitions
- **Parameterized tests** — tuples, `CaseIterable`, cartesian products, `zip()` patterns
- **Exit tests** — process crash verification (Swift 6.2+)
- **Energy/power measurement** — `os_signpost` instrumentation with `XCTOSSignpostMetric` for CPU, memory, and power correlation
- **Page object pattern** — encapsulated screen interactions for maintainable UI tests

## License

MIT

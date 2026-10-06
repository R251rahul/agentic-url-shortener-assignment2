# Brownfield scenario

**Input:** Add analytics to an existing URL shortener without breaking redirect behavior.

The graph inserts a `brownfield_analysis` node after requirements. It identifies impacted modules, API contracts and regression-sensitive flows before implementation. Implementation depends on both architecture and brownfield analysis.

**Validation:** redirect regression test, analytics integration test, security gate and release gate.

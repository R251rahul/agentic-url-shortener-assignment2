# Greenfield scenario

**Input:** Build a URL shortener with creation, redirect and click analytics.

**Decomposition:**
1. Requirements agent normalizes intent and acceptance criteria.
2. Architecture agent chooses API, persistence, service boundaries and governance controls.
3. Implementation agent produces service/data-flow artifacts.
4. Tests and security execute independently after implementation.
5. Documentation runs in parallel with implementation/test work where dependencies allow.
6. Release is synchronized behind tests + security + documentation and a policy/human gate.

**Validation:** unit/integration tests, security policy check, release readiness check and audit trail.

## Why

Suppressing noisy InsecureRequestWarning messages can improve readability in local and test runs that intentionally disable TLS verification, but forcing warning suppression globally can hide critical security signals in higher environments. This change is needed to make warning suppression explicit, configurable, and safe-by-default.

## What Changes

- Define a configurable warning suppression policy for urllib3 InsecureRequestWarning.
- Require security-safe defaults where warning suppression is disabled unless explicitly enabled.
- Define environment-based controls for when warning suppression is allowed (local/test) and when it is disallowed (production/CI).
- Add startup messaging that clearly states current TLS verify mode and warning suppression mode.
- Add validation behavior for conflicting settings (for example: verify enabled but suppression forced).

## Capabilities

### New Capabilities
- tls-warning-suppression-control: Control and audit insecure TLS warning suppression behavior through explicit runtime configuration and environment safety rules.

### Modified Capabilities
- None.

## Impact

- Affected code: TLS utility and startup/runtime messaging in services.py.
- Affected dependencies: urllib3 warning handling pathway in requests stack.
- Security impact: Ensures warning suppression cannot silently weaken production observability.
- Operational impact: Cleaner local logs with explicit safety guardrails and diagnostics.

## 1. Configuration model

- [ ] 1.1 Add explicit environment flag for insecure TLS warning suppression control.
- [ ] 1.2 Add environment mode resolution (local/test/prod-like) used by suppression policy.
- [ ] 1.3 Add optional production override flag for exceptional suppression use cases.

## 2. Suppression policy implementation

- [ ] 2.1 Refactor urllib3 warning suppression from unconditional import-time call to policy-gated execution.
- [ ] 2.2 Enforce default-deny suppression in production-like environments without explicit override.
- [ ] 2.3 Keep existing ATLASSIAN_VERIFY_TLS behavior unchanged while decoupling warning suppression control.

## 3. Runtime diagnostics

- [ ] 3.1 Add compact startup status output for TLS verify mode, suppression mode, and environment mode.
- [ ] 3.2 Add targeted warning for conflicting settings (suppression enabled while verify=true).
- [ ] 3.3 Add targeted warning when suppression request is rejected by environment policy.

## 4. Documentation and examples

- [ ] 4.1 Update .env usage documentation comments/examples for suppression flags and environment mode.
- [ ] 4.2 Add operator-facing examples for local/test and production-safe configurations.

## 5. Verification

- [ ] 5.1 Validate default behavior keeps InsecureRequestWarning visible when suppression flag is absent.
- [ ] 5.2 Validate suppression applies in allowed non-production mode.
- [ ] 5.3 Validate suppression is blocked in production-like mode without explicit override.
- [ ] 5.4 Validate startup diagnostics and conflict warnings for each configuration combination.

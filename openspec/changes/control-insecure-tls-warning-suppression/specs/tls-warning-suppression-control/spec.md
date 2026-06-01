## ADDED Requirements

### Requirement: Warning suppression is explicit and configurable
The system SHALL suppress urllib3 InsecureRequestWarning messages only when an explicit suppression configuration flag is enabled.

#### Scenario: Suppression disabled by default
- **WHEN** no suppression configuration is provided
- **THEN** urllib3 InsecureRequestWarning messages remain enabled

#### Scenario: Suppression explicitly enabled
- **WHEN** suppression configuration is explicitly set to true
- **THEN** urllib3 InsecureRequestWarning messages are suppressed for that runtime

### Requirement: Environment-aware suppression safety policy
The system SHALL enforce an environment-aware policy that prevents accidental warning suppression in production-like environments by default.

#### Scenario: Non-production environment
- **WHEN** runtime environment is local or test and suppression is enabled
- **THEN** warning suppression is applied and runtime status indicates suppression mode

#### Scenario: Production-like environment without override
- **WHEN** runtime environment is production-like and suppression is enabled without explicit override
- **THEN** suppression is not applied and the system emits a policy warning

### Requirement: TLS and warning mode diagnostics
The system SHALL provide runtime diagnostics that clearly indicate TLS verification mode and warning suppression mode.

#### Scenario: Startup diagnostics emitted
- **WHEN** the script starts
- **THEN** it prints a concise status message with verify mode, suppression mode, and environment mode

#### Scenario: Conflicting configuration
- **WHEN** suppression is enabled while TLS verification remains enabled
- **THEN** the system emits a warning indicating suppression has no practical effect in that configuration

### Requirement: Backward-safe behavior with existing TLS verify controls
The system SHALL remain compatible with existing ATLASSIAN_VERIFY_TLS behavior while keeping warning suppression independently controlled.

#### Scenario: TLS verify disabled and suppression disabled
- **WHEN** TLS verification is disabled but suppression is disabled
- **THEN** insecure TLS warnings are visible and existing request behavior remains unchanged

#### Scenario: TLS verify disabled and suppression enabled
- **WHEN** TLS verification is disabled and suppression is enabled under allowed policy
- **THEN** request behavior remains unchanged and insecure TLS warnings are suppressed

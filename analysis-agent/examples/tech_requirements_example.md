## Golden Example: Technical Requirement

This example demonstrates how to translate a dense, technical requirement into a clear work package description and a
set of atomic, testable acceptance criteria.

---

#### Input Text:

```text
SWX002-COZY0012: Manifest integrity checksum check failed

GIVEN <Dash CoZy Stuff> has computed the received Manifest integrity checksum
WHEN the computed value does not match the integrityChecksum of the received Manifest
THEN <Dash CoZy Stuff> shall
    - set the synchronization state to SynchroNeeded and store the current date as last synchronization date
    - store the integrityChecksum of the received Manifest for future synchronization calls
    - store a ManifestStatus object with error code FAILED / MANIFEST_INVALID_CHECKSUM
    - start a status flush procedure
```

#### Generated Output:

This task is to implement the error handling logic on the Dash CoZy Stuff unit for when a received software manifest
fails its integrity checksum validation. When the onboard unit calculates a checksum for a downloaded manifest that does
not match the `integrityChecksum` provided within that manifest, it must reject the update and perform a series of
specific fallback and logging actions to ensure system stability and provide clear diagnostics for future analysis.

**Acceptance Criteria:**

* GIVEN Dash CoZy Stuff has received a Manifest AND has computed its integrity checksum
* WHEN the computed checksum does not match the `integrityChecksum` field in the Manifest
* THEN the synchronization state must be set to `SynchroNeeded`.
* AND THEN the current date and time must be stored as the last synchronization date.
* AND THEN the incorrect `integrityChecksum` from the received Manifest must be stored for future reference.
* AND THEN a new `ManifestStatus` object must be created and stored with an error code of `FAILED` and a reason of
  `MANIFEST_INVALID_CHECKSUM`.
* AND THEN a status flush procedure must be initiated.
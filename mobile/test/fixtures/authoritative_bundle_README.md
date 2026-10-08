# Synthetic bundle-v1 specimens

These fixtures contain no production data. They were captured from the isolated
`backend/tests/test_authoritative_state.py` fixture builder at B-1, with a fixed
Snapshot clock, evaluation context and judgment RNG seed (1234).

- `empty`: minimal initialized state.
- `rich`: ordinary/utility/override spending, Claim/Family/frozen/fixed panels,
  partial card payment, cash and an edited recurring child in archive with NULL date.
- `early`: executed cash-fixed with reset-sensitive Summary/payment distinction.
- `boundary`: exact supported safe-integer maximum.
- `real`: supported pre_batch migration retaining integral REAL JSON values.
- `closed`: cancellation/reconfirmation followed by actual month close.
- `canonical_edges`: an archived planned source with complete ownership and
  an unowned manual entry's empty key, both independently accepted by B-1 and
  the old acquisition oracle. The parser must not invent stricter constraints.
- `authoritative_bundle/identity_edges`: canonical isolated server output with
  fixed panel 11 and planned ledger source 11. Their close-item identities are
  distinct (`kind`, `id`), despite the same numeric ID.

The parser tests compare the real old API/coordinator model assembly against the
opt-in bundle assembly and OfflineBaseline serialization. Keep original numeric
tokens (including `5000.0`); reformatting a REAL value to `5000` changes its hash.
No fixture is an owner manifest, recovery artifact, or deployed Snapshot.

Canonical admission also checks the complete raw/projected field intersection,
exact source membership and repository SQL ordering. Explicit presenter
exceptions are the confirmed child's displayed date and toll-group rewritten
fields; this is validation, never client financial calculation or fuzzy repair.

`scripts/generate_bundle_policy.py` prints the admission-only policy artifact
from the backend registry. Regenerate and review
`mobile/lib/src/generated/bundle_policy_manifest.dart` whenever that registry
changes; `--check` and `backend/tests/test_bundle_policy_artifact.py` enforce
exact build parity. A policy supplied by a bundle cannot redefine the trusted
registry. Dictionary ordering is immaterial; canonical rate strings are exact
(`0.0120` is not `0.012`). These definitions must not drive client calculations.

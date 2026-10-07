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

The parser tests compare the real old API/coordinator model assembly against the
opt-in bundle assembly and OfflineBaseline serialization. Keep original numeric
tokens (including `5000.0`); reformatting a REAL value to `5000` changes its hash.
No fixture is an owner manifest, recovery artifact, or deployed Snapshot.

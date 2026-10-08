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

Admission follows the normative server-authoritative trust boundary in
`docs/architecture.md`. These tests are not an independent financial oracle.
The complete raw/projected field intersection is checked for each supplied raw
entity. Composite payment groups are not copies of their first member.
Server-selected projection completeness, financial eligibility, partition and
ordering are not reconstructed on mobile. A required section missing from the
wire still rejects; a present empty selection is not the same as a missing field.

## Admission responsibility inventory

| Check | Category | Action | Contract / reason |
| --- | --- | --- | --- |
| Trusted-server authentication, principal, generation guards | A | KEEP | Identity and stale-response isolation; diagnostic acquisition stays nonpublishing |
| Version, required field presence/types, null/false/zero/empty | A | KEEP | Typed defaults cannot manufacture authoritative data |
| Raw numeric tokens, safe exact money, duplicate JSON keys | A | KEEP | Wire safety before JSON rounding/model construction |
| Snapshot schema, columns, counts, hashes and authority fingerprint | A | KEEP | Structural integrity, not independent financial correctness proof |
| Revision, evaluation date and explicit policy/status context | A | KEEP | Coherent authority envelope |
| Durable readback, pending and Offline gates | A | KEEP | Existing publication/recovery boundary remains unchanged |
| Snapshot raw domains and namespace-specific primary identities | B | KEEP | Storage and safe typed representation |
| Raw recurring epochs, source/child ownership, fixed/cash references | B | KEEP | Snapshot restoreability; no eligibility calculation |
| Raw batches/events/allocations and explicit stored conservation | B | KEEP | Storage ownership, not recreation of allocation decisions |
| Payment event non-null idempotency keys | B | FIX | Actual migrated table-wide partial UNIQUE, BINARY; empty keys are indexed, nulls are not |
| Canonical policy registry and exact duplicated definitions | B | KEEP | Existing Snapshot restore / Offline compatibility; no discount calculation |
| Projection policy descriptor reference/schema/rounding | B/C | NARROW | Require a supported matching scope/definition, not latest-by-month selection |
| Supplied raw entry/panel/cash fields | B | KEEP | Complete shared-field equality and real source existence |
| Current/confirmed projection membership | B/C | NARROW | Supplied sources/epochs and disjoint installed identities required; monthly selection not recomputed |
| Confirmed actual principal/date | B | KEEP | Owned immutable raw child witness; indexed once, no per-source ledger scan |
| Visible actual's duplicated effective aliases | B | KEEP | Same explicit value must agree; agreement is not financial proof |
| Archived effective discounts/burden | C | SERVER OWNED | No independent policy-dependent calculation |
| Close collection | B/C | NARROW | Supplied references/kinds/raw fields/unique identities required; completeness, date eligibility and order server owned |
| Payment rows/members/parts/events | B/C | NARROW | Unique valid references, explicit member lists, raw values and same-entity aliases required; expected full set/order not recreated |
| Payment composite ID/key shape | B | KEEP | Declared group namespace, not classifier/partition proof |
| Payment grouping, partition, classifier and composite presentation | C | REMOVE | Server financial projection, not first-member raw equality |
| Composite principal/remaining sums | B/C | NARROW | Keep direct principal aliases; backend owns aggregation/allocation |
| Summary, judgment and financial formulas | C | SERVER OWNED | No new client calculation |

Manipulated and rehashed synthetic bodies are not evidence of authenticated
server origin. A/B defects must reject before candidate or durable publication.
C-only disagreement is not a client blocker; canonical calculation tests belong
on the backend. Future registry drift remains a compatibility concern, not a
solved protocol guarantee.

Bundle admission also checks every decoded string value and map key for valid
Unicode scalar representation before shape/money/Snapshot hashing. This covers
nullable strings and nested generic JSON, including escaped lone UTF-16
surrogates in otherwise valid UTF-8 transport. It rejects without replacing,
trimming or normalizing. `bundle_unicode.json` is shared with the actual backend
canonical UTF-8 / migrated SQLite restore oracle; valid supplementary pairs,
NUL and distinct composed/decomposed strings retain their existing semantics.

`scripts/generate_bundle_policy.py` prints the admission-only policy artifact
from the backend registry. Regenerate and review
`mobile/lib/src/generated/bundle_policy_manifest.dart` whenever that registry
changes; `--check` and `backend/tests/test_bundle_policy_artifact.py` enforce
exact build parity. A policy supplied by a bundle cannot redefine the trusted
registry. Dictionary ordering is immaterial; canonical rate strings are exact
(`0.0120` is not `0.012`). These definitions must not drive client calculations.

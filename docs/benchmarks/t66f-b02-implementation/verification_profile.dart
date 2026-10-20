// Explicit synthetic HOST harness configuration, never imported by app code.
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

// Measured 100k graph: V=400532, E=400528, payload=261543083 B.
// 500k permits its 400558-object G1/G2 union with finite headroom.
// 384 MiB covers ~282 MB core metadata + two further complete stage-link
// sets (~102.5 MB) and bounded receipts. This is NOT a promise that every
// graph at the object ceiling fits every independent byte/page budget.
const largeVerificationStoreLimits = ClientStoreLimits(
  objectCount: 500000,
  metadataBytes: 384 * 1024 * 1024,
);
const largeVerificationFetchLimits = FetchLimits.largeGraphVerification();

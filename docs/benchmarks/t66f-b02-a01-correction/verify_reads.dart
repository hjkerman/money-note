// Fresh-process host oracle: canonical hot/control and bounded accepted reads.
// No baseline installation, financial recomputation, source switch or activation.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../t66f-b02-implementation/verification_profile.dart';

Future<void> main(List<String> args) async {
  final out = Directory(args.single);
  final result = jsonDecode(File('${out.path}/result.json').readAsStringSync());
  if (!(result['status'] as String).startsWith('PASS_COLD')) {
    throw StateError('complete accepted campaign required');
  }
  final fixture = jsonDecode(
    File('${out.path}/server/backend-fixture.json').readAsStringSync(),
  );
  final cache = CacheNamespace.forTarget(
    result['origin'],
    SyncTarget.parse(fixture['manifest']['target']),
  );
  final store = SegmentedClientStore.open(
    Directory('${out.path}/client'),
    cache,
    adapters: true,
    limits: largeVerificationStoreLimits,
  );
  List<int> pins() {
    final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
    try {
      return encodeC1([
        for (final row in db.select(
          'SELECT * FROM generation_roots ORDER BY generation_id,hash',
        ))
          Map<String, dynamic>.from(row),
      ]);
    } finally {
      db.close();
    }
  }

  try {
    final accepted = await store.recoverAcceptedGeneration();
    if (accepted.id != result['accepted_after'])
      throw StateError('wrong accepted source');
    final before = pins();
    store.withAcceptedRead(accepted, (view) {
      if (objectHash('hot', encodeC1(view.hot)) !=
              view.target.roots['hot']!.hash ||
          objectHash('control', encodeC1(view.control)) !=
              view.target.roots['control']!.hash) {
        throw StateError('backend projection/control bytes changed');
      }
    });
    final work = store.work.snapshot(), watch = Stopwatch()..start();
    for (var i = 0; i < 20; i++) {
      store.withAcceptedRead(accepted, (v) {
        final rows = v.rows('ledger_entries', limit: 16);
        if (rows.length != 16)
          throw StateError('unexpected authoritative page');
      });
    }
    final delta = store.work.since(work);
    for (final name in [
      'full_recoveries',
      'full_verifications',
      'canonical_full_builds',
      'pin_inserts',
      'pin_deletes',
    ]) {
      if ((delta[name] ?? 0) != 0)
        throw StateError('unexpected repeated-read work: $name');
    }
    if (!sameBytes(before, pins()))
      throw StateError('pins changed during reads');
    for (final entry in (result['protected_legacy_before'] as Map).entries) {
      if (localChecksum(File(entry.key as String).readAsBytesSync()) !=
          entry.value) {
        throw StateError('legacy or pending bytes changed');
      }
    }
    File('${out.path}/post-reads.json').writeAsStringSync(
      '${const JsonEncoder.withIndent('  ').convert({'accepted': accepted.id, 'sequence': accepted.sequence, 'hot_control_hashes_match_backend_roots': true, 'reads': 20, 'work': delta, 'elapsed_us': watch.elapsedMicroseconds, 'pin_rows_unchanged': true, 'legacy_pending_bytes_unchanged': true, 'rss_peak_bytes': ProcessInfo.maxRss, 'scope': 'accepted logical read; NOT legacy Frozen-B installation or R1 proof'})}\n',
    );
  } finally {
    store.close();
  }
}

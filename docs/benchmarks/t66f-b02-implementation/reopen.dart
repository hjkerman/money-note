// Fresh process: actual E1 open/recovery, no accepted metadata fabrication.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import 'verification_profile.dart';

Future<void> main(List<String> args) async {
  final out = Directory(args.single);
  final prior = jsonDecode(File('${out.path}/result.json').readAsStringSync());
  final source = jsonDecode(
    File('${out.path}/server/backend-fixture.json').readAsStringSync(),
  );
  final target = SyncTarget.parse(source['manifest']['target']);
  final store = SegmentedClientStore.open(
    Directory('${out.path}/client'),
    CacheNamespace.forTarget(prior['origin'], target),
    adapters: true,
    limits: largeVerificationStoreLimits,
  );
  try {
    final accepted = await store.recoverAcceptedGeneration();
    final health = store.inspectStoreHealth();
    final preserved = <String, String>{
      for (final p in (prior['protected_legacy_before'] as Map).keys)
        p as String: localChecksum(File(p).readAsBytesSync()),
    };
    final sameLegacy =
        jsonEncode(preserved) == jsonEncode(prior['protected_legacy_before']);
    if (!health.healthy ||
        accepted.id != prior['accepted_after'] ||
        !sameLegacy) {
      throw StateError('fresh process did not preserve verified state');
    }
    if (accepted.id != null) {
      store.withAcceptedRead(
        accepted,
        (r) => r.rows('ledger_entries', limit: 1),
      );
    }
    File('${out.path}/fresh-process.json').writeAsStringSync(
      jsonEncode({
        'healthy': health.healthy,
        'objects_checked': health.objectsChecked,
        'stages_checked': health.stagingsChecked,
        'accepted_id': accepted.id,
        'legacy_and_pending_bytes_preserved': sameLegacy,
        'r1_activation': 'CLOSED',
        'work': store.work.snapshot(),
      }),
    );
  } finally {
    store.close();
  }
}

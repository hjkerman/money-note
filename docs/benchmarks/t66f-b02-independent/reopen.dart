// fresh VM 전체 authoritative read. old ticket/observation 권한을 사용하지 않는다.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import '../t66f-b02-implementation/verification_profile.dart';
import 'values.dart';

Future<void> main(List<String> args) async {
  final out = Directory(args.single),
      r = jsonDecode(File('${out.path}/result.json').readAsStringSync()) as Map;
  final initial = SyncTarget.parse(
    (jsonDecode(
      File('${out.path}/server/backend-fixture.json').readAsStringSync(),
    ) as Map)['manifest']['target'],
  );
  final store = SegmentedClientStore.open(
    Directory('${out.path}/client'),
    CacheNamespace.forTarget(r['origin'] as String, initial),
    adapters: true,
    limits: largeVerificationStoreLimits,
  );
  try {
    final health = store.inspectStoreHealth();
    if (!health.healthy) throw StateError('health');
    final accepted = await store.recoverAcceptedGeneration();
    final expected = (jsonDecode(
      File('${out.path}/server/mutation-123457.json').readAsStringSync(),
    ) as Map)['graph']['raw_value_sha256'];
    final actual = store.withAcceptedRead(accepted, independentReadDigests);
    if (jsonEncode(actual) != jsonEncode(expected)) {
      for (final key in actual.keys) {
        if (jsonEncode(actual[key]) != jsonEncode(expected[key]))
          throw StateError('fresh value digest $key');
      }
    }
    final value = {
      'status': 'PASS',
      'healthy': health.healthy,
      'objects_checked': health.objectsChecked,
      'stages_checked': health.stagingsChecked,
      'accepted': accepted.id,
      'complete_e4_digests': actual,
      'old_authority_reused': false,
      'r1': 'CLOSED',
    };
    File('${out.path}/fresh-process.json')
        .writeAsStringSync('${jsonEncode(value)}\n');
    stdout.writeln(jsonEncode(value));
  } finally {
    store.close();
  }
}

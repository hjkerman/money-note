// Test-only real child. Parent SIGKILLs at actual E1 renewed-stage/batch hooks.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';
import '../../../mobile/test/support/segmented_large_transport.dart';
import '../t66f-b02-implementation/verification_profile.dart';

Future<void> main(List<String> args) async {
  final root = Directory(args[0]), point = args[2];
  final fixture = GenerationFixture(
    jsonDecode(File(args[1]).readAsStringSync()),
  );
  final transport = BatchFixtureTransport(fixture);
  var observations = 0, requests = 0, expired = false, newObject = false;
  transport.after = (reply, method, path, body) {
    if (path.endsWith('/observations') && reply.status == 201) observations++;
    return reply;
  };
  transport.before = (method, path, body) async {
    if (path.endsWith('/objects') && ++requests == 3 && !expired) {
      expired = true;
      return remoteError(
        'OBSERVATION_EXPIRED',
        'new_observation',
        410,
        body!['request_id'],
      );
    }
    return null;
  };
  final store = SegmentedClientStore.open(
    root,
    fixture.cache,
    publication: true,
    limits: largeVerificationStoreLimits,
    fault: (actual) {
      if (observations != 2) return;
      if (actual == 'after_object_insert') newObject = true;
      if ((point == 'renewed_stage_prepare' &&
              actual == 'after_staging_insert') ||
          (point == 'renewed_stage_commit' && actual == 'after_commit') ||
          (point == 'renewed_batch_prepare' &&
              actual == 'after_object_insert') ||
          (point == 'renewed_batch_commit' &&
              newObject &&
              actual == 'after_commit')) {
        File('${root.path}/ready').writeAsStringSync(point, flush: true);
        stdin.readLineSync();
      }
    },
  );
  await IncrementalFetcher(
    store,
    transport,
    limits: largeVerificationFetchLimits,
  ).acquire();
  store.close();
}

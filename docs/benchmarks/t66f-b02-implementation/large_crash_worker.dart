// Actual E2 + selected profile; parent terminates this process at durable hooks.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';
import '../../../mobile/test/support/segmented_large_transport.dart';
import 'verification_profile.dart';

Future<void> main(List<String> args) async {
  final root = Directory(args[0]);
  final fixture = GenerationFixture(
    jsonDecode(File(args[1]).readAsStringSync()) as Map<String, dynamic>,
  );
  final point = args[2];
  var progressSeen = false;
  var progressRecords = 0;
  final store = SegmentedClientStore.open(
    root,
    fixture.cache,
    acquisition: true,
    limits: largeVerificationStoreLimits,
    fault: (actual) {
      if (actual == 'after_acquisition_insert') progressSeen = true;
      if (actual == 'after_progress_insert') progressRecords++;
      if (actual == point ||
          (point == 'batch_middle' &&
              actual == 'after_progress_insert' &&
              progressRecords == 2) ||
          (point == 'after_acquisition_commit' &&
              progressSeen &&
              actual == 'after_commit')) {
        File('${root.path}/ready').writeAsStringSync(point, flush: true);
        stdin.readLineSync();
      }
    },
  );
  await IncrementalFetcher(
    store,
    BatchFixtureTransport(fixture),
    limits: largeVerificationFetchLimits,
  ).acquire();
  store.close();
}

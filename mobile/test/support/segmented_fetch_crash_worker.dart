// Actual E2 orchestration in a disposable child. Parent SIGKILLs at barriers.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import 'segmented_e2_fixture.dart';

Future<void> main(List<String> args) async {
  final root = Directory(args[0]),
      fixture = GenerationFixture(
          jsonDecode(File(args[1]).readAsStringSync()) as Map<String, dynamic>),
      point = args[2];
  var progressSeen = false;
  final store = SegmentedClientStore.open(root, fixture.cache,
      acquisition: true, fault: (actual) {
    if (actual == 'after_acquisition_insert') progressSeen = true;
    if (actual == point ||
        (point == 'after_acquisition_commit' &&
            progressSeen &&
            actual == 'after_commit')) {
      File('${root.path}/ready').writeAsStringSync(point, flush: true);
      stdin.readLineSync();
    }
  });
  await IncrementalFetcher(store, FixtureTransport(fixture)).acquire();
  store.close();
}

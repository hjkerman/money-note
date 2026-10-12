// Disposable child process only; parent SIGKILLs at a synchronous DB checkpoint.
import 'dart:io';

import 'package:money_note_mobile/src/segmented/store.dart';
import 'segmented_fixture.dart';

void main(List<String> args) {
  final root = Directory(args[0]),
      golden = ServerGolden(args[1]),
      point = args[2];
  final store = SegmentedClientStore.open(root, golden.cache, fault: (actual) {
    if (actual == point ||
        (point == 'after_staging_commit' && actual == 'after_commit')) {
      File('${root.path}/ready').writeAsStringSync(point, flush: true);
      stdin.readLineSync(); // Deterministic barrier, not a guessed delay.
    }
  });
  if (point == 'after_staging_insert' || point == 'after_staging_commit') {
    store.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
  } else {
    store.putVerifiedObject(golden.ref('raw-root'), golden.bytes('raw-root'));
  }
  store.close();
}

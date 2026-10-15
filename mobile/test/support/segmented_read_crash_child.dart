import 'dart:io';

import 'package:money_note_mobile/src/segmented/store.dart';

import 'segmented_e2_fixture.dart';
import 'dart:convert';

Future<void> main(List<String> args) async {
  final root = Directory(args[0]), point = args[1];
  final fixture = GenerationFixture(jsonDecode(
      File('${root.path}/synthetic-fixture.json').readAsStringSync()));
  final store =
      SegmentedClientStore.open(root, fixture.cache, publication: true);
  final accepted = await store.recoverAcceptedGeneration();
  void boundary(String name) {
    if (name != point) return;
    File('${root.path}/reader-ready').writeAsStringSync(name, flush: true);
    // Parent terminates this newly owned synthetic process with SIGKILL.
    while (true) {
      sleep(const Duration(milliseconds: 20));
    }
  }

  boundary('before_read');
  if (point == 'full_proof_ready') {
    await store.verifyAcceptedForMaterialization(accepted);
    boundary(point);
  }
  store.withAcceptedRead(accepted, (read) {
    read.rows('app_settings');
    boundary('during_read');
    return read.hot;
  });
  boundary('after_read');
  store.close();
}

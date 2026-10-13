import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';

import 'segmented_e2_fixture.dart';

Future<void> main(List<String> args) async {
  final root = Directory(args[0]);
  final fixture = GenerationFixture(
      jsonDecode(File(args[1]).readAsStringSync()) as Map<String, dynamic>);
  void boundary(String point) {
    if (point != args[3]) return;
    File('${root.path}/ready').writeAsStringSync(point, flush: true);
    while (true) {
      sleep(const Duration(seconds: 1));
    }
  }

  final store = SegmentedClientStore.open(root, fixture.cache,
      publication: true, fault: boundary);
  final expected = await store.recoverAcceptedGeneration();
  final stage = store.loadStaging(args[2])!;
  final version = store.publicationDataVersion;
  final proof = args.length > 4 && args[4] == 'incremental'
      ? await store.verifyPublicationCandidate(stage.manifest, expected,
          verifiedDataVersion: version)
      : await verifyCompleteGeneration(
          stage.manifest,
          (ref) =>
              store.getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING')),
          base: expected.manifest);
  final prepared = store.prepareGeneration(
      syncUuid(), stage.id, proof, expected,
      verifiedDataVersion: version);
  boundary('before_transaction');
  store.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
  throw StateError('boundary not reached');
}

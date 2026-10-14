// 보존된 최초 E3 source snapshot만 시험하는 counterfactual 비용 재현이다.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';

Future<void> main(List<String> args) async {
  final job = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final fixtures = (job['fixtures'] as List)
      .map(
        (p) => GenerationFixture(
          jsonDecode(File(p as String).readAsStringSync())
              as Map<String, dynamic>,
        ),
      )
      .toList();
  final store = SegmentedClientStore.open(
    Directory(job['root'] as String),
    fixtures.first.cache,
    publication: true,
  );
  final records = <Map>[];
  try {
    for (final item in [
      (0, 'cold'),
      (0, 'identical'),
      (1, 'single-change'),
      (1, 'repeated'),
    ]) {
      final fixture = fixtures[item.$1];
      AuditTrace.reset('recovery');
      final expected = await store.recoverAcceptedGeneration();
      AuditTrace.phase = 'acquisition';
      final stage = await IncrementalFetcher(
        store,
        FixtureTransport(fixture),
      ).acquire();
      final version = store.publicationDataVersion;
      AuditTrace.phase = 'verification';
      final proof = await verifyCompleteGeneration(
        stage.manifest,
        (r) => store.getVerifiedObject(r)!,
        base: expected.manifest,
      );
      AuditTrace.phase = 'preparation';
      final prepared = store.prepareGeneration(
        syncUuid(),
        stage.stagingId,
        proof,
        expected,
        verifiedDataVersion: version,
      );
      AuditTrace.phase = 'publication';
      final result = store.commitPreparedGeneration(
        prepared,
        finalAuthorityFence: () {},
      );
      AuditTrace.phase = 'cleanup';
      store.discardUnacceptedGeneration(prepared.id);
      records.add({
        'scenario': item.$2,
        'sequence': result.sequence,
        'objects': fixture.objects.length,
        'events': AuditTrace.stop(),
      });
    }
    stdout.writeln(jsonEncode({'path': store.path, 'records': records}));
  } finally {
    store.close();
  }
}

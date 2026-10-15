// Actual SQL observer in a disposable package copy. Input binding and graph
// fixtures were produced by the actual AppState/D3a/D3b Flutter cost test.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';
import '../t66e4/measure.dart' show summarize;

Future<void> main(List<String> args) async {
  final inputs = jsonDecode(File(args.single).readAsStringSync()) as List;
  final output = <Map<String, Object?>>[];
  for (final input in inputs) {
    final first = GenerationFixture(input['initial']),
        next = GenerationFixture(input['changed']);
    final root = Directory.systemTemp.createTempSync('mn-e4-frozen-sql-');
    var store = SegmentedClientStore.open(root, first.cache, adapters: true);
    try {
      Future<void> publish(GenerationFixture fixture) async {
        final base = await store.recoverAcceptedGeneration();
        final acquired = await IncrementalFetcher(
          store,
          FixtureTransport(fixture),
        ).acquire(verifiedBase: base);
        final version = store.publicationDataVersion;
        final proof = await store.verifyPublicationCandidate(
          acquired.manifest,
          base,
          verifiedDataVersion: version,
        );
        final p = store.prepareGeneration(
          syncUuid(),
          acquired.stagingId,
          proof,
          base,
          verifiedDataVersion: version,
        );
        store.commitPreparedGeneration(p, finalAuthorityFence: () {});
      }

      await publish(first);
      final accepted = store.acceptedGeneration(),
          full = await store.verifyAcceptedForMaterialization(
            store.acceptedGeneration(),
          );
      final binding = Map<String, dynamic>.from(input['binding']);
      // Only local storage UUID/namespace/sequence are rebound. Legacy logical
      // B identity, user/synced_at and hashes remain the actual fixture values.
      binding['namespace'] = store.cache.key;
      binding['generation'] = accepted.id;
      binding['sequence'] = accepted.sequence;
      final phases = <Map<String, Object?>>[];
      final beforePins = store.work.snapshot(),
          pinsWatch = Stopwatch()..start();
      AuditTrace.reset('frozen_pin_handoff');
      final f = store.prepareFrozenGeneration(
        accepted,
        full,
        binding,
        frozenId: syncUuid(),
        finalAuthorityFence: () {},
      );
      store.finishFrozenHandoff(f, finalAuthorityFence: () {});
      pinsWatch.stop();
      final pinEvents = AuditTrace.stop();
      phases.add({
        ...summarize(
          'frozen_pin_handoff',
          pinsWatch.elapsedMicroseconds,
          pinEvents,
          store.work.since(beforePins),
        ),
        'frozen_insert': pinEvents
            .where((e) => (e['sql'] as String).startsWith('INSERT INTO frozen'))
            .length,
        'frozen_update': pinEvents
            .where((e) => (e['sql'] as String).startsWith('UPDATE frozen'))
            .length,
      });
      Future<void> measure(String name) async {
        final before = store.work.snapshot();
        AuditTrace.reset(name);
        final watch = Stopwatch()..start();
        final frozen = await store.recoverFrozenGeneration(f.id);
        store.withFrozenRead(frozen, (r) {
          r.hot;
          r.control;
        });
        watch.stop();
        final delta = store.work.since(before);
        phases.add({
          ...summarize(
            name,
            watch.elapsedMicroseconds,
            AuditTrace.stop(),
            delta,
          ),
          'full_frozen_recoveries': delta['frozen_full_recoveries'] ?? 0,
        });
      }

      await measure('cold_frozen');
      await measure('warm_frozen');
      await measure('repeated_frozen');
      await publish(next);
      await measure('unrelated_accepted_change');
      final other = SegmentedClientStore.open(
        root,
        first.cache,
        adapters: true,
      );
      final id = syncUuid();
      other.createStaging(
        id,
        ObservationManifest.fromBytes(encodeC1(first.manifest)),
        DateTime.now().toUtc(),
      );
      other.close();
      await measure('external_commit_full_fallback');
      await measure('post_fallback_warm');
      store.close();
      AuditTrace.reset('fresh_handle_open');
      final openWatch = Stopwatch()..start();
      store = SegmentedClientStore.open(root, first.cache, adapters: true);
      openWatch.stop();
      phases.add(
        summarize(
          'fresh_handle_open',
          openWatch.elapsedMicroseconds,
          AuditTrace.stop(),
          const {},
        ),
      );
      await measure('fresh_handle_full_recovery');
      await measure('fresh_handle_warm');
      output.add({
        'history': input['history'],
        'required_objects': first.objects.length,
        'phases': phases,
      });
    } finally {
      store.close();
      root.deleteSync(recursive: true);
    }
  }
  stdout.writeln(jsonEncode(output));
}

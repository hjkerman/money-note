// Existing independent SQL observer, in a disposable package copy ONLY.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';

Map<String, Object?> summarize(
  String name,
  int us,
  List<Map<String, Object?>> events,
  Map<String, int> work,
) {
  int sum(String field) =>
      events.fold(0, (n, e) => n + (e[field] as int? ?? 0));
  return {
    'name': name,
    'elapsed_us': us,
    'sql_statements': events.length,
    'returned_rows': sum('rows_returned'),
    'object_body_bytes': sum('body_bytes_read'),
    'raw_rows': sum('raw_rows_read'),
    'raw_nodes': sum('raw_objects_read'),
    'index_nodes': sum('index_objects_read'),
    'pin_insert': sum('pin_insert'),
    'pin_delete': sum('pin_delete'),
    'pin_update': sum('pin_update'),
    'read_begin': events.where((e) => e['sql'] == 'BEGIN DEFERRED').length,
    'full_recoveries': work['full_recoveries'] ?? 0,
    'rss_bytes': ProcessInfo.currentRss,
    'object_identities': events
        .expand((e) => (e['object_identities'] as List? ?? []))
        .toSet()
        .toList(),
    'sql': events.map((e) => e['sql']).toSet().toList(),
  };
}

Future<void> main() async {
  final results = <Map<String, Object?>>[];
  for (final size in [4, 400]) {
    final bridge = await BackendBridge.start(history: size);
    final fixture = GenerationFixture(bridge.fixture);
    final root = Directory.systemTemp.createTempSync('mn-e4-measure-');
    var store = SegmentedClientStore.open(
      root,
      fixture.cache,
      publication: true,
    );
    try {
      Future<void> publish() async {
        final expected = await store.recoverAcceptedGeneration();
        final acquired = await IncrementalFetcher(
          store,
          AuthenticatedSegmentedTransport(
            client: bridge,
            origin: syntheticOrigin,
            credential: () => bridge.token,
          ),
        ).acquire(verifiedBase: expected);
        final version = store.publicationDataVersion;
        final proof = await store.verifyPublicationCandidate(
          acquired.manifest,
          expected,
          verifiedDataVersion: version,
        );
        final p = store.prepareGeneration(
          syncUuid(),
          acquired.stagingId,
          proof,
          expected,
          verifiedDataVersion: version,
        );
        store.commitPreparedGeneration(p, finalAuthorityFence: () {});
      }

      await publish();
      final reads = <Map<String, Object?>>[];
      Future<void> measure(String name, Future<void> Function() action) async {
        final before = store.work.snapshot();
        AuditTrace.reset(name);
        final watch = Stopwatch()..start();
        await action();
        watch.stop();
        reads.add(
          summarize(
            name,
            watch.elapsedMicroseconds,
            AuditTrace.stop(),
            store.work.since(before),
          ),
        );
      }

      Future<void> hot() async {
        final accepted = await store.recoverAcceptedGeneration();
        store.withAcceptedRead(accepted, (r) {
          final hot = r.hot, control = r.control;
          if (hot['kind'] != 'hot' || control['kind'] != 'control')
            throw StateError('read oracle');
          return r.generation.id;
        });
      }

      await measure('healthy_hot', hot);
      await measure('repeated_hot', hot);
      await measure('one_row_page', () async {
        final a = await store.recoverAcceptedGeneration();
        final rows = store.withAcceptedRead(
          a,
          (r) => r.rows(
            'ledger_entries',
            after: TreeKey.parse(['i', '999'], 'ledger_entries'),
            limit: 1,
          ),
        );
        if (rows.length != 1) throw StateError('page oracle');
        final expected = (fixture.source['ledger_entries'] as List).singleWhere(
          (r) => r['id'] == 1000,
        );
        if (rows.single['title'] != expected['title']) {
          throw StateError('Unicode oracle');
        }
      });
      await bridge.command({'command': 'mutate'});
      await publish();
      await measure('small_change_hot', hot);
      store.close();
      store = SegmentedClientStore.open(root, fixture.cache, publication: true);
      await measure('fresh_recovery_hot', hot);
      await measure('post_recovery_hot', hot);
      final direct = await bridge.command({'command': 'oracle'});
      // Independent committed storage inspection, OUTSIDE the timed read phases.
      final sqlite = sqlite3.open(store.path);
      final persistedObjects = sqlite
          .select('SELECT count(*) AS n FROM objects')
          .single['n'];
      final rootPins = sqlite
          .select('SELECT count(*) AS n FROM generation_roots')
          .single['n'];
      final acceptedSequence = sqlite
          .select('SELECT sequence FROM accepted')
          .single['sequence'];
      sqlite.close();
      results.add({
        'history': size,
        'objects': (direct['objects'] as List).length,
        'persisted_objects': persistedObjects,
        'root_pin_rows': rootPins,
        'accepted_sequence': acceptedSequence,
        'source_rows': (direct['source'] as Map).values.fold<int>(
          0,
          (n, v) => n + (v as List).length,
        ),
        'reads': reads,
      });
    } finally {
      store.close();
      await bridge.dispose();
      root.deleteSync(recursive: true);
    }
  }
  stdout.writeln(jsonEncode(results));
}

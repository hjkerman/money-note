// 소스 copy의 SQL 계측 외에 검증·저장·publication 알고리즘은 변경하지 않는다.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';
import 'package:sqlite3/sqlite3.dart';

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
  final root = Directory(job['root'] as String);
  String? fault;
  String? crash;
  final fired = <String>[];
  void hook(String point) {
    fired.add(point);
    if (crash == point) {
      File('${root.path}/crash-ready').writeAsStringSync(point, flush: true);
      while (true) {
        sleep(const Duration(seconds: 1));
      }
    }
    if (fault == point) throw const SegmentedException('AUDIT_FAULT');
  }

  var store = SegmentedClientStore.open(
    root,
    fixtures.first.cache,
    publication: true,
    fault: hook,
  );
  CompleteGenerationProof? last;
  PreparedGeneration? prepared;
  Future<Map<String, Object?>> publish(int target, String action) async {
    final watch = Stopwatch()..start();
    final fixture = fixtures[target];
    AuditTrace.reset('recovery');
    try {
      if (action == 'reopen') {
        store.close();
        store = SegmentedClientStore.open(
          root,
          fixture.cache,
          publication: true,
          fault: hook,
        );
      }
      final expected = await store.recoverAcceptedGeneration();
      AuditTrace.phase = 'acquisition';
      final transport = FixtureTransport(fixture);
      final stage = await IncrementalFetcher(
        store,
        transport,
      ).acquire(verifiedBase: expected);
      final version = store.publicationDataVersion;
      AuditTrace.phase = 'verification';
      final proof = await store.verifyPublicationCandidate(
        stage.manifest,
        expected,
        verifiedDataVersion: version,
      );
      last = proof;
      AuditTrace.phase = 'preparation';
      prepared = store.prepareGeneration(
        syncUuid(),
        stage.stagingId,
        proof,
        expected,
        verifiedDataVersion: version,
      );
      if (action == 'prepare-only')
        return {'ok': true, 'prepared': true, 'events': AuditTrace.stop()};
      AuditTrace.phase = 'publication';
      if (action == 'fault-before') fault = 'before_publication_commit';
      if (action == 'fault-after') fault = 'during_publication_readback';
      if (action == 'crash-before') crash = 'before_publication_commit';
      if (action == 'crash-after') crash = 'after_publication_commit';
      final result = store.commitPreparedGeneration(
        prepared!,
        finalAuthorityFence: () {
          if (action == 'guard-fails')
            throw const SegmentedException('AUDIT_GUARD');
        },
      );
      fault = null;
      AuditTrace.phase = 'cleanup';
      store.discardUnacceptedGeneration(prepared!.id);
      final events = AuditTrace.stop();
      return {
        'ok': true,
        'sequence': result.sequence,
        'target': result.target.syncRoot,
        'idempotent': result.idempotent,
        'object_requests': transport.objectRequests,
        'payload_bytes': transport.payloadBytes,
        'latency_us': watch.elapsedMicroseconds,
        'events': events,
        'changed': proof.difference.changes
            .map(
              (c) => {
                'table': c.table,
                'key': c.key,
                'before': c.before,
                'after': c.after,
              },
            )
            .toList(),
        'graph_hashes': proof.graph.objects.map((r) => r.hash).toList(),
        'receipt': decodeC1(proof.receipt),
      };
    } on Object catch (error) {
      fault = null;
      final events = AuditTrace.stop();
      return {
        'ok': false,
        'error': error.toString(),
        'committed_error': error is PublicationCommittedException,
        'events': events,
        'latency_us': watch.elapsedMicroseconds,
      };
    }
  }

  stdout.writeln(jsonEncode({'ready': true, 'path': store.path}));
  await for (final line
      in stdin.transform(utf8.decoder).transform(const LineSplitter())) {
    final command = jsonDecode(line) as Map;
    if (command['action'] == 'exit') break;
    if (command['action'] == 'cleanup-stages') {
      final inspect = sqlite3.open(store.path);
      final ids = inspect
          .select('SELECT id FROM staging')
          .map((r) => r['id'] as String)
          .toList();
      inspect.close();
      for (final id in ids) {
        store.removeUnreferencedStagingData(id);
      }
      stdout.writeln(jsonEncode({'ok': true, 'removed': ids.length}));
    } else if (command['action'] == 'commit-pending') {
      try {
        final p = store.commitPreparedGeneration(
          prepared!,
          finalAuthorityFence: () {},
        );
        stdout.writeln(jsonEncode({'ok': true, 'sequence': p.sequence}));
      } on Object catch (error) {
        stdout.writeln(jsonEncode({'ok': false, 'error': error.toString()}));
      }
    } else if (command['action'] == 'verify-variant') {
      final fixture = GenerationFixture(
        jsonDecode(File(command['fixture'] as String).readAsStringSync())
            as Map<String, dynamic>,
      );
      final all = <String, List<int>>{
        for (final f in fixtures) ...f.objects,
        ...fixture.objects,
      };
      VerifiedObject read(ObjectRef r) => VerifiedObject.verify(
        all[r.hash] ?? (rejectSegment('OBJECT_MISSING')),
        r,
        fixture.cache,
      );
      final outcomes = <String, Object?>{};
      for (final incremental in [false, true]) {
        try {
          final proof = incremental
              ? await verifyIncrementalGeneration(
                  ObservationManifest.fromBytes(encodeC1(fixture.manifest)),
                  last!,
                  read,
                )
              : await verifyCompleteGeneration(
                  ObservationManifest.fromBytes(encodeC1(fixture.manifest)),
                  read,
                  base: last!.manifest,
                );
          outcomes[incremental ? 'incremental' : 'full'] = {
            'accepted': true,
            'target': proof.manifest.target.syncRoot,
          };
        } on Object catch (error) {
          outcomes[incremental ? 'incremental' : 'full'] = {
            'accepted': false,
            'error': error.toString(),
          };
        }
      }
      stdout.writeln(jsonEncode(outcomes));
    } else if (command['action'] == 'recover') {
      try {
        final a = await store.recoverAcceptedGeneration();
        stdout.writeln(
          jsonEncode({
            'ok': true,
            'sequence': a.sequence,
            'target': a.manifest?.target.syncRoot,
          }),
        );
      } on Object catch (error) {
        stdout.writeln(jsonEncode({'ok': false, 'error': error.toString()}));
      }
    } else if (command['action'] == 'scrub') {
      final h = store.inspectStoreHealth();
      stdout.writeln(jsonEncode({'healthy': h.healthy, 'issues': h.issues}));
    } else if (command['action'] == 'reopen-only') {
      store.close();
      try {
        store = SegmentedClientStore.open(
          root,
          fixtures.first.cache,
          publication: true,
          fault: hook,
        );
        final a = await store.recoverAcceptedGeneration();
        stdout.writeln(jsonEncode({'ok': true, 'sequence': a.sequence}));
      } on Object catch (error) {
        stdout.writeln(jsonEncode({'ok': false, 'error': error.toString()}));
      }
    } else {
      stdout.writeln(
        jsonEncode(
          await publish(command['target'] as int, command['action'] as String),
        ),
      );
    }
  }
  store.close();
}

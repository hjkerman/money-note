@Timeout(Duration(minutes: 8))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/e4_targeted_fixture.dart';
import 'support/logical_cost_files.dart';
import 'support/logical_cost_sqlite.dart';
import 'support/segmented_e2_fixture.dart';

class CountingEncoding extends Encoding {
  int calls = 0;
  @override
  String get name => 'utf-8';
  @override
  Converter<String, List<int>> get encoder => utf8.encoder;
  @override
  Converter<List<int>, String> get decoder => utf8.decoder;
  @override
  List<int> encode(String input) {
    calls++;
    return utf8.encode(input);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late BackendBridge bridge;
  late GenerationFixture fixture;
  late Map<String, dynamic> wire;
  setUpAll(() async {
    bridge = await BackendBridge.start(history: 4);
    fixture = GenerationFixture(bridge.fixture);
    wire = await e4WireOracle();
  });
  tearDownAll(() => bridge.dispose());

  test('file write span is encoded once, flushed and atomically renamed',
      () async {
    final root = Directory.systemTemp.createTempSync('mn-b03-files-');
    final c = LogicalCost(), s = SqlCosts(), encoding = CountingEncoding();
    final io = CostIo(root, s);
    try {
      await c.run(
          LogicalCostStage.calibration,
          () => io.run(() async {
                final candidate = File('${root.path}/baseline.json.prepared');
                await candidate.writeAsString('한😀',
                    encoding: encoding, flush: true);
                candidate.renameSync('${root.path}/baseline.json');
                final journal = File('${root.path}/journal.ndjson');
                journal.writeAsBytesSync([1, 2], flush: true);
                final raf = await journal.open(mode: FileMode.append);
                await raf.writeFrom([8, 3, 4, 9], 1, 3);
                await raf.flush();
                await raf.close();
              }));
      expect(encoding.calls, 1);
      expect(File('${root.path}/baseline.json').readAsBytesSync(),
          [237, 149, 156, 240, 159, 152, 128]);
      expect(
          File('${root.path}/journal.ndjson').readAsBytesSync(), [1, 2, 3, 4]);
      expect(
          s.values['calibration/file/baseline/submittedBytes'], BigInt.from(7));
      expect(
          s.values['calibration/file/baseline/completedBytes'], BigInt.from(7));
      expect(
          s.values['calibration/file/baseline/publishedRenames'], BigInt.one);
      expect(
          s.values['calibration/file/journal/completedBytes'], BigInt.from(4));
    } finally {
      root.deleteSync(recursive: true);
    }
  });

  test('file failures count actual attempts but never report completion',
      () async {
    final root = Directory.systemTemp.createTempSync('mn-b03-file-fail-');
    final c = LogicalCost(), s = SqlCosts(), io = CostIo(root, s);
    final file = File('${root.path}/baseline.json')
      ..writeAsBytesSync([255, 1, 2]);
    try {
      await c.run(
          LogicalCostStage.calibration,
          () => io.run(() async {
                final readOnly = File(file.path).openSync();
                expect(() => readOnly.writeFromSync([1, 2, 3, 4]),
                    throwsA(isA<FileSystemException>()));
                readOnly.closeSync();
                await expectLater(File(file.path).readAsString(),
                    throwsA(isA<FileSystemException>()));
              }));
      expect(
          s.values['calibration/file/baseline/submittedBytes'], BigInt.from(4));
      expect(s.values['calibration/file/baseline/completedBytes'], isNull);
      expect(s.values['calibration/file/baseline/decodeFailedSubmittedBytes'],
          BigInt.from(3));
      expect(file.readAsBytesSync(), [255, 1, 2]);
    } finally {
      root.deleteSync(recursive: true);
    }
  });

  test('closed SQL and file owner cannot contaminate a new run', () {
    final root = Directory.systemTemp.createTempSync('mn-b03-file-closed-');
    final a = LogicalCost(),
        b = LogicalCost(),
        s = SqlCosts(),
        io = CostIo(root, s);
    final db = CostDatabase(sqlite3.openInMemory(), s);
    try {
      a.run(
          LogicalCostStage.calibration,
          () => io.run(() {
                db.execute('CREATE TABLE objects(k TEXT,body BLOB)');
                db.execute("INSERT INTO objects VALUES ('a',x'01')");
                a.close();
                final before = s.snapshot();
                db.execute("INSERT INTO objects VALUES ('late',x'0203')");
                File('${root.path}/baseline.json').writeAsStringSync('late');
                expect(s.snapshot(), before);
                b.run(
                    LogicalCostStage.e1,
                    () => db
                        .execute("INSERT INTO objects VALUES ('b',x'040506')"));
              }));
      expect(s.forCollector(b).values['e1/objects/INSERT/blobBytes/committed'],
          BigInt.from(3));
    } finally {
      db.close();
      root.deleteSync(recursive: true);
    }
  });

  for (final phase in [
    'manifest',
    'objects',
    'terminal',
    'retry',
    'exhausted',
    'cancel'
  ]) {
    test(
        'actual acquisition accounting preserves $phase failure/reuse semantics',
        () async {
      final root = Directory.systemTemp.createTempSync('mn-b03-expiry-');
      final c = LogicalCost(), s = SqlCosts();
      final store = SegmentedClientStore.open(root, fixture.cache,
          acquisition: true,
          diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), s));
      final transport = FixtureTransport(fixture);
      var injected = 0;
      transport.before = (method, path, body) async {
        if (method != 'POST') return null;
        final match = phase == 'manifest' ||
                phase == 'retry' ||
                phase == 'exhausted' ||
                phase == 'cancel'
            ? path.endsWith('/observations')
            : phase == 'objects'
                ? path.endsWith('/objects')
                : path.endsWith('/observations') &&
                    transport.manifestRequests == 1;
        if (match && (injected == 0 || phase == 'exhausted')) {
          injected++;
          if (phase == 'cancel') rejectSegment('ACQUISITION_CANCELLED');
          return remoteError(
              phase == 'retry' ? 'ROOT_NOT_READY' : 'OBSERVATION_EXPIRED',
              phase == 'retry' ? 'retry_same' : 'new_observation',
              phase == 'retry' ? 503 : 410,
              body!['request_id'],
              retry: phase == 'retry' ? 1 : null);
        }
        return null;
      };
      final fetch = IncrementalFetcher(store, transport,
          delay: (_, c) async => c.check());
      try {
        if (phase == 'exhausted' || phase == 'cancel') {
          await expectLater(c.run(LogicalCostStage.e2, () => fetch.acquire()),
              throwsA(isA<AcquisitionFailure>()));
          expect(store.listStoredObjectIdentities(), isEmpty);
          if (phase == 'exhausted') expect(injected, 3);
        } else {
          final result =
              await c.run(LogicalCostStage.e2, () => fetch.acquire());
          expect(result.graph.objects.length, fixture.objects.length);
          expect(s.values['e2/objects/INSERT/effective/rows'],
              BigInt.from(fixture.objects.length));
          if (phase == 'terminal') {
            expect(result.metrics.cacheHits, fixture.objects.length);
          }
        }
        expect(c.snapshot().keys.any((k) => k.startsWith('e2/c1/')), true);
        expect(LogicalCost.activeCollector, isNull);
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }

  test(
      'real Frozen handoff, healthy reads and reopen fallback account without pin rewrites',
      () async {
    final h = await E4Harness.create(bridge, wire),
        c = LogicalCost(),
        s = SqlCosts(),
        files = SqlCosts();
    final io = CostIo(h.root, files);
    void reopen() {
      final cache = h.store.cache;
      h.store.close();
      h.store = SegmentedClientStore.open(h.root, cache,
          adapters: true,
          diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), s));
    }

    try {
      reopen();
      final pending = await h.workspace.beginOnlineWrite(1);
      final pendingBytes = h.pendingFile.readAsBytesSync();
      final result =
          await c.run(LogicalCostStage.e4Legacy, () => io.run(h.install));
      expect(result.pendingRemains, true);
      expect(
          (await h.workspace.loadPendingOnlineWrite(1))!.token, pending.token);
      expect(h.pendingFile.readAsBytesSync(), pendingBytes);
      final fingerprint = result.frozen.binding['legacy_fingerprint'];
      final before = h.store.work.snapshot();
      final frozen = result.frozen;
      final first = await c.run(
          LogicalCostStage.e4Read,
          () => io.run(
              () => h.workspace.readFrozenBaseline(h.store, frozen.id, 1)));
      for (var i = 0; i < 3; i++) {
        final b = await c.run(
            LogicalCostStage.e4Read,
            () => io.run(
                () => h.workspace.readFrozenBaseline(h.store, frozen.id, 1)));
        expect(b.serverStateFingerprint, first.serverStateFingerprint);
      }
      expect(h.store.work.since(before)['frozen_full_recoveries'] ?? 0, 0);
      expect(
          s.values.keys.where(
              (k) => k.startsWith('e4Read/') && k.contains('/effective/')),
          isEmpty);
      expect(
          files.values.keys.where(
              (k) => k.startsWith('e4Read/') && k.contains('completedBytes')),
          isEmpty);
      expect(files.values['e4Legacy/file/baseline/completedBytes'],
          BigInt.from(h.baselineFile.lengthSync()));
      expect(files.values['e4Legacy/file/source/publishedRenames'], isNotNull);
      expect(BigInt.parse(c.snapshot()['e4Legacy/lineageHash/hashInputBytes']!),
          greaterThan(BigInt.zero));
      expect(c.snapshot()['e4Read/lineageHash/calls'], isNull,
          reason: 'healthy provenance reuse must not repeat lineage hashing');
      final healthyWork = h.store.work.since(before);
      reopen();
      final workspace = E4Workspace(h.root);
      final recovered = await c.run(
          LogicalCostStage.recovery,
          () => io
              .run(() => workspace.readFrozenBaseline(h.store, frozen.id, 1)));
      expect(recovered.serverStateFingerprint, fingerprint);
      expect(h.pendingFile.readAsBytesSync(), pendingBytes);
      final direct = sqlite3.open(h.store.path);
      expect(direct.select('SELECT count(*) n FROM frozen').single['n'], 1);
      expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
      direct.close();
      expect(c.snapshot().keys.any((k) => k.startsWith('recovery/legacyHash/')),
          true);
      final oracle = await Process.run('python3', [
        '-c',
        'import json,sys; b=json.load(open(sys.argv[1])); '
            'print(len(json.dumps({"schema_version":1,"origin":"mobile-baseline-lineage","baseline":b}, '
            'sort_keys=True,ensure_ascii=False,separators=(",",":")).encode("utf-8")))',
        h.baselineFile.path
      ]);
      expect(oracle.exitCode, 0, reason: '${oracle.stderr}');
      final lineageBytes = BigInt.parse('${oracle.stdout}'.trim());
      expect(c.snapshot()['recovery/lineageHash/calls'], '2');
      expect(c.snapshot()['recovery/lineageHash/hashInputBytes'],
          (lineageBytes * BigInt.two).toString());
      final childInput = File('${h.root.path}/b03-frozen-input.json')
        ..writeAsStringSync(jsonEncode({
          'root': h.root.path,
          'target': frozen.target.toJson(),
          'origin': h.store.cache.origin,
          'frozen': frozen.id,
          'fingerprint': fingerprint
        }));
      final childOutput = '${h.root.path}/b03-frozen-output.json';
      final child = await Process.run('/home/hjkerman/.flutter/bin/flutter', [
        'test',
        '--no-pub',
        '--machine',
        '--dart-define=B03_FRESH_INPUT=${childInput.path}',
        '--dart-define=B03_FRESH_OUTPUT=$childOutput',
        '${Directory.current.parent.path}/docs/benchmarks/t66f-b03/fresh_frozen_test.dart'
      ]);
      expect(child.exitCode, 0,
          reason:
              '${child.stderr}\n${child.exitCode == 0 ? '' : '${child.stdout}'.split('\n').reversed.take(12).toList().reversed.join('\n')}');
      final fresh = jsonDecode(File(childOutput).readAsStringSync());
      expect(fresh['fingerprint'], fingerprint);
      expect(fresh['primitive']['recovery/lineageHash/calls'], '2');
      expect(fresh['primitive']['recovery/lineageHash/hashInputBytes'],
          (lineageBytes * BigInt.two).toString());
      expect(h.pendingFile.readAsBytesSync(), pendingBytes);
      const out = String.fromEnvironment('B03_OUTPUT');
      if (out.isNotEmpty) {
        File('$out-frozen.json').writeAsStringSync(jsonEncode({
          'schema_version': 1,
          'primitive': c.snapshot(),
          'sqlite': s.snapshot(),
          'files': files.snapshot(),
          'healthy_read_work': healthyWork,
          'pending_preserved': true,
          'fresh_process': fresh,
          'coverage':
              '실제 Frozen install/repeated/reopen fallback. file completed는 physical durability 아님'
        }));
      }
    } finally {
      h.dispose();
    }
  });
}

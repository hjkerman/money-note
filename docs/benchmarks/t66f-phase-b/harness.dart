import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/offline_mode_fixtures.dart';

class RealHttpOverrides extends HttpOverrides {}

class RealBackend {
  RealBackend._(
    this.process,
    this.lines,
    this.origin,
    this.token,
    this.fixture,
  );
  final Process? process;
  final StreamIterator<String>? lines;
  final String origin, token;
  final Map<String, dynamic> fixture;
  static RealBackend remote(Map<String, dynamic> value) => RealBackend._(
    null,
    null,
    value['origin'],
    value['token'],
    value['fixture'],
  );
  static String get repo => Directory.current.parent.path;
  static Future<RealBackend> start(int history) async {
    final p = await Process.start('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66f-phase-b/server.py',
      '$history',
    ]);
    final errors = StringBuffer();
    p.stderr.transform(utf8.decoder).listen(errors.write);
    final lines = StreamIterator(
      p.stdout.transform(utf8.decoder).transform(const LineSplitter()),
    );
    if (!await lines.moveNext().timeout(const Duration(minutes: 5))) {
      throw StateError('synthetic TLS startup failed: $errors');
    }
    final init = jsonDecode(lines.current);
    return RealBackend._(
      p,
      lines,
      init['origin'],
      init['token'],
      init['fixture'],
    );
  }

  Future<void> _tail = Future.value();
  Future<Map<String, dynamic>> command(Map<String, dynamic> input) {
    final done = Completer<Map<String, dynamic>>();
    _tail = _tail
        .then((_) async {
          process!.stdin.writeln(jsonEncode(input));
          if (!await lines!.moveNext())
            throw StateError('synthetic backend ended');
          return jsonDecode(lines!.current) as Map<String, dynamic>;
        })
        .then(done.complete, onError: done.completeError);
    return done.future;
  }

  Future<List<Map<String, dynamic>>> stats({bool reset = false}) async =>
      ((await command({'command': 'stats', 'reset': reset}))['records'] as List)
          .cast<Map<String, dynamic>>();
  Future<void> waitEntered() async {
    final watch = Stopwatch()..start();
    while (watch.elapsed < const Duration(seconds: 30)) {
      if ((await command({'command': 'entered'}))['entered'] == true) return;
      await Future<void>.delayed(const Duration(milliseconds: 5));
    }
    throw StateError('controlled HTTP barrier not reached');
  }

  Future<void> dispose() async {
    await command({'command': 'release'});
    await command({'command': 'exit'});
    await process!.stdin.close();
    expect(await process!.exitCode.timeout(const Duration(seconds: 30)), 0);
    await lines!.cancel();
  }
}

class RealHarness {
  RealHarness._(
    this.backend,
    this.root,
    this.store,
    this.workspace,
    this.io,
    this.api,
    this.state,
  );
  final RealBackend backend;
  final Directory root;
  SegmentedClientStore store;
  E4Workspace workspace;
  final IOClient io;
  final MoneyNoteApiClient api;
  final AppState state;
  File get source => File('${workspace.root.path}/e4-source.json');
  File get baseline =>
      File('${workspace.root.path}/offline-mode/baseline.json');
  File get pending =>
      File('${workspace.root.path}/offline-mode/online-write-1.json');
  static Future<RealHarness> create(
    RealBackend b, {
    void Function(String)? fault,
    StoreFault? sqlFault,
    E4Workspace Function(Directory)? workspaceFactory,
    SyncTarget? targetOverride,
  }) async {
    FlutterSecureStorage.setMockInitialValues({});
    final root = Directory.systemTemp.createTempSync('mn-phase-b-');
    final target =
        targetOverride ?? SyncTarget.parse(b.fixture['manifest']['target']);
    final store = SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(b.origin, target),
      adapters: true,
      fault: sqlFault,
    );
    final workspace =
        workspaceFactory?.call(root) ?? E4Workspace(root, fault: fault);
    final native = HttpOverrides.runWithHttpOverrides(
      () => HttpClient(),
      RealHttpOverrides(),
    )..maxConnectionsPerHost = 1;
    // 이 인증서 예외는 이 새 loopback 주소 하나에만 적용한다. 제품 TLS 설정은 변경하지 않는다.
    native.badCertificateCallback = (cert, host, port) =>
        host == '127.0.0.1' && port == Uri.parse(b.origin).port;
    final io = IOClient(native);
    final api = MoneyNoteApiClient(client: io, baseUrl: b.origin);
    await api.saveSession(b.token);
    final state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    return RealHarness._(b, root, store, workspace, io, api, state);
  }

  Map<String, dynamic> disk() {
    final db = sqlite3.open(store.path);
    try {
      expect(db.select('PRAGMA integrity_check').single.values.single, 'ok');
      expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      return {
        'source': source.existsSync()
            ? base64Encode(source.readAsBytesSync())
            : null,
        'B': baseline.existsSync()
            ? base64Encode(baseline.readAsBytesSync())
            : null,
        'pending': pending.existsSync()
            ? base64Encode(pending.readAsBytesSync())
            : null,
        for (final table in [
          'accepted',
          'installed',
          'frozen',
          'generation_roots',
        ])
          table: db
              .select('SELECT * FROM $table ORDER BY 1,2')
              .map(
                (r) => r.map(
                  (k, v) => MapEntry(k, v is List<int> ? localChecksum(v) : v),
                ),
              )
              .toList(),
      };
    } finally {
      db.close();
    }
  }

  Future<Map<String, dynamic>> inspect() async {
    final p = await Process.run('${RealBackend.repo}/.venv/bin/python', [
      '${RealBackend.repo}/docs/benchmarks/t66e4-audit/state_oracle.py',
      store.path,
      workspace.root.path,
    ]);
    if (p.exitCode != 0)
      throw StateError('independent persisted-state oracle: ${p.stderr}');
    return jsonDecode(p.stdout as String);
  }

  Future<Map<String, dynamic>> compareBackend() async {
    final expected = await backend.command({'command': 'oracle'});
    final accepted = store.acceptedGeneration();
    final actualHot = store.withInstalledRead(accepted, (r) => r.hot['state']);
    expect(actualHot, expected['expected_hot']);
    final proof = await store.verifyAcceptedForMaterialization(accepted);
    final bundle = store.withAcceptedRead(
      accepted,
      (r) => materializeLegacyRead(r, baselineFixture().user),
      materializationProof: proof,
    );
    expect(bundle.envelope.snapshot, expected['expected_snapshot']);
    expect(bundle.envelope.fingerprint, expected['expected_fingerprint']);
    expect(
      bundle.envelope.fingerprint,
      isNot(accepted.manifest!.target.syncRoot),
    );
    final expectedObjects = {
      for (final o in expected['objects'])
        o['ref']['hash'] as String: base64Decode(o['data_base64']),
    };
    final db = sqlite3.open(store.path);
    try {
      for (final e in expectedObjects.entries) {
        final row = db.select('SELECT body FROM objects WHERE hash=?', [
          e.key,
        ]).single;
        expect(
          row['body'],
          e.value,
          reason: 'actual HTTP → SQLite exact immutable bytes ${e.key}',
        );
      }
    } finally {
      db.close();
    }
    final inspected = await inspect();
    expect(
      (inspected['generations'][accepted.id]['closure'] as List).toSet(),
      expectedObjects.keys.toSet(),
    );
    return {
      'target': expected['manifest']['target'],
      'expected_objects': expectedObjects.length,
      'source_rows': {
        for (final e in (expected['source'] as Map).entries)
          e.key: (e.value as List).length,
      },
      'snapshot_fingerprint': expected['expected_fingerprint'],
      'persisted': inspected,
    };
  }

  Future<Map<String, dynamic>> freshRead(
    String? frozen, {
    bool recover = true,
  }) async {
    final input = File('${root.path}/fresh-input.json')
      ..writeAsStringSync(
        jsonEncode({
          'root': root.path,
          'target': store.acceptedGeneration().manifest!.target.toJson(),
          'origin': backend.origin,
          'frozen': frozen,
          'recover': recover,
        }),
      );
    final output = '${root.path}/fresh-output.json';
    final p = await Process.run('/home/hjkerman/.flutter/bin/flutter', [
      'test',
      '--no-pub',
      '--machine',
      '--dart-define=F_REOPEN=${input.path}',
      '--dart-define=F_REOPEN_OUTPUT=$output',
      '${RealBackend.repo}/docs/benchmarks/t66f-phase-b/fresh_test.dart',
    ], workingDirectory: Directory.current.path);
    if (p.exitCode != 0)
      throw StateError(
        'fresh process failed: ${(p.stdout as String).split('\n').reversed.take(8).toList()}',
      );
    return jsonDecode(File(output).readAsStringSync());
  }

  void reopen() {
    final cache = store.cache;
    store.close();
    store = SegmentedClientStore.open(root, cache, adapters: true);
    workspace = E4Workspace(root);
  }

  void dispose() {
    state.dispose();
    store.close();
    io.close();
    root.deleteSync(recursive: true);
  }
}

@Timeout(Duration(minutes: 20))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/money.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/api_transport.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import 'harness.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';

class DelayedRecoveryWorkspace extends E4Workspace {
  DelayedRecoveryWorkspace(super.root, {super.fault});
  bool pause = false;
  final entered = Completer<void>(), release = Completer<void>();
  @override
  Future<OfflineWorkspaceMetadata> loadMetadata() async {
    if (pause) {
      pause = false;
      entered.complete();
      await release.future;
    }
    return super.loadMetadata();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late RealBackend backend;
  final evidence = <Map<String, dynamic>>[];
  setUpAll(() async {
    backend = await RealBackend.start(9);
  });
  setUp(() async {
    // 거부된 미파싱 manifest는 lease ID를 알 수 없다. 규범 TTL로 다음 독립 case를 분리한다.
    await backend.command({'command': 'advance', 'seconds': 901});
  });
  tearDownAll(() async {
    const out = String.fromEnvironment('F_PHASE_B_OUTPUT');
    if (out.isNotEmpty) File(out).writeAsStringSync(jsonEncode(evidence));
    await backend.dispose();
  });
  void record(String id, Map<String, dynamic> value) =>
      evidence.add({'id': id, ...value});
  void noAuthority(Map<String, dynamic> disk) {
    final pointer = (disk['accepted'] as List).single;
    expect(pointer['current_id'], isNull);
    expect(pointer['previous_id'], isNull);
    expect(pointer['sequence'], 0);
    for (final t in ['installed', 'frozen']) expect(disk[t], isEmpty);
  }

  Future<Object?> outcome(Future<dynamic> f) =>
      f.then<Object?>((_) => null, onError: (Object e) => e);
  List<Map<String, dynamic>> objects(List<Map<String, dynamic>> rows) =>
      rows.where((r) => (r['path'] as String).endsWith('/objects')).toList();

  test(
    'FB01 real TLS cold → identical → localized → split → delete → later delta',
    () async {
      final h = await RealHarness.create(backend);
      final phases = <Map<String, dynamic>>[];
      Set<String> prior = {};
      try {
        for (final phase in [
          'cold',
          'identical',
          'localized',
          'several',
          'split',
          'delete',
          'after_large',
        ]) {
          if (phase == 'localized' || phase == 'after_large') {
            await backend.command({
              'command': 'mutate',
              'title': '원문 변경 $phase',
            });
          } else if (phase == 'several') {
            for (final id in [1000, 1003, 1007]) {
              await backend.command({
                'command': 'mutate',
                'id': id,
                'title': '다중 $id',
              });
            }
          } else if (phase == 'split') {
            await backend.command({
              'command': 'mutate',
              'op': 'insert',
              'count': 260,
            });
          } else if (phase == 'delete') {
            await backend.command({
              'command': 'mutate',
              'op': 'delete',
              'id': 1001,
            });
          }
          await backend.stats(reset: true);
          await h.state.refreshSegmentedForIsolatedUse(h.store);
          final wire = await backend.stats();
          final oracle = await h.compareBackend();
          final closure =
              ((oracle['persisted']['generations'][h.store
                          .acceptedGeneration()
                          .id]['closure'])
                      as List)
                  .cast<String>()
                  .toSet();
          final requested = {
            for (final r in objects(wire))
              ...((r['objects'] as List).cast<String>()),
          };
          expect(
            requested,
            closure.difference(prior),
            reason: 'independent backend graph delta versus real D3 payload request set',
          );
          if (phase == 'identical') expect(objects(wire), isEmpty);
          final db = sqlite3.open(h.store.path);
          final money = <String>[];
          try {
            for (final row in db.select(
              "SELECT body FROM objects WHERE kind='snapshot-leaf'",
            )) {
              final b = jsonDecode(utf8.decode(row['body'] as List<int>));
              if (b['table'] == 'app_settings') {
                money.addAll([
                  for (final r in b['rows'])
                    if (r['value']['key'] == 'cash_flow_balance')
                      r['value']['value'] as String,
                ]);
              }
            }
          } finally {
            db.close();
          }
          expect(money, contains('\u001c+0001000.00\u001f'));
          phases.add({
            'phase': phase,
            'wire': wire,
            'oracle': oracle,
            'new_objects': requested.length,
            'reused_objects': closure.intersection(prior).length,
          });
          prior = closure;
        }
        final fresh = await h.freshRead(null);
        expect(fresh['accepted'], h.store.acceptedGeneration().id);
        record('FB01', {'phases': phases, 'fresh': fresh});
      } finally {
        h.dispose();
        await backend.command({'command': 'mutate', 'op': 'delete_added'});
      }
    },
  );

  test('FB02 real legacy handoff preserves backend v7 identity and unknown pending', () async {
    final h = await RealHarness.create(backend);
    try {
      await h.workspace.beginOnlineWrite(1);
      final pending = h.pending.readAsBytesSync();
      final installed = await h.state.installSegmentedLegacyForIsolatedUse(
        h.store,
      );
      expect(h.pending.readAsBytesSync(), pending);
      final oracle = await h.compareBackend();
      final b = await h.workspace.readFrozenBaseline(
        h.store,
        installed.frozen.id,
        1,
      );
      expect(b.serverStateFingerprint, oracle['snapshot_fingerprint']);
      final fresh = await h.freshRead(installed.frozen.id);
      expect(fresh['frozen_fingerprint'], b.serverStateFingerprint);
      record('FB02', {
        'oracle': oracle,
        'fresh': fresh,
        'pending_sha256': localChecksum(pending),
        'pending_after_sha256': localChecksum(h.pending.readAsBytesSync()),
        'disk': h.disk(),
      });
    } finally {
      h.dispose();
    }
  });

  test(
    'FB03 Frozen G1 survives real G2 publication and native source switch',
    () async {
      final h = await RealHarness.create(backend);
      try {
        final initial = await h.state.installSegmentedLegacyForIsolatedUse(
          h.store,
        );
        final before = h.disk();
        await backend.command({
          'command': 'mutate',
          'title': 'F는 G1, native는 G2',
        });
        await h.state.refreshSegmentedForIsolatedUse(h.store);
        expect(
          h.store.acceptedGeneration().id,
          isNot(initial.publication.generationId),
        );
        final b = await h.workspace.readFrozenBaseline(
          h.store,
          initial.frozen.id,
          1,
        );
        expect(h.disk()['B'], before['B']);
        expect(h.disk()['frozen'], before['frozen']);
        final fresh = await h.freshRead(initial.frozen.id);
        expect(fresh['frozen_fingerprint'], b.serverStateFingerprint);
        record('FB03', {
          'before': before,
          'after': h.disk(),
          'fresh': fresh,
          'oracle': await h.inspect(),
        });
      } finally {
        h.dispose();
      }
    },
  );

  test(
    'FB04 RA01 required predecessor rejection preserves a valid Frozen source',
    () async {
      final h = await RealHarness.create(backend);
      try {
        final f = (await h.state.installSegmentedLegacyForIsolatedUse(h.store))
            .frozen;
        await h.state.refreshSegmentedForIsolatedUse(h.store);
        await h.workspace.beginOnlineWrite(1);
        await backend.command({
          'command': 'mutate',
          'title': '미설치 target provenance',
        });
        await h.state.publishSegmentedForIsolatedUse(h.store);
        final accepted = h.store.acceptedGeneration();
        // 실제 미완료 native preparation을 만든 뒤 rollback hint만 손실시킨다.
        final prepared = Map<String, dynamic>.from(
          h.workspace.prepareSegmentedSource(h.store, accepted, () {}),
        );
        expect(prepared['legacy_frozen'], isNotNull);
        prepared['previous_source'] = null;
        h.source.writeAsStringSync(jsonEncode(prepared), flush: true);
        final before = h.disk();
        final error = await outcome(
          h.state.refreshSegmentedForIsolatedUse(h.store),
        );
        expect(
          error,
          isA<SegmentedException>().having(
            (e) => e.code,
            'code',
            'SOURCE_PROVENANCE_REQUIRED',
          ),
        );
        expect(h.disk(), before);
        final b = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
        // 이미 preparation의 복구 증거를 시험이 지웠으므로 자동 repair는 요구하지 않는다.
        // 별도 새 process의 명시적 검증된 Frozen read만 확인한다.
        final fresh = await h.freshRead(f.id, recover: false);
        expect(fresh['frozen_fingerprint'], b.serverStateFingerprint);
        record('FB04', {
          'error': '$error',
          'before': before,
          'after': h.disk(),
          'fresh': fresh,
        });
      } finally {
        h.dispose();
      }
    },
  );

  test(
    'FB05 A01 delayed canceled real acquisition recovery cannot revert B',
    () async {
      late DelayedRecoveryWorkspace workspace;
      var failOlder = false;
      final cancel = SyncCancellation();
      final h = await RealHarness.create(
        backend,
        workspaceFactory: (root) => workspace = DelayedRecoveryWorkspace(
          root,
          fault: (p) {
            if (failOlder && p == 'before_legacy_rename') {
              failOlder = false;
              workspace.pause = true;
              cancel.cancel();
            }
          },
        ),
      );
      try {
        await h.state.installSegmentedLegacyForIsolatedUse(h.store);
        await workspace.beginOnlineWrite(1);
        failOlder = true;
        final older = outcome(
          h.state.installSegmentedLegacyForIsolatedUse(
            h.store,
            cancellation: cancel,
          ),
        );
        await workspace.entered.future.timeout(const Duration(seconds: 90));
        await backend.command({'command': 'mutate', 'title': '정상 newer B'});
        final newer = await h.state.installSegmentedLegacyForIsolatedUse(
          h.store,
        );
        final before = h.disk();
        workspace.release.complete();
        expect(await older, isNotNull);
        expect(h.disk(), before);
        final b = await workspace.readFrozenBaseline(
          h.store,
          newer.frozen.id,
          1,
        );
        final fresh = await h.freshRead(newer.frozen.id);
        expect(fresh['frozen_fingerprint'], b.serverStateFingerprint);
        record('FB05', {
          'before_delayed_recovery': before,
          'after_delayed_recovery': h.disk(),
          'fresh': fresh,
          'oracle': await h.inspect(),
        });
      } finally {
        if (!workspace.release.isCompleted) workspace.release.complete();
        h.dispose();
      }
    },
  );

  for (final mode in [
    'wrong_principal',
    'wrong_epoch',
    'unsupported',
    'wrong_root',
    'malformed',
    'bad_object',
    'wrong_object',
    'wrong_observation',
  ]) {
    test(
      'FB-N-$mode real wire injection cannot produce accepted or installed authority',
      () async {
        final h = await RealHarness.create(backend);
        try {
          final atObjects = [
            'bad_object',
            'wrong_object',
            'wrong_observation',
          ].contains(mode);
          await backend.command({
            'command': 'fault',
            'mode': mode,
            'path': atObjects ? '/objects' : '/observations',
          });
          final error = await outcome(
            h.state.refreshSegmentedForIsolatedUse(h.store),
          );
          expect(error, isNotNull);
          final after = h.disk();
          noAuthority(after);
          expect(after['source'], isNull);
          // 동일 IOClient가 다음 정상 관측/객체 전송에도 사용된다.
          await h.state.refreshSegmentedForIsolatedUse(h.store);
          final oracle = await h.compareBackend();
          record('FB-N-$mode', {
            'error': '$error',
            'rejected_state': after,
            'followup': oracle,
          });
        } finally {
          h.dispose();
        }
      },
    );
  }

  for (final change in [
    'credential',
    'logout',
    'offline',
    'newer_legacy',
    'cancel',
  ]) {
    test(
      'FB-A-$change original-ticket rejection during actual object response',
      () async {
        final h = await RealHarness.create(backend);
        final cancel = SyncCancellation();
        try {
          await backend.command({'command': 'pause', 'path': '/objects'});
          final inFlight = outcome(
            h.state.refreshSegmentedForIsolatedUse(
              h.store,
              cancellation: cancel,
            ),
          );
          await backend.waitEntered();
          if (change == 'credential') {
            await h.api.saveSession('${backend.token}-replacement');
          } else if (change == 'logout') {
            await h.state.logout();
          } else if (change == 'offline') {
            h.state.connectivityMode = ConnectivityMode.offline;
          } else if (change == 'newer_legacy') {
            await outcome(h.state.refresh());
          } else {
            cancel.cancel();
          }
          await backend.command({'command': 'release'});
          expect(await inFlight, isNotNull);
          final disk = h.disk();
          noAuthority(disk);
          expect(disk['source'], isNull);
          record('FB-A-$change', {'rejected_state': disk});
        } finally {
          await backend.command({'command': 'release'});
          h.dispose();
        }
      },
    );
  }

  test(
    'FB06 partial real transfer canceled then resumed with fresh authorization',
    () async {
      final h = await RealHarness.create(backend);
      try {
        final cancel = SyncCancellation();
        await backend.command({
          'command': 'pause',
          'path': '/objects',
          'skip': 4,
        });
        final failed = outcome(
          h.state.refreshSegmentedForIsolatedUse(h.store, cancellation: cancel),
        );
        await backend.waitEntered();
        cancel.cancel();
        await backend.command({'command': 'release'});
        expect(await failed, isNotNull);
        final before = h.disk();
        noAuthority(before);
        final db = sqlite3.open(h.store.path);
        late Set<String> cached;
        try {
          cached = db
              .select('SELECT hash FROM objects')
              .map((r) => r['hash'] as String)
              .toSet();
        } finally {
          db.close();
        }
        expect(cached.length, 4);
        h.reopen();
        final state = AppState(h.api, offlineStore: h.workspace)
          ..user = baselineFixture().user;
        try {
          await backend.stats(reset: true);
          await state.refreshSegmentedForIsolatedUse(h.store);
          final wire = await backend.stats(), oracle = await h.compareBackend();
          final closure =
              (oracle['persisted']['generations'][h.store
                          .acceptedGeneration()
                          .id]['closure']
                      as List)
                  .cast<String>()
                  .toSet();
          final requested = {
            for (final response in wire)
              ...((response['objects'] as List).cast<String>()),
          };
          expect(requested, closure.difference(cached));
          record('FB06', {
            'before': before,
            'verified_objects_before_resume': cached.toList(),
            'wire': wire,
            'after': oracle,
          });
        } finally {
          state.dispose();
        }
      } finally {
        h.dispose();
      }
    },
  );

  test(
    'FB07 current logical read scope excludes concurrent writer commit',
    () async {
      final h = await RealHarness.create(backend);
      try {
        await h.state.refreshSegmentedForIsolatedUse(h.store);
        final g1 = h.store.acceptedGeneration();
        final sql = sqlite3.open(h.store.path)
          ..execute('PRAGMA busy_timeout=1');
        late List<Map<String, dynamic>> rows;
        try {
          h.store.withInstalledRead(g1, (read) {
            final one = read.rows('ledger_entries', limit: 1);
            sql.execute('BEGIN IMMEDIATE');
            // benign metadata update establishes a real competing write.
            sql.execute('UPDATE accepted SET sequence=sequence');
            expect(
              () => sql.execute('COMMIT'),
              throwsA(isA<SqliteException>()),
            );
            sql.execute('ROLLBACK');
            rows = read.rows('ledger_entries', limit: 10);
            expect(rows.first, one.first);
          });
        } finally {
          sql.close();
        }
        await backend.command({'command': 'mutate', 'title': '다음 read는 G2'});
        await h.state.refreshSegmentedForIsolatedUse(h.store);
        final g2 = h.store.acceptedGeneration();
        expect(g2.id, isNot(g1.id));
        record('FB07', {
          'G1': g1.id,
          'G2': g2.id,
          'g1_page_rows': rows,
          'oracle': await h.compareBackend(),
        });
      } finally {
        h.dispose();
      }
    },
  );

  test('FB08 P0 raw admission and R1 activation remain distinct from installed sync', () async {
    final h = await RealHarness.create(backend);
    try {
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      final oracle = await h.compareBackend();
      expect(
        () => exactMoney('\u001c+0001000.00\u001f'),
        throwsA(isA<FormatException>()),
      );
      expect(
        () => requireSegmentedOfflineRecovery(),
        throwsA(
          isA<SegmentedException>().having(
            (e) => e.code,
            'code',
            'R1_RECOVERY_CONTRACT_REQUIRED',
          ),
        ),
      );
      record('FB08', {
        'oracle': oracle,
        'r1_gate': 'CLOSED',
        'raw': '\u001c+0001000.00\u001f',
      });
    } finally {
      h.dispose();
    }
  });

  test('FB09 real backend header rejection releases six TCP responses with pool limit one', () async {
    final h = await RealHarness.create(backend);
    int clientSockets() {
      final inodes = <String>{};
      for (final fd in Directory('/proc/self/fd').listSync()) {
        try {
          final target = Link(fd.path).targetSync();
          if (target.startsWith('socket:['))
            inodes.add(target.substring(8, target.length - 1));
        } on FileSystemException {
          /* FD가 관측 사이 닫힐 수 있다. */
        }
      }
      final port = Uri.parse(backend.origin).port
          .toRadixString(16)
          .toUpperCase()
          .padLeft(4, '0');
      return File('/proc/net/tcp').readAsLinesSync().skip(1).where((line) {
        final columns = line.trim().split(RegExp(r'\s+'));
        return columns[2].endsWith(':$port') && inodes.contains(columns[9]);
      }).length;
    }

    try {
      final resources = <int>[], errors = <String>[], timings = <int>[];
      for (var i = 0; i < 6; i++) {
        await backend.command({
          'command': 'fault',
          'mode': 'oversized',
          'path': '/objects',
        });
        final elapsed = Stopwatch()..start();
        final error = await outcome(
          h.state.refreshSegmentedForIsolatedUse(h.store),
        );
        elapsed.stop();
        expect(
          error,
          isA<AcquisitionFailure>().having(
            (e) => e.code,
            'code',
            'RESPONSE_SIZE_EXCEEDED',
          ),
        );
        resources.add(clientSockets());
        errors.add('$error');
        timings.add(elapsed.elapsedMilliseconds);
        // E2는 header 거부 socket을 폐기한 뒤 같은 client로 lease DELETE를 한다.
        // 그 204 응답의 idle pooled socket 한 개는 정상이다.
        expect(resources.last, lessThanOrEqualTo(1));
        expect(elapsed.elapsed, lessThan(const Duration(seconds: 5)));
      }
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      final oracle = await h.compareBackend();
      expect(clientSockets(), 1); // 성공 응답의 reusable idle pool socket은 정상이다.
      record('FB09', {
        'six_client_tcp_fds': resources,
        'errors': errors,
        'rejection_ms': timings,
        'valid_followup_idle_tcp': clientSockets(),
        'oracle': oracle,
      });
    } finally {
      h.dispose();
    }
  });

  test('FB10 empty financial tables traverse all certified empty roots over real TLS', () async {
    final b = await RealBackend.start(-1);
    final h = await RealHarness.create(b);
    try {
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      final oracle = await h.compareBackend();
      for (final table in [
        'ledger_entries',
        'cash_flows',
        'monthly_panels',
        'card_payment_events',
        'card_payment_allocations',
      ]) {
        expect(oracle['source_rows'][table], 0);
      }
      record('FB10', {'oracle': oracle, 'wire': await b.stats()});
    } finally {
      h.dispose();
      await b.dispose();
    }
  });

  for (final churn in [false, true]) {
    test(
      'FB11-$churn real mid-transfer expiry reacquires an authorized complete generation',
      () async {
        final h = await RealHarness.create(backend);
        try {
          await backend.stats(reset: true);
          await backend.command({'command': 'pause', 'path': '/objects'});
          final inFlight = outcome(
            h.state.refreshSegmentedForIsolatedUse(h.store),
          );
          await backend.waitEntered();
          if (churn)
            await backend.command({
              'command': 'mutate',
              'title': 'lease 중 새 generation',
            });
          await backend.command({'command': 'advance', 'seconds': 901});
          await backend.command({'command': 'release'});
          expect(await inFlight, isNull);
          final wire = await backend.stats();
          expect(wire.any((r) => r['status'] == 410), true);
          final oracle = await h.compareBackend();
          record('FB11-$churn', {
            'wire': wire,
            'oracle': oracle,
            'persisted': h.disk(),
          });
        } finally {
          await backend.command({'command': 'release'});
          h.dispose();
        }
      },
    );
  }

  test('FB12 credential transition after real E3 acceptance cannot install over valid Frozen B', () async {
    late RealHarness h;
    var armed = false;
    h = await RealHarness.create(
      backend,
      fault: (point) {
        if (armed && point == 'after_e3_acceptance') {
          armed = false;
          unawaited(h.api.saveSession('${backend.token}-replacement'));
        }
      },
    );
    try {
      final f = (await h.state.installSegmentedLegacyForIsolatedUse(h.store))
          .frozen;
      await h.workspace.beginOnlineWrite(1);
      final before = h.disk();
      await backend.command({
        'command': 'mutate',
        'title': 'accepted cache와 설치 권한 분리',
      });
      armed = true;
      final error = await outcome(
        h.state.refreshSegmentedForIsolatedUse(h.store),
      );
      expect(error, isNotNull);
      final after = h.disk();
      for (final k in ['B', 'pending', 'frozen', 'source', 'installed'])
        expect(after[k], before[k]);
      expect(
        after['accepted'],
        isNot(before['accepted']),
      ); // old session의 complete cache 허용, 설치는 금지.
      await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      record('FB12', {
        'error': '$error',
        'before': before,
        'after': after,
        'fresh': await h.freshRead(f.id),
        'oracle': await h.inspect(),
      });
    } finally {
      h.dispose();
    }
  });

  test('FB13 real capability response keeps R1 support unavailable', () async {
    final h = await RealHarness.create(backend);
    try {
      final response = await h.io.get(
        Uri.parse('${backend.origin}/api/sync/v1/capabilities'),
      );
      expect(response.statusCode, 404);
      expect(response.headers['cache-control'], 'no-store');
      noAuthority(h.disk());
      record('FB13', {
        'status': response.statusCode,
        'headers': response.headers,
        'body_bytes': response.bodyBytes.length,
      });
    } finally {
      h.dispose();
    }
  });

  test('FB14 actual authenticated other principal cannot enter principal-one cache or installation', () async {
    final h = await RealHarness.create(backend);
    try {
      await h.workspace.beginOnlineWrite(1);
      final before = h.disk();
      final other = await backend.command({'command': 'other_principal'});
      await h.api.saveSession(other['token']);
      final error = await outcome(
        h.state.refreshSegmentedForIsolatedUse(h.store),
      );
      expect(error, isNotNull);
      final after = h.disk();
      for (final key in [
        'accepted',
        'installed',
        'frozen',
        'source',
        'B',
        'pending',
      ])
        expect(after[key], before[key]);
      await h.api.saveSession(backend.token);
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      record('FB14', {
        'error': '$error',
        'before': before,
        'rejected_state': after,
        'correct_principal': await h.compareBackend(),
      });
    } finally {
      h.dispose();
    }
  });

  test('FB15 schema trigger loss cannot bypass E1 through a real cached E4 refresh', () async {
    final h = await RealHarness.create(backend);
    String? trigger;
    try {
      final f = (await h.state.installSegmentedLegacyForIsolatedUse(h.store))
          .frozen;
      await h.workspace.beginOnlineWrite(1);
      final before = h.disk();
      final db = sqlite3.open(h.store.path);
      try {
        trigger =
            db
                    .select(
                      "SELECT sql FROM sqlite_master WHERE type='trigger' AND name='object_usage'",
                    )
                    .single['sql']
                as String;
        db.execute('DROP TRIGGER object_usage');
      } finally {
        db.close();
      }
      await backend.command({
        'command': 'mutate',
        'title': 'schema fence actual refresh',
      });
      final error = await outcome(
        h.state.refreshSegmentedForIsolatedUse(h.store),
      );
      expect(error, isNotNull);
      expect(h.disk(), before);
      final restore = sqlite3.open(h.store.path);
      try {
        restore.execute(trigger);
      } finally {
        restore.close();
      }
      trigger = null;
      await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      record('FB15', {
        'error': '$error',
        'before': before,
        'after': h.disk(),
        'fresh': await h.freshRead(f.id),
      });
    } finally {
      if (trigger != null) {
        final db = sqlite3.open(h.store.path);
        try {
          db.execute(trigger);
        } finally {
          db.close();
        }
      }
      h.dispose();
    }
  });

  test('FB16 object quota failure preserves prior valid Frozen source and unknown pending', () async {
    final h = await RealHarness.create(backend);
    try {
      final f = (await h.state.installSegmentedLegacyForIsolatedUse(h.store))
          .frozen;
      await h.workspace.beginOnlineWrite(1);
      final before = h.disk();
      final db = sqlite3.open(h.store.path);
      final count =
          db.select('SELECT count(*) AS n FROM objects').single['n'] as int;
      db.close();
      final cache = h.store.cache;
      h.store.close();
      h.store = SegmentedClientStore.open(
        h.root,
        cache,
        adapters: true,
        limits: ClientStoreLimits(objectCount: count),
      );
      await backend.command({
        'command': 'mutate',
        'title': '새 immutable bytes는 quota를 넘는다',
      });
      final error = await outcome(
        h.state.refreshSegmentedForIsolatedUse(h.store),
      );
      expect(error, isNotNull);
      final after = h.disk();
      for (final k in [
        'accepted',
        'installed',
        'frozen',
        'generation_roots',
        'source',
        'B',
        'pending',
      ])
        expect(after[k], before[k]);
      final check = sqlite3.open(h.store.path);
      try {
        expect(
          check.select('SELECT count(*) AS n FROM objects').single['n'],
          count,
        );
      } finally {
        check.close();
      }
      await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      record('FB16', {
        'error': '$error',
        'before': before,
        'after': after,
        'objects_before': count,
        'fresh': await h.freshRead(f.id),
      });
    } finally {
      h.dispose();
    }
  });

  test('FB17 matching server content never acknowledges or rebases ordered Frozen J inputs', () async {
    final h = await RealHarness.create(backend);
    try {
      final f = (await h.state.installSegmentedLegacyForIsolatedUse(h.store))
          .frozen;
      final baseline = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      final row = h.store.withFrozenRead(
        f,
        (r) => r.rows('ledger_entries').singleWhere((v) => v['id'] == 100),
      );
      final lineage = h.workspace.recoveryLineageFingerprint(baseline);
      await h.workspace.saveMetadata(
        OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          baselineLineageFingerprint: lineage,
        ),
      );
      final operations = [];
      for (var i = 0; i < 2; i++) {
        operations.add(
          await h.workspace.appendOperation(
            type: OfflineOperationType.createCardExpense,
            baseline: baseline,
            payload: {
              'entry_date': row['entry_date'],
              'title': row['title'],
              'amount_value': '+0001200.00',
              'spending_category': 'general',
              'discount_enabled': false,
            },
          ),
        );
      }
      final journal = File(
        '${h.workspace.root.path}/offline-mode/journal.ndjson',
      );
      final bytes = journal.readAsBytesSync(), before = h.disk();
      h.state.connectivityMode = ConnectivityMode.offline;
      // 명시적 nonpublishing E2 테스트 호출. normal OFFLINE 경로는 이 호출을 하지 않는다.
      final staged = await IncrementalFetcher(
        h.store,
        segmentedTransportForApi(h.api),
      ).acquire(verifiedBase: h.store.acceptedGeneration());
      final error = await outcome(
        h.state.refreshSegmentedForIsolatedUse(h.store),
      );
      expect(error, isNotNull);
      expect(h.disk(), before);
      expect(journal.readAsBytesSync(), bytes);
      final loaded = await h.workspace.loadJournal();
      expect(
        loaded.map((o) => o.operationId).toList(),
        operations.map((o) => o.operationId).toList(),
      );
      expect(loaded.map((o) => o.sequence).toList(), [1, 2]);
      expect(loaded.map((o) => o.payload['amount_value']).toList(), [
        '+0001200.00',
        '+0001200.00',
      ]);
      final after = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      expect(h.workspace.recoveryLineageFingerprint(after), lineage);
      record('FB17', {
        'original_lineage': lineage,
        'journal_sha256': localChecksum(bytes),
        'journal_after_sha256': localChecksum(journal.readAsBytesSync()),
        'operation_ids': loaded.map((o) => o.operationId).toList(),
        'sequences': [1, 2],
        'staging_id': staged.stagingId,
        'before': before,
        'after': h.disk(),
        'fresh': await h.freshRead(f.id),
      });
    } finally {
      h.dispose();
    }
  });
  test('FB18 actual truncated object response retries boundedly and stores only complete bytes', () async {
    final h = await RealHarness.create(backend);
    try {
      await backend.stats(reset: true);
      await backend.command({
        'command': 'fault',
        'mode': 'truncated',
        'path': '/objects',
      });
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      final wire = await backend.stats(), oracle = await h.compareBackend();
      final requests = wire
          .where((r) => (r['path'] as String).endsWith('/objects'))
          .toList();
      final counts = <String, int>{};
      for (final r in requests) {
        for (final hash in r['objects']) {
          counts[hash] = (counts[hash] ?? 0) + 1;
        }
      }
      expect(requests.length, oracle['expected_objects'] + 1);
      expect(counts.values.where((v) => v == 2).length, 1);
      expect(counts.values.every((v) => v <= 2), true);
      expect(wire.where((r) => r['injected'] == 'truncated').length, 1);
      record('FB18', {'wire': wire, 'oracle': oracle});
    } finally {
      h.dispose();
    }
  });

  test('FB19 real backend epoch rotation rejects new-context installation and preserves old Frozen B', () async {
    final b = await RealBackend.start(2);
    final h = await RealHarness.create(b);
    try {
      final f = (await h.state.installSegmentedLegacyForIsolatedUse(h.store))
          .frozen;
      await h.workspace.beginOnlineWrite(1);
      final before = h.disk();
      final url = Uri.parse('${b.origin}/api/sync/v1/observations');
      final headers = {
        'Authorization': 'Bearer ${b.token}',
        'Content-Type': 'application/json',
      };
      final oldResponse = await h.io.post(
        url,
        headers: headers,
        body: jsonEncode({
          'protocol': 1,
          'request_id': syncUuid(),
          'base': null,
          'inline_bytes': 0,
        }),
      );
      expect(oldResponse.statusCode, 201);
      final old = jsonDecode(oldResponse.body);
      await b.command({'command': 'rotate_epoch'});
      final expired = await h.io.post(
        Uri.parse(
          '${b.origin}/api/sync/v1/observations/${old['observation_id']}/objects',
        ),
        headers: headers,
        body: jsonEncode({
          'protocol': 1,
          'request_id': syncUuid(),
          'items': [
            {
              'path': [old['target']['raw_ref']['hash']],
              'offset': '0',
              'length': 1,
            },
          ],
        }),
      );
      // process restart가 아닌 명시 epoch 전환: §17의 EPOCH_CHANGED 분기다.
      expect(expired.statusCode, 409);
      expect(jsonDecode(expired.body)['error']['code'], 'EPOCH_CHANGED');
      expect(jsonDecode(expired.body)['error']['action'], 'full_resync');
      final error = await outcome(
        h.state.refreshSegmentedForIsolatedUse(h.store),
      );
      expect(error, isNotNull);
      expect(h.disk(), before);
      await h.workspace.readFrozenBaseline(h.store, f.id, 1);
      final current = await b.command({'command': 'oracle'});
      final newStore = await RealHarness.create(
        b,
        targetOverride: SyncTarget.parse(current['manifest']['target']),
      );
      late Map<String, dynamic> newOracle;
      try {
        await newStore.state.refreshSegmentedForIsolatedUse(newStore.store);
        newOracle = await newStore.compareBackend();
        expect(
          newOracle['snapshot_fingerprint'],
          f.binding['legacy_fingerprint'],
        );
        expect(
          newOracle['target']['ns']['epoch'],
          isNot(old['target']['ns']['epoch']),
        );
      } finally {
        newStore.dispose();
      }
      expect(h.disk(), before);
      record('FB19', {
        'old_epoch': old['target']['ns']['epoch'],
        'old_transfer_status': expired.statusCode,
        'new_context_error': '$error',
        'before': before,
        'after': h.disk(),
        'fresh': await h.freshRead(f.id),
        'explicit_new_namespace_full_resync': newOracle,
      });
    } finally {
      h.dispose();
      await b.dispose();
    }
  });
}

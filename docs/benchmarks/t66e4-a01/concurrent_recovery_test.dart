// Additional concurrent-winner case derived from the unchanged Phase A FA17.
@Timeout(Duration(minutes: 8))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

// Only delay an existing async metadata read. No product source instrumentation,
// authority bypass, extra AppState/coordinator, external schema change or reentrant hook.
class DelayedMetadataWorkspace extends E4Workspace {
  DelayedMetadataWorkspace(super.root, {super.fault});
  bool pauseNextMetadata = false;
  final entered = Completer<void>(), release = Completer<void>();
  @override
  Future<OfflineWorkspaceMetadata> loadMetadata() async {
    if (pauseNextMetadata) {
      pauseNextMetadata = false;
      entered.complete();
      await release.future;
    }
    return super.loadMetadata();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('A01 concurrent old and winning recoveries preserve the newer original-ticket installation', () async {
    final root = Directory.systemTemp.createTempSync(
      'mn-e4-independent-stale-recovery-',
    );
    final bridge = await BackendBridge.start(history: 7);
    FlutterSecureStorage.setMockInitialValues({});
    var store = SegmentedClientStore.open(
      root,
      GenerationFixture(bridge.fixture).cache,
      adapters: true,
    );
    late DelayedMetadataWorkspace workspace;
    bool failOlder = false;
    final cancellation = SyncCancellation();
    workspace = DelayedMetadataWorkspace(
      root,
      fault: (point) {
        if (failOlder && point == 'before_legacy_rename') {
          failOlder = false;
          workspace.pauseNextMetadata = true;
          // The ordinary cancellation check immediately before rename rejects A.
          cancellation.cancel();
        }
      },
    );
    final api = TargetedApi(bridge, await e4WireOracle());
    await api.saveSession(bridge.token);
    final state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    try {
      for (final o in bridge.fixture['objects']) {
        store.putVerifiedObject(
          ObjectRef.parse(o['ref']),
          base64Decode(o['data_base64']),
        );
      }
      final initial = await state.installSegmentedLegacyForIsolatedUse(store);
      await workspace.beginOnlineWrite(1); // Unknown must never be retired.
      final markerFile = File(
        '${workspace.root.path}/offline-mode/online-write-1.json',
      );
      final marker = markerFile.readAsBytesSync();
      failOlder = true;
      Object? olderFailure;
      final older = state
          .installSegmentedLegacyForIsolatedUse(
            store,
            cancellation: cancellation,
          )
          .then<void>(
            (_) {
              throw StateError('older unexpectedly succeeded');
            },
            onError: (Object error) {
              olderFailure = error;
            },
          );
      await workspace.entered.future.timeout(const Duration(seconds: 90));
      // The older lineage critical section has released; only its finally recovery
      // is suspended at the real asynchronous metadata load.
      await bridge.command({'command': 'mutate'});
      final newer = await state.installSegmentedLegacyForIsolatedUse(store);
      final sourceFile = File('${workspace.root.path}/e4-source.json');
      final before = sourceFile.readAsBytesSync();
      final baseline = File(
        '${workspace.root.path}/offline-mode/baseline.json',
      );
      final newB = baseline.readAsBytesSync();
      expect(jsonDecode(utf8.decode(before))['frozen'], newer.frozen.id);
      workspace.release.complete();
      final winningRecovery = workspace.recoverLegacyHandoff(store);
      await older;
      await winningRecovery;
      expect(olderFailure, isA<SegmentedException>());
      expect(
        (olderFailure as SegmentedException).code,
        'ACQUISITION_CANCELLED',
      );
      final after = sourceFile.readAsBytesSync();
      Object? readFailure, recoveryFailure;
      try {
        await workspace.readFrozenBaseline(store, newer.frozen.id, 1);
      } catch (e) {
        readFailure = e;
      }
      store.close();
      store = SegmentedClientStore.open(
        root,
        GenerationFixture(bridge.fixture).cache,
        adapters: true,
      );
      try {
        await E4Workspace(root).recoverLegacyHandoff(store);
      } catch (e) {
        recoveryFailure = e;
      }
      final direct = sqlite3.open(store.path);
      final committed = {
        'accepted': direct
            .select('SELECT * FROM accepted')
            .map((r) => Map<String, dynamic>.from(r))
            .toList(),
        'installed': direct
            .select('SELECT * FROM installed')
            .map((r) => Map<String, dynamic>.from(r))
            .toList(),
        'frozen': direct
            .select('SELECT id,generation_id,checksum,state FROM frozen')
            .map((r) => Map<String, dynamic>.from(r))
            .toList(),
        'foreign_keys': direct.select('PRAGMA foreign_key_check').length,
      };
      direct.close();
      final repo = Directory.current.parent.path;
      final oracle = await Process.run('$repo/.venv/bin/python', [
        '$repo/docs/benchmarks/t66e4-audit/state_oracle.py',
        store.path,
      ]);
      expect(oracle.exitCode, 0, reason: oracle.stderr as String);
      final evidence = {
        'initial_frozen': initial.frozen.id,
        'new_frozen': newer.frozen.id,
        'new_installation_succeeded': true,
        'source_before_old_recovery': jsonDecode(utf8.decode(before)),
        'source_after_old_recovery': jsonDecode(utf8.decode(after)),
        'legacy_b_unchanged_after_success': sameBytes(
          newB,
          baseline.readAsBytesSync(),
        ),
        'unknown_marker_unchanged': sameBytes(
          marker,
          markerFile.readAsBytesSync(),
        ),
        'older_error': olderFailure.runtimeType.toString(),
        'older_error_code': (olderFailure as SegmentedException).code,
        'fresh_store_opened': true,
        'frozen_read_error': readFailure is SegmentedException
            ? readFailure.code
            : readFailure?.runtimeType.toString(),
        'fresh_recovery_error': recoveryFailure is SegmentedException
            ? recoveryFailure.code
            : recoveryFailure?.runtimeType.toString(),
        'committed': committed,
        'independent_graph': jsonDecode(oracle.stdout as String),
      };
      const output = String.fromEnvironment('AUDIT_E4_STALE_OUTPUT');
      if (output.isNotEmpty)
        File(output).writeAsStringSync(jsonEncode(evidence), flush: true);
      expect(
        after,
        before,
        reason: 'An older failed finally recovery must not overwrite the successful newer handoff source.',
      );
      expect(readFailure, null);
      expect(recoveryFailure, null);
    } finally {
      if (!workspace.release.isCompleted) workspace.release.complete();
      state.dispose();
      store.close();
      await bridge.dispose();
      root.deleteSync(recursive: true);
    }
  });
}

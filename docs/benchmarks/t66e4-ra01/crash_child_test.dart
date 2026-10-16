import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('RA01 owned native handoff process-death worker', () async {
    const path = String.fromEnvironment('RA01_ROOT');
    const mode = String.fromEnvironment('RA01_MODE');
    const boundary = String.fromEnvironment('RA01_BOUNDARY');
    if (path.isEmpty ||
        File('$path/owned').readAsStringSync() != 'synthetic E4-RA01') {
      throw StateError('unowned RA01 test root');
    }
    final root = Directory(path), savedFile = File('$path/expected.json');
    if (mode == 'recover') {
      final saved = jsonDecode(savedFile.readAsStringSync());
      final store = SegmentedClientStore.open(
        root,
        CacheNamespace.forTarget(
          syntheticOrigin,
          SyncTarget.parse(saved['target']),
        ),
        adapters: true,
      );
      try {
        final workspace = E4Workspace(root);
        Object? recoveryError;
        try {
          await workspace.recoverLegacyHandoff(store);
        } catch (error) {
          recoveryError = error;
        }
        if (boundary == 'invalid_rejected') {
          expect(
            recoveryError,
            isA<SegmentedException>().having(
              (e) => e.code,
              'code',
              'SOURCE_PROVENANCE_REQUIRED',
            ),
          );
        } else {
          expect(recoveryError, null);
        }
        // This is an isolated, verified Frozen-B read, NOT native installation,
        // successful recovery of damaged metadata, or general-user Offline.
        final b = await workspace.readFrozenBaseline(store, saved['frozen'], 1);
        final f = store.frozenGenerations().singleWhere(
          (f) => f.id == saved['frozen'],
        );
        expect(
          workspace.recoveryLineageFingerprint(b),
          f.binding['legacy_lineage'],
        );
        expect(b.serverStateFingerprint, f.binding['legacy_fingerprint']);
        expect(
          () => requireSegmentedOfflineRecovery(),
          throwsA(isA<SegmentedException>()),
        );
        File('$path/recovered.json').writeAsStringSync(
          jsonEncode({
            'recovery_error': recoveryError is SegmentedException
                ? recoveryError.code
                : null,
            'frozen_read': true,
            'r1_gate': 'CLOSED',
            'installed': store.installedGeneration()!.id,
            'source': jsonDecode(
              File('${workspace.root.path}/e4-source.json').readAsStringSync(),
            ),
          }),
          flush: true,
        );
      } finally {
        store.close();
      }
      return;
    }
    FlutterSecureStorage.setMockInitialValues({});
    final bridge = await BackendBridge.start(history: 6);
    var armed = false, sourcePrepared = false;
    late SegmentedClientStore store;
    late E4Workspace workspace;
    void barrier() {
      File('$path/barrier.json').writeAsStringSync(
        jsonEncode({'pid': pid, 'boundary': boundary}),
        flush: true,
      );
      while (true) {
        sleep(const Duration(milliseconds: 100));
      }
    }

    store = SegmentedClientStore.open(
      root,
      GenerationFixture(bridge.fixture).cache,
      adapters: true,
      fault: (point) {
        if (!armed) return;
        if ((boundary == 'after_pointer_before_commit' &&
                point == 'after_segmented_install_pointer') ||
            (boundary == 'after_commit' &&
                sourcePrepared &&
                point == 'after_commit') ||
            (boundary == 'during_readback' &&
                point == 'during_installation_readback') ||
            (boundary == 'recovery_after_commit' && point == 'after_commit')) {
          barrier();
        }
      },
    );
    workspace = E4Workspace(
      root,
      fault: (point) {
        if (!armed || point != 'before_source_rename') return;
        if (boundary == 'before_source' || boundary == 'recovery_before_commit')
          barrier();
        sourcePrepared = true;
      },
    );
    final api = TargetedApi(bridge, await e4WireOracle());
    await api.saveSession(bridge.token);
    final state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    try {
      await workspace.beginOnlineWrite(1);
      final old = (await state.installSegmentedLegacyForIsolatedUse(store))
          .frozen;
      final source = File('${workspace.root.path}/e4-source.json');
      final bfile = File('${workspace.root.path}/offline-mode/baseline.json');
      final pending = File(
        '${workspace.root.path}/offline-mode/online-write-1.json',
      );
      await bridge.command({'command': 'mutate'});
      await state.publishSegmentedForIsolatedUse(store);
      final accepted = store.acceptedGeneration();
      final expected = <String, dynamic>{
        'target': accepted.manifest!.target.toJson(),
        'store_path': store.path,
        'frozen': old.id,
        'old_installed': store.installedGeneration()!.id,
        'new_generation': accepted.id,
        'baseline': base64Encode(bfile.readAsBytesSync()),
        'pending': base64Encode(pending.readAsBytesSync()),
        'old_source_sha256': localChecksum(source.readAsBytesSync()),
      };
      savedFile.writeAsStringSync(jsonEncode(expected), flush: true);
      if (boundary == 'invalid_rejected' || boundary.startsWith('recovery_')) {
        workspace.prepareSegmentedSource(store, accepted, () {});
        if (boundary == 'invalid_rejected') {
          final invalid = jsonDecode(source.readAsStringSync())
            ..['previous_source'] = null;
          source.writeAsStringSync(jsonEncode(invalid), flush: true);
          final prior = source.readAsBytesSync();
          await expectLater(
            state.refreshSegmentedForIsolatedUse(store),
            throwsA(
              isA<SegmentedException>().having(
                (e) => e.code,
                'code',
                'SOURCE_PROVENANCE_REQUIRED',
              ),
            ),
          );
          expect(source.readAsBytesSync(), prior);
          expect(store.installedGeneration()!.id, expected['old_installed']);
          expected['rejected_source_sha256'] = localChecksum(prior);
          savedFile.writeAsStringSync(jsonEncode(expected), flush: true);
          barrier();
        }
        armed = true;
        await workspace.recoverLegacyHandoff(store);
      } else {
        armed = true;
        await state.refreshSegmentedForIsolatedUse(store);
      }
      throw StateError('RA01 process-death boundary not reached');
    } finally {
      state.dispose();
      store.close();
      await bridge.dispose();
    }
  }, timeout: const Timeout(Duration(minutes: 5)));
}

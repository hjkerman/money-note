import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/segmented_e4_a01_test.dart' show RecoveryWorkspace;
import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('A01 owned process-death worker', () async {
    const path = String.fromEnvironment('A01_ROOT');
    const mode = String.fromEnvironment('A01_MODE');
    const boundary = String.fromEnvironment('A01_BOUNDARY');
    if (path.isEmpty ||
        File('$path/owned').readAsStringSync() != 'synthetic E4-A01') {
      throw StateError('unowned A01 test directory');
    }
    final root = Directory(path);
    final savedFile = File('$path/expected.json');
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
        await workspace.recoverLegacyHandoff(store);
        if (saved['frozen'] != null) {
          await workspace.readFrozenBaseline(store, saved['frozen'], 1);
          expect(store.frozenGenerations().length, 1);
          expect(store.frozenGenerations().single.id, saved['frozen']);
        } else {
          final installed = await store.recoverInstalledGeneration();
          expect(installed!.id, saved['native_generation']);
          store.withInstalledRead(installed, (r) {
            r.hot;
            r.control;
          });
          expect(store.frozenGenerations(), isEmpty);
        }
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
        File('$path/recovered')
            .writeAsStringSync('data-only source recovery', flush: true);
      } finally {
        store.close();
      }
      return;
    }

    FlutterSecureStorage.setMockInitialValues({});
    final bridge = await BackendBridge.start(history: 5);
    var armed = false;
    Database? reader;
    late SegmentedClientStore store;
    late RecoveryWorkspace workspace;
    void barrier({bool wait = true}) {
      File('$path/barrier.json').writeAsStringSync(
        jsonEncode({'pid': pid, 'boundary': boundary}),
        flush: true,
      );
      if (wait) {
        while (true) {
          sleep(const Duration(milliseconds: 100));
        }
      }
    }

    store = SegmentedClientStore.open(
      root,
      GenerationFixture(bridge.fixture).cache,
      adapters: true,
      fault: (p) {
        if (armed &&
            boundary == 'source_restore_after_commit' &&
            p == 'after_commit')
          barrier();
      },
    );
    workspace = RecoveryWorkspace(
      root,
      fault: (p) {
        if (armed &&
            boundary.endsWith('source_restore_before_commit') &&
            p == 'before_source_rename') {
          armed = false;
          // A real SQLite SHARED lock makes COMMIT wait, not an artificial
          // after-guard callback. Supervisor observes the replaced source and
          // SIGKILLs the actual tester during native COMMIT's busy interval.
          reader = sqlite3.open(store.path);
          reader!.execute('BEGIN DEFERRED');
          reader!.select('SELECT * FROM frozen');
          barrier(wait: false);
        }
      },
    );
    final api = TargetedApi(bridge, await e4WireOracle());
    await api.saveSession(bridge.token);
    final state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    final source = File('${workspace.root.path}/e4-source.json');
    final baseline = File('${workspace.root.path}/offline-mode/baseline.json');
    final pending = File(
      '${workspace.root.path}/offline-mode/online-write-1.json',
    );
    try {
      FrozenGeneration? expected;
      if (!boundary.startsWith('native_only_')) {
        expected = (await state.installSegmentedLegacyForIsolatedUse(store))
            .frozen;
      }
      if (boundary.startsWith('native_')) {
        await state.refreshSegmentedForIsolatedUse(store);
      }
      await workspace.beginOnlineWrite(1);
      final accepted = store.acceptedGeneration();
      final full = await store.verifyAcceptedForMaterialization(accepted);
      final bundle = store.withAcceptedRead(
        accepted,
        (r) => materializeLegacyRead(r, baselineFixture().user),
        materializationProof: full,
      );
      final b = legacyBaseline(bundle, DateTime.utc(2026, 10, 16));
      final preparation = store.prepareFrozenGeneration(
        accepted,
        full,
        workspace.bindingFor(accepted, b, store.cache.key),
        frozenId: syncUuid(),
        finalAuthorityFence: () {},
      );
      workspace.prepareLegacySource(preparation, () {});
      if (boundary.startsWith('stale_')) {
        workspace.pause();
        final older = workspace.recoverLegacyHandoff(store);
        await workspace.entered!.future;
        await E4Workspace(root).recoverLegacyHandoff(store);
        await bridge.command({'command': 'mutate'});
        expected = (await state.installSegmentedLegacyForIsolatedUse(store))
            .frozen;
        savedFile.writeAsStringSync(
          jsonEncode({
            'target': store.acceptedGeneration().manifest!.target.toJson(),
            'frozen': expected.id,
            'abandoned': preparation.id,
            'store_path': store.path,
            'source': base64Encode(source.readAsBytesSync()),
            'baseline': base64Encode(baseline.readAsBytesSync()),
            'pending': base64Encode(pending.readAsBytesSync()),
          }),
          flush: true,
        );
        if (boundary == 'stale_before_release') barrier();
        workspace.release!.complete();
        expect(await older, null);
        expect(
          source.readAsBytesSync(),
          base64Decode(jsonDecode(savedFile.readAsStringSync())['source']),
        );
        barrier();
      } else {
        savedFile.writeAsStringSync(
          jsonEncode({
            'target': store.acceptedGeneration().manifest!.target.toJson(),
            'frozen': expected?.id,
            'native_generation': store.installedGeneration()?.id,
            'restored_source': jsonDecode(
              source.readAsStringSync(),
            )['previous_source'],
            'abandoned': preparation.id,
            'store_path': store.path,
            'baseline': baseline.existsSync()
                ? base64Encode(baseline.readAsBytesSync())
                : null,
            'pending': base64Encode(pending.readAsBytesSync()),
          }),
          flush: true,
        );
        armed = true;
        await workspace.recoverLegacyHandoff(store);
      }
      throw StateError('A01 crash boundary not reached');
    } finally {
      reader?.close();
      state.dispose();
      store.close();
      await bridge.dispose();
    }
  }, timeout: const Timeout(Duration(minutes: 5)));
}

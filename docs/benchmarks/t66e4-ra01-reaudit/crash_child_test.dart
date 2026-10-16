import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
    'independent RA01 first and alternating source process-death worker',
    () async {
      const path = String.fromEnvironment('NR_ROOT');
      const mode = String.fromEnvironment('NR_MODE');
      const boundary = String.fromEnvironment('NR_BOUNDARY');
      if (path.isEmpty ||
          File('$path/owned').readAsStringSync() !=
              'synthetic independent RA01') {
        throw StateError('unowned test path');
      }
      final root = Directory(path), saved = File('$path/expected.json');
      if (mode == 'recover') {
        final expected = jsonDecode(saved.readAsStringSync());
        final s = SegmentedClientStore.open(
          root,
          CacheNamespace.forTarget(
            syntheticOrigin,
            SyncTarget.parse(expected['target']),
          ),
          adapters: true,
        );
        try {
          final w = E4Workspace(root);
          await w.recoverLegacyHandoff(s);
          await w.recoverLegacyHandoff(s);
          final actual = await s.recoverInstalledGeneration();
          final selected = boundary == 'first_before_commit'
              ? null
              : expected['installed'];
          expect(actual?.id, selected);
          if (expected['frozen'] != null) {
            final b = await w.readFrozenBaseline(s, expected['frozen'], 1);
            expect(w.recoveryLineageFingerprint(b), expected['lineage']);
            expect(b.serverStateFingerprint, expected['fingerprint']);
          } else if (actual != null) {
            s.withInstalledRead(actual, (r) {
              expect(r.hot, isNotNull);
              expect(r.control, isNotNull);
            });
          }
          expect(
            () => requireSegmentedOfflineRecovery(),
            throwsA(isA<SegmentedException>()),
          );
          File('$path/recovered.json').writeAsStringSync(
            jsonEncode({
              'installed': actual?.id,
              'frozen': expected['frozen'],
              'readable': true,
              'r1': 'CLOSED',
            }),
            flush: true,
          );
        } finally {
          s.close();
        }
        return;
      }
      FlutterSecureStorage.setMockInitialValues({});
      final bridge = await BackendBridge.start(history: 8);
      var armed = false, prepared = false;
      late SegmentedClientStore s;
      late E4Workspace w;
      void stop() {
        final source = File('${w.root.path}/e4-source.json');
        final value = jsonDecode(source.readAsStringSync());
        final id = value['legacy_frozen'] ?? value['frozen'];
        final frozen = id == null
            ? null
            : s.frozenGenerations().singleWhere((f) => f.id == id);
        final b = File('${w.root.path}/offline-mode/baseline.json');
        final pending = File('${w.root.path}/offline-mode/online-write-1.json');
        saved.writeAsStringSync(
          jsonEncode({
            'target': s.acceptedGeneration().manifest!.target.toJson(),
            'store': s.path,
            'installed': s.installedGeneration()?.id,
            'frozen': id,
            'lineage': frozen?.binding['legacy_lineage'],
            'fingerprint': frozen?.binding['legacy_fingerprint'],
            'baseline': b.existsSync()
                ? base64Encode(b.readAsBytesSync())
                : null,
            'pending': base64Encode(pending.readAsBytesSync()),
            'source': value,
          }),
          flush: true,
        );
        File('$path/barrier.json').writeAsStringSync(
          jsonEncode({'pid': pid, 'boundary': boundary}),
          flush: true,
        );
        while (true) {
          sleep(const Duration(milliseconds: 50));
        }
      }

      s = SegmentedClientStore.open(
        root,
        GenerationFixture(bridge.fixture).cache,
        adapters: true,
        fault: (p) {
          if (!armed) return;
          if (boundary == 'alternating_legacy_before_native' &&
              p == 'after_frozen_install')
            stop();
          if (boundary == 'first_before_commit' &&
              p == 'after_segmented_install_pointer')
            stop();
          if (boundary == 'first_after_commit' &&
              prepared &&
              p == 'after_commit')
            stop();
        },
      );
      w = E4Workspace(
        root,
        fault: (p) {
          if (!armed) return;
          if (p == 'before_source_rename') prepared = true;
        },
      );
      final api = TargetedApi(bridge, await e4WireOracle());
      await api.saveSession(bridge.token);
      final state = AppState(api, offlineStore: w)
        ..user = baselineFixture().user;
      try {
        await w.beginOnlineWrite(1);
        if (boundary.startsWith('first_')) {
          armed = true;
          await state.refreshSegmentedForIsolatedUse(s);
        } else {
          await state.installSegmentedLegacyForIsolatedUse(s);
          await bridge.command({'command': 'mutate'});
          await state.refreshSegmentedForIsolatedUse(s);
          await bridge.command({'command': 'mutate'});
          armed = true;
          await state.installSegmentedLegacyForIsolatedUse(s);
        }
        throw StateError('boundary was not reached');
      } finally {
        state.dispose();
        s.close();
        await bridge.dispose();
      }
    },
    timeout: const Timeout(Duration(minutes: 5)),
  );
}

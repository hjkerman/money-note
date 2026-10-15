import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('independent owned G1-to-G2 crash worker', () async {
    const path = String.fromEnvironment('AUDIT_E4_ROOT');
    const mode = String.fromEnvironment('AUDIT_E4_MODE');
    const boundary = String.fromEnvironment('AUDIT_E4_BOUNDARY');
    if (path.isEmpty ||
        File('$path/owned').readAsStringSync() != 'independent synthetic E4')
      throw StateError('unowned test path');
    final root = Directory(path), workspace = E4Workspace(root);
    if (mode == 'recover') {
      final saved = jsonDecode(File('$path/before.json').readAsStringSync());
      final cache = CacheNamespace.forTarget(
        syntheticOrigin,
        SyncTarget.parse(saved['target']),
      );
      final store = SegmentedClientStore.open(root, cache, adapters: true);
      try {
        await workspace.recoverLegacyHandoff(store);
        await store.recoverAcceptedGeneration();
        await store.recoverInstalledGeneration();
        File('$path/recovered').writeAsStringSync('data only');
      } finally {
        store.close();
      }
      return;
    }
    FlutterSecureStorage.setMockInitialValues({});
    final bridge = await BackendBridge.start(history: 7);
    var armed = false;
    late SegmentedClientStore store;
    void fault(String point) {
      if (!armed || point != boundary.replaceFirst('native_', '')) return;
      File('$path/barrier.json').writeAsStringSync(
        jsonEncode({'pid': pid, 'path': store.path, 'point': point}),
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
      fault: fault,
    );
    final owner = E4Workspace(root, fault: fault),
        api = TargetedApi(bridge, await e4WireOracle());
    await api.saveSession(bridge.token);
    final state = AppState(api, offlineStore: owner)
      ..user = baselineFixture().user;
    try {
      final g1 = await state.installSegmentedLegacyForIsolatedUse(store);
      final pending = await owner.beginOnlineWrite(
        1,
      ); // Unknown must survive every crash and recovery.
      final baselineFile = File(
        '${owner.root.path}/offline-mode/baseline.json',
      );
      final markerFile = File(
        '${owner.root.path}/offline-mode/online-write-1.json',
      );
      File('$path/before.json').writeAsStringSync(
        jsonEncode({
          'target': g1.publication.target.toJson(),
          'g1': g1.publication.generationId,
          'frozen': g1.frozen.id,
          'baseline': base64Encode(baselineFile.readAsBytesSync()),
          'marker': base64Encode(markerFile.readAsBytesSync()),
          'token': pending.token,
          'store_path': store.path,
        }),
        flush: true,
      );
      await bridge.command({'command': 'mutate'});
      armed = true;
      if (boundary.startsWith('native_')) {
        await state.refreshSegmentedForIsolatedUse(store);
      } else {
        await state.installSegmentedLegacyForIsolatedUse(store);
      }
      throw StateError('boundary not reached');
    } finally {
      state.dispose();
      store.close();
      await bridge.dispose();
    }
  }, timeout: const Timeout(Duration(minutes: 5)));
}

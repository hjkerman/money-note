// Actual Flutter/AppState child, invoked only with a parent-owned synthetic root.
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('parent controlled synthetic E4 handoff child', () async {
    const location = String.fromEnvironment('E4_CRASH_ROOT'),
        point = String.fromEnvironment('E4_CRASH_POINT');
    if (location.isEmpty ||
        point.isEmpty ||
        File('$location/e4-owned').readAsStringSync() != 'synthetic E4')
      throw StateError('missing owned synthetic crash root');
    final root = Directory(location),
        bridge = await BackendBridge.start(history: 4);
    late SegmentedClientStore store;
    void fault(String actual) {
      if (actual != point.replaceFirst('native_', '')) return;
      File('$location/crash-ready.json').writeAsStringSync(
        jsonEncode({'pid': pid, 'store_path': store.path, 'point': actual}),
        flush: true,
      );
      while (true) {
        sleep(const Duration(milliseconds: 100));
      }
    }

    FlutterSecureStorage.setMockInitialValues({});
    store = SegmentedClientStore.open(
      root,
      GenerationFixture(bridge.fixture).cache,
      adapters: true,
      fault: fault,
    );
    final workspace = E4Workspace(root, fault: fault),
        api = TargetedApi(bridge, await e4WireOracle());
    await api.saveSession(bridge.token);
    final state = AppState(api, offlineStore: workspace)
      ..user = baselineFixture().user;
    try {
      if (point.startsWith('native_'))
        await state.refreshSegmentedForIsolatedUse(store);
      else
        await state.installSegmentedLegacyForIsolatedUse(store);
      throw StateError('crash point not reached');
    } finally {
      state.dispose();
      store.close();
      await bridge.dispose();
    }
  }, timeout: const Timeout(Duration(minutes: 4)));
}

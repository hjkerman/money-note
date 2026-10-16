@Timeout(Duration(minutes: 10))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import 'harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('FB real HTTP installation child boundary', () async {
    final config = jsonDecode(
      File(const String.fromEnvironment('F_CRASH_INPUT')).readAsStringSync(),
    );
    final backend = RealBackend.remote(config['backend']);
    var armed = false;
    Map<String, dynamic>? initial;
    late RealHarness h;
    h = await RealHarness.create(
      backend,
      sqlFault: (point) {
        if (armed &&
            config['boundary'] == 'native_before_commit' &&
            point == 'before_commit' &&
            StackTrace.current.toString().contains(
              'commitInstalledGeneration',
            )) {
          File(config['barrier']).writeAsStringSync(
            jsonEncode({
              'pid': pid,
              'root': h.root.path,
              'db': h.store.path,
              'origin': backend.origin,
              'target': h.store.acceptedGeneration().manifest!.target.toJson(),
              'boundary': 'native_before_commit',
              'initial': initial,
            }),
            flush: true,
          );
          while (true) {
            sleep(const Duration(milliseconds: 100));
          }
        }
      },
      fault: (point) {
        if (armed && point == config['boundary']) {
          File(config['barrier']).writeAsStringSync(
            jsonEncode({
              'pid': pid,
              'root': h.root.path,
              'db': h.store.path,
              'origin': backend.origin,
              'target': h.store.acceptedGeneration().manifest!.target.toJson(),
              'boundary': point,
              'initial': initial,
            }),
            flush: true,
          );
          // 이 child만 부모가 실제 SIGKILL한다. exception injection이 아니다.
          while (true) {
            sleep(const Duration(milliseconds: 100));
          }
        }
      },
    );
    try {
      final f = (await h.state.installSegmentedLegacyForIsolatedUse(h.store))
          .frozen;
      await h.workspace.beginOnlineWrite(1);
      initial = {
        'frozen': f.id,
        'fingerprint': f.binding['legacy_fingerprint'],
        'baseline_sha256': localChecksum(h.baseline.readAsBytesSync()),
        'pending_sha256': localChecksum(h.pending.readAsBytesSync()),
        'installed': h.disk()['installed'],
      };
      File(config['ready']).writeAsStringSync(jsonEncode(initial), flush: true);
      while (!File(config['continue']).existsSync()) {
        sleep(const Duration(milliseconds: 20));
      }
      armed = true;
      await h.state.refreshSegmentedForIsolatedUse(h.store);
      throw StateError('requested child boundary not hit');
    } finally {
      h.dispose();
    }
  });
}

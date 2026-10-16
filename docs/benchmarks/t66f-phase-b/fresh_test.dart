import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('FB fresh-process accepted and Frozen-B recovery', () async {
    const input = String.fromEnvironment('F_REOPEN');
    const output = String.fromEnvironment('F_REOPEN_OUTPUT');
    final config = jsonDecode(File(input).readAsStringSync());
    final root = Directory(config['root']);
    final store = SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(
        config['origin'],
        SyncTarget.parse(config['target']),
      ),
      adapters: true,
    );
    try {
      if (config['recover'] != false)
        await E4Workspace(root).recoverLegacyHandoff(store);
      final accepted = await store.recoverAcceptedGeneration();
      String? fingerprint;
      if (config['frozen'] != null) {
        final b = await E4Workspace(root)
            .readFrozenBaseline(store, config['frozen'], 1);
        fingerprint = b.serverStateFingerprint;
      }
      File(output).writeAsStringSync(
        jsonEncode({
          'accepted': accepted.id,
          'sequence': accepted.sequence,
          'frozen_fingerprint': fingerprint,
          'source': jsonDecode(
            File('${E4Workspace(root).root.path}/e4-source.json')
                .readAsStringSync(),
          ),
        }),
      );
    } finally {
      store.close();
    }
  });
}

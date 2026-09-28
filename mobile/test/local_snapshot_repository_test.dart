import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';

class SnapshotApiFake extends MoneyNoteApiClient {
  SnapshotApiFake() : super(baseUrl: 'https://example.invalid');

  int downloads = 0;
  int restores = 0;

  @override
  Future<SnapshotDownload> downloadSnapshot() async {
    downloads += 1;
    return SnapshotDownload(
      filename: 'server-provided-name.json',
      bytes: Uint8List.fromList(utf8.encode('{"fixture":true}')),
    );
  }

  @override
  Future<Map<String, dynamic>> restoreSnapshot({
    required String password,
    required String snapshotText,
  }) async {
    restores += 1;
    return {};
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('plugins.flutter.io/path_provider');
  late Directory directory;

  setUp(() async {
    directory =
        await Directory.systemTemp.createTemp('money-note-t4-snapshot-');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      if (call.method == 'getApplicationDocumentsDirectory') {
        return directory.path;
      }
      return null;
    });
  });

  tearDown(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
    await directory.delete(recursive: true);
  });

  test('launch backup keeps newest 30 and ignores server filename', () async {
    final snapshots = Directory('${directory.path}/snapshots');
    await snapshots.create();
    for (var index = 0; index < 30; index++) {
      final file =
          File('${snapshots.path}/old-$index.money-note-snapshot.json');
      await file.writeAsString('old-$index', flush: true);
      await file.setLastModified(
          DateTime.utc(2020, 1, 1).add(Duration(seconds: index)));
    }
    final api = SnapshotApiFake();
    final state = AppState(api);
    await state.saveLaunchSnapshot();
    final listed = await state.listLocalSnapshots();
    expect(api.downloads, 1);
    expect(listed, hasLength(30));
    expect(
        listed.any((item) => item.filename == 'old-0.money-note-snapshot.json'),
        isFalse);
    final newest = listed.first;
    expect(newest.filename, startsWith('money-note-snapshot-'));
    expect(newest.filename, endsWith('.money-note-snapshot.json'));
    expect(await File('${snapshots.path}/${newest.filename}').readAsString(),
        '{"fixture":true}');
  });

  test('unknown snapshot path cannot delete or restore another file', () async {
    final outside = File('${directory.path}/outside.money-note-snapshot.json');
    await outside.writeAsString('outside', flush: true);
    final api = SnapshotApiFake();
    final state = AppState(api);
    await state.deleteLocalSnapshot('../outside.money-note-snapshot.json');
    expect(await outside.readAsString(), 'outside');
    await state.restoreLocalSnapshot(
        filename: '../outside.money-note-snapshot.json',
        password: 'test-password');
    expect(api.restores, 0);
    expect(await outside.readAsString(), 'outside');
  });
}

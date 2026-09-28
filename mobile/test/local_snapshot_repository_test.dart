import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/local_snapshot_repository.dart';

class SnapshotApiFake extends MoneyNoteApiClient {
  SnapshotApiFake(this.snapshotBytes)
      : super(baseUrl: 'https://example.invalid');

  final Uint8List snapshotBytes;

  int downloads = 0;
  int restores = 0;

  @override
  Future<SnapshotDownload> downloadSnapshot() async {
    downloads += 1;
    return SnapshotDownload(
      filename: 'server-provided-name.json',
      bytes: snapshotBytes,
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

class InterruptedSnapshotFile implements File {
  InterruptedSnapshotFile(this.delegate);
  final File delegate;

  @override
  String get path => delegate.path;

  @override
  Future<File> create({bool recursive = false, bool exclusive = false}) =>
      delegate.create(recursive: recursive, exclusive: exclusive);

  @override
  Future<File> writeAsBytes(List<int> bytes,
      {FileMode mode = FileMode.write, bool flush = false}) async {
    await delegate.writeAsBytes(bytes.take(16).toList(), flush: true);
    throw FileSystemException('injected partial write', path);
  }

  @override
  Future<bool> exists() => delegate.exists();

  @override
  Future<FileSystemEntity> delete({bool recursive = false}) =>
      delegate.delete(recursive: recursive);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class ShareSelectionRepository extends LocalSnapshotRepository {
  ShareSelectionRepository(Directory directory)
      : super(directoryProvider: () async => directory);

  String? selectedFilename;

  @override
  Future<File> safeFile(String filename) async {
    selectedFilename = filename;
    throw const FileSystemException('stop before platform share');
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('plugins.flutter.io/path_provider');
  late Directory directory;
  late Uint8List validSnapshotBytes;

  setUp(() async {
    directory =
        await Directory.systemTemp.createTemp('money-note-t4-snapshot-');
    validSnapshotBytes =
        await File('test/fixtures/valid_snapshot.json').readAsBytes();
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
      await file.writeAsBytes(validSnapshotBytes, flush: true);
      await file.setLastModified(
          DateTime.utc(2020, 1, 1).add(Duration(seconds: index)));
    }
    final api = SnapshotApiFake(validSnapshotBytes);
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
    expect(await File('${snapshots.path}/${newest.filename}').readAsBytes(),
        validSnapshotBytes);
  });

  test('unknown snapshot path cannot delete or restore another file', () async {
    final outside = File('${directory.path}/outside.money-note-snapshot.json');
    await outside.writeAsString('outside', flush: true);
    final api = SnapshotApiFake(validSnapshotBytes);
    final state = AppState(api);
    await state.deleteLocalSnapshot('../outside.money-note-snapshot.json');
    expect(await outside.readAsString(), 'outside');
    await state.restoreLocalSnapshot(
        filename: '../outside.money-note-snapshot.json',
        password: 'test-password');
    expect(api.restores, 0);
    expect(await outside.readAsString(), 'outside');
  });

  test('partial write is never published or prunes the previous 30 backups',
      () async {
    final snapshots = await Directory('${directory.path}/snapshots').create();
    for (var index = 0; index < 30; index++) {
      final file =
          File('${snapshots.path}/old-$index.money-note-snapshot.json');
      await file.writeAsBytes(validSnapshotBytes, flush: true);
      await file.setLastModified(
          DateTime.utc(2020, 1, 1).add(Duration(seconds: index)));
    }
    final repository =
        LocalSnapshotRepository(directoryProvider: () async => directory);
    final parentZone = Zone.current;
    await expectLater(
        IOOverrides.runZoned(() async {
          await repository.save(validSnapshotBytes);
        }, createFile: (path) {
          final real = parentZone.run(() => File(path));
          return path.endsWith('.pending')
              ? InterruptedSnapshotFile(real)
              : real;
        }),
        throwsA(isA<FileSystemException>()));

    final restarted =
        LocalSnapshotRepository(directoryProvider: () async => directory);
    final listed = await restarted.list();
    expect(listed, hasLength(30));
    expect(listed.first.filename, 'old-29.money-note-snapshot.json');
    expect(
        await File('${snapshots.path}/old-0.money-note-snapshot.json').exists(),
        isTrue);
    expect(snapshots.listSync().whereType<File>().length, 30);
  });

  test('invalid download and old partial final backup are not share candidates',
      () async {
    final snapshots = await Directory('${directory.path}/snapshots').create();
    final valid = File('${snapshots.path}/old.money-note-snapshot.json');
    await valid.writeAsBytes(validSnapshotBytes, flush: true);
    await valid.setLastModified(DateTime.utc(2020));
    final malformed = File('${snapshots.path}/new.money-note-snapshot.json');
    await malformed.writeAsString('{"schema_version": 7', flush: true);
    final repository =
        LocalSnapshotRepository(directoryProvider: () async => directory);

    await expectLater(repository.save(Uint8List.fromList(utf8.encode('{}'))),
        throwsA(isA<FormatException>()));
    final restarted =
        LocalSnapshotRepository(directoryProvider: () async => directory);
    final listed = await restarted.list();
    expect(listed, hasLength(1));
    expect(listed.single.filename, valid.uri.pathSegments.last);
    await expectLater(restarted.safeFile(malformed.uri.pathSegments.last),
        throwsA(isA<MoneyNoteApiException>()));
    expect(snapshots.listSync().whereType<File>().length, 2);

    final selection = ShareSelectionRepository(directory);
    final state = AppState(SnapshotApiFake(validSnapshotBytes),
        snapshotRepository: selection);
    await state.shareCurrentSnapshot();
    expect(selection.selectedFilename, valid.uri.pathSegments.last);
    await state.deleteAllLocalSnapshots();
    expect(snapshots.listSync().whereType<File>(), isEmpty);
  });

  test('stale pending writes are ignored and removed on the next save',
      () async {
    final snapshots = await Directory('${directory.path}/snapshots').create();
    final pending =
        File('${snapshots.path}/.money-note-snapshot-interrupted.pending');
    await pending.writeAsString('{"incomplete":', flush: true);
    await pending.setLastModified(DateTime.utc(2020));
    final repository =
        LocalSnapshotRepository(directoryProvider: () async => directory);
    expect(await repository.list(), isEmpty);

    final saved = await repository.save(validSnapshotBytes);
    expect(saved, hasLength(1));
    expect(await pending.exists(), isFalse);
  });
}

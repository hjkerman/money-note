import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/local_snapshot_repository.dart';
import 'package:money_note_mobile/src/snapshot_file_codec.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'support/offline_mode_fixtures.dart';
import 'response_coding_deflate_test.dart' show storedWitness;

class FailedReadbackFile implements File {
  FailedReadbackFile(this.file, this.corrupt);
  final File file;
  final bool corrupt;
  @override
  String get path => file.path;
  @override
  Future<File> create({bool recursive = false, bool exclusive = false}) =>
      file.create(recursive: recursive, exclusive: exclusive);
  @override
  Future<File> writeAsBytes(List<int> bytes,
      {FileMode mode = FileMode.write, bool flush = false}) async {
    await file.writeAsBytes(bytes, mode: mode, flush: flush);
    return this;
  }

  @override
  Stream<List<int>> openRead([int? start, int? end]) => corrupt
      ? Stream.value([0, 1, 2])
      : Stream.error(const FileSystemException('injected readback failure'));
  @override
  Future<bool> exists() => file.exists();
  @override
  Future<FileSystemEntity> delete({bool recursive = false}) =>
      file.delete(recursive: recursive);
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory root;
  late LocalSnapshotRepository repo;
  late Uint8List raw;
  setUp(() async {
    root = await Directory.systemTemp.createTemp('mn-snapshot-gzip-');
    repo = LocalSnapshotRepository(directoryProvider: () async => root);
    raw = await File('test/fixtures/valid_snapshot.json').readAsBytes();
  });
  tearDown(() async {
    await root.delete(recursive: true);
  });
  Future<File> legacy(String name, List<int> bytes) async {
    final dir = await Directory('${root.path}/snapshots').create();
    return File('${dir.path}/$name').writeAsBytes(bytes);
  }

  test('gzip save and legacy read preserve original JSON bytes', () async {
    final old = await legacy('old.money-note-snapshot.json', raw);
    final saved = await repo.save(raw);
    final compressed = saved.singleWhere((x) => x.filename.endsWith('.gz'));
    expect(await repo.readText(compressed.filename), utf8.decode(raw));
    expect(
        gzip.decode(await File('${root.path}/snapshots/${compressed.filename}')
            .readAsBytes()),
        raw);
    expect(
        await repo.readText('old.money-note-snapshot.json'), utf8.decode(raw));
    expect(await old.readAsBytes(), raw);
  });
  test('mixed retention removes only oldest after successful save', () async {
    for (var i = 0; i < 30; i++) {
      final gz = i.isOdd;
      final f = await legacy('$i.money-note-snapshot.json${gz ? '.gz' : ''}',
          gz ? gzip.encode(raw) : raw);
      await f.setLastModified(DateTime.utc(2020).add(Duration(seconds: i)));
    }
    expect(await repo.save(raw), hasLength(30));
    expect(
        await File('${root.path}/snapshots/0.money-note-snapshot.json')
            .exists(),
        false);
    expect(
        await File('${root.path}/snapshots/1.money-note-snapshot.json.gz')
            .exists(),
        true);
    await expectLater(repo.save(Uint8List.fromList(utf8.encode('{}'))),
        throwsFormatException);
    expect(await repo.list(), hasLength(30));
  });
  test(
      'extension mismatch and corrupt files cannot restore or change baseline/pending',
      () async {
    final good = await legacy('good.money-note-snapshot.json', raw);
    final bad = await legacy('bad.money-note-snapshot.json.gz', raw);
    var requests = 0;
    final api = MoneyNoteApiClient(
        baseUrl: 'https://example.invalid',
        client: MockClient((_) async {
          requests++;
          return http.Response('{}', 200);
        }));
    final store = OfflineStore(directoryProvider: () async => root);
    final baseline = baselineFixture();
    await store.replaceBaseline(baseline);
    await store.beginOnlineWrite(baseline.user.id);
    final state = AppState(api, snapshotRepository: repo, offlineStore: store)
      ..user = baseline.user;
    final oldSummary = state.summary;
    final oldEntries = state.entries;
    final oldJournal = state.offlineJournal;
    final durable = Directory('${root.path}/offline-mode')
        .listSync(recursive: true)
        .whereType<File>();
    final before = {for (final f in durable) f.path: await f.readAsBytes()};
    await state.restoreLocalSnapshot(
        filename: bad.uri.pathSegments.last, password: 'test');
    expect(requests, 0);
    expect(state.summary, same(oldSummary));
    expect(state.entries, same(oldEntries));
    expect(state.offlineJournal, same(oldJournal));
    expect(state.authoritativeRebuildPending, false);
    for (final e in before.entries) {
      expect(await File(e.key).readAsBytes(), e.value);
    }
    expect(await good.readAsBytes(), raw);
    state.dispose();
  });
  for (final defect in [
    'trailer',
    'crc',
    'isize',
    'middle',
    'magic',
    'extra',
    'members',
    'flags'
  ]) {
    test('reject $defect before decode success', () {
      final good = gzip.encode(raw);
      var b = List<int>.from(good);
      switch (defect) {
        case 'trailer':
          b = b.sublist(0, b.length - 8);
        case 'crc':
          b[b.length - 8] ^= 1;
        case 'isize':
          b[b.length - 4] ^= 1;
        case 'middle':
          b = b.sublist(0, b.length ~/ 2);
        case 'magic':
          b[0] = 0;
        case 'extra':
          b.add(0);
        case 'members':
          b.addAll(good);
        case 'flags':
          b[3] = 8;
      }
      expect(() => decodeSnapshotBytes(Uint8List.fromList(b), compressed: true),
          throwsFormatException);
    });
  }
  for (final delta in [-1, 0, 1]) {
    test('real output and identity boundary $delta', () async {
      final bytes = Uint8List(snapshotJsonLimit + delta)
        ..fillRange(0, snapshotJsonLimit + delta, 32);
      expect(() => decodeSnapshotBytes(bytes, compressed: false),
          delta > 0 ? throwsFormatException : returnsNormally);
      final encoded = Uint8List.fromList(GZipCodec(level: 6).encode(bytes));
      expect(encoded.length, lessThan(30000));
      if (delta > 0) {
        expect(() => decodeSnapshotBytes(encoded, compressed: true),
            throwsFormatException);
      } else {
        expect(decodeSnapshotBytes(encoded, compressed: true), bytes);
      }
      final f = File('${root.path}/bounded.json');
      await f.writeAsBytes(bytes);
      if (delta > 0) {
        await expectLater(
            readSnapshotBytes(f, compressed: false), throwsFormatException);
      } else {
        expect((await readSnapshotBytes(f, compressed: false)).length,
            bytes.length);
      }
    });
    test('compressed actual read boundary $delta', () async {
      final f = File('${root.path}/input.gz');
      await f.writeAsBytes(Uint8List(snapshotGzipLimit + delta));
      try {
        await readSnapshotBytes(f, compressed: true);
        fail('must reject invalid input');
      } on FormatException catch (e) {
        expect(
            e.message,
            delta > 0
                ? 'Snapshot size limit exceeded'
                : 'Snapshot extension/content mismatch');
      }
    });
    test('actual serialized request UTF8 boundary $delta', () async {
      final base = SnapshotRestoreRequest.prepare('p', '').byteLength;
      final text = 'x' * (snapshotJsonLimit - base + delta);
      var calls = 0;
      final api = MoneyNoteApiClient(
          baseUrl: 'https://example.invalid',
          client: MockClient((req) async {
            calls++;
            expect(req.bodyBytes.length, snapshotJsonLimit + delta);
            return http.Response('{}', 200);
          }));
      if (delta > 0) {
        expect(() => api.restoreSnapshot(password: 'p', snapshotText: text),
            throwsFormatException);
        expect(calls, 0);
      } else {
        await api.restoreSnapshot(password: 'p', snapshotText: text);
        expect(calls, 1);
      }
    });
  }
  test(
      'oversized restore request preserves actual durable baseline and pending',
      () async {
    final store = OfflineStore(directoryProvider: () async => root);
    final baseline = baselineFixture();
    await store.replaceBaseline(baseline);
    await store.beginOnlineWrite(baseline.user.id);
    final files = Directory('${root.path}/offline-mode')
        .listSync(recursive: true)
        .whereType<File>();
    final before = {for (final f in files) f.path: await f.readAsBytes()};
    final padded = Uint8List(snapshotJsonLimit)
      ..setRange(0, raw.length, raw)
      ..fillRange(raw.length, snapshotJsonLimit, 32);
    final saved = await repo.save(padded);
    var calls = 0;
    final api = MoneyNoteApiClient(
        baseUrl: 'https://example.invalid',
        client: MockClient((_) async {
          calls++;
          return http.Response('{}', 200);
        }));
    final state = AppState(api, offlineStore: store, snapshotRepository: repo)
      ..user = baseline.user;
    final entries = state.entries;
    final summary = state.summary;
    await state.restoreLocalSnapshot(
        filename: saved.first.filename, password: 'test');
    expect(calls, 0);
    expect(state.authoritativeRebuildPending, false);
    expect(state.entries, same(entries));
    expect(state.summary, same(summary));
    for (final e in before.entries) {
      expect(await File(e.key).readAsBytes(), e.value);
    }
    expect(await repo.list(), hasLength(1));
    state.dispose();
  });
  for (final compressed in [false, true]) {
    test(
        'local ${compressed ? 'gzip' : 'legacy JSON'} sends original text to unchanged Restore API',
        () async {
      final file = await legacy(
          'restore.money-note-snapshot.json${compressed ? '.gz' : ''}',
          compressed ? gzip.encode(raw) : raw);
      var calls = 0;
      final api = MoneyNoteApiClient(
          baseUrl: 'https://example.invalid',
          client: MockClient((req) async {
            calls++;
            expect(req.url.path, '/api/admin/snapshot/restore');
            expect(req.headers['content-encoding'], isNull);
            expect(jsonDecode(req.body)['snapshot_text'], utf8.decode(raw));
            return http.Response('{}', 200);
          }));
      await api.restoreSnapshot(
          password: 'test',
          snapshotText: await repo.readText(file.uri.pathSegments.last));
      expect(calls, 1);
    });
  }
  test('reserved and missing-final DEFLATE are rejected for local files', () {
    for (final ending in [
      [7],
      <int>[]
    ]) {
      expect(
          () => decodeSnapshotBytes(
              Uint8List.fromList(storedWitness(raw, ending)),
              compressed: true),
          throwsFormatException);
    }
  });
  test('Restore UTF8 wire remains identical including Unicode and escaping',
      () async {
    const text = '{"한글":"가😀\\줄"}';
    const password = '비밀번호😀';
    var calls = 0;
    final api = MoneyNoteApiClient(
        baseUrl: 'https://example.invalid',
        client: MockClient((r) async {
          calls++;
          expect(
              r.bodyBytes,
              utf8.encode(
                  jsonEncode({'password': password, 'snapshot_text': text})));
          expect(r.headers['content-encoding'], isNull);
          return http.Response('{}', 200);
        }));
    await api.restoreSnapshot(password: password, snapshotText: text);
    expect(calls, 1);
  });
  for (final corrupt in [false, true]) {
    test(
        'readback ${corrupt ? 'corruption' : 'IO failure'} preserves existing backups',
        () async {
      final good = await legacy('existing.money-note-snapshot.json', raw);
      final parent = Zone.current;
      await expectLater(
          IOOverrides.runZoned(() => repo.save(raw), createFile: (path) {
            final f = parent.run(() => File(path));
            return path.endsWith('.pending')
                ? FailedReadbackFile(f, corrupt)
                : f;
          }),
          throwsA(anyOf(isA<FormatException>(), isA<FileSystemException>())));
      expect(await good.readAsBytes(), raw);
      expect(await repo.list(), hasLength(1));
      expect(Directory('${root.path}/snapshots').listSync().whereType<File>(),
          hasLength(1));
    });
  }
  test('oversized compression input cannot prune an existing backup', () async {
    final file = await legacy('existing.money-note-snapshot.json', raw);
    await expectLater(
        repo.save(Uint8List(snapshotJsonLimit + 1)), throwsFormatException);
    expect(await file.readAsBytes(), raw);
    expect(await repo.list(), hasLength(1));
  });
  test('sharing preserves real filename, bytes and MIME for both formats',
      () async {
    final calls = <Map<dynamic, dynamic>>[];
    const ch = MethodChannel('dev.fluttercommunity.plus/share');
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(ch, (call) async {
      calls.add(call.arguments as Map);
      return 'success';
    });
    final api = MoneyNoteApiClient(baseUrl: 'https://example.invalid');
    final state = AppState(api, snapshotRepository: repo);
    final old = await legacy('legacy.money-note-snapshot.json', raw);
    await old.setLastModified(DateTime.utc(2020));
    final items = await repo.save(raw);
    for (final item in items) {
      final path = '${root.path}/snapshots/${item.filename}';
      final before = await File(path).readAsBytes();
      await state.shareLocalSnapshot(item.filename);
      expect(calls.last['mimeTypes'], [snapshotMimeType(item.filename)]);
      expect(calls.last['paths'], [path]);
      expect(await File(path).readAsBytes(), before);
    }
    await state.shareCurrentSnapshot();
    expect(calls.last['mimeTypes'], ['application/gzip']);
    state.dispose();

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(ch, null);
  });
  test('existing 10K fixture roundtrip', () async {
    final path = Platform.environment['P2_N01_FIXTURES'];
    if (path == null) {
      fail('synthetic fixture environment required');
    }
    final bytes = await File('$path/10000-snapshot.raw').readAsBytes();
    final list = await repo.save(bytes);
    final f = File('${root.path}/snapshots/${list.single.filename}');
    expect(gzip.decode(await f.readAsBytes()), bytes);
    expect(await f.length(), lessThan(bytes.length));
    expect(utf8.encode(await repo.readText(list.single.filename)), bytes);
  });
}

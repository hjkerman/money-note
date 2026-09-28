import 'dart:io';
import 'dart:typed_data';

import 'package:path_provider/path_provider.dart';

import 'api_client.dart';

typedef SnapshotDirectoryProvider = Future<Directory> Function();

class LocalSnapshotRepository {
  LocalSnapshotRepository({SnapshotDirectoryProvider? directoryProvider})
      : _directoryProvider =
            directoryProvider ?? getApplicationDocumentsDirectory;

  static const _maxLocalSnapshots = 30;
  final SnapshotDirectoryProvider _directoryProvider;

  Future<List<LocalSnapshotInfo>> save(Uint8List bytes) async {
    final directory = await _snapshotDirectory();
    final backup = File(
        '${directory.path}/money-note-snapshot-${timestampForFilename()}.money-note-snapshot.json');
    await backup.writeAsBytes(bytes, flush: true);
    await _prune();
    return list();
  }

  Future<String> readText(String filename) async =>
      (await safeFile(filename)).readAsString();

  Future<void> delete(String filename) async {
    final snapshot = await safeFile(filename);
    if (await snapshot.exists()) await snapshot.delete();
  }

  Future<void> deleteAll() async {
    for (final snapshot in await list()) {
      final file = await safeFile(snapshot.filename);
      if (await file.exists()) await file.delete();
    }
  }

  Future<List<LocalSnapshotInfo>> list() async {
    final directory = await _snapshotDirectory();
    final items = <LocalSnapshotInfo>[];
    final files = directory
        .listSync()
        .whereType<File>()
        .where((file) => file.path.endsWith('.money-note-snapshot.json'))
        .toList();
    for (final file in files) {
      final stat = await file.stat();
      items.add(LocalSnapshotInfo(
        filename: file.uri.pathSegments.last,
        sizeBytes: stat.size,
        updatedAt: stat.modified,
      ));
    }
    items.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return items;
  }

  Future<File> safeFile(String filename) async {
    final allowed = (await list()).map((snapshot) => snapshot.filename).toSet();
    if (!allowed.contains(filename)) {
      throw MoneyNoteApiException('알 수 없는 스냅샷 파일입니다.');
    }
    final directory = await _snapshotDirectory();
    return File('${directory.path}/$filename');
  }

  Future<void> _prune() async {
    final snapshots = await list();
    for (final snapshot in snapshots.skip(_maxLocalSnapshots)) {
      final file = await safeFile(snapshot.filename);
      if (await file.exists()) await file.delete();
    }
  }

  Future<Directory> _snapshotDirectory() async {
    final base = await _directoryProvider();
    final directory = Directory('${base.path}/snapshots');
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  String timestampForFilename() {
    final now = DateTime.now();
    return '${now.year.toString().padLeft(4, '0')}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}-${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}${now.millisecond.toString().padLeft(3, '0')}';
  }
}

class LocalSnapshotInfo {
  LocalSnapshotInfo({
    required this.filename,
    required this.sizeBytes,
    required this.updatedAt,
  });

  final String filename;
  final int sizeBytes;
  final DateTime updatedAt;
}

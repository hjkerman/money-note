import 'dart:convert';
import 'dart:io';
import 'dart:math';
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
    await _discardStaleTemporaryFiles(directory);
    final random = Random.secure();
    final suffix = List<int>.generate(12, (_) => random.nextInt(256))
        .map((value) => value.toRadixString(16).padLeft(2, '0'))
        .join();
    final basename = 'money-note-snapshot-${timestampForFilename()}-$suffix';
    final temporary = File('${directory.path}/.$basename.pending');
    final backup = File('${directory.path}/$basename.money-note-snapshot.json');
    try {
      await temporary.create(exclusive: true);
      await temporary.writeAsBytes(bytes, flush: true);
      await _validateSnapshotFile(temporary, expectedBytes: bytes);
      await temporary.rename(backup.path);
      await _prune();
      return await list();
    } finally {
      try {
        if (await temporary.exists()) await temporary.delete();
      } on FileSystemException {
        // A failed cleanup must not conceal a successfully published backup.
      }
    }
  }

  Future<String> readText(String filename) async =>
      (await safeFile(filename)).readAsString();

  Future<void> delete(String filename) async {
    final snapshot = await safeFile(filename);
    if (await snapshot.exists()) await snapshot.delete();
  }

  Future<void> deleteAll() async {
    final directory = await _snapshotDirectory();
    for (final file in directory
        .listSync()
        .whereType<File>()
        .where((file) => file.path.endsWith('.money-note-snapshot.json'))) {
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
      try {
        await _validateSnapshotFile(file);
        final stat = await file.stat();
        items.add(LocalSnapshotInfo(
          filename: file.uri.pathSegments.last,
          sizeBytes: stat.size,
          updatedAt: stat.modified,
        ));
      } on FileSystemException {
        // A partial or unreadable old backup is not a share/restore candidate.
      } on FormatException {
        // Server restore remains the final compatibility/integrity authority.
      }
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
    final directory = await _snapshotDirectory();
    for (final snapshot in snapshots.skip(_maxLocalSnapshots)) {
      final file = File('${directory.path}/${snapshot.filename}');
      if (await file.exists()) await file.delete();
    }
  }

  Future<void> _validateSnapshotFile(File file,
      {Uint8List? expectedBytes}) async {
    final bytes = await file.readAsBytes();
    if (expectedBytes != null &&
        (bytes.length != expectedBytes.length ||
            !_sameBytes(bytes, expectedBytes))) {
      throw const FormatException('snapshot write was incomplete');
    }
    final decoded = jsonDecode(utf8.decode(bytes));
    if (decoded is! Map<String, dynamic> ||
        decoded['schema_version'] is! int ||
        decoded['range'] is! Map ||
        decoded['data'] is! Map ||
        decoded['card_charge_policy'] is! Map ||
        decoded['manifest'] is! Map ||
        decoded['manifest']['tables'] is! Map ||
        decoded['manifest']['content_sha256'] is! String ||
        !RegExp(r'^[0-9a-f]{64}$')
            .hasMatch(decoded['manifest']['content_sha256'] as String)) {
      throw const FormatException('snapshot envelope is incomplete');
    }
  }

  bool _sameBytes(List<int> left, List<int> right) {
    for (var index = 0; index < left.length; index += 1) {
      if (left[index] != right[index]) return false;
    }
    return true;
  }

  Future<void> _discardStaleTemporaryFiles(Directory directory) async {
    try {
      final cutoff = DateTime.now().subtract(const Duration(days: 1));
      for (final entity in directory.listSync().whereType<File>()) {
        final filename = entity.uri.pathSegments.last;
        if (!RegExp(r'^\.money-note-snapshot-[A-Za-z0-9-]+\.pending$')
            .hasMatch(filename)) {
          continue;
        }
        try {
          if ((await entity.stat()).modified.isBefore(cutoff)) {
            await entity.delete();
          }
        } on FileSystemException {
          // Stale temporary cleanup is best effort and never prunes backups.
        }
      }
    } on FileSystemException {
      // A cleanup error must not prevent a new backup from being published.
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

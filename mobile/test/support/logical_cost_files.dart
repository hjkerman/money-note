// Explicit synthetic IO scope. Mirrors the SDK's single encode -> write path.
// No second encode, readback, hash, file write or financial transformation.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';

import 'logical_cost_sqlite.dart';

final class _NativeIo extends IOOverrides {}

class CostIo {
  CostIo(this.root, this.costs);
  final Directory root;
  final SqlCosts costs;
  final _native = _NativeIo();
  T run<T>(T Function() body) => IOOverrides.runZoned(body, createFile: (path) {
        final native = _native.createFile(path);
        // Product fixtures pass absolute owned paths. Calling File.absolute
        // here would itself invoke createFile and recursively reenter us.
        if (!path.startsWith('${root.path}/')) {
          return native;
        }
        return _CostFile(native, this);
      });

  void count(String path, String metric, [int n = 1]) {
    final stage = (LogicalCost.activeStage ?? LogicalCostStage.setup).name;
    final category = path.contains('journal.ndjson')
        ? 'journal'
        : path.contains('online-write-')
            ? 'pending'
            : path.contains('e4-source.json')
                ? 'source'
                : path.contains('baseline.json')
                    ? 'baseline'
                    : path.contains('snapshot')
                        ? 'snapshot'
                        : 'other';
    costs
        .forCollector(LogicalCost.activeCollector)
        .add('$stage/file/$category/$metric', n);
  }
}

class _CostFile implements File {
  _CostFile(this.inner, this.owner);
  final File inner;
  final CostIo owner;
  @override
  String get path => inner.path;
  @override
  Uri get uri => inner.uri;
  @override
  File get absolute => _CostFile(inner.absolute, owner);
  @override
  Directory get parent => inner.parent;
  @override
  Future<bool> exists() => inner.exists();
  @override
  bool existsSync() => inner.existsSync();
  @override
  Future<int> length() => inner.length();
  @override
  int lengthSync() => inner.lengthSync();
  @override
  Future<FileStat> stat() => inner.stat();
  @override
  FileStat statSync() => inner.statSync();
  @override
  Future<String> resolveSymbolicLinks() => inner.resolveSymbolicLinks();
  @override
  String resolveSymbolicLinksSync() => inner.resolveSymbolicLinksSync();
  @override
  Future<Uint8List> readAsBytes() async {
    final bytes = await inner.readAsBytes();
    owner.count(path, 'readBytes', bytes.length);
    return bytes;
  }

  @override
  Uint8List readAsBytesSync() {
    final bytes = inner.readAsBytesSync();
    owner.count(path, 'readBytes', bytes.length);
    return bytes;
  }

  String _decode(List<int> bytes, Encoding encoding) {
    owner.count(path, 'decodeSubmittedBytes', bytes.length);
    try {
      final value = encoding.decode(bytes);
      owner.count(path, 'decodeCompletedBytes', bytes.length);
      return value;
    } catch (_) {
      owner.count(path, 'decodeFailedSubmittedBytes', bytes.length);
      throw FileSystemException(
          "Failed to decode data using encoding '${encoding.name}'", path);
    }
  }

  @override
  Future<String> readAsString({Encoding encoding = utf8}) async =>
      _decode(await readAsBytes(), encoding);
  @override
  String readAsStringSync({Encoding encoding = utf8}) =>
      _decode(readAsBytesSync(), encoding);
  @override
  Future<File> create({bool recursive = false, bool exclusive = false}) async {
    await inner.create(recursive: recursive, exclusive: exclusive);
    return this;
  }

  @override
  void createSync({bool recursive = false, bool exclusive = false}) =>
      inner.createSync(recursive: recursive, exclusive: exclusive);
  @override
  Future<FileSystemEntity> delete({bool recursive = false}) async {
    await inner.delete(recursive: recursive);
    owner.count(path, 'deletes');
    return this;
  }

  @override
  void deleteSync({bool recursive = false}) {
    inner.deleteSync(recursive: recursive);
    owner.count(path, 'deletes');
  }

  @override
  Future<File> rename(String target) async {
    final renamed = await inner.rename(target);
    owner.count(path, 'publishedRenames');
    return _CostFile(renamed, owner);
  }

  @override
  File renameSync(String target) {
    final renamed = inner.renameSync(target);
    owner.count(path, 'publishedRenames');
    return _CostFile(renamed, owner);
  }

  @override
  Future<RandomAccessFile> open({FileMode mode = FileMode.read}) async =>
      _CostRaf(await inner.open(mode: mode), owner, path);
  @override
  RandomAccessFile openSync({FileMode mode = FileMode.read}) =>
      _CostRaf(inner.openSync(mode: mode), owner, path);
  @override
  Future<File> writeAsBytes(List<int> bytes,
      {FileMode mode = FileMode.write, bool flush = false}) {
    return open(mode: mode)
        .then((file) => file.writeFrom(bytes, 0, bytes.length).then<File>((_) {
              if (flush) return file.flush().then((_) => this);
              return this;
            }).whenComplete(file.close));
  }

  @override
  void writeAsBytesSync(List<int> bytes,
      {FileMode mode = FileMode.write, bool flush = false}) {
    final file = openSync(mode: mode);
    try {
      file.writeFromSync(bytes, 0, bytes.length);
      if (flush) file.flushSync();
    } finally {
      file.closeSync();
    }
  }

  @override
  Future<File> writeAsString(String contents,
      {FileMode mode = FileMode.write,
      Encoding encoding = utf8,
      bool flush = false}) {
    try {
      return writeAsBytes(encoding.encode(contents), mode: mode, flush: flush);
    } catch (error, stack) {
      return Future.error(error, stack);
    }
  }

  @override
  void writeAsStringSync(String contents,
          {FileMode mode = FileMode.write,
          Encoding encoding = utf8,
          bool flush = false}) =>
      writeAsBytesSync(encoding.encode(contents), mode: mode, flush: flush);
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnsupportedError(
      'B03 unobserved File API: ${invocation.memberName}');
}

class _CostRaf implements RandomAccessFile {
  _CostRaf(this.inner, this.owner, this.path);
  final RandomAccessFile inner;
  final CostIo owner;
  @override
  final String path;
  @override
  Future<RandomAccessFile> writeFrom(List<int> buffer,
      [int start = 0, int? end]) async {
    end ??= buffer.length;
    // Counter arithmetic only; native SDK owns range admission exactly once.
    final span =
        start >= 0 && end >= start && end <= buffer.length ? end - start : null;
    if (span != null) owner.count(path, 'submittedBytes', span);
    try {
      await inner.writeFrom(buffer, start, end);
      if (span != null) owner.count(path, 'completedBytes', span);
    } catch (_) {
      owner.count(path, 'failedWrites');
      rethrow;
    }
    return this;
  }

  @override
  void writeFromSync(List<int> buffer, [int start = 0, int? end]) {
    end ??= buffer.length;
    final span =
        start >= 0 && end >= start && end <= buffer.length ? end - start : null;
    if (span != null) owner.count(path, 'submittedBytes', span);
    try {
      inner.writeFromSync(buffer, start, end);
      if (span != null) owner.count(path, 'completedBytes', span);
    } catch (_) {
      owner.count(path, 'failedWrites');
      rethrow;
    }
  }

  @override
  Future<RandomAccessFile> writeString(String value,
          {Encoding encoding = utf8}) =>
      writeFrom(encoding.encode(value));
  @override
  void writeStringSync(String value, {Encoding encoding = utf8}) =>
      writeFromSync(encoding.encode(value));
  @override
  Future<RandomAccessFile> writeByte(int value) async {
    owner.count(path, 'submittedBytes', 1);
    try {
      await inner.writeByte(value);
      owner.count(path, 'completedBytes', 1);
    } catch (_) {
      owner.count(path, 'failedWrites');
      rethrow;
    }
    return this;
  }

  @override
  int writeByteSync(int value) {
    owner.count(path, 'submittedBytes', 1);
    try {
      final result = inner.writeByteSync(value);
      owner.count(path, 'completedBytes', 1);
      return result;
    } catch (_) {
      owner.count(path, 'failedWrites');
      rethrow;
    }
  }

  @override
  Future<RandomAccessFile> flush() async {
    await inner.flush();
    owner.count(path, 'flushes');
    return this;
  }

  @override
  void flushSync() {
    inner.flushSync();
    owner.count(path, 'flushes');
  }

  @override
  Future<void> close() => inner.close();
  @override
  void closeSync() => inner.closeSync();
  @override
  Future<RandomAccessFile> truncate(int length) async {
    await inner.truncate(length);
    owner.count(path, 'truncates');
    return this;
  }

  @override
  void truncateSync(int length) {
    inner.truncateSync(length);
    owner.count(path, 'truncates');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnsupportedError(
      'B03 unobserved RandomAccessFile API: ${invocation.memberName}');
}

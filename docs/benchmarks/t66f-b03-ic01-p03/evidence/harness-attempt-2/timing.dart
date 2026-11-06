import 'dart:ffi';

import 'package:sqlite3/sqlite3.dart';

// Same SQL timing boundary in both modes. No additional product SQL/hash/parse.
class TimedDatabase implements Database {
  TimedDatabase(this.inner);
  final Database inner;
  int sqlUs = 0, calls = 0, callbackUs = 0, callbackCalls = 0;
  T timed<T>(T Function() f) {
    final w = Stopwatch()..start();
    try {
      return f();
    } finally {
      sqlUs += w.elapsedMicroseconds;
      calls++;
    }
  }

  @override
  void execute(String s, [List<Object?> p = const []]) =>
      timed(() => inner.execute(s, p));
  @override
  ResultSet select(String s, [List<Object?> p = const []]) =>
      timed(() => inner.select(s, p));
  @override
  PreparedStatement prepare(
    String s, {
    bool persistent = false,
    bool vtab = true,
    bool checkNoTail = false,
  }) => inner.prepare(
    s,
    persistent: persistent,
    vtab: vtab,
    checkNoTail: checkNoTail,
  );
  @override
  void createFunction({
    required String functionName,
    required ScalarFunction function,
    AllowedArgumentCount argumentCount = const AllowedArgumentCount.any(),
    bool deterministic = false,
    bool directOnly = true,
    bool subtype = false,
  }) => inner.createFunction(
    functionName: functionName,
    argumentCount: argumentCount,
    deterministic: deterministic,
    directOnly: directOnly,
    subtype: subtype,
    function: (args) {
      final w = Stopwatch()..start();
      try {
        return function(args);
      } finally {
        callbackUs += w.elapsedMicroseconds;
        callbackCalls++;
      }
    },
  );
  @override
  void close() => inner.close();
  @override
  bool get autocommit => inner.autocommit;
  @override
  int get updatedRows => inner.updatedRows;
  @override
  int get userVersion => inner.userVersion;
  @override
  set userVersion(int n) => inner.userVersion = n;
  @override
  Pointer<void> get handle => inner.handle;
  @override
  int get lastInsertRowId => inner.lastInsertRowId;
  @override
  DatabaseConfig get config => inner.config;
  @override
  dynamic noSuchMethod(Invocation i) =>
      throw UnsupportedError('P03 timing ${i.memberName}');
}

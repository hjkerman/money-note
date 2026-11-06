// Synthetic verification only. Observes the original SQLite connection, not a copy.
import 'dart:ffi';

import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';

class SqlCosts {
  LogicalCost? _primaryOwner;
  final _scopes = Expando<SqlCosts>();
  SqlCosts forCollector(LogicalCost? owner) {
    if (owner == null) return this;
    _primaryOwner ??= owner;
    if (identical(_primaryOwner, owner)) return this;
    return _scopes[owner] ??= (SqlCosts().._primaryOwner = owner);
  }

  final Map<String, BigInt> values = {};
  bool get isClosed => _primaryOwner?.isClosed ?? false;
  void add(String key, [int amount = 1]) {
    if (!isClosed) {
      values[key] = (values[key] ?? BigInt.zero) + BigInt.from(amount);
    }
  }

  Map<String, String> snapshot() =>
      {for (final k in (values.keys.toList()..sort())) k: values[k].toString()};
}

// TEMP triggers observe actual NEW value lengths, including SQL literals,
// trigger updates, cascades and WITHOUT ROWID tables. No rows are persisted.
// Only BLOB/TEXT have payload-byte metrics; scalars are counted, not guessed.
class CostDatabase implements Database {
  CostDatabase(this.inner, this.costs) {
    inner.createFunction(
        functionName: 'b03_observe_row',
        argumentCount: const AllowedArgumentCount(8),
        directOnly: false,
        function: (args) {
          final timing = args[0] as String, table = args[1] as String;
          final op = args[2] as String;
          final key = '$_stage/$table/$op/$timing';
          final meter = costs.forCollector(LogicalCost.activeCollector);
          meter.add('$key/rows');
          for (var i = 3; i < 8; i++) {
            const labels = [
              'blobBytes',
              'textBytes',
              'scalarValues',
              'nullValues',
              'columns'
            ];
            final n = args[i] as int;
            meter.add('$key/${labels[i - 3]}', n);
            if (timing == 'effective') {
              final p = '$_stage/$table/$op/${labels[i - 3]}';
              final owned = (meter, p);
              _pending[owned] =
                  (_pending[owned] ?? BigInt.zero) + BigInt.from(n);
            }
          }
          return null;
        });
  }

  final Database inner;
  final SqlCosts costs;
  final Set<String> _tables = {};
  final Map<(SqlCosts, String), BigInt> _pending = {};
  final List<(String, Map<(SqlCosts, String), BigInt>)> _savepoints = [];
  String _stage = LogicalCostStage.setup.name;
  bool _schemaDirty = true;

  static String _quote(String name) => '"${name.replaceAll('"', '""')}"';

  void _install() {
    for (final row in inner.select(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")) {
      final table = row['name'] as String;
      if (_tables.contains(table)) continue;
      if (_tables.length >= 128) {
        throw StateError('B03 table capacity exceeded');
      }
      final columns = inner
          .select('PRAGMA table_info(${_quote(table)})')
          .map((r) => r['name'] as String)
          .toList();
      String sum(String predicate, {bool lengths = false}) => columns.map((c) {
            final value = 'NEW.${_quote(c)}';
            return 'CASE WHEN typeof($value) $predicate THEN ${lengths ? 'length(CAST($value AS BLOB))' : '1'} ELSE 0 END';
          }).join('+');
      for (final op in ['INSERT', 'UPDATE', 'DELETE']) {
        for (final timing in ['attempted', 'effective']) {
          final values = op == 'DELETE'
              ? '0,0,0,0,0'
              : [
                  sum("='blob'", lengths: true),
                  sum("='text'", lengths: true),
                  sum("IN ('integer','real')"),
                  sum("='null'"),
                  '${columns.length}'
                ].join(',');
          final trigger = _quote('b03_${table}_${op}_$timing');
          inner.execute(
              'CREATE TEMP TRIGGER $trigger ${timing == 'attempted' ? 'BEFORE' : 'AFTER'} $op ON main.${_quote(table)} BEGIN SELECT b03_observe_row(\'$timing\',\'$table\',\'$op\',$values); END;');
          costs.add('observer/setupStatements');
        }
      }
      _tables.add(table);
    }
  }

  void _settle(String outcome, Map<(SqlCosts, String), BigInt> values) {
    for (final e in values.entries) {
      if (e.key.$1.isClosed) continue;
      final target = e.key.$1.values, key = '${e.key.$2}/$outcome';
      target[key] = (target[key] ?? BigInt.zero) + e.value;
    }
  }

  T _call<T>(String sql, List<Object?> parameters, T Function() body) {
    _stage = (LogicalCost.activeStage ?? LogicalCostStage.setup).name;
    final meter = costs.forCollector(LogicalCost.activeCollector);
    meter.add('$_stage/sql/statements');
    for (final value in parameters) {
      if (value is String) {
        meter.add('$_stage/sql/bindTextCodeUnits', value.length);
      } else if (value is List<int>) {
        meter.add('$_stage/sql/bindBlobBytes', value.length);
      } else {
        meter.add('$_stage/sql/scalarOrNullBinds');
      }
    }
    final before = Map<(SqlCosts, String), BigInt>.of(_pending);
    final words = sql.trimLeft().split(RegExp(r'\s+'));
    final verb = words.first.toUpperCase();
    if (_schemaDirty &&
        const ['INSERT', 'UPDATE', 'DELETE', 'REPLACE'].contains(verb)) {
      _install();
      _schemaDirty = false;
    }
    try {
      final result = body();
      if (verb == 'SAVEPOINT') {
        if (_savepoints.length >= 32) {
          throw StateError('B03 savepoint capacity exceeded');
        }
        _savepoints.add((words[1], before));
      } else if (verb == 'ROLLBACK' && words.length > 1) {
        final index = _savepoints.indexWhere((p) => p.$1 == words.last);
        final saved = _savepoints[index].$2;
        _settle('rolledBack', {
          for (final e in _pending.entries)
            e.key: e.value - (saved[e.key] ?? BigInt.zero)
        });
        _pending
          ..clear()
          ..addAll(saved);
        _savepoints.removeRange(index + 1, _savepoints.length);
      } else if (verb == 'ROLLBACK') {
        _settle('rolledBack', _pending);
        _pending.clear();
        _savepoints.clear();
      } else if (verb == 'RELEASE') {
        final index = _savepoints.indexWhere((p) => p.$1 == words.last);
        _savepoints.removeRange(index, _savepoints.length);
      }
      if (inner.autocommit) {
        _settle('committed', _pending);
        _pending.clear();
      }
      if (RegExp(r'\b(CREATE|ALTER)\s', caseSensitive: false).hasMatch(sql)) {
        _schemaDirty = true;
      }
      return result;
    } catch (_) {
      meter.add('$_stage/sql/failedStatements');
      if (inner.autocommit) {
        _settle('rolledBack', _pending);
        _pending.clear();
      } else {
        _settle('statementRolledBack', {
          for (final e in _pending.entries)
            e.key: e.value - (before[e.key] ?? BigInt.zero)
        });
        _pending
          ..clear()
          ..addAll(before);
      }
      rethrow;
    }
  }

  @override
  void execute(String sql, [List<Object?> parameters = const []]) =>
      _call(sql, parameters, () => inner.execute(sql, parameters));
  @override
  ResultSet select(String sql, [List<Object?> parameters = const []]) =>
      _call(sql, parameters, () => inner.select(sql, parameters));
  @override
  PreparedStatement prepare(String sql,
          {bool persistent = false,
          bool vtab = true,
          bool checkNoTail = false}) =>
      CostStatement(
          this,
          inner.prepare(sql,
              persistent: persistent, vtab: vtab, checkNoTail: checkNoTail));
  @override
  void close() {
    inner.close();
    _settle('rolledBackOnClose', _pending);
    _pending.clear();
  }

  @override
  bool get autocommit => inner.autocommit;
  @override
  int get updatedRows => inner.updatedRows;
  @override
  int get userVersion => inner.userVersion;
  @override
  set userVersion(int value) => execute('PRAGMA user_version=$value');
  @override
  Pointer<void> get handle => inner.handle;
  @override
  int get lastInsertRowId => inner.lastInsertRowId;
  @override
  DatabaseConfig get config => inner.config;
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('Unobserved SQLite API: ${invocation.memberName}');
}

class CostStatement implements PreparedStatement {
  CostStatement(this.database, this.inner);
  final CostDatabase database;
  final PreparedStatement inner;
  @override
  String get sql => inner.sql;
  @override
  int get parameterCount => inner.parameterCount;
  @override
  bool get isReadOnly => inner.isReadOnly;
  @override
  void execute([List<Object?> parameters = const []]) =>
      database._call(sql, parameters, () => inner.execute(parameters));
  @override
  ResultSet select([List<Object?> parameters = const []]) =>
      database._call(sql, parameters, () => inner.select(parameters));
  @override
  void close() => inner.close();
  @override
  void reset() => inner.reset();
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnsupportedError(
      'Unobserved statement API: ${invocation.memberName}');
}

// Synthetic verification only. Observes the original SQLite connection, not a copy.
import 'dart:ffi';

import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';

// Only the statement/control prefix is needed. Never rewrite executed SQL.
List<String> costSqlWords(String sql) {
  final words = <String>[];
  var i = 0;
  while (i < sql.length && words.length < 6) {
    if (sql.codeUnitAt(i) <= 32 || sql[i] == ';') {
      i++;
    } else if (sql.startsWith('--', i)) {
      final end = sql.indexOf('\n', i + 2);
      i = end < 0 ? sql.length : end + 1;
    } else if (sql.startsWith('/*', i)) {
      final end = sql.indexOf('*/', i + 2);
      i = end < 0 ? sql.length : end + 2;
    } else if ('"\'`['.contains(sql[i])) {
      final quote = sql[i] == '[' ? ']' : sql[i];
      i++;
      final value = StringBuffer();
      while (i < sql.length) {
        final ch = sql[i++];
        if (ch == quote) {
          if (i < sql.length && sql[i] == ch && ch != ']') {
            i++;
          } else {
            break;
          }
        }
        value.write(ch);
      }
      words.add(_asciiLower(value.toString()));
    } else {
      final start = i;
      while (i < sql.length && _word(sql.codeUnitAt(i))) {
        i++;
      }
      if (i == start) break;
      words.add(_asciiLower(sql.substring(start, i)));
    }
  }
  return words;
}

bool _word(int c) =>
    c >= 128 ||
    c == 95 ||
    (c >= 48 && c <= 57) ||
    (c >= 65 && c <= 90) ||
    (c >= 97 && c <= 122);
String _asciiLower(String s) => s.replaceAllMapped(
    RegExp('[A-Z]'), (m) => String.fromCharCode(m[0]!.codeUnitAt(0) + 32));

bool _multipleStatements(String sql) {
  if (!sql.contains(';')) return false;
  var i = 0;
  while (i < sql.length) {
    if (sql.startsWith('--', i)) {
      final end = sql.indexOf('\n', i + 2);
      i = end < 0 ? sql.length : end + 1;
    } else if (sql.startsWith('/*', i)) {
      final end = sql.indexOf('*/', i + 2);
      i = end < 0 ? sql.length : end + 2;
    } else if ('"\'`['.contains(sql[i])) {
      final quote = sql[i] == '[' ? ']' : sql[i];
      i++;
      while (i < sql.length) {
        if (sql[i++] == quote) {
          if (i < sql.length && sql[i] == quote && quote != ']') {
            i++;
          } else {
            break;
          }
        }
      }
    } else if (sql[i++] == ';') {
      return costSqlWords(sql.substring(i)).isNotEmpty;
    }
  }
  return false;
}

bool _preservesFailedPrefix(List<String> words, Object error) =>
    words.length >= 3 &&
    words[1] == 'or' &&
    words[2] == 'fail' &&
    error is SqliteException &&
    // Native CHECK/NOTNULL/PRIMARYKEY/UNIQUE; FK/trigger ABORT overrides FAIL.
    const {275, 1299, 1555, 2067}.contains(error.extendedResultCode);

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
  CostDatabase(this.inner, this.costs, {this.statementCapacity = 32}) {
    if (statementCapacity < 0 || statementCapacity > 32) {
      throw ArgumentError.value(
          statementCapacity, 'statementCapacity', '0..32');
    }
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
              _owners.add(meter);
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
  // Diagnostic connection-owned LRU. No result or attribution context is cached.
  // Capacity zero is the exact original execute/select path for paired oracles.
  final int statementCapacity;
  final Map<String, PreparedStatement> _statements = {};
  final Set<PreparedStatement> _executing = {};
  final Map<String, int> statementReuse = {
    'hits': 0,
    'misses': 0,
    'evictions': 0,
    'created': 0,
    'finalized': 0,
    'peakLive': 0,
    'capacityRejections': 0,
  };
  bool _closed = false;

  void _finalize(PreparedStatement statement) {
    statement.close();
    statementReuse['finalized'] = statementReuse['finalized']! + 1;
  }

  T _prepared<T>(String sql, List<Object?> parameters,
      T Function(PreparedStatement) body, T Function() original) {
    if (_closed || statementCapacity == 0 || sql.length > 16384) {
      return original();
    }
    var statement = _statements.remove(sql);
    if (statement != null && _executing.contains(statement)) {
      _statements[sql] = statement;
      statementReuse['capacityRejections'] =
          statementReuse['capacityRejections']! + 1;
      throw StateError(
          'B03 reentrant prepared statement; measurement incomplete');
    }
    if (statement == null) {
      statementReuse['misses'] = statementReuse['misses']! + 1;
      if (_statements.length == statementCapacity) {
        final idle =
            _statements.entries.where((e) => !_executing.contains(e.value));
        if (idle.isEmpty) {
          statementReuse['capacityRejections'] =
              statementReuse['capacityRejections']! + 1;
          throw StateError(
              'B03 active statement capacity; measurement incomplete');
        }
        final evicted = idle.first;
        _statements.remove(evicted.key);
        _finalize(evicted.value);
        statementReuse['evictions'] = statementReuse['evictions']! + 1;
      }
      statement = inner.prepare(sql, persistent: true, checkNoTail: true);
      statementReuse['created'] = statementReuse['created']! + 1;
    } else {
      statementReuse['hits'] = statementReuse['hits']! + 1;
    }
    _statements[sql] = statement;
    final live = _statements.length;
    if (live > statementReuse['peakLive']!) statementReuse['peakLive'] = live;
    _executing.add(statement);
    try {
      final result = body(statement);
      // Driver reset/rebinds all indexed parameters on every execution. Clear
      // native bindings AND Dart debug arguments so idle handles retain no BLOB.
      statement.reset();
      for (var i = 1; i <= statement.parameterCount; i++) {
        statement.raw.bindNull(i);
      }
      statement.raw.debugParameters = const [];
      return result;
    } catch (_) {
      _statements.remove(sql);
      _finalize(statement);
      rethrow;
    } finally {
      _executing.remove(statement);
    }
  }

  final Set<String> _tables = {};
  final Map<(SqlCosts, String), BigInt> _pending = {};
  final Set<SqlCosts> _owners = {};
  static const transactionOwnerLimit = 32;
  final List<(String, Map<(SqlCosts, String), BigInt>)> _savepoints = [];
  String _stage = LogicalCostStage.setup.name;
  bool _schemaDirty = true;
  int? _schemaVersion;

  static String _quote(String name) => '"${name.replaceAll('"', '""')}"';

  void _install() {
    // Refresh schema-derived TEMP triggers after DDL. IF NOT EXISTS alone
    // would preserve NEW-column expressions built before an ALTER TABLE.
    for (final table in _tables.toList()) {
      for (final op in ['INSERT', 'UPDATE', 'DELETE']) {
        for (final timing in ['attempted', 'effective']) {
          final trigger = _quote('b03_${table}_${op}_$timing');
          inner.execute('DROP TRIGGER IF EXISTS temp.$trigger');
          costs.add('observer/setupStatements');
        }
      }
    }
    _tables.clear();
    for (final row in inner
        .select('SELECT sql FROM sqlite_master WHERE sql IS NOT NULL')) {
      if (RegExp(r'\bON\s+CONFLICT\s+FAIL\b|\bRAISE\s*\(\s*FAIL\b',
              caseSensitive: false)
          .hasMatch(row['sql'] as String)) {
        throw StateError('B03 unsupported schema conflict mode');
      }
    }
    for (final row in inner.select(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")) {
      final table = row['name'] as String;
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
              'CREATE TEMP TRIGGER IF NOT EXISTS $trigger ${timing == 'attempted' ? 'BEFORE' : 'AFTER'} $op ON main.${_quote(table)} BEGIN SELECT b03_observe_row(\'$timing\',\'$table\',\'$op\',$values); END;');
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
    final words = costSqlWords(sql);
    final verb = words.isEmpty ? '' : words.first.toUpperCase();
    if (const ['INSERT', 'UPDATE', 'DELETE', 'REPLACE'].contains(verb) &&
        _multipleStatements(sql)) {
      meter.add('$_stage/coverage/multipleStatements');
      throw StateError(
          'B03 unsupported multiple DML statements; measurement incomplete');
    }
    if (verb == 'SAVEPOINT' && _savepoints.length >= 32) {
      throw StateError('B03 savepoint capacity exceeded');
    }
    if (const ['INSERT', 'UPDATE', 'DELETE', 'REPLACE'].contains(verb) &&
        !_owners.contains(meter) &&
        _owners.length >= transactionOwnerLimit) {
      meter.add('$_stage/coverage/transactionOwnerCapacity');
      throw StateError(
          'B03 transaction owner capacity exceeded; measurement incomplete');
    }
    if (const ['INSERT', 'UPDATE', 'DELETE', 'REPLACE'].contains(verb)) {
      // A scalar connection-local cookie also detects committed DDL from
      // another connection. Observer reads are not application SQL work.
      final version = inner
          .select('PRAGMA main.schema_version')
          .single['schema_version'] as int;
      meter.add('$_stage/observer/schemaChecks');
      if (_schemaVersion != null && version != _schemaVersion) {
        meter.add('$_stage/coverage/externalSchemaChange');
        throw StateError('B03 external schema change; measurement incomplete');
      }
      if (_schemaDirty || version != _schemaVersion) {
        _install();
        _schemaVersion = version;
        _schemaDirty = false;
      }
    }
    final wasInTransaction = !inner.autocommit;
    try {
      final result = body();
      if (verb == 'SAVEPOINT') {
        _savepoints.add((words[1], before));
      } else if (verb == 'ROLLBACK' && words.contains('to')) {
        final index = _savepoints.lastIndexWhere((p) => p.$1 == words.last);
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
        final index = _savepoints.lastIndexWhere((p) => p.$1 == words.last);
        _savepoints.removeRange(index, _savepoints.length);
      }
      if (inner.autocommit) {
        _settle('committed', _pending);
        _pending.clear();
        _owners.clear();
        _savepoints.clear();
      }
      if (const ['CREATE', 'ALTER', 'DROP', 'ROLLBACK'].contains(verb)) {
        _schemaDirty = true;
        _schemaVersion = null;
        if (verb == 'ROLLBACK' && inner.autocommit) _owners.clear();
      }
      return result;
    } catch (error) {
      meter.add('$_stage/sql/failedStatements');
      if (_preservesFailedPrefix(words, error)) {
        if (inner.autocommit) {
          _settle('committed', _pending);
          _pending.clear();
        }
      } else if (inner.autocommit) {
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
      if (inner.autocommit) {
        if (wasInTransaction) _schemaVersion = null;
        _owners.clear();
        _savepoints.clear();
        _schemaDirty = true;
      }
      rethrow;
    }
  }

  @override
  void execute(String sql, [List<Object?> parameters = const []]) => _call(
      sql,
      parameters,
      () => parameters.isEmpty
          ? inner.execute(
              sql, parameters) // Keep sqlite3_exec/multi-DDL semantics.
          : _prepared(sql, parameters, (s) => s.execute(parameters),
              () => inner.execute(sql, parameters)));
  @override
  ResultSet select(String sql, [List<Object?> parameters = const []]) => _call(
      sql,
      parameters,
      () => _prepared(sql, parameters, (s) => s.select(parameters),
          () => inner.select(sql, parameters)));
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
    if (_executing.isNotEmpty) {
      throw StateError('B03 cannot close active diagnostic statement');
    }
    for (final statement in _statements.values) {
      _finalize(statement);
    }
    _statements.clear();
    _closed = true;
    inner.close();
    _settle('rolledBackOnClose', _pending);
    _pending.clear();
    _savepoints.clear();
    _owners.clear();
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

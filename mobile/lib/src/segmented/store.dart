// Isolated segmented-store/1. Intentionally has NO accepted pointer or app DI.
import 'dart:io';
import 'dart:typed_data';

import 'package:sqlite3/sqlite3.dart';

import 'c1.dart';
import 'object.dart';
import 'protocol.dart';

class ClientStoreLimits {
  const ClientStoreLimits(
      {this.objectBytes = 64 * 1024 * 1024,
      this.totalObjectBytes = 512 * 1024 * 1024,
      this.objectCount = 100000,
      this.manifestBytes = 8 * 1024 * 1024,
      this.metadataBytes = 32 * 1024 * 1024,
      this.stagingCount = 128,
      this.databasePages = 262144,
      this.busyMilliseconds = 1000});
  // Local resource policy, NOT server object-format or financial-input limits.
  final int objectBytes,
      totalObjectBytes,
      objectCount,
      manifestBytes,
      metadataBytes,
      stagingCount,
      databasePages,
      busyMilliseconds;
  void validate() {
    if ([
          objectBytes,
          totalObjectBytes,
          objectCount,
          manifestBytes,
          metadataBytes,
          stagingCount,
          databasePages,
          busyMilliseconds
        ].any((n) => n <= 0) ||
        busyMilliseconds > 10000 ||
        objectBytes > totalObjectBytes ||
        manifestBytes > metadataBytes) {
      rejectSegment('LOCAL_LIMIT_INVALID');
    }
  }
}

typedef StoreFault = void Function(String point);

class StagingSession {
  const StagingSession(
      this.id, this.manifest, this.createdAt, this.objectCount);
  final String id; // Local UUID, not observation ID or Target.sync_root.
  final ObservationManifest manifest;
  final DateTime createdAt;
  final int objectCount;
  String get validationState => 'staged'; // Never complete or active in E1.
}

class StoreHealth {
  const StoreHealth(this.objectsChecked, this.stagingsChecked, this.issues);
  final int objectsChecked, stagingsChecked;
  final List<String>
      issues; // No row values, credentials, or financial content.
  bool get healthy => issues.isEmpty;
}

class SegmentedClientStore {
  SegmentedClientStore._(
      this._db, this.path, this.cache, this.limits, this._fault);
  static const discriminator = 'segmented-store/1';
  static const schemaVersion = 1;
  final Database _db;
  final String path;
  final CacheNamespace cache;
  final ClientStoreLimits limits;
  final StoreFault? _fault;
  bool _closed = false;

  // Caller chooses a private root; never invoked by ordinary application startup.
  static SegmentedClientStore open(Directory privateRoot, CacheNamespace cache,
      {ClientStoreLimits limits = const ClientStoreLimits(),
      StoreFault? fault}) {
    limits.validate();
    final directory = Directory('${privateRoot.path}/segmented-store-v1')
      ..createSync(recursive: true);
    final path = '${directory.path}/${cache.key}.sqlite';
    Database? db;
    try {
      db = sqlite3.open(path);
      db.execute('PRAGMA busy_timeout=${limits.busyMilliseconds}');
      final version = db.select('PRAGMA user_version').single.values.first;
      final tables = db.select(
          "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'");
      if (version != 0 && version != schemaVersion) {
        rejectSegment('UNSUPPORTED_STORAGE_SCHEMA');
      }
      if (version == 0 && tables.isNotEmpty) {
        rejectSegment('STORE_PROFILE_INVALID');
      }
      db.execute('PRAGMA foreign_keys=ON');
      db.execute('PRAGMA synchronous=EXTRA');
      if (db.select('PRAGMA journal_mode').single.values.first != 'delete') {
        db.execute('PRAGMA journal_mode=DELETE');
      }
      if (db.select('PRAGMA journal_mode').single.values.first != 'delete' ||
          db.select('PRAGMA synchronous').single.values.first != 3 ||
          db.select('PRAGMA foreign_keys').single.values.first != 1) {
        rejectSegment('STORE_DURABILITY_UNAVAILABLE');
      }
      db.execute('BEGIN IMMEDIATE');
      try {
        // Another creator may have initialized while we waited for its lock.
        final lockedVersion =
            db.select('PRAGMA user_version').single.values.first;
        if (lockedVersion != 0 && lockedVersion != schemaVersion) {
          rejectSegment('UNSUPPORTED_STORAGE_SCHEMA');
        }
        if (lockedVersion == 0) {
          db.execute(_schema);
          db.execute('PRAGMA user_version=1');
          db.execute('INSERT INTO profile VALUES(1,?,?,?)',
              [discriminator, cache.key, VerifiedObject.validatorBuild]);
        }
        final profile = db.select('SELECT * FROM profile');
        if (profile.length != 1 ||
            profile.single['discriminator'] != discriminator ||
            profile.single['namespace'] != cache.key ||
            profile.single['validator'] != VerifiedObject.validatorBuild) {
          rejectSegment('STORE_PROFILE_INVALID');
        }
        if (db.select('PRAGMA quick_check').single.values.first != 'ok' ||
            db.select('PRAGMA foreign_key_check').isNotEmpty) {
          rejectSegment('STORE_CORRUPT');
        }
        final actualTables = db
            .select("SELECT name FROM sqlite_master WHERE type='table'")
            .map((r) => r['name'])
            .toSet();
        if (actualTables.length != 8 ||
            !actualTables.containsAll([
              'profile',
              'refs',
              'objects',
              'edges',
              'staging',
              'staging_roots',
              'staging_objects',
              'usage'
            ])) {
          rejectSegment('STORE_PROFILE_INVALID');
        }
        if (!_usageValid(db)) {
          rejectSegment('STORE_METADATA_CORRUPT');
        }
        db.execute('COMMIT');
      } catch (_) {
        db.execute('ROLLBACK');
        rethrow;
      }
      if (db
              .select('PRAGMA max_page_count=${limits.databasePages}')
              .single
              .values
              .first !=
          limits.databasePages) {
        rejectSegment('LOCAL_STORAGE_BUDGET');
      }
      return SegmentedClientStore._(db, path, cache, limits, fault);
    } on SqliteException catch (error) {
      db?.close();
      rejectSegment(error.resultCode == 5 || error.resultCode == 6
          ? 'STORE_BUSY'
          : 'PERSISTENCE_FAILED');
    } catch (_) {
      db?.close();
      rethrow;
    }
  }

  T _transaction<T>(T Function() body) {
    if (_closed) rejectSegment('STORE_CLOSED');
    var begun = false;
    try {
      _db.execute('BEGIN IMMEDIATE');
      begun = true;
      final result = body();
      final usage = _db.select('SELECT * FROM usage WHERE id=1').single;
      if ((usage['objects'] as int) > limits.objectCount ||
          (usage['payload'] as int) > limits.totalObjectBytes) {
        rejectSegment('LOCAL_STORAGE_BUDGET');
      }
      if ((usage['stages'] as int) > limits.stagingCount ||
          (usage['metadata'] as int) > limits.metadataBytes) {
        rejectSegment('LOCAL_METADATA_BUDGET');
      }
      _fault?.call('before_commit');
      _db.execute('COMMIT');
      begun = false;
      _fault?.call('after_commit');
      return result;
    } on SqliteException catch (error) {
      throw SegmentedException(
          error.resultCode == 5 || error.resultCode == 6
              ? 'STORE_BUSY'
              : 'PERSISTENCE_FAILED',
          storageCode: error.extendedResultCode);
    } finally {
      if (begun) {
        // SQLITE_FULL can already have rolled back; do not conceal the error.
        try {
          _db.execute('ROLLBACK');
        } on SqliteException {/* already aborted */}
      }
    }
  }

  void _reference(ObjectRef ref) {
    final rows = _db.select('SELECT bytes FROM refs WHERE hash=?', [ref.hash]);
    if (rows.isNotEmpty && rows.single['bytes'] != ref.bytes) {
      rejectSegment('OBJECT_REF_CONFLICT');
    }
    _db.execute(
        'INSERT OR IGNORE INTO refs VALUES(?,?)', [ref.hash, ref.bytes]);
  }

  VerifiedObject putVerifiedObject(ObjectRef ref, List<int> bytes) {
    final verified =
        VerifiedObject.verify(bytes, ref, cache, maxBytes: limits.objectBytes);
    return _transaction(() {
      final old =
          _db.select('SELECT body FROM objects WHERE hash=?', [ref.hash]);
      if (old.isNotEmpty) {
        if (!sameBytes(old.single['body'] as Uint8List, verified.bytes)) {
          rejectSegment('IMMUTABLE_OBJECT_CONFLICT');
        }
        // Verify old persisted data/edges too; no silent repair or stale flag trust.
        return _read(ref)!;
      }
      _reference(ref);
      _fault?.call('before_object_insert');
      _db.execute('INSERT INTO objects VALUES(?,?,?,?)', [
        ref.hash,
        verified.kind,
        verified.bytes,
        VerifiedObject.validatorBuild
      ]);
      _fault?.call('after_object_insert');
      for (var i = 0; i < verified.children.length; i++) {
        final child = verified.children[i];
        _reference(
            child.ref); // Missing placeholder, never advertised as verified.
        _db.execute('INSERT INTO edges VALUES(?,?,?,?)',
            [ref.hash, i, child.ref.hash, child.kinds.toList().join(',')]);
      }
      _fault?.call('after_edges_insert');
      return _read(ref)!;
    });
  }

  VerifiedObject? _read(ObjectRef ref) {
    final size = _db.select(
        'SELECT length(body) AS n FROM objects WHERE hash=?', [ref.hash]);
    if (size.isNotEmpty && (size.single['n'] as int) > limits.objectBytes) {
      rejectSegment('LOCAL_OBJECT_BUDGET');
    }
    final rows = _db.select(
        'SELECT o.*,r.bytes AS size FROM objects o JOIN refs r USING(hash) WHERE hash=?',
        [ref.hash]);
    if (rows.isEmpty) return null;
    final row = rows.single;
    if (row['size'] != ref.bytes ||
        row['validator'] != VerifiedObject.validatorBuild) {
      rejectSegment('OBJECT_METADATA_INVALID');
    }
    final obj = VerifiedObject.verify(row['body'] as Uint8List, ref, cache,
        maxBytes: limits.objectBytes);
    if (obj.kind != row['kind']) rejectSegment('OBJECT_METADATA_INVALID');
    final edges = _db.select(
        'SELECT e.*,r.bytes FROM edges e JOIN refs r ON r.hash=e.child WHERE parent=? ORDER BY position',
        [ref.hash]);
    if (edges.length != obj.children.length) {
      rejectSegment('OBJECT_EDGE_INVALID');
    }
    for (var i = 0; i < edges.length; i++) {
      final child = obj.children[i], edge = edges[i];
      if (edge['position'] != i ||
          edge['child'] != child.ref.hash ||
          edge['bytes'] != child.ref.bytes ||
          edge['kinds'] != child.kinds.toList().join(',')) {
        rejectSegment('OBJECT_EDGE_INVALID');
      }
    }
    return obj;
  }

  VerifiedObject? getVerifiedObject(ObjectRef ref) {
    if (_closed) rejectSegment('STORE_CLOSED');
    try {
      return _read(ref);
    } on SqliteException {
      rejectSegment('PERSISTENCE_FAILED');
    }
  }

  bool containsVerifiedObject(ObjectRef ref) => getVerifiedObject(ref) != null;

  // Keyset paging: no payloads, no all-object materialization.
  List<ObjectRef> listStoredObjectIdentities(
      {String? afterHash, int limit = 256}) {
    if (_closed) rejectSegment('STORE_CLOSED');
    if (limit < 1 || limit > 1024) rejectSegment('LOCAL_ENUMERATION_BUDGET');
    if (afterHash != null) hashValue(afterHash);
    return _db
        .select(
            'SELECT hash,bytes FROM refs JOIN objects USING(hash) WHERE hash>? ORDER BY hash LIMIT ?',
            [afterHash ?? '', limit])
        .map((r) => ObjectRef.parse({'hash': r['hash'], 'bytes': r['bytes']}))
        .toList(growable: false);
  }

  StagingSession createStaging(
      String localId, ObservationManifest manifest, DateTime createdAt) {
    uuidValue(localId);
    cache.verifyTarget(manifest.target);
    if (!createdAt.isUtc) rejectSegment('LOCAL_TIME_INVALID');
    if (manifest.bytes.length > limits.manifestBytes) {
      rejectSegment('LOCAL_METADATA_BUDGET');
    }
    return _transaction(() {
      final existing =
          _db.select('SELECT manifest FROM staging WHERE id=?', [localId]);
      if (existing.isNotEmpty) {
        if (!sameBytes(
            existing.single['manifest'] as Uint8List, manifest.bytes)) {
          rejectSegment('STAGING_CONFLICT');
        }
        return _loadStage(localId)!;
      }
      _db.execute('INSERT INTO staging VALUES(?,?,?,?)', [
        localId,
        manifest.bytes,
        localChecksum(manifest.bytes),
        createdAt.toIso8601String()
      ]);
      for (final root in manifest.target.roots.entries) {
        _reference(root.value);
        _db.execute('INSERT INTO staging_roots VALUES(?,?,?)',
            [localId, root.key, root.value.hash]);
      }
      _fault?.call('after_staging_insert');
      return _loadStage(localId)!;
    });
  }

  void recordStagedObject(String localId, ObjectRef ref) => _transaction(() {
        if (_loadStage(localId) == null) rejectSegment('STAGING_MISSING');
        if (_read(ref) == null) rejectSegment('OBJECT_MISSING');
        _db.execute('INSERT OR IGNORE INTO staging_objects VALUES(?,?)',
            [localId, ref.hash]);
        _fault?.call('after_progress_insert');
      });

  StagingSession? _loadStage(String id) {
    final size = _db
        .select('SELECT length(manifest) AS n FROM staging WHERE id=?', [id]);
    if (size.isNotEmpty && (size.single['n'] as int) > limits.manifestBytes) {
      rejectSegment('LOCAL_METADATA_BUDGET');
    }
    final rows = _db.select('SELECT * FROM staging WHERE id=?', [id]);
    if (rows.isEmpty) return null;
    final row = rows.single;
    final raw = row['manifest'] as Uint8List;
    if (localChecksum(raw) != row['checksum']) {
      rejectSegment('STAGING_CORRUPT');
    }
    final manifest =
        ObservationManifest.fromBytes(raw, maxBytes: limits.manifestBytes);
    cache.verifyTarget(manifest.target);
    final roots = _db.select(
        'SELECT role,hash,bytes FROM staging_roots JOIN refs USING(hash) WHERE staging_id=?',
        [id]);
    if (roots.length != 4 ||
        roots.any((r) =>
            manifest.target.roots[r['role']]?.hash != r['hash'] ||
            manifest.target.roots[r['role']]?.bytes != r['bytes'])) {
      rejectSegment('STAGING_CORRUPT');
    }
    final created = DateTime.tryParse(row['created_at'] as String);
    if (created == null || !created.isUtc) rejectSegment('STAGING_CORRUPT');
    return StagingSession(
        id,
        manifest,
        created,
        _db.select(
            'SELECT count(*) AS n FROM staging_objects WHERE staging_id=?',
            [id]).single['n'] as int);
  }

  StagingSession? loadStaging(String localId) {
    uuidValue(localId);
    if (_closed) rejectSegment('STORE_CLOSED');
    try {
      return _loadStage(localId);
    } on SqliteException {
      rejectSegment('PERSISTENCE_FAILED');
    }
  }

  List<String> listStagingIdentities({String? afterId, int limit = 128}) {
    if (_closed) {
      rejectSegment('STORE_CLOSED');
    }
    if (limit < 1 || limit > 1024) {
      rejectSegment('LOCAL_ENUMERATION_BUDGET');
    }
    if (afterId != null) {
      uuidValue(afterId);
    }
    return _db
        .select('SELECT id FROM staging WHERE id>? ORDER BY id LIMIT ?',
            [afterId ?? '', limit])
        .map((row) => uuidValue(row['id']))
        .toList(growable: false);
  }

  // Explicit staging abandonment only. No object sweep, no accepted/frozen pins.
  // SQLite handles its own rollback journal; never manually delete sidecars.
  bool removeUnreferencedStagingData(String localId) => _transaction(() {
        uuidValue(localId);
        _db.execute('DELETE FROM staging WHERE id=?', [localId]);
        final removed = _db.updatedRows != 0;
        // This explicit staging cleanup may inspect metadata, never payloads.
        _db.execute(
            'DELETE FROM refs WHERE hash NOT IN (SELECT hash FROM objects) AND hash NOT IN (SELECT child FROM edges) AND hash NOT IN (SELECT hash FROM staging_roots)');
        return removed;
      });

  StoreHealth inspectStoreHealth() {
    if (_closed) rejectSegment('STORE_CLOSED');
    final issues = <String>[];
    if (!_usageValid(_db)) {
      issues.add('STORE_METADATA_CORRUPT');
    }
    var objects = 0, stagings = 0;
    // Explicit recovery/scrub O(N), never called by ordinary object put/get.
    String? after;
    while (true) {
      final page = listStoredObjectIdentities(afterHash: after);
      if (page.isEmpty) break;
      for (final ref in page) {
        try {
          getVerifiedObject(ref);
        } on SegmentedException catch (error) {
          issues.add('${ref.hash}:${error.code}');
        }
        objects++;
      }
      after = page.last.hash;
    }
    for (final row in _db.select('SELECT id FROM staging ORDER BY id')) {
      final id = row['id'] as String;
      try {
        _loadStage(id);
        for (final item in _db.select(
            'SELECT hash,bytes FROM staging_objects JOIN refs USING(hash) WHERE staging_id=?',
            [id])) {
          if (getVerifiedObject(ObjectRef.parse(
                  {'hash': item['hash'], 'bytes': item['bytes']})) ==
              null) {
            rejectSegment('OBJECT_MISSING');
          }
        }
      } on SegmentedException catch (error) {
        issues.add('$id:${error.code}');
      }
      stagings++;
    }
    return StoreHealth(objects, stagings, List.unmodifiable(issues));
  }

  void close() {
    if (!_closed) {
      _db.close();
      _closed = true;
    }
  }
}

// Recovery/scrub only: counters bound normal puts without growing-table scans.
bool _usageValid(Database db) {
  final rows = db.select('SELECT * FROM usage');
  if (rows.length != 1) {
    return false;
  }
  final actual = rows.single;
  final expected = db.select('''SELECT
    (SELECT count(*) FROM objects) AS objects,
    (SELECT coalesce(sum(length(body)),0) FROM objects) AS payload,
    (SELECT count(*) FROM staging) AS stages,
    (SELECT count(*)*192 FROM objects)+(SELECT count(*)*128 FROM refs)+
    (SELECT count(*)*256 FROM edges)+(SELECT coalesce(sum(length(manifest)+256),0) FROM staging)+
    (SELECT count(*)*128 FROM staging_roots)+(SELECT count(*)*128 FROM staging_objects) AS metadata''').single;
  return actual['id'] == 1 &&
      ['objects', 'payload', 'stages', 'metadata']
          .every((key) => actual[key] is int && actual[key] == expected[key]);
}

const _schema = '''
CREATE TABLE profile(id INTEGER PRIMARY KEY CHECK(id=1),discriminator TEXT NOT NULL,namespace TEXT NOT NULL,validator TEXT NOT NULL);
CREATE TABLE refs(hash TEXT PRIMARY KEY,bytes TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE objects(hash TEXT PRIMARY KEY REFERENCES refs(hash),kind TEXT NOT NULL,body BLOB NOT NULL,validator TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE edges(parent TEXT NOT NULL REFERENCES objects(hash),position INTEGER NOT NULL,child TEXT NOT NULL REFERENCES refs(hash),kinds TEXT NOT NULL,PRIMARY KEY(parent,position)) WITHOUT ROWID;
CREATE INDEX edge_children ON edges(child);
CREATE TABLE staging(id TEXT PRIMARY KEY,manifest BLOB NOT NULL,checksum TEXT NOT NULL,created_at TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE staging_roots(staging_id TEXT NOT NULL REFERENCES staging(id) ON DELETE CASCADE,role TEXT NOT NULL,hash TEXT NOT NULL REFERENCES refs(hash),PRIMARY KEY(staging_id,role)) WITHOUT ROWID;
CREATE TABLE staging_objects(staging_id TEXT NOT NULL REFERENCES staging(id) ON DELETE CASCADE,hash TEXT NOT NULL REFERENCES objects(hash),PRIMARY KEY(staging_id,hash)) WITHOUT ROWID;
CREATE TABLE usage(id INTEGER PRIMARY KEY CHECK(id=1),objects INTEGER NOT NULL CHECK(objects>=0),payload INTEGER NOT NULL CHECK(payload>=0),stages INTEGER NOT NULL CHECK(stages>=0),metadata INTEGER NOT NULL CHECK(metadata>=0));
INSERT INTO usage VALUES(1,0,0,0,0);
CREATE TRIGGER object_usage AFTER INSERT ON objects BEGIN UPDATE usage SET objects=objects+1,payload=payload+length(NEW.body),metadata=metadata+192; END;
CREATE TRIGGER refs_usage AFTER INSERT ON refs BEGIN UPDATE usage SET metadata=metadata+128; END;
CREATE TRIGGER refs_release AFTER DELETE ON refs BEGIN UPDATE usage SET metadata=metadata-128; END;
CREATE TRIGGER edge_usage AFTER INSERT ON edges BEGIN UPDATE usage SET metadata=metadata+256; END;
CREATE TRIGGER staging_usage AFTER INSERT ON staging BEGIN UPDATE usage SET stages=stages+1,metadata=metadata+length(NEW.manifest)+256; END;
CREATE TRIGGER staging_release AFTER DELETE ON staging BEGIN UPDATE usage SET stages=stages-1,metadata=metadata-length(OLD.manifest)-256; END;
CREATE TRIGGER root_usage AFTER INSERT ON staging_roots BEGIN UPDATE usage SET metadata=metadata+128; END;
CREATE TRIGGER root_release AFTER DELETE ON staging_roots BEGIN UPDATE usage SET metadata=metadata-128; END;
CREATE TRIGGER progress_usage AFTER INSERT ON staging_objects BEGIN UPDATE usage SET metadata=metadata+128; END;
CREATE TRIGGER progress_release AFTER DELETE ON staging_objects BEGIN UPDATE usage SET metadata=metadata-128; END;
CREATE TRIGGER immutable_body BEFORE UPDATE ON objects BEGIN SELECT RAISE(ABORT,'immutable object'); END;
''';

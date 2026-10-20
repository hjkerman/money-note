// Isolated segmented-store/1. E1/E2 profiles have no accepted pointer. E3's
// explicit publication profile adds a segmented-internal pointer, never app DI.
import 'dart:io';
import 'dart:typed_data';

import 'package:sqlite3/sqlite3.dart';

import 'c1.dart';
import 'graph.dart';
import 'object.dart';
import 'protocol.dart';
import 'verification.dart';
import 'work.dart';

part 'store_publication.dart';
part 'store_read.dart';
part 'store_frozen.dart';

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

// Local acquisition bookkeeping, never a CompleteTargetVerified receipt.
class AcquisitionProgress {
  const AcquisitionProgress(this.state, this.errorCode);
  final String state;
  final String? errorCode;
}

class SegmentedClientStore {
  SegmentedClientStore._(this._db, this.path, this.cache, this.limits,
      this._fault, this.acquisitionEnabled, this.publicationEnabled);
  static const discriminator = 'segmented-store/1';
  static const schemaVersion = 1;
  final Database _db;
  final String path;
  final CacheNamespace cache;
  final ClientStoreLimits limits;
  final StoreFault? _fault;
  final bool acquisitionEnabled;
  final bool publicationEnabled;
  bool _closed = false;
  bool _readingAccepted = false;
  bool get adaptersEnabled {
    if (_closed) rejectSegment('STORE_CLOSED');
    return _db.select('PRAGMA user_version').single.values.first == 5;
  }

  final _frozenSessions = <String, _FrozenSession>{};
  final _materializationProofs = Expando<_ReadProofBinding>();
  final SegmentedWork work = SegmentedWork();
  _AcceptedSession? _acceptedSession;
  _AcceptedSession? _installedSession;
  final _candidateBindings = Expando<_CandidateBinding>();

  // Caller chooses a private root; never invoked by ordinary application startup.
  static SegmentedClientStore open(Directory privateRoot, CacheNamespace cache,
      {ClientStoreLimits limits = const ClientStoreLimits(),
      StoreFault? fault,
      bool acquisition = false,
      bool publication = false,
      bool adapters = false}) {
    publication = publication || adapters;
    acquisition = acquisition || publication;
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
      if (version != 0 &&
          version != schemaVersion &&
          !(acquisition && version == 2) &&
          !(publication && (version == 3 || version == 4)) &&
          !(adapters && version == 5)) {
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
            db.select('PRAGMA user_version').single.values.first as int;
        if (lockedVersion != 0 &&
            lockedVersion != schemaVersion &&
            !(acquisition && lockedVersion == 2) &&
            !(publication && (lockedVersion == 3 || lockedVersion == 4)) &&
            !(adapters && lockedVersion == 5)) {
          rejectSegment('UNSUPPORTED_STORAGE_SCHEMA');
        }
        if (lockedVersion == 0) {
          db.execute(_schema);
          db.execute('PRAGMA user_version=1');
          db.execute('INSERT INTO profile VALUES(1,?,?,?)',
              [discriminator, cache.key, VerifiedObject.validatorBuild]);
        }
        // Opt-in upgrade only, under the same write lock. Validate the complete
        // old profile before adding anything: never repair a damaged v1 store.
        if (acquisition && lockedVersion < 2) {
          _requireSchema(db);
          if (!_usageValid(db)) rejectSegment('STORE_METADATA_CORRUPT');
          db.execute(_acquisitionSchema);
          db.execute('PRAGMA user_version=2');
        }
        if (publication && lockedVersion < 3) {
          _requireSchema(db, acquisition: true);
          if (!_usageValid(db, acquisition: true)) {
            rejectSegment('STORE_METADATA_CORRUPT');
          }
          db.execute(_publicationSchema);
          db.execute('UPDATE accepted SET checksum=? WHERE id=1',
              [_acceptedChecksum(cache.key, null, null, 0)]);
          db.execute('PRAGMA user_version=3');
        }
        if (publication && lockedVersion < 4) {
          // Additive opt-in extension: preserve every v3 pin, receipt and
          // protective trigger. Never repair an invalid old schema.
          _requireSchema(db,
              acquisition: true, publication: true, publicationVersion: 3);
          if (!_usageValid(db, acquisition: true, publication: true)) {
            rejectSegment('STORE_METADATA_CORRUPT');
          }
          db.execute(_incrementalPublicationSchema);
          db.execute('PRAGMA user_version=4');
        }
        if (adapters && lockedVersion < 5) {
          _requireSchema(db,
              acquisition: true, publication: true, publicationVersion: 4);
          if (!_usageValid(db, acquisition: true, publication: true)) {
            rejectSegment('STORE_METADATA_CORRUPT');
          }
          db.execute(_frozenSchema);
          db.execute('PRAGMA user_version=5');
        }
        _requireSchema(db, acquisition: acquisition, publication: publication);
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
        if (actualTables.length !=
                (publication
                    ? (adapters ? 15 : 13)
                    : acquisition
                        ? 9
                        : 8) ||
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
        if (!_usageValid(db,
            acquisition: acquisition, publication: publication)) {
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
      return SegmentedClientStore._(
          db, path, cache, limits, fault, acquisition, publication);
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

  T _transaction<T>(T Function() body,
      {void Function()? finalFence, void Function()? onCommitted}) {
    _requireNoAcceptedReader();
    work.add('transactions');
    if (_closed) rejectSegment('STORE_CLOSED');
    var begun = false;
    try {
      _db.execute('BEGIN IMMEDIATE');
      begun = true;
      // DDL is a SQLite write too: this same write transaction excludes schema
      // changes by other connections until COMMIT/ROLLBACK. Never cache a flag.
      _requireSchema(_db,
          acquisition: acquisitionEnabled, publication: publicationEnabled);
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
      if (finalFence is Future Function() && finalFence is! Never Function()) {
        rejectSegment('ASYNC_PUBLICATION_FENCE');
      }
      finalFence?.call();
      _db.execute('COMMIT');
      begun = false;
      onCommitted?.call();
      _fault?.call('after_commit');
      return result;
    } on SqliteException catch (error) {
      _acceptedSession = null;
      _frozenSessions.clear();
      _installedSession = null;
      throw SegmentedException(
          error.resultCode == 5 || error.resultCode == 6
              ? 'STORE_BUSY'
              : 'PERSISTENCE_FAILED',
          storageCode: error.extendedResultCode);
    } catch (_) {
      _acceptedSession = null;
      _frozenSessions.clear();
      _installedSession = null;
      rethrow;
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
    return _transaction(() => _putVerified(verified));
  }

  // Same immutable insertion/readback as the original single-object API. A
  // bounded acquisition batch owns the transaction; no nested BEGIN/COMMIT.
  VerifiedObject _putVerified(VerifiedObject verified) {
    final ref = verified.ref;
    final old = _db.select('SELECT body FROM objects WHERE hash=?', [ref.hash]);
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
  }

  // Explicit E2 verification envelope only. Objects AND their progress links
  // commit together. At most 64 entries / 1 MiB object bytes (cached included);
  // an oversized object
  // may be a singleton only, still subject to the existing object/payload caps.
  // Null bytes denote a cached object, reverified under the same SQL lock.
  void putVerifiedStagedBatch(
      String localId, List<({ObjectRef ref, List<int>? bytes})> entries) {
    if (!acquisitionEnabled) rejectSegment('ACQUISITION_METADATA_REQUIRED');
    if (entries.isEmpty || entries.length > 64) {
      rejectSegment('LOCAL_BATCH_BUDGET');
    }
    final chargedBytes = entries.fold<int>(
        0,
        (n, e) =>
            n +
            ((e.bytes?.length ?? 0) > e.ref.byteLength
                ? e.bytes!.length
                : e.ref.byteLength));
    if (chargedBytes > 1048576 && entries.length != 1) {
      rejectSegment('LOCAL_BATCH_BUDGET');
    }
    final refs = List<ObjectRef>.unmodifiable(entries.map((e) => e.ref));
    // Own/verify all new bytes before BEGIN. No partly verified buffer can be
    // persisted; the original verifier and all transaction quota/schema checks
    // remain mandatory. Memory is bounded by the above envelope.
    final verified = [
      for (final e in entries)
        e.bytes == null
            ? null
            : VerifiedObject.verify(e.bytes!, e.ref, cache,
                maxBytes: limits.objectBytes)
    ];
    _transaction(() {
      if (_loadStage(localId, includeCount: false) == null) {
        rejectSegment('STAGING_MISSING');
      }
      for (var i = 0; i < refs.length; i++) {
        final object = verified[i];
        if (object != null) {
          _putVerified(object);
        } else if (_read(refs[i]) == null) {
          rejectSegment('OBJECT_MISSING');
        }
        _db.execute('INSERT OR IGNORE INTO staging_objects VALUES(?,?)',
            [localId, refs[i].hash]);
        _fault?.call('after_progress_insert');
      }
    });
  }

  bool isStagedObject(String localId, ObjectRef ref) {
    if (_closed) rejectSegment('STORE_CLOSED');
    return _db.select(
        'SELECT 1 FROM staging_objects WHERE staging_id=? AND hash=?',
        [localId, ref.hash]).isNotEmpty;
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
    work.add('object_reads');
    work.add('verified_bytes', obj.bytes.length);
    if (obj.kind.startsWith('snapshot-')) work.add('raw_object_reads');
    if (obj.kind.startsWith('index-')) work.add('index_object_reads');
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
      final result = _read(ref);
      if (result == null &&
          ((_acceptedSession?.proof?.graph.provenance?.contains(ref) ??
                  false) ||
              (_installedSession?.proof?.graph.provenance?.contains(ref) ??
                  false) ||
              _frozenSessions.values.any(
                  (s) => s.proof.graph.provenance?.contains(ref) ?? false))) {
        _acceptedSession = null;
        _installedSession = null;
        _frozenSessions.clear();
      }
      return result;
    } on SqliteException {
      _acceptedSession = null;
      _frozenSessions.clear();
      _installedSession = null;
      rejectSegment('PERSISTENCE_FAILED');
    } catch (_) {
      _acceptedSession = null;
      _installedSession = null;
      _frozenSessions.clear();
      rethrow;
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
        if (_loadStage(localId, includeCount: false) == null) {
          rejectSegment('STAGING_MISSING');
        }
        if (_read(ref) == null) rejectSegment('OBJECT_MISSING');
        _db.execute('INSERT OR IGNORE INTO staging_objects VALUES(?,?)',
            [localId, ref.hash]);
        _fault?.call('after_progress_insert');
      });

  StagingSession? _loadStage(String id, {bool includeCount = true}) {
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
        includeCount
            ? _db.select(
                'SELECT count(*) AS n FROM staging_objects WHERE staging_id=?',
                [id]).single['n'] as int
            : 0);
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

  AcquisitionProgress? acquisitionProgress(String localId) {
    if (!acquisitionEnabled) rejectSegment('ACQUISITION_METADATA_REQUIRED');
    if (loadStaging(localId) == null) rejectSegment('STAGING_MISSING');
    final rows = _db.select(
        'SELECT state,error_code FROM acquisition WHERE staging_id=?',
        [localId]);
    if (rows.isEmpty) return null;
    final state = rows.single['state'], code = rows.single['error_code'];
    _validateAcquisition(state, code);
    return AcquisitionProgress(state as String, code as String?);
  }

  void recordAcquisition(String localId, String state, {String? errorCode}) {
    if (!acquisitionEnabled) rejectSegment('ACQUISITION_METADATA_REQUIRED');
    _validateAcquisition(state, errorCode);
    _transaction(() {
      if (_loadStage(localId, includeCount: false) == null) {
        rejectSegment('STAGING_MISSING');
      }
      _db.execute(
          'INSERT INTO acquisition VALUES(?,?,?) ON CONFLICT(staging_id) DO UPDATE SET state=excluded.state,error_code=excluded.error_code',
          [localId, state, errorCode]);
      _fault?.call('after_acquisition_insert');
    });
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
    try {
      _requireSchema(_db,
          acquisition: acquisitionEnabled, publication: publicationEnabled);
    } on SegmentedException catch (error) {
      issues.add(error.code);
    }
    if (!_usageValid(_db,
        acquisition: acquisitionEnabled, publication: publicationEnabled)) {
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
        if (acquisitionEnabled) acquisitionProgress(id);
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
    if (issues.isNotEmpty) {
      _acceptedSession = null;
      _installedSession = null;
      _frozenSessions.clear();
    }
    return StoreHealth(objects, stagings, List.unmodifiable(issues));
  }

  void close() {
    _requireNoAcceptedReader();
    if (!_closed) {
      _acceptedSession = null;
      _installedSession = null;
      _frozenSessions.clear();
      _db.close();
      _closed = true;
    }
  }

  void _requireNoAcceptedReader() {
    if (_readingAccepted) rejectSegment('ACCEPTED_READ_IN_PROGRESS');
  }
}

// Closed, versioned schema: compare actual definitions, not just trigger names.
// The trusted initialization DDL is the sole schema definition source. SQLite
// stores these CREATE statements without their final semicolon. Equivalent but
// differently rewritten DDL is conservatively unsupported, never auto-repaired.
final _schemaDefinitions = <String, String>{
  for (final match
      in RegExp(r'^CREATE (?:TABLE|INDEX|TRIGGER) (\w+).+$', multiLine: true)
          .allMatches(_schema))
    match.group(1)!: match.group(0)!.substring(0, match.group(0)!.length - 1)
};
final _acquisitionDefinitions = <String, String>{
  ..._schemaDefinitions,
  for (final match
      in RegExp(r'^CREATE (?:TABLE|INDEX|TRIGGER) (\w+).+$', multiLine: true)
          .allMatches(_acquisitionSchema))
    match.group(1)!: match.group(0)!.substring(0, match.group(0)!.length - 1)
};

void _requireSchema(Database db,
    {bool acquisition = false,
    bool publication = false,
    int? publicationVersion}) {
  publicationVersion ??=
      db.select('PRAGMA user_version').single.values.first == 5 ? 5 : 4;
  if (db.select('PRAGMA user_version').single.values.first !=
      (publication
          ? publicationVersion
          : acquisition
              ? 2
              : SegmentedClientStore.schemaVersion)) {
    rejectSegment('UNSUPPORTED_STORAGE_SCHEMA');
  }
  final definitions = publication
      ? (publicationVersion == 3
          ? _publicationDefinitions
          : publicationVersion == 5
              ? _frozenDefinitions
              : _incrementalPublicationDefinitions)
      : acquisition
          ? _acquisitionDefinitions
          : _schemaDefinitions;
  final rows = db.select(
      'SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name LIMIT ?',
      [definitions.length + 1]);
  if (rows.length != definitions.length ||
      rows.any((row) => definitions[row['name']] != row['sql'])) {
    rejectSegment('STORE_SCHEMA_CORRUPT');
  }
}

// Recovery/scrub only: counters bound normal puts without growing-table scans.
bool _usageValid(Database db,
    {bool acquisition = false, bool publication = false}) {
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
  final acquisitionCharge = acquisition
      ? db.select('SELECT count(*)*256 AS n FROM acquisition').single['n']
          as int
      : 0;
  final publicationCharge = publication
      ? db.select('''SELECT
    (SELECT coalesce(sum(length(manifest)+length(receipt)+512),0) FROM generations)+
    (SELECT count(*)*128 FROM generation_objects)+256 AS n''').single['n']
          as int
      : 0;
  final rootCharge = publication &&
          (db.select('PRAGMA user_version').single.values.first as int) >= 4
      ? db.select('SELECT count(*)*128 AS n FROM generation_roots').single['n']
          as int
      : 0;
  final frozenCharge = publication &&
          db.select('PRAGMA user_version').single.values.first == 5
      ? db
          .select(
              'SELECT coalesce(sum(length(binding)+512),0)+(SELECT count(*)*256 FROM installed) AS n FROM frozen')
          .single['n'] as int
      : 0;
  return actual['id'] == 1 &&
      ['objects', 'payload', 'stages', 'metadata'].every((key) =>
          actual[key] is int &&
          actual[key] ==
              (expected[key] as int) +
                  (key == 'metadata'
                      ? acquisitionCharge +
                          publicationCharge +
                          rootCharge +
                          frozenCharge
                      : 0));
}

void _validateAcquisition(Object? state, Object? code) {
  if (!['acquiring', 'interrupted', 'graph_verified'].contains(state) ||
      (state == 'interrupted') != (code != null) ||
      (code != null &&
          (code is! String ||
              !RegExp(r'^[A-Z][A-Z0-9_]{0,63}$').hasMatch(code)))) {
    rejectSegment('ACQUISITION_METADATA_INVALID');
  }
}

const _acquisitionSchema = '''
CREATE TABLE acquisition(staging_id TEXT PRIMARY KEY REFERENCES staging(id) ON DELETE CASCADE,state TEXT NOT NULL CHECK(state IN ('acquiring','interrupted','graph_verified')),error_code TEXT,CHECK((state='interrupted')=(error_code IS NOT NULL))) WITHOUT ROWID;
CREATE TRIGGER acquisition_usage AFTER INSERT ON acquisition BEGIN UPDATE usage SET metadata=metadata+256; END;
CREATE TRIGGER acquisition_release AFTER DELETE ON acquisition BEGIN UPDATE usage SET metadata=metadata-256; END;
''';

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

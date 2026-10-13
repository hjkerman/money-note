import 'package:flutter_test/flutter_test.dart';
import 'package:sqlite3/sqlite3.dart';

// Independent SQLite retention oracle. Each case creates its OWN in-memory DB;
// no application file, object bytes, financial row or existing pin is deleted.
void main() {
  for (final commit in [false, true]) {
    test(
        'root retention model: G2 -> G3 ${commit ? "COMMIT" : "ROLLBACK"} preserves current AND previous',
        () {
      final db = sqlite3.openInMemory();
      try {
        db.execute('''
PRAGMA foreign_keys=ON;
CREATE TABLE objects(hash TEXT PRIMARY KEY);
CREATE TABLE edges(parent TEXT REFERENCES objects(hash),child TEXT REFERENCES objects(hash));
CREATE TABLE generations(id TEXT PRIMARY KEY);
CREATE TABLE generation_roots(generation_id TEXT REFERENCES generations(id) ON DELETE CASCADE,hash TEXT REFERENCES objects(hash),PRIMARY KEY(generation_id,hash));
CREATE TABLE accepted(current_id TEXT REFERENCES generations(id),previous_id TEXT REFERENCES generations(id));
CREATE TRIGGER retain_generation BEFORE DELETE ON generations WHEN EXISTS(SELECT 1 FROM accepted WHERE current_id=OLD.id OR previous_id=OLD.id) BEGIN SELECT RAISE(ABORT,'retained generation'); END;
CREATE TRIGGER retain_object BEFORE DELETE ON objects WHEN EXISTS(WITH RECURSIVE retained(hash) AS(SELECT hash FROM generation_roots UNION SELECT e.child FROM edges e JOIN retained r ON e.parent=r.hash) SELECT 1 FROM retained WHERE hash=OLD.hash) BEGIN SELECT RAISE(ABORT,'retained object'); END;
CREATE TRIGGER retain_edge BEFORE DELETE ON edges WHEN EXISTS(WITH RECURSIVE retained(hash) AS(SELECT hash FROM generation_roots UNION SELECT e.child FROM edges e JOIN retained r ON e.parent=r.hash) SELECT 1 FROM retained WHERE hash=OLD.parent) BEGIN SELECT RAISE(ABORT,'retained edge'); END;
INSERT INTO objects VALUES('r1'),('r2'),('r3'),('shared'),('old-only'),('new-only');
INSERT INTO edges VALUES('r1','shared'),('r1','old-only'),('r2','shared'),('r3','shared'),('r3','new-only');
INSERT INTO generations VALUES('G1'),('G2'),('G3');
INSERT INTO generation_roots VALUES('G1','r1'),('G2','r2'),('G3','r3');
INSERT INTO accepted VALUES('G2','G1');
''');
        final beforeObjects = db
            .select('SELECT hash FROM objects ORDER BY hash')
            .map((r) => r['hash'])
            .toList();
        db.execute('BEGIN IMMEDIATE');
        final expected = db.select('SELECT * FROM accepted').single;
        expect(expected['current_id'], 'G2');
        expect(expected['previous_id'], 'G1');
        db.execute("UPDATE accepted SET current_id='G3',previous_id='G2'");
        // Exact obsolete ID from the just-fenced pointer, never a broad target.
        db.execute(
            'DELETE FROM generations WHERE id=?', [expected['previous_id']]);
        expect(() => db.execute("DELETE FROM generations WHERE id='G2'"),
            throwsA(isA<SqliteException>()));
        db.execute(commit ? 'COMMIT' : 'ROLLBACK');
        final pointer = db.select('SELECT * FROM accepted').single;
        expect(pointer['current_id'], commit ? 'G3' : 'G2');
        expect(pointer['previous_id'], commit ? 'G2' : 'G1');
        final generations =
            db.select('SELECT id FROM generations').map((r) => r['id']).toSet();
        expect(generations,
            containsAll([pointer['current_id'], pointer['previous_id']]));
        const closure =
            'WITH RECURSIVE retained(hash) AS(SELECT hash FROM generation_roots UNION SELECT e.child FROM edges e JOIN retained r ON e.parent=r.hash) SELECT hash FROM retained';
        final retained =
            db.select(closure).map((r) => r['hash'] as String).toList();
        expect(retained, containsAll(['r2', 'r3', 'shared', 'new-only']));
        if (!commit) expect(retained, containsAll(['r1', 'old-only']));
        for (final hash in retained) {
          expect(() => db.execute('DELETE FROM objects WHERE hash=?', [hash]),
              throwsA(isA<SqliteException>()));
        }
        expect(() => db.execute("DELETE FROM edges WHERE parent='r2'"),
            throwsA(isA<SqliteException>()));
        expect(
            db
                .select('SELECT hash FROM objects ORDER BY hash')
                .map((r) => r['hash'])
                .toList(),
            beforeObjects);
        expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      } finally {
        db.close();
      }
    });
  }
}

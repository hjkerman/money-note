from pathlib import Path
import json,hashlib,difflib
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=Path('/tmp/money-note-t66f-b09-20261026');C=W/'candidate';sha=lambda b:hashlib.sha256(b).hexdigest()
p='backend/app/db_migrations.py';a=(W/'baseline'/p).read_text();b=(C/p).read_text();start=a.index('def _validate_revision_triggers(');end=a.index('\n\ndef ',start)
bstart=b.index('@lru_cache(maxsize=1)\ndef _expected_revision_contract(');bend=b.index('\n\ndef ',b.index('def _validate_revision_triggers('))
old=a[start:end];new=b[bstart:bend];assert b.replace(new,old,1)==a
review=json.loads((E/'source-lock-review.json').read_text());review['B08_unchanged_optimization']={'path':p,'before_sha256':sha(a.encode()),'after_sha256':sha(b.encode()),'changes':[{'before':old,'after':new}],'authorization':'B09 §3D: 검증된 B08 engine identity에만 의존하는 source-SHA 테스트 전이; 원 historical SHA 그대로'}
(E/'source-lock-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n');(C/'docs/benchmarks/t66f-b09/source-lock-review.json').write_bytes((E/'source-lock-review.json').read_bytes())
p='mobile/test/segmented_adapter_isolation_test.dart';t=(C/p).read_text();before=t
needle="      final actual = path == 'mobile/lib/src/segmented/c1.dart'"
replacement="""      if (path == 'backend/app/db_migrations.py') {
        final review = jsonDecode(read('docs/benchmarks/t66f-b09/source-lock-review.json')) as Map;
        final b08 = review['B08_unchanged_optimization'] as Map;
        expect(hash(path), b08['after_sha256']);
        var restored = read(path);
        for (final change in b08['changes'] as List) {
          final after = change['after'] as String;
          expect(after.allMatches(restored).length, 1);
          restored = restored.replaceFirst(after, change['before'] as String);
        }
        expect(sha256.convert(utf8.encode(restored)).toString(), protected[path]['sha256']);
        return;
      }
"""+needle
assert t.count(needle)==1;t=t.replace(needle,replacement,1);(C/p).write_text(t)
(E/'guard-dependent-update.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),t.splitlines(True),fromfile=p,tofile=p)))

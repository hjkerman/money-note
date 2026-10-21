"""합성 benchmark evidence v1. sync wire/protocol이 아니다."""

BYTE_METRICS = frozenset(
    {
        "hash_input_bytes",
        "submitted_bytes",
        "completed_bytes",
        "failed_submitted_bytes",
        "output_bytes",
        "bind_blob_bytes",
        "bind_text_bytes",
        "blob_bytes",
        "text_bytes",
        "hashInputBytes",
        "submittedBytes",
        "completedBytes",
        "failedSubmittedBytes",
        "outputBytes",
        "bindBlobBytes",
        "bindTextBytes",
        "blobBytes",
        "textBytes",
        "object_bytes_read",
        "decoded_bytes",
        "response_bytes",
        "readBytes",
        "decodeSubmittedBytes",
        "decodeCompletedBytes",
        "decodeFailedSubmittedBytes",
    }
)
OUTCOMES = frozenset(
    {
        "attempted",
        "effective",
        "committed",
        "rolled_back",
        "rolled_back_on_close",
        "statement_rolled_back",
        "rolledBack",
        "rolledBackOnClose",
        "statementRolledBack",
    }
)


def snapshot(run_id, fixture, workload, layer, counters, environment, coverage):
    rows = []
    for key, raw in sorted(counters.items()):
        value = int(raw)
        if value < 0:
            raise ValueError("음수 누계는 증거로 승인하지 않는다")
        parts = key.split("/")
        status = next((p for p in parts if p in OUTCOMES), "performed")
        metric = next((p for p in reversed(parts) if p not in OUTCOMES), parts[-1])
        operation = "/".join(p for p in parts[1:] if p not in OUTCOMES and p != metric)
        rows.append(
            {
                "stage": parts[0],
                "operation": operation,
                "counter": metric,
                "value": str(value),
                "unit": "bytes" if metric in BYTE_METRICS else "count",
                "status": status,
                "source_key": key,
            }
        )
    return {
        "schema_version": 1,
        "instrumentation_version": "t66f-b03/1",
        "run_id": run_id,
        "fixture": fixture,
        "workload": workload,
        "layer": layer,
        "environment": environment,
        "coverage": coverage,
        "counters": rows,
        "overlap": "hash/validation/write는 별도 비용이며 합쳐 unique bytes로 쓰지 않는다",
    }

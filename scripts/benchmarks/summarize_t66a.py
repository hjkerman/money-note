"""Aggregate T6.6A observations; no runtime imports, no invented wire bytes."""

import argparse
import json
from pathlib import Path

from payload_bytes import JsonBytes, stats
from t66a import write_json


def summarize(root):
    measurements = json.loads((root / "measurements.json").read_text())
    client_rows = json.loads((root / "client-raw.json").read_text())
    http_client = json.loads((root / "client-http-raw.json").read_text())
    http_wire = [json.loads(line) for line in (root / "http.ndjson").read_text().splitlines()]
    client, wire, bandwidth = {}, {}, []
    for dataset, result in measurements.items():
        records = [r for r in client_rows if r["dataset"] == dataset]
        assert len(records) == 20
        assert all(r["sha256"] == result["sha256"] for r in records)
        assert sum(r["raw_bytes"] for r in result["attribution"]["partition"]) == result["raw_bytes"]
        summary = {key: stats([r[key] for r in records]) for key in records[0] if key.endswith("_ms")}
        summary["stages"] = {key: stats([r["stages"][key] for r in records]) for key in records[0]["stages"]}
        summary["baseline_bytes"] = records[0]["baseline_bytes"]
        assert all(r["baseline_bytes"] == summary["baseline_bytes"] for r in records)
        summary["parser_and_publication_ms"] = stats([r["parser_typed_ms"] + r["baseline_construction_ms"] +
                                                      r["baseline_publish_ms"] for r in records])
        client[dataset] = summary
        for codec in ("gzip", "brotli"):
            setting = 6 if codec == "gzip" else 4
            selected = next((r for r in result["compression"] if r["codec"] == codec and r["setting"] == setting), None)
            if selected is None:
                continue
            for mbps in (1, 5, 10, 50, 100):
                raw_ms = result["raw_bytes"] * 8 / (mbps * 1000)
                encoded_ms = selected["bytes"] * 8 / (mbps * 1000)
                cpu_ms = selected["encode"]["wall_ms"]["median"] + selected["decode"]["wall_ms"]["median"]
                bandwidth.append({"dataset": dataset, "codec": codec, "setting": setting,
                                  "mbps": mbps, "raw_transfer_ms": raw_ms,
                                  "encoded_transfer_ms": encoded_ms,
                                  "transfer_saving_ms": raw_ms-encoded_ms,
                                  "host_encode_decode_wall_ms": cpu_ms,
                                  "modeled_net_saving_ms": raw_ms-encoded_ms-cpu_ms,
                                  "break_even_mbps": (result["raw_bytes"]-selected["bytes"])*8/(cpu_ms*1000)})
    for path in sorted({r["path"] for r in http_wire}):
        records = [r for r in http_wire if r["path"] == path]
        mode, dataset = path.split("/")[1:3]
        clients = [r for r in http_client if r["dataset"] == dataset and r["mode"] == mode]
        example = records[0]
        wire[path] = {"observations_including_warmups": len(records),
                      "request_header_bytes": sorted({r["request_header_bytes"] for r in records}),
                      "response_header_bytes": sorted({r["response_header_bytes"] for r in records}),
                      "response_entity_bytes": sorted({r["response_entity_bytes"] for r in records}),
                      "accept_encoding": example["accept_encoding"], "content_encoding": example["content_encoding"],
                      "http_version": example["http_version"], "tls": False,
                      "transfer_encoding": example["transfer_encoding"],
                      "connections": len({r["connection"] for r in records}),
                      "handler_ms": stats([r["handler_ms"] for r in records]),
                      "compression_ms": stats([r["compression_ms"] for r in records])}
        if clients:
            wire[path]["body_available_ms"] = stats([r["http_body_available_ms"] for r in clients])
            assert len(clients) == 20
            assert all(r["decoded_sha256"] == measurements[dataset]["sha256"] for r in clients)
        if mode in ("identity", "gzip"):
            expected = measurements[dataset]["raw_bytes"] if mode == "identity" else next(
                r["bytes"] for r in measurements[dataset]["compression"] if r["codec"] == "gzip" and r["setting"] == 6)
            assert all(r["response_entity_bytes"] == expected for r in records)
    dart_decode = {r["dataset"]: stats(r["samples_ms"]) for r in http_client if r["mode"] == "dart_gzip_decode"}
    write_json(root / "client-summary.json", client)
    write_json(root / "http-summary.json", wire)
    write_json(root / "bandwidth-model.json", bandwidth)
    write_json(root / "dart-gzip-summary.json", dart_decode)
    # Descriptive least-squares model: fixed active/current composition only.
    names = ("376", "1000", "5000", "10000")
    xs = [measurements[n]["ledger_rows"] for n in names]
    growth = {}
    for category, ys in {
        "body": [measurements[n]["raw_bytes"] for n in names],
        "snapshot": [measurements[n]["attribution"]["snapshot_bytes"] for n in names],
        "typed": [measurements[n]["attribution"]["state_bytes"] for n in names],
    }.items():
        xm, ym = sum(xs)/len(xs), sum(ys)/len(ys)
        slope = sum((x-xm)*(y-ym) for x, y in zip(xs, ys))/sum((x-xm)**2 for x in xs)
        intercept = ym-slope*xm
        residuals = [y-intercept-slope*x for x, y in zip(xs, ys)]
        growth[category] = {"fixed_bytes": intercept, "bytes_per_extra_ledger_row": slope,
                            "residual_bytes": residuals, "datasets": list(names)}
    write_json(root / "growth.json", growth)
    before = (root / "body-10000.json").read_bytes()
    after = (root / "delta-after-10000.json").read_bytes()
    a, b = json.loads(before), json.loads(after)
    tree = JsonBytes(after)
    old_ids = {r["id"] for r in a["snapshot"]["data"]["ledger_entries"]}
    new_row_bytes = sum(span.size for row, span in zip(b["snapshot"]["data"]["ledger_entries"],
                         tree.get("snapshot", "data", "ledger_entries").children) if row["id"] not in old_ids)
    new_entry_bytes = sum(span.size for row, span in zip(b["state"]["entries"], tree.get("state", "entries").children)
                          if row["id"] not in old_ids)
    changed = [key for key in a["state"] if a["state"][key] != b["state"][key]]
    metadata_bytes = tree.get("authority").size + tree.get("snapshot", "manifest").size + tree.get("snapshot", "snapshot_id").size
    after_by_id = {row["id"]: row for row in b["snapshot"]["data"]["ledger_entries"]}
    # Hypothetical byte budget only, NOT a valid new protocol/restoreable delta.
    delta = json.loads((root / "delta.json").read_text())
    delta.update(new_raw_row_bytes=new_row_bytes, new_typed_entry_bytes=new_entry_bytes,
                 changed_projection_value_bytes=sum(tree.get("state", k).size for k in changed),
                 hypothetical_granular_value_budget_bytes=new_row_bytes+new_entry_bytes+metadata_bytes+
                 sum(tree.get("state", k).size for k in changed if k != "entries"),
                 metadata_value_budget_bytes=metadata_bytes,
                 unchanged_old_ledger_rows=sum(row == after_by_id.get(row["id"])
                                               for row in a["snapshot"]["data"]["ledger_entries"]))
    write_json(root / "delta.json", delta)
    print("exact accounting / codec bytes / mobile hashes / baseline sizes: PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.output)

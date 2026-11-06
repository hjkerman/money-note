def _lookup(self, conn, retired, observation_id, credential, guard):
        now = self._guard(conn, credential, guard)
        row = conn.execute("SELECT * FROM sync_observations WHERE id=?", (observation_id,)).fetchone()
        if row is None:
            reject("OBSERVATION_INCOMPLETE", "new_observation")
        if row["credential_hash"] != credential.token_hash or row["principal_id"] != credential.user_id:
            reject("PRINCIPAL_OR_SESSION_CHANGED", "reauthenticate")
        namespace = conn.execute("SELECT namespace FROM sync_current WHERE id=1").fetchone()
        if namespace is None or namespace[0] != row["namespace"]:
            reject("EPOCH_CHANGED", "full_resync")
        self._check_lease(conn, retired, row, credential, now)
        response, target = decode_c1(row["response"]), decode_c1(row["target"])
        if type(target) is not dict or "sync_root" not in target:
            reject("REQUIRED_METADATA_INVALID")
        derived_root = sync_root({k: v for k, v in target.items() if k != "sync_root"})
        if (type(response) is not dict or set(response) != {"protocol", "request_id", "status", "observation_id", "validated_at", "expires_at", "base_sync_root", "change_kind", "target", "inline_objects"} or
                response["protocol"] != 1 or response["observation_id"] != row["id"] or response["request_id"] != row["request_id"] or
                response["status"] != "available" or response["validated_at"] != row["validated_at"] or response["expires_at"] != row["expires_at"] or
                target["principal_id"] != row["principal_id"] or response["target"] != target or
                target["sync_root"] != derived_root or
                target["versions"] != versions() or target["ns"] != decode_c1(row["namespace"]) or
                target["context"]["financial_engine"] != hashlib.sha256(engine_artifact()).hexdigest()):
            reject("REQUIRED_METADATA_INVALID")
        cert = conn.execute("SELECT * FROM sync_commits WHERE tx_id=?", (row["tx_id"],)).fetchone()
        if cert is None or cert["status"] != "complete" or any(cert[k] != expected for k, expected in (
                ("raw_hash", target["raw_ref"]["hash"]), ("index_hash", target["index_ref"]["hash"]),
                ("target_revision", int(target["revision"])), ("target_epoch", target["ns"]["epoch"]), ("input_hash", row["input_hash"]))):
            reject("REQUIRED_METADATA_INVALID")
        pins = {r["role"]: r["hash"] for r in conn.execute("SELECT * FROM sync_observation_pins WHERE observation_id=? AND active=1", (observation_id,))}
        expected = {k: target[k+"_ref"]["hash"] for k in ("raw", "index", "hot", "control")}
        expected["input"] = row["input_hash"]
        if pins != expected:
            reject("OBSERVATION_INCOMPLETE", "new_observation")
        for kind in ("hot", "control"):
            obj = self._view_object(conn, target[kind+"_ref"], kind, target["ns"])
            if kind == "hot" and (obj.body().get("context") != target["context"] or obj.body().get("projection_schema") != target["versions"]["projection_schema"]):
                reject("REQUIRED_METADATA_INVALID")
        from isolated_sync.canonical import Context, Namespace
        from isolated_sync.store import Store
        store = Store(conn, Context(Namespace(**target["ns"]), target["versions"]["raw_schema"]))
        store.get(target["raw_ref"], {"raw-root"})
        store.index(target["index_ref"])
        input_index(conn, store, row["tx_id"])
        terminal = self._guard(conn, credential, guard)
        self._check_lease(conn, retired, row, credential, terminal)
        return response

/// Server application-response rejection contracts, not a global HTTP list.
/// A transport/parse error and every 5xx remain ambiguous. A retry of an older
/// ambiguous request must never retire its marker based on a later rejection.
enum MutationContract {
  /// Validated creates/patches and month close: validation precedes commit,
  /// including required status/model/body preparation on the server.
  validatedWrite,

  /// Manual/notification panel creation also supports pre-handler 400 input
  /// rejection from the request parser (and legacy clients' rejection contract).
  panelCreate,
  snapshotRestore,

  /// These DELETE routers roll back on conflict and missing-target rejection.
  entryDelete,
  cashFlowDelete,

  /// These routes return 404 without mutation; 409 is NOT their contract.
  plannedDelete,
  panelDelete,
  discountDelete;

  bool rejectsWithoutMutation(int? status) {
    // The shared auth dependency rejects before invoking any command.
    if (status == 401) return true;
    return switch (this) {
      validatedWrite => status == 422,
      panelCreate => status == 400 || status == 422,
      snapshotRestore => status == 400 || status == 422,
      entryDelete || cashFlowDelete => status == 404 || status == 409,
      plannedDelete || panelDelete || discountDelete => status == 404,
    };
  }
}

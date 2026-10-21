// Opt-in synthetic diagnostics. Never integrity, publication or installation proof.
import 'dart:async';

enum LogicalCostStage {
  setup,
  e1,
  e2,
  e3Verify,
  e3Prepare,
  e3Commit,
  e3Readback,
  e4Read,
  recovery,
  e4Legacy,
  calibration
}

enum LogicalCostOperation {
  objectHash,
  checksum,
  legacyHash,
  lineageHash,
  c1,
  encoding
}

enum LogicalCostMetric {
  calls,
  hashInputBytes,
  submittedBytes,
  completedBytes,
  failedCalls,
  failedSubmittedBytes,
  outputBytes
}

// Fixed categories, BigInt aggregates, no callbacks or retained input bytes.
final class LogicalCost {
  static final Object _key = Object();
  static _CostScope? get _scope => Zone.current[_key] as _CostScope?;
  static LogicalCostStage? get activeStage => _scope?.stage;
  static LogicalCost? get activeCollector => _scope?.owner;
  final Map<String, BigInt> _values = {};
  bool _closed = false;
  bool get isClosed => _closed;

  T run<T>(LogicalCostStage stage, T Function() body) =>
      runZoned(body, zoneValues: {_key: _CostScope(this, stage)});

  // Trusted operation scopes only. No observer callbacks and no extra await.
  static T at<T>(LogicalCostStage stage, T Function() body) {
    final scope = _scope;
    return scope == null || scope.owner._closed
        ? body()
        : scope.owner.run(stage, body);
  }

  void close() => _closed = true;

  Map<String, String> snapshot() => {
        for (final key in (_values.keys.toList()..sort()))
          key: _values[key].toString()
      };

  static void observe(
      LogicalCostOperation operation, LogicalCostMetric metric, int value) {
    final scope = _scope;
    if (scope == null || scope.owner._closed) return;
    final key = '${scope.stage.name}/${operation.name}/${metric.name}';
    scope.owner._values[key] =
        (scope.owner._values[key] ?? BigInt.zero) + BigInt.from(value);
  }
}

final class _CostScope {
  const _CostScope(this.owner, this.stage);
  final LogicalCost owner;
  final LogicalCostStage stage;
}

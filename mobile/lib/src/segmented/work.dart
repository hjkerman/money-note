// Operation counters, never integrity or authorization evidence. No callbacks.
class SegmentedWork {
  final Map<String, int> _counts = {};
  void add(String name, [int count = 1]) =>
      _counts[name] = (_counts[name] ?? 0) + count;
  Map<String, int> snapshot() => Map.unmodifiable(_counts);
  Map<String, int> since(Map<String, int> before) => {
        for (final key in {...before.keys, ..._counts.keys})
          key: (_counts[key] ?? 0) - (before[key] ?? 0)
      };
}

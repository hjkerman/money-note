/// 등록 화면의 최초 체크 상태만 제안한다. 실제 할인액은 서버가 계산한다.
bool? cardDiscountDefaultEnabled(
  bool? policyEnabled,
  String? usagePlace,
  String? usageItem, {
  bool? explicitChoice,
}) {
  if (explicitChoice != null) return explicitChoice;
  const utilityWords = ['도시가스', '가스요금', '전기', '전력', '수도'];
  final place = usagePlace ?? '';
  final item = usageItem ?? '';
  if (utilityWords.any((word) => place.contains(word) || item.contains(word))) {
    return false;
  }
  return policyEnabled;
}

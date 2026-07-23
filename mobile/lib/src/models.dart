class AuthUser {
  AuthUser({
    required this.id,
    required this.username,
    required this.displayName,
    required this.sharePinNeedsChange,
    this.sessionToken,
  });

  final int id;
  final String username;
  final String displayName;
  final bool sharePinNeedsChange;
  final String? sessionToken;

  factory AuthUser.fromJson(Map<String, dynamic> json) {
    return AuthUser(
      id: json['id'] as int,
      username: json['username'] as String,
      displayName: json['display_name'] as String,
      sharePinNeedsChange: json['share_pin_needs_change'] as bool? ?? false,
      sessionToken: json['session_token'] as String?,
    );
  }
}

class Summary {
  Summary({
    required this.cardTotal,
    required this.currentSpendingTotal,
    required this.currentDiscountTotal,
    required this.plannedRecurringTotal,
    required this.fixedCashTotal,
    required this.frozenAssetTotal,
    required this.liquidityStatus,
    required this.nextMonthLiquidity,
    required this.claimOriginalTotal,
    required this.claimNetTotal,
    required this.familyCardOriginalTotal,
    required this.familyCardNetTotal,
    required this.visibleCashFlowTotal,
  });

  final int cardTotal;
  final int currentSpendingTotal;
  final int currentDiscountTotal;
  final int plannedRecurringTotal;
  final int fixedCashTotal;
  final int frozenAssetTotal;
  final int liquidityStatus;
  final int nextMonthLiquidity;
  final int claimOriginalTotal;
  final int claimNetTotal;
  final int familyCardOriginalTotal;
  final int familyCardNetTotal;
  final int visibleCashFlowTotal;

  factory Summary.fromJson(Map<String, dynamic> json) {
    return Summary(
      cardTotal: _int(json['card_total']),
      currentSpendingTotal: _int(json['current_spending_total']),
      currentDiscountTotal: _int(json['current_discount_total']),
      plannedRecurringTotal: _int(json['planned_recurring_total']),
      fixedCashTotal: _int(json['fixed_cash_total']),
      frozenAssetTotal: _int(json['frozen_asset_total']),
      liquidityStatus: _int(json['liquidity_status']),
      nextMonthLiquidity: _int(json['next_month_liquidity']),
      claimOriginalTotal: _int(json['claim_original_total']),
      claimNetTotal: _int(json['claim_net_total']),
      familyCardOriginalTotal: _int(json['family_card_original_total']),
      familyCardNetTotal: _int(json['family_card_net_total']),
      visibleCashFlowTotal: _int(json['visible_cash_flow_total']),
    );
  }
}

class LedgerEntry {
  LedgerEntry({
    required this.id,
    required this.bookSection,
    required this.entryKind,
    required this.title,
    required this.sortOrder,
    this.entryDate,
    this.usagePlace,
    this.usageItem,
    this.amountValue,
    this.spendingCategory,
    this.paymentKey,
    this.auxAmountValue,
    this.discountOverride = 0,
    this.discountPolicy = 'disabled',
    this.automaticDiscountEligible = false,
    this.automaticDiscountAmount = 0,
    this.effectiveDiscountAmount = 0,
    this.effectiveAmountValue,
    this.isTransport = false,
    this.isToll = false,
    this.dueDay,
    this.confirmedMonth,
  });

  final int id;
  final String bookSection;
  final String entryKind;
  final String title;
  final int sortOrder;
  final String? entryDate;
  final String? usagePlace;
  final String? usageItem;
  final int? amountValue;
  final String? spendingCategory;
  final String? paymentKey;
  final int? auxAmountValue;
  final int discountOverride;
  final String discountPolicy;
  final bool automaticDiscountEligible;
  final int automaticDiscountAmount;
  final int effectiveDiscountAmount;
  final int? effectiveAmountValue;
  final bool isTransport;
  final bool isToll;
  final int? dueDay;
  final String? confirmedMonth;

  int get manualDiscount => discountOverride != 0 ? (auxAmountValue ?? 0) : 0;
  bool get isDiscountExcluded =>
      discountOverride != 0 && effectiveDiscountAmount <= 0;
  bool get isDiscountIneligible => !automaticDiscountEligible;
  bool get isDiscountPolicyEnabled => discountPolicy == 'enabled';
  int get effectiveAmount => effectiveAmountValue ?? (amountValue ?? 0);

  factory LedgerEntry.fromJson(Map<String, dynamic> json) {
    return LedgerEntry(
      id: json['id'] as int,
      bookSection: json['book_section'] as String,
      entryKind: json['entry_kind'] as String,
      title: json['title'] as String? ?? '',
      sortOrder: _int(json['sort_order']),
      entryDate: json['entry_date'] as String?,
      usagePlace: json['usage_place'] as String?,
      usageItem: json['usage_item'] as String?,
      amountValue:
          json['amount_value'] == null ? null : _int(json['amount_value']),
      spendingCategory: json['spending_category'] as String?,
      paymentKey: json['payment_key'] as String?,
      auxAmountValue: json['aux_amount_value'] == null
          ? null
          : _int(json['aux_amount_value']),
      discountOverride: _int(json['discount_override']),
      discountPolicy: json['discount_policy'] as String? ?? 'disabled',
      automaticDiscountEligible:
          json['automatic_discount_eligible'] as bool? ?? false,
      automaticDiscountAmount: _int(json['automatic_discount_amount']),
      effectiveDiscountAmount: _int(json['effective_discount_amount']),
      effectiveAmountValue: json['effective_amount_value'] == null
          ? null
          : _int(json['effective_amount_value']),
      isTransport: json['is_transport'] as bool? ?? false,
      isToll: json['is_toll'] as bool? ?? false,
      dueDay: json['due_day'] == null ? null : _int(json['due_day']),
      confirmedMonth: json['confirmed_month'] as String?,
    );
  }
}

class MonthlyPanel {
  MonthlyPanel({
    required this.id,
    required this.month,
    required this.panelType,
    required this.title,
    required this.sortOrder,
    required this.discountAmount,
    required this.discountOverride,
    this.discountPolicy = 'disabled',
    this.automaticDiscountEligible = false,
    this.automaticDiscountAmount = 0,
    this.effectiveDiscountAmount = 0,
    this.effectiveAmountValue,
    this.spentOn,
    this.amountValue,
    this.dueDay,
  });

  final int id;
  final String month;
  final String panelType;
  final String title;
  final int sortOrder;
  final int discountAmount;
  final int discountOverride;
  final String discountPolicy;
  final bool automaticDiscountEligible;
  final int automaticDiscountAmount;
  final int effectiveDiscountAmount;
  final int? effectiveAmountValue;
  final String? spentOn;
  final int? amountValue;
  final int? dueDay;

  int get effectiveAmount => effectiveAmountValue ?? (amountValue ?? 0);
  bool get isDiscountExcluded =>
      discountOverride != 0 && effectiveDiscountAmount <= 0;
  bool get isDiscountIneligible => !automaticDiscountEligible;
  bool get isDiscountPolicyEnabled => discountPolicy == 'enabled';

  factory MonthlyPanel.fromJson(Map<String, dynamic> json) {
    return MonthlyPanel(
      id: json['id'] as int,
      month: json['month'] as String,
      panelType: json['panel_type'] as String,
      title: json['title'] as String? ?? '',
      sortOrder: _int(json['sort_order']),
      discountAmount: _int(json['discount_amount']),
      discountOverride: _int(json['discount_override']),
      discountPolicy: json['discount_policy'] as String? ?? 'disabled',
      automaticDiscountEligible:
          json['automatic_discount_eligible'] as bool? ?? false,
      automaticDiscountAmount: _int(json['automatic_discount_amount']),
      effectiveDiscountAmount: _int(json['effective_discount_amount']),
      effectiveAmountValue: json['effective_amount_value'] == null
          ? null
          : _int(json['effective_amount_value']),
      spentOn: json['spent_on'] as String?,
      amountValue:
          json['amount_value'] == null ? null : _int(json['amount_value']),
      dueDay: json['due_day'] == null ? null : _int(json['due_day']),
    );
  }
}

class CashFlow {
  CashFlow({
    required this.id,
    required this.occurredOn,
    required this.title,
    required this.amountValue,
    required this.sortOrder,
    required this.isPrimaryIncome,
  });

  final int id;
  final String occurredOn;
  final String title;
  final int amountValue;
  final int sortOrder;
  final bool isPrimaryIncome;

  factory CashFlow.fromJson(Map<String, dynamic> json) {
    return CashFlow(
      id: json['id'] as int,
      occurredOn: json['occurred_on'] as String,
      title: json['title'] as String? ?? '',
      amountValue: _int(json['amount_value']),
      sortOrder: _int(json['sort_order']),
      isPrimaryIncome: _int(json['is_primary_income']) == 1,
    );
  }
}

class SpendingCategoryOption {
  const SpendingCategoryOption({required this.value, required this.label});

  final String? value;
  final String label;
}

const spendingCategoryOptions = [
  SpendingCategoryOption(value: null, label: '미분류'),
  SpendingCategoryOption(value: 'essential', label: '안 썼으면 큰일'),
  SpendingCategoryOption(value: 'questionable', label: '꼭 써야 했을까...?'),
  SpendingCategoryOption(value: 'dignity', label: '최소한의 품위유지비'),
];

String spendingCategoryLabel(String? value) {
  for (final option in spendingCategoryOptions) {
    if (option.value == value) return option.label;
  }
  return '미분류';
}

String? normalizeSpendingCategory(String? value) {
  if (value == null || value.isEmpty) return null;
  for (final option in spendingCategoryOptions) {
    if (option.value == value) return value;
  }
  return null;
}

class CardDiscountMonth {
  CardDiscountMonth({
    required this.month,
    required this.scope,
    required this.policy,
  });

  final String month;
  final String scope;
  final String policy;

  bool get isEnabled => policy == 'enabled';

  factory CardDiscountMonth.fromJson(Map<String, dynamic> json) {
    return CardDiscountMonth(
      month: json['month'] as String? ?? '',
      scope: json['scope'] as String? ?? '',
      policy: json['policy'] as String? ?? 'disabled',
    );
  }
}

class MonthCloseStatus {
  MonthCloseStatus({
    required this.calendarDate,
    required this.calendarMonth,
    required this.needsClose,
    required this.isEarlyClose,
    required this.earlyCloseAvailable,
    required this.earlyCloseStartDay,
    required this.canClose,
    this.oldestOpenMonth,
    this.lastClosedMonth,
  });

  final String calendarDate;
  final String calendarMonth;
  final String? oldestOpenMonth;
  final String? lastClosedMonth;
  final bool needsClose;
  final bool isEarlyClose;
  final bool earlyCloseAvailable;
  final int earlyCloseStartDay;
  final bool canClose;

  factory MonthCloseStatus.fromJson(Map<String, dynamic> json) {
    return MonthCloseStatus(
      calendarDate: json['calendar_date'] as String? ?? '',
      calendarMonth: json['calendar_month'] as String? ?? '',
      oldestOpenMonth: json['oldest_open_month'] as String?,
      lastClosedMonth: json['last_closed_month'] as String?,
      needsClose: json['needs_close'] as bool? ?? false,
      isEarlyClose: json['is_early_close'] as bool? ?? false,
      earlyCloseAvailable: json['early_close_available'] as bool? ?? false,
      earlyCloseStartDay: _int(json['early_close_start_day']),
      canClose: json['can_close'] as bool? ?? false,
    );
  }
}

class AppSettings {
  AppSettings({
    required this.values,
  });

  final Map<String, String> values;

  String get ownerCardLast4 => values['owner_card_last4'] ?? '';
  String get familyCardLast4 => values['family_card_last4'] ?? '';

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    return AppSettings(
        values:
            json.map((key, value) => MapEntry(key, value?.toString() ?? '')));
  }
}

class CardNotificationCandidate {
  CardNotificationCandidate({
    required this.id,
    required this.capturedAt,
    required this.cardLast4,
    required this.cardRole,
    required this.entryDate,
    required this.amount,
    required this.merchant,
    required this.rawText,
  });

  final String id;
  final int capturedAt;
  final String cardLast4;
  final String cardRole;
  final String entryDate;
  final int amount;
  final String merchant;
  final String rawText;

  bool get isOwnerCard => cardRole == 'owner';
  bool get isFamilyCard => cardRole == 'family';

  factory CardNotificationCandidate.fromJson(Map<String, dynamic> json) {
    return CardNotificationCandidate(
      id: json['id'] as String? ?? '',
      capturedAt: _int(json['captured_at']),
      cardLast4: json['card_last4'] as String? ?? '',
      cardRole: json['card_role'] as String? ?? '',
      entryDate: json['entry_date'] as String? ?? '',
      amount: _int(json['amount']),
      merchant: json['merchant'] as String? ?? '',
      rawText: json['raw_text'] as String? ?? '',
    );
  }
}

class CapturedNotificationLog {
  CapturedNotificationLog({
    required this.id,
    required this.source,
    required this.capturedAt,
    required this.packageName,
    required this.title,
    required this.text,
    required this.bigText,
    required this.subText,
    required this.textLines,
    required this.rawText,
    required this.notificationKey,
    required this.postTime,
    required this.isOngoing,
    required this.category,
    required this.isApprovalCandidate,
    required this.parseStatus,
    required this.parseFailureReason,
    required this.cardLast4,
    required this.entryDate,
    required this.amount,
    required this.merchant,
  });

  final String id;
  final String source;
  final int capturedAt;
  final String packageName;
  final String title;
  final String text;
  final String bigText;
  final String subText;
  final List<String> textLines;
  final String rawText;
  final String notificationKey;
  final int postTime;
  final bool isOngoing;
  final String category;
  final bool isApprovalCandidate;
  final String parseStatus;
  final String parseFailureReason;
  final String cardLast4;
  final String entryDate;
  final int amount;
  final String merchant;

  bool get needsManualReview =>
      parseStatus == 'failed' || parseStatus == 'installment_manual';

  factory CapturedNotificationLog.fromJson(Map<String, dynamic> json) {
    return CapturedNotificationLog(
      id: json['id'] as String? ?? '',
      source: json['source'] as String? ?? 'woori_card',
      capturedAt: _int(json['captured_at']),
      packageName: json['package_name'] as String? ?? '',
      title: json['title'] as String? ?? '',
      text: json['text'] as String? ?? '',
      bigText: json['big_text'] as String? ?? '',
      subText: json['sub_text'] as String? ?? '',
      textLines: (json['text_lines'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      rawText: json['raw_text'] as String? ?? '',
      notificationKey: json['notification_key'] as String? ?? '',
      postTime: _int(json['post_time']),
      isOngoing: json['is_ongoing'] as bool? ?? false,
      category: json['category'] as String? ?? '',
      isApprovalCandidate: json['is_approval_candidate'] as bool? ?? false,
      parseStatus: json['parse_status'] as String? ?? '',
      parseFailureReason: json['parse_failure_reason'] as String? ?? '',
      cardLast4: json['card_last4'] as String? ?? '',
      entryDate: json['entry_date'] as String? ?? '',
      amount: _int(json['amount']),
      merchant: json['merchant'] as String? ?? '',
    );
  }
}

class NotificationCandidateCounts {
  const NotificationCandidateCounts({
    required this.owner,
    required this.family,
    required this.manualReview,
  });

  const NotificationCandidateCounts.empty()
      : owner = 0,
        family = 0,
        manualReview = 0;

  final int owner;
  final int family;
  final int manualReview;

  int get total => owner + family;
}

class JudgmentTone {
  JudgmentTone({required this.message});

  final String message;

  factory JudgmentTone.fromJson(Map<String, dynamic> json) {
    return JudgmentTone(message: json['message'] as String? ?? '');
  }
}

class JudgmentState {
  JudgmentState({
    required this.budget,
    required this.credit,
    required this.payment,
  });

  final JudgmentTone budget;
  final JudgmentTone credit;
  final JudgmentTone payment;

  factory JudgmentState.fromJson(Map<String, dynamic> json) {
    return JudgmentState(
      budget: JudgmentTone.fromJson(
          json['budget'] as Map<String, dynamic>? ?? const {}),
      credit: JudgmentTone.fromJson(
          json['credit'] as Map<String, dynamic>? ?? const {}),
      payment: JudgmentTone.fromJson(
          json['payment'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

int _int(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value) ?? 0;
  return 0;
}

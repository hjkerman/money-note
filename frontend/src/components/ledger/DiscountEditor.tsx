import { formatWon } from "../../utils";

export function DiscountEditor({
  currentAmount,
  defaultAmount,
  isOverride,
  onExclude,
  onClear,
  disabled = false,
}: {
  currentAmount: number;
  defaultAmount: number;
  isOverride: boolean;
  onExclude: () => void;
  onClear?: () => void;
  disabled?: boolean;
}) {
  const hasDiscount = currentAmount > 0;
  const showOverrideDiscount = disabled && isOverride;
  const badgeText =
    disabled && !showOverrideDiscount
      ? "혜택 없음"
      : `할인 ${formatWon(isOverride ? currentAmount : defaultAmount)}`;
  return (
    <div className="discount-editor">
      <div>
        <span
          className={
            (disabled && !showOverrideDiscount) || !hasDiscount
              ? "discount-badge muted-discount-badge"
              : "discount-badge"
          }
        >
          {badgeText}
        </span>
        {!disabled && hasDiscount ? (
          <button type="button" onClick={onExclude}>
            할인 제외
          </button>
        ) : null}
        {!disabled && !hasDiscount ? (
          <button type="button" onClick={onClear} disabled={!onClear}>
            할인 적용
          </button>
        ) : null}
      </div>
    </div>
  );
}

export type PaymentPayload = {
  event_date: string;
  event_type: "immediate";
  note: string;
  allocations: { entry_payment_key: string; amount_value: number }[];
};

export type PendingPayment = {
  fingerprint: string;
  key: string;
  payload: PaymentPayload;
  draftAllocations: Record<string, string>;
};

type PaymentStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export class PendingPaymentStore {
  constructor(
    private readonly storage: () => PaymentStorage,
    private readonly createKey: () => string = createIdempotencyKey,
  ) {}

  static fingerprint(payload: PaymentPayload): string {
    return JSON.stringify(payload);
  }

  static storageKey(userId: number): string {
    return `money-note-pending-card-payment-v1:${userId}`;
  }

  create(payload: PaymentPayload, draftAllocations: Record<string, string>): PendingPayment {
    return {
      fingerprint: PendingPaymentStore.fingerprint(payload),
      key: this.createKey(),
      payload,
      draftAllocations: { ...draftAllocations },
    };
  }

  read(userId: number): PendingPayment | "corrupt" | null {
    try {
      const raw = this.storage().getItem(PendingPaymentStore.storageKey(userId));
      if (!raw) return null;
      const pending = JSON.parse(raw) as PendingPayment;
      if (
        typeof pending.key !== "string" ||
        pending.key.length < 16 ||
        typeof pending.fingerprint !== "string" ||
        !pending.payload ||
        !pending.draftAllocations ||
        typeof pending.draftAllocations !== "object" ||
        Array.isArray(pending.draftAllocations) ||
        PendingPaymentStore.fingerprint(pending.payload) !== pending.fingerprint
      ) return "corrupt";
      return pending;
    } catch {
      return "corrupt";
    }
  }

  save(userId: number, pending: PendingPayment): void {
    this.storage().setItem(PendingPaymentStore.storageKey(userId), JSON.stringify(pending));
  }

  clear(userId: number): void {
    this.storage().removeItem(PendingPaymentStore.storageKey(userId));
  }
}

function createIdempotencyKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

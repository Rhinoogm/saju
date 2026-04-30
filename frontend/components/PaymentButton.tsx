"use client";

import * as PortOne from "@portone/browser-sdk/v2";
import type { User } from "@supabase/supabase-js";
import { CreditCard, LoaderCircle } from "lucide-react";
import { useState } from "react";

import { ApiError, completePayment, createCheckout, type CheckoutResponse } from "@/lib/api";
import { isLocalDemoMode } from "@/lib/localDemo";

interface PaymentButtonProps {
  sessionId: string;
  user: User;
  onPaid: () => Promise<void> | void;
  onError: (message: string) => void;
}

export function PaymentButton({ sessionId, user, onPaid, onError }: PaymentButtonProps) {
  const [loading, setLoading] = useState(false);
  const [checkout, setCheckout] = useState<CheckoutResponse | null>(null);

  async function handlePayment() {
    setLoading(true);
    onError("");
    try {
      const payment = checkout ?? (await createCheckout(sessionId));
      setCheckout(payment);
      if (isLocalDemoMode()) {
        await completePayment(payment.payment_id);
        await onPaid();
        return;
      }

      const paymentRequest = {
        storeId: payment.store_id,
        channelKey: payment.channel_key,
        paymentId: payment.payment_id,
        orderName: payment.order_name,
        totalAmount: payment.total_amount,
        currency: payment.currency,
        payMethod: "CARD",
        customer: {
          customerId: user.id,
          email: user.email ?? undefined,
        },
        noticeUrls: payment.notice_urls,
      };
      const response = await PortOne.requestPayment(paymentRequest as Parameters<typeof PortOne.requestPayment>[0]);

      if (response?.code !== undefined) {
        throw new Error(response.message ?? "결제가 완료되지 않았습니다.");
      }

      await completePayment(payment.payment_id);
      await onPaid();
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        onError("결제 검증에 실패했어요. 결제가 완료됐다면 잠시 뒤 계정 페이지에서 상태를 확인해주세요.");
      } else {
        onError(error instanceof Error ? error.message : "결제 처리 중 오류가 발생했어요.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      disabled={loading}
      onClick={() => void handlePayment()}
      className="flex h-14 w-full items-center justify-center gap-2 rounded-lg bg-coral px-5 text-base font-black text-white shadow-soft transition hover:bg-berry disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading ? <LoaderCircle className="animate-spin" size={20} aria-hidden /> : <CreditCard size={19} aria-hidden />}
      {loading ? "결제 확인 중" : isLocalDemoMode() ? "모의 결제로 계속하기" : "1회권 결제하기"}
    </button>
  );
}

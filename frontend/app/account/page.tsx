"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, LoaderCircle, ReceiptText, ScrollText } from "lucide-react";

import { getAccountMe, getAccountOrders, getAccountReadings, type AccountMeResponse, type AccountOrderResponse, type AccountReadingResponse } from "@/lib/api";

export default function AccountPage() {
  const [me, setMe] = useState<AccountMeResponse | null>(null);
  const [orders, setOrders] = useState<AccountOrderResponse[]>([]);
  const [readings, setReadings] = useState<AccountReadingResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setError("");
      try {
        const [meResponse, orderResponse, readingResponse] = await Promise.all([getAccountMe(), getAccountOrders(), getAccountReadings()]);
        setMe(meResponse);
        setOrders(orderResponse);
        setReadings(readingResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : "계정 정보를 불러오지 못했어요.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl space-y-5">
        <header className="flex flex-col gap-3 rounded-lg border border-stone-200 bg-white p-5 shadow-soft sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-black uppercase text-mint">Account</p>
            <h1 className="mt-1 text-2xl font-black text-ink">내 계정</h1>
            <p className="mt-2 text-sm font-bold text-stone-500">{me?.email ?? "로그인 계정"}</p>
          </div>
          <Link href="/" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 px-4 text-sm font-black text-stone-600">
            <ArrowLeft size={16} aria-hidden />
            돌아가기
          </Link>
        </header>

        {loading && (
          <div className="flex items-center gap-2 rounded-lg border border-mint/20 bg-white px-4 py-3 text-sm font-black text-mint shadow-soft">
            <LoaderCircle className="animate-spin" size={17} aria-hidden />
            불러오는 중
          </div>
        )}
        {error && <div className="rounded-lg border border-coral/20 bg-white px-4 py-3 text-sm font-bold text-coral shadow-soft">{error}</div>}

        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
          <h2 className="flex items-center gap-2 text-lg font-black text-ink">
            <ReceiptText size={18} aria-hidden />
            구매 내역
          </h2>
          <div className="mt-4 divide-y divide-stone-100">
            {orders.length === 0 && <p className="py-4 text-sm font-bold text-stone-500">구매 내역이 없습니다.</p>}
            {orders.map((order) => (
              <div key={order.id} className="flex flex-col gap-1 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-black text-ink">{order.order_name}</p>
                  <p className="mt-1 text-xs font-bold text-stone-500">{order.payment_id}</p>
                </div>
                <p className="text-sm font-black text-stone-700">
                  {order.amount_krw.toLocaleString("ko-KR")}원 · {order.status}
                </p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
          <h2 className="flex items-center gap-2 text-lg font-black text-ink">
            <ScrollText size={18} aria-hidden />
            내 리딩
          </h2>
          <div className="mt-4 divide-y divide-stone-100">
            {readings.length === 0 && <p className="py-4 text-sm font-bold text-stone-500">리딩 세션이 없습니다.</p>}
            {readings.map((reading) => (
              <div key={reading.id} className="flex flex-col gap-1 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-black text-ink">{reading.reading_style}</p>
                  <p className="mt-1 text-xs font-bold text-stone-500">{reading.id}</p>
                </div>
                <p className="text-sm font-black text-stone-700">{reading.has_final_result ? "결과 완료" : reading.status}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

import Link from "next/link";

import { AuthButtons } from "@/components/AuthButtons";

export default function LoginPage() {
  return (
    <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-md rounded-lg border border-[#eadfce] bg-[#fffdf8] p-6 shadow-soft">
        <p className="mb-3 inline-flex items-center rounded-full bg-[#fff0b9] px-3 py-1.5 text-xs font-black text-[#6e5428]">사주 심리 리딩</p>
        <h1 className="text-3xl font-black leading-tight text-ink">로그인</h1>
        <p className="mt-3 text-sm font-bold leading-6 text-stone-500">리딩 세션, 결제 내역, 결과 조회를 계정에 안전하게 연결합니다.</p>
        <div className="mt-6">
          <AuthButtons />
        </div>
        <Link href="/" className="mt-5 inline-flex text-sm font-black text-stone-500 transition hover:text-coral">
          메인으로 돌아가기
        </Link>
      </div>
    </main>
  );
}

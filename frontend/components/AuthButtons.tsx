"use client";

import { LogIn, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { isLocalDemoMode, signInLocalDemo } from "@/lib/localDemo";
import { createClient } from "@/lib/supabase/client";

export function AuthButtons() {
  const router = useRouter();
  const [loadingProvider, setLoadingProvider] = useState<"google" | "kakao" | null>(null);
  const [error, setError] = useState("");

  function signInDemo() {
    signInLocalDemo();
    router.push("/");
    router.refresh();
  }

  async function signIn(provider: "google" | "kakao") {
    setError("");
    setLoadingProvider(provider);
    try {
      const supabase = createClient();
      const redirectTo = `${window.location.origin}/auth/callback`;
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo },
      });
      if (error) {
        setError(error.message);
        setLoadingProvider(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인 설정을 확인해주세요.");
      setLoadingProvider(null);
    }
  }

  if (isLocalDemoMode()) {
    return (
      <div className="grid gap-3">
        <div className="rounded-lg border border-mint/25 bg-mint/10 px-4 py-3 text-sm font-black leading-6 text-mint">
          <span className="inline-flex items-center gap-2">
            <ShieldCheck size={16} aria-hidden />
            로컬 데모 모드입니다. 실제 OAuth 로그인 없이 데모 계정으로 진행합니다.
          </span>
        </div>
        <button
          type="button"
          onClick={signInDemo}
          className="flex h-12 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-black text-white shadow-soft transition hover:bg-stone-800"
        >
          <LogIn size={17} aria-hidden />
          모의 로그인으로 계속하기
        </button>
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      <button
        type="button"
        disabled={loadingProvider !== null}
        onClick={() => void signIn("google")}
        className="flex h-12 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-black text-white shadow-soft transition hover:bg-stone-800 disabled:opacity-60"
      >
        <LogIn size={17} aria-hidden />
        {loadingProvider === "google" ? "연결 중" : "Google로 로그인"}
      </button>
      <button
        type="button"
        disabled={loadingProvider !== null}
        onClick={() => void signIn("kakao")}
        className="flex h-12 items-center justify-center gap-2 rounded-lg bg-honey px-4 text-sm font-black text-[#4d3b21] shadow-soft transition hover:bg-[#f5c85f] disabled:opacity-60"
      >
        <LogIn size={17} aria-hidden />
        {loadingProvider === "kakao" ? "연결 중" : "Kakao로 로그인"}
      </button>
      {error && <p className="rounded-lg border border-coral/20 bg-coral/10 px-4 py-3 text-sm font-bold text-coral">{error}</p>}
    </div>
  );
}

"use client";

import type { User } from "@supabase/supabase-js";
import { LogOut, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { isLocalDemoMode, signOutLocalDemo } from "@/lib/localDemo";
import { createClient } from "@/lib/supabase/client";

export function UserMenu({ user }: { user: User | null }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function signOut() {
    setLoading(true);
    setError("");
    try {
      if (isLocalDemoMode()) {
        signOutLocalDemo();
        router.refresh();
        router.push("/login");
        return;
      }
      const supabase = createClient();
      await supabase.auth.signOut();
      router.refresh();
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그아웃에 실패했습니다.");
      setLoading(false);
    }
  }

  if (!user) {
    return (
      <Link href="/login" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-ink px-4 text-sm font-black text-white">
        <UserRound size={16} aria-hidden />
        로그인
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Link href="/account" className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 bg-white px-3 text-sm font-black text-stone-700">
        <UserRound size={16} aria-hidden />
        내 계정
      </Link>
      <button
        type="button"
        disabled={loading}
        onClick={() => void signOut()}
        className="grid h-10 w-10 place-items-center rounded-lg border border-stone-200 bg-white text-stone-600 transition hover:text-coral disabled:opacity-60"
        aria-label="로그아웃"
      >
        <LogOut size={17} aria-hidden />
      </button>
      {error && <span className="sr-only">{error}</span>}
    </div>
  );
}

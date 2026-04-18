"use client";

import { useEffect, useMemo, useState } from "react";

type PromptName = "question_system_prompt" | "final_system_prompt";

interface PromptResponse {
  name: string;
  content: string;
  updated_at: string;
}

const STORAGE_KEY = "saju_admin_api_key";

function apiBaseUrl() {
  return (
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    (typeof window === "undefined" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}:8000`)
  );
}

async function fetchPrompt(name: PromptName, adminKey: string): Promise<PromptResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/admin/prompts/${name}`, {
    headers: {
      "X-Admin-Key": adminKey,
    },
    cache: "no-store",
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : `불러오기 실패 (${response.status})`);
  }
  return body as PromptResponse;
}

async function savePrompt(name: PromptName, content: string, adminKey: string): Promise<PromptResponse> {
  const response = await fetch(`${apiBaseUrl()}/api/admin/prompts/${name}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
    },
    body: JSON.stringify({ content }),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : `저장 실패 (${response.status})`);
  }
  return body as PromptResponse;
}

export default function AdminPromptsPage() {
  const promptNames: { name: PromptName; label: string }[] = useMemo(
    () => [
      { name: "question_system_prompt", label: "질문 생성 System Prompt" },
      { name: "final_system_prompt", label: "최종 풀이 System Prompt" },
    ],
    [],
  );

  const [adminKey, setAdminKey] = useState("");
  const [content, setContent] = useState<Record<PromptName, string>>({
    question_system_prompt: "",
    final_system_prompt: "",
  });
  const [updatedAt, setUpdatedAt] = useState<Record<PromptName, string | null>>({
    question_system_prompt: null,
    final_system_prompt: null,
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) setAdminKey(stored);
  }, []);

  function persistKey(next: string) {
    setAdminKey(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }

  async function handleLoad() {
    setError("");
    setMessage("");
    if (!adminKey.trim()) {
      setError("Admin Key를 입력해주세요.");
      return;
    }
    setLoading(true);
    try {
      const [question, final] = await Promise.all([
        fetchPrompt("question_system_prompt", adminKey.trim()),
        fetchPrompt("final_system_prompt", adminKey.trim()),
      ]);
      setContent({
        question_system_prompt: question.content,
        final_system_prompt: final.content,
      });
      setUpdatedAt({
        question_system_prompt: question.updated_at,
        final_system_prompt: final.updated_at,
      });
      setMessage("불러오기 완료");
    } catch (err) {
      setError(err instanceof Error ? err.message : "불러오기 중 오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(name: PromptName) {
    setError("");
    setMessage("");
    if (!adminKey.trim()) {
      setError("Admin Key를 입력해주세요.");
      return;
    }
    const nextContent = content[name].trim();
    if (!nextContent) {
      setError("프롬프트 내용이 비어있어요.");
      return;
    }
    setLoading(true);
    try {
      const saved = await savePrompt(name, nextContent, adminKey.trim());
      setContent((current) => ({ ...current, [name]: saved.content }));
      setUpdatedAt((current) => ({ ...current, [name]: saved.updated_at }));
      setMessage("저장 완료 (즉시 반영)");
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장 중 오류가 발생했어요.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-cloud px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl space-y-5">
        <header className="rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
          <h1 className="text-2xl font-black text-ink">관리자 · 프롬프트 편집</h1>
          <p className="mt-2 text-sm leading-6 text-stone-500">수정 후 저장하면 다음 LLM 요청부터 즉시 적용됩니다.</p>

          <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <label className="block">
              <span className="mb-2 block text-sm font-black text-stone-700">Admin Key</span>
              <input
                value={adminKey}
                onChange={(e) => persistKey(e.target.value)}
                placeholder="ADMIN_API_KEY"
                className="w-full rounded-lg border border-stone-200 bg-white px-4 py-3 text-base text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
              />
            </label>
            <button
              type="button"
              disabled={loading}
              onClick={handleLoad}
              className="h-[50px] rounded-lg bg-mint px-5 text-sm font-black text-white shadow-soft transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? "불러오는 중" : "불러오기"}
            </button>
          </div>

          {error && <div className="mt-4 rounded-lg border border-coral/20 bg-coral/10 px-4 py-3 text-sm font-bold leading-6 text-coral">{error}</div>}
          {message && <div className="mt-4 rounded-lg border border-mint/20 bg-mint/10 px-4 py-3 text-sm font-bold leading-6 text-mint">{message}</div>}
        </header>

        <div className="grid gap-4">
          {promptNames.map(({ name, label }) => (
            <section key={name} className="rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-lg font-black text-ink">{label}</h2>
                  <p className="mt-1 text-xs font-bold text-stone-500">name: {name}</p>
                  {updatedAt[name] && <p className="mt-1 text-xs font-bold text-stone-500">updated_at: {updatedAt[name]}</p>}
                </div>
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => handleSave(name)}
                  className="h-11 rounded-lg bg-coral px-4 text-sm font-black text-white shadow-soft transition hover:bg-berry disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {loading ? "저장 중" : "저장"}
                </button>
              </div>

              <textarea
                value={content[name]}
                onChange={(e) => setContent((current) => ({ ...current, [name]: e.target.value }))}
                className="mt-4 min-h-72 w-full resize-y rounded-lg border border-stone-200 bg-cloud px-4 py-3 text-sm leading-7 text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
                placeholder="여기에 system prompt를 입력하세요."
              />
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}


"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCcw, Save, Settings2 } from "lucide-react";

type PromptName = "question_system_prompt" | "question_user_prompt" | "final_system_prompt" | "final_user_prompt";
type LLMProviderName = "ollama" | "groq";
type LLMSettingKey = "llm_provider" | "groq_model" | "ollama_model";

interface PromptResponse {
  name: PromptName;
  content: string;
  updated_at: string;
}

interface LLMSettingsResponse {
  llm_provider: LLMProviderName;
  groq_model: string;
  ollama_model: string;
  updated_at: Partial<Record<LLMSettingKey, string>>;
}

const STORAGE_KEY = "saju_admin_api_key";

const emptyContent: Record<PromptName, string> = {
  question_system_prompt: "",
  question_user_prompt: "",
  final_system_prompt: "",
  final_user_prompt: "",
};

const emptyPromptUpdatedAt: Record<PromptName, string | null> = {
  question_system_prompt: null,
  question_user_prompt: null,
  final_system_prompt: null,
  final_user_prompt: null,
};

const defaultLLMSettings: LLMSettingsResponse = {
  llm_provider: "ollama",
  groq_model: "",
  ollama_model: "",
  updated_at: {},
};

function apiBaseUrl() {
  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    (typeof window === "undefined" ? "http://localhost:8000" : `${window.location.protocol}//${window.location.hostname}:8000`);

  return baseUrl.replace(/\/+$/, "");
}

function apiUrl(path: string) {
  return `${apiBaseUrl()}/${path.replace(/^\/+/, "")}`;
}

async function readJson<TResponse>(response: Response, fallback: string): Promise<TResponse> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof body?.detail === "string" ? body.detail : `${fallback} (${response.status})`);
  }
  return body as TResponse;
}

async function fetchPrompts(adminKey: string): Promise<PromptResponse[]> {
  const response = await fetch(apiUrl("/api/admin/prompts"), {
    headers: {
      "X-Admin-Key": adminKey,
    },
    cache: "no-store",
  });
  return readJson<PromptResponse[]>(response, "프롬프트 불러오기 실패");
}

async function fetchLLMSettings(adminKey: string): Promise<LLMSettingsResponse> {
  const response = await fetch(apiUrl("/api/admin/settings/llm"), {
    headers: {
      "X-Admin-Key": adminKey,
    },
    cache: "no-store",
  });
  return readJson<LLMSettingsResponse>(response, "모델 설정 불러오기 실패");
}

async function savePrompt(name: PromptName, content: string, adminKey: string): Promise<PromptResponse> {
  const response = await fetch(apiUrl(`/api/admin/prompts/${name}`), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
    },
    body: JSON.stringify({ content }),
  });
  return readJson<PromptResponse>(response, "프롬프트 저장 실패");
}

async function saveLLMSettings(settings: LLMSettingsResponse, adminKey: string): Promise<LLMSettingsResponse> {
  const response = await fetch(apiUrl("/api/admin/settings/llm"), {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
    },
    body: JSON.stringify({
      llm_provider: settings.llm_provider,
      groq_model: settings.groq_model,
      ollama_model: settings.ollama_model,
    }),
  });
  return readJson<LLMSettingsResponse>(response, "모델 설정 저장 실패");
}

export default function AdminPromptsPage() {
  const promptNames: { name: PromptName; label: string; description: string }[] = useMemo(
    () => [
      { name: "question_system_prompt", label: "질문 System", description: "질문 생성 역할과 JSON 출력 규칙" },
      { name: "question_user_prompt", label: "질문 Prompt", description: "{profile_json}, {saju_json} 사용 가능" },
      { name: "final_system_prompt", label: "최종 답변 System", description: "최종 리포트 역할과 JSON 출력 규칙" },
      { name: "final_user_prompt", label: "최종 답변 Prompt", description: "{profile_json}, {saju_json}, {answers_json} 사용 가능" },
    ],
    [],
  );

  const [adminKey, setAdminKey] = useState("");
  const [content, setContent] = useState<Record<PromptName, string>>(emptyContent);
  const [updatedAt, setUpdatedAt] = useState<Record<PromptName, string | null>>(emptyPromptUpdatedAt);
  const [llmSettings, setLLMSettings] = useState<LLMSettingsResponse>(defaultLLMSettings);
  const [loading, setLoading] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);
  const [savingPrompt, setSavingPrompt] = useState<PromptName | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function persistKey(next: string) {
    setAdminKey(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }

  const loadAdminState = useCallback(async (key: string) => {
    setError("");
    setMessage("");
    const nextKey = key.trim();
    if (!nextKey) {
      setError("관리 비밀번호를 입력해주세요.");
      return;
    }

    setLoading(true);
    try {
      const [prompts, settings] = await Promise.all([fetchPrompts(nextKey), fetchLLMSettings(nextKey)]);
      const nextContent = { ...emptyContent };
      const nextUpdatedAt = { ...emptyPromptUpdatedAt };

      for (const prompt of prompts) {
        nextContent[prompt.name] = prompt.content;
        nextUpdatedAt[prompt.name] = prompt.updated_at || null;
      }

      setContent(nextContent);
      setUpdatedAt(nextUpdatedAt);
      setLLMSettings(settings);
      setMessage("불러오기 완료");
    } catch (err) {
      setError(err instanceof Error ? err.message : "관리자 설정을 불러오지 못했어요.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return;
    setAdminKey(stored);
    void loadAdminState(stored);
  }, [loadAdminState]);

  function handleLoad() {
    void loadAdminState(adminKey);
  }

  async function handleSaveSettings() {
    setError("");
    setMessage("");
    if (!adminKey.trim()) {
      setError("관리 비밀번호를 입력해주세요.");
      return;
    }
    if (!llmSettings.groq_model.trim() || !llmSettings.ollama_model.trim()) {
      setError("모델 이름을 입력해주세요.");
      return;
    }

    setSavingSettings(true);
    try {
      const saved = await saveLLMSettings(
        {
          ...llmSettings,
          groq_model: llmSettings.groq_model.trim(),
          ollama_model: llmSettings.ollama_model.trim(),
        },
        adminKey.trim(),
      );
      setLLMSettings(saved);
      setMessage("모델 설정 저장 완료. 다음 요청부터 적용됩니다.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "모델 설정 저장 중 오류가 발생했어요.");
    } finally {
      setSavingSettings(false);
    }
  }

  async function handleSavePrompt(name: PromptName) {
    setError("");
    setMessage("");
    if (!adminKey.trim()) {
      setError("관리 비밀번호를 입력해주세요.");
      return;
    }
    const nextContent = content[name].trim();
    if (!nextContent) {
      setError("프롬프트 내용이 비어있어요.");
      return;
    }

    setSavingPrompt(name);
    try {
      const saved = await savePrompt(name, nextContent, adminKey.trim());
      setContent((current) => ({ ...current, [name]: saved.content }));
      setUpdatedAt((current) => ({ ...current, [name]: saved.updated_at }));
      setMessage("프롬프트 저장 완료. 다음 요청부터 적용됩니다.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "프롬프트 저장 중 오류가 발생했어요.");
    } finally {
      setSavingPrompt(null);
    }
  }

  return (
    <main className="min-h-screen bg-cloud px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-5">
        <header className="rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="mb-2 text-xs font-black uppercase tracking-wide text-mint">Admin</p>
              <h1 className="text-2xl font-black text-ink">모델 · 프롬프트 설정</h1>
            </div>
            <Link
              href="/"
              className="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 px-4 text-sm font-black text-stone-600 transition hover:border-mint hover:text-mint"
            >
              <ArrowLeft size={16} strokeWidth={2.4} aria-hidden="true" />
              돌아가기
            </Link>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <label className="block">
              <span className="mb-2 block text-sm font-black text-stone-700">관리 비밀번호</span>
              <input
                type="password"
                value={adminKey}
                onChange={(event) => persistKey(event.target.value)}
                placeholder="ADMIN_API_KEY"
                autoComplete="current-password"
                className="w-full rounded-lg border border-stone-200 bg-white px-4 py-3 text-base text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
              />
            </label>
            <button
              type="button"
              disabled={loading}
              onClick={handleLoad}
              className="inline-flex h-[50px] items-center justify-center gap-2 rounded-lg bg-mint px-5 text-sm font-black text-white shadow-soft transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <RefreshCcw size={16} strokeWidth={2.5} aria-hidden="true" />
              {loading ? "불러오는 중" : "불러오기"}
            </button>
          </div>

          {error && <div className="mt-4 rounded-lg border border-coral/20 bg-coral/10 px-4 py-3 text-sm font-bold leading-6 text-coral">{error}</div>}
          {message && <div className="mt-4 rounded-lg border border-mint/20 bg-mint/10 px-4 py-3 text-sm font-bold leading-6 text-mint">{message}</div>}
        </header>

        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-full bg-mint/10 text-mint">
                <Settings2 size={19} strokeWidth={2.5} aria-hidden="true" />
              </div>
              <div>
                <h2 className="text-lg font-black text-ink">LLM 모델</h2>
                <p className="mt-1 text-xs font-bold text-stone-500">provider: {llmSettings.llm_provider}</p>
              </div>
            </div>
            <button
              type="button"
              disabled={savingSettings}
              onClick={handleSaveSettings}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-coral px-4 text-sm font-black text-white shadow-soft transition hover:bg-berry disabled:cursor-not-allowed disabled:opacity-70"
            >
              <Save size={16} strokeWidth={2.5} aria-hidden="true" />
              {savingSettings ? "저장 중" : "모델 저장"}
            </button>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <label className="block">
              <span className="mb-2 block text-sm font-black text-stone-700">사용 Provider</span>
              <select
                value={llmSettings.llm_provider}
                onChange={(event) => setLLMSettings((current) => ({ ...current, llm_provider: event.target.value as LLMProviderName }))}
                className="h-12 w-full rounded-lg border border-stone-200 bg-cloud px-4 text-base font-bold text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
              >
                <option value="groq">Groq</option>
                <option value="ollama">Ollama</option>
              </select>
              {llmSettings.updated_at.llm_provider && <span className="mt-2 block text-xs font-bold text-stone-500">{llmSettings.updated_at.llm_provider}</span>}
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-black text-stone-700">Groq 모델</span>
              <input
                value={llmSettings.groq_model}
                onChange={(event) => setLLMSettings((current) => ({ ...current, groq_model: event.target.value }))}
                placeholder="openai/gpt-oss-20b"
                className="h-12 w-full rounded-lg border border-stone-200 bg-cloud px-4 text-base text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
              />
              {llmSettings.updated_at.groq_model && <span className="mt-2 block text-xs font-bold text-stone-500">{llmSettings.updated_at.groq_model}</span>}
            </label>

            <label className="block">
              <span className="mb-2 block text-sm font-black text-stone-700">Ollama 모델</span>
              <input
                value={llmSettings.ollama_model}
                onChange={(event) => setLLMSettings((current) => ({ ...current, ollama_model: event.target.value }))}
                placeholder="qwen3:4b"
                className="h-12 w-full rounded-lg border border-stone-200 bg-cloud px-4 text-base text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
              />
              {llmSettings.updated_at.ollama_model && <span className="mt-2 block text-xs font-bold text-stone-500">{llmSettings.updated_at.ollama_model}</span>}
            </label>
          </div>
        </section>

        <div className="grid gap-4">
          {promptNames.map(({ name, label, description }) => (
            <section key={name} className="rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-lg font-black text-ink">{label}</h2>
                  <p className="mt-1 text-xs font-bold text-stone-500">{description}</p>
                  {updatedAt[name] && <p className="mt-1 text-xs font-bold text-stone-500">{updatedAt[name]}</p>}
                </div>
                <button
                  type="button"
                  disabled={savingPrompt === name}
                  onClick={() => handleSavePrompt(name)}
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-coral px-4 text-sm font-black text-white shadow-soft transition hover:bg-berry disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Save size={16} strokeWidth={2.5} aria-hidden="true" />
                  {savingPrompt === name ? "저장 중" : "저장"}
                </button>
              </div>

              <textarea
                value={content[name]}
                onChange={(event) => setContent((current) => ({ ...current, [name]: event.target.value }))}
                className="mt-4 min-h-80 w-full resize-y rounded-lg border border-stone-200 bg-cloud px-4 py-3 font-mono text-sm leading-7 text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15"
                placeholder="프롬프트를 입력하세요."
              />
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}

"use client";

import { CalendarDays, Clock3, LoaderCircle, MessageSquareText, Send, UserRound } from "lucide-react";
import { FormEvent, useMemo } from "react";

import type { InitialProfile } from "@/lib/api";

const inputClass =
  "w-full rounded-lg border border-stone-200 bg-white px-4 py-3 text-base text-ink outline-none transition focus:border-coral focus:ring-4 focus:ring-coral/15";
const labelClass = "mb-2 flex items-center gap-2 text-sm font-bold text-stone-700";

interface InitialFormProps {
  profile: InitialProfile;
  loading: boolean;
  onChange: (profile: InitialProfile) => void;
  onSubmit: () => void;
  onSajuOnly: () => void;
}

export function InitialForm({ profile, loading, onChange, onSubmit, onSajuOnly }: InitialFormProps) {
  const currentYear = new Date().getFullYear();
  const years = useMemo(() => {
    const end = Math.min(2100, currentYear);
    return Array.from({ length: end - 1900 + 1 }, (_, index) => end - index);
  }, [currentYear]);

  function update<K extends keyof InitialProfile>(key: K, value: InitialProfile[K]) {
    onChange({ ...profile, [key]: value });
  }

  function updateBirth<K extends keyof InitialProfile["birth"]>(key: K, value: InitialProfile["birth"][K]) {
    onChange({ ...profile, birth: { ...profile.birth, [key]: value } });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-stone-200 bg-white p-4 shadow-soft sm:p-6">
      <section>
        <div className="mb-4">
          <h1 className="text-3xl font-black tracking-normal text-ink">사주 심리 리딩</h1>
          <p className="mt-2 text-sm leading-6 text-stone-500">생년월일시와 고민을 먼저 받고, 이어서 마음의 방향을 확인할 질문을 생성합니다.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <label>
            <span className={labelClass}>
              <UserRound size={17} aria-hidden /> 이름
            </span>
            <input
              className={inputClass}
              value={profile.name}
              onChange={(event) => update("name", event.target.value)}
              placeholder="홍길동"
              required
            />
          </label>

          <label>
            <span className={labelClass}>성별</span>
            <select className={inputClass} value={profile.gender} onChange={(event) => update("gender", event.target.value as InitialProfile["gender"])}>
              <option value="female">여성</option>
              <option value="male">남성</option>
              <option value="other">기타/미입력</option>
            </select>
          </label>
        </div>
      </section>

      <section className="rounded-lg border border-stone-200 bg-cloud p-4">
        <div className="mb-4 flex items-center gap-2 text-sm font-bold text-stone-700">
          <CalendarDays size={17} aria-hidden /> 생년월일시
        </div>

        <div className="mb-4 grid grid-cols-2 gap-2 rounded-lg bg-white p-1">
          {(["solar", "lunar"] as const).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => updateBirth("calendar_type", type)}
              className={`h-10 rounded-md px-3 text-sm font-bold transition ${
                profile.birth.calendar_type === type ? "bg-mint text-white shadow-sm" : "text-stone-600 hover:bg-stone-50"
              }`}
            >
              {type === "solar" ? "양력" : "음력"}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs font-bold text-stone-500">연도</span>
            <select className={inputClass} value={profile.birth.year} onChange={(event) => updateBirth("year", Number(event.target.value))}>
              {years.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-1 block text-xs font-bold text-stone-500">월</span>
            <input className={inputClass} type="number" min={1} max={12} value={profile.birth.month} onChange={(event) => updateBirth("month", Number(event.target.value))} />
          </label>
          <label>
            <span className="mb-1 block text-xs font-bold text-stone-500">일</span>
            <input className={inputClass} type="number" min={1} max={31} value={profile.birth.day} onChange={(event) => updateBirth("day", Number(event.target.value))} />
          </label>
          <label>
            <span className="mb-1 flex items-center gap-1 text-xs font-bold text-stone-500">
              <Clock3 size={14} aria-hidden /> 시
            </span>
            <input className={inputClass} type="number" min={0} max={23} value={profile.birth.hour} onChange={(event) => updateBirth("hour", Number(event.target.value))} />
          </label>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label>
            <span className="mb-1 block text-xs font-bold text-stone-500">분</span>
            <input className={inputClass} type="number" min={0} max={59} value={profile.birth.minute} onChange={(event) => updateBirth("minute", Number(event.target.value))} />
          </label>
          {profile.birth.calendar_type === "lunar" && (
            <label className="flex h-[50px] items-center gap-3 rounded-lg border border-stone-200 bg-white px-4 text-sm font-bold text-stone-700">
              <input
                type="checkbox"
                checked={profile.birth.is_leap_month}
                onChange={(event) => updateBirth("is_leap_month", event.target.checked)}
                className="h-5 w-5 accent-coral"
              />
              윤달
            </label>
          )}
        </div>

        <details className="mt-3 rounded-lg border border-stone-200 bg-white">
          <summary className="cursor-pointer list-none px-4 py-3 text-sm font-bold text-stone-700">태양시 보정</summary>
          <div className="grid gap-3 border-t border-stone-100 p-4 sm:grid-cols-2">
            <label>
              <span className="mb-1 block text-xs font-bold text-stone-500">출생 도시</span>
              <input className={inputClass} value={profile.birth.city} onChange={(event) => updateBirth("city", event.target.value)} />
            </label>
            <label>
              <span className="mb-1 block text-xs font-bold text-stone-500">경도</span>
              <input
                className={inputClass}
                type="number"
                step="0.0001"
                value={profile.birth.longitude ?? ""}
                onChange={(event) => updateBirth("longitude", event.target.value === "" ? null : Number(event.target.value))}
                placeholder="126.9780"
              />
            </label>
            <label className="flex h-[50px] items-center gap-3 rounded-lg bg-cloud px-4 text-sm font-bold text-stone-700 sm:col-span-2">
              <input
                type="checkbox"
                checked={profile.birth.use_solar_time}
                onChange={(event) => updateBirth("use_solar_time", event.target.checked)}
                className="h-5 w-5 accent-coral"
              />
              태양시 보정 사용
            </label>
          </div>
        </details>
      </section>

      <label className="block">
        <span className={labelClass}>
          <MessageSquareText size={17} aria-hidden /> 초기 고민
        </span>
        <textarea
          className={`${inputClass} min-h-36 resize-y leading-7`}
          value={profile.initial_concern}
          onChange={(event) => update("initial_concern", event.target.value)}
          placeholder="이직을 해야 할지 버텨야 할지 모르겠어요. 지금 회사에 있으면 안정적이지만 계속 답답합니다."
        />
      </label>

      <div className="grid gap-3 sm:grid-cols-2">
        <button
          type="button"
          onClick={onSajuOnly}
          disabled={loading}
          className="flex h-[54px] w-full items-center justify-center gap-2 rounded-lg border border-stone-200 bg-white px-5 text-base font-black text-stone-700 shadow-soft transition hover:bg-cloud disabled:cursor-not-allowed disabled:opacity-70"
        >
          사주만 보기
        </button>
        <button
          type="submit"
          disabled={loading}
          className="flex h-[54px] w-full items-center justify-center gap-2 rounded-lg bg-coral px-5 text-base font-black text-white shadow-soft transition hover:bg-berry disabled:cursor-not-allowed disabled:opacity-70"
        >
          {loading ? <LoaderCircle className="animate-spin" size={20} aria-hidden /> : <Send size={19} aria-hidden />}
          {loading ? "질문 생성 중" : "진단 질문 생성"}
        </button>
      </div>
    </form>
  );
}

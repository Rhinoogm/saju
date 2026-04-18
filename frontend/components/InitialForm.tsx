"use client";

import { CalendarDays, ChevronDown, Clock3, LoaderCircle, MapPin, MessageSquareText, Send, Sparkles, UserRound } from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useMemo } from "react";

import type { InitialProfile } from "@/lib/api";

const inputClass =
  "h-14 w-full rounded-lg border border-[#eadfce] bg-white px-4 text-base font-bold text-ink shadow-[0_8px_24px_rgba(83,64,42,0.06)] outline-none transition placeholder:text-stone-400 focus:border-coral focus:ring-4 focus:ring-coral/15";
const selectClass = `${inputClass} appearance-none pr-11`;
const labelClass = "mb-2 flex items-center gap-2 text-sm font-black text-stone-700";
const helperLabelClass = "mb-1.5 flex items-center gap-1.5 text-xs font-black text-stone-500";

const months = Array.from({ length: 12 }, (_, index) => index + 1);
const hours = Array.from({ length: 24 }, (_, index) => index);
const minutes = Array.from({ length: 60 }, (_, index) => index);

interface InitialFormProps {
  profile: InitialProfile;
  loading: boolean;
  onChange: (profile: InitialProfile) => void;
  onSubmit: () => void;
  onSajuOnly: () => void;
}

interface SelectFieldProps {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  children: ReactNode;
  className?: string;
  icon?: ReactNode;
}

function formatNumber(value: number) {
  return value.toString().padStart(2, "0");
}

function getDayCount(year: number, month: number, calendarType: InitialProfile["birth"]["calendar_type"]) {
  if (calendarType === "lunar") {
    return 30;
  }
  return new Date(year, month, 0).getDate();
}

function SelectField({ label, value, onChange, children, className = "", icon }: SelectFieldProps) {
  return (
    <label className={className}>
      <span className={helperLabelClass}>
        {icon}
        {label}
      </span>
      <span className="relative block">
        <select className={selectClass} value={value} onChange={(event) => onChange(event.target.value)}>
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-stone-400" size={18} aria-hidden />
      </span>
    </label>
  );
}

export function InitialForm({ profile, loading, onChange, onSubmit, onSajuOnly }: InitialFormProps) {
  const currentYear = new Date().getFullYear();
  const years = useMemo(() => {
    const end = Math.min(2100, currentYear);
    return Array.from({ length: end - 1900 + 1 }, (_, index) => end - index);
  }, [currentYear]);
  const days = useMemo(
    () => Array.from({ length: getDayCount(profile.birth.year, profile.birth.month, profile.birth.calendar_type) }, (_, index) => index + 1),
    [profile.birth.calendar_type, profile.birth.month, profile.birth.year],
  );

  function update<K extends keyof InitialProfile>(key: K, value: InitialProfile[K]) {
    onChange({ ...profile, [key]: value });
  }

  function updateBirth<K extends keyof InitialProfile["birth"]>(key: K, value: InitialProfile["birth"][K]) {
    const nextBirth = { ...profile.birth, [key]: value };
    const maxDay = getDayCount(nextBirth.year, nextBirth.month, nextBirth.calendar_type);
    if (nextBirth.day > maxDay) {
      nextBirth.day = maxDay;
    }
    onChange({ ...profile, birth: nextBirth });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-[#eadfce] bg-[#fffdf8] p-4 shadow-soft sm:p-6">
      <section>
        <div className="mb-6">
          <p className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#fff0b9] px-3 py-1.5 text-xs font-black text-[#6e5428]">
            <Sparkles size={14} aria-hidden /> 사주 심리 리딩
          </p>
          <h1 className="text-4xl font-black leading-tight tracking-normal text-ink sm:text-5xl">프로필을 입력해주세요.</h1>
          <p className="mt-3 text-sm font-bold leading-6 text-stone-500">생년월일시와 출생 지역을 기준으로 만세력을 계산합니다.</p>
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
            <span className="relative block">
              <select className={selectClass} value={profile.gender} onChange={(event) => update("gender", event.target.value as InitialProfile["gender"])}>
                <option value="female">여성</option>
                <option value="male">남성</option>
                <option value="other">기타/미입력</option>
              </select>
              <ChevronDown className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-stone-400" size={18} aria-hidden />
            </span>
          </label>
        </div>
      </section>

      <section className="rounded-lg border border-[#f0dfc4] bg-[#fff8e8] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
        <div className="mb-4 flex items-center gap-2 text-sm font-black text-stone-700">
          <CalendarDays size={17} aria-hidden /> 생년월일시
        </div>

        <div className="mb-4 grid grid-cols-2 gap-2 rounded-lg border border-[#eadfce] bg-white p-1">
          {(["solar", "lunar"] as const).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => updateBirth("calendar_type", type)}
              className={`h-11 rounded-md px-3 text-sm font-black transition ${
                profile.birth.calendar_type === type ? "bg-[#73c8b7] text-white shadow-sm" : "text-stone-600 hover:bg-[#f7fbf8]"
              }`}
            >
              {type === "solar" ? "양력" : "음력"}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <SelectField className="sm:col-span-2" label="연도" value={profile.birth.year} onChange={(value) => updateBirth("year", Number(value))}>
            {years.map((year) => (
              <option key={year} value={year}>
                {year}년
              </option>
            ))}
          </SelectField>

          <SelectField label="월" value={profile.birth.month} onChange={(value) => updateBirth("month", Number(value))}>
            {months.map((month) => (
              <option key={month} value={month}>
                {month}월
              </option>
            ))}
          </SelectField>

          <SelectField label="일" value={profile.birth.day} onChange={(value) => updateBirth("day", Number(value))}>
            {days.map((day) => (
              <option key={day} value={day}>
                {day}일
              </option>
            ))}
          </SelectField>

          <SelectField label="시" value={profile.birth.hour} onChange={(value) => updateBirth("hour", Number(value))} icon={<Clock3 size={14} aria-hidden />}>
            {hours.map((hour) => (
              <option key={hour} value={hour}>
                {formatNumber(hour)}시
              </option>
            ))}
          </SelectField>
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <SelectField label="분" value={profile.birth.minute} onChange={(value) => updateBirth("minute", Number(value))}>
            {minutes.map((minute) => (
              <option key={minute} value={minute}>
                {formatNumber(minute)}분
              </option>
            ))}
          </SelectField>

          {profile.birth.calendar_type === "lunar" && (
            <label className="flex h-14 items-center gap-3 rounded-lg border border-[#eadfce] bg-white px-4 text-sm font-black text-stone-700 shadow-[0_8px_24px_rgba(83,64,42,0.06)]">
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

        <details className="mt-4 rounded-lg border border-[#eadfce] bg-white shadow-[0_8px_24px_rgba(83,64,42,0.06)]">
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-black text-stone-700">
            <span className="flex items-center gap-2">
              <MapPin size={16} aria-hidden /> 출생 지역과 태양시
            </span>
            <ChevronDown size={17} aria-hidden />
          </summary>
          <div className="grid gap-3 border-t border-stone-100 p-4 sm:grid-cols-2">
            <label>
              <span className={helperLabelClass}>출생 도시</span>
              <input className={inputClass} value={profile.birth.city} onChange={(event) => updateBirth("city", event.target.value)} />
            </label>
            <label>
              <span className={helperLabelClass}>경도</span>
              <input
                className={inputClass}
                type="number"
                step="0.0001"
                value={profile.birth.longitude ?? ""}
                onChange={(event) => updateBirth("longitude", event.target.value === "" ? null : Number(event.target.value))}
                placeholder="126.9780"
              />
            </label>
            <label className="flex h-14 items-center gap-3 rounded-lg bg-[#f4fbf7] px-4 text-sm font-black text-stone-700 sm:col-span-2">
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
          className={`${inputClass} min-h-36 resize-y py-4 leading-7`}
          value={profile.initial_concern}
          onChange={(event) => update("initial_concern", event.target.value)}
          placeholder="이직을 해야 할지 버텨야 할지 모르겠어요. 지금 회사에 있으면 안정적이지만 계속 답답합니다."
        />
      </label>

      <div className="grid gap-3">
        <button
          type="button"
          onClick={onSajuOnly}
          disabled={loading}
          className="flex h-16 w-full items-center justify-center gap-2 rounded-full bg-honey px-5 text-lg font-black text-[#4d3b21] shadow-[0_14px_30px_rgba(241,190,77,0.34)] transition hover:bg-[#f5c85f] disabled:cursor-not-allowed disabled:opacity-70"
        >
          만세력 보러가기
        </button>
        <button
          type="submit"
          disabled={loading}
          className="flex h-16 w-full items-center justify-center gap-2 rounded-full bg-[#e9ecef] px-5 text-lg font-black text-stone-700 shadow-[0_12px_24px_rgba(82,70,58,0.08)] transition hover:bg-[#dde8e2] disabled:cursor-not-allowed disabled:opacity-70"
        >
          {loading ? <LoaderCircle className="animate-spin" size={20} aria-hidden /> : <Send size={19} aria-hidden />}
          {loading ? "무료 서버 응답 대기 중" : "심리 리딩 질문 받기"}
        </button>
      </div>
    </form>
  );
}

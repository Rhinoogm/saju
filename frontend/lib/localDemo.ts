"use client";

import type { User } from "@supabase/supabase-js";

const LOCAL_DEMO_SESSION_KEY = "saju.localDemo.signedIn";

export const LOCAL_DEMO_BEARER_TOKEN = process.env.NEXT_PUBLIC_LOCAL_DEMO_BEARER_TOKEN ?? "local-demo-token";

export function isLocalDemoMode() {
  return process.env.NEXT_PUBLIC_LOCAL_DEMO === "true";
}

export function getLocalDemoUser(): User {
  return {
    id: "00000000-0000-0000-0000-000000000001",
    aud: "authenticated",
    role: "authenticated",
    email: "demo@local.test",
    app_metadata: { provider: "local-demo", providers: ["local-demo"] },
    user_metadata: { name: "로컬 데모" },
    created_at: "2026-01-01T00:00:00.000Z",
    updated_at: "2026-01-01T00:00:00.000Z",
  } as User;
}

export function hasLocalDemoSession() {
  if (!isLocalDemoMode() || typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(LOCAL_DEMO_SESSION_KEY) === "true";
}

export function getLocalDemoSessionUser() {
  return hasLocalDemoSession() ? getLocalDemoUser() : null;
}

export function signInLocalDemo() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LOCAL_DEMO_SESSION_KEY, "true");
}

export function signOutLocalDemo() {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(LOCAL_DEMO_SESSION_KEY);
}

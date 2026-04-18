import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const adminEnabled = process.env.ENABLE_ADMIN_PROMPTS === "true";

  if (!adminEnabled && request.nextUrl.pathname.startsWith("/admin/prompts")) {
    return new NextResponse("Not Found", {
      status: 404,
      headers: {
        "content-type": "text/plain; charset=utf-8",
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/prompts/:path*"],
};

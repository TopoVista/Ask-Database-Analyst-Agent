const rawApiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
const useDirectApi = process.env.NEXT_PUBLIC_USE_DIRECT_API === "true";

function isSameOriginRelative(apiUrl: string) {
  return apiUrl.startsWith("/");
}

// Default browser traffic to the built-in Next.js proxy so Vercel can forward
// requests server-side to Render without browser CORS issues.
export const API_URL = useDirectApi ? rawApiUrl : isSameOriginRelative(rawApiUrl) ? rawApiUrl : "";

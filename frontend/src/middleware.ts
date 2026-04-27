import { clerkMiddleware } from "@clerk/nextjs/server";

// Keep middleware active so Clerk can hydrate auth state,
// but let the dashboard layout handle route protection.
export default clerkMiddleware(() => {});

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)"],
};

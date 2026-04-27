import { SignIn } from "@clerk/nextjs";
import { AuthFrame } from "@/components/auth/AuthFrame";

export default function SignInPage() {
  return (
    <AuthFrame>
      <SignIn routing="path" path="/sign-in" signUpUrl="/sign-up" afterSignInUrl="/dashboard" />
    </AuthFrame>
  );
}

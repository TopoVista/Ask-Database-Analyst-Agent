import { SignUp } from "@clerk/nextjs";
import { AuthFrame } from "@/components/auth/AuthFrame";

export default function SignUpCatchAllPage() {
  return (
    <AuthFrame>
      <SignUp routing="path" path="/sign-up" signInUrl="/sign-in" afterSignUpUrl="/dashboard" />
    </AuthFrame>
  );
}

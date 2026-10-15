import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { AuthShell } from "./AuthShell";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

/** Target of the activation link in the e-mail: /activate/<uid>/<token> */
export default function Activate() {
  const { uid, token } = useParams();
  const [state, setState] = useState<"working" | "ok" | "error">("working");
  const [message, setMessage] = useState("");
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;       // React StrictMode runs effects twice; the token is single-use
    started.current = true;
    api.post("/auth/users/activation/", { uid, token })
      .then(() => setState("ok"))
      .catch((e) => { setState("error"); setMessage(e instanceof Error ? e.message : "Activation failed"); });
  }, [uid, token]);

  return (
    <AuthShell title="Account activation" subtitle="Confirming your e-mail address.">
      <div className="rounded-lg border bg-card p-6 text-center">
        {state === "working" && <Loader2 className="mx-auto h-10 w-10 animate-spin text-muted-foreground" />}
        {state === "ok" && <><CheckCircle2 className="mx-auto h-12 w-12 text-success" /><p className="mt-3 font-semibold">Your account is active.</p></>}
        {state === "error" && <><XCircle className="mx-auto h-12 w-12 text-destructive" /><p className="mt-3 font-semibold">This link is invalid or already used.</p><p className="mt-1 text-sm text-muted-foreground">{message}</p></>}
      </div>
      <Button asChild size="lg" className="mt-6 w-full"><Link to="/login">Go to sign in</Link></Button>
    </AuthShell>
  );
}

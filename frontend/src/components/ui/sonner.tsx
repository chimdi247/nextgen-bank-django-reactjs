import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      position="top-right"
      richColors
      toastOptions={{ classNames: { toast: "font-sans rounded-lg" } }}
    />
  );
}

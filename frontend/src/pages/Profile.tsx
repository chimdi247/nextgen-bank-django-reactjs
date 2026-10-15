import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { CheckCircle2, Circle, ImagePlus, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { ErrorNote, Field } from "@/components/Field";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, mediaUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useFetch } from "@/lib/hooks";
import { fetchAccounts } from "@/lib/queries";
import { formatErr } from "@/lib/errors";
import type { NextOfKin, Profile as ProfileT } from "@/lib/types";

type FieldDef = { key: string; label: string; type?: "text" | "date" | "number" | "select"; options?: [string, string][]; maxLength?: number; hint?: string; optional?: boolean };

const TITLE: [string, string][] = [["mr", "Mr"], ["mrs", "Mrs"], ["miss", "Miss"]];
const GENDER: [string, string][] = [["male", "Male"], ["female", "Female"]];
const MARITAL: [string, string][] = [["single", "Single"], ["married", "Married"], ["divorced", "Divorced"], ["widowed", "Widowed"], ["separated", "Separated"], ["unknown", "Prefer not to say"]];
const ID_MEANS: [string, string][] = [["national_id", "National ID"], ["passport", "Passport"], ["drivers_license", "Driver's licence"]];
const EMPLOYMENT: [string, string][] = [["employed", "Employed"], ["self_employed", "Self-employed"], ["unemployed", "Unemployed"], ["retired", "Retired"], ["student", "Student"]];

const PERSONAL: FieldDef[] = [
  { key: "title", label: "Title", type: "select", options: TITLE }, { key: "gender", label: "Gender", type: "select", options: GENDER },
  { key: "date_of_birth", label: "Date of birth", type: "date" }, { key: "marital_status", label: "Marital status", type: "select", options: MARITAL },
  { key: "country_of_birth", label: "Country of birth", maxLength: 2, hint: "2-letter code, e.g. KE" }, { key: "place_of_birth", label: "Place of birth", maxLength: 50 },
  { key: "nationality", label: "Nationality", maxLength: 30 }, { key: "phone_number", label: "Phone", hint: "International format, e.g. +254700000000" },
  { key: "address", label: "Address", maxLength: 100 }, { key: "city", label: "City", maxLength: 50 },
  { key: "country", label: "Country", maxLength: 2, hint: "2-letter code, e.g. KE" },
  { key: "means_of_identification", label: "ID type", type: "select", options: ID_MEANS }, { key: "passport_number", label: "Passport number", maxLength: 20, optional: true },
  { key: "id_issue_date", label: "ID issued", type: "date" }, { key: "id_expiry_date", label: "ID expires", type: "date" },
];
const EMPLOY: FieldDef[] = [
  { key: "employment_status", label: "Employment", type: "select", options: EMPLOYMENT }, { key: "employer_name", label: "Employer", maxLength: 50, optional: true },
  { key: "annual_income", label: "Annual income", type: "number" },
];
const ACCOUNT: FieldDef[] = [
  { key: "account_currency", label: "Currency", type: "select", options: [["us_dollar", "US Dollar"], ["pound_sterling", "Pound Sterling"], ["kenya_shilling", "Kenya Shilling"]] },
  { key: "account_type", label: "Account type", type: "select", options: [["current", "Current"], ["savings", "Savings (earns interest)"]] },
];
const PHOTOS = [["photo", "Portrait photo"], ["id_photo", "ID document"], ["signature_photo", "Signature"]] as const;

function renderField(d: FieldDef, value: string, onChange: (v: string) => void) {
  const id = `f-${d.key}`;
  return (
    <Field key={d.key} id={id} label={d.label} hint={d.hint}>
      {d.type === "select" ? (
        <Select id={id} value={value} onChange={(e) => onChange(e.target.value)}>{!value && <option value="">Choose…</option>}{d.options!.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
      ) : (
        <Input id={id} type={d.type ?? "text"} step={d.type === "number" ? "0.01" : undefined} maxLength={d.maxLength} value={value} onChange={(e) => onChange(d.maxLength === 2 ? e.target.value.toUpperCase() : e.target.value)} required={!d.optional} />
      )}
    </Field>
  );
}

function Check({ ok, children }: { ok: boolean; children: React.ReactNode }) {
  return <li className="flex items-center gap-2 text-sm">{ok ? <CheckCircle2 className="h-4 w-4 text-success" /> : <Circle className="h-4 w-4 text-muted-foreground" />}<span className={ok ? "" : "text-muted-foreground"}>{children}</span></li>;
}

export default function Profile() {
  const { user, refreshUser } = useAuth();
  const profile = useFetch(() => api.get<ProfileT>("/profiles/my-profile/"));
  const accounts = useFetch(fetchAccounts);
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [kinOpen, setKinOpen] = useState(false);
  const polling = useRef<ReturnType<typeof setInterval> | null>(null);
  const p = profile.data;

  useEffect(() => { if (p) setForm(Object.fromEntries([...PERSONAL, ...EMPLOY, ...ACCOUNT].map((d) => [d.key, String((p as unknown as Record<string, unknown>)[d.key] ?? "")]))); }, [p]);
  useEffect(() => () => { if (polling.current) clearInterval(polling.current); }, []);

  // photos are processed asynchronously by Celery (and the account is opened when everything is in place): poll for a short while
  const watch = useCallback(() => {
    if (polling.current) clearInterval(polling.current);
    let n = 0;
    polling.current = setInterval(() => {
      n++; void profile.reload(true); void accounts.reload(true);
      if (n >= 12 && polling.current) { clearInterval(polling.current); polling.current = null; }
    }, 2500);
  }, [profile, accounts]);

  const save = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([k, v]) => { if (v !== "") fd.append(k, v); });
      await api.patchForm("/profiles/my-profile/", fd);
      toast.success("Profile saved"); void profile.reload(true); void refreshUser(); watch();
    } catch (err) { setError(formatErr(err)); } finally { setBusy(false); }
  };

  const upload = async (field: string, file: File | undefined) => {
    if (!file) return;
    setUploading(field);
    try {
      const fd = new FormData(); fd.append(field, file);
      ["account_currency", "account_type"].forEach((k) => form[k] && fd.append(k, form[k]));
      await api.patchForm("/profiles/my-profile/", fd);
      toast.success("Upload received", { description: "Processing in the background…" }); watch();
    } catch (err) { toast.error(formatErr(err)); } finally { setUploading(null); }
  };

  const hasPhotos = !!(p?.photo_url && p?.id_photo_url && p?.signature_photo_url);
  const hasKin = (p?.next_of_kin?.length ?? 0) > 0;
  const hasChoice = !!(p?.account_currency && p?.account_type);
  const opened = (accounts.data ?? []).length > 0;

  return (
    <>
      <PageHeader title="Profile & KYC" description="Your details, identity documents and next of kin. Complete them and your account opens automatically." />
      {profile.loading ? <Skeleton className="h-64" /> : (
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2">Account opening {opened && <Badge variant="success">Account opened</Badge>}</CardTitle><CardDescription>An account executive verifies your identity after the account is created.</CardDescription></CardHeader>
            <CardContent><ul className="grid gap-2 sm:grid-cols-2">
              <Check ok={hasPhotos}>Portrait, ID document and signature uploaded</Check>
              <Check ok={hasKin}>At least one next of kin</Check>
              <Check ok={hasChoice}>Account currency and type chosen</Check>
              <Check ok={opened}>Bank account opened</Check>
            </ul>
              <p className="mt-4 rounded-md bg-secondary/70 px-3 py-2 text-xs text-muted-foreground">Your username (needed to confirm withdrawals): <b className="font-mono text-foreground">{user?.username}</b></p></CardContent>
          </Card>

          <form onSubmit={save} className="space-y-6">
            <Card><CardHeader><CardTitle>Personal details</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2">{PERSONAL.map((d) => renderField(d, form[d.key] ?? "", (v) => setForm((f) => ({ ...f, [d.key]: v }))))}</CardContent></Card>
            <Card><CardHeader><CardTitle>Employment</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2">{EMPLOY.map((d) => renderField(d, form[d.key] ?? "", (v) => setForm((f) => ({ ...f, [d.key]: v }))))}</CardContent></Card>
            <Card><CardHeader><CardTitle>Account you want</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2">{ACCOUNT.map((d) => renderField(d, form[d.key] ?? "", (v) => setForm((f) => ({ ...f, [d.key]: v }))))}</CardContent></Card>
            <ErrorNote message={error} />
            <Button type="submit" size="lg" loading={busy}>Save profile</Button>
          </form>

          <Card>
            <CardHeader><CardTitle>Identity documents</CardTitle><CardDescription>JPEG or PNG. They are processed in the background.</CardDescription></CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-3">
              {PHOTOS.map(([field, label]) => {
                const url = mediaUrl((p as unknown as Record<string, string | undefined>)?.[`${field}_url`]);
                return (
                  <label key={field} className="group relative flex aspect-[4/3] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-lg border border-dashed bg-secondary/40 text-center hover:bg-secondary">
                    {url ? <img src={url} alt={label} className="absolute inset-0 h-full w-full object-cover" onError={(e) => ((e.target as HTMLImageElement).style.display = "none")} /> : null}
                    <span className="relative flex flex-col items-center gap-1 rounded-md bg-card/80 px-3 py-2 text-xs font-semibold backdrop-blur">
                      {uploading === field ? "Uploading…" : <><ImagePlus className="h-5 w-5" />{url ? "Replace" : "Upload"} {label.toLowerCase()}</>}
                    </span>
                    <input type="file" accept="image/*" className="sr-only" onChange={(e) => void upload(field, e.target.files?.[0])} />
                  </label>
                );
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0"><div><CardTitle>Next of kin</CardTitle><CardDescription>At least one is required; exactly one can be primary.</CardDescription></div><Button variant="outline" onClick={() => setKinOpen(true)}><Plus />Add</Button></CardHeader>
            <CardContent className="p-0">
              {(p?.next_of_kin ?? []).length === 0 ? <p className="px-5 pb-6 text-sm text-muted-foreground">None added yet.</p> : (
                <ul className="divide-y">{p!.next_of_kin.map((k) => (
                  <li key={k.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{k.first_name} {k.last_name} {k.is_primary && <Badge variant="secondary" className="ml-1">Primary</Badge>}</p><p className="truncate text-xs text-muted-foreground">{k.relationship} · {k.email_address} · {k.phone_number}</p></div>
                    <Button variant="ghost" size="icon" className="text-destructive" aria-label="Remove" onClick={async () => { try { await api.del(`/profiles/my-profile/next-of-kin/${k.id}/`); void profile.reload(true); } catch (e) { toast.error(formatErr(e)); } }}><Trash2 /></Button>
                  </li>))}</ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}
      <KinDialog open={kinOpen} onClose={() => setKinOpen(false)} onSaved={() => { void profile.reload(true); void accounts.reload(true); watch(); }} first={!hasKin} />
    </>
  );
}

function KinDialog({ open, onClose, onSaved, first }: { open: boolean; onClose: () => void; onSaved: () => void; first: boolean }) {
  const blank = { title: "mr", first_name: "", last_name: "", date_of_birth: "", gender: "male", relationship: "", email_address: "", phone_number: "", address: "", city: "", country: "KE" };
  const [k, setK] = useState<Record<string, string>>(blank);
  const [primary, setPrimary] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { if (open) { setK(blank); setPrimary(first); setError(null); } }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setK((p) => ({ ...p, [key]: e.target.value }));
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null);
    try { await api.post<NextOfKin>("/profiles/my-profile/next-of-kin/", { ...k, country: k.country.toUpperCase(), is_primary: primary }); toast.success("Next of kin added"); onSaved(); onClose(); }
    catch (err) { setError(formatErr(err)); } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-xl overflow-y-auto">
        <DialogHeader><DialogTitle>Add next of kin</DialogTitle><DialogDescription>Someone we can contact on your behalf.</DialogDescription></DialogHeader>
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <Field id="k-title" label="Title"><Select id="k-title" value={k.title} onChange={set("title")}>{TITLE.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
          <Field id="k-gender" label="Gender"><Select id="k-gender" value={k.gender} onChange={set("gender")}>{GENDER.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
          <Field id="k-fn" label="First name"><Input id="k-fn" required value={k.first_name} onChange={set("first_name")} /></Field>
          <Field id="k-ln" label="Last name"><Input id="k-ln" required value={k.last_name} onChange={set("last_name")} /></Field>
          <Field id="k-dob" label="Date of birth"><Input id="k-dob" type="date" required value={k.date_of_birth} onChange={set("date_of_birth")} /></Field>
          <Field id="k-rel" label="Relationship"><Input id="k-rel" required value={k.relationship} onChange={set("relationship")} placeholder="Spouse, parent…" /></Field>
          <Field id="k-em" label="Email"><Input id="k-em" type="email" required value={k.email_address} onChange={set("email_address")} /></Field>
          <Field id="k-ph" label="Phone" hint="e.g. +254700000000"><Input id="k-ph" required value={k.phone_number} onChange={set("phone_number")} /></Field>
          <Field id="k-ad" label="Address"><Input id="k-ad" required value={k.address} onChange={set("address")} /></Field>
          <Field id="k-ci" label="City"><Input id="k-ci" required value={k.city} onChange={set("city")} /></Field>
          <Field id="k-co" label="Country" hint="2-letter code"><Input id="k-co" required maxLength={2} value={k.country} onChange={set("country")} /></Field>
          <label className="flex items-center gap-2 self-end pb-2 text-sm"><input type="checkbox" checked={primary} onChange={(e) => setPrimary(e.target.checked)} />Primary contact</label>
          <div className="sm:col-span-2"><ErrorNote message={error} /></div>
          <DialogFooter className="sm:col-span-2"><Button type="button" variant="outline" onClick={onClose} disabled={busy}>Cancel</Button><Button type="submit" loading={busy}>Add next of kin</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

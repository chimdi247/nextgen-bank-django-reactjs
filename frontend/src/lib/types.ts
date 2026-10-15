export type Role = "customer" | "teller" | "account_executive" | "branch_manager";
export type Currency = "us_dollar" | "pound_sterling" | "kenya_shilling";
export type AccountType = "current" | "savings";

export interface User {
  id: string;
  email: string;
  username: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  full_name: string;
  id_no: number;
  role: Role;
  is_staff: boolean;
  is_superuser: boolean;
  account_status: "active" | "locked";
  security_question: string;
  date_joined: string;
}

export interface Account {
  id: string;
  account_number: string;
  account_balance: string;
  currency: Currency;
  account_type: AccountType;
  account_status: string;
  is_primary: boolean;
  kyc_submitted: boolean;
  kyc_verified: boolean;
  fully_activated: boolean;
  annual_interest_rate: string;
  created_at: string;
}

export interface PendingAccount {
  id: string;
  account_number: string;
  currency: Currency;
  account_type: AccountType;
  account_status: string;
  kyc_submitted: boolean;
  kyc_verified: boolean;
  fully_activated: boolean;
  verification_notes: string;
  created_at: string;
  holder_name: string;
  holder_email: string;
  holder_id_no: number;
  profile_complete: boolean;
  photo_url: string | null;
  id_photo_url: string | null;
  signature_photo_url: string | null;
}

export interface Transaction {
  id: string;
  amount: string;
  description: string | null;
  status: "pending" | "completed" | "failed";
  transaction_type: "deposit" | "withdrawal" | "transfer" | "interest";
  created_at: string;
  sender: string | null;
  receiver: string | null;
  sender_account: string | null;
  receiver_account: string | null;
}

export interface Page<T> { count: number; next: string | null; previous: string | null; results: T[] }

export interface NextOfKin {
  id: string;
  title: string;
  first_name: string;
  last_name: string;
  other_names?: string | null;
  date_of_birth: string;
  gender: string;
  relationship: string;
  email_address: string;
  phone_number: string;
  address: string;
  city: string;
  country: string;
  is_primary: boolean;
}

export interface Profile {
  id: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  username: string;
  id_no: number;
  email: string;
  full_name: string;
  title: string;
  gender: string;
  date_of_birth: string;
  country_of_birth: string;
  place_of_birth: string;
  marital_status: string;
  means_of_identification: string;
  id_issue_date: string;
  id_expiry_date: string;
  passport_number?: string | null;
  nationality: string;
  phone_number: string;
  address: string;
  city: string;
  country: string;
  employment_status: string;
  employer_name?: string | null;
  annual_income: string;
  next_of_kin: NextOfKin[];
  photo_url?: string | null;
  id_photo_url?: string | null;
  signature_photo_url?: string | null;
  account_currency?: Currency | null;
  account_type?: AccountType | null;
}

export interface VirtualCard {
  id: string;
  card_number: string;
  expiry_date: string;
  cvv: string;
  balance: string;
  status: string;
}

export interface BankStats {
  customers: number;
  locked_users: number;
  new_customers_7d: number;
  accounts_total: number;
  accounts_pending_kyc: number;
  balances: { currency: Currency; total: string; accounts: number }[];
  transactions_24h: { type: string; count: number; amount: string }[];
  generated_at: string;
}

export interface LookupResult {
  account_number: string;
  holder_name: string;
  currency: Currency;
  account_type: AccountType;
  is_active: boolean;
}

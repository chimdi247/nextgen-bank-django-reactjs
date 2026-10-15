import { api, asList } from "./api";
import type { Account, Page, Transaction, VirtualCard } from "./types";

export const fetchAccounts = () => api.get<unknown>("/accounts/").then((v) => asList<Account>(v));
export const fetchTransactions = (params: Record<string, string | number | undefined>) => api.get<Page<Transaction>>("/accounts/transactions/", params);
export const fetchCards = () => api.get<unknown>("/cards/virtual-cards/").then((v) => asList<VirtualCard>(v));

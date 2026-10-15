/** One readable string for any thrown value (ApiError carries the server message already). */
export function formatErr(e: unknown): string {
  return e instanceof Error ? e.message : "Something went wrong";
}

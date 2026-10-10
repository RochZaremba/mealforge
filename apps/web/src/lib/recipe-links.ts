export type RecipeLinkSummary = {
  id: string;
  household_id: string;
  user_title: string;
  source_url: string;
  host: string;
  source_id: string | null;
  source_registry_checked_at: string;
  status: "link_only";
  version: 1;
  planner_eligible: false;
  license: null;
  automatic_fetch_enabled: false;
  nutrition_status: "unknown";
  allergen_status: "unknown";
  created_at: string;
};
export type RecipeLink = RecipeLinkSummary & {
  canonical_url: string;
  own_note: string | null;
  own_contribution_attestation: "i_am_author_of_label_and_note";
  actor_user_id: string;
};
export type RecipeLinkPage = {
  recipe_links: RecipeLinkSummary[];
  next_cursor: string | null;
};
// Only a server-confirmed opening URL is eligible for the explicit external anchor.
// This is a rendering guard, not a replacement for the backend bookmark policy.
export function safeOpeningUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password &&
      (!url.port || url.port === "443") && !/[\u0000-\u0020\u007f\\]/.test(value)
      ? value : null;
  } catch { return null; }
}

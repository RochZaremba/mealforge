export type RecipeWarning = { code: string; message: string };
export type Ingredient = {
  name: string;
  amount: string | null;
  unit: "g" | "ml" | "piece" | "unknown";
  weight_state: "raw" | "cooked" | "as_packaged" | "unknown";
};
export type RecipeSummary = {
  id: string;
  household_id: string;
  version: number;
  title: string;
  created_at: string;
  status: "draft_requires_review";
  planner_eligible: false;
  warnings: RecipeWarning[];
};
export type OriginalOrigin = {
  source_id: string;
  author: string;
  license: string;
  license_scope: string;
  attribution: string;
};
export type Recipe = RecipeSummary & {
  version_id: string;
  instructions: string[];
  ingredients: Ingredient[];
  nutrients: { kcal: null; protein_g: null; carbs_g: null; fat_g: null; fiber_g: null };
  allergen_status: "unknown";
  yield_mass_g: null;
  yield_basis: "unknown_until_weighed";
  servings: number | null;
  servings_basis: "unknown" | "intentional_recipe_design";
  prep_time_minutes: null;
  cook_time_minutes: null;
  storage_method: null;
  storage_validation_ref: null;
  prices: null;
  provenance: {
    source_mode: "user_authored";
    source_id: "private_user_content" | "original_fixture";
    author: string;
    rights_mode: "private_user_content";
    license: string | null;
    license_scope: string | null;
    attribution: string | null;
    rights_attestation: "i_am_author" | null;
    source_version_id: string | null;
    original_origin: OriginalOrigin | null;
  };
};
export type RecipePage = { recipes: RecipeSummary[]; next_cursor: string | null };
export type RecipeHistory = { history: Recipe[]; next_before_version: number | null };
export const unitLabels = { g: "g", ml: "ml", piece: "szt.", unknown: "Nieznana" };
export const stateLabels = { raw: "Surowy", cooked: "Po ugotowaniu", as_packaged: "Jak w opakowaniu", unknown: "Nieznany" };

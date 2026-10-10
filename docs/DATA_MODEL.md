# Konceptualny model danych i inwarianty

Kontrakty poniżej opisują minimalny schemat logiczny, również dla przyszłych fal. SQLAlchemy + Alembic są źródłem wdrożonego DDL, `contracts/openapi.yaml` jest generowane z aktualnego API.

## Identity i żywienie

- `users(id, email unique, display_name, created_at)`
- `households(id, name, owner_id, timezone, currency, created_at)`
- `household_members(id, household_id, user_id?, display_name, role, is_guest, active)`; `role` owner/editor/viewer; guest może być profilem bez loginu.
- `nutrition_profiles(id, member_id, kcal_target, protein_target_g, carbs_target_g, fat_target_g, activity, goal_type, valid_from, valid_to)`; profile versioned.
- `member_restrictions(id, member_id, ingredient_id?, allergen_code?, restriction_type, severity, note)`.
- `meal_slot_presets(id, household_id, slot_name, ordering, default_share, default_time)`; standardowych 5, włączanie per member/day.

## Recipes / provenance / nutrition

- `ingredients(id, canonical_name, food_group, default_unit, allergens, raw_cooked_state)`.
- `ingredient_synonyms(id, ingredient_id, language, alias)`.
- `food_nutrient_records(id, ingredient_id, source_system, source_id, raw_cooked_state, basis_g, calories_kcal?, protein_g?, fat_g?, carbs_g?, fiber_g?, saturated_fat_g?, sodium_mg?, quality, retrieved_at, license)`.
- `recipes(id, household_id?, title, visibility, validation_status, primary_source_id?, created_by_member_id?)`.
- `recipe_versions(id, recipe_id, version, yield_g?, servings?, prep_time_min?, cook_time_min?, instructions_rights?, frozen_nutrition_json?, validated_at?)`.
- `recipe_ingredients(id, recipe_version_id, ingredient_id?, literal_name, amount?, unit, normalized_g?, weight_state, match_confidence, parse_status)`.
- `recipe_sources(id, recipe_id?, source_domain, canonical_url, author?, license_name?, attribution?, rights_mode, fetch_permission_ref?, fetched_at?, fingerprint?, source_status)`.
- `recipe_ratings(id, household_member_id, recipe_id, rating, feedback, created_at)`.

## Plans / events

- `meal_plans(id, household_id, start_date, end_date, status, version, objective_snapshot_json)`.
- `meal_slots(id, plan_id, day, slot_preset_id, excluded, locked, repeat_template_key?, event_id?)`.
- `planned_meals(id, meal_slot_id, recipe_version_id?, planned_batch_id?, external_meal, prep_session_id?, version)`.
- `planned_portions(id, planned_meal_id, member_id, portion_mass_g?, extras_json, nutrient_snapshot_json, portion_status)`.
- `calendar_events(id, household_id, start_time, end_time, event_type, participant_scope, meal_scope, guest_count, notes, version)`.
- `plan_changes(id, plan_id, base_version, new_version, actor_member_id, op_type, before_json, after_json, timestamp)`.

## Batching / storage / inventory

- `containers(id, household_id, label, volume_ml?, tare_g?, freezer_safe, dishwasher_safe)`.
- `cooking_sessions(id, household_id, scheduled_at, actual_started_at?, status, equipment_json)`.
- `meal_batches(id, household_id, recipe_version_id, session_id, made_at?, yield_g?, nutrition_snapshot_json, storage_method, storage_validation_ref?, status)`.
- `batch_portions(id, batch_id, net_weight_g, container_id?, storage_location_id?, reserved_for_planned_portion_id?, best_before?, status, label_code unique)`.
- `inventory_locations(id, household_id, location_kind, name)`.
- `inventory_lots(id, household_id, ingredient_id?, product_barcode?, batch_portion_id?, location_id, unit, received_at, opened_at?, expires_at?, current_quantity, reserved_quantity, row_version)`.
- `inventory_transactions(id, household_id, lot_id, actor_id, operation, quantity_delta, reservation_delta, idempotency_key, related_entity_type?, related_entity_id?, created_at)`.
- `inventory_reservations(id, lot_id, plan_version_id?, batch_id?, quantity, status, version)`.

## Shopping / feedback

- `shopping_lists(id, household_id, for_plan_id, plan_version, status, updated_at)`.
- `shopping_items(id, list_id, ingredient_id, amount_g, units, pack_size?, price_estimate?, price_source?, checked_by?, received_lot_id?)`.
- `food_prices(id, source, product_ref, price, currency, pack_quantity, observed_at)`.
- `preference_feedback(id, member_id, recipe_id, kind, rating?, reason_code?, created_at)`.
- `audit_events(id, household_id, actor_id, action, entity_type, entity_id, version_before?, version_after?, request_id, created_at)`.

## Inwarianty blokujące release

- W każdej tabeli `household_id` jest egzekwowany przez service layer; obcy ID w URL nie upoważnia do odczytu/mutacji.
- `InventoryLot.available = current_quantity - reserved_quantity >= 0` i nigdy `current_quantity < 0` (dla niezarejestrowanego odpadu oddzielna operacja).
- `BatchPortion` wskazana jako consumed nie może nadal pozostawać reserved dla innego planu.
- Atomic commit: zmiana planu + różnice rezerwacji + shopping snapshot tworzą jeden spójny version id; w razie błędu rollback.
- Cena/gramy oraz skwantowane makro liczone jako Decimal lub int scaled units; brak wartości jest `null`, nie zero.
- `RecipeVersion` immutable po `validated_at`, wersjonowanie zmian receptury zamiast nadpisywania historycznych wyników.
- Gdy `recipe_sources.rights_mode=link_only`, dozwolone jest jedynie przechowywanie URL i użytkownikowskich pól pomocniczych; żadnych skopiowanych instrukcji/zdjęć w publicznym katalogu.
- `verified_canned_food` wymaga `storage_validation_ref` do zatwierdzonego przepisu i procesu; nie odziedziczy go custom recipe automatycznie.
- Wszystkie mutacje inventory mają unikalne `(household_id, idempotency_key)`; duplikat nie może zmienić stanów po raz drugi.

## Stany planów

`draft -> validated -> committed -> archived`. Jedynie committed plan rezerwuje zapasy. Przepis z linku = metadata/favorite, ale nie automated recipe candidate bez danych.

## Stany importu

`link_only` → (ręczne dane użytkownika) `draft_requires_review` → `normalized` → `nutrition_verified` → `validated`; błędy/licencje: `quarantined` / `rights_denied`.

## W01-A schema implementation (PR #2 merged; gates passed)
Migration0002 adds users/password_hash (Argon2id), sessions/token_hash only with expiry/revocation, auth_rate_buckets with HMAC keys and finite windows; households with slot_revision; household_members with target_revision, composite id/household uniqueness and guest-no-login check; nutrition_profiles immutable version rows, composite household/member FK and Numeric(9,3) nullable targets; meal_slot_presets active rows with local time, nullable exact share, repeat_weekly; audit_events metadata only; idempotency_records actor/scope/key with fingerprint and private JSON result.

Transactions lock the authenticated session for revocation consistency, member for target expected_version and household for slot revision. Idempotency uses a transaction-scoped PostgreSQL advisory lock; replay reauthorizes membership. Profile valid_from is a local date and cannot be future in A; history stays immutable. Guests/unlinked residents never authorize an account. Recipe/inventory/planning tables above remain requirements for future slices.

## W01-B schema (PR #3 merged; gates passed)

Migration0003 adds `household_members.access_enabled` (default true) and `access_version` (default 0), separately from participation `active` and nutrition `target_revision`. Account access changes do not delete or rewrite nutrition profiles. Authorization and household listing require the current active, access-enabled membership and matching authenticated user.

`household_invitations` stores UUID, household, creator, editor/viewer role, optional existing member scoped with a composite household FK, private random nonce, unique SHA256 token hash, issued/expiry timestamps, accepted-at/by, revoked-at and version. Raw codes are derived with a domain-separated HMAC and never stored in idempotency JSON or audit metadata. The owner identity is protected by `households.owner_user_id`, not a mutable role string.

Acceptance, access changes and private household operations serialize on the same household lock before invitation/member locks. Locked ORM reloads must refresh preloaded objects to avoid stale role or invitation status after concurrent revocation. Acceptance atomically links a resident, consumes the invitation, writes metadata-only audit and records idempotency. Session revocation and current authorization checks also apply on replay. Tests must prove single use across distinct accounts and preservation of the existing resident profile.

## W01-C schema (integration and verification pending)

Migration0004 adds `households.source` with `user_created` for existing households and explicit `demo_seed` only for opt-in demo creation. Recipe identities in `recipes` carry UUID, household, current revision and timestamp. `recipe_versions` store scoped recipe UUID, positive version, acting user, timestamp and a Pydantic-validated JSONB snapshot. Snapshots preserve exact Decimal strings and unknown values; they do not claim normalized ingredient identities or verified nutrition. The deployed C schema is deliberately narrower than the future normalized recipe model above.

Recipe version `(recipe_id, household_id, version)` is unique. A composite FK from the recipe's `(id, household_id, current_version)` to that key is `DEFERRABLE INITIALLY DEFERRED`, allowing atomic identity/version insertion while preventing an invalid pointer at transaction commit. Version rows refer back to the household-scoped identity; PostgreSQL guards reject version UPDATE and DELETE, including drafts. Updates append snapshots and advance the current revision under household lock with expected-version checking. There is no delete/archive endpoint in C.

Recipe mutations write metadata-only audit and idempotency records in the same transaction; retries store references, reauthorize current membership and return the original committed version, even after later edits. Demo creation uses global authenticated-user scope, then current owner authorization on replay. All demo profiles, five slots and three recipe versions commit together. Normal household creation and startup never seed targets or recipes. Nutrition profile source already supports the explicit `demo_seed` value; existing user targets/history remain unchanged.

Trusted original provenance comes exclusively from the packaged, bounded, audited fixture. Edited snapshots retain finite original attribution and a source-version reference, without copying an unbounded chain of historical snapshots. New user contributions have private rights with unknown license. No external recipe source adapter or fetch job is introduced.

# Example: Change Existing Project

**User:** Add team workspaces to this existing single-user app.

**Correct route:** Change / Deep if the app contains private user data.

**Inspect first:** Current identity model, ownership columns, authorization tests, sharing behavior, database schema, and migration tooling.

**Upstream decision:** Is a resource owned by exactly one workspace, or may it be shared across workspaces?

**Recommendation:**

> **Recommendation:** Use exactly one owning workspace per resource in v1 and handle sharing as a later explicit capability. This keeps authorization and migration understandable. Choose cross-workspace sharing now only if it is required by a named workflow that cannot be represented otherwise.

**Required output:** AS-IS/TO-BE, ownership migration, preserved single-user behavior, authorization regression tests, staged rollout, and rollback.

**Bad behavior:** Ask which framework the app uses before inspecting the repository.

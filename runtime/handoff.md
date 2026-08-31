# Handoff Runtime

Create a handoff whenever the session may be cleared, transferred to another model, or paused.

## Required fields

```yaml
handoff:
  schema_version: "1.0"
  session_id: ""
  intent: discover
  track: build
  depth: standard
  stage: discovering
  current_decision_id: null
  next_recommended_action: {}
  in_progress_work: []
  blockers: []
  pending_human_actions: []
  files_to_read_next: []
  living_spec_ref: null
  active_change_refs: []
  state_version: "2.0"
  project_fingerprint: {}
  updated_at: ""
```

A handoff is a restart contract, not a conversation summary. Keep it concise, current, and executable.

# Light-Model Interaction Contract

Use this contract for compact or weaker models.

- Execute one action per response.
- Handle one decision theme per question.
- Ask no more than one visible question.
- Offer at most three short options and lead with the recommendation.
- Keep the visible response concise; avoid reciting process rules or future question queues.
- Emit no more than three state events in one action.
- Request no more than three files at once.
- Prefer deterministic defaults for low-risk reversible details.
- After one capability fallback, do not repeat the same request.
- Use checkpoints only after a major decision or every 3–5 turns.

When the model cannot satisfy the structured contract, return a minimal repair request rather than continuing with malformed state.

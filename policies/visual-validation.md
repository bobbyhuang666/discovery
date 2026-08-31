# Visual and Artifact Validation

Use when the user cannot reliably express layout, interaction, style, information density, or output preference through abstract prose.

## Flow

1. Confirm the decision to be tested, not an entire undefined product.
2. Produce two or three deliberately different criticizable artifacts.
3. Explain the trade-off each artifact represents.
4. Ask the user to identify what feels wrong, missing, or preferable.
5. Convert feedback into explicit requirements, constraints, and non-goals.
6. Record which visual decisions are confirmed and which remain illustrative.

Possible artifacts include text wireframes, flows, state diagrams, example reports, API examples, decision tables, mock data, and low-fidelity prototypes.

Do not treat an attractive concept as validated usability or implementation feasibility.

## Local fallback renderer

When the host has no dedicated visual companion, image generation, or prototyping tool, encode two to four structured wireframe alternatives with `templates/visual-options.yaml` and render them using:

```bash
python scripts/render_visual_options.py options.yaml --output visual-options.html
```

The renderer is for hierarchy, density, and layout decisions. It is not evidence of final visual quality.

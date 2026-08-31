# Capability Negotiation and Graceful Fallback

Capabilities are facts about the current runtime, not questions to repeat.

## Negotiate once

At the start of a task, record whether the runtime can use:

- filesystem or attachments;
- code search;
- command execution;
- web research;
- visual rendering;
- durable persistence.

Do not promise inspection when the capability is absent.

## Missing workspace access

Explain the limitation once, then offer no more than three concrete paths:

1. upload or attach the relevant artifact;
2. paste the smallest relevant section;
3. continue under explicit assumptions and list what remains unverified.

If the user rejects all three, do not ask for the same file again. Continue only where safe or mark the task blocked.

## Missing research or visual tools

Use a text comparison, local HTML sketch, or explicit research request only when the available capabilities support it. Otherwise defer the action and preserve the unresolved decision.

## Evidence discipline

An unavailable tool does not convert an inspectable fact into a user preference. Mark it `unverified_due_to_capability`, not confirmed.

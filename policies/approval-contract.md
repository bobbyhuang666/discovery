# Approval Contract Policy

## Purpose

Prevent implementation from outrunning shared understanding while avoiding a heavyweight approval ceremony for every tiny reversible change.

## Approval levels

| Level | Use when | Required approval |
|---|---|---|
| none | low-impact, reversible default explicitly authorized | no additional gate |
| checkpoint | standard feature or material workflow decision | user confirms concise design/spec checkpoint |
| formal | safety, money, sensitive data, migration, contract, many stakeholders, or hard-to-reverse architecture | named decision owner approves durable artifact |

## Gate behavior

Before implementation or implementation planning:

1. identify the required approval level;
2. present the smallest artifact that makes the decision reviewable;
3. run spec self-review and relevant validators;
4. request approval from the correct authority;
5. record approver, scope, timestamp, and conditions;
6. do not treat silence as approval.

A Quick task must still have shared understanding, but its approval artifact may be only a short implementation brief.

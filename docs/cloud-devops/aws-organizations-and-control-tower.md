---
title: "AWS Organizations & Control Tower"
---

# AWS Organizations & Control Tower

[AWS Accounts & IAM](aws-accounts-and-iam.md#policy-evaluation-logic)
already covers how an SCP fits into policy evaluation inside a single
account. This page covers the service that SCP actually belongs to —
managing many accounts as one organization — and the service built on
top of it that automates setting that up correctly.

## AWS Organizations

Central management for multiple AWS accounts: one **management
account**, any number of **member accounts**, consolidated billing, and
org-wide guardrails.

- **Organizational Units (OUs)** — group accounts into a hierarchy (e.g.
  `Production`, `Sandbox`, `Security`) so a policy applies to every
  account in that group at once, instead of being attached account by
  account.
- **Consolidated billing** — one bill for the whole organization, and
  volume discounts/Savings Plans/Reserved Instance pricing tiers combine
  across every member account's usage, not per account.
- **Tag policies** and **backup policies** — the same OU-based
  "define once, apply to the whole group" model, applied to tagging
  standards and AWS Backup plans instead of permissions.

### SCPs set a ceiling — they never grant anything

This is the single most tested fact about Organizations, and it's easy
to get backwards:

!!! danger "An SCP allowing an action grants nothing by itself"

    A Service Control Policy defines the **maximum** available
    permissions for every account/OU it's attached to — it still takes
    an IAM identity policy inside that account to actually grant
    anything. The default SCP (`FullAWSAccess`) allows everything,
    which is why attaching one more permissive SCP never changes
    anything on its own. What SCPs are actually used for is **explicit
    deny** — "no account in the Sandbox OU may ever disable
    CloudTrail," enforced organization-wide regardless of what any
    account's own IAM policies say. This is exactly the ceiling
    behavior already covered in
    [policy evaluation logic](aws-accounts-and-iam.md#policy-evaluation-logic) —
    an SCP that doesn't allow an action means the action is denied no
    matter what the account's own identity policies say, the same way a
    permission boundary caps a single role.

## Control Tower

Control Tower doesn't replace Organizations — it automates setting up a
secure multi-account **landing zone** on top of it, instead of hand-building
the OU structure, SCPs, and logging account yourself.

- **Guardrails** — pre-built rules applied across accounts, in two
  flavors:
    - *Preventive* guardrails are implemented as SCPs — they stop an
      action from happening at all (e.g. "prevent disabling CloudTrail").
    - *Detective* guardrails are implemented as AWS Config rules — they
      flag a resource that's already out of compliance, rather than
      blocking the action that created it (covered in
      [Security & Compliance Services](aws-security-and-compliance-services.md#aws-config-resource-configuration-compliance)).
- **Account Factory** — self-service provisioning of new accounts that
  are already compliant with the landing zone's guardrails from the
  moment they're created, instead of a new account starting with no
  guardrails until someone remembers to apply them.

!!! success "The exam signal"

    "Quickly set up a secure, compliant multi-account environment with
    minimal operational overhead" almost always points to **Control
    Tower**, not hand-rolling Organizations + SCPs + a logging account
    from scratch — the whole value proposition is not doing that by
    hand.

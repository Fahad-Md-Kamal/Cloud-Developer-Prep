---
title: "Encryption, Secrets & Identity Federation"
---

# Encryption, Secrets & Identity Federation

[AWS Accounts & IAM](aws-accounts-and-iam.md) covers identity for people and
AWS services — users, roles, policies, STS. This page covers three
services the exam expects alongside that: protecting the encryption
*keys* (KMS), protecting the secret *values* those keys encrypt (Secrets
Manager / Parameter Store), and identity for an application's own
end users rather than AWS principals (Cognito).

## KMS: Keys, Not the Secrets Themselves

KMS manages **encryption keys** — it doesn't store application secrets
itself. Secrets Manager and Parameter Store (below) store the actual
secret values, and typically use a KMS key under the hood to encrypt
them at rest. Mixing these two up is a common exam trap.

|  | AWS managed key (`aws/s3`, `aws/rds`, …) | Customer managed key (CMK) |
|---|---|---|
| Who controls the key policy | AWS | You |
| Rotation | Automatic, fixed schedule, not configurable | Automatic (opt-in, annual) or manual, your choice |
| Can be disabled / scheduled for deletion | No | Yes |
| Cost | Free | Monthly fee per key + per-API-call cost |
| Use when | Good enough default, no cross-account sharing needed | Need to share the key across accounts, control rotation, or audit key usage independently |

### Key policies work the same AND logic as S3

A **key policy** is the resource-based policy attached directly to the
key — separate from any IAM identity policy granting `kms:*` actions.
Both must allow the action, exactly the same "resource policy AND
identity policy" logic already covered for
[cross-account access](aws-accounts-and-iam.md#identity-based-vs-resource-based-policies).
Granting `kms:Decrypt` in an IAM policy with no matching key policy still
results in `AccessDenied` — the single most common real-world KMS
mistake.

### Envelope Encryption — Why KMS Doesn't Encrypt Your Data Directly

KMS has a small payload limit (4 KB) on its own `Encrypt` API — it's not
built to encrypt a 2 GB file directly. Envelope encryption solves this:

1. Call `GenerateDataKey` — KMS returns a plaintext data key *and* that
   same key encrypted under your CMK.
2. Encrypt your actual data locally, in memory, using the plaintext data
   key — as much data as you want, at memory speed, no further KMS calls.
3. Discard the plaintext data key. Store the encrypted data key alongside
   the encrypted data.
4. To decrypt later: send the encrypted data key back to KMS
   (`Decrypt`), get the plaintext data key back, decrypt the data
   locally.

!!! note "This is what S3/EBS/RDS encryption is already doing for you"

    Every AWS service with "encrypt with a KMS key" as a checkbox is
    running exactly this envelope-encryption flow internally — the
    checkbox just hides steps 1–4. Understanding the flow is what lets
    you reason about exam questions on KMS grants, cross-account key
    sharing, and why a key's region matters (KMS keys are regional,
    never span regions, unlike IAM).

## Secrets Manager vs Parameter Store

Both store a value and retrieve it by name instead of hardcoding it.
The exam tests the distinction constantly.

|  | Secrets Manager | Systems Manager Parameter Store |
|---|---|---|
| Cost | Paid — per secret per month, plus API calls | Standard tier: free. Advanced tier: paid |
| Automatic rotation | Built-in, one click for RDS/Aurora/Redshift/DocumentDB (runs a Lambda AWS manages) | No built-in rotation — you'd wire up EventBridge + your own Lambda |
| Max value size | 64 KB | 4 KB (standard), 8 KB (advanced) |
| Encryption | Always encrypted (KMS) | Only if stored as `SecureString`; plain `String`/`StringList` are not encrypted |
| Versioning | Yes | Yes |

- Exam phrase **"needs automatic credential rotation"** → Secrets
  Manager.
- Exam phrase **"cost-effective," "simple config value," "feature
  flag"** → Parameter Store.
- Both integrate the same way into ECS task definitions and Lambda
  environment variables — the choice is about rotation and cost, not
  capability.

## Cognito: Identity for Your Application's Own Users

IAM identities are for *AWS principals* — the people and services
operating your AWS account. Cognito identities are for *your
application's end users* — the people signing up for your mobile app.
These solve different problems; the exam leans on this distinction hard.

`User Pools`
:   A user directory: sign-up, sign-in, MFA, password policies, a
    hosted login UI, and OAuth2/OIDC support. A successful login
    returns JWT tokens (ID, access, refresh) your app verifies — this
    is authentication.

`Identity Pools (Federated Identities)`
:   Exchanges a token — from a User Pool, or an external provider like
    Google/Facebook/SAML — for **temporary AWS credentials** via STS.
    This is what actually lets your app call S3 or DynamoDB directly
    from a mobile client without a backend proxying every request.

The typical pairing: a User Pool authenticates the user and issues a
token, then an Identity Pool trades that token for a temporary IAM role
via STS — the same `sts:AssumeRole`-issued, short-lived credential
mechanism already covered for
[AWS service roles](aws-accounts-and-iam.md#principals-users-groups-and-roles),
just handed to an end user's device instead of an EC2 instance or Lambda
function.

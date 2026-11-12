# Speedtest Tracker

Runs scheduled internet speed tests and graphs the history. UI: `https://speedtest-tracker.k3s-node.home`. Manifests: [`apps/speedtest-tracker`](../apps/speedtest-tracker).

It is an independent open-source project (not made by Ookla). It drives Ookla's official Speedtest CLI, so the tests run against speedtest.net servers.

## Required secret (before the pod can start)

The app needs a Laravel `APP_KEY`. Seal it as `speedtest-tracker` in namespace `speedtest-tracker`, key `APP_KEY`, and save it as `apps/speedtest-tracker/secret.sealed.yaml` ([secrets.md](secrets.md)).

Generate a value on your PC (PowerShell):

```powershell
$b = New-Object byte[] 32; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b); "base64:" + [Convert]::ToBase64String($b)
```

Paste the output into the sealed-secrets web UI; do not save it to disk. Until the SealedSecret exists, the pod sits in `CreateContainerConfigError` and the Fleet bundle shows not ready.

## First run

Default login is `admin@example.com` / `password`. Change both immediately (profile page). The schedule is `SPEEDTEST_SCHEDULE` in `deployment.yaml` (default every 6 hours). Each test uses real bandwidth, so watch the frequency on a metered connection. Timezone is `America/Denver`.

Data (SQLite, history) is on `local-path` with **no backups**.

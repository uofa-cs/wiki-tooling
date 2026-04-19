# Content repo setup

These files and steps live in the **content repo** (`uofa-cs/uofa-cs-wiki`), not here. Copy them over, then do the PAT setup below.

## 1. Copy the workflow
Copy `.github/workflows/notify-build.yml` from this folder into the **root** of `uofa-cs/uofa-cs-wiki` at the same path.

## 2. Create a PAT
On a user/org account that has **write access to `uofa-cs/wiki-tooling`**:

- Go to https://github.com/settings/personal-access-tokens/new (fine-grained token)
- **Resource owner**: `uofa-cs`
- **Repository access**: only `uofa-cs/wiki-tooling`
- **Permissions** → Repository permissions → **Contents: Read and write** (required for `repository_dispatch`)
- Copy the token.

Classic PAT alternative: a classic token with the `repo` scope also works if fine-grained tokens aren't available for the org.

## 3. Add the secret to the content repo
In `uofa-cs/uofa-cs-wiki` → Settings → Secrets and variables → Actions → New repository secret:

- **Name**: `WIKI_TOOLING_DISPATCH_TOKEN`
- **Value**: the PAT from step 2

## 4. Verify
Push any commit to `uofa-cs/uofa-cs-wiki` `main`. You should see:

1. `Notify Build Repo` workflow run in the content repo.
2. `Deploy Wiki Site` workflow run in this repo (triggered by `repository_dispatch`).

The 10-minute cron stays as a safety net.

# GeoTask Core Public Release Runbook

**Status**: DRAFT — requires human approval before execution
**Date**: 2026-07-21

---

## Pre-Release Checklist

### 1. Legal/IP Approval (BLOCKING — PENDING HUMAN REVIEW)
- [ ] Company open-source approval obtained
- [ ] Copyright ownership confirmed
- [ ] Patent/public-disclosure boundary confirmed
- [ ] License (MIT) approved
- [ ] Third-party dependency review completed

### 2. Manual File Review (BLOCKING — PENDING HUMAN REVIEW)
- [ ] `docs/reports/public_file_human_review.md` reviewed and signed
- [ ] No internal names, paths, or credentials in any public file
- [ ] README reviewed for appropriate language
- [ ] CONTRIBUTING.md and SECURITY.md reviewed

### 3. Technical Verification (COMPLETED)
- [x] Repository tests: 621 passed, 1 skipped
- [x] Public export: 89 files, 528.9 KB, scan 0 findings
- [x] Exported tests: 204 passed
- [x] Build: wheel + sdist OK
- [x] Wheel audit: 0 forbidden entries
- [x] Clean install: import path confirmed (site-packages)
- [x] CLI smoke: validate + run OK

---

## Release Steps (DO NOT AUTO-EXECUTE)

### Step 1: Create Public Repository
```bash
# On Gitee/GitHub (human executes):
# 1. Create new repository "GeoTask" with MIT license
# 2. Do NOT initialize with README
# 3. Set to PRIVATE initially
```

### Step 2: Initialize and Push Export
```bash
# Run from the clean export directory:
cd ../geotask-core-public-final
git init
git add -A
git commit -m "GeoTask Core v0.1.0 — initial public release"
git remote add origin <PUBLIC_REPO_URL>
# DO NOT PUSH until human approves
```

### Step 3: Add CI
```bash
mkdir -p .github/workflows
cp .github/workflows/ci.yml .  # From internal repo
git add .github/
git commit -m "Add CI configuration"
```

### Step 4: Tag and Push
```bash
git tag v0.1.0
# HUMAN APPROVAL REQUIRED before next line:
git push -u origin main --tags
```

### Step 5: Switch Visibility
```
# On repository settings page (human executes):
# Switch from Private to Public
```

### Step 6: Create Release
```
# On repository Releases page:
# Create new release "v0.1.0"
# Attach wheel and sdist
```

### Step 7: Post-Release
- [ ] Verify CI passes on public repo
- [ ] Verify online secret scanning passes
- [ ] Add repository description and topics
- [ ] (Optional) Publish to PyPI: `twine upload dist/*`
- [ ] Announce via appropriate channels

---

## PyPI Publishing (Optional)
```bash
pip install twine
twine check dist/*
# HUMAN APPROVAL REQUIRED:
twine upload dist/*
```

---

## Rollback
```bash
# If issues found:
# 1. Delete release
# 2. Switch to Private
# 3. Force-push empty commit or delete repo
# 4. Investigate and fix before re-attempting
```

---

## External Actions Performed
**None** — all steps require explicit human authorization.

# Submission — DevOps Engineer Assignment

**Candidate name:** Rahsheetha V
**Email:** rakshuvasanth18@gmail.com
**Date submitted:** 2026-05-22
**Hours spent (approximate):** 12

## Deliverables checklist

- [x] Part A: Terraform code under /terraform applies cleanly on LocalStack
- [x] Part A: `terraform validate` and `terraform fmt -check` both pass
- [x] Part B: Janitor script runs in --dry-run mode and produces report.json
- [x] Part B: GitHub Actions workflow runs green on a fresh PR
- [x] Part B: --delete mode respects Protected=true tag
- [x] Part C: DESIGN.md is present and within 2 pages
- [x] Walkthrough video link below is accessible (unlisted is fine)

## Walkthrough video

Link (Loom / YouTube unlisted / Google Drive): https://www.loom.com/share/9ccbbe321c0e4a3c8b5d6e82b6d3cc71
Length: max 5 minutes

## Sample report

Path to a sample report.json produced by your script: `samples/report.example.json`

## Known limitations

* S3 lifecycle configuration is currently commented out because of a timeout issue in LocalStack Community Edition. The configuration itself is valid and would work normally on real AWS.

* Unit tests were not implemented, so the `janitor/tests/` directory is empty. This was mainly due to the limited timeline of the assignment.

* `age_days` appears as `0` for all detected resources since the infrastructure was freshly created inside LocalStack during testing. In a real AWS environment, actual resource ages would be visible.

* Remote Terraform state management was intentionally not configured to keep the project fully local and self-contained without requiring real AWS credentials.

---

## AI usage disclosure

* **AI tools used:** Claude (Anthropic) was used for speeding up parts of the development process such as Terraform module scaffolding, initial Python janitor structure, GitHub Actions workflow setup, and debugging the LocalStack S3 lifecycle timeout issue.

* **Issue caught manually:** One incorrect output from the AI was the initial `report.json` schema. It included extra fields like `generated_at` and `total_findings`, which did not match the assignment requirements. This was identified by carefully re-checking the specification and corrected manually.

* **Written manually without AI:** The `Decisions & deviations` section and most of `DESIGN.md` were written manually because they depended more on actual reasoning, debugging experience, and design decisions rather than generated.

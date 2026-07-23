# Resume Match Three-State Design

## Goal

Turn the existing resume-only review surface into a true resume-to-JD matching workflow while preserving uploaded resumes, legacy standalone analysis results, existing APIs, and interview integrations.

## Product Flow

The primary experience uses three independent routes:

1. Input: choose or upload a resume, paste a complete JD, and browse recent matches.
2. Task: show persisted extraction, JD parsing, evidence matching, and report generation progress. Navigation and refresh must not interrupt the task.
3. Report: render a structured match report with an evidence-backed score, requirement coverage, strengths, gaps, interview focus, and resume revision actions.

The interface follows the approved JD analysis visual language: quiet workbench layout, teal primary actions, gold emphasis, coral risk signals, restrained cards, custom confirmation dialogs, responsive one-column mobile layouts, and complete dark mode.

## Data Model

Uploaded resumes remain assets in `resumes`. A new `resume_matches` table stores one record per resume/JD pair:

- identity: `id`, `user_id`, `resume_id`
- input: `job_description`
- output: `result_json`
- lifecycle: `status`, `stage`, `progress`, `error`
- timestamps: `created_at`, `updated_at`

This permits one resume to be matched against multiple roles without overwriting `Resume.analysis_result`. Deleting a match does not delete its resume. Deleting a resume cancels and removes its dependent match records through API cleanup.

## Structured Report

`ResumeMatchReport` contains:

- `job`: inferred title and company when present
- `candidate`: inferred headline and seniority
- `score`: 0-100 overall score, level, and concise rationale
- `metrics`: required coverage, preferred coverage, skill coverage, evidence quality
- `requirements`: importance, match status, JD requirement, resume evidence, and recommendation
- `skills`: importance, match status, evidence, and gap
- `strengths`: evidence-backed advantages
- `gaps`: severity, missing evidence, and repair action
- `interview_focus`: likely question, reason, and preparation
- `resume_actions`: prioritized rewrite actions with optional example text
- `summary`: short conclusion and tags

Scores are allowed because both the JD and resume are present. The model must not invent experience; unsupported claims are explicitly marked as missing evidence.

## API And Task Lifecycle

Existing `/api/resumes/*` endpoints stay compatible. New endpoints are:

- `POST /api/resume-matches` creates a persisted task and returns 202.
- `GET /api/resume-matches` lists history.
- `GET /api/resume-matches/{id}` returns persisted running or terminal state.
- `POST /api/resume-matches/{id}/resume` idempotently reclaims stale tasks.
- `DELETE /api/resume-matches/{id}` cancels and deletes one match.

Stages are `extracting`, `parsing_jd`, `matching`, `saving`, `completed`, and `failed`. `TaskService` provides SSE while database state remains authoritative across reloads.

## Compatibility And Errors

- Legacy `Resume.analysis_result` remains readable from the input page as a legacy resume review.
- The old synchronous `/api/resumes/{id}/analyze` endpoint remains unchanged.
- Missing resume files, unsupported media, model errors, invalid structured output, and stale tasks produce contained error states with retry.
- Browser-native confirmation dialogs and full-screen blocking overlays are not used.

## Verification

- Backend tests cover schema validation, task persistence, stale-task resume, terminal-state protection, history, deletion, and existing resume API regression.
- Frontend build must pass.
- Browser verification covers upload/selection, JD validation, route transitions, leaving and returning during analysis, refresh recovery, report rendering, delete confirmation, desktop/mobile, and light/dark modes.

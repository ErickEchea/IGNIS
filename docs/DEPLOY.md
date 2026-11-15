# Deploying IGNIS

IGNIS is **static-first**. The frontend works on its own from the precomputed bundles in
`frontend/public/data`, and the backend only adds the live Copilot. If the backend is down or asleep, the
site still works, and the Copilot shows the precomputed answers, labeled as such.

## Frontend (Vercel)

1. In Vercel, choose **Add New → Project → Import** `ErickEchea/IGNIS`.
2. Set **Root Directory** to `frontend`. The framework (Vite) is auto-detected.
3. Optional, after the backend is live: add the environment variable `VITE_API_BASE` with the Cloud Run URL, for
   example `https://ignis-api-xxxx.a.run.app`, and redeploy.
4. Single-page-app routing is handled by `frontend/vercel.json`.

## Backend (Google Cloud Run)

Prerequisites:

- a Google Cloud project with billing enabled;
- the Google Cloud SDK (`gcloud`) installed, and `gcloud auth login` done.

```bash
gcloud config set project <PROJECT_ID>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# Store the Gemini key as a secret (never in the image, never in the frontend)
printf "%s" "<GEMINI_API_KEY>" | gcloud secrets create gemini-api-key --data-file=-

# Build with Cloud Build from the repo root (uses Dockerfile + .gcloudignore) and deploy
gcloud run deploy ignis-api --source . --region us-central1 \
  --memory 2Gi --cpu 2 --timeout 120 --concurrency 4 --min-instances 0 --max-instances 2 \
  --allow-unauthenticated \
  --set-env-vars IGNIS_LLM_MODE=CLOUD,IGNIS_ALLOWED_ORIGINS='["https://<your-vercel-domain>"]' \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

Before building, generate the retrieval index locally (`uv run python -m ignis.pipeline.index_build`), because the
image bakes it in. The ONNX models (embeddings, reranker and NLI) are downloaded at build time.

Notes:

- There is no Ollama in the cloud. Use `IGNIS_LLM_MODE=CLOUD`. If Gemini fails, the API answers with evidence
  only and says so.
- `--min-instances 0` keeps cost near zero, but a cold start takes about 20 s while the models load. Use
  `--min-instances 1` during judging if the budget allows.
- To check the deployment: `curl https://<service-url>/api/health` and `curl https://<service-url>/api/status`.

## Freezing the submitted version

When the Space Apps submission is made:

```bash
git tag v1.0-spaceapps && git push origin v1.0-spaceapps
```

Keep the judged Vercel deployment pinned to that commit, and do later work on a separate preview URL.

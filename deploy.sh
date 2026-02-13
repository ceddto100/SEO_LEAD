#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# deploy.sh — Deploy SEO_LEAD to Google Cloud Run + Cloud Scheduler
#
# Prerequisites:
#   1. Install Google Cloud SDK: https://cloud.google.com/sdk/install
#   2. Authenticate: gcloud auth login
#   3. Create a GCP project and enable billing
#   4. Fill in your .env file with real API keys
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Configuration (edit these) ───────────────────────────────
PROJECT_ID="${GCP_PROJECT_ID:-your-gcp-project-id}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="seo-lead"
IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/seo-lead/$SERVICE_NAME"
SCHEDULER_TIMEZONE="America/New_York"

# ── Colors ───────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

# ── Step 1: Enable required APIs ─────────────────────────────
log "Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    --project="$PROJECT_ID"

# ── Step 2: Create Artifact Registry repo (if not exists) ────
log "Creating Artifact Registry repository..."
gcloud artifacts repositories create seo-lead \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT_ID" 2>/dev/null || true

# ── Step 3: Build and push Docker image ──────────────────────
log "Building and pushing Docker image..."
gcloud builds submit . \
    --tag="$IMAGE" \
    --project="$PROJECT_ID"

# ── Step 4: Read .env and convert to Cloud Run env vars ──────
log "Reading .env for Cloud Run environment variables..."
ENV_VARS=""
if [ -f .env ]; then
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        # Skip lines without =
        [[ "$line" != *"="* ]] && continue
        key="${line%%=*}"
        value="${line#*=}"
        # Skip placeholder values
        [[ "$value" == "your_"* ]] && { warn "Skipping placeholder: $key"; continue; }
        [[ -z "$value" ]] && continue
        ENV_VARS="$ENV_VARS,$key=$value"
    done < .env
    # Remove leading comma
    ENV_VARS="${ENV_VARS#,}"
fi

# ── Step 5: Deploy to Cloud Run ──────────────────────────────
log "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
    --image="$IMAGE" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --platform=managed \
    --no-allow-unauthenticated \
    --memory=512Mi \
    --timeout=300 \
    --max-instances=1 \
    --set-env-vars="$ENV_VARS" \
    --quiet

# Get the service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format="value(status.url)")
log "Service deployed at: $SERVICE_URL"

# ── Step 6: Create service account for Cloud Scheduler ───────
SA_NAME="seo-lead-scheduler"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

log "Creating scheduler service account..."
gcloud iam service-accounts create "$SA_NAME" \
    --display-name="SEO Lead Scheduler" \
    --project="$PROJECT_ID" 2>/dev/null || true

# Grant the SA permission to invoke Cloud Run
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/run.invoker" \
    --quiet

# ── Step 7: Create Cloud Scheduler cron jobs ─────────────────
log "Setting up Cloud Scheduler jobs..."

create_job() {
    local name=$1
    local schedule=$2
    local path=$3
    local description=$4

    gcloud scheduler jobs delete "$name" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --quiet 2>/dev/null || true

    gcloud scheduler jobs create http "$name" \
        --schedule="$schedule" \
        --uri="$SERVICE_URL$path" \
        --http-method=POST \
        --oidc-service-account-email="$SA_EMAIL" \
        --oidc-token-audience="$SERVICE_URL" \
        --location="$REGION" \
        --project="$PROJECT_ID" \
        --time-zone="$SCHEDULER_TIMEZONE" \
        --description="$description" \
        --attempt-deadline="300s" \
        --quiet

    log "  Created: $name ($schedule)"
}

# Workflow schedules
create_job "seo-wf01-keyword-research"  "0 6 * * 1"      "/run/wf01" "WF01: Keyword Research (Mon 6am)"
create_job "seo-wf02-content-strategy"  "0 7 * * 1"      "/run/wf02" "WF02: Content Strategy (Mon 7am)"
create_job "seo-wf03-blog-writing"      "0 8 * * 1,3,5"  "/run/wf03" "WF03: Blog Writing (Mon/Wed/Fri 8am)"
create_job "seo-wf04-image-generation"  "30 8 * * 1,3,5" "/run/wf04" "WF04: Image Gen (Mon/Wed/Fri 8:30am)"
create_job "seo-wf05-auto-publishing"   "0 9 * * 1,3,5"  "/run/wf05" "WF05: Publishing (Mon/Wed/Fri 9am)"
create_job "seo-wf06-social-media"      "30 9 * * 1,3,5" "/run/wf06" "WF06: Social Media (Mon/Wed/Fri 9:30am)"
create_job "seo-wf07-lead-capture"      "*/30 * * * *"    "/run/wf07" "WF07: Lead Capture (every 30 min)"
create_job "seo-wf08-crm-followup"      "0 10 * * *"     "/run/wf08" "WF08: CRM Follow-Up (daily 10am)"
create_job "seo-wf09-email-marketing"   "0 8 * * 4"      "/run/wf09" "WF09: Email Marketing (Thu 8am)"
create_job "seo-wf10-analytics-daily"   "0 23 * * *"     "/run/wf10" "WF10: Analytics (daily 11pm)"
create_job "seo-wf11-feedback-loop"     "0 8 * * 0"      "/run/wf11" "WF11: Feedback Loop (Sun 8am)"

# ── Done ─────────────────────────────────────────────────────
echo ""
log "═══════════════════════════════════════════════════════════"
log "DEPLOYMENT COMPLETE!"
log "═══════════════════════════════════════════════════════════"
log ""
log "Service URL:  $SERVICE_URL"
log "Region:       $REGION"
log "Auth:         OIDC (Cloud Scheduler only)"
log "Cron jobs:    11 created"
log ""
log "Next steps:"
log "  1. Verify: curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" $SERVICE_URL/"
log "  2. Manual trigger: gcloud scheduler jobs run seo-wf01-keyword-research --location=$REGION"
log "  3. View logs: gcloud run logs read --service=$SERVICE_NAME --region=$REGION"

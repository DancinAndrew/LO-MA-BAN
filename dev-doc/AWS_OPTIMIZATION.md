# ScoutNet Backend — AWS Optimization Plan

> Based on current architecture: FastAPI + 4 parallel security API calls + conditional LLM analysis

---

## Priority 1: Amazon ElastiCache (Redis) — Response Caching

**Problem**: Every `/api/v1/analyze` request hits 4 external security APIs + LLM, even for the same URL.

**Solution**: Use ElastiCache (Redis) to cache security check results by URL.

- **Cache key**: URL hash (SHA-256)
- **TTL strategy**:
  - Security results: 1–6 hours (threat databases update periodically)
  - LLM analysis: 12–24 hours (same input = same output at low temperature)
  - Full response: 1 hour (for identical requests within short window)
- **Expected improvement**: Repeated URL lookups drop from ~5–15s to <50ms
- **Cost**: ~$15–50/month (cache.t3.micro/small)

```
Client → API → Redis Cache HIT → return cached response (< 50ms)
                       MISS → Security APIs + LLM → cache + return
```

---

## Priority 2: AWS App Runner or ECS Fargate — Public Deployment

**Problem**: No production-grade deployment; running locally via `uvicorn`.

**Solution**: Use **App Runner** (simplest) or **ECS Fargate** (more control) for containerized deployment.

### Option A: App Runner (Recommended for MVP)
- Auto-scaling, built-in HTTPS, zero infrastructure management
- Connect directly from GitHub/ECR
- Custom domain support via Route 53
- Cost: Pay per request/compute, ~$5–25/month at low traffic

### Option B: ECS Fargate (Recommended for Production)
- More granular scaling policies
- VPC integration (for ElastiCache private access)
- Task-level resource control (CPU/Memory)
- ALB for load balancing + health checks
- Cost: ~$15–60/month depending on traffic

### Deployment Checklist
1. Create `Dockerfile` (Python 3.12 + uvicorn)
2. Push to ECR
3. Configure App Runner / ECS service
4. Set environment variables via service config (not .env file)

---

## Priority 3: Amazon API Gateway — Rate Limiting & API Management

**Problem**: No rate limiting, no API key management, CORS wildcard `allow_origins=["*"]`.

**Solution**: Put API Gateway in front of the backend service.

- **Usage plans**: Limit requests per API key (e.g., 100 req/min for Chrome Extension)
- **Throttling**: Prevent abuse from a single client
- **API keys**: Issue keys to Chrome Extension for tracking
- **CORS**: Managed at Gateway level instead of application code
- **Request/Response transformation**: Strip unnecessary headers
- **Cost**: ~$3.50 per million requests

---

## Priority 4: AWS Secrets Manager — Secure API Key Storage

**Problem**: API keys stored in `.env` file, loaded via `python-dotenv`.

**Solution**: Migrate to Secrets Manager for all sensitive credentials.

- **Keys to migrate**: `FEATHERLESS_API_KEY`, `VIRUSTOTAL_API_KEY`, `URLHAUS_AUTH_KEY`, `PHISHTANK_API_KEY`, `GOOGLE_SAFE_BROWSING_API_KEY`
- **Benefits**: Automatic rotation, audit trail (CloudTrail), IAM-based access control
- **Integration**: Use `boto3` to fetch secrets at startup, cache in memory
- **Cost**: $0.40/secret/month + $0.05 per 10K API calls

```python
# Example integration
import boto3, json

def get_secrets():
    client = boto3.client("secretsmanager", region_name="ap-northeast-1")
    resp = client.get_secret_value(SecretId="scoutnet/api-keys")
    return json.loads(resp["SecretString"])
```

---

## Priority 5: Amazon Bedrock — Replace External LLM

**Problem**: LLM calls go to Featherless AI (external), adding network latency + dependency on third-party availability.

**Solution**: Use Amazon Bedrock (e.g., Claude 3 Haiku / Llama 3) for same-region, low-latency inference.

- **Latency reduction**: Eliminate cross-network hop; same VPC/region
- **Availability**: AWS SLA-backed, no third-party downtime risk
- **Model options**: Claude 3 Haiku (fast + cheap), Claude 3.5 Sonnet (smarter)
- **Integration**: Replace `AsyncOpenAI` client with `boto3` Bedrock runtime
- **Cost**: Pay per token, Haiku ~$0.25/1M input tokens

**Trade-off**: Requires AWS account with Bedrock access enabled; model selection differs from Featherless.

---

## Priority 6: Amazon CloudFront — Edge Caching

**Problem**: All requests routed to single-region backend.

**Solution**: CloudFront CDN in front of API Gateway/App Runner.

- Cache `GET /health` at edge indefinitely
- Cache `POST /api/v1/analyze` responses by request body hash (custom cache policy)
- Provides global edge locations for lower latency worldwide
- Built-in DDoS protection (AWS Shield Standard)
- Cost: ~$0.085/GB data transfer

---

## Priority 7: AWS WAF — API Protection

**Problem**: No protection against malicious traffic, bot abuse, or injection.

**Solution**: Attach WAF to API Gateway or CloudFront.

- **Managed rule groups**: Common threats, known bad inputs, SQL injection
- **Rate-based rules**: Block IPs exceeding threshold (e.g., 2000 req/5min)
- **Geo-blocking**: Optional, restrict to target regions
- **Cost**: $5/month per Web ACL + $1/month per rule

---

## Priority 8: Amazon CloudWatch — Observability

**Problem**: Logging only to stderr; no metrics, no alerting.

**Solution**: CloudWatch for centralized logging + metrics + alarms.

- **Logs**: Structured JSON logs → CloudWatch Logs → Insights queries
- **Custom Metrics**: API latency, cache hit ratio, LLM token usage, error rate by source
- **Alarms**: Alert on high error rate, LLM timeout, security API failures
- **Dashboard**: Real-time view of all key metrics
- **Cost**: ~$0.50/GB log ingestion

---

## Priority 9: Amazon DynamoDB — Analysis History

**Problem**: No persistence; analysis results are fire-and-forget.

**Solution**: Store each analysis result in DynamoDB for history/analytics.

- **Partition key**: URL hash
- **Sort key**: Timestamp
- **Use cases**: Trend analysis, repeat-offender detection, user history
- **TTL**: Auto-expire records after 90 days to control storage
- **Cost**: On-demand ~$1.25/million writes

---

## Architecture Diagram (Target State)

```
Chrome Extension
      │
      ▼
CloudFront (CDN + DDoS)
      │
      ▼
API Gateway (Rate Limit + API Key + WAF)
      │
      ▼
App Runner / ECS Fargate
   ├── ElastiCache (Redis) ← Cache layer
   ├── Secrets Manager     ← API keys
   ├── Bedrock (LLM)       ← Same-region inference
   └── CloudWatch           ← Logs + Metrics
      │
      ▼
DynamoDB (History)
```

---

## Cost Estimate (Low Traffic, ~10K req/month)

| Service          | Monthly Cost |
|------------------|-------------|
| App Runner       | ~$10        |
| ElastiCache      | ~$15        |
| API Gateway      | ~$1         |
| Secrets Manager  | ~$3         |
| CloudFront       | ~$1         |
| WAF              | ~$6         |
| CloudWatch       | ~$3         |
| DynamoDB         | ~$1         |
| **Total**        | **~$40**    |

> Bedrock cost depends on LLM usage volume; estimate $5–20/month at 10K requests with ~30% LLM trigger rate.

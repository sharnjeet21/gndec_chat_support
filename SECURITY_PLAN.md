# Tech Support AI — Long-Term Security Plan

This document outlines the strategic steps required to secure this application for production use. It serves as a roadmap for the team.

## 1. Infrastructure & Secrets Management

- **Current State:** Credentials (`API_KEY`, Postgres passwords, Redis passwords) are stored in local `.env` files.
- **Long-Term Plan:**
  - Migrate all secrets to a managed secrets provider (e.g., AWS Secrets Manager, HashiCorp Vault, or Doppler).
  - Use CI/CD to inject secrets securely into the production environment at runtime.
  - Rotate database and JWT secrets every 90 days.

## 2. Authentication & Authorization

- **Current State:** A single `X-API-KEY` is checked in the FastAPI middleware, and user sessions are linked loosely by `phone` number provided by the client.
- **Long-Term Plan:**
  - **API Layer:** Implement OAuth2 with JWT (JSON Web Tokens). The frontend should negotiate a token upon login and pass it via the `Authorization: Bearer <token>` header.
  - **User Identity:** Integrate an Identity Provider (IdP) like Auth0, AWS Cognito, or custom Postgres-backed user tables to verify ownership of phone numbers via OTP (One-Time Password) before issuing a JWT.
  - **RBAC (Role-Based Access Control):** Differentiate between standard users (students/parents) and admin users (staff who can update FAISS embeddings or view chat histories).

## 3. Network Security & DDoS Protection

- **Current State:** CORS was fully permissive (`*`). (Recently patched to allow only defined `FRONTEND_URLS`).
- **Long-Term Plan:**
  - **WAF:** Deploy the application behind a Web Application Firewall (Cloudflare or AWS WAF) to filter out SQL injection attempts, malformed requests, and mitigate DDoS attacks.
  - **Rate Limiting:** Implement robust rate limiting on the `/api/ask` and `/api/ask_stream` endpoints to prevent abuse of the LLM API, using Redis to track hits per IP or per JWT. (e.g. 10 requests per minute).

## 4. LLM Security (Prompt Guarding)

- **Current State:** The LLM is given a system prompt and relies on basic instruction adherence.
- **Long-Term Plan:**
  - **Prompt Injection Defense:** Run user queries through an LLM guardrail (like NeMo Guardrails or Lakera) *before* passing them to the main LLM.
  - **PII Scrubbing:** If users input sensitive data (credit cards, Aadhar numbers, etc.), use an NLP scrubbing layer (like Microsoft Presidio) to mask this data before saving to Redis or sending to the LLM.
  - **Output Parsing:** Verify that the output doesn't contain hallucinated links or malicious markdown that could lead to XSS on the React frontend.

## 5. Database Security

- **Current State:** Local Postgres and Redis instances without TLS.
- **Long-Term Plan:**
  - **Encryption in Transit:** Require TLS/SSL for all connections to PostgreSQL and Redis.
  - **Encryption at Rest:** Ensure the host volumes for Postgres and Redis are encrypted (e.g., AWS EBS encryption, or LUKS on Linux).
  - **Data Retention:** The current Redis session TTL is 7 days. Ensure that Postgres logs and historical chats are subject to a strict 30-day or 90-day retention policy to comply with data minimization principles.

---
*End of Plan*

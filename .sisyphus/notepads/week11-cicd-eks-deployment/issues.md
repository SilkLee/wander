# Issues — Week 11 CI/CD + EKS Deployment

## [2026-03-15] Session Started: ses_31077bfdbffeX00Hgz5ysRHTV1

### Known Constraints
- Docker CLI not available in dev env — Dockerfile validation by inspection only
- terraform, kubectl, aws CLI not available — IaC validation uses `terraform validate` with `-backend=false`
- Tasks 11-13 (actual deployment) must be run from user's real terminal

### Known Gotchas
- Background agents consistently error/expire — ALL work done in main session
- PostgreSQL init.sql needs `IF NOT EXISTS` added before mounting as ConfigMap
- Frontend nginx.conf needs `/api` proxy_pass to api-gateway:8000
- Go api-gateway scratch base: NO exec probes allowed anywhere
- finetune service has tests but NO Dockerfile — must create one
- finetune NOT in docker-compose.yml — port 8006 assigned

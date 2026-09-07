# M09-RUNTIME-007 PM real restart evidence

Status: `READY_FOR_INDEPENDENT_VERIFY`

Observed at: 2026-09-07 14:48–14:57 CST.

## First integrated draft — FAIL retained

- Exact PID `240721` was stopped and the production launcher started PID `279636`.
- No manual probe POST was issued.
- Startup completed in 7.535 seconds with `enabled=true`, `probed=8`, `available=4`.
- Health remained OK with 10 services, but capability returned
  `supported=false / SERVICE_PROBE_CHANGED`; 5182 create-options closed.
- PM rejected the worker receipt and restored the live preview temporarily with
  startup auto-probe disabled plus only the four previously accepted probes.

## Corrected integrated draft — PASS candidate

- Exact temporary PID `280547` was stopped; it exited naturally after TERM.
- Production launcher started PID `292980` in tmux pane `%26` with its default
  automatic readiness behavior. No manual probe POST was issued.
- Startup completed in 5.253 seconds.
- Health: `startup_readiness={enabled:true, probed:4, available:4}`;
  `service_count=10`; encrypted Secret Store and storage checks OK.
- Capability: `supported=true`, `reason_code=null`, `bootstrap_ready=true`.
- 8000 and 5182 create-options both returned infographic
  `available=true` with no `reason` field.

No Task, render, provider generation, service definition, Secret, activation
pointer or frozen output was created or changed.

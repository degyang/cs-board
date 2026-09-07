# M09-ACTIVATE-005 PM acceptance supplement

Verdict: **ACCEPTED**

- Consumed independent `M09-ACTIVATE-005-V` PASS: three implementation hashes and
  pointer hash unchanged; 38 focused tests passed with the one documented unrelated
  browser-resolver deselection; live 8000 capability and 8000/5182 create-options
  both expose `infographic-remotion` as available; service and voice invariants hold;
  fresh Workmates evidence is PASS.
- PM supplemented the verifier's unavailable browser layer using the accepted local
  Chrome Headless Shell `152.0.7977.75`, an isolated `/tmp` profile, and CDP against
  `http://127.0.0.1:5182/tasks/new`. After clicking `#tab-output`, the button containing
  `动态信息图` was found with `disabled=false`, class `opt-card output-card`, and no
  `暂未开放` text. No form submission, task, run, render, provider call, service edit,
  secret access, or user-data write was performed.
- The response still carries a cosmetic `reason="能力未就绪"` when available because
  `create_options()` fills a default reason for null reason codes; the UI displays it
  only for unavailable options. This is non-blocking and is not treated as a runtime
  readiness failure.
- Final video appearance and content quality remain user acceptance.

# Clean-install and offline rehearsal

## Required machine

- Python 3.11+
- Node.js 20+
- 2 GB free RAM for the 500-record demonstration
- Internet is needed once to install packages; normal runtime needs no external service or paid API

## Rehearsal

1. Clone the repository into a new directory.
2. Run `npm run install:all`.
3. Run `npm test`.
4. Run `npm run build`.
5. Start with `npm run dev` and open `http://localhost:5173`.
6. Select **Fusion replay**, click **Reset**, then **Start guided demo**.
7. Confirm 14/14 entities, 6/6 relations, hidden path `YES`, false merges `0`.
8. Confirm protected identities are masked and the risk policy says prohibited.
9. Select **Verify chain** and confirm `VALID`.
10. Turn off network access, refresh the app, repeat the replay, TRACE path, graph view, analytics, and PDF export.

## Automated release check

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_release.ps1
```

Expected result: backend tests, frontend tests, production build, dependency checks, flagship ground truth, audit verification, and scale-result presence all pass.

## Judge-day reset

- The reset removes only synthetic identity-review decisions; it does not alter evidence.
- A reset itself is appended to the audit chain.
- Keep `operation-suraksha` active and stage one selected.
- Use only fictional identifiers on the public deployment.
- If a free host was idle, open it two minutes before the round to allow a cold start.

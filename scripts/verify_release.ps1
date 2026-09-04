$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Push-Location $ProjectRoot
try {
    python -m pytest -q
    Push-Location (Join-Path $ProjectRoot "frontend")
    try {
        npm test
        npm run build
        npm audit --audit-level=high
    } finally {
        Pop-Location
    }
    python -m pip check
    python -c "from backend.app.suraksha import evaluation; value=evaluation()['summary']; assert value['entities_recovered']==14 and value['relationships_recovered']==6 and value['false_merges']==0"
    python -c "from backend.app.suraksha import fusion_assurance; value=fusion_assurance()['summary']; assert value['patterns_recovered']==5 and value['edge_provenance_coverage']==100.0"
    python -c "import json, pathlib; value=json.loads(pathlib.Path('backend/benchmarks/model_evaluation.json').read_text()); assert value['dataset']['suspects']==434 and value['graphsage']['held_out_node_validation']['samples']==87 and value['claim_assurance']['field_accuracy']=='not-established' and len(value['limitations'])>=4"
    python -c "from backend.app.readiness import system_readiness; assert system_readiness()['ready']"
    Write-Host "Sentinel release verification passed." -ForegroundColor Green
} finally {
    Pop-Location
}

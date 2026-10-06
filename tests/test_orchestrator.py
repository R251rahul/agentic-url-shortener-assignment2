from app.store import SQLiteStore
from app.orchestrator import Orchestrator

def test_greenfield_dag_succeeds(tmp_path):
    o=Orchestrator(SQLiteStore(str(tmp_path/'a.db')))
    r=o.start('greenfield','Build a URL shortener with analytics',True)
    assert r['status'] == 'SUCCEEDED'
    assert r['nodes']['tests']['status'] == 'SUCCEEDED'
    assert r['nodes']['security']['status'] == 'SUCCEEDED'
    assert r['metrics']['success_rate'] == 1.0

def test_ambiguous_requires_approval_when_disabled(tmp_path):
    o=Orchestrator(SQLiteStore(str(tmp_path/'a.db')))
    r=o.start('ambiguous','Build a shortener; analytics are required but retention is unclear',False)
    assert r['status'] == 'WAITING_APPROVAL'
    r=o.approve(r['run_id'], True, 'Approved after requirement review')
    assert r['status'] == 'SUCCEEDED'

def test_brownfield_has_analysis_dependency(tmp_path):
    o=Orchestrator(SQLiteStore(str(tmp_path/'a.db')))
    r=o.start('brownfield','Add analytics to the existing URL shortener without breaking redirect',True)
    assert r['status'] == 'SUCCEEDED'
    assert r['nodes']['brownfield_analysis']['status'] == 'SUCCEEDED'

def test_replan_increments_context(tmp_path):
    o=Orchestrator(SQLiteStore(str(tmp_path/'a.db')))
    r=o.start('greenfield','Build shortener',True)
    version=r['context']['context_version']
    r=o.replan(r['run_id'],'Also add expiry support and analytics retention policy')
    assert r['context']['context_version'] > version
    assert r['status'] == 'SUCCEEDED'

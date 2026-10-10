import copy
from datetime import datetime, timedelta, timezone
import json
import tempfile
import threading
import unittest
from pathlib import Path
from production import Ledger
from media_review import bounds
from lint_plan import lint, BOUNDARY


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.l = Ledger(self.root/'project', {'show_before_regeneration': True})
        self.file = self.root/'fake.mp4'; self.file.write_bytes(b'original media fixture')
        self.l.add({'id':'plan1','kind':'plan','data': {'intent':'continuous tracking'}})
        self.l.review('plan1','accepted','agent preflight: plan reviewed under user brief')

    def tearDown(self):
        self.l.close(); self.temp.cleanup()

    def spec(self, key='j1', parents=None):
        return {'id':key,'shot':'s1','endpoint':'test/not-network','input':{'prompt':'track right'},
                'parents':parents or ['plan1'],'authorization_source':'test user request','capability_source':'test fixture', 'capability_checked_at':datetime.now(timezone.utc).date().isoformat()}

    def finished(self):
        self.l.create_job(self.spec()); self.l.claim('j1'); self.l.submitted('j1','remote1')
        self.l.complete('j1','clip1',self.file)

    def test_ambiguous_submission_survives_reopen_and_cannot_retry(self):
        self.l.create_job(self.spec()); self.l.claim('j1'); self.l.close()
        self.l=Ledger(self.root/'project')
        self.assertIn('do not POST', self.l.resume()['jobs'][0]['next_action'])
        with self.assertRaises(ValueError): self.l.claim('j1')
        self.l.submitted('j1','recovered-id')
        self.l.submitted('j1','recovered-id')  # idempotent reconciliation
        with self.assertRaises(ValueError): self.l.submitted('j1','different-id')

    def test_show_before_regeneration_and_review(self):
        self.finished(); self.l.create_job(self.spec('j2'))
        with self.assertRaises(ValueError): self.l.claim('j2')
        with self.assertRaises(ValueError): self.l.review('clip1','accepted','pretend approval')
        self.l.shown('j1','message/display-1'); self.l.review('clip1','accepted','user: next shot')
        self.l.claim('j2')

    def test_canonical_change_invalidates_transitive_children_and_pending_jobs(self):
        self.l.alias('look','plan1','initial')
        self.l.add({'id':'frame1','kind':'image','parents':['plan1']})
        self.l.review('frame1','accepted','approved')
        self.l.add({'id':'child1','kind':'clip','parents':['frame1']})
        self.l.review('child1','accepted','approved')
        self.l.create_job(self.spec())
        self.l.add({'id':'plan2','kind':'plan'})
        self.l.review('plan2','accepted','replacement approved')
        self.l.alias('look','plan2','user correction')
        self.assertTrue(self.l.node('child1')['stale'])
        with self.assertRaises(ValueError): self.l.claim('j1')
        self.assertEqual(self.l.node('plan1')['status'],'accepted')

    def test_replacement_derived_from_old_reference_stays_fresh(self):
        self.l.alias('look','plan1','initial')
        self.l.add({'id':'plan2','kind':'plan','parents':['plan1']})
        self.l.review('plan2','accepted','reviewed edit derived from prior')
        self.l.alias('look','plan2','replacement')
        self.l.fresh('plan2',accepted=True)
        self.l.create_job(self.spec(parents=['plan2']))

    def test_output_completed_after_reference_change_is_preserved_but_stale(self):
        self.l.alias('look','plan1','initial'); self.l.create_job(self.spec())
        self.l.claim('j1'); self.l.submitted('j1','remote')
        self.l.add({'id':'plan2','kind':'plan'}); self.l.review('plan2','accepted','new')
        self.l.alias('look','plan2','changed during generation')
        self.l.complete('j1','clip1',self.file)
        self.assertTrue(self.l.node('clip1')['stale'])
        self.l.shown('j1','display stale result')
        with self.assertRaises(ValueError): self.l.review('clip1','accepted','approval')

    def test_tampering_detected_through_ancestor(self):
        self.l.add({'id':'frame','kind':'image','file':str(self.file),'parents':['plan1']})
        self.l.review('frame','accepted','approved')
        self.l.add({'id':'derived','kind':'frame','parents':['frame']})
        (self.l.root/self.l.node('frame')['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError): self.l.fresh('derived')

    def test_rollback_on_duplicate_keeps_original_and_events(self):
        before=self.l.resume()
        with self.assertRaises(Exception): self.l.add({'id':'plan1','kind':'changed'})
        self.assertEqual(self.l.node('plan1')['kind'],'plan')
        self.assertEqual(before['recent_events'], self.l.resume()['recent_events'])

    def test_dangling_self_and_secret_references_rejected(self):
        for parents in (['missing'], ['cycle']):
            with self.assertRaises(ValueError): self.l.add({'id':'cycle','kind':'plan','parents':parents})
        spec=self.spec(); spec['input']['Authorization']='secret'
        with self.assertRaises(ValueError): self.l.create_job(spec)
        self.assertEqual(self.l.resume()['jobs'],[])

    def test_concurrent_claim_is_single_winner(self):
        self.l.create_job(self.spec()); results=[]; barrier=threading.Barrier(2)
        def attempt():
            db=Ledger(self.root/'project')
            try:
                barrier.wait(); db.claim('j1'); results.append('claimed')
            except ValueError: results.append('blocked')
            finally: db.close()
        ts=[threading.Thread(target=attempt) for _ in range(2)]
        for t in ts:t.start()
        for t in ts:t.join(timeout=10)
        self.assertCountEqual(results,['claimed','blocked'])

    def test_no_second_inflight_job(self):
        self.l.create_job(self.spec()); self.l.claim('j1')
        self.l.create_job(self.spec('j2'))
        with self.assertRaises(ValueError): self.l.claim('j2')
        self.l.fail('j1','not_submitted','provider verified request was never received')
        self.l.claim('j2')

    def test_capability_age_blocks_claim(self):
        spec=self.spec();spec['capability_checked_at']=(datetime.now(timezone.utc).date()-timedelta(days=8)).isoformat()
        self.l.create_job(spec)
        with self.assertRaises(ValueError):self.l.claim('j1')

    def test_timeout_cannot_be_recorded_as_terminal_failure(self):
        self.l.create_job(self.spec());self.l.claim('j1')
        with self.assertRaises(ValueError):self.l.fail('j1','failed','client timed out')
        with self.assertRaises(ValueError):self.l.fail('j1','unknown','no response')
        self.l.submitted('j1','recovered')
        with self.assertRaises(ValueError):self.l.fail('j1','not_submitted','contradictory')
        self.l.fail('j1','failed','saved provider FAILED receipt')

    def test_no_new_dependency_on_superseded_reference(self):
        self.l.alias('current','plan1','initial')
        self.l.add({'id':'new','kind':'plan'});self.l.review('new','accepted','new')
        self.l.alias('current','new','replacement')
        with self.assertRaises(ValueError):self.l.add({'id':'bad','kind':'image','parents':['plan1']})

    def test_policy_change_requires_evidence_and_preserves_history(self):
        with self.assertRaises(ValueError): self.l.policy({'show_before_regeneration':False}, '')
        self.l.policy({'show_before_regeneration':False}, 'User now permits automatic batches')
        self.assertFalse(self.l.config()['show_before_regeneration'])
        self.assertEqual(self.l.resume()['recent_events'][0]['type'], 'policy')

    def test_job_requires_accepted_plan_dependency(self):
        self.l.add({'id':'frame','kind':'image'}); self.l.review('frame','accepted','approved')
        with self.assertRaises(ValueError): self.l.create_job(self.spec(parents=['frame']))

    def test_existing_init_is_not_overwritten(self):
        with self.assertRaises(ValueError): Ledger(self.root/'project',{'show_before_regeneration':False})
        self.assertTrue(self.l.config()['show_before_regeneration'])

    def test_accepted_review_immutable_and_evidence_required(self):
        with self.assertRaises(ValueError): self.l.review('plan1','rejected','new view')
        with self.assertRaises(ValueError): self.l.alias('bad','plan1','')


class ContractTests(unittest.TestCase):
    def shot(self):
        state={k:'same' for k in BOUNDARY};state['speed_class']='slow'
        return {'id':'s1','purpose':'reveal','primary_camera_move':'track','conditioning':'video_extension',
                'usable_seconds':6,'generation_seconds':8,'entry':state.copy(),'exit':state.copy(),'join_after':'continuous'}

    def test_boundary_state_mismatch_caught(self):
        a=self.shot();b=copy.deepcopy(a);b.update(id='s2',join_after='end')
        self.assertFalse(lint({'shots':[a,b]})['errors'])
        b['entry']['motion_direction']='left'
        self.assertTrue(any('motion_direction' in e for e in lint({'shots':[a,b]})['errors']))

    def test_unplanned_stop_and_impossible_duration_caught(self):
        a=self.shot();a['exit']['speed_class']='stopped';a['usable_seconds']=9
        errors=lint({'shots':[a]})['errors']
        self.assertTrue(any('stopped' in e for e in errors));self.assertTrue(any('duration' in e for e in errors))

    def test_exact_frame_boundary_ranges(self):
        a={'frames':240,'fps':'24'};b={'frames':300,'fps':'30000/1001'}
        self.assertEqual(bounds(a,b,240,0,1),(216,240,0,30))
        for out,inc,secs in ((0,0,1),(241,0,1),(240,300,1),(240,0,float('nan'))):
            with self.assertRaises(ValueError):bounds(a,b,out,inc,secs)


if __name__=='__main__':unittest.main()

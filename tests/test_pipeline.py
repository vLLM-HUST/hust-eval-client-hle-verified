import argparse
import ast
import copy
import hashlib
import http.server
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from hust_eval_hle_verified import pipeline as p, seal
from hust_eval_hle_verified.official_prompts import SYSTEM_PROMPT, JUDGE_PROMPT, RESPONSE_FORMAT

GOOD={'extracted_final_answer':'A','reasoning':'Matches the reference.','correct':'yes','confidence':90,'strict':True}

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.counter=0;outer=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                outer.counter+=1;outer.bodies.append(body)
                content=json.dumps(GOOD) if 'response_format' in body else 'Explanation: test\nAnswer: A\nConfidence: 90%'
                response={'choices':[{'message':{'content':content},'finish_reason':'stop'}],'usage':{'completion_tokens':10}}
                raw=json.dumps(response).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        self.bodies=[];self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.assets=self.root/'assets';self.info={}
        for tr in ('gold','revision'):
            rows=[{'id':tr+'1','question':'Question\u2028unicode line separator','answer':True if tr=='revision' else 'A',
                   'answer_type':'multipleChoice','Verified_Classes':tr.title()+' subset','image':'','category':'Math'},
                  {'id':tr+'2','question':'Image question','answer':'A','answer_type':'exactMatch',
                   'Verified_Classes':tr.title()+' subset','image':'data:image/png;base64,YWJj','category':'Physics'}]
            dest=self.assets/tr/'test.jsonl';dest.parent.mkdir(parents=True)
            dest.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
            self.info[tr]={'rows':2,'bytes':dest.stat().st_size,'sha256':p.sha256_file(dest),'filename':tr+'.jsonl'}
        self.patcher=patch.object(p,'DATA',self.info);self.patcher.start()
        cfg={'base_url':'http://127.0.0.1:'+str(self.server.server_port),'model':'synthetic-test','concurrency':2,'timeout':3,
             'request':{'max_tokens':40,'temperature':0}}
        p.dump(self.root/'solver.json',cfg);p.dump(self.root/'judge.json',dict(cfg,scoring_policy='strict_json'))
        self.plan=self.root/'plan'
    def tearDown(self):
        self.patcher.stop();self.server.shutdown();self.server.server_close();self.tmp.cleanup()
    def prepare(self,modality='all'):
        return p.prepare(argparse.Namespace(output=str(self.plan),assets=str(self.assets),subset=None,modality=modality,
            solver_config=str(self.root/'solver.json'),judge_config=str(self.root/'judge.json')))
    def execute(self,stage,**kwargs):
        a=argparse.Namespace(plan=str(self.plan),output=str(self.root/stage),responses=str(self.root/'solver'),
                             resume=kwargs.get('resume',False),limit=None,case_ids=None,track=None)
        return p.execute(a,stage)
    def test_end_to_end_prompts_images_resume_summary(self):
        self.prepare();self.execute('solver')
        self.assertEqual(self.counter,4)
        self.assertEqual(self.bodies[0]['messages'][0],{'role':'system','content':SYSTEM_PROMPT})
        self.assertTrue(any(any(x.get('type')=='image_url' for x in b['messages'][1]['content']) for b in self.bodies))
        self.execute('solver',resume=True);self.assertEqual(self.counter,4)
        self.execute('judge');self.assertEqual(self.counter,8)
        for b in self.bodies[4:]:
            self.assertEqual(b['response_format'],RESPONSE_FORMAT)
            self.assertEqual(b['messages'][0]['role'],'user')
            self.assertIn('[correct_answer]:',b['messages'][0]['content'])
        report=p.summary(argparse.Namespace(plan=str(self.plan),responses=str(self.root/'solver'),grades=str(self.root/'judge'),output=str(self.root/'report')))
        self.assertEqual(report['tracks']['gold']['accuracy'],1)
        self.assertEqual(report['scope'],'complete_selected_plan')
        self.assertEqual(report['groups']['revision/image']['total'],1)
    def test_text_selection_is_explicit(self):
        self.prepare('text-only');c,t=p.load_plan(self.plan)
        self.assertEqual(len(t),2);self.assertEqual(c['selection']['excluded'],2)
        self.assertEqual(t[1]['answer'],'True')
    def test_dataset_tamper_rejected(self):
        with (self.assets/'gold/test.jsonl').open('a') as f:f.write(' ')
        with self.assertRaises(ValueError):self.prepare()
    def test_contract_and_task_tamper_rejected(self):
        self.prepare()
        with (self.plan/'contract.json').open('a') as f:f.write(' ')
        with self.assertRaises(ValueError):p.load_plan(self.plan)
    def test_resume_tamper_rejected(self):
        self.prepare();self.execute('solver')
        f=next((self.root/'solver/requests').glob('*.json'));obj=p.read(f);obj['content']='tampered';p.dump(f,obj)
        with self.assertRaises(ValueError):self.execute('solver',resume=True)
    def test_judge_cannot_mix_solver_runs(self):
        self.prepare();self.execute('solver');self.execute('judge')
        f=self.root/'solver/run.json';obj=p.read(f);obj['stage']='wrong';p.dump(f,obj)
        with self.assertRaises(ValueError):p.verify_run(self.root/'solver',p.sha256_file(self.plan/'contract.json'),'solver')
    def test_materialize_excludes_images_and_records_scope(self):
        self.prepare();out=self.root/'bench.jsonl'
        result=p.materialize(argparse.Namespace(plan=str(self.plan),sample=None,output=str(out)))
        self.assertEqual(result['prompts'],2)
        self.assertEqual(p.read(str(out)+'.manifest.json')['excluded_images'],2)
    def test_official_grade_schema_and_truncation(self):
        self.assertTrue(p.parse_grade('gold',json.dumps(GOOD),'stop')['correct'])
        with self.assertRaises(ValueError):p.parse_grade('gold',json.dumps(GOOD),'length')
        self.assertTrue(p.parse_grade('gold',json.dumps(GOOD),'length','complete_json')['correct'])
        for raw in ['VERDICT: CORRECT','```json\n'+json.dumps(GOOD)+'\n```',json.dumps(GOOD)[:-1],json.dumps(GOOD)[:-1]+',"correct":"no"}']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):p.parse_grade('gold',raw,'stop')
        for key,value in [('confidence',True),('confidence',101),('correct','YES'),('strict',False)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):p.parse_grade('gold',json.dumps(dict(GOOD,**{key:value})),'stop')
    def test_seal_bundle_digest_tamper(self):
        (self.root/'evidence').write_text('evidence');seal.seal_evidence(self.root)
        f=self.root/'EVIDENCE_BUNDLE.json';data=p.read(f);data['evidence_bundle_sha256']='0'*64;p.dump(f,data)
        self.assertFalse(seal.seal_check(self.root)['ok'])


    def test_invalid_judge_stays_in_denominator(self):
        self.prepare();self.execute('solver')
        def bad_call(c,body):
            return {'status':'ok','request':body,'content':'{"correct":"yes"}','finish_reason':'length'}
        with patch.object(p,'call',bad_call):self.execute('judge')
        report=p.summary(argparse.Namespace(plan=str(self.plan),responses=str(self.root/'solver'),grades=str(self.root/'judge'),output=str(self.root/'report')))
        self.assertEqual(report['tracks']['gold']['total'],2)
        self.assertEqual(report['tracks']['gold']['accuracy'],0)
        self.assertEqual(report['tracks']['gold']['judge_invalid'],2)
        self.assertEqual(report['tracks']['gold']['judge_truncated'],2)

    def test_solver_http_failure_is_not_judged(self):
        self.prepare()
        with patch.object(p,'call',side_effect=lambda *a: {'status':'transport_error','error':'synthetic 500'}):self.execute('solver')
        with patch.object(p,'call') as call:
            self.execute('judge');call.assert_not_called()
        report=p.summary(argparse.Namespace(plan=str(self.plan),responses=str(self.root/'solver'),grades=str(self.root/'judge'),output=str(self.root/'report')))
        self.assertEqual(report['tracks']['gold']['solver_failures'],2)
        self.assertEqual(report['tracks']['gold']['unresolved'],2)

    def test_table_and_manifest_bind_summary(self):
        self.prepare();self.execute('solver');self.execute('judge')
        summary=self.root/'report'
        p.summary(argparse.Namespace(plan=str(self.plan),responses=str(self.root/'solver'),grades=str(self.root/'judge'),output=str(summary)))
        bundle=seal.seal_evidence(self.root)
        result=p.table(argparse.Namespace(run_dir=str(self.root),summary=str(summary/'summary.json')))
        self.assertIn(bundle['evidence_bundle_sha256'],Path(result['table']).read_text())
        seal.seal_final(self.root,result['table'])
        self.assertTrue(seal.seal_check(self.root)['ok'])
        obj=p.read(self.root/'MANIFEST.json');obj['evidence_bundle_sha256']='0'*64;p.dump(self.root/'MANIFEST.json',obj)
        self.assertFalse(seal.seal_check(self.root)['ok'])

    def test_receipt_with_already_frozen_profile(self):
        from hust_eval_hle_verified import receipt
        profile=Path(__file__).resolve().parents[1]/'examples/profile.b0_35b.json'
        import shutil
        shutil.copyfile(profile,self.root/'profile.json')
        with patch.object(receipt,'_get',return_value=b'{"data": []}'),patch.object(receipt.config_check,'verify',return_value={'ok':True}):
            result=receipt.capture(self.root,'http://127.0.0.1',profile=str(self.root/'profile.json'),with_metrics=False)
        self.assertTrue(result['effective']['ok'])

if __name__=='__main__':unittest.main()

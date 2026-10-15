import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from hust_eval_hle_verified.bench_inputs import materialize_sealed, validate_input, write
from hust_eval_hle_verified.bench import bench, build_command
from hust_eval_hle_verified.hashing import sha256_file
from hust_eval_hle_verified.seal import seal_evidence, seal_final


class MultimodalBenchTests(unittest.TestCase):
    def source(self, root):
        run = root/'accuracy'
        (run/'plan').mkdir(parents=True)
        image = 'data:image/png;base64,'+base64.b64encode(b'image-test-bytes').decode()
        tasks = [{'case_id': 'gold-'+str(i), 'track': 'gold', 'row_index': i,
                  'problem': 'question '+str(i), 'image': image if i == 4 else ''} for i in range(5)]
        write(run/'plan/tasks.json', tasks)
        write(run/'plan/contract.json', {'tasks_sha256': sha256_file(run/'plan/tasks.json')})
        (run/'plan/contract.sha256').write_text(sha256_file(run/'plan/contract.json')+'\n')
        write(run/'source.json', {'git_commit': 'test'})
        seal_evidence(run)
        (run/'results').mkdir()
        (run/'results/table.md').write_text('test')
        seal_final(run, run/'results/table.md')
        return run, image

    def test_export_selection_image_bytes_and_frozen_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source, image = self.source(root)
            m = materialize_sealed(source, root/'text', 'text', 2)
            self.assertEqual([c['case_id'] for c in m['cases']], ['gold-0', 'gold-2'])
            m = materialize_sealed(source, root/'image', 'image')
            self.assertEqual(m['cases'][0]['image']['sha256'], hashlib.sha256(b'image-test-bytes').hexdigest())
            row = json.loads((root/'image/prompts.jsonl').read_text())
            self.assertEqual(row['content'][1]['image_url']['url'], image)
            self.assertNotIn('answer', row)
            self.assertEqual(validate_input(root/'image/prompts.jsonl', 'image', root/'image/prompts.jsonl.manifest.json'), 1)
            result = bench(root/'dry', 'img', str(root/'image/prompts.jsonl'), 'http://localhost', 'm', 't', 1, 256,
                           dry_run=True, modality='image', input_manifest=root/'image/prompts.jsonl.manifest.json')
            self.assertIn('custom_image', result['command'])
            self.assertFalse((root/'dry/.active.lock').exists())
            m['cases'][0]['image']['sha256'] = 'wrong'
            (root/'image/prompts.jsonl.manifest.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):
                validate_input(root/'image/prompts.jsonl', 'image', root/'image/prompts.jsonl.manifest.json')

    def test_reject_changed_source_and_write_into_seal(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source, _ = self.source(root)
            with self.assertRaises(ValueError): materialize_sealed(source, source/'export', 'text')
            (source/'plan/tasks.json').write_text('[]')
            with self.assertRaises(ValueError): materialize_sealed(source, root/'export', 'text')

    def test_request_semantics_equal_across_modalities(self):
        for mode in ('text', 'image'):
            cmd = build_command('vllm', 'http://localhost', 'm', 't', 'd', 2, 256, 'r', 'name', mode)
            self.assertIn('--skip-chat-template', cmd)
            self.assertIn('--no-oversample', cmd)
            self.assertNotIn('--max-concurrency', cmd)
            body = json.loads(cmd[cmd.index('--extra-body')+1])
            self.assertFalse(body['chat_template_kwargs']['enable_thinking'])
            self.assertFalse(body['ignore_eos'])
            self.assertEqual(body['seed'], 0)

    def test_images_cannot_be_silently_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'bad.jsonl'; p.write_text('{"prompt":"image question","image_files":["x"]}\n')
            for mode in ('text', 'image'):
                with self.assertRaises(ValueError): validate_input(p, mode)

"""Source-only regression checks; never import torch/vLLM or load a model."""
import ast
import copy
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('compat', HERE / 'vllm-t4-compat.py')
compat = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compat)
SOURCE = HERE / 'runtime/vllm-wheel-source/vllm/attention/ops/prefix_prefill.py'


class Checks(unittest.TestCase):
    def test_only_query_tile_expression_changes(self):
        original = SOURCE.read_bytes()
        patched = compat.patched_bytes(original)
        before, after = ast.parse(original), ast.parse(patched)
        changes = 0
        for node in ast.walk(after):
            if isinstance(node, ast.keyword) and node.arg == 'BLOCK_M' and isinstance(node.value, ast.IfExp):
                expression = ast.Expression(copy.deepcopy(node.value))
                self.assertEqual(eval(compile(expression, '<tile>', 'eval'), {'IS_TURING': True}), 64)
                self.assertEqual(eval(compile(expression, '<tile>', 'eval'), {'IS_TURING': False}), 128)
                node.value = ast.Constant(value=128)
                changes += 1
        self.assertEqual(changes, 1)
        self.assertEqual(ast.dump(before), ast.dump(after))
        self.assertIn(b'triton.cdiv(max_input_len, META["BLOCK_M"])', patched)

    def test_wrong_source_rejected_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'prefix.py'
            source.write_bytes(SOURCE.read_bytes() + b'\n')
            original = source.read_bytes()
            with self.assertRaises(RuntimeError):
                compat.apply(source, Path(directory) / 'evidence')
            self.assertEqual(source.read_bytes(), original)

    def test_backup_diff_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            source, evidence = Path(directory) / 'prefix.py', Path(directory) / 'evidence'
            source.write_bytes(SOURCE.read_bytes())
            first = compat.apply(source, evidence)
            second = compat.apply(source, evidence)
            self.assertEqual(first, second)
            self.assertEqual((evidence / 'prefix-prefill.original.py').read_bytes(), SOURCE.read_bytes())
            self.assertEqual(source.read_bytes(), compat.patched_bytes(SOURCE.read_bytes()))
            self.assertEqual((evidence / 'vllm-t4-prefix.patch').read_text().count('\n-        BLOCK_M=128,'), 1)

    def test_gpu_helper_import_preserves_allowlisted_package(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'fixed-package'
            package.mkdir()
            source = package / 'vllm-t4-compat.py'
            source.write_bytes((HERE / 'vllm-t4-compat.py').read_bytes())
            program = '''import importlib.util, runpy, sys
from pathlib import Path
runpy.run_path(sys.argv[1], run_name='source_only_test')
source = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location('compat', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert {p.name for p in source.parent.iterdir()} == {source.name}
'''
            old_helper = Path(directory) / 'old-helper.py'
            old_helper.write_text((HERE / 'verify-t4-prefix-kernel.py').read_text().replace('sys.dont_write_bytecode = True', 'sys.dont_write_bytecode = False'))
            old_package = Path(directory) / 'old-package'
            old_package.mkdir()
            old_source = old_package / source.name
            old_source.write_bytes(source.read_bytes())
            failed = subprocess.run([sys.executable, '-c', program, str(old_helper), str(old_source)], capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertTrue((old_package / '__pycache__').is_dir())
            subprocess.run([sys.executable, '-c', program, str(HERE / 'verify-t4-prefix-kernel.py'), str(source)], check=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)

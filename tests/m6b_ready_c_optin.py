"""ADAPTATION CPU contract tests; mocked results are not native-fit evidence."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flash.rbeast_adapter import RbeastAdapter, CANDIDATE_C_SHA256, worker


class Tests(unittest.TestCase):
    def test_explicit_command_and_rollback(self):
        for adapter,exe,flags in [(RbeastAdapter(),sys.executable,[]),
                (RbeastAdapter(candidate_c_python='/isolated/bin/python'),'/isolated/bin/python',['--candidate-c']),
                (RbeastAdapter(),sys.executable,[])]:
            with patch('flash.rbeast_adapter.subprocess.run',return_value=SimpleNamespace(returncode=77,stdout='',stderr='')) as run:
                self.assertEqual(adapter.analyze([1]*8)['status'],'BLOCKED')
                self.assertEqual(run.call_args.args[0],[exe,str(Path(__file__).resolve().parents[1]/'flash/rbeast_adapter.py'),'--worker']+flags)
                self.assertEqual(run.call_args.kwargs['timeout'],30)

    def test_relative_interpreter_rejected(self):
        for value in ('','python','./bin/python'):
            with self.assertRaises(ValueError):RbeastAdapter(candidate_c_python=value)

    def test_identity_failure_propagated(self):
        payload=dict(status='BLOCKED',reason='CANDIDATE_C_IDENTITY_REJECTED',native_fit_started=False,raw=None)
        with patch('flash.rbeast_adapter.subprocess.run',return_value=SimpleNamespace(returncode=78,stdout='M5_RESULT='+json.dumps(payload),stderr='')):
            result=RbeastAdapter(candidate_c_python='/isolated/bin/python').analyze([1]*8)
        self.assertEqual(result['reason'],payload['reason'])
        self.assertFalse(result['native_fit_started'])
        self.assertEqual(result['worker_exit_code'],78)

    def test_worker_rejects_before_fit(self):
        for identity in (dict(native_sha256='0'*64,mapped_library_lines=['mapped']),
                         dict(native_sha256=CANDIDATE_C_SHA256,mapped_library_lines=[])):
            np=SimpleNamespace(__version__='2.2.6')
            rb=SimpleNamespace(beast=lambda *args,**kwargs:self.fail('fit entered before identity rejection'))
            stdout=io.StringIO()
            with patch.dict(sys.modules,{'numpy':np,'Rbeast':rb}), patch('importlib.metadata.version',return_value='0.1.25'), patch('flash.rbeast_adapter.runtime_identity',return_value=identity), patch('sys.stdin',io.StringIO('invalid input proves identity checked first')), contextlib.redirect_stdout(stdout):
                self.assertEqual(worker(candidate_c=True),78)
            payload=json.loads(stdout.getvalue().removeprefix('M5_RESULT='))
            self.assertFalse(payload['native_fit_started'])

    def test_timeout_and_missing_interpreter(self):
        for error,reason in [(subprocess.TimeoutExpired(['worker'],30),'NATIVE_TIMEOUT'),(FileNotFoundError('missing'),'FileNotFoundError: missing')]:
            with patch('flash.rbeast_adapter.subprocess.run',side_effect=error):
                result=RbeastAdapter(candidate_c_python='/missing/python').analyze([1]*8)
            self.assertEqual(result['status'],'INSUFFICIENT_EVIDENCE')
            self.assertEqual(result['reason'],reason)

    def test_default_identity_observation_does_not_gate_fit(self):
        np=SimpleNamespace(__version__='2.2.6',float64=float,asarray=lambda values,dtype:values)
        from unittest.mock import Mock
        rb=SimpleNamespace(beast=Mock(return_value={'real_default_result':True}))
        stdout=io.StringIO()
        with patch.dict(sys.modules,{'numpy':np,'Rbeast':rb}), patch('importlib.metadata.version',return_value='0.1.25'), patch('flash.rbeast_adapter.runtime_identity',side_effect=OSError('identity unavailable')), patch('sys.stdin',io.StringIO('[1,2,3]')), contextlib.redirect_stdout(stdout):
            self.assertEqual(worker(),0)
        rb.beast.assert_called_once()
        payload=json.loads(stdout.getvalue().removeprefix('M5_RESULT='))
        self.assertTrue(payload['native_fit_started'])
        self.assertEqual(payload['runtime_identity_error'],'identity unavailable')

    def test_bad_worker_output(self):
        for code,stdout in [(1,''),(0,''),(0,'M5_RESULT={}\nM5_RESULT={}')]:
            with patch('flash.rbeast_adapter.subprocess.run',return_value=SimpleNamespace(returncode=code,stdout=stdout,stderr='failure')):
                result=RbeastAdapter(candidate_c_python='/isolated/bin/python').analyze([1]*8)
            self.assertEqual(result['reason'],'NATIVE_WORKER_FAILED')

if __name__=='__main__':unittest.main()

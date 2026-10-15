"""
nvmeof gateways get a key of the previous type (aes): the gateway images of
this release carry a librados from before aes256k and cannot connect with
an aes256k key.
"""
import base64
import struct
from unittest.mock import MagicMock

from ceph.deployment.service_spec import NvmeofServiceSpec

from cephadm import utils
from cephadm.services.cephadmservice import CephadmDaemonDeploySpec
from cephadm.services.nvmeof import NvmeofService


def keyring(entity: str, key_type: int) -> str:
    raw = struct.pack('<H', key_type) + b'\0' * 8 + \
        struct.pack('<H', 16 if key_type == 1 else 32) + \
        b'k' * (16 if key_type == 1 else 32)
    return f'[{entity}]\n\tkey = {base64.b64encode(raw).decode()}\n'


def test_key_type_for():
    assert utils.key_type_for('nvmeof') == 'aes'
    for t in ('osd', 'mds', 'mgr', 'mon', 'crash', 'rgw'):
        assert utils.key_type_for(t) == utils.ROTATION_CIPHER == 'aes256k'


def test_keyring_key_type():
    assert utils.keyring_key_type(keyring('client.x', 1)) == 'aes'
    assert utils.keyring_key_type(keyring('client.x', 2)) == 'aes256k'
    assert utils.keyring_key_type('') is None
    assert utils.keyring_key_type('[client.x]\n\tkey = !!!\n') is None


def test_key_rotate_keeps_nvmeof_on_the_legacy_type():
    from cephadm.module import CephadmOrchestrator
    mgr = MagicMock()
    mgr.mon_command.return_value = (0, '', '')
    for daemon_type, want in (('nvmeof', 'aes'), ('osd', 'aes256k')):
        spec = CephadmDaemonDeploySpec(host='h', daemon_id='a.b',
                                       service_name=f'{daemon_type}.a',
                                       daemon_type=daemon_type)
        CephadmOrchestrator.key_rotate(mgr, spec)
        assert mgr.mon_command.call_args[0][0]['key_type'] == want


def _service(keyrings):
    mgr = MagicMock()
    spec = NvmeofServiceSpec(service_id='a', pool='p')
    mgr.spec_store.__getitem__.return_value.spec = spec
    mgr.inventory.get_addr.return_value = '10.0.0.1'
    mgr.mon_command.return_value = (0, '', '')
    svc = NvmeofService(mgr)
    svc.get_keyring_with_caps = MagicMock(side_effect=keyrings)
    return mgr, svc


def _deploy(svc):
    ds = CephadmDaemonDeploySpec(host='h', daemon_id='a.h.xyz',
                                 service_name='nvmeof.a', daemon_type='nvmeof')
    try:
        svc.prepare_create(ds)
    except Exception:
        # past the keyring, prepare_create renders the gateway config from
        # the mocked mgr; only the key handling is under test here
        pass


def test_new_gateway_key_is_legacy():
    mgr, svc = _service([keyring('client.nvmeof.a.h.xyz', 1)])
    _deploy(svc)
    assert svc.get_keyring_with_caps.call_args.kwargs['key_type'] == 'aes'
    assert not any(c[0][0].get('prefix') == 'auth rotate'
                   for c in mgr.mon_command.call_args_list)


def test_gateway_with_an_aes256k_key_is_rotated_back():
    entity = 'client.nvmeof.a.h.xyz'
    mgr, svc = _service([keyring(entity, 2), keyring(entity, 1)])
    _deploy(svc)
    rot = [c[0][0] for c in mgr.mon_command.call_args_list
           if c[0][0].get('prefix') == 'auth rotate']
    assert rot == [{'prefix': 'auth rotate', 'entity': entity,
                    'format': 'json', 'key_type': 'aes'}]
    assert svc.get_keyring_with_caps.call_count == 2

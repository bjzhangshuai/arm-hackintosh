"""Build unsigned local-routing metadata from unchanged downloaded Apple metadata.

This does not generate an Apple manifest/signature/ticket, change device support,
or modify the payload. Apple's later package/content checks remain required.
"""
from copy import deepcopy
import os
from pathlib import Path
import platform
import plistlib


def local_catalog(info):
    if info.get('CFBundleIdentifier') != 'com.apple.MobileAsset.MacSoftwareUpdate':
        raise ValueError('not a macOS update asset')
    props = info.get('MobileAssetProperties')
    if not isinstance(props, dict):
        raise ValueError('asset properties absent')
    if props.get('Build') != '25G83' or props.get('OSVersion') != '26.6.2':
        raise ValueError('wrong downloaded product version')
    if 'VMA2MACOSAP' not in props.get('SupportedDeviceModels', []):
        raise ValueError('asset does not list this virtual Mac model')
    if props.get('ContainsSFRContent') is not True:
        raise ValueError('local SFR content not advertised')
    # Do not accidentally introduce a second remote package source.
    if any(key in props for key in ('__BaseURL', '__RelativePath', 'URL')):
        raise ValueError('unexpected external asset locator')
    return {'Assets': [deepcopy(props)]}


def main():
    if (platform.system() != 'Linux' or platform.machine() != 'x86_64'
            or platform.node() != 'macvm-validation'
            or os.environ.get('MACVM_DEBUG_ENV_CONFIRMED') != 'YES'):
        raise RuntimeError('isolated Linux guard required')
    source = Path('/home/macvm/installation-data/install-analysis/boot120-local-product-25G83-Info.plist')
    target = Path('/home/macvm/installation-data/guest-install-control')
    info = plistlib.loads(source.read_bytes())
    products = {
        'boot120-local-catalog.plist': local_catalog(info),
        # The matching constructor derives OS/payload identity from UpdateBrain
        # and UpdateBundle. This optional descriptor supplies no extra packages.
        'boot120-local-InstallInfo.plist': {},
    }
    if any((target / name).exists() for name in products):
        raise RuntimeError('never overwrite a staged local configuration')
    for name, data in products.items():
        with (target / name).open('xb') as stream:
            plistlib.dump(data, stream, fmt=plistlib.FMT_XML)
    print('MACVM_BOOT120_LOCAL_METADATA_READY build=25G83 model=VMA2MACOSAP remote_payload_urls=0')


if __name__ == '__main__':
    main()

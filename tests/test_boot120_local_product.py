from copy import deepcopy
import unittest
from tools.build_boot120_local_product_metadata import local_catalog


class LocalProductTests(unittest.TestCase):
    def setUp(self):
        self.info = {'CFBundleIdentifier': 'com.apple.MobileAsset.MacSoftwareUpdate',
                     'MobileAssetProperties': {'Build': '25G83', 'OSVersion': '26.6.2',
                        'SupportedDeviceModels': ['VMA2MACOSAP'], 'ContainsSFRContent': True}}

    def test_properties_preserved_without_mutating_source(self):
        original = deepcopy(self.info)
        result = local_catalog(self.info)
        self.assertEqual(result['Assets'], [original['MobileAssetProperties']])
        result['Assets'][0]['SupportedDeviceModels'].append('test-only')
        self.assertEqual(self.info, original)

    def test_wrong_asset_type(self):
        self.info['CFBundleIdentifier'] = 'unrelated'
        with self.assertRaises(ValueError): local_catalog(self.info)

    def test_missing_properties(self):
        del self.info['MobileAssetProperties']
        with self.assertRaises(ValueError): local_catalog(self.info)

    def test_wrong_versions(self):
        for key, value in [('Build', '25G72'), ('OSVersion', '27.0')]:
            changed = deepcopy(self.info)
            changed['MobileAssetProperties'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): local_catalog(changed)

    def test_does_not_invent_device_support(self):
        self.info['MobileAssetProperties']['SupportedDeviceModels'] = ['J160AP']
        with self.assertRaises(ValueError): local_catalog(self.info)

    def test_missing_local_sfr_rejected(self):
        self.info['MobileAssetProperties']['ContainsSFRContent'] = False
        with self.assertRaises(ValueError): local_catalog(self.info)

    def test_remote_locators_rejected(self):
        for key in ['__BaseURL', '__RelativePath', 'URL']:
            changed = deepcopy(self.info)
            changed['MobileAssetProperties'][key] = 'https://invalid.example/product.zip'
            with self.subTest(key=key), self.assertRaises(ValueError): local_catalog(changed)


if __name__ == '__main__': unittest.main()

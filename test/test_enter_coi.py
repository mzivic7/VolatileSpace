import unittest
import numpy as np


from volatilespace.physics.orbit_intersect_debug import predict_enter_coi


def compare(a, b):
    """Compares 2 values and returns percentage difference"""
    if a == b:
        return 0.0
    elif 0 in (a, b):
        return 100.0
    elif a > 0 and b > 0:
        return abs(a - b) / max(a, b) * 100
    elif a < 0 and b < 0:
        a = abs(a)
        b = abs(b)
        return abs(a - b) / max(a, b) * 100
    else:   # skipping negative
        return 100


class TestEnterCOI(unittest.TestCase):

    def test_ell_cir_cc_cc_front_1(self):
        """Testing case from ell_cir_cc_cc_front_1.ini"""
        vessel_data = (
            0.7848720504761658,
            5.792703785429235,
            5.052894377513411,
            4.155140632859112,
            0.0,
            300.474848502583,
            186.1916018303689,
            235.83431046073758,
            1463.5482795169676,
            682.376786025227,
            1.0
        )
        body_data = (
            0.0542305694443186,
            5.692060439783578,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            0.0,
            1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -124.72164445074682,
            -200.15577282704854
        )
        hint_ma = np.nan
        expected_result = [2.69872535, 0.77398723, 2.36238264, 0.73608049, 664.52033938]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cc_cc_front_2(self):
        """Testing case from ell_cir_cc_cc_front_2.ini"""
        vessel_data = (
            0.6008720504761658,
            5.792703785429235,
            5.288975731201161,
            4.155140632859112,
            0.0,
            300.474848502583,
            240.1831335461591,
            180.5469383362623,
            1463.5482795169676,
            682.376786025227,
            1.0
        )
        body_data = (
            0.0542305694443186,
            5.692060439783578,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            0.0,
            1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -95.48276078172731,
            -153.23263143370454
        )
        hint_ma = np.nan
        expected_result = [2.24094719e+00, 4.85828094e-01, 1.77002695e+00, 4.60505629e-01, 5.26542371e+02]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cc_cc_front_3(self):
        """Testing case from ell_cir_cc_cc_front_3.ini"""
        vessel_data = (
            0.5947403407220562,
            0.33615483255680795,
            0.7349643268603749,
            5.816409142227941,
            0.0,
            500.66551264659745,
            402.49394796688745,
            297.7659775792203,
            3147.867049201737,
            682.376786025227,
            1.0
        )
        body_data = (
            0.05142305694443186,
            0.9986766764331892,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.79871362007106,
            25.735226460979458,
            0.0,
            1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            265.91207004888776,
            -133.99756865713707
        )
        hint_ma = np.nan
        expected_result = [1.33446605, 1.47019993, 0.75625727, 1.41903685, 210.47073382]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cc_cc_back(self):
        """Testing case from ell_cir_cc_cc_back.ini"""
        vessel_data = (
            0.4947403407220562,
            6.186702952265563,
            6.09334387990604,
            5.816409142227941,
            0.0,
            570.6655126465974,
            495.93164095912755,
            282.3312501651045,
            3830.6044359516877,
            682.376786025227,
            1.0
        )
        body_data = (
            0.05142305694443186,
            0.2824225835089252,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.79871362007106,
            25.735226460979458,
            0.0,
            1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            252.12849292333814,
            -127.05179210069038
        )
        hint_ma = np.nan
        expected_result = [0.88085131, 1.05249803, 0.49926748, 1.0078287, 363.20462315]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cw_cw_front(self):
        """Testing case from ell_cir_cw_cw_front.ini"""
        vessel_data = (
            0.6548720504761658,
            5.069106150672166,
            4.438622001025442,
            4.155140632859112,
            0.0,
            300.474848502583,
            227.080792410182,
            196.77258015540178,
            1463.5482795169676,
            682.376786025227,
            -1.0
        )
        body_data = (
            0.0542305694443186,
            1.995298498507102,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            0.0,
            -1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -104.06373751067869,
            -167.00355336435985
        )
        hint_ma = np.nan
        expected_result = [3.65440535, 1.54083435, 3.97570527, 1.48662812, 254.68689769]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cw_cw_back(self):
        """Testing case from ell_cir_cw_cw_back.ini"""
        vessel_data = (
            0.6548720504761658,
            5.069106150672166,
            4.438622001025442,
            2.155140632859112,
            0.0,
            300.474848502583,
            227.080792410182,
            196.77258015540178,
            1463.5482795169676,
            682.376786025227,
            -1.0
        )
        body_data = (
            1e-07,
            2.105298498507102,
            0.0,
            3.737838350399759,
            0.001997238120388435,
            500.4608436404148,
            500.4608436404123,
            5.004608436404148e-05,
            0.0,
            -1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -108.5501061806167,
            164.12288916903353
        )
        hint_ma = np.nan
        expected_result = [1000]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_ell_cc_cc_ap_1(self):
        """Testing case from ell_ell_cc_cc_ap_1.ini"""
        vessel_data = (
            0.142305694443186,
            5.902629254752289,
            5.841842855658451,
            6.137838350399759,
            0.0,
            500.4608436404148,
            495.3675317835397,
            71.21842789587195,
            3145.9370032240295,
            682.376786025227,
            1.0
        )
        body_data = (
            0.7848720504761658,
            5.792703785429235,
            0.0,
            4.155140632859112,
            0.004293117893762481,
            300.474848502583,
            186.1916018303689,
            235.83431046073758,
            0.0,
            1.0,
            59.95261418131872
        )
        vessel_orbit_center = (
            70.46748040140535,
            -10.314973477283674
        )
        hint_ma = np.nan
        expected_result = [0.53970815, 2.03298226, 0.4665793, 1.33045905, 424.15340419]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_ell_cc_cc_ap_2(self):
        """Testing case from ell_ell_cc_cc_ap_2.ini"""
        vessel_data = (
            0.0542305694443186,
            5.692060439783578,
            5.6604290383119045,
            6.137838350399759,
            0.0,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            3145.9370032240295,
            682.376786025227,
            1.0
        )
        body_data = (
            0.6008720504761658,
            5.792703785429235,
            0.0,
            4.155140632859112,
            0.004293117893762481,
            300.474848502583,
            240.1831335461591,
            180.5469383362623,
            0.0,
            1.0,
            59.95261418131872
        )
        vessel_orbit_center = (
            26.85410168881374,
            -3.9308819486451823
        )
        hint_ma = np.nan
        expected_result = [0.71692278, 2.56977628, 0.6812896, 2.24460814, 637.08701408]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_ell_cc_cc_pe(self):
        """Testing case from ell_ell_cc_cc_pe.ini"""
        vessel_data = (
            0.7248720504761658,
            5.792703785429235,
            5.130179760374571,
            4.155140632859112,
            0.0,
            300.474848502583,
            206.99217268425696,
            217.80581955058258,
            1463.5482795169676,
            682.376786025227,
            1.0
        )
        body_data = (
            0.4042305694443186,
            5.692060439783578,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            457.75007379654517,
            202.30157180934899,
            0.0,
            1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -115.18722586302306,
            -184.85474845965373
        )
        hint_ma = np.nan
        expected_result = [1.53077389e+00, 2.05552577e-02, 8.06482314e-01, 1.22467793e-02, 3.02103009e+02]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_ell_cw_cw_ap(self):
        """Testing case from ell_ell_cw_cw_ap.ini"""
        vessel_data = (
            0.0542305694443186,
            1.995298498507102,
            2.043580194630821,
            6.137838350399759,
            0.0,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            3145.9370032240295,
            682.376786025227,
            -1.0
        )
        body_data = (
            0.6548720504761658,
            5.069106150672166,
            0.0,
            4.155140632859112,
            0.004293117893762481,
            300.474848502583,
            227.080792410182,
            196.77258015540178,
            0.0,
            -1.0,
            59.95261418131872
        )
        vessel_orbit_center = (
            26.85410168881374,
            -3.9308819486451823
        )
        hint_ma = np.nan
        expected_result = [1.3404741, 3.3881921, 1.2876756, 3.54805141, 354.30071477]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cc_cw(self):
        """Testing case from ell_cir_cc_cw.ini"""
        vessel_data = (
            0.7848720504761658,
            0.992583440886423,
            1.7630022581148967,
            4.155140632859112,
            0.0,
            300.474848502583,
            186.1916018303689,
            235.83431046073758,
            1463.5482795169676,
            682.376786025227,
            1.0
        )
        body_data = (
            0.0542305694443186,
            2.0750622037600603,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            0.0,
            -1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -124.72164445074682,
            -200.15577282704854
        )
        hint_ma = np.nan
        expected_result = [3.00824047, 1.2371284, 2.90365525, 1.18588879, 445.20150498]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cw_cc_1(self):
        """Testing case from ell_cir_cw_cc_1.ini"""
        vessel_data = (
            0.7848720504761658,
            5.784117549641709,
            5.041325229594321,
            4.155140632859112,
            0.0,
            300.474848502583,
            186.1916018303689,
            235.83431046073758,
            1463.5482795169676,
            682.376786025227,
            -1.0
        )
        body_data = (
            0.0542305694443186,
            5.692060439783578,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            0.0,
            1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -124.72164445074682,
            -200.15577282704854
        )
        hint_ma = np.nan
        expected_result = [2.91728537, 0.86507371, 2.74282216, 0.82379649, 708.43898914]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_cir_cw_cc_2(self):
        """Testing case from ell_cir_cw_cc.ini"""
        vessel_data = (
            0.7848720504761658,
            3.0665739228900817,
            3.09955689747222,
            4.155140632859112,
            0.0,
            300.474848502583,
            186.1916018303689,
            235.83431046073758,
            1463.5482795169676,
            682.376786025227,
            -1.0
        )
        body_data = (
            0.0542305694443186,
            0.6731268628099034,
            0.0,
            6.137838350399759,
            0.001997238120388435,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            0.0,
            1.0,
            99.85506614332527
        )
        vessel_orbit_center = (
            -124.72164445074682,
            -200.15577282704854
        )
        hint_ma = np.nan
        expected_result = [1000]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")

    def test_ell_ell_cc_cw(self):
        """Testing case from ell_ell_cc_cw.ini"""
        vessel_data = (
            0.0542305694443186,
            5.692060439783578,
            5.6604290383119045,
            6.137838350399759,
            0.0,
            500.4608436404148,
            499.7243854434846,
            27.14027653520379,
            3145.9370032240295,
            682.376786025227,
            1.0
        )
        body_data = (
            0.6008720504761658,
            5.784117549641709,
            0.0,
            4.155140632859112,
            0.004293117893762481,
            300.474848502583,
            240.1831335461591,
            180.5469383362623,
            0.0,
            -1.0,
            59.95261418131872
        )
        vessel_orbit_center = (
            26.85410168881374,
            -3.9308819486451823
        )
        hint_ma = np.nan
        expected_result = [1000]
        result = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, hint_ma)
        diff = compare(result[0], expected_result[0])
        self.assertLess(diff, 1, "Vessel Ea error is greater than 1%")


if __name__ == '__main__':
    unittest.main()

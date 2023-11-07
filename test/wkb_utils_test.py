import logging
import unittest

from mtkgpkg2svg.wkb_utils import (
    parse_wkb,
    parse_gpkgblob,
    WKBPointZ,
    WKBPoint,
    WKBLineStringZ,
    WKBPolygonZ,
    WKBLinearRingZ,
)

logging.basicConfig(level=logging.DEBUG)


class WKBUtilsUtilsTestCase(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(
            WKBPoint(x=2.0, y=4.0),
            parse_wkb(bytes.fromhex("000000000140000000000000004010000000000000"), 0),
        )

    def test_parse_gpkgblob(self):
        self.assertEqual(
            WKBPolygonZ(
                rings=[
                    WKBLinearRingZ(
                        points=[
                            WKBPointZ(x=416048.232, y=6644631.735, z=0.001),
                            WKBPointZ(x=417982.351, y=6644480.951, z=0.001),
                            WKBPointZ(x=419863.508, y=6644334.295, z=0.001),
                            WKBPointZ(x=420778.14, y=6644262.616, z=0.001),
                            WKBPointZ(x=420778.519, y=6644262.586, z=0.001),
                            WKBPointZ(x=420996.099, y=6644301.629, z=0.001),
                            WKBPointZ(x=422889.834, y=6644641.448, z=0.001),
                            WKBPointZ(x=429859.455, y=6646079.141, z=0.001),
                            WKBPointZ(x=435334.249, y=6647208.615, z=0.001),
                            WKBPointZ(x=439855.394, y=6648141.348, z=0.001),
                            WKBPointZ(x=445150.626, y=6649234.044, z=0.001),
                            WKBPointZ(x=447262.983, y=6651875.334, z=0.001),
                            WKBPointZ(x=448432.298, y=6653337.445, z=0.001),
                            WKBPointZ(x=448432.691, y=6653337.936, z=0.001),
                            WKBPointZ(x=449851.278, y=6653919.157, z=0.001),
                            WKBPointZ(x=454792.645, y=6655944.768, z=0.001),
                            WKBPointZ(x=459410.057, y=6656612.675, z=0.001),
                            WKBPointZ(x=460637.304, y=6656790.195, z=0.001),
                            WKBPointZ(x=460725.508, y=6656799.214, z=0.001),
                            WKBPointZ(x=463149.878, y=6651029.029, z=0.001),
                            WKBPointZ(x=455977.653, y=6649993.828, z=0.001),
                            WKBPointZ(x=451582.315, y=6648192.516, z=0.001),
                            WKBPointZ(x=442186.532, y=6636444.738, z=0.001),
                            WKBPointZ(x=413756.023, y=6638667.794, z=0.001),
                            WKBPointZ(x=397559.681, y=6640379.891, z=0.0),
                            WKBPointZ(x=397119.091, y=6646433.217, z=0.001),
                            WKBPointZ(x=397234.152, y=6646450.84, z=0.001),
                            WKBPointZ(x=397725.005, y=6646526.022, z=0.001),
                            WKBPointZ(x=406641.326, y=6645584.167, z=0.001),
                            WKBPointZ(x=414559.187, y=6644747.822, z=0.001),
                            WKBPointZ(x=416048.232, y=6644631.735, z=0.001),
                        ]
                    )
                ]
            ),
            parse_gpkgblob(
                bytes.fromhex(
                    "47500005fb0b0000a01a2f5dfc3c1841986e1283b7441c415a643b2fe75059410e2db2cdc76459410000000000000000fca9f1d24d62503f01eb030000010000001f000000736891edc0641941713d0aefe5585941fca9f1d24d62503f448b6c67f98219411b2fdd3cc0585941fca9f1d24d62503fe92631085ea01941ae47e1929b585941fca9f1d24d62503ff6285c8fa8ae1941448b6ca789585941fca9f1d24d62503f6abc7413aaae1941250681a589585941fca9f1d24d62503f8941606510b219413789416893585941fca9f1d24d62503f93180456a7cf19413108ac5ce8585941fca9f1d24d62503f1f85ebd18d3c1a41dd2406c94f5a5941fca9f1d24d62503f23dbf9fe18921a41f6285c276a5b5941fca9f1d24d62503f6abc7493bdd81a41cba14556535c5941fca9f1d24d62503fdd2406817a2b1b4160e5d082645d5941fca9f1d24d62503f508d97ee7b4c1b41894160d5f85f5941fca9f1d24d62503f79e92631c15e1b4148e17a5c66615941fca9f1d24d62503f068195c3c25e1b418b6ce77b66615941fca9f1d24d62503f3108ac1ced741b41ba490ccaf7615941fca9f1d24d62503f48e17a9422c21b4179e92631f2635941fca9f1d24d62503f3f355e3a480a1c413333332b99645941fca9f1d24d62503fa8c64b37751d1c4148e17a8cc5645941fca9f1d24d62503fe9263108d61e1c410e2db2cdc7645941fca9f1d24d62503f986e1283b7441c41d122db41255f5941fca9f1d24d62503f3108ac9ca6d41b41b6f3fd74225e5941fca9f1d24d62503f295c8f42f98f1b41dd240621605c5941fca9f1d24d62503fa69bc4202afd1a415a643b2fe7505941fca9f1d24d62503fdf4f8d17f040194160e5d0f212535941fca9f1d24d62503f621058b9de431841dd2406f9be5459410000000000000000a01a2f5dfc3c1841f853e34da85a5941fca9f1d24d62503f54e3a59bc83e18415c8fc2b5ac5a5941fca9f1d24d62503f52b81e0574461841b0726881bf5a5941fca9f1d24d62503faaf1d24dc5d11841c520b00ad4595941fca9f1d24d62503f91ed7cbf7c4d1941e3a59bf402595941fca9f1d24d62503f736891edc0641941713d0aefe5585941fca9f1d24d62503f"
                )
            ),
        )
        self.assertEqual(
            WKBPointZ(x=242763.463, y=6968745.822, z=81.26),
            parse_gpkgblob(
                bytes.fromhex(
                    "47500001FB0B000001E9030000105839B45BA20D41E3A59B746A955A41713D0AD7A3505440"
                )
            ),
        )

        self.assertEqual(
            WKBLineStringZ(
                points=[
                    WKBPointZ(x=354567.334, y=6651799.415, z=13.436),
                    WKBPointZ(x=354555.325, y=6651823.991, z=14.431),
                    WKBPointZ(x=354508.565, y=6651830.167, z=9.188),
                    WKBPointZ(x=354507.053, y=6651830.367, z=8.951),
                    WKBPointZ(x=354459.318, y=6651836.003, z=-0.3),
                ]
            ),
            parse_gpkgblob(
                bytes.fromhex(
                    "47500005FB0B0000C1CAA1456DA21541931804561DA41541295C8FDAE55F5941E9263100EF5F5941333333333333D3BFE9263108ACDC2C4001EA03000005000000931804561DA41541295C8FDAE55F5941AC1C5A643BDF2A40CDCCCC4CEDA31541448B6CFFEB5F5941E9263108ACDC2C40295C8F4232A31541C520B08AED5F5941C74B378941602240CBA145362CA3154191ED7C97ED5F5941F4FDD478E9E62140C1CAA1456DA21541E9263100EF5F5941333333333333D3BF"
                )
            ),
        )

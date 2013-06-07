from unittest import TestCase, main
import pbjson


class TestSpeedups(TestCase):
    def test_make_decoder(self):
        if not pbjson._has_decoder_speedups():
            return
        self.assertRaises(TypeError, pbjson.decoder.c_decoder, 1)

    def test_make_encoder(self):
        if not pbjson._has_encoder_speedups():
            return
        self.assertRaises(TypeError, pbjson.encoder.c_iterencoder)

if __name__ == '__main__':
    main()

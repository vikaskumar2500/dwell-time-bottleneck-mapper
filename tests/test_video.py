import unittest

from dwell_mapper.video import VideoError, observations_from_boxes, parse_video_source


class VideoAdapterTests(unittest.TestCase):
    def test_camera_index_and_path_parsing(self):
        self.assertEqual(parse_video_source("0"), 0)
        self.assertEqual(parse_video_source(" 2 "), 2)
        self.assertEqual(parse_video_source("clips/store.mp4"), "clips/store.mp4")
        self.assertEqual(parse_video_source("rtsp://camera/live"), "rtsp://camera/live")
        with self.assertRaises(VideoError):
            parse_video_source("  ")

    def test_boxes_become_bottom_center_points(self):
        observations = observations_from_boxes([7, 11], [[10, 20, 30, 80], [50, 10, 90, 70]])
        self.assertEqual(observations[0].track_id, "7")
        self.assertEqual(observations[0].point, (20, 80))
        self.assertEqual(observations[1].point, (70, 70))

    def test_malformed_tracking_output_is_rejected(self):
        with self.assertRaisesRegex(VideoError, "same length"):
            observations_from_boxes([1], [])
        with self.assertRaisesRegex(VideoError, "x1"):
            observations_from_boxes([1], [[0, 1, 2]])


if __name__ == "__main__":
    unittest.main()

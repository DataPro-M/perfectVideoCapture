"""Test suite for videoio."""

# import docopt
import os

from docs import config as cfg  # noqa: E402
from videoio.videoio import RedisVideoCapture

config_path = os.path.dirname(os.path.abspath(cfg.__file__))
initfile = os.path.join(config_path, "config.ini")
config, default_args = cfg.read_ini(initfile)


def test_config_file() -> None:
    """Test config file."""
    # check if the config file is read
    assert config is not None
    # check if the --src starts with rtsp://
    assert config["defaultArgs"]["--src"].startswith("rtsp://")
    # check if --width and --height are integers
    assert isinstance(int(config["defaultArgs"]["--width"]), int)
    assert isinstance(int(config["defaultArgs"]["--height"]), int)
    # check if --fps_rdg is an integer
    assert isinstance(int(config["defaultArgs"]["--fps_rdg"]), int)
    # check if --verbose is an integer and >= 0 and <= 2
    assert isinstance(int(config["defaultArgs"]["--verbose"]), int)
    assert int(config["defaultArgs"]["--verbose"]) >= 0
    assert int(config["defaultArgs"]["--verbose"]) <= 2
    # check if fps_van is an integer and > 0 and less than --fps_rdg if --fps_rdg != 0
    assert isinstance(int(config["Analysis"]["fps_van"]), int)
    assert int(config["Analysis"]["fps_van"]) > 0
    if int(config["defaultArgs"]["--fps_rdg"]) != 0:
        assert int(config["Analysis"]["fps_van"]) < int(
            config["defaultArgs"]["--fps_rdg"]
        )
    # check if rec_permit is a boolean (True or False)
    assert isinstance(eval(config["record"]["rec_permit"]), bool)
    # check if Rec_Buf_Sec (total record buffer in seconds) is an integer and > 0 and less than 60
    assert isinstance(int(config["record"]["rec_buf_sec"]), int)
    assert int(config["record"]["rec_buf_sec"]) > 0
    assert int(config["record"]["rec_buf_sec"]) < 60
    # check if Rec_Dir (recording directory) is a directory
    assert os.path.isdir(config["record"]["rec_dir"])
    # check if Rec_Dir (recording directory) is writable
    assert os.access(config["record"]["rec_dir"], os.W_OK)
    # check if Rec_Dir (recording directory) is readable
    assert os.access(config["record"]["rec_dir"], os.R_OK)
    # check vcodec (ffmpeg supported video codec) is one of the following:
    #   - h264 (H.264)
    #   - h265 (H.265)
    assert (
        config["record"]["vcodec"] == "h264" or config["Analysis"]["vcodec"] == "h265"
    )
    # check if Rec_File_Ext (opencv supported file extension) is one of the following:
    #   - avi
    #   - mp4
    assert any(
        [
            config["record"]["rec_file_ext"] == "avi",
            config["record"]["rec_file_ext"] == "mp4",
        ]
    )
    # check if pidfilepath is a path to a directory
    assert os.path.isdir(config["process"]["pidfilepath"])
    # check if PidFilePath is writable
    assert os.access(config["process"]["pidfilepath"], os.W_OK)
    # check if PidFilePath is readable
    assert os.access(config["process"]["pidfilepath"], os.R_OK)

    # check if HOST (redis host) is a valid hostname
    assert config["redis"]["host"] == "localhost"
    # check if PORT (redis port) is an integer and > 0 and less than 65536
    assert isinstance(int(config["redis"]["port"]), int)
    assert int(config["redis"]["port"]) > 0
    assert int(config["redis"]["port"]) < 65536
    # check if DB (redis db) is an integer and >= 0 and less than 16
    assert isinstance(int(config["redis"]["db"]), int)
    assert int(config["redis"]["db"]) >= 0
    assert int(config["redis"]["db"]) < 16


def test_read_write() -> None:
    """Test RedisVideoCapture read and write."""
    # create a RedisVideoCapture object
    rvc = RedisVideoCapture(config)
    # check if the object is created
    assert rvc is not None
    # check if the object is opened
    assert rvc.stream.isOpened()
    # check if the frame is read
    assert rvc.frame is not None
    # start the thread to read frames from the video stream
    rvc.start()
    # wait until the frame buffer is full
    rvc.waitOnFrameBuf()
    # get the frame from the buffer
    frame, grabbed, timestamp = rvc.read()
    # stop the thread
    rvc.stop()
    # check if capture failed
    assert rvc.capture_failed is False

__author__ = 'Eric Gallimore'

from datetime import datetime
import os
import pyaudio
import wave
from collections import deque
import math
import logging


class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'



class Recorder(object):
    '''
    Class used to record audio data from a sound card to wave files.
    Generates both timestamped continuous recordings and tagged files when triggered by an external thread.
    '''

    samples_per_audio_buffer = 32768  # Overflows occur if this is too low

    def __init__(self, output_directory='', continous_recording_seconds=600.0, triggered_recording_seconds=4.5,
                 num_channels=1, sample_rate=96000, sample_format=pyaudio.paInt24, unified_log=None):
        '''
        Instantiate a recorder object for recording audio to wave files.
        :param output_directory: Directory to save files
        :param continous_recording_seconds: Length of each continuous recording in seconds.
        A new file will be created when this interval elapses.  If set to 0, no continuous recordings will be made
        :param triggered_recording_seconds: Length of each triggered recording in seconds.
        If set to 0, no triggered recordings will be made
        :param num_channels: Number of channels to record
        :param sample_rate: Audio sample rate
        :param sample_format: Audio sample format.  One of PyAudio sample formats.
        :return:
        '''
        # Set up logging
        # Set up logging
        if unified_log is not None:
            self.log = unified_log.getLogger("recorder")
        else:
            self.log = logging.getLogger("recorder")
        self.log.setLevel(logging.INFO)

        self._num_channels = 1
        self._sample_rate = 96000
        self._sample_format = sample_format

        audio = pyaudio.PyAudio()

        self.stream = audio.open(format=self._sample_format,
                                channels=self._num_channels,
                                rate=self._sample_rate,
                                input=True,
                                input_device_index=0,
                                output=False,
                                frames_per_buffer=Recorder.samples_per_audio_buffer,
                                stream_callback=self._record_callback,
                                )

        self.output_directory = output_directory
        self.continous_recording_seconds = continous_recording_seconds
        # Figure out how many frames we will have in each continuous file
        self._samples_in_continuous_file = math.floor(self.continous_recording_seconds * self._sample_rate)

        self.triggered_recording_seconds = float(triggered_recording_seconds)
        # figure out how many buffers we will have in the ring buffer
        buffer_duration_s = float(Recorder.samples_per_audio_buffer) / self._sample_rate
        bufs_in_ring_buffer = math.ceil(self.triggered_recording_seconds * self._sample_rate / Recorder.samples_per_audio_buffer)
        triggered_actual_duration_s = bufs_in_ring_buffer * buffer_duration_s
        self._ring_buffer = deque(maxlen=bufs_in_ring_buffer)

        self._current_wave_file = None

        self.log.info("Initialized recorder")
        self.log.info(" Channels: {}".format(self._num_channels))
        self.log.info(" Sample Rate: {} Hz".format(self._sample_rate))
        self.log.info(" Samples per buffer: {}".format(Recorder.samples_per_audio_buffer))
        self.log.info(" Buffer duration: {} s".format(buffer_duration_s))
        self.log.info(" Sample format: {}".format(self._sample_format))
        self.log.info(" Continuous recording duration: {} s".format(continous_recording_seconds))
        self.log.info(" Triggered recording duration: {} s".format(triggered_actual_duration_s))



    def _record_callback(self, in_data, frame_count, time_info, status):
        '''
        Function called when new audio data is available.
        :param in_data: new buffer of data
        :param frame_count: Ignored
        :param time_info: Ignored
        :param status: Ignored
        :return: Tuple of None (would be used for playback) and paContinue
        '''
        if pyaudio.paInputOverflow & status:
            self.log.error("Input buffer overflow")
            print(color.RED + color.BOLD + "Input Buffer Overflow" + color.END + "\n")

        # append data to the ring buffer
        self._ring_buffer.append(in_data)

        # Also append directly to continuous wave file, if requested.
        self.append_to_wave_file(in_data)

        return None, pyaudio.paContinue


    def start(self):
        self.stream.start_stream()

    def stop(self):
        self.stream.stop_stream()

    def _start_wave_file(self):
        ''' Open a new wave file for writing in the specified output directory.
        Files are named using the UTC timestamp and a c_ prefix
        :return:
        '''
        # figure out the new filename
        now = datetime.utcnow()
        file_name = "c_{0}.wav".format(now.strftime("%Y%m%dT%H%M%SZ"))
        file_path = os.path.join(self.output_directory, file_name)

        self._current_wave_file = wave.open(file_path, mode='wb')
        self._current_wave_file.setnchannels(self._num_channels)
        self._current_wave_file.setsampwidth(pyaudio.get_sample_size(self._sample_format))
        self._current_wave_file.setframerate(self._sample_rate)

        self.log.info("Starting continuous recording: " + file_name)


    def append_to_wave_file(self, data):
        # See if we should save anything
        if self.continous_recording_seconds <= 0:
            return

        # See if we need to start a new file
        if self._current_wave_file is None:
            self._start_wave_file()

        # Append data to the current wave file
        self._current_wave_file.writeframes(data)

        # Check to see how long this file is.
        # If it has reached the specified length, close it so we can start a new one.
        if self._current_wave_file.getnframes() >= self._samples_in_continuous_file:
            # Close the file
            self._current_wave_file.close()
            # Set it to None so that we start a new one
            self._current_wave_file = None

    def trigger_recording(self, filename=None):
        '''
        :param filename: If specified, this filename will be used to save the triggered recording.  If not, a
        filename will be generated by appending the UTC timestamp to t_.
        :return:
        '''

        # figure out the new filename, if not specified
        if filename is None:
            now = datetime.utcnow()
            filename = "t_{0}.wav".format(now.strftime("%Y%m%dT%H%M%SZ"))
        file_path = os.path.join(self.output_directory, filename)

        triggered_wave_file = wave.open(file_path, mode='wb')
        triggered_wave_file.setnchannels(self._num_channels)
        triggered_wave_file.setsampwidth(pyaudio.get_sample_size(self._sample_format))
        triggered_wave_file.setframerate(self._sample_rate)

        triggered_wave_file.writeframes(''.join(self._ring_buffer))
        triggered_wave_file.close()

        self.log.info("Wrote triggered file: " + filename)

    @staticmethod
    def print_device_capabilities():
        p = pyaudio.PyAudio()
        devinfo = p.get_default_input_device_info()
        if devinfo.get('maxInputChannels')>0:
            print("Default Input Device: ", devinfo.get('name'))

            if p.is_format_supported(96000.0,  # Sample rate
                                 input_device=devinfo["index"],
                                 input_channels=devinfo['maxInputChannels'],
                                 input_format=pyaudio.paInt24):
                    print('24-bit 96000Hz supported!')

            if devinfo.get('maxOutputChannels')>0:
                    print("Output Device: ", devinfo.get('name'))



        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        #for each audio device, determine if is an input or an output and add it to the appropriate list and dictionary
        for i in range (0,numdevices):
            devinfo = p.get_device_info_by_host_api_device_index(0,i)
            if devinfo.get('maxInputChannels')>0:
                print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0,i).get('name'))

                if p.is_format_supported(96000.0,  # Sample rate
                                 input_device=devinfo["index"],
                                 input_channels=devinfo['maxInputChannels'],
                                 input_format=pyaudio.paInt24):
                    print('24-bit 96000Hz supported!')

            if devinfo.get('maxOutputChannels')>0:
                    print("Output Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0,i).get('name'))


        devinfo = p.get_device_info_by_index(1)
        print("Selected device is ", devinfo.get('name'))

        p.terminate()
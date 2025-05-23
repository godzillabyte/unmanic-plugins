#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    plugins.__init__.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Aug 2021, (20:38 PM)

    Copyright:
        Copyright (C) 2021 Josh Sunnex

        This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
        Public License as published by the Free Software Foundation, version 3.

        This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the
        implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
        for more details.

        You should have received a copy of the GNU General Public License along with this program.
        If not, see <https://www.gnu.org/licenses/>.

"""
import logging
import os

from unmanic.libs.unplugins.settings import PluginSettings

from encoder_audio_ac3.lib.ffmpeg import StreamMapper, Probe, Parser

# Configure plugin logger
logger = logging.getLogger("Unmanic.Plugin.encoder_audio_ac3")


class Settings(PluginSettings):
    settings = {
        "advanced":              False,
        "max_muxing_queue_size": 2048,
        "main_options":          "",
        "advanced_options":      "",
        "custom_options":        "",
        "codec_selection_mode":  "all",
        "selected_codecs":       ["dts", "dca", "truehd", "mp3", "mp2", "aac"],
    }

    def __init__(self, *args, **kwargs):
        super(Settings, self).__init__(*args, **kwargs)
        self.form_settings = {
            "advanced":              {
                "label": "Write your own FFmpeg params",
            },
            "max_muxing_queue_size": self.__set_max_muxing_queue_size_form_settings(),
            "main_options":          self.__set_main_options_form_settings(),
            "advanced_options":      self.__set_advanced_options_form_settings(),
            "custom_options":        self.__set_custom_options_form_settings(),
            "codec_selection_mode":  self.__set_codec_selection_mode_form_settings(),
            "selected_codecs":       self.__set_selected_codecs_form_settings(),
        }


    def __set_codec_selection_mode_form_settings(self):
        return {
            "label": "Codec Selection Mode",
            "input_type": "select",
            "select_options": [
                {
                    "value": "all",
                    "label": "Convert all non-AC3 audio codecs"
                },
                {
                    "value": "selected",
                    "label": "Convert only selected codecs"
                }
            ],
        }

    def __set_selected_codecs_form_settings(self):
        values = {
            "label": "Select codecs to convert to AC3",
            "input_type": "checkbox",
            "checkbox_options": [
                ("dts", "DTS"),
                ("dca", "DCA (DTS)"),
                ("truehd", "TrueHD"),
                ("eac3", "EAC3"),
                ("mp3", "MP3"),
                ("mp2", "MP2"),
                ("aac", "AAC"),
                ("opus", "Opus"),
                ("flac", "FLAC"),
                ("vorbis", "Vorbis"),
                ("pcm_s16le", "PCM"),
                ("other", "Other codecs"),
            ],
        }
        if self.get_setting('codec_selection_mode') != 'selected':
            values["display"] = 'hidden'
        return values

    def __set_max_muxing_queue_size_form_settings(self):
        values = {
            "label":          "Max input stream packet buffer",
            "input_type":     "slider",
            "slider_options": {
                "min": 1024,
                "max": 10240,
            },
        }
        if self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_main_options_form_settings(self):
        values = {
            "label":      "Write your own custom main options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_advanced_options_form_settings(self):
        values = {
            "label":      "Write your own custom advanced options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values

    def __set_custom_options_form_settings(self):
        values = {
            "label":      "Write your own custom audio options",
            "input_type": "textarea",
        }
        if not self.get_setting('advanced'):
            values["display"] = 'hidden'
        return values


class PluginStreamMapper(StreamMapper):
    def __init__(self):
        super(PluginStreamMapper, self).__init__(logger, ['audio'])
        self.codec = 'ac3'
        self.encoder = 'ac3'
        self.settings = None

    def set_default_values(self, settings, abspath, probe):
        """
        Configure the stream mapper with defaults

        :param settings:
        :param abspath:
        :param probe:
        :return:
        """
        self.abspath = abspath
        # Set the file probe data
        self.set_probe(probe)
        # Set the input file
        self.set_input_file(abspath)
        # Configure settings
        self.settings = settings

        # Build default options of advanced mode
        if self.settings.get_setting('advanced'):
            # If any main options are provided, overwrite them
            main_options = settings.get_setting('main_options').split()
            if main_options:
                # Overwrite all main options
                self.main_options = main_options
            # If any advanced options are provided, overwrite them
            advanced_options = settings.get_setting('advanced_options').split()
            if advanced_options:
                # Overwrite all advanced options
                self.advanced_options = advanced_options

    @staticmethod
    def calculate_bitrate(stream_info: dict):
        channels = stream_info.get('channels')
        # If no channel count is provided, assume the highest for AC3
        if not channels:
            logger.debug("Stream did not contain 'channels'. Setting max AC3 bit rate (640k).")
            return '640'

        if int(channels) > 6:
            channels = 6

        # Determine bitrate based on source channel count
        if int(channels) <= 2:
            logger.debug("Stream 'channels' is <= 2. Setting AC3 bit rate to 448k.")
            return '224'
        elif int(channels) <= 4:
            logger.debug("Stream 'channels' is <= 4. Setting AC3 bit rate to 448k.")
            return '448'
        elif int(channels) <= 6:
            logger.debug("Stream 'channels' is <= 6. Setting max AC3 bit rate (640k).")
            return '640'

        # Default to best quality
        logger.debug("Stream 'bit_rate' could not be matched directly ({}). Setting max AC3 bit rate.".format(
            channels))
        return '640'

    def test_stream_needs_processing(self, stream_info: dict):
        # Ignore streams already of the required codec_name
        if stream_info.get('codec_name').lower() in [self.codec]:
            return False
        return True

    def custom_stream_mapping(self, stream_info: dict, stream_id: int):
        stream_encoding = ['-c:a:{}'.format(stream_id), self.encoder]
        if self.settings.get_setting('advanced'):
            stream_encoding += self.settings.get_setting('custom_options').split()
        else:
            # Automatically detect bitrate for this stream.
            if stream_info.get('channels'):
                # Use 64K for the bitrate per channel
                calculated_bitrate = self.calculate_bitrate(stream_info)
                channels = int(stream_info.get('channels'))
                if int(channels) > 6:
                    channels = 6
                stream_encoding += [
                    '-ac:a:{}'.format(stream_id), '{}'.format(channels), '-b:a:{}'.format(stream_id), "{}k".format(calculated_bitrate)
                ]

        return {
            'stream_mapping':  ['-map', '0:a:{}'.format(stream_id)],
            'stream_encoding': stream_encoding,
        }


def on_library_management_file_test(data):
    """
    Runner function - enables additional actions during the library management file tests.

    The 'data' object argument includes:
        path                            - String containing the full path to the file being tested.
        issues                          - List of currently found issues for not processing the file.
        add_file_to_pending_tasks       - Boolean, is the file currently marked to be added to the queue for processing.

    :param data:
    :return:

    """
    # Get the path to the file
    abspath = data.get('path')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['audio', 'video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure settings object (maintain compatibility with v1 plugins)
    if data.get('library_id'):
        settings = Settings(library_id=data.get('library_id'))
    else:
        settings = Settings()

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_default_values(settings, abspath, probe)

    if mapper.streams_need_processing():
        # Mark this file to be added to the pending tasks
        data['add_file_to_pending_tasks'] = True
        logger.debug("File '{}' should be added to task list. Probe found streams require processing.".format(abspath))
    else:
        logger.debug("File '{}' does not contain streams require processing.".format(abspath))

    return data


def on_worker_process(data):
    """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        exec_command            - A command that Unmanic should execute. Can be empty.
        command_progress_parser - A function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - The source file to be processed by the command.
        file_out                - The destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - The absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    :param data:
    :return:

    """
    # Default to no FFMPEG command required. This prevents the FFMPEG command from running if it is not required
    data['exec_command'] = []
    data['repeat'] = False

    # Get the path to the file
    abspath = data.get('file_in')

    # Get file probe
    probe = Probe(logger, allowed_mimetypes=['audio', 'video'])
    if not probe.file(abspath):
        # File probe failed, skip the rest of this test
        return data

    # Configure settings object (maintain compatibility with v1 plugins)
    settings = Settings(library_id=data.get('library_id'))

    # Get stream mapper
    mapper = PluginStreamMapper()
    mapper.set_default_values(settings, abspath, probe)

    if mapper.streams_need_processing():
        # Set the input file
        mapper.set_input_file(abspath)

        # Set the output file
        mapper.set_output_file(data.get('file_out'))

        # Get generated ffmpeg args
        ffmpeg_args = mapper.get_ffmpeg_args()

        # Apply ffmpeg args to command
        data['exec_command'] = ['ffmpeg']
        data['exec_command'] += ffmpeg_args

        # Set the parser
        parser = Parser(logger)
        parser.set_probe(probe)
        data['command_progress_parser'] = parser.parse_progress

# Copyright 2022 Mycroft AI Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import argparse
import io
import logging
import threading
import tempfile
import typing
import simpleaudio as sa
import wave
from queue import Queue

from mimic3_tts import (
    AudioResult,
    Mimic3Settings,
    Mimic3TextToSpeechSystem,
    SSMLSpeaker,
)
from mimic3_tts.config import InferenceConfig

from mimic3_http.const import TextToWavParams

_LOGGER = logging.getLogger(__name__)

from dataclasses import dataclass
inf_conf = InferenceConfig()

def do_synthesis(params: TextToWavParams, mimic3: Mimic3TextToSpeechSystem) -> bytes:
    """Synthesize text into audio.

    Returns: WAV bytes
    """
    mimic3.speaker = None
    mimic3.voice = params.voice

    mimic3.settings.length_scale = params.length_scale
    mimic3.settings.noise_scale = params.noise_scale
    mimic3.settings.noise_w = params.noise_w

    with io.BytesIO() as wav_io:
        wav_file: wave.Wave_write = wave.open(wav_io, "wb")
        wav_params_set = False

        with wav_file:
            try:
                if params.ssml:
                    # SSML
                    results = SSMLSpeaker(mimic3).speak(params.text)
                else:
                    # Plain text
                    mimic3.begin_utterance()
                    mimic3.speak_text(params.text, text_language=params.text_language)
                    results = mimic3.end_utterance()

                for result in results:
                    # Add audio to existing WAV file
                    if isinstance(result, AudioResult):
                        if not wav_params_set:
                            wav_file.setframerate(result.sample_rate_hz)
                            wav_file.setsampwidth(result.sample_width_bytes)
                            wav_file.setnchannels(result.num_channels)
                            wav_params_set = True

                        wav_file.writeframes(result.audio_bytes)
            except Exception as e:
                if not wav_params_set:
                    # Set default parameters so exception can propagate
                    wav_file.setframerate(22050)
                    wav_file.setsampwidth(2)
                    wav_file.setnchannels(1)

                raise e

        wav_bytes = wav_io.getvalue()

        return wav_bytes

def create_mimic3_system(
        voice: str=None, speaker: str=None, length_scale:float=None,
        rate: float = None,
        noise_scale:float=None, noise_w:float=None, use_cuda: bool=None,
        voices_directories: list[str]=None, use_deterministic_compute:bool=None,
        preload_voices:list[str]=None
    ) -> Mimic3TextToSpeechSystem:

    mimic3 = Mimic3TextToSpeechSystem(
        Mimic3Settings(
            rate=rate,
            voice=voice,
            speaker=speaker,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w,
            use_cuda=use_cuda,
            voices_directories=voices_directories,
            use_deterministic_compute=use_deterministic_compute,
        )
    )
    with mimic3:
        if preload_voices:
            # Ensure voices are preloaded
            for voice_key in preload_voices:
                mimic3.preload_voice(voice_key)
    return mimic3

def play_wav_bytes(wav_bytes: bytes):
    with tempfile.NamedTemporaryFile(mode="wb+", suffix=".wav") as wav_file:
        wav_file.write(wav_bytes)
        wav_file.seek(0)

        filename = wav_file.name
        wave_obj = sa.WaveObject.from_wave_file(filename)
        play_obj = wave_obj.play()
        play_obj.wait_done()

def say_words(words: str, mimic3: Mimic3TextToSpeechSystem, length_scale: float = None, ssml=False):
    """Thread handler for synthesis requests"""
    try:
        with mimic3:
            params = TextToWavParams(
                text=words, voice=mimic3.settings.voice,
                noise_scale=mimic3.settings.noise_scale,
                noise_w=mimic3.settings.noise_w,
                ssml=ssml,
                length_scale=length_scale if length_scale is not None else mimic3.settings.length_scale
            )

            try:
                play_wav_bytes(do_synthesis(params, mimic3))
            except Exception as e:
                raise(e)

    except Exception as e:
        raise(e)

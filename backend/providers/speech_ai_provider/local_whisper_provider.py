import os
import re
import tempfile
from functools import lru_cache

from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from providers.speech_ai_provider.base import SpeechAIProvider

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")
SUPPORTED_MODEL_SIZES = {"base", "small", "medium"}


class LocalWhisperSpeechProvider(SpeechAIProvider):
    """默认语音提供者：本地 faster-whisper。"""

    def transcribe(self, wav_path: str, *, initial_prompt: str = "") -> str:
        if WhisperModel is None:
            raise RuntimeError("当前环境缺少离线转写依赖，请安装 faster-whisper")

        model = _get_whisper_model()
        single = self._transcribe_single_pass(model, wav_path, initial_prompt)
        text = single["text"]
        segment_meta = list(single["segments"])

        audio = AudioSegment.from_wav(wav_path)
        if audio.duration_seconds >= 10 or len(re.sub(r"\s+", "", text)) < 6:
            chunk_data = self._transcribe_by_nonsilent_chunks(model, audio, wav_path, initial_prompt)
            chunk_text = chunk_data["text"]
            if len(re.sub(r"\s+", "", chunk_text)) > len(re.sub(r"\s+", "", text)):
                text = chunk_text
                segment_meta = list(chunk_data["segments"])

        raw_before_clean = text
        print(
            f"[speech-provider] raw_transcript_before_clean len={len(raw_before_clean)} "
            f"preview={raw_before_clean[:500]!r}"
        )
        cleaned = self._clean_transcript(text)
        print(
            f"[speech-provider] final_transcript_after_clean len={len(cleaned)} "
            f"preview={cleaned[:500]!r}"
        )
        return cleaned

    def transcribe_with_meta(self, wav_path: str, *, initial_prompt: str = "") -> dict:
        if WhisperModel is None:
            raise RuntimeError("当前环境缺少离线转写依赖，请安装 faster-whisper")

        model = _get_whisper_model()
        single = self._transcribe_single_pass(model, wav_path, initial_prompt)
        text = single["text"]
        segment_meta = list(single["segments"])

        audio = AudioSegment.from_wav(wav_path)
        used_chunk_fallback = False
        if audio.duration_seconds >= 10 or len(re.sub(r"\s+", "", text)) < 6:
            chunk_data = self._transcribe_by_nonsilent_chunks(model, audio, wav_path, initial_prompt)
            chunk_text = chunk_data["text"]
            if len(re.sub(r"\s+", "", chunk_text)) > len(re.sub(r"\s+", "", text)):
                text = chunk_text
                segment_meta = list(chunk_data["segments"])
                used_chunk_fallback = True

        raw_before_clean = text
        print(
            f"[speech-provider] raw_transcript_before_clean len={len(raw_before_clean)} "
            f"preview={raw_before_clean[:500]!r}"
        )
        cleaned = self._clean_transcript(text)
        print(
            f"[speech-provider] final_transcript_after_clean len={len(cleaned)} "
            f"preview={cleaned[:500]!r}"
        )
        return {
            "text": cleaned,
            "segments": segment_meta,
            "used_chunk_fallback": used_chunk_fallback,
        }

    def _transcribe_single_pass(self, model, wav_path: str, initial_prompt: str) -> dict:
        segments, _ = model.transcribe(
            wav_path,
            language="zh",
            task="transcribe",
            beam_size=6,
            best_of=6,
            vad_filter=True,
            temperature=0.0,
            condition_on_previous_text=False,
            initial_prompt=initial_prompt or None,
        )
        text_segments = []
        segment_meta = []
        for seg in segments:
            seg_text = re.sub(r"\s+", " ", (seg.text or "")).strip()
            if seg_text:
                text_segments.append(seg_text)
            segment_meta.append(
                {
                    "text": seg_text,
                    "no_speech_prob": getattr(seg, "no_speech_prob", None),
                    "avg_logprob": getattr(seg, "avg_logprob", None),
                    "compression_ratio": getattr(seg, "compression_ratio", None),
                    "start": getattr(seg, "start", None),
                    "end": getattr(seg, "end", None),
                }
            )
        return {"text": " ".join(text_segments).strip(), "segments": segment_meta}

    def _transcribe_by_nonsilent_chunks(self, model, wav_audio: AudioSegment, wav_path: str, initial_prompt: str) -> dict:
        nonsilent_ranges = detect_nonsilent(
            wav_audio,
            min_silence_len=350,
            silence_thresh=wav_audio.dBFS - 18 if wav_audio.dBFS != float("-inf") else -42,
        )
        if not nonsilent_ranges:
            return {"text": "", "segments": []}

        chunk_texts = []
        all_segments_meta = []
        for start_ms, end_ms in nonsilent_ranges:
            duration_sec = (end_ms - start_ms) / 1000.0
            if duration_sec < 0.6:
                continue
            chunk = wav_audio[max(start_ms - 120, 0): min(end_ms + 120, len(wav_audio))]
            fd, chunk_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                chunk.export(chunk_path, format="wav", parameters=["-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le"])
                chunk_data = self._transcribe_single_pass(model, chunk_path, initial_prompt)
                chunk_text = chunk_data["text"]
                if chunk_text:
                    chunk_texts.append(chunk_text)
                for seg in chunk_data["segments"]:
                    merged = dict(seg)
                    merged["chunk_start_ms"] = start_ms
                    merged["chunk_end_ms"] = end_ms
                    all_segments_meta.append(merged)
            except Exception as e:
                print(f"[speech-provider] chunk transcribe failed: {repr(e)} source={wav_path}")
            finally:
                if os.path.exists(chunk_path):
                    try:
                        os.remove(chunk_path)
                    except Exception:
                        pass
        return {"text": " ".join(chunk_texts).strip(), "segments": all_segments_meta}

    def _clean_transcript(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", (text or "")).strip()
        cleaned = re.sub(r"([，。！？,.!?])\1{1,}", r"\1", cleaned)
        cleaned = re.sub(r"\b([\u4e00-\u9fff]{1,3})\s+\1\b", r"\1", cleaned)
        cleaned = re.sub(r"([\u4e00-\u9fff]{1,3})\1{2,}", r"\1", cleaned)
        cleaned = self._strip_metric_hallucination_loops(cleaned)
        return cleaned

    def _strip_metric_hallucination_loops(self, text: str) -> str:
        """去掉因旧版 initial_prompt 或噪声导致的「语速/停顿」循环式幻听，不替代真实讲话内容。"""
        t = re.sub(r"\s+", " ", (text or "").strip())
        if not t:
            return ""
        # 典型污染：语速、停顿、语速、停顿
        t = re.sub(r"(语速\s*[、，,]\s*停顿\s*)+", " ", t)
        t = re.sub(r"(停顿\s*[、，,]\s*语速\s*)+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        # 整段仅为评估词与标点交替时视为无效转写
        if re.fullmatch(r"([\s、，,。.]*(?:语速|停顿|口头禅)[\s、，,。.]*)+", t):
            return ""
        return t

    def analyze_audio(self, audio_path: str, *, analysis_phase: str = "lecture") -> dict:
        """委托 `AudioService`，复用现有归一化、静音门控与指标计算。"""
        _ = analysis_phase
        from services.audio_service import AudioService

        return AudioService().analyze_audio(audio_path)


@lru_cache(maxsize=1)
def _get_whisper_model():
    return WhisperModel(_get_effective_model_size(), device="cpu", compute_type="int8")


def _get_effective_model_size() -> str:
    model_size = (WHISPER_MODEL_SIZE or "medium").lower().strip()
    if model_size not in SUPPORTED_MODEL_SIZES:
        return "medium"
    return model_size


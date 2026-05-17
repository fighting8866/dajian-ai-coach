import os
import re
import shutil
import tempfile

from pydub import AudioSegment
from pydub.silence import detect_nonsilent, detect_silence

from factories.provider_factory import get_speech_ai_provider

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_DBFS = -20.0
# 勿在 initial_prompt 中写入「语速、停顿、口头禅」等评估指标词：Whisper 易在静音/噪声下
# 重复输出提示词内容，污染 transcript。仅用简短中性语境引导中文口语。
TRANSCRIBE_INITIAL_PROMPT = "以下为中文口语内容。"

# 有效语音门槛（静音/噪声不误送 Whisper，避免幻听）
MIN_VALID_DURATION_SEC = 1.0
MIN_VALID_DBFS = -48.0
MIN_VALID_NON_SILENT_SEC = 0.8
NONSILENT_MIN_SILENCE_MS = 300

INVALID_AUDIO_MESSAGE = "未检测到有效语音，请靠近麦克风后重试"
HALLUCINATION_BLACKLIST_PHRASES = [
    "点赞",
    "订阅",
    "转发",
    "打赏",
    "支持",
    "明镜",
    "栏目",
    "请不吝",
    "感谢观看",
    "欢迎收看",
    "点点栏目",
]


def _invalid_audio_analysis_result() -> dict:
    return {
        "transcript": "",
        "speech_rate": 0,
        "pause_count": 0,
        "avg_pause_sec": 0.0,
        "filler_count": 0,
        "audio_valid": False,
        "audio_message": INVALID_AUDIO_MESSAGE,
    }


class AudioService:
    """离线音频分析服务（语音能力通过 speech_ai_provider 注入）。"""

    def __init__(self):
        self.speech_provider = get_speech_ai_provider()

    def transcribe_audio(self, audio_path: str) -> tuple[str, list[dict]]:
        try:
            segments_meta: list[dict] = []
            if hasattr(self.speech_provider, "transcribe_with_meta"):
                data = self.speech_provider.transcribe_with_meta(  # type: ignore[attr-defined]
                    audio_path, initial_prompt=TRANSCRIBE_INITIAL_PROMPT
                )
                text = data.get("text", "") if isinstance(data, dict) else ""
                segments_meta = data.get("segments", []) if isinstance(data, dict) else []
                if not isinstance(segments_meta, list):
                    segments_meta = []
            else:
                text = self.speech_provider.transcribe(audio_path, initial_prompt=TRANSCRIBE_INITIAL_PROMPT)

            print(
                f"[audio.transcribe] transcript_text len={len(text)} "
                f"preview={text[:500]!r}"
            )
            if len(text) < 2:
                print(f"[audio.transcribe] transcript 过短或为空: {text!r}")
            print(f"[audio.transcribe] segments_count={len(segments_meta)}")
            for idx, seg in enumerate(segments_meta):
                seg_text = str(seg.get("text") or "")
                print(
                    f"[audio.transcribe.segment] idx={idx} "
                    f"text={seg_text[:120]!r} "
                    f"no_speech_prob={seg.get('no_speech_prob')!r} "
                    f"avg_logprob={seg.get('avg_logprob')!r} "
                    f"compression_ratio={seg.get('compression_ratio')!r}"
                )
            return text, segments_meta
        except Exception as e:
            raise RuntimeError(f"音频转写失败：{repr(e)}")

    def _extract_blacklist_hits(self, transcript: str) -> dict:
        hit_count = 0
        hit_terms = []
        hit_chars = 0
        for term in HALLUCINATION_BLACKLIST_PHRASES:
            cnt = transcript.count(term)
            if cnt > 0:
                hit_terms.append(term)
                hit_count += cnt
                hit_chars += len(term) * cnt
        return {
            "hit_count": hit_count,
            "hit_terms": hit_terms,
            "hit_chars": hit_chars,
        }

    def _assess_asr_quality(self, transcript: str, segments_meta: list[dict]) -> tuple[bool, str]:
        pure_text = re.sub(r"\s+", "", transcript or "")
        text_len = len(pure_text)
        hits = self._extract_blacklist_hits(pure_text)
        hit_count = int(hits["hit_count"])
        hit_terms = list(hits["hit_terms"])
        hit_ratio = float(hits["hit_chars"]) / max(float(text_len), 1.0)

        no_speech_probs = []
        avg_logprobs = []
        compression_ratios = []
        for seg in segments_meta:
            no_speech = seg.get("no_speech_prob")
            avg_logprob = seg.get("avg_logprob")
            compression_ratio = seg.get("compression_ratio")
            if isinstance(no_speech, (float, int)):
                no_speech_probs.append(float(no_speech))
            if isinstance(avg_logprob, (float, int)):
                avg_logprobs.append(float(avg_logprob))
            if isinstance(compression_ratio, (float, int)):
                compression_ratios.append(float(compression_ratio))

        segments_count = len(segments_meta)
        avg_no_speech = (sum(no_speech_probs) / len(no_speech_probs)) if no_speech_probs else None
        avg_logprob = (sum(avg_logprobs) / len(avg_logprobs)) if avg_logprobs else None
        avg_compression = (sum(compression_ratios) / len(compression_ratios)) if compression_ratios else None
        high_no_speech_ratio = (
            sum(1 for p in no_speech_probs if p >= 0.70) / len(no_speech_probs) if no_speech_probs else 0.0
        )
        low_logprob_ratio = (
            sum(1 for p in avg_logprobs if p <= -1.2) / len(avg_logprobs) if avg_logprobs else 0.0
        )
        high_compression_ratio = (
            sum(1 for p in compression_ratios if p >= 2.4) / len(compression_ratios) if compression_ratios else 0.0
        )

        print(
            "[audio.quality] blacklist_hits="
            f"{hit_terms} hit_count={hit_count} hit_ratio={hit_ratio:.2f} text_len={text_len}"
        )
        print(
            "[audio.quality] segment_stats="
            f"segments={segments_count} avg_no_speech={avg_no_speech} avg_logprob={avg_logprob} "
            f"avg_compression={avg_compression} high_no_speech_ratio={high_no_speech_ratio:.2f} "
            f"low_logprob_ratio={low_logprob_ratio:.2f} high_compression_ratio={high_compression_ratio:.2f}"
        )

        # 规则 1：无文本直接无效
        if text_len == 0:
            return False, "转写文本为空"

        # 规则 2：黑名单命中高 + 低质量信号（保守）
        if hit_count >= 2:
            if (
                (avg_no_speech is not None and avg_no_speech >= 0.70)
                or (avg_logprob is not None and avg_logprob <= -1.2)
                or high_no_speech_ratio >= 0.60
                or low_logprob_ratio >= 0.60
                or high_compression_ratio >= 0.60
                or segments_count <= 1
            ):
                return False, "命中高风险幻觉词且缺少有效语音证据"

        # 规则 3：文本主要由黑名单词组成
        if hit_count >= 2 and hit_ratio >= 0.60:
            return False, "转写文本主要由黑名单短语组成"

        # 规则 4：整体置信明显异常
        if (
            avg_no_speech is not None
            and avg_logprob is not None
            and avg_no_speech >= 0.85
            and avg_logprob <= -1.25
        ):
            return False, "no_speech_prob 与 avg_logprob 指示低质量"

        # 规则 5：长文本但重复命中常见幻觉短语
        if text_len >= 18 and hit_count >= 3 and (segments_count <= 2 or high_compression_ratio >= 0.50):
            return False, "长文本命中多项高风险短语，判定为幻觉"

        return True, "通过第二层 ASR 质量判定"

    def analyze_audio_metrics(self, audio_path: str, transcript: str) -> dict:
        try:
            audio = AudioSegment.from_wav(audio_path)
        except Exception as e:
            raise RuntimeError(f"读取标准化 wav 失败: {repr(e)}")
        duration_sec = max(float(audio.duration_seconds), 1e-6)
        print(
            f"[audio.metrics] wav_duration_sec={duration_sec:.2f} wav_frame_rate={audio.frame_rate} wav_channels={audio.channels}"
        )
        duration_min = duration_sec / 60.0
        silence_ranges = detect_silence(
            audio,
            min_silence_len=400,
            silence_thresh=audio.dBFS - 16 if audio.dBFS != float("-inf") else -40,
        )
        pause_durations = [(end - start) / 1000.0 for start, end in silence_ranges if (end - start) >= 400]
        pause_count = len(pause_durations)
        avg_pause_sec = (sum(pause_durations) / pause_count) if pause_count > 0 else 0.0

        text = transcript or ""
        pure_text = re.sub(r"\s+", "", text)
        if len(pure_text) < 2:
            speech_rate = 0.0
            print("[audio.metrics] transcript 过短，speech_rate 按 0 处理")
        else:
            speech_rate = len(pure_text) / duration_min
        if duration_sec > 0 and len(pure_text) == 0:
            print("[audio.metrics] 音频有时长，但转写为空")

        fillers = ["然后", "就是", "那个", "嗯", "呃", "所以"]
        filler_count = sum(text.count(filler) for filler in fillers)
        print(f"[audio.metrics] wav_duration_sec={duration_sec:.2f} transcript_len={len(pure_text)}")

        return {
            "speech_rate": round(speech_rate, 2),
            "pause_count": pause_count,
            "avg_pause_sec": round(avg_pause_sec, 2),
            "filler_count": filler_count,
        }

    def normalize_audio_to_wav(self, input_path: str) -> str:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("当前环境缺少 ffmpeg，无法解析浏览器录音格式")

        fd, wav_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            audio = AudioSegment.from_file(input_path)
            processed = audio.set_channels(TARGET_CHANNELS).set_frame_rate(TARGET_SAMPLE_RATE)
            if processed.dBFS != float("-inf"):
                gain = TARGET_DBFS - processed.dBFS
                gain = max(min(gain, 10.0), -10.0)
                processed = processed.apply_gain(gain)
            processed.export(
                wav_path,
                format="wav",
                parameters=["-ac", str(TARGET_CHANNELS), "-ar", str(TARGET_SAMPLE_RATE), "-acodec", "pcm_s16le"],
            )
            if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                raise RuntimeError("音频转码失败：输出 wav 文件为空")
            wav_audio = AudioSegment.from_wav(wav_path)
            print(
                f"[audio.normalize] source={input_path} wav={wav_path} size={os.path.getsize(wav_path)} "
                f"duration_sec={wav_audio.duration_seconds:.2f} dBFS={wav_audio.dBFS:.2f} channels={wav_audio.channels} frame_rate={wav_audio.frame_rate}"
            )
            return wav_path
        except Exception as e:
            if os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
            raise RuntimeError(f"音频转码失败: {repr(e)}")

    def _assess_speech_validity(self, wav_path: str) -> tuple[bool, dict | None]:
        """normalize 后的 wav：时长 / 平均电平 / 非静音总时长。不通过则返回 (False, 结构化结果)，不进入转写。"""
        try:
            audio = AudioSegment.from_wav(wav_path)
        except Exception as e:
            print(f"[audio.validity] 读取 wav 失败: {e!r}")
            return False, _invalid_audio_analysis_result()

        duration_sec = float(audio.duration_seconds)
        dbfs = audio.dBFS

        if duration_sec < MIN_VALID_DURATION_SEC:
            print(
                f"[audio.validity] reject: duration_sec={duration_sec:.3f} < {MIN_VALID_DURATION_SEC}"
            )
            return False, _invalid_audio_analysis_result()

        if dbfs == float("-inf") or dbfs < MIN_VALID_DBFS:
            print(f"[audio.validity] reject: dBFS={dbfs} (min {MIN_VALID_DBFS})")
            return False, _invalid_audio_analysis_result()

        # 与 metrics 中 detect_silence 一致：相对整段电平的静音阈值
        silence_thresh = max(dbfs - 16.0, -55.0) if dbfs != float("-inf") else -50.0
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=NONSILENT_MIN_SILENCE_MS,
            silence_thresh=silence_thresh,
            seek_step=10,
        )
        nonsilent_ms = sum((end - start) for start, end in nonsilent_ranges)
        nonsilent_sec = nonsilent_ms / 1000.0

        if nonsilent_sec < MIN_VALID_NON_SILENT_SEC:
            print(
                f"[audio.validity] reject: nonsilent_sec={nonsilent_sec:.3f} < {MIN_VALID_NON_SILENT_SEC} "
                f"(thresh={silence_thresh:.1f} dBFS)"
            )
            return False, _invalid_audio_analysis_result()

        print(
            f"[audio.validity] ok: duration_sec={duration_sec:.2f} dBFS={dbfs:.2f} "
            f"nonsilent_sec={nonsilent_sec:.2f} silence_thresh={silence_thresh:.1f}"
        )
        return True, None

    def analyze_audio(self, audio_path: str) -> dict:
        wav_path = self.normalize_audio_to_wav(audio_path)
        try:
            ok, invalid_payload = self._assess_speech_validity(wav_path)
            print(f"[audio.analyze] first_layer_validity={ok}")
            if not ok:
                print("[audio.analyze] final_audio_valid=False reason=第一层声学门控不通过")
                return invalid_payload

            transcript, segments_meta = self.transcribe_audio(wav_path)
            quality_ok, quality_reason = self._assess_asr_quality(transcript, segments_meta)
            if not quality_ok:
                print(f"[audio.analyze] final_audio_valid=False reason={quality_reason}")
                return _invalid_audio_analysis_result()

            metrics = self.analyze_audio_metrics(wav_path, transcript)
            result = {
                "transcript": transcript,
                **metrics,
                "audio_valid": True,
                "audio_message": "",
            }
            print(f"[audio.analyze] final_audio_valid=True reason={quality_reason}")
            print(
                "[audio.analyze] transcript_text (pure ASR)="
                + repr(result.get("transcript", ""))[:800]
            )
            print(
                "[audio.analyze] metrics (separate from transcript)="
                + repr(
                    {
                        "speech_rate": result.get("speech_rate"),
                        "pause_count": result.get("pause_count"),
                        "avg_pause_sec": result.get("avg_pause_sec"),
                        "filler_count": result.get("filler_count"),
                    }
                )
            )
            return result
        finally:
            if wav_path != audio_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except Exception:
                    pass
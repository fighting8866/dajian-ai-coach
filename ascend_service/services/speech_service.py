from __future__ import annotations

"""
语音分析精调收口 V1（板侧 ascend_service）

- **ASR**：`faster-whisper`（WhisperModel，可选 `vad_filter` 与 pydub 非静音分段兜底）。
- **VAD / 有效语音门控**：以 `pydub.silence.detect_nonsilent` 为主判定非静音占比；
  与 Whisper 内置 VAD 互补，非 Silero。若后续接入 **silero-vad**，建议在本模块
  `_assess_speech_validity` 旁增加分支，保持 `audio_valid` / `analyze_audio` 出口不变。
- **长时答辩 V2 第一阶段**：超过阈值的音频走 **固定窗口分段 ASR**（见 `_transcribe_chunked_v1`），
  避免整段 + 非静音碎片反复 `vad_filter=False` 拖垮时延；短时仍走原 `faster-whisper` 单段/兜底路径。
"""

import os
import re
import shutil
import tempfile
import time
from typing import Any

from pydub import AudioSegment
from pydub.silence import detect_nonsilent, detect_silence

try:
    from faster_whisper import WhisperModel
except Exception:
    WhisperModel = None

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_DBFS = -20.0
TRANSCRIBE_LANGUAGE = "zh"
TRANSCRIBE_INITIAL_PROMPT = "面试答辩现场录音转写。仅输出实际听到的中文，不要补充模板语。"
TRANSCRIBE_BEAM_SIZE = 6
TRANSCRIBE_BEST_OF = 6
TRANSCRIBE_TEMPERATURE = 0.0

# 有效语音门控（略放宽以减少「有说话却被判无效」；仍挡极短/极静）
MIN_VALID_DURATION_SEC = 0.95
MIN_VALID_DBFS = -52.0
# 略低于 0.68：减少「有语音但 VAD 切分偏严」导致的误判；与 chunk 最小时长配合
MIN_VALID_NON_SILENT_SEC = 0.63
NONSILENT_MIN_SILENCE_MS = 280
INVALID_AUDIO_MESSAGE = "未检测到有效语音，请靠近麦克风或稍大声后重试"
# 非静音分段逐段转写时跳过过短块，减少噪声碎片伪转写（略高于原 0.6s）
CHUNK_MIN_NONSILENT_SEC = 0.68

# 极端语速（字/分钟量级异常）常与幻觉/碎片转写共存
MAX_REASONABLE_SPEECH_RATE = 520
SPEECH_RATE_SUSPICIOUS_DURATION_SEC = 14
SPEECH_RATE_SUSPICIOUS_CHAR_LEN = 22

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small").strip().lower() or "small"
# 长时 chunked 仍用 SPEECH_LONG_SESSION_MODEL_SIZE；短时/常规路径用 WHISPER_MODEL_SIZE（默认 small，可设 WHISPER_MODEL_SIZE=medium）
SPEECH_LONG_SESSION_MODEL_SIZE = (
    os.getenv("SPEECH_LONG_SESSION_MODEL_SIZE", "small").strip().lower() or "small"
)


def _speech_env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return float(default)
    try:
        return float(str(v).strip())
    except ValueError:
        return float(default)


def _speech_env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        return int(default)
    try:
        return int(str(v).strip())
    except ValueError:
        return int(default)


# 达到该时长（秒）即走固定窗口分段，且 **禁止** 再走非静音 chunk_fallback（避免 1~3 分钟仍 vad_filter=False 碎片风暴）
LONG_AUDIO_CHUNKED_THRESHOLD_SEC = _speech_env_float("SPEECH_LONG_AUDIO_CHUNKED_THRESHOLD_SEC", 25.0)
AUDIO_CHUNK_SECONDS = _speech_env_float("AUDIO_CHUNK_SECONDS", 20.0)
AUDIO_CHUNK_OVERLAP_SECONDS = _speech_env_float("AUDIO_CHUNK_OVERLAP_SECONDS", 1.0)
# 长时分段 ASR：降低 beam/best_of 以缩短墙钟
SPEECH_LONG_TRANSCRIBE_BEAM_SIZE = max(1, _speech_env_int("SPEECH_LONG_TRANSCRIBE_BEAM_SIZE", 1))
SPEECH_LONG_TRANSCRIBE_BEST_OF = max(1, _speech_env_int("SPEECH_LONG_TRANSCRIBE_BEST_OF", 1))

_LAST_SPEECH_ANALYZE_DEBUG: dict[str, Any] = {}
_WHISPER_MODEL_SINGLETONS: dict[str, Any] = {}
_LAST_WHISPER_SESSION: dict[str, Any] = {}


def get_last_speech_analyze_debug() -> dict[str, Any]:
    """供 api/speech 打印长时分段统计；不改变 JSON 协议。"""
    return dict(_LAST_SPEECH_ANALYZE_DEBUG)


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
TEMPLATE_CONTAMINATION_PHRASES = [
    "面试答辩现场录音转写",
    "中文口语内容",
    "录音转写",
    "现场录音转写",
]
TEMPLATE_CONTAMINATION_MESSAGE = "检测到模板化伪转写，请重新录音"


def _normalize_speech_analysis_phase(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in ("qa_answer", "qa", "qa_answer_phase"):
        return "qa_answer"
    return "lecture"


def _strip_trailing_modal_particles(text: str) -> str:
    return re.sub(r"(啊|呀|呢|吧|哦|噢|嗯|哈|嘛)+$", "", str(text or "").strip())


def _compact_hanzi_letters(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", s or "")


def _is_legit_short_qa_answer(text: str) -> bool:
    """问答阶段常见短答：不因「有效汉字种类过少」一律判伪转写；模板污染仍由短语闸门拦截。"""
    raw = _strip_trailing_modal_particles(str(text or "").strip())
    compact = _compact_hanzi_letters(raw)
    if not compact:
        return False
    exact_ok = {
        "我不知道",
        "不晓得",
        "不清楚",
        "不太清楚",
        "不太确定",
        "不太懂",
        "不确定",
        "不好说",
        "暂时没有",
        "暂时还没有",
        "暂时不会",
        "还没做",
        "还没有",
        "还没想好",
        "需要确认",
        "需要再确认",
        "需要查证",
        "我再想想",
        "没准备",
        "没有准备",
        "说不上来",
        "答不上来",
    }
    if compact in exact_ok:
        return True
    prefixes = (
        "我不知道",
        "我不太确定",
        "暂时",
        "还没",
        "需要确认",
    )
    if any(compact.startswith(p) for p in prefixes) and len(compact) <= 14:
        return True
    return False


# 长时会话（>=60s）转写充分性 / 可信度闸门（不替代污染检测，仅补充会话级质量）
LONG_SESSION_ADEQUACY_THRESHOLD_SEC = 60.0
ADEQUACY_GATE_FAIL_MESSAGE = "语音内容有效性不足，请重试或靠近麦克风后再录制"
# 中短时轻量闸门：默认 [25, 60) 秒，或 chunked 且整段 <60s（与长闸门互斥）
SHORT_ADEQUACY_GATE_MIN_SEC = _speech_env_float("SPEECH_SHORT_ADEQUACY_GATE_MIN_SEC", 25.0)


def _short_session_transcript_adequacy_gate(
    *,
    duration_sec: float,
    transcript: str,
    speech_rate: float,
    pause_count: int,
    transcribed_chunks: int,
    chunked_mode_used: bool,
    analysis_phase: str = "lecture",
) -> tuple[bool, str, dict[str, Any]]:
    """25~60s（或 chunked 且 <60s）轻量充分性闸门；与 >=60s 长闸门独立，不修改长闸门逻辑。"""
    if _normalize_speech_analysis_phase(analysis_phase) == "qa_answer":
        pure0 = len(re.sub(r"\s+", "", transcript or ""))
        duration_min0 = max(float(duration_sec) / 60.0, 1e-6)
        cpm0 = float(pure0) / duration_min0
        tc0 = max(int(transcribed_chunks or 0), 0)
        avg0 = float(pure0) / max(tc0, 1) if tc0 > 0 else float(pure0)
        stats_skip: dict[str, Any] = {
            "short_adequacy_gate_hit": False,
            "short_adequacy_gate_reason": "",
            "total_audio_duration_sec": round(float(duration_sec), 3),
            "transcript_chars_per_minute": round(cpm0, 2),
            "avg_chars_per_chunk": round(avg0, 2),
        }
        print(
            "[ascend_service.speech.short_adequacy] "
            f"phase=qa_answer short_adequacy_skipped_for_qa=True transcript_pure_len={pure0}"
        )
        return False, "", stats_skip
    pure = len(re.sub(r"\s+", "", transcript or ""))
    duration_min = max(float(duration_sec) / 60.0, 1e-6)
    cpm = float(pure) / duration_min
    tc = max(int(transcribed_chunks or 0), 0)
    avg_chunk = float(pure) / max(tc, 1) if tc > 0 else float(pure)

    stats: dict[str, Any] = {
        "short_adequacy_gate_hit": False,
        "short_adequacy_gate_reason": "",
        "total_audio_duration_sec": round(float(duration_sec), 3),
        "transcript_chars_per_minute": round(cpm, 2),
        "avg_chars_per_chunk": round(avg_chunk, 2),
    }
    if duration_sec >= LONG_SESSION_ADEQUACY_THRESHOLD_SEC:
        return False, "", stats

    in_mid_window = (
        float(duration_sec) >= SHORT_ADEQUACY_GATE_MIN_SEC
        and float(duration_sec) < LONG_SESSION_ADEQUACY_THRESHOLD_SEC
    )
    chunked_under_long = chunked_mode_used and float(duration_sec) < LONG_SESSION_ADEQUACY_THRESHOLD_SEC
    if not in_mid_window and not chunked_under_long:
        return False, "", stats

    reasons: list[str] = []
    if pure < 12:
        reasons.append(f"总文本过短(chars={pure} < 12)")
    if cpm < 22.0:
        reasons.append(f"每分钟有效文本量过低(cpm={cpm:.1f} < 22)")
    if chunked_mode_used and tc >= 2 and avg_chunk < 6.0 and pure < 28:
        reasons.append(
            f"分段均值过低(avg_chars_per_chunk={avg_chunk:.1f}, chunks={tc}, chars={pure})"
        )
    if float(speech_rate) < 22.0 and int(pause_count) > max(8, int(float(duration_sec) * 0.38)):
        reasons.append(
            f"语速极低且停顿偏多(speech_rate={speech_rate}, pause_count={pause_count})"
        )

    if reasons:
        stats["short_adequacy_gate_hit"] = True
        stats["short_adequacy_gate_reason"] = "; ".join(reasons)
        return True, stats["short_adequacy_gate_reason"], stats
    return False, "", stats


def _long_session_transcript_adequacy_gate(
    *,
    duration_sec: float,
    transcript: str,
    speech_rate: float,
    pause_count: int,
    transcribed_chunks: int,
    chunked_mode_used: bool,
) -> tuple[bool, str, dict[str, Any]]:
    """当 total_audio_duration_sec >= 60 时评估会话级转写是否足以采信。返回 (hit, reason, stats)。"""
    pure = len(re.sub(r"\s+", "", transcript or ""))
    duration_min = max(float(duration_sec) / 60.0, 1e-6)
    cpm = float(pure) / duration_min
    tc = max(int(transcribed_chunks or 0), 0)
    avg_chunk = float(pure) / max(tc, 1) if tc > 0 else float(pure)

    stats: dict[str, Any] = {
        "total_audio_duration_sec": round(float(duration_sec), 3),
        "transcript_chars_per_minute": round(cpm, 2),
        "avg_chars_per_chunk": round(avg_chunk, 2),
        "adequacy_gate_hit": False,
        "adequacy_gate_reason": "",
    }
    if duration_sec < LONG_SESSION_ADEQUACY_THRESHOLD_SEC:
        return False, "", stats

    reasons: list[str] = []

    # 总字符过低（随时长略升，避免 3 分钟仅几十字过关）
    min_chars = max(40.0, min(320.0, float(duration_sec) * 0.30))
    if pure < int(min_chars):
        reasons.append(f"总文本过短(chars={pure} < floor={min_chars:.0f})")

    # 每分钟有效文本量过低
    if cpm < 30.0:
        reasons.append(f"每分钟有效文本量过低(cpm={cpm:.1f} < 30)")

    # 分段模式下平均每段字符过低 + 总量不足
    if chunked_mode_used and tc >= 2 and avg_chunk < 12.0 and pure < 90:
        reasons.append(
            f"分段均值过低(avg_chars_per_chunk={avg_chunk:.1f}, chunks={tc}, chars={pure})"
        )

    # 语速极低且停顿过多（整段静音/碎片拼接）
    if float(speech_rate) < 22.0 and int(pause_count) > max(40, int(duration_sec * 0.45)):
        reasons.append(
            f"语速极低且停顿过多(speech_rate={speech_rate}, pause_count={pause_count})"
        )

    # 分段数多但总体信息量仍极低
    if tc >= 6 and pure < 72 and avg_chunk < 14.0:
        reasons.append(f"分段数多但信息量过低(chunks={tc}, chars={pure}, avg={avg_chunk:.1f})")

    if reasons:
        stats["adequacy_gate_hit"] = True
        stats["adequacy_gate_reason"] = "; ".join(reasons)
        return True, stats["adequacy_gate_reason"], stats
    return False, "", stats


def _speech_tune_v1_log(
    *,
    raw_transcript: str,
    cleaned_transcript: str,
    speech_rate: float | None,
    contamination_hit: bool,
    contamination_reason: str,
    audio_valid: bool,
    audio_message: str,
    note: str = "",
) -> None:
    """比赛/排障统一检索：`[ascend_service.speech.tune_v1]`。"""
    tail = f" note={note}" if note else ""
    print(
        "[ascend_service.speech.tune_v1] "
        f"raw_len={len(raw_transcript)} cleaned_len={len(cleaned_transcript)} "
        f"raw_preview={raw_transcript[:140]!r} cleaned_preview={cleaned_transcript[:140]!r} "
        f"speech_rate={speech_rate} "
        f"contamination_hit={contamination_hit} contamination_reason={contamination_reason!r} "
        f"audio_valid={audio_valid} audio_message={audio_message!r}"
        f"{tail}"
    )


def _invalid_audio_analysis_result(message: str = INVALID_AUDIO_MESSAGE) -> dict[str, Any]:
    return {
        "transcript": "",
        "merged_transcript": "",
        "speech_rate": 0.0,
        "pause_count": 0,
        "avg_pause_sec": 0.0,
        "filler_count": 0,
        "audio_valid": False,
        "audio_message": message,
        "total_audio_duration_sec": 0.0,
        "transcribed_chunks": 0,
        "skipped_chunks": 0,
        "dropped_dirty_chunks": 0,
        "total_chunks": 0,
        "chunked_mode_used": False,
        "audio_metrics_scope": "session_unavailable",
    }


def _finalize_audio_session_result(result: dict[str, Any], wav_path: str | None) -> dict[str, Any]:
    """整场会话级汇总字段：`transcript` 与 `merged_transcript` 在有效时一致；指标基于整段 wav。"""
    dur = 0.0
    if wav_path and os.path.isfile(wav_path):
        try:
            dur = float(AudioSegment.from_wav(wav_path).duration_seconds)
        except Exception:
            dur = 0.0
    dbg = _LAST_SPEECH_ANALYZE_DEBUG
    mt = str(result.get("transcript") or "")
    result["merged_transcript"] = mt
    result["total_audio_duration_sec"] = round(float(dur), 3)
    result["transcribed_chunks"] = int(dbg.get("transcribed_chunks") or 0)
    result["skipped_chunks"] = int(dbg.get("skipped_chunks") or 0)
    result["dropped_dirty_chunks"] = int(dbg.get("dropped_dirty_chunks") or 0)
    result["total_chunks"] = int(dbg.get("total_chunks") or 0)
    result["chunked_mode_used"] = bool(dbg.get("chunked_mode_used"))
    scope = result.get("audio_metrics_scope")
    if not scope:
        result["audio_metrics_scope"] = (
            "session_whole_file_merged_segments"
            if dbg.get("chunked_mode_used")
            else "session_whole_file_single_or_fallback"
        )
    return result


def _normalize_audio_to_wav(input_path: str) -> str:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("当前环境缺少 ffmpeg，无法解析上传音频")

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
            raise RuntimeError("音频标准化失败：输出 wav 文件为空")
        wav_audio = AudioSegment.from_wav(wav_path)
        print(
            "[ascend_service.speech.normalize] "
            f"source={input_path} wav={wav_path} size={os.path.getsize(wav_path)} "
            f"duration_sec={wav_audio.duration_seconds:.2f} dBFS={wav_audio.dBFS:.2f} "
            f"channels={wav_audio.channels} frame_rate={wav_audio.frame_rate}"
        )
        return wav_path
    except Exception as e:
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
        raise RuntimeError(f"音频标准化失败: {repr(e)}")


def _assess_speech_validity(wav_path: str) -> tuple[bool, dict[str, Any] | None]:
    try:
        audio = AudioSegment.from_wav(wav_path)
    except Exception as e:
        print(f"[ascend_service.speech.validity] 读取 wav 失败: {repr(e)}")
        return False, _invalid_audio_analysis_result()

    duration_sec = float(audio.duration_seconds)
    dbfs = audio.dBFS
    if duration_sec < MIN_VALID_DURATION_SEC:
        print(
            f"[ascend_service.speech.validity] reject duration_sec={duration_sec:.3f} "
            f"< {MIN_VALID_DURATION_SEC}"
        )
        return False, _invalid_audio_analysis_result()
    if dbfs == float("-inf") or dbfs < MIN_VALID_DBFS:
        print(f"[ascend_service.speech.validity] reject dBFS={dbfs} min={MIN_VALID_DBFS}")
        return False, _invalid_audio_analysis_result()

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
            f"[ascend_service.speech.validity] reject nonsilent_sec={nonsilent_sec:.3f} "
            f"< {MIN_VALID_NON_SILENT_SEC}"
        )
        return False, _invalid_audio_analysis_result()

    print(
        "[ascend_service.speech.validity] ok "
        f"duration_sec={duration_sec:.2f} dBFS={dbfs:.2f} nonsilent_sec={nonsilent_sec:.2f}"
    )
    return True, None


def _coerce_whisper_size(name: str, *, fallback: str) -> str:
    n = (name or "").strip().lower() or fallback
    allowed = {
        "tiny",
        "tiny.en",
        "base",
        "base.en",
        "small",
        "small.en",
        "medium",
        "medium.en",
        "large-v1",
        "large-v2",
        "large-v3",
    }
    return n if n in allowed else fallback


def _load_whisper_for_session(model_size_env: str, *, size_fallback: str = "small") -> Any:
    """进程内按 (model_size, device, compute_type) 单例复用，避免每请求重复加载。"""
    if WhisperModel is None:
        raise RuntimeError("当前环境缺少 faster-whisper 依赖")
    sz = _coerce_whisper_size(model_size_env, fallback=size_fallback)
    cache_key = f"{sz}|cpu|int8"
    hit = cache_key in _WHISPER_MODEL_SINGLETONS
    if not hit:
        print(
            "[ascend_service.speech.warmup] loading whisper model "
            f"size={sz!r} device='cpu' compute_type='int8'"
        )
        started = time.perf_counter()
        model = WhisperModel(sz, device="cpu", compute_type="int8")
        elapsed = time.perf_counter() - started
        print(f"[ascend_service.speech.warmup] whisper model loaded in {elapsed:.2f}s")
        _WHISPER_MODEL_SINGLETONS[cache_key] = model
    _LAST_WHISPER_SESSION.clear()
    _LAST_WHISPER_SESSION["model_size_used"] = sz
    _LAST_WHISPER_SESSION["model_cache_hit"] = bool(hit)
    return _WHISPER_MODEL_SINGLETONS[cache_key]


def _clean_transcript(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    cleaned = re.sub(r"([，。！？,.!?])\1{1,}", r"\1", cleaned)
    cleaned = re.sub(r"\b([\u4e00-\u9fff]{1,3})\s+\1\b", r"\1", cleaned)
    cleaned = re.sub(r"([\u4e00-\u9fff]{1,3})\1{2,}", r"\1", cleaned)
    return cleaned


def _transcribe_with_meta(
    wav_path: str, *, allow_nonsilent_chunk_fallback: bool = True
) -> tuple[str, str, list[dict[str, Any]]]:
    model = _load_whisper_for_session(WHISPER_MODEL_SIZE)
    wav_audio = AudioSegment.from_wav(wav_path)
    print(
        "[ascend_service.speech.transcribe.config] "
        f"model_size={_LAST_WHISPER_SESSION.get('model_size_used')!r} "
        f"model_cache_hit={_LAST_WHISPER_SESSION.get('model_cache_hit')} "
        f"language={TRANSCRIBE_LANGUAGE!r} "
        f"prompt={TRANSCRIBE_INITIAL_PROMPT!r} beam_size={TRANSCRIBE_BEAM_SIZE} "
        f"best_of={TRANSCRIBE_BEST_OF} temperature={TRANSCRIBE_TEMPERATURE} "
        f"allow_nonsilent_chunk_fallback={allow_nonsilent_chunk_fallback}"
    )

    single_vad_on = _transcribe_single_pass(model, wav_path, vad_filter=True)
    text = single_vad_on["text"]
    segment_meta = list(single_vad_on["segments"])
    selected_path = "single_vad_on"

    # 避免 VAD 在弱语音场景下吃掉中文短句：当首轮结果为空时，补一次 vad_filter=False
    if len(segment_meta) == 0 or len(re.sub(r"\s+", "", text)) == 0:
        single_vad_off = _transcribe_single_pass(model, wav_path, vad_filter=False)
        if len(re.sub(r"\s+", "", single_vad_off["text"])) > len(re.sub(r"\s+", "", text)):
            text = single_vad_off["text"]
            segment_meta = list(single_vad_off["segments"])
            selected_path = "single_vad_off"

    # 进一步兜底：非静音分段逐段转写（仅 **短于** LONG_AUDIO_CHUNKED_THRESHOLD_SEC 的链路；长音频只走固定窗分段）
    used_chunk_fallback = False
    if (
        allow_nonsilent_chunk_fallback
        and wav_audio.duration_seconds < LONG_AUDIO_CHUNKED_THRESHOLD_SEC
        and (
            wav_audio.duration_seconds >= 10
            or len(segment_meta) == 0
            or len(re.sub(r"\s+", "", text)) < 6
        )
    ):
        chunk_data = _transcribe_by_nonsilent_chunks(model, wav_audio, wav_path)
        if len(re.sub(r"\s+", "", chunk_data["text"])) > len(re.sub(r"\s+", "", text)):
            text = chunk_data["text"]
            segment_meta = list(chunk_data["segments"])
            selected_path = "chunk_fallback"
            used_chunk_fallback = True

    raw_transcript = str(text or "")
    transcript = _clean_transcript(raw_transcript)
    print(
        "[ascend_service.speech.transcribe] raw transcript before cleanup "
        f"len={len(raw_transcript)} preview={raw_transcript[:200]!r}"
    )
    print(
        "[ascend_service.speech.transcribe] cleaned transcript after cleanup "
        f"len={len(transcript)} preview={transcript[:200]!r}"
    )
    print(
        "[ascend_service.speech.transcribe] "
        f"selected_path={selected_path} used_chunk_fallback={used_chunk_fallback} "
        f"transcript_len={len(transcript)} preview={transcript[:200]!r} segments={len(segment_meta)}"
    )
    for idx, seg in enumerate(segment_meta):
        seg_text = str(seg.get("text") or "")
        print(
            "[ascend_service.speech.transcribe.segment] "
            f"idx={idx} text={seg_text[:120]!r} "
            f"no_speech_prob={seg.get('no_speech_prob')!r} "
            f"avg_logprob={seg.get('avg_logprob')!r} "
            f"compression_ratio={seg.get('compression_ratio')!r}"
        )
    return raw_transcript, transcript, segment_meta


def _transcribe_single_pass(
    model: Any,
    wav_path: str,
    *,
    vad_filter: bool,
    beam_size: int | None = None,
    best_of: int | None = None,
) -> dict[str, Any]:
    bs = int(TRANSCRIBE_BEAM_SIZE if beam_size is None else beam_size)
    bo = int(TRANSCRIBE_BEST_OF if best_of is None else best_of)
    bs = max(1, bs)
    bo = max(1, bo)
    print(
        f"[ascend_service.speech.transcribe.pass] wav={wav_path} vad_filter={vad_filter} "
        f"beam_size={bs} best_of={bo}"
    )
    segments, _ = model.transcribe(
        wav_path,
        language=TRANSCRIBE_LANGUAGE,
        task="transcribe",
        beam_size=bs,
        best_of=bo,
        vad_filter=vad_filter,
        temperature=TRANSCRIBE_TEMPERATURE,
        condition_on_previous_text=False,
        initial_prompt=TRANSCRIBE_INITIAL_PROMPT,
    )
    text_segments: list[str] = []
    segment_meta: list[dict[str, Any]] = []
    for seg in segments:
        seg_text = re.sub(r"\s+", " ", str(getattr(seg, "text", "") or "")).strip()
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
    merged = " ".join(text_segments).strip()
    print(
        "[ascend_service.speech.transcribe.pass] "
        f"vad_filter={vad_filter} segments={len(segment_meta)} merged_len={len(merged)}"
    )
    return {"text": merged, "segments": segment_meta}


def _transcribe_by_nonsilent_chunks(
    model: Any,
    wav_audio: AudioSegment,
    wav_path: str,
) -> dict[str, Any]:
    nonsilent_ranges = detect_nonsilent(
        wav_audio,
        min_silence_len=350,
        silence_thresh=wav_audio.dBFS - 18 if wav_audio.dBFS != float("-inf") else -42,
    )
    print(
        "[ascend_service.speech.transcribe.chunk] "
        f"ranges={len(nonsilent_ranges)} wav_duration={wav_audio.duration_seconds:.2f}"
    )
    if not nonsilent_ranges:
        return {"text": "", "segments": []}

    chunk_texts: list[str] = []
    all_segments_meta: list[dict[str, Any]] = []
    for idx, (start_ms, end_ms) in enumerate(nonsilent_ranges):
        duration_sec = (end_ms - start_ms) / 1000.0
        if duration_sec < CHUNK_MIN_NONSILENT_SEC:
            continue
        chunk = wav_audio[max(start_ms - 120, 0): min(end_ms + 120, len(wav_audio))]
        fd, chunk_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            chunk.export(
                chunk_path,
                format="wav",
                parameters=["-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le"],
            )
            chunk_data = _transcribe_single_pass(model, chunk_path, vad_filter=False)
            chunk_text = chunk_data["text"]
            print(
                "[ascend_service.speech.transcribe.chunk] "
                f"idx={idx} start_ms={start_ms} end_ms={end_ms} text={chunk_text[:120]!r}"
            )
            if chunk_text:
                chunk_texts.append(chunk_text)
            for seg in chunk_data["segments"]:
                merged = dict(seg)
                merged["chunk_start_ms"] = start_ms
                merged["chunk_end_ms"] = end_ms
                all_segments_meta.append(merged)
        except Exception as e:
            print(
                "[ascend_service.speech.transcribe.chunk] failed "
                f"idx={idx} source={wav_path} err={repr(e)}"
            )
        finally:
            if os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                except Exception:
                    pass
    return {"text": " ".join(chunk_texts).strip(), "segments": all_segments_meta}


def _iter_audio_chunks_ms(total_ms: int, chunk_ms: int, overlap_ms: int) -> list[tuple[int, int]]:
    chunk_ms = max(int(chunk_ms), 5000)
    step = max(1000, chunk_ms - max(0, int(overlap_ms)))
    out: list[tuple[int, int]] = []
    start = 0
    while start < total_ms:
        end = min(start + chunk_ms, total_ms)
        if end - start >= 800:
            out.append((start, end))
        start += step
    return out


def _fixed_window_chunk_is_valid(segment: AudioSegment) -> bool:
    """分段 V1：窗口内静音比例过高或过短则跳过 ASR，省时间、减幻觉。"""
    d_sec = float(len(segment)) / 1000.0
    if d_sec < 1.0:
        return False
    dbfs = segment.dBFS
    if dbfs == float("-inf") or dbfs < -58.0:
        return False
    silence_thresh = max(dbfs - 16.0, -55.0) if dbfs != float("-inf") else -50.0
    nonsilent_ranges = detect_nonsilent(
        segment,
        min_silence_len=NONSILENT_MIN_SILENCE_MS,
        silence_thresh=silence_thresh,
        seek_step=10,
    )
    nonsilent_sec = sum((e - s) for s, e in nonsilent_ranges) / 1000.0
    min_ns = max(0.9, d_sec * 0.10)
    if nonsilent_sec < min_ns:
        return False
    if nonsilent_sec / max(d_sec, 1e-6) < 0.06:
        return False
    return True


def _transcribe_chunked_v1(
    wav_path: str, *, analysis_phase: str = "lecture"
) -> tuple[str, str, list[dict[str, Any]], dict[str, Any]]:
    """长音频固定窗口 + 窗内门控 + 仅 vad_filter=True 分段 ASR，按时间顺序拼接。"""
    t0 = time.perf_counter()
    wav_audio = AudioSegment.from_wav(wav_path)
    total_ms = len(wav_audio)
    chunk_ms = int(max(5.0, AUDIO_CHUNK_SECONDS) * 1000)
    overlap_ms = int(max(0.0, AUDIO_CHUNK_OVERLAP_SECONDS) * 1000)
    windows = _iter_audio_chunks_ms(total_ms, chunk_ms, overlap_ms)
    model = _load_whisper_for_session(SPEECH_LONG_SESSION_MODEL_SIZE, size_fallback="small")
    chunk_texts: list[str] = []
    all_segments_meta: list[dict[str, Any]] = []
    skipped = 0
    asr_runs = 0
    dropped_dirty = 0
    for wi, (s_ms, e_ms) in enumerate(windows):
        seg_audio = wav_audio[s_ms:e_ms]
        if not _fixed_window_chunk_is_valid(seg_audio):
            skipped += 1
            print(
                "[ascend_service.speech.chunked_v1] skip "
                f"wi={wi} start_ms={s_ms} end_ms={e_ms} reason=chunk_gate"
            )
            continue
        fd, chunk_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            seg_audio.export(
                chunk_path,
                format="wav",
                parameters=["-ac", "1", "-ar", "16000", "-acodec", "pcm_s16le"],
            )
            chunk_data = _transcribe_single_pass(
                model,
                chunk_path,
                vad_filter=True,
                beam_size=SPEECH_LONG_TRANSCRIBE_BEAM_SIZE,
                best_of=SPEECH_LONG_TRANSCRIBE_BEST_OF,
            )
            asr_runs += 1
            raw_piece = str(chunk_data.get("text") or "")
            cleaned_piece = _clean_transcript(raw_piece)
            seg_list = list(chunk_data.get("segments") or [])
            dirty, dirty_reason = _chunk_asr_output_is_dirty(
                raw_piece, cleaned_piece, seg_list, analysis_phase=analysis_phase
            )
            if dirty:
                dropped_dirty += 1
                print(
                    "[ascend_service.speech.chunked_v1] drop_dirty "
                    f"wi={wi} start_ms={s_ms} end_ms={e_ms} reason={dirty_reason!r} "
                    f"preview={cleaned_piece[:80]!r}"
                )
                continue
            if cleaned_piece:
                chunk_texts.append(cleaned_piece)
            off_sec = s_ms / 1000.0
            for seg in seg_list:
                merged = dict(seg)
                merged["window_start_sec"] = off_sec
                all_segments_meta.append(merged)
            print(
                "[ascend_service.speech.chunked_v1] ok "
                f"wi={wi} start_ms={s_ms} end_ms={e_ms} piece_len={len(cleaned_piece)}"
            )
        except Exception as e:
            skipped += 1
            print(f"[ascend_service.speech.chunked_v1] asr_fail wi={wi} err={repr(e)}")
        finally:
            if os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                except Exception:
                    pass

    raw = " ".join(chunk_texts).strip()
    cleaned = _clean_transcript(raw)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    kept_chunks = max(0, asr_runs - dropped_dirty)
    stats: dict[str, Any] = {
        "chunked_mode_used": True,
        "total_chunks": len(windows),
        "skipped_chunks": skipped,
        "transcribed_chunks": kept_chunks,
        "dropped_dirty_chunks": dropped_dirty,
        "chunk_asr_runs": asr_runs,
        "merged_transcript_length": len(cleaned),
        "total_elapsed_ms": round(float(elapsed_ms), 1),
        "model_size_used": _LAST_WHISPER_SESSION.get("model_size_used"),
        "model_cache_hit": _LAST_WHISPER_SESSION.get("model_cache_hit"),
        "long_asr_beam_size": SPEECH_LONG_TRANSCRIBE_BEAM_SIZE,
        "long_asr_best_of": SPEECH_LONG_TRANSCRIBE_BEST_OF,
    }
    print(
        "[ascend_service.speech.chunked_v1] summary "
        f"model_size_used={stats.get('model_size_used')} model_cache_hit={stats.get('model_cache_hit')} "
        f"long_beam={SPEECH_LONG_TRANSCRIBE_BEAM_SIZE} long_best_of={SPEECH_LONG_TRANSCRIBE_BEST_OF} "
        f"total_chunks={stats['total_chunks']} skipped_chunks={skipped} "
        f"chunk_asr_runs={asr_runs} dropped_dirty_chunks={dropped_dirty} "
        f"transcribed_chunks={kept_chunks} merged_transcript_length={len(cleaned)} "
        f"total_elapsed_ms={stats['total_elapsed_ms']:.1f}"
    )
    return raw, cleaned, all_segments_meta, stats


def _extract_blacklist_hits(transcript: str) -> tuple[int, float]:
    pure_text = re.sub(r"\s+", "", transcript or "")
    if not pure_text:
        return 0, 0.0
    hit_chars = 0
    hit_count = 0
    for phrase in HALLUCINATION_BLACKLIST_PHRASES:
        cnt = pure_text.count(phrase)
        hit_count += cnt
        hit_chars += cnt * len(phrase)
    hit_ratio = float(hit_chars) / max(float(len(pure_text)), 1.0)
    return hit_count, hit_ratio


def _detect_template_contamination(raw_transcript: str, cleaned_transcript: str) -> tuple[bool, str]:
    raw = str(raw_transcript or "").strip()
    cleaned = str(cleaned_transcript or "").strip()
    raw_compact = re.sub(r"\s+", "", raw)
    cleaned_compact = re.sub(r"\s+", "", cleaned)

    for phrase in TEMPLATE_CONTAMINATION_PHRASES:
        phrase_compact = re.sub(r"\s+", "", phrase)
        if phrase_compact and (
            phrase_compact in raw_compact or phrase_compact in cleaned_compact
        ):
            return True, f"命中模板污染短语: {phrase}"

    if cleaned_compact:
        unique_chars = len(set(cleaned_compact))
        unique_ratio = unique_chars / max(len(cleaned_compact), 1)
        repeated_template = any(
            cleaned_compact.count(re.sub(r"\s+", "", phrase)) >= 2
            for phrase in TEMPLATE_CONTAMINATION_PHRASES
        )
        if repeated_template:
            return True, "模板污染短语重复出现"
        if len(cleaned_compact) <= 8 and any(k in cleaned_compact for k in ("转写", "录音", "中文")):
            return True, "低信息量模板文本"
        if len(cleaned_compact) <= 12 and unique_ratio <= 0.35:
            return True, "低信息量重复文本"

    return False, ""


def _normalize_for_template_match(text: str) -> str:
    normalized = str(text or "")
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", normalized)
    return normalized


def _compress_repeated_sentences(text: str) -> str:
    normalized = re.sub(r"[。！？!?；;，,]+", "。", str(text or "").strip())
    parts = [p.strip() for p in normalized.split("。") if p.strip()]
    compressed: list[str] = []
    for part in parts:
        if not compressed or compressed[-1] != part:
            compressed.append(part)
    return "。".join(compressed)


def _final_template_contamination_gate(
    raw_transcript: str,
    cleaned_transcript: str,
    *,
    analysis_phase: str = "lecture",
) -> tuple[bool, str]:
    phase = _normalize_speech_analysis_phase(analysis_phase)
    raw_text = str(raw_transcript or "").strip()
    cleaned_text = str(cleaned_transcript or "").strip()
    final_before_gate = cleaned_text or raw_text
    no_space = re.sub(r"\s+", "", final_before_gate)
    no_punct = _normalize_for_template_match(final_before_gate)
    compressed = _compress_repeated_sentences(final_before_gate)
    compressed_norm = _normalize_for_template_match(compressed)

    phrase_hits = 0
    matched_phrases: list[str] = []
    for phrase in TEMPLATE_CONTAMINATION_PHRASES:
        phrase_norm = _normalize_for_template_match(phrase)
        if not phrase_norm:
            continue
        if (
            phrase_norm in _normalize_for_template_match(raw_text)
            or phrase_norm in _normalize_for_template_match(cleaned_text)
            or phrase_norm in no_punct
            or phrase_norm in compressed_norm
        ):
            phrase_hits += 1
            matched_phrases.append(phrase)

    if matched_phrases:
        return True, f"命中最终模板污染短语: {matched_phrases}"

    repeated_template = False
    template_chars = 0
    for phrase in TEMPLATE_CONTAMINATION_PHRASES:
        phrase_norm = _normalize_for_template_match(phrase)
        cnt = no_punct.count(phrase_norm) if phrase_norm else 0
        if cnt >= 2:
            repeated_template = True
        template_chars += cnt * len(phrase_norm)
    if repeated_template:
        return True, "模板句重复污染（同一句模板短语重复 >= 2 次）"

    total_chars = len(no_punct)
    if total_chars > 0:
        template_ratio = template_chars / max(total_chars, 1)
        if template_ratio >= 0.5:
            return True, f"模板短语占比过高: ratio={template_ratio:.2f}"

    hanzi_chars = re.findall(r"[\u4e00-\u9fff]", final_before_gate)
    unique_hanzi = len(set(hanzi_chars))
    unique_ratio = unique_hanzi / max(len(hanzi_chars), 1) if hanzi_chars else 0.0
    if phase == "qa_answer":
        legit = _is_legit_short_qa_answer(final_before_gate)
        print(f"[ascend_service.speech.qa_short_answer] legit_short_answer={legit}")
        if legit:
            print(
                "[ascend_service.speech.final_gate] "
                f"phase={phase} low_info_rule_applied=False rule=skip_low_info_for_legit_qa_short"
            )
            return False, ""
    if len(hanzi_chars) <= 10 and unique_hanzi <= 4:
        print(f"[ascend_service.speech.final_gate] phase={phase} low_info_rule_applied=True")
        return True, "低信息量文本（有效汉字种类过少）"
    if len(hanzi_chars) <= 14 and unique_ratio <= 0.35:
        print(f"[ascend_service.speech.final_gate] phase={phase} low_info_rule_applied=True")
        return True, "低信息量文本（重复度过高）"
    if len(hanzi_chars) <= 12 and any(k in final_before_gate for k in ("转写", "录音", "中文", "现场")):
        print(f"[ascend_service.speech.final_gate] phase={phase} low_info_rule_applied=True")
        return True, "低信息量文本（明显像提示模板）"

    print(f"[ascend_service.speech.final_gate] phase={phase} low_info_rule_applied=False")
    return False, ""


def _force_invalid_due_to_contamination(
    reason: str,
    *,
    raw_transcript: str,
    cleaned_transcript: str,
    final_before_gate: str,
    analysis_phase: str = "lecture",
) -> dict[str, Any]:
    result = _invalid_audio_analysis_result(TEMPLATE_CONTAMINATION_MESSAGE)
    result.update(
        {
            "transcript": "",
            "speech_rate": 0,
            "pause_count": 0,
            "avg_pause_sec": 0,
            "filler_count": 0,
            "audio_valid": False,
            "audio_message": TEMPLATE_CONTAMINATION_MESSAGE,
        }
    )
    ph = _normalize_speech_analysis_phase(analysis_phase)
    print(
        "[ascend_service.speech.final_gate] "
        f"phase={ph} "
        f"raw_transcript={raw_transcript[:200]!r} "
        f"cleaned_transcript={cleaned_transcript[:200]!r} "
        f"final_transcript_before_contamination_gate={final_before_gate[:200]!r} "
        f"contamination_hit=True contamination_reason={reason!r} "
        f"final_transcript_after_contamination_gate='' "
        f"final_audio_valid={result['audio_valid']} "
        f"final_audio_message={result['audio_message']!r}"
    )
    _speech_tune_v1_log(
        raw_transcript=raw_transcript,
        cleaned_transcript=cleaned_transcript,
        speech_rate=None,
        contamination_hit=True,
        contamination_reason=reason,
        audio_valid=False,
        audio_message=str(result.get("audio_message") or ""),
        note="final_contamination_gate",
    )
    return result


def _detect_repeat_spam_transcript(text: str) -> tuple[bool, str]:
    """短片段异常重复（非口吃自然重复），多见于伪转写。"""
    t = re.sub(r"\s+", "", text or "")
    if len(t) < 14:
        return False, ""
    counts: dict[str, int] = {}
    for i in range(len(t) - 1):
        bg = t[i : i + 2]
        if len(bg) < 2:
            continue
        counts[bg] = counts.get(bg, 0) + 1
    max_rep = max(counts.values()) if counts else 0
    if max_rep >= 6 and max_rep * 2 >= len(t) * 0.35:
        return True, "异常重复双字片段占比过高（疑似伪转写）"
    return False, ""


def _chunk_asr_output_is_dirty(
    raw_piece: str,
    cleaned_piece: str,
    seg_meta: list[dict[str, Any]],
    *,
    analysis_phase: str = "lecture",
) -> tuple[bool, str]:
    """分段 ASR 后立即过滤：避免垃圾段拼进全文后才被总闸门打爆。"""
    hit, reason = _detect_template_contamination(raw_piece, cleaned_piece)
    if hit:
        return True, reason
    if _normalize_speech_analysis_phase(analysis_phase) == "qa_answer" and _is_legit_short_qa_answer(
        cleaned_piece
    ):
        return False, ""
    spam_hit, spam_reason = _detect_repeat_spam_transcript(cleaned_piece)
    if spam_hit:
        return True, spam_reason
    pure = re.sub(r"\s+", "", cleaned_piece or "")
    if len(pure) >= 6:
        probs = [
            float(s["no_speech_prob"])
            for s in seg_meta
            if isinstance(s.get("no_speech_prob"), (int, float))
        ]
        if probs:
            avg_ns = sum(probs) / len(probs)
            if avg_ns >= 0.84 and len(pure) <= 48:
                return True, "分段 no_speech 偏高且文本过短"
    if len(pure) >= 4:
        blacklist_count, blacklist_ratio = _extract_blacklist_hits(cleaned_piece)
        if blacklist_count >= 1 and blacklist_ratio >= 0.45 and len(pure) <= 80:
            return True, "分段黑名单短语占比过高"
    return False, ""


def _speech_rate_looks_pseudo(
    speech_rate: float, duration_sec: float, pure_text_len: int
) -> tuple[bool, str]:
    if speech_rate <= MAX_REASONABLE_SPEECH_RATE:
        return False, ""
    if duration_sec < SPEECH_RATE_SUSPICIOUS_DURATION_SEC and pure_text_len < SPEECH_RATE_SUSPICIOUS_CHAR_LEN:
        return True, "语速异常偏高且内容过短，疑似不稳定转写"
    if speech_rate >= 620:
        return True, "语速指标异常偏高，疑似伪转写"
    return False, ""


def _assess_asr_quality(transcript: str, segments_meta: list[dict[str, Any]]) -> tuple[bool, str]:
    pure_text = re.sub(r"\s+", "", transcript or "")
    if len(pure_text) == 0:
        return False, "转写文本为空"

    hit_count, hit_ratio = _extract_blacklist_hits(pure_text)
    no_speech_probs = [
        float(seg["no_speech_prob"])
        for seg in segments_meta
        if isinstance(seg.get("no_speech_prob"), (float, int))
    ]
    avg_no_speech = sum(no_speech_probs) / len(no_speech_probs) if no_speech_probs else None
    print(
        "[ascend_service.speech.quality] "
        f"text_len={len(pure_text)} hit_count={hit_count} hit_ratio={hit_ratio:.2f} "
        f"avg_no_speech={avg_no_speech} segments={len(segments_meta)}"
    )

    if hit_count >= 2 and hit_ratio >= 0.60:
        return False, "转写文本主要由黑名单短语组成"
    # 略放宽：边缘帧略多 no_speech 时仍允许通过，减少误判
    if avg_no_speech is not None and avg_no_speech >= 0.88:
        return False, "no_speech_prob 指示低质量"
    spam_hit, spam_reason = _detect_repeat_spam_transcript(transcript)
    if spam_hit:
        return False, spam_reason
    return True, "通过第二层 ASR 质量判定"


def _analyze_audio_metrics(wav_path: str, transcript: str) -> dict[str, Any]:
    audio = AudioSegment.from_wav(wav_path)
    duration_sec = max(float(audio.duration_seconds), 1e-6)
    duration_min = duration_sec / 60.0
    silence_ranges = detect_silence(
        audio,
        min_silence_len=400,
        silence_thresh=audio.dBFS - 16 if audio.dBFS != float("-inf") else -40,
    )
    pause_durations = [(end - start) / 1000.0 for start, end in silence_ranges if (end - start) >= 400]
    pause_count = len(pause_durations)
    avg_pause_sec = (sum(pause_durations) / pause_count) if pause_count > 0 else 0.0

    pure_text = re.sub(r"\s+", "", transcript or "")
    speech_rate = (len(pure_text) / duration_min) if len(pure_text) >= 2 else 0.0
    fillers = ["然后", "就是", "那个", "嗯", "呃", "所以"]
    filler_count = sum((transcript or "").count(f) for f in fillers)
    metrics = {
        "speech_rate": round(float(speech_rate), 2),
        "pause_count": int(pause_count),
        "avg_pause_sec": round(float(avg_pause_sec), 2),
        "filler_count": int(filler_count),
        "audio_metrics_scope": "session_whole_file",
    }
    print(f"[ascend_service.speech.metrics] {metrics}")
    return metrics


def analyze_audio(audio_path: str, *, analysis_phase: str | None = None) -> dict[str, Any]:
    global _LAST_SPEECH_ANALYZE_DEBUG
    t_analyze_wall = time.perf_counter()
    _LAST_SPEECH_ANALYZE_DEBUG = {
        "chunked_mode_used": False,
        "total_chunks": 0,
        "skipped_chunks": 0,
        "transcribed_chunks": 0,
        "dropped_dirty_chunks": 0,
        "merged_transcript_length": 0,
        "total_elapsed_ms": 0.0,
        "chunk_asr_elapsed_ms": None,
        "model_size_used": None,
        "model_cache_hit": None,
        "normalize_elapsed_ms": None,
        "metrics_elapsed_ms": None,
        "final_gate_elapsed_ms": None,
    }
    source_path = str(audio_path or "").strip()
    if not source_path:
        result = _invalid_audio_analysis_result("上传音频为空")
        print(f"[ascend_service.speech] invalid input: {result}")
        _LAST_SPEECH_ANALYZE_DEBUG["total_elapsed_ms"] = round(
            (time.perf_counter() - t_analyze_wall) * 1000.0, 1
        )
        return _finalize_audio_session_result(result, None)
    if not os.path.exists(source_path):
        result = _invalid_audio_analysis_result("上传音频不存在")
        print(f"[ascend_service.speech] invalid input path={source_path}")
        _LAST_SPEECH_ANALYZE_DEBUG["total_elapsed_ms"] = round(
            (time.perf_counter() - t_analyze_wall) * 1000.0, 1
        )
        return _finalize_audio_session_result(result, None)
    source_size = os.path.getsize(source_path)
    phase_resolved = _normalize_speech_analysis_phase(analysis_phase)
    print(f"[ascend_service.speech] input path={source_path} size={source_size} phase={phase_resolved}")

    wav_path = ""
    analyze_timings: dict[str, float | None] = {
        "normalize_elapsed_ms": None,
        "chunk_asr_elapsed_ms": None,
        "metrics_elapsed_ms": None,
        "final_gate_elapsed_ms": None,
    }
    try:
        t_norm0 = time.perf_counter()
        wav_path = _normalize_audio_to_wav(source_path)
        analyze_timings["normalize_elapsed_ms"] = round(
            (time.perf_counter() - t_norm0) * 1000.0, 1
        )
        valid, invalid_payload = _assess_speech_validity(wav_path)
        if not valid:
            assert invalid_payload is not None
            print(
                "[ascend_service.speech.summary] raw_len=0 cleaned_len=0 audio_valid=False "
                f"audio_message={invalid_payload.get('audio_message')!r} "
                "contamination_hit=False reason=validity_gate"
            )
            _speech_tune_v1_log(
                raw_transcript="",
                cleaned_transcript="",
                speech_rate=None,
                contamination_hit=False,
                contamination_reason="",
                audio_valid=False,
                audio_message=str(invalid_payload.get("audio_message") or ""),
                note="validity_gate",
            )
            return _finalize_audio_session_result(invalid_payload, wav_path)

        wav_probe = AudioSegment.from_wav(wav_path)
        duration_sec = float(wav_probe.duration_seconds)
        t_chunk0 = time.perf_counter()
        if duration_sec >= LONG_AUDIO_CHUNKED_THRESHOLD_SEC:
            print(
                "[ascend_service.speech] using chunked ASR v1 "
                f"duration_sec={duration_sec:.2f} >= threshold={LONG_AUDIO_CHUNKED_THRESHOLD_SEC} "
                f"chunk_sec={AUDIO_CHUNK_SECONDS} overlap_sec={AUDIO_CHUNK_OVERLAP_SECONDS}"
            )
            raw_transcript, transcript, segments_meta, ch_stats = _transcribe_chunked_v1(
                wav_path, analysis_phase=phase_resolved
            )
            _LAST_SPEECH_ANALYZE_DEBUG.update(ch_stats)
            _LAST_SPEECH_ANALYZE_DEBUG["chunk_asr_elapsed_ms"] = ch_stats.get("total_elapsed_ms")
        else:
            raw_transcript, transcript, segments_meta = _transcribe_with_meta(
                wav_path, allow_nonsilent_chunk_fallback=True
            )
            _LAST_SPEECH_ANALYZE_DEBUG.update(
                {
                    "chunked_mode_used": False,
                    "total_chunks": 1,
                    "skipped_chunks": 0,
                    "transcribed_chunks": 1 if len((transcript or "").strip()) > 0 else 0,
                    "dropped_dirty_chunks": 0,
                    "merged_transcript_length": len(transcript),
                    "model_size_used": _LAST_WHISPER_SESSION.get("model_size_used"),
                    "model_cache_hit": _LAST_WHISPER_SESSION.get("model_cache_hit"),
                }
            )
        contamination_hit, contamination_reason = _detect_template_contamination(raw_transcript, transcript)
        print(
            "[ascend_service.speech.contamination] "
            f"raw_transcript={raw_transcript[:200]!r} cleaned_transcript={transcript[:200]!r} "
            f"contamination_hit={contamination_hit} contamination_reason={contamination_reason!r}"
        )
        if contamination_hit:
            analyze_timings["chunk_asr_elapsed_ms"] = round(
                (time.perf_counter() - t_chunk0) * 1000.0, 1
            )
            return _finalize_audio_session_result(
                _force_invalid_due_to_contamination(
                    contamination_reason,
                    raw_transcript=raw_transcript,
                    cleaned_transcript=transcript,
                    final_before_gate=transcript,
                    analysis_phase=phase_resolved,
                ),
                wav_path,
            )
        quality_ok, quality_reason = _assess_asr_quality(transcript, segments_meta)
        print(f"[ascend_service.speech] quality_reason={quality_reason!r}")
        if not quality_ok:
            analyze_timings["chunk_asr_elapsed_ms"] = round(
                (time.perf_counter() - t_chunk0) * 1000.0, 1
            )
            result = _invalid_audio_analysis_result()
            result["transcript"] = ""
            print(
                "[ascend_service.speech.summary] "
                f"raw_len={len(raw_transcript)} cleaned_len={len(transcript)} audio_valid=False "
                f"audio_message={result['audio_message']!r} contamination_hit=False "
                f"quality_fail={quality_reason!r}"
            )
            _speech_tune_v1_log(
                raw_transcript=raw_transcript,
                cleaned_transcript=transcript,
                speech_rate=None,
                contamination_hit=False,
                contamination_reason="",
                audio_valid=False,
                audio_message=str(result.get("audio_message") or ""),
                note=f"quality_fail:{quality_reason}",
            )
            return _finalize_audio_session_result(result, wav_path)

        analyze_timings["chunk_asr_elapsed_ms"] = round(
            (time.perf_counter() - t_chunk0) * 1000.0, 1
        )

        t_metrics0 = time.perf_counter()
        metrics = _analyze_audio_metrics(wav_path, transcript)
        analyze_timings["metrics_elapsed_ms"] = round(
            (time.perf_counter() - t_metrics0) * 1000.0, 1
        )
        duration_sec = float(wav_probe.duration_seconds)
        pure_len = len(re.sub(r"\s+", "", transcript or ""))
        t_final_gate0 = time.perf_counter()
        rate_bad, rate_reason = _speech_rate_looks_pseudo(
            float(metrics.get("speech_rate") or 0.0), duration_sec, pure_len
        )
        if rate_bad:
            analyze_timings["final_gate_elapsed_ms"] = round(
                (time.perf_counter() - t_final_gate0) * 1000.0, 1
            )
            bad = _invalid_audio_analysis_result(rate_reason)
            print(
                "[ascend_service.speech] final audio_valid=False "
                f"speech_rate_suspicious reason={rate_reason!r} "
                f"speech_rate={metrics.get('speech_rate')} duration_sec={duration_sec:.2f} "
                f"pure_len={pure_len}"
            )
            _speech_tune_v1_log(
                raw_transcript=raw_transcript,
                cleaned_transcript=transcript,
                speech_rate=float(metrics.get("speech_rate") or 0.0),
                contamination_hit=False,
                contamination_reason="",
                audio_valid=False,
                audio_message=str(bad.get("audio_message") or ""),
                note=f"speech_rate_pseudo:{rate_reason}",
            )
            return _finalize_audio_session_result(bad, wav_path)

        dbg_pre = dict(_LAST_SPEECH_ANALYZE_DEBUG)
        short_hit, short_reason, short_stats = _short_session_transcript_adequacy_gate(
            duration_sec=duration_sec,
            transcript=transcript,
            speech_rate=float(metrics.get("speech_rate") or 0.0),
            pause_count=int(metrics.get("pause_count") or 0),
            transcribed_chunks=int(dbg_pre.get("transcribed_chunks") or 0),
            chunked_mode_used=bool(dbg_pre.get("chunked_mode_used")),
            analysis_phase=phase_resolved,
        )
        print(
            "[ascend_service.speech.short_adequacy] "
            f"short_adequacy_gate_hit={short_stats.get('short_adequacy_gate_hit')} "
            f"short_adequacy_gate_reason={short_stats.get('short_adequacy_gate_reason')!r} "
            f"total_audio_duration_sec={short_stats.get('total_audio_duration_sec')} "
            f"transcript_chars_per_minute={short_stats.get('transcript_chars_per_minute')} "
            f"avg_chars_per_chunk={short_stats.get('avg_chars_per_chunk')} "
            f"chunked_mode_used={dbg_pre.get('chunked_mode_used')}"
        )
        if short_hit:
            analyze_timings["final_gate_elapsed_ms"] = round(
                (time.perf_counter() - t_final_gate0) * 1000.0, 1
            )
            bad = _invalid_audio_analysis_result(ADEQUACY_GATE_FAIL_MESSAGE)
            bad.update(
                {
                    "short_adequacy_gate_hit": True,
                    "short_adequacy_gate_reason": short_reason,
                    "adequacy_gate_hit": False,
                    "adequacy_gate_reason": "",
                    "transcript_chars_per_minute": short_stats.get("transcript_chars_per_minute"),
                    "avg_chars_per_chunk": short_stats.get("avg_chars_per_chunk"),
                }
            )
            _speech_tune_v1_log(
                raw_transcript=raw_transcript,
                cleaned_transcript=transcript,
                speech_rate=float(metrics.get("speech_rate") or 0.0),
                contamination_hit=False,
                contamination_reason="",
                audio_valid=False,
                audio_message=str(bad.get("audio_message") or ""),
                note=f"short_adequacy_gate:{short_reason[:120]}",
            )
            return _finalize_audio_session_result(bad, wav_path)

        adeq_hit, adeq_reason, adeq_stats = _long_session_transcript_adequacy_gate(
            duration_sec=duration_sec,
            transcript=transcript,
            speech_rate=float(metrics.get("speech_rate") or 0.0),
            pause_count=int(metrics.get("pause_count") or 0),
            transcribed_chunks=int(dbg_pre.get("transcribed_chunks") or 0),
            chunked_mode_used=bool(dbg_pre.get("chunked_mode_used")),
        )
        print(
            "[ascend_service.speech.adequacy] "
            f"total_audio_duration_sec={adeq_stats.get('total_audio_duration_sec')} "
            f"transcript_chars_per_minute={adeq_stats.get('transcript_chars_per_minute')} "
            f"avg_chars_per_chunk={adeq_stats.get('avg_chars_per_chunk')} "
            f"adequacy_gate_hit={adeq_stats.get('adequacy_gate_hit')} "
            f"adequacy_gate_reason={adeq_stats.get('adequacy_gate_reason')!r}"
        )
        if adeq_hit:
            analyze_timings["final_gate_elapsed_ms"] = round(
                (time.perf_counter() - t_final_gate0) * 1000.0, 1
            )
            bad = _invalid_audio_analysis_result(ADEQUACY_GATE_FAIL_MESSAGE)
            bad.update(
                {
                    "adequacy_gate_hit": True,
                    "adequacy_gate_reason": adeq_reason,
                    "short_adequacy_gate_hit": False,
                    "short_adequacy_gate_reason": "",
                    "transcript_chars_per_minute": adeq_stats.get("transcript_chars_per_minute"),
                    "avg_chars_per_chunk": adeq_stats.get("avg_chars_per_chunk"),
                }
            )
            _speech_tune_v1_log(
                raw_transcript=raw_transcript,
                cleaned_transcript=transcript,
                speech_rate=float(metrics.get("speech_rate") or 0.0),
                contamination_hit=False,
                contamination_reason="",
                audio_valid=False,
                audio_message=str(bad.get("audio_message") or ""),
                note=f"adequacy_gate:{adeq_reason[:120]}",
            )
            return _finalize_audio_session_result(bad, wav_path)

        result = {
            "transcript": transcript,
            **metrics,
            "audio_valid": True,
            "audio_message": "",
            "adequacy_gate_hit": False,
            "adequacy_gate_reason": "",
            "short_adequacy_gate_hit": False,
            "short_adequacy_gate_reason": "",
            "transcript_chars_per_minute": adeq_stats.get("transcript_chars_per_minute"),
            "avg_chars_per_chunk": adeq_stats.get("avg_chars_per_chunk"),
        }
        final_before_gate = str(result.get("transcript") or "")
        final_hit, final_reason = _final_template_contamination_gate(
            raw_transcript, final_before_gate, analysis_phase=phase_resolved
        )
        if final_hit:
            analyze_timings["final_gate_elapsed_ms"] = round(
                (time.perf_counter() - t_final_gate0) * 1000.0, 1
            )
            return _finalize_audio_session_result(
                _force_invalid_due_to_contamination(
                    final_reason,
                    raw_transcript=raw_transcript,
                    cleaned_transcript=transcript,
                    final_before_gate=final_before_gate,
                    analysis_phase=phase_resolved,
                ),
                wav_path,
            )
        print(
            "[ascend_service.speech.final_gate] "
            f"phase={phase_resolved} "
            f"raw_transcript={raw_transcript[:200]!r} "
            f"cleaned_transcript={transcript[:200]!r} "
            f"final_transcript_before_contamination_gate={final_before_gate[:200]!r} "
            f"contamination_hit=False contamination_reason='' "
            f"final_transcript_after_contamination_gate={final_before_gate[:200]!r} "
            f"final_audio_valid={result['audio_valid']} "
            f"final_audio_message={result['audio_message']!r}"
        )
        print(
            "[ascend_service.speech.summary] "
            f"raw_len={len(raw_transcript)} cleaned_len={len(transcript)} "
            f"audio_valid={result['audio_valid']} audio_message={result['audio_message']!r} "
            f"contamination_hit=False contamination_reason='' "
            f"speech_rate={metrics.get('speech_rate')} pause_count={metrics.get('pause_count')} "
            f"cleaned_preview={transcript[:160]!r}"
        )
        _speech_tune_v1_log(
            raw_transcript=raw_transcript,
            cleaned_transcript=transcript,
            speech_rate=float(metrics.get("speech_rate") or 0.0),
            contamination_hit=False,
            contamination_reason="",
            audio_valid=True,
            audio_message="",
            note="ok",
        )
        analyze_timings["final_gate_elapsed_ms"] = round(
            (time.perf_counter() - t_final_gate0) * 1000.0, 1
        )
        return _finalize_audio_session_result(result, wav_path)
    except Exception as e:
        result = _invalid_audio_analysis_result("语音分析失败，请重试")
        print(f"[ascend_service.speech] analyze failed err={repr(e)} fallback={result}")
        _speech_tune_v1_log(
            raw_transcript="",
            cleaned_transcript="",
            speech_rate=None,
            contamination_hit=False,
            contamination_reason="",
            audio_valid=False,
            audio_message=str(result.get("audio_message") or ""),
            note=f"exception:{repr(e)[:120]}",
        )
        return _finalize_audio_session_result(result, wav_path if wav_path else None)
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
        wall_ms = (time.perf_counter() - t_analyze_wall) * 1000.0
        _LAST_SPEECH_ANALYZE_DEBUG["total_elapsed_ms"] = round(float(wall_ms), 1)
        _LAST_SPEECH_ANALYZE_DEBUG["normalize_elapsed_ms"] = analyze_timings.get("normalize_elapsed_ms")
        _LAST_SPEECH_ANALYZE_DEBUG["metrics_elapsed_ms"] = analyze_timings.get("metrics_elapsed_ms")
        _LAST_SPEECH_ANALYZE_DEBUG["final_gate_elapsed_ms"] = analyze_timings.get("final_gate_elapsed_ms")
        print(
            "[ascend_service.speech.analyze_wall] "
            f"total_elapsed_ms={_LAST_SPEECH_ANALYZE_DEBUG['total_elapsed_ms']:.1f} "
            f"chunked_mode_used={_LAST_SPEECH_ANALYZE_DEBUG.get('chunked_mode_used')} "
            f"model_size_used={_LAST_SPEECH_ANALYZE_DEBUG.get('model_size_used')} "
            f"model_cache_hit={_LAST_SPEECH_ANALYZE_DEBUG.get('model_cache_hit')}"
        )
        if analyze_timings:
            print(
                "[ascend_service.speech.timing_breakdown] "
                f"model_size_used={_LAST_SPEECH_ANALYZE_DEBUG.get('model_size_used')} "
                f"model_cache_hit={_LAST_SPEECH_ANALYZE_DEBUG.get('model_cache_hit')} "
                f"normalize_elapsed_ms={analyze_timings.get('normalize_elapsed_ms')} "
                f"chunk_asr_elapsed_ms={analyze_timings.get('chunk_asr_elapsed_ms')} "
                f"(含转写后污染检测与 ASR 质量闸门) "
                f"metrics_elapsed_ms={analyze_timings.get('metrics_elapsed_ms')} "
                f"final_gate_elapsed_ms={analyze_timings.get('final_gate_elapsed_ms')} "
                f"(语速异常/充分性闸门/最终模板闸门) "
                f"total_elapsed_ms={_LAST_SPEECH_ANALYZE_DEBUG['total_elapsed_ms']:.1f}"
            )


def analyze_speech(payload: dict) -> dict:
    audio_path = str((payload or {}).get("audio_path") or "").strip()
    return analyze_audio(audio_path)

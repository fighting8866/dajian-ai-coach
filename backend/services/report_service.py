class ReportService:
    """训练报告整理服务（第一版）"""

    def build_report(self, result_data: dict) -> dict:
        session_id = result_data.get("session_id", "")
        summary = result_data.get("summary") or {}
        return {
            "session_id": session_id,
            "basic_info": {
                "session_name": result_data.get("session_name", f"训练_{session_id[:8]}"),
                "timestamp": result_data.get("timestamp", ""),
                "total_score": result_data.get("total_score", 0.0),
            },
            "scores": {
                "language_score": result_data.get("language_score", 0.0),
                "posture_score": result_data.get("posture_score", 0.0),
            },
            "metrics": result_data.get("metrics", []),
            "summary": summary,
            "ppt_match": result_data.get("ppt_match"),
            "qa_result": result_data.get("qa_result"),
            "suggestions": result_data.get("suggestions", []),
        }

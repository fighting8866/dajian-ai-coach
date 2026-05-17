from models.result_model import SuggestionItem

class ScoreService:
    """评分服务"""

    def calculate_scores(self, session_id: str, metrics: dict) -> dict:
        """根据指标计算评分

        Args:
            session_id: 会话ID
            metrics: 训练指标字典

        Returns:
            dict: 包含评分和建议的字典
        """
        # 使用默认值
        default_metrics = {
            "speech_rate": 238.0,
            "pause_count": 11,
            "avg_pause_sec": 0.9,
            "filler_count": 4,
            "forward_gaze_ratio": 0.63,
            "downward_head_ratio": 0.18,
            "posture_stability": 0.76
        }
        
        # 合并指标
        final_metrics = {**default_metrics, **(metrics or {})}

        # 计算语言分
        language_score = self._calculate_language_score(final_metrics)
        
        # 计算仪态分
        posture_score = self._calculate_posture_score(final_metrics)
        
        # 计算总分
        total_score = language_score + posture_score
        
        # 生成建议
        suggestions = self._generate_suggestions(final_metrics)
        
        # 生成总结
        summary = self._generate_summary(total_score, language_score, posture_score, final_metrics)
        
        # 构建详细指标
        detailed_metrics = [
            {"name": "语速", "value": final_metrics["speech_rate"], "unit": "字/分钟", "description": "演讲平均语速"},
            {"name": "停顿次数", "value": final_metrics["pause_count"], "unit": "次", "description": "演讲中的停顿次数"},
            {"name": "平均停顿时长", "value": final_metrics["avg_pause_sec"], "unit": "秒", "description": "平均每次停顿时长"},
            {"name": "口头禅次数", "value": final_metrics["filler_count"], "unit": "次", "description": "无意义填充词出现次数"},
            {"name": "正视前方比例", "value": final_metrics["forward_gaze_ratio"], "unit": "", "description": "面向听众的时间比例"},
            {"name": "低头率", "value": final_metrics["downward_head_ratio"], "unit": "", "description": "低头看稿或屏幕的比例"},
            {"name": "姿态稳定度", "value": final_metrics["posture_stability"], "unit": "", "description": "站姿和身体稳定程度"}
        ]

        return {
            "session_id": session_id,
            "total_score": total_score,
            "language_score": language_score,
            "posture_score": posture_score,
            "metrics": detailed_metrics,
            "suggestions": suggestions,
            "summary": summary
        }

    def _calculate_language_score(self, metrics: dict) -> int:
        """计算语言分"""
        # A. 语速 20分
        speech_rate = metrics["speech_rate"]
        if 180 <= speech_rate <= 260:
            speech_score = 20
        elif (140 <= speech_rate <= 179) or (261 <= speech_rate <= 300):
            speech_score = 15
        elif (110 <= speech_rate <= 139) or (301 <= speech_rate <= 340):
            speech_score = 10
        else:
            speech_score = 5

        # B. 停顿 15分
        avg_pause = metrics["avg_pause_sec"]
        pause_count = metrics["pause_count"]
        if 0.5 <= avg_pause <= 1.5 and 3 <= pause_count <= 15:
            pause_score = 15
        elif 0.3 <= avg_pause <= 2.0:
            pause_score = 10
        else:
            pause_score = 5

        # C. 口头禅 15分
        filler_count = metrics["filler_count"]
        if filler_count <= 2:
            filler_score = 15
        elif 3 <= filler_count <= 5:
            filler_score = 10
        elif 6 <= filler_count <= 8:
            filler_score = 6
        else:
            filler_score = 3

        return speech_score + pause_score + filler_score

    def _calculate_posture_score(self, metrics: dict) -> int:
        """计算仪态分"""
        # D. 正视前方比例 20分
        forward_gaze = metrics["forward_gaze_ratio"]
        if forward_gaze >= 0.70:
            gaze_score = 20
        elif forward_gaze >= 0.50:
            gaze_score = 15
        elif forward_gaze >= 0.30:
            gaze_score = 10
        else:
            gaze_score = 5

        # E. 低头率 15分
        downward_head = metrics["downward_head_ratio"]
        if downward_head < 0.10:
            head_score = 15
        elif downward_head < 0.20:
            head_score = 12
        elif downward_head < 0.35:
            head_score = 8
        else:
            head_score = 4

        # F. 姿态稳定度 15分
        stability = metrics["posture_stability"]
        if stability >= 0.80:
            stability_score = 15
        elif stability >= 0.65:
            stability_score = 12
        elif stability >= 0.45:
            stability_score = 8
        else:
            stability_score = 4

        return gaze_score + head_score + stability_score

    def _generate_suggestions(self, metrics: dict) -> list:
        """生成建议"""
        suggestions = []

        # 语速
        speech_rate = metrics["speech_rate"]
        if speech_rate > 300:
            suggestions.append(SuggestionItem(category="语速", content="语速过快，建议适当放慢，保持在180-260字/分钟"))
        elif speech_rate < 140:
            suggestions.append(SuggestionItem(category="语速", content="语速过慢，建议适当加快，保持在180-260字/分钟"))

        # 停顿
        avg_pause = metrics["avg_pause_sec"]
        pause_count = metrics["pause_count"]
        if not (0.5 <= avg_pause <= 1.5 and 3 <= pause_count <= 15):
            suggestions.append(SuggestionItem(category="停顿", content="停顿不够自然，建议调整停顿时长和次数"))

        # 口头禅
        filler_count = metrics["filler_count"]
        if filler_count > 5:
            suggestions.append(SuggestionItem(category="口头禅", content="口头禅使用较多，建议注意减少"))

        # 正视前方
        forward_gaze = metrics["forward_gaze_ratio"]
        if forward_gaze < 0.5:
            suggestions.append(SuggestionItem(category="视线", content="正视前方时间不足，建议更多与观众眼神交流"))

        # 低头率
        downward_head = metrics["downward_head_ratio"]
        if downward_head >= 0.2:
            suggestions.append(SuggestionItem(category="姿态", content="低头率偏高，建议保持抬头状态"))

        # 姿态稳定度
        stability = metrics["posture_stability"]
        if stability < 0.65:
            suggestions.append(SuggestionItem(category="姿态", content="姿态稳定度不足，建议保持身体稳定"))

        # 补充建议，确保至少3条
        if len(suggestions) < 3:
            suggestions.append(SuggestionItem(category="整体", content="继续保持练习，提高演讲自信度"))
        if len(suggestions) < 3:
            suggestions.append(SuggestionItem(category="整体", content="注意语调变化，增强演讲感染力"))

        # 最多返回3条
        return suggestions[:3]

    def _generate_summary(self, total_score: int, language_score: int, posture_score: int, metrics: dict) -> dict:
        """生成总结"""
        # 总评
        if total_score >= 85:
            overall_comment = "整体表现优秀，已经具备较好的答辩表达能力"
        elif total_score >= 70:
            overall_comment = "整体表现良好，但还有进一步优化空间"
        else:
            overall_comment = "当前表达仍有明显提升空间，建议针对薄弱项重点训练"

        # 最强项
        aspects = []
        if language_score >= 40:
            aspects.append("语言表达")
        if posture_score >= 40:
            aspects.append("仪态表现")
        
        # 具体指标
        if 180 <= metrics["speech_rate"] <= 260:
            aspects.append("语速控制")
        if 0.5 <= metrics["avg_pause_sec"] <= 1.5 and 3 <= metrics["pause_count"] <= 15:
            aspects.append("停顿节奏")
        if metrics["filler_count"] <= 2:
            aspects.append("口头禅控制")
        if metrics["forward_gaze_ratio"] >= 0.7:
            aspects.append("目光交流")
        if metrics["downward_head_ratio"] < 0.1:
            aspects.append("抬头状态")
        if metrics["posture_stability"] >= 0.8:
            aspects.append("姿态稳定")
        
        strongest_aspect = "整体表现均衡" if not aspects else f"{aspects[0]}较好"

        # 待改进项
        weak_aspects = []
        if metrics["speech_rate"] > 300 or metrics["speech_rate"] < 140:
            weak_aspects.append("语速")
        if not (0.5 <= metrics["avg_pause_sec"] <= 1.5 and 3 <= metrics["pause_count"] <= 15):
            weak_aspects.append("停顿节奏")
        if metrics["filler_count"] > 5:
            weak_aspects.append("口头禅")
        if metrics["forward_gaze_ratio"] < 0.5:
            weak_aspects.append("正视前方比例")
        if metrics["downward_head_ratio"] >= 0.2:
            weak_aspects.append("低头率")
        if metrics["posture_stability"] < 0.65:
            weak_aspects.append("姿态稳定度")
        
        weakest_aspect = "无明显短板" if not weak_aspects else f"{weak_aspects[0]}需要改进"

        # 训练建议
        if weak_aspects:
            if "语速" in weak_aspects:
                training_tip = "建议练习控制语速，保持在180-260字/分钟"
            elif "停顿节奏" in weak_aspects:
                training_tip = "建议练习自然停顿，控制停顿时长和次数"
            elif "口头禅" in weak_aspects:
                training_tip = "建议注意减少口头禅的使用"
            elif "正视前方比例" in weak_aspects:
                training_tip = "建议增加与观众的眼神交流"
            elif "低头率" in weak_aspects:
                training_tip = "建议保持抬头状态，减少低头频率"
            else:
                training_tip = "建议加强姿态稳定性训练"
        else:
            training_tip = "继续保持练习，进一步提升演讲自信度"

        return {
            "overall_comment": overall_comment,
            "strongest_aspect": strongest_aspect,
            "weakest_aspect": weakest_aspect,
            "training_tip": training_tip
        }
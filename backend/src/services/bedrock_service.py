import os
import json
import boto3
from typing import Optional
from src.models.schemas import VisualDefectEvidence

# The model must be ACTIVE in the deployment region. Set BEDROCK_MODEL_ID at deploy time
# (see template.yaml) and confirm it with `aws bedrock list-foundation-models`.
DEFAULT_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")


class BedrockVisionService:
    def __init__(self, region_name: Optional[str] = None, model_id: Optional[str] = None):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.model_id = model_id or DEFAULT_MODEL_ID
        try:
            self.client = boto3.client("bedrock-runtime", region_name=self.region_name)
        except Exception as e:
            self.client = None
            print(f"BedrockVisionService initialized without a client: {e}")

    def analyze_defect_image(
        self, image_bytes: bytes, image_format: str = "jpeg", product_hint: Optional[str] = None
    ) -> VisualDefectEvidence:
        """
        Analyzes product defect imagery using Amazon Bedrock (Converse API, image content block).
        Documents visible physical anomalies only; does not perform root-cause diagnosis.
        """
        if not self.client or not self.model_id:
            return self._unavailable("Amazon Bedrock is not configured for this environment.")

        # Trust the bytes, not the caller: detect the real image format.
        if image_bytes[:3] == b"\xff\xd8\xff":
            image_format = "jpeg"
        elif image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            image_format = "png"
        elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            image_format = "webp"
        else:
            return self._unavailable("Unsupported image format (use JPEG, PNG or WebP).")

        system_prompt = (
            "You are an evidence intake assistant for RemedyAI, a consumer claim preparation engine. "
            "Your task is strictly to inspect defect photos and document visible physical anomalies and symptoms. "
            "CRITICAL RULES:\n"
            "1. You document VISIBLE physical anomalies only (e.g. cracked hinge, screen banding, cracked back glass).\n"
            "2. DO NOT speculate or claim to diagnose internal electrical or engineering root causes.\n"
            "3. If the image does not show something, do not claim it.\n"
            "4. Return ONLY a valid JSON object matching the requested schema.\n"
        )

        user_prompt = (
            f"Analyze this product defect photograph (Product context: {product_hint or 'Consumer product'}). "
            "Output a JSON object with exactly these keys:\n"
            "{\n"
            '  "anomaly_detected": true/false,\n'
            '  "visible_physical_damage": true/false,\n'
            '  "physical_damage_severity": "none" | "cosmetic" | "screen_cracked" | "severe",\n'
            '  "symptom_category": "string (e.g. rear_camera, receiver_audio, display_panel, mechanical_hinge, enclosure, power)",\n'
            '  "visual_observations": ["list", "of", "concrete", "visual", "observations"]\n'
            "}"
        )

        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "image": {
                                    "format": image_format.lower().replace("jpg", "jpeg"),
                                    "source": {"bytes": image_bytes},
                                }
                            },
                            {"text": user_prompt},
                        ],
                    }
                ],
                system=[{"text": system_prompt}],
                inferenceConfig={"temperature": 0.1, "maxTokens": 500},
            )

            response_text = ""
            for block in response.get("output", {}).get("message", {}).get("content", []):
                if "text" in block:
                    response_text += block["text"]

            cleaned_text = response_text.strip()
            if "```json" in cleaned_text:
                cleaned_text = cleaned_text.split("```json")[1].split("```")[0].strip()
            elif "```" in cleaned_text:
                cleaned_text = cleaned_text.split("```")[1].split("```")[0].strip()

            parsed = json.loads(cleaned_text)
            severity = parsed.get("physical_damage_severity", "none")
            if severity not in ("none", "cosmetic", "screen_cracked", "severe"):
                severity = "severe" if parsed.get("visible_physical_damage") else "none"
            return VisualDefectEvidence(
                anomaly_detected=parsed.get("anomaly_detected", False),
                visible_physical_damage=parsed.get("visible_physical_damage", False),
                physical_damage_severity=severity,
                symptom_category=parsed.get("symptom_category"),
                visual_observations=parsed.get("visual_observations", []),
                source="bedrock",
            )

        except Exception as e:
            print(f"Bedrock Converse call failed: {type(e).__name__}")
            return self._unavailable("Automated image analysis failed for this upload.")

    @staticmethod
    def _unavailable(reason: str) -> VisualDefectEvidence:
        """Neutral record: never invents observations when no model output exists."""
        return VisualDefectEvidence(
            anomaly_detected=False,
            visible_physical_damage=False,
            physical_damage_severity="none",
            symptom_category=None,
            visual_observations=[f"{reason} No visual observations were recorded."],
            source="unavailable",
        )

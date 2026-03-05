"""
llm.py — LLM client using Amazon Bedrock (Qwen3 model)
========================================================

Replaces the previous Azure OpenAI client with Amazon Bedrock, using the
Qwen3 model for all LLM inference.  The public interface (LLMOpenAI class
name and method signatures) is preserved so that callers (device_analyser.py)
require no changes.

Environment variables (read from .env or process environment):
  AWS_REGION               — Bedrock region (default: us-east-1)
  BEDROCK_MODEL_ID         — Bedrock model identifier (default: qwen.qwen3-next-80b-a3b)
  AWS_ACCESS_KEY_ID        — (optional if running on Lambda with IAM role)
  AWS_SECRET_ACCESS_KEY    — (optional if running on Lambda with IAM role)
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import boto3
from botocore.config import Config
from dotenv import load_dotenv

from prompts import (
    build_compliance_doc_prompt,
    build_conversational_prompt,
    build_explanation_prompt,
    build_itsm_task_prompt,
    fallback_explanation,
    fallback_itsm_task,
)

# LLM call timeout in seconds (design.md: graceful degradation after 10 s)
_LLM_TIMEOUT_SECONDS = 10

# Resolve .env relative to this file: src/llm_engine/llm.py -> repo root
_DOTENV_PATH = Path(__file__).parent.parent.parent / ".env"

log = logging.getLogger(__name__)


class LLMOpenAI:
    """
    LLM client backed by Amazon Bedrock (Qwen3 model).

    The class name is kept as LLMOpenAI for backward compatibility with
    existing imports in device_analyser.py.
    """

    def __init__(self) -> None:
        # Load .env from the repo root so the path is stable regardless of
        # which directory uvicorn / the calling process was started from.
        loaded = load_dotenv(_DOTENV_PATH)
        if not loaded:
            log.warning(
                "load_dotenv: .env file not found at '%s'. "
                "AWS credentials must be set as environment variables or via IAM role.",
                _DOTENV_PATH,
            )

        self._region = os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION", "us-east-1")
        self._model_id = os.getenv("BEDROCK_MODEL_ID", "qwen.qwen3-next-80b-a3b")

        bedrock_config = Config(
            region_name=self._region,
            read_timeout=_LLM_TIMEOUT_SECONDS + 5,
            retries={"max_attempts": 2, "mode": "adaptive"},
        )

        self._client = boto3.client(
            "bedrock-runtime",
            config=bedrock_config,
        )

        log.info(
            "Bedrock LLM client initialised — region=%s  model=%s",
            self._region,
            self._model_id,
        )

    # ------------------------------------------------------------------
    # Core inference methods
    # ------------------------------------------------------------------

    def generic_llm(self, system_message: str, question: str) -> str:
        """
        Call Bedrock Converse API with Qwen3 model.
        Returns the assistant's text response.
        """
        messages = [
            {"role": "user", "content": [{"text": question}]},
        ]

        system = [{"text": system_message}]

        inference_config = {
            "maxTokens": 2000,
            "temperature": 0.0,
            "topP": 1.0,
        }

        response = self._client.converse(
            modelId=self._model_id,
            messages=messages,
            system=system,
            inferenceConfig=inference_config,
        )

        output_message = response["output"]["message"]
        result_text = ""
        for block in output_message["content"]:
            if "text" in block:
                result_text += block["text"]

        return result_text

    def generic_llm_rest(self, system_message: str, query: str) -> str:
        """
        Alternative invocation using Bedrock InvokeModel API (raw payload).
        Falls back to the same Bedrock endpoint but uses the lower-level API.
        """
        payload = {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query},
            ],
            "max_tokens": 2000,
            "temperature": 0.0,
            "top_p": 1.0,
        }

        response = self._client.invoke_model(
            modelId=self._model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )

        result = json.loads(response["body"].read())
        # Handle different response formats from different model providers
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        elif "output" in result:
            return result["output"]["text"]
        elif "content" in result:
            return result["content"][0]["text"]
        else:
            return str(result)

    # ------------------------------------------------------------------
    # Purpose-specific methods — each uses the matching prompt builder
    # and falls back gracefully on timeout or service errors.
    # ------------------------------------------------------------------

    def generate_recommendation_explanation(
        self,
        asset_id: str,
        device_type: str,
        age_months: int,
        department: str,
        region: str,
        risk_score: float,
        risk_label: str,
        confidence_band: str,
        recommended_action: str,
        supporting_signals: list,
        policy_result: dict,
        ml_result: Optional[dict] = None,
        telemetry: Optional[dict] = None,
        tickets: Optional[dict] = None,
    ) -> str:
        """
        Requirement 8 — Generate a factual recommendation explanation (≤120 words).
        Falls back to a template string if the LLM times out or is unavailable.
        """
        system_msg, user_msg = build_explanation_prompt(
            asset_id=asset_id,
            device_type=device_type,
            age_months=age_months,
            department=department,
            region=region,
            risk_score=risk_score,
            risk_label=risk_label,
            confidence_band=confidence_band,
            recommended_action=recommended_action,
            supporting_signals=supporting_signals,
            policy_result=policy_result,
            ml_result=ml_result,
            telemetry=telemetry,
            tickets=tickets,
        )
        try:
            start = time.time()
            result = self.generic_llm(system_msg, user_msg)
            if time.time() - start > _LLM_TIMEOUT_SECONDS:
                raise TimeoutError("LLM response exceeded timeout threshold")
            return result
        except Exception as exc:
            log.warning("LLM explanation failed (%s), using fallback", exc)
            return fallback_explanation(
                recommended_action=recommended_action,
                risk_score=risk_score,
                age_months=age_months,
                total_incidents=tickets.get("total_incidents", 0) if tickets else 0,
                risk_label=risk_label,
            )

    def scaffold_itsm_task(
        self,
        asset_id: str,
        recommended_action: str,
        rationale: str,
        confidence_score: float,
        device_type: str,
        department: str,
        region: str,
        age_months: int,
        compliance_requirements: Optional[list] = None,
    ) -> dict:
        """
        Requirement 9 — Generate a structured ITSM task (JSON).
        Falls back to a minimal task dict if the LLM is unavailable.
        """
        system_msg, user_msg = build_itsm_task_prompt(
            asset_id=asset_id,
            recommended_action=recommended_action,
            rationale=rationale,
            confidence_score=confidence_score,
            device_type=device_type,
            department=department,
            region=region,
            age_months=age_months,
            compliance_requirements=compliance_requirements,
        )
        try:
            start = time.time()
            raw = self.generic_llm(system_msg, user_msg)
            if time.time() - start > _LLM_TIMEOUT_SECONDS:
                raise TimeoutError("LLM response exceeded timeout threshold")
            return json.loads(raw)
        except Exception as exc:
            log.warning("LLM ITSM task failed (%s), using fallback", exc)
            return fallback_itsm_task(
                asset_id=asset_id,
                recommended_action=recommended_action,
                device_type=device_type,
                region=region,
            )

    def process_compliance_document(
        self,
        document_type: str,
        region: str,
        asset_id: str,
        file_content: str,
        required_fields: list,
        region_requirements: Optional[dict] = None,
    ) -> dict:
        """
        Requirement 10 — Extract entities from a compliance document and flag gaps.
        """
        system_msg, user_msg = build_compliance_doc_prompt(
            document_type=document_type,
            region=region,
            asset_id=asset_id,
            file_content=file_content,
            required_fields=required_fields,
            region_requirements=region_requirements,
        )
        raw = self.generic_llm(system_msg, user_msg)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "summary": raw,
                "extracted_entities": {},
                "missing_fields": required_fields,
                "verification_status": "INCOMPLETE",
                "recommendations": ["Re-upload document or verify extraction manually."],
            }

    def answer_conversational_query(
        self,
        user_query: str,
        semantic_layer_schema: Optional[dict] = None,
        available_aggregations: Optional[list] = None,
        context_data: Optional[dict] = None,
    ) -> str:
        """
        Requirement 11 — Answer a natural-language question about asset lifecycle data.
        """
        system_msg, user_msg = build_conversational_prompt(
            user_query=user_query,
            semantic_layer_schema=semantic_layer_schema,
            available_aggregations=available_aggregations,
            context_data=context_data,
        )
        return self.generic_llm(system_msg, user_msg)

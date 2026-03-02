import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import AzureOpenAI

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


class LLMOpenAI():

    def __init__(self) -> None:
        # Load .env from the repo root so the path is stable regardless of
        # which directory uvicorn / the calling process was started from.
        loaded = load_dotenv(_DOTENV_PATH)
        if not loaded:
            log.warning(
                "load_dotenv: .env file not found at '%s'. "
                "Azure OpenAI credentials must be set as environment variables.",
                _DOTENV_PATH,
            )

        endpoint    = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("azure_oai_endpoint")
        api_key     = os.getenv("AZURE_OPENAI_API_KEY")  or os.getenv("azure_oai_key")
        api_version = (
            os.getenv("AZURE_OPENAI_API_VERSION")
            or os.getenv("azure_oai_version")
            or "2024-02-01"   # stable default — override via .env if needed
        )

        missing = [name for name, val in [
            ("AZURE_OPENAI_ENDPOINT", endpoint),
            ("AZURE_OPENAI_API_KEY",  api_key),
        ] if not val]

        if missing:
            raise EnvironmentError(
                f"Missing Azure OpenAI credential(s): {', '.join(missing)}. "
                f"Add them to '{_DOTENV_PATH}' or set them as environment variables. "
                f"Expected keys: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY. "
                f"Optional: AZURE_OPENAI_API_VERSION (defaults to 2024-02-01)."
            )

        self.openai = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

        

    # Method for calling LLM using openai client
    def generic_llm(self,system_message,question)->str: 
 
        chat_completion = self.openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": question}
        ],
        #logit_bias= {2435: -100, 640: -100},
        max_tokens= 2000,
        temperature= 0, # Optional, Defaults to 1. Range: 0 to 2
        top_p= 1 # Optional, Defaults to 1. It is generally recommended to alter this or temperature but not both.
        )
        response = chat_completion.choices[0].message.content
        return response
    
    # Method for calling LLM via REST API
    def generic_llm_rest(self, system_message, query):
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("azure_oai_endpoint")
        api_key        = os.getenv("AZURE_OPENAI_API_KEY")  or os.getenv("azure_oai_key")
        api_version    = (
            os.getenv("AZURE_OPENAI_API_VERSION")
            or os.getenv("azure_oai_version")
            or "2024-02-01"
        )

        api_endpoint = azure_endpoint
        payload_headers = {
            "Content-Type": "application/json",
            "api-key": api_key,
        }
        payload = {
                "messages": [
                                {"role": "system", "content": [{"type": "text","text": system_message}]},
                                {"role": "user", "content": [{"type": "text","text": query}]}
                            ],
                "temperature": 0,
                "top_p": 1,
                "max_tokens": 2000
                }
    
        try:
            response = requests.post(api_endpoint, headers=payload_headers, json=payload)
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        except requests.RequestException as e:
         raise SystemExit(f"Failed to make the request. Error: {e}")
 
        required_data = response.json()
    
        return required_data['choices'][0]["message"]["content"]

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
        except Exception:
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
        except Exception:
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
        Returns a dict with summary, extracted_entities, missing_fields,
        verification_status, and recommendations.
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
        Returns a plain-text response with provenance and suggested follow-up queries.
        """
        system_msg, user_msg = build_conversational_prompt(
            user_query=user_query,
            semantic_layer_schema=semantic_layer_schema,
            available_aggregations=available_aggregations,
            context_data=context_data,
        )
        return self.generic_llm(system_msg, user_msg)
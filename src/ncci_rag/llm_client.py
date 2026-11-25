"""One place that creates the model client, so the rest of the code does not care
whether it talks to OpenAI or to Azure OpenAI."""

from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_client():
    from openai import AzureOpenAI, OpenAI

    if os.getenv("AZURE_OPENAI_ENDPOINT"):
        # With Azure, model names in settings are *deployment* names.
        return AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Locally: copy .env.example to .env and add your key. "
            "Hosted (Streamlit Community Cloud): add OPENAI_API_KEY under Manage app -> Settings -> Secrets."
        )
    return OpenAI()

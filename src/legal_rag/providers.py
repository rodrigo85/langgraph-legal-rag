"""
LLM and embedding provider factory.

Business logic (chains, graph nodes) asks for "a chat model" and never imports a
vendor SDK directly. The provider is chosen by configuration:

    LLM_PROVIDER / EMBEDDING_PROVIDER = ollama | bedrock | azure_openai

Cloud SDKs are optional extras (`pip install .[aws]` / `.[azure]`) and are
imported lazily, so a local Ollama install needs none of them.
"""

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel

from legal_rag.config import Settings, get_settings


class ProviderNotInstalledError(RuntimeError):
    """Raised when the configured provider's optional dependency is missing."""


def _missing(extra: str, package: str) -> ProviderNotInstalledError:
    return ProviderNotInstalledError(
        f"Provider requires '{package}'. Install it with: pip install '.[{extra}]'"
    )


def get_chat_model(
    temperature: float = 0.0,
    max_tokens: int = 512,
    settings: Settings | None = None,
) -> BaseChatModel:
    """Returns a LangChain chat model for the configured provider."""
    settings = settings or get_settings()
    provider = settings.llm_provider

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
            num_predict=max_tokens,
            keep_alive=settings.ollama_keep_alive,
        )

    if provider == "bedrock":
        try:
            from langchain_aws import ChatBedrockConverse
        except ImportError as err:
            raise _missing("aws", "langchain-aws") from err

        return ChatBedrockConverse(
            model=settings.bedrock_llm_model_id,
            region_name=settings.aws_region,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if provider == "azure_openai":
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError as err:
            raise _missing("azure", "langchain-openai") from err

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_chat_deployment,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    raise ValueError(f"Unknown LLM provider: {provider}")


def get_embeddings(settings: Settings | None = None) -> Embeddings:
    """Returns the embedding model for the configured provider."""
    settings = settings or get_settings()
    provider = settings.embedding_provider

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=settings.ollama_embed_model, base_url=settings.ollama_base_url)

    if provider == "bedrock":
        try:
            from langchain_aws import BedrockEmbeddings
        except ImportError as err:
            raise _missing("aws", "langchain-aws") from err

        return BedrockEmbeddings(model_id=settings.bedrock_embed_model_id, region_name=settings.aws_region)

    if provider == "azure_openai":
        try:
            from langchain_openai import AzureOpenAIEmbeddings
        except ImportError as err:
            raise _missing("azure", "langchain-openai") from err

        return AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
            azure_deployment=settings.azure_openai_embed_deployment,
        )

    raise ValueError(f"Unknown embedding provider: {provider}")

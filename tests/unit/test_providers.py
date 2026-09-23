"""Provider factory: the configured backend is constructed without any network call."""

import sys

import pytest
from pydantic import SecretStr

from legal_rag.config import Settings
from legal_rag.providers import ProviderNotInstalledError, get_chat_model, get_embeddings


@pytest.fixture(autouse=True)
def _dummy_aws_credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.delenv("AWS_PROFILE", raising=False)


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def azure_settings(**overrides) -> Settings:
    return make_settings(
        azure_openai_endpoint="https://example.openai.azure.com",
        azure_openai_api_key=SecretStr("dummy-key"),
        **overrides,
    )


def test_ollama_chat_model():
    from langchain_ollama import ChatOllama

    llm = get_chat_model(temperature=0.2, max_tokens=64, settings=make_settings(llm_provider="ollama"))

    assert isinstance(llm, ChatOllama)
    assert llm.num_predict == 64
    assert llm.temperature == 0.2
    assert llm.model == "antitrust-specialist-v2"


def test_bedrock_chat_model():
    from langchain_aws import ChatBedrockConverse

    settings = make_settings(llm_provider="bedrock", aws_region="eu-west-1", bedrock_llm_model_id="model-x")
    llm = get_chat_model(temperature=0.0, max_tokens=128, settings=settings)

    assert isinstance(llm, ChatBedrockConverse)
    assert llm.model_id == "model-x"
    assert llm.region_name == "eu-west-1"
    assert llm.max_tokens == 128


def test_azure_openai_chat_model():
    from langchain_openai import AzureChatOpenAI

    llm = get_chat_model(max_tokens=256, settings=azure_settings(llm_provider="azure_openai"))

    assert isinstance(llm, AzureChatOpenAI)
    assert llm.deployment_name == "gpt-4o-mini"
    assert llm.max_tokens == 256


def test_ollama_embeddings():
    from langchain_ollama import OllamaEmbeddings

    emb = get_embeddings(make_settings(embedding_provider="ollama"))
    assert isinstance(emb, OllamaEmbeddings)
    assert emb.model == "nomic-embed-text:latest"


def test_bedrock_embeddings():
    from langchain_aws import BedrockEmbeddings

    emb = get_embeddings(make_settings(embedding_provider="bedrock", aws_region="us-west-2"))
    assert isinstance(emb, BedrockEmbeddings)
    assert emb.model_id == "amazon.titan-embed-text-v2:0"
    assert emb.region_name == "us-west-2"


def test_azure_openai_embeddings():
    from langchain_openai import AzureOpenAIEmbeddings

    emb = get_embeddings(azure_settings(embedding_provider="azure_openai"))
    assert isinstance(emb, AzureOpenAIEmbeddings)
    assert emb.deployment == "text-embedding-3-small"


@pytest.mark.parametrize("factory", [get_chat_model, get_embeddings])
def test_unknown_provider_raises(factory):
    # Bypass Literal validation to simulate a provider the factory does not know.
    settings = make_settings().model_copy(update={"llm_provider": "watsonx", "embedding_provider": "watsonx"})
    with pytest.raises(ValueError, match="Unknown"):
        factory(settings=settings)


@pytest.mark.parametrize(
    ("module", "provider", "extra"),
    [("langchain_aws", "bedrock", "aws"), ("langchain_openai", "azure_openai", "azure")],
)
@pytest.mark.parametrize("factory", [get_chat_model, get_embeddings])
def test_missing_optional_dependency(monkeypatch, factory, module, provider, extra):
    monkeypatch.setitem(sys.modules, module, None)  # makes `from module import X` raise ImportError
    settings = azure_settings(llm_provider=provider, embedding_provider=provider)
    with pytest.raises(ProviderNotInstalledError, match=rf"\.\[{extra}\]"):
        factory(settings=settings)

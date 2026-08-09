from langchain_openai import ChatOpenAI


class TokenAwareLLM(ChatOpenAI):
    """
    vLLM backend does not support token counting.
    LangChain's summary memory requires token counting.
    So we approximate 1 token ≈ 4 characters.
    """

    def get_num_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def get_num_tokens_from_messages(self, messages) -> int:
        joined = ""
        for m in messages:
            joined += m.content + "\n"
        return self.get_num_tokens(joined)

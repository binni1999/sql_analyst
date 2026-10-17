# LLM provider fallback

DataPilot keeps Groq as its primary provider. When Groq returns a transient provider error (including HTTP 429 rate limits, timeouts, connection failures, or 5xx responses), the SQL generator, SQL repair calls, tool-calling model, and answer generator try configured backup providers in order.

## Configure a backup

Set at least one backup key in the same environment as the backend:

```dotenv
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
# Optional; used if the Gemini LangChain integration is installed
GEMINI_API_KEY=your_gemini_key

# Optional settings
GROQ_PRIMARY_MODEL=openai/gpt-oss-120b
OPENAI_FALLBACK_MODEL=gpt-4o-mini
GEMINI_FALLBACK_MODEL=gemini-2.5-flash
LLM_FALLBACK_ORDER=openai,gemini
```

Install the optional integration(s) for the provider(s) you configure:

```bash
pip install langchain-openai
pip install langchain-google-genai
```

Only install the package(s) you intend to use. The fallback wrapper skips a provider if its integration is unavailable, and the primary Groq model remains usable if no backup is configured. Never commit API keys to source control.

Fallback is not used for arbitrary application or validation errors, because switching providers would not fix those issues. A provider fallback also cannot guarantee a response if every configured provider is rate-limited or unavailable.

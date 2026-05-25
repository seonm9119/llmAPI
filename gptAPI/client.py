import json

from openai import OpenAI

from config import GPT_MODEL, GPT_TIMEOUT, OPENAI_API_KEY


def get_openai_client():
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    return OpenAI(api_key=OPENAI_API_KEY, timeout=GPT_TIMEOUT)


def create_structured_response(system_prompt, user_payload, response_schema, model=None):
    client = get_openai_client()
    response = client.responses.create(
        model=model or GPT_MODEL,
        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "viewer_mapping",
                "strict": True,
                "schema": response_schema,
            }
        },
    )

    output_text = getattr(response, "output_text", "") or ""

    if not output_text:
        raise RuntimeError("OpenAI response did not include output_text.")

    return json.loads(output_text), output_text

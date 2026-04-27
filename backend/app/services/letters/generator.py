"""Generate a single personalized B2B email. Full implementation in Phase 3."""

from app.services.llm import get_llm_client
from app.services.llm.base import LLMMessage

SYSTEM_PROMPT = """Ты — редактор холодных B2B-писем для малого бизнеса в России.
Пишешь по-русски, кратко, без канцелярита и штампов.
Не используешь эмодзи, восклицательных знаков не более одного.
Структура: 1 тема + приветствие + краткая причина контакта + ценностное предложение + мягкий вопрос-CTA.
Длина: {max_words} слов. Тема: до 60 знаков.
Тональность: {tone_ru}.
Если данных о лиде мало — пиши нейтрально, не выдумывай.
Никогда не упоминай, что письмо сгенерировано AI.
Отвечай ТОЛЬКО JSON вида {{"subject": "...", "body": "..."}} без Markdown.
"""

TONE_RU = {
    "formal": "вежливый деловой",
    "friendly": "дружелюбный, на «вы», но неформальный",
    "expert": "экспертный, по делу, с конкретикой",
}


async def generate_letter(sender: dict, contact: dict, template_name: str, template_instruction: str, tone: str = "friendly", max_words: int = 120) -> dict:
    client = get_llm_client("letters")
    system = SYSTEM_PROMPT.format(max_words=max_words, tone_ru=TONE_RU.get(tone, TONE_RU["friendly"]))
    user = f"""Отправитель:
- Имя: {sender.get('name', '—')}
- Бизнес: {sender.get('business', '—')}
- Оффер: {sender.get('offer', '—')}
- Город: {sender.get('city', '—')}

Получатель:
- Компания: {contact.get('company_name', '—')}
- Контакт: {contact.get('contact_name', '—')}
- Сайт: {contact.get('website', '—')}
- Отрасль: {contact.get('industry', '—')}
- Город: {contact.get('city', '—')}
- Краткое о сайте: {contact.get('website_summary', '—')}

Задача: напиши письмо по шаблону "{template_name}".
{template_instruction}"""
    result = await client.chat(
        messages=[LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)],
        temperature=0.7,
        max_tokens=450,
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(result.content)

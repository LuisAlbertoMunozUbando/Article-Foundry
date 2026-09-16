from __future__ import annotations

import json
import re

from app import main as base


async def chat_json_robust(system: str, user: str, max_tokens: int = 3200):
    """Use the existing local LLM call, but recover JSON embedded in prose/fences."""
    model = base.MODEL
    headers = {'Authorization': f'Bearer {base.KEY}'}
    async with base.httpx.AsyncClient(timeout=180) as h:
        if not model:
            r = await h.get(f'{base.LLM}/models', headers=headers)
            r.raise_for_status()
            model = r.json()['data'][0]['id']
        r = await h.post(
            f'{base.LLM}/chat/completions',
            headers=headers,
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'temperature': 0.1,
                'max_tokens': max_tokens,
            },
        )
        r.raise_for_status()
        raw = r.json()['choices'][0]['message']['content'].strip()

    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.I)
    raw = re.sub(r'\s*```$', '', raw, flags=re.I)
    try:
        return json.loads(raw)
    except Exception:
        start = raw.find('{')
        end = raw.rfind('}')
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise


async def chat_text(system: str, user: str, max_tokens: int = 3200):
    model = base.MODEL
    headers = {'Authorization': f'Bearer {base.KEY}'}
    async with base.httpx.AsyncClient(timeout=180) as h:
        if not model:
            r = await h.get(f'{base.LLM}/models', headers=headers)
            r.raise_for_status()
            model = r.json()['data'][0]['id']
        r = await h.post(
            f'{base.LLM}/chat/completions',
            headers=headers,
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'temperature': 0.1,
                'max_tokens': max_tokens,
            },
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()


async def compose_document(mode, title, frags, sources, language):
    lang = base.LANGUAGES.get(language, 'Spanish')
    by_fragment = {}
    for s in sources:
        if s.get('fragment_id'):
            by_fragment.setdefault(s['fragment_id'], []).append(s['citekey'])

    corpus_parts = []
    for i, f in enumerate(frags):
        keys = by_fragment.get(f.get('id'), [])
        citation_line = ('\nCITATION_KEYS: ' + ', '.join(keys)) if keys else '\nCITATION_KEYS: none'
        corpus_parts.append(f"FRAGMENT {i+1}:\n{f['text']}{citation_line}")

    unlinked = [s for s in sources if not s.get('fragment_id')]
    if unlinked:
        corpus_parts.append(
            'PROJECT SOURCES NOT LINKED TO A SPECIFIC FRAGMENT:\n' +
            '\n'.join(f"{s['citekey']}: {s['raw']}" for s in unlinked)
        )
    corpus = '\n\n'.join(corpus_parts) or 'No content yet.'

    structures = {
        'divulgacion': 'popular-science article with an engaging opening, central idea, clear explanation, evidence/connections, implications, and conclusion',
        'ieee': 'IEEE-style scientific paper with abstract, introduction, related work/context, methodology or approach when supported, results/evidence when supported, discussion, and conclusion',
        'patent': 'patent-oriented technical document with technical field, background, technical problem, summary of invention, detailed description, embodiments, claims draft, and abstract',
    }

    prompt = f'''MANDATORY OUTPUT LANGUAGE: {lang}.
Every title, heading, abstract sentence, and body sentence MUST be written in {lang}, regardless of the language of the source fragments.
Translate the source material when necessary. Preserve proper nouns, equations, citation keys, and technical identifiers.

Create a coherent {structures[mode]} using ONLY the supplied fragments as factual content.
Do not invent experiments, results, citations, inventors, dates, or unsupported novelty claims.

CITATION RULES:
- When a statement is supported by a fragment that has CITATION_KEYS, add [[CITE:key]] or [[CITE:key1,key2]] immediately after the supported statement.
- Use ONLY citation keys explicitly supplied below.
- Never invent a citation key.

Return ONLY valid JSON in exactly this shape:
{{"title":"...","abstract":"...","sections":[{{"heading":"...","body":"..."}}]}}

Requested title: {title}

SOURCE MATERIAL:
{corpus}'''

    try:
        doc = await chat_json_robust(
            f'You are a multilingual scientific and technical writer. The mandatory output language is {lang}. Return strict JSON only.',
            prompt,
            3600,
        )
    except Exception:
        # Never silently fall back to untranslated source text. If JSON generation fails,
        # perform an explicit translation/rewrite pass and wrap it in a minimal document.
        fallback_prompt = f'''Write the following material entirely in {lang}.
Do not leave narrative passages in the source language. Preserve proper nouns, technical identifiers, equations, and [[CITE:...]] markers.
Do not add facts. Produce a coherent document body suitable for this mode: {structures[mode]}.

{corpus}'''
        body = await chat_text(
            f'You are a translator and technical editor. Output only {lang}.',
            fallback_prompt,
            3600,
        )
        title_out = title
        try:
            title_out = await chat_text(
                f'Translate the title into {lang}. Return only the translated title.',
                title,
                120,
            )
        except Exception:
            pass
        doc = {'title': title_out, 'abstract': '', 'sections': [{'heading': 'Content', 'body': body}]}

    return base.ensure_document_citations(doc, sources)


# Monkey-patch the original module. Existing FastAPI route functions resolve this global
# from app.main at request time, so no route duplication is needed.
base.compose_document = compose_document
base.chat_json = chat_json_robust
base.app.version = '0.3.3'
app = base.app

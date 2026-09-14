"""AI Service - Credibility analysis and news summarization"""
import re
import json
import uuid
from typing import Optional
from config import EMERGENT_LLM_KEY, logger


async def analyze_credibility(title: str, summary: str, source_name: str) -> Optional[dict]:
    """Use AI to analyze news credibility"""
    if not EMERGENT_LLM_KEY:
        return None
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"fakenews_{uuid.uuid4().hex[:8]}",
            system_message="""Você é um especialista em verificação de notícias (fact-checker).
Analise a notícia fornecida e determine sua credibilidade.

CRITÉRIOS DE AVALIAÇÃO:
- Linguagem sensacionalista ou clickbait
- Afirmações extraordinárias sem evidências
- Teorias da conspiração
- Promessas milagrosas ou impossíveis
- Manipulação emocional excessiva
- Fonte confiável ou desconhecida

Responda APENAS em JSON no formato:
{"score": 0.0 a 1.0, "reason": "breve explicação em português"}

Onde score é:
- 0.0-0.3 = Provavelmente fake news
- 0.4-0.6 = Suspeito, precisa verificação
- 0.7-1.0 = Provavelmente confiável"""
        ).with_model("openai", "gpt-4.1-mini")
        
        prompt = f"""Analise esta notícia:

TÍTULO: {title}
RESUMO: {summary}
FONTE: {source_name or 'Desconhecida'}

Responda apenas o JSON com score e reason."""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        try:
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                result = json.loads(json_match.group())
                if "score" in result:
                    return result
        except json.JSONDecodeError:
            pass
        
        return None
    except Exception as e:
        logger.error(f"AI credibility analysis error: {str(e)}")
        return None


_CATEGORIES_PROMPT = """Categorias válidas (responda APENAS com o id):
- economia: economia, finanças, investimentos, criptomoedas, loterias, impostos, mercado
- tecnologia: tecnologia, IA, apps, smartphones, internet, empresas de tech
- games: videogames, consoles, e-sports, jogos eletrônicos
- esportes: esportes EXCETO futebol (F1, NBA, UFC, tênis, vôlei, olimpíadas)
- futebol: futebol nacional e internacional, clubes, jogadores, campeonatos
- entretenimento: filmes, séries, novelas, animes, streaming, TV, cultura pop
- musica: músicas, cantores, shows, festivais, álbuns
- celebridades: famosos, influencers, BBB, reality shows, fofocas
- gastronomia: receitas, restaurantes, chefs, culinária
- automoveis: lançamentos de carros/motos, indústria automotiva, CNH, IPVA (NÃO acidentes de trânsito)
- educacao: ENEM, escolas, universidades, cursos, professores
- planeta: clima, meio ambiente, desastres naturais, previsão do tempo, sustentabilidade
- ciencia_saude: ciência, espaço, NASA, pesquisas, medicina, saúde, doenças, vacinas
- politica_mundo: política brasileira, governo, eleições, STF, guerras, notícias internacionais
- seguranca: crimes, polícia, prisões, violência, acidentes de trânsito com vítimas, tragédias"""


def _extract_category(response: str) -> Optional[str]:
    """Extract a valid category id from an LLM response."""
    try:
        from services.classifier import VALID_IDS
    except ImportError:
        from classifier import VALID_IDS
    cat = (response or "").strip().lower().strip('"\'.` ')
    if cat in VALID_IDS:
        return cat
    for vid in VALID_IDS:
        if vid in cat:
            return vid
    return None


async def classify_with_llm(title: str, summary: str = "", source_name: str = "") -> Optional[str]:
    """Classify a single news article into one of the 15 categories using AI."""
    if not EMERGENT_LLM_KEY or not title:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"classify_{uuid.uuid4().hex[:8]}",
            system_message=f"""Você é um editor de jornal brasileiro que classifica notícias.
{_CATEGORIES_PROMPT}

Responda APENAS com o id da categoria (ex: futebol). Nada mais."""
        ).with_model("openai", "gpt-4.1-mini")

        prompt = f"TÍTULO: {title}\nRESUMO: {(summary or '')[:300]}\nFONTE: {source_name or 'desconhecida'}"
        response = await chat.send_message(UserMessage(text=prompt))
        return _extract_category(response)
    except Exception as e:
        logger.error(f"LLM classify error: {str(e)}")
        return None


async def classify_batch_llm(items: list) -> Optional[list]:
    """Classify up to 20 articles in a single AI call.
    items: list of dicts with 'title' and 'summary'.
    Returns a list of category ids (same length/order) or None on failure."""
    if not EMERGENT_LLM_KEY or not items:
        return None
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"classify_batch_{uuid.uuid4().hex[:8]}",
            system_message=f"""Você é um editor de jornal brasileiro que classifica notícias.
{_CATEGORIES_PROMPT}

Responda APENAS com um array JSON de ids, um por notícia, na mesma ordem.
Exemplo: ["futebol", "economia", "seguranca"]"""
        ).with_model("openai", "gpt-4.1-mini")

        lines = []
        for i, it in enumerate(items, 1):
            lines.append(f"{i}. {it.get('title', '')} — {(it.get('summary') or '')[:150]}")
        response = await chat.send_message(UserMessage(text="\n".join(lines)))

        match = re.search(r'\[.*\]', response, re.DOTALL)
        if not match:
            return None
        cats = json.loads(match.group())
        if not isinstance(cats, list) or len(cats) != len(items):
            return None
        return [_extract_category(str(c)) for c in cats]
    except Exception as e:
        logger.error(f"LLM batch classify error: {str(e)}")
        return None


async def generate_summary(title: str, content: str, category: str) -> Optional[str]:
    """Use AI to generate a concise Portuguese summary of a news article"""
    if not EMERGENT_LLM_KEY:
        return None
    
    if not content or len(content.strip()) < 50:
        return None
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"summary_{uuid.uuid4().hex[:8]}",
            system_message="""Você é um jornalista brasileiro experiente e revisor de textos.
Sua tarefa é criar um resumo conciso e informativo de notícias.

REGRAS OBRIGATÓRIAS:
- Máximo 2 frases (50-80 palavras)
- Português brasileiro PERFEITO: gramática, acentuação e ortografia impecáveis
- Linguagem clara, direta e profissional
- Capture o fato principal e o impacto da notícia
- NÃO use aspas, citações diretas ou emojis
- NÃO comece com "A notícia", "O artigo", "Segundo" ou "De acordo"
- Comece direto com o fato principal (sujeito + verbo)
- Tom informativo e neutro, sem sensacionalismo
- Revise a ortografia antes de responder"""
        ).with_model("openai", "gpt-4.1-mini")
        
        truncated = content[:1500] if len(content) > 1500 else content
        
        prompt = f"""Resuma esta notícia em 2 frases curtas e bem escritas em português brasileiro:

TÍTULO: {title}
CATEGORIA: {category}
CONTEÚDO: {truncated}"""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        if response and len(response.strip()) > 20:
            summary = response.strip()
            summary = re.sub(r'^["\']+|["\']+$', '', summary)
            summary = re.sub(r'\n+', ' ', summary)
            summary = re.sub(r'\s+', ' ', summary).strip()
            return summary
        
        return None
    except Exception as e:
        logger.error(f"AI summary generation error: {str(e)}")
        return None

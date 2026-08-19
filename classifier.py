"""LoopNews - Sistema unificado de categorias (15) e classificação de notícias.
Pontuação ponderada: título vale 2x, resumo 1x. Exclusões subtraem pontos.
"""
import re
import html as html_lib

# ==================== 15 CATEGORIAS ====================
CATEGORIES_15 = [
    {"id": "economia", "name": "Economia e Finanças", "icon": "chart-line"},
    {"id": "tecnologia", "name": "Tecnologia", "icon": "laptop"},
    {"id": "games", "name": "Games", "icon": "gamepad"},
    {"id": "esportes", "name": "Esportes", "icon": "basketball"},
    {"id": "futebol", "name": "Futebol", "icon": "football"},
    {"id": "entretenimento", "name": "Entretenimento", "icon": "film"},
    {"id": "musica", "name": "Músicas", "icon": "musical-notes"},
    {"id": "celebridades", "name": "Celebridades", "icon": "star"},
    {"id": "gastronomia", "name": "Gastronomia", "icon": "restaurant"},
    {"id": "automoveis", "name": "Automóveis", "icon": "car-sport"},
    {"id": "educacao", "name": "Educação", "icon": "school"},
    {"id": "planeta", "name": "Planeta e Clima", "icon": "leaf"},
    {"id": "ciencia_saude", "name": "Ciência, Espaço e Saúde", "icon": "flask"},
    {"id": "politica_mundo", "name": "Política e Mundo", "icon": "globe"},
    {"id": "seguranca", "name": "Segurança", "icon": "shield-checkmark"},
]

VALID_IDS = {c["id"] for c in CATEGORIES_15}

# Mapeamento das categorias antigas -> novas
OLD_TO_NEW = {
    "economia": "economia", "investimentos": "economia", "financas": "economia",
    "finanças": "economia", "criptomoedas": "economia",
    "tecnologia": "tecnologia",
    "games": "games",
    "esportes": "esportes",
    "futebol": "futebol",
    "entretenimento": "entretenimento", "anime": "entretenimento",
    "filmes": "entretenimento", "series": "entretenimento", "séries": "entretenimento",
    "novelas": "entretenimento",
    "famosos": "celebridades", "celebridades": "celebridades",
    "musica": "musica", "música": "musica",
    "gastronomia": "gastronomia",
    "automoveis": "automoveis",
    "educacao": "educacao",
    "planeta": "planeta",
    "saude": "ciencia_saude", "saúde": "ciencia_saude", "ciencia": "ciencia_saude",
    "ciência": "ciencia_saude", "ciencia_saude": "ciencia_saude",
    "politica": "politica_mundo", "política": "politica_mundo",
    "mundo": "politica_mundo", "politica_mundo": "politica_mundo",
    "policial": "seguranca", "seguranca": "seguranca",
}

# ==================== PALAVRAS-CHAVE (peso 3 = forte, peso 1 = apoio) ====================
KW = {
    "futebol": {
        3: ["futebol", "gol ", "gols", "brasileirão", "brasileirao", "libertadores", "champions league",
            "premier league", "la liga", "copa do brasil", "copa do mundo", "flamengo", "corinthians",
            "palmeiras", "são paulo fc", "vasco", "grêmio", "gremio", "internacional", "cruzeiro",
            "atlético-mg", "fluminense", "botafogo", "santos fc", "neymar", "vini jr", "vinicius júnior",
            "seleção brasileira", "selecao brasileira", "técnico ", "artilheiro", "escalação", "escalacao",
            "real madrid", "barcelona", "messi", "cristiano ronaldo", "fifa", "cbf", "zagueiro",
            "atacante", "meio-campo", "goleiro", "lateral", "rodada", "empate", "pênalti", "penalti"],
        1: ["campeonato", "clube", "estádio", "estadio", "torcida", "partida", "jogador", "contratação"],
    },
    "esportes": {
        3: ["basquete", "nba", "vôlei", "volei", "tênis ", "tenis ", "fórmula 1", "formula 1", "f1 ",
            "mma", "ufc", "boxe", "atletismo", "natação", "natacao", "olimpíadas", "olimpiadas",
            "ginástica", "ginastica", "surfe", "skate", "ciclismo", "maratona", "handebol",
            "grand prix", "grande prêmio", "pole position", "medalha", "wimbledon", "roland garros",
            "nfl", "beisebol", "hamilton", "verstappen"],
        1: ["atleta", "esporte", "torneio", "pódio", "podio", "recorde"],
    },
    "games": {
        3: ["playstation", "xbox", "nintendo", "ps5", "ps4", "videogame", "video game", "gamer",
            "e-sports", "esports", "steam", "gta ", "minecraft", "fortnite", "free fire",
            "call of duty", "league of legends", "valorant", "console", "gameplay", "dlc",
            "jogo mobile", "novo jogo", "lançamento do jogo", "game pass", "epic games", "roblox"],
        1: ["jogo", "games", "fase", "personagem jogável"],
    },
    "tecnologia": {
        3: ["inteligência artificial", "inteligencia artificial", "chatgpt", "smartphone", "iphone",
            "android", "aplicativo", "software", "hardware", "startup", "google", "microsoft",
            "apple", "samsung", "meta ", "whatsapp", "instagram", "tiktok", "internet",
            "cibersegurança", "ciberseguranca", "chip", "processador", "notebook", "gadget",
            "openai", "robô", "robo ", "5g", "computador", "celular", "tablet", "wi-fi"],
        1: ["tecnologia", "digital", "app ", "atualização", "usuários", "plataforma"],
    },
    "economia": {
        3: ["ibovespa", "dólar", "dolar", "inflação", "inflacao", "selic", "juros", "banco central",
            "bitcoin", "criptomoeda", "ethereum", "ações ", "acoes ", "bolsa de valores", "b3 ",
            "investimento", "dividendos", "fundos imobiliários", "tesouro direto", "pib ",
            "imposto de renda", "salário mínimo", "salario minimo", "fgts", "inss", "aposentadoria",
            "mercado financeiro", "wall street", "recessão", "recessao", "cripto", "renda fixa",
            "financiamento", "empréstimo", "emprestimo", "pix ", "auxílio", "auxilio", "bolsa família"],
        1: ["economia", "preço", "preco", "mercado", "lucro", "empresa", "bilhões", "bilhoes", "milhões"],
    },
    "entretenimento": {
        3: ["filme", "cinema", "netflix", "série ", "serie ", "temporada", "novela", "anime",
            "mangá", "manga ", "hollywood", "oscar", "trailer", "estreia", "streaming",
            "disney", "hbo", "prime video", "globoplay", "marvel", "dc comics", "bilheteria",
            "diretor do filme", "elenco", "spoiler"],
        1: ["episódio", "episodio", "protagonista", "ator", "atriz", "produção"],
    },
    "musica": {
        3: ["cantor", "cantora", "álbum", "album", "single", "clipe", "show ", "turnê", "turne",
            "festival de música", "sertanejo", "funk ", "pagode", "rock ", "rapper", "grammy",
            "spotify", "billboard", "anitta", "taylor swift", "banda ", "dj ", "música nova",
            "lançou a música", "hit ", "rock in rio", "lollapalooza"],
        1: ["música", "musica", "canção", "cancao", "palco", "fãs", "fas "],
    },
    "celebridades": {
        3: ["celebridade", "famoso", "famosa", "influencer", "influenciador", "bbb", "big brother",
            "reality show", "a fazenda", "affair", "namoro dos famosos", "virginia", "neymar pai",
            "casamento de", "separação de", "gravidez de", "fofoca", "paparazzi", "red carpet",
            "tapete vermelho", "look de"],
        1: ["polêmica", "polemica", "apresentador", "apresentadora", "web reagiu"],
    },
    "gastronomia": {
        3: ["receita", "restaurante", "chef ", "gastronomia", "culinária", "culinaria", "masterchef",
            "prato ", "sobremesa", "churrasco", "confeitaria", "michelin", "food truck", "cardápio",
            "cardapio", "degustação", "degustacao", "harmonização", "vinho ", "cerveja artesanal"],
        1: ["comida", "cozinha", "ingrediente", "sabor", "alimento"],
    },
    "automoveis": {
        3: ["carro elétrico", "carro eletrico", "novo carro", "lançamento do carro", "suv ", "picape",
            "sedan", "hatch", "motocicleta", "moto ", "tesla", "volkswagen", "chevrolet", "fiat ",
            "toyota", "hyundai", "honda ", "bmw", "mercedes", "ferrari", "montadora", "ipva",
            "detran", "cnh ", "combustível", "combustivel", "etanol", "gasolina", "km/l", "test drive",
            "recall", "automotivo"],
        1: ["veículo", "veiculo", "motorista", "trânsito", "transito", "carro"],
    },
    "educacao": {
        3: ["enem", "vestibular", "universidade", "faculdade", "escola", "professor", "educação",
            "educacao", "ensino médio", "ensino medio", "ensino fundamental", "bolsa de estudo",
            "prouni", "fies", "sisu", "mec ", "alfabetização", "alfabetizacao", "matrícula",
            "matricula", "curso gratuito", "pós-graduação", "graduação", "aula "],
        1: ["estudante", "aluno", "aprendizagem", "prova ", "educador"],
    },
    "planeta": {
        3: ["terremoto", "aquecimento global", "mudanças climáticas", "mudancas climaticas",
            "meio ambiente", "desmatamento", "amazônia", "amazonia", "furacão", "furacao",
            "ciclone", "tornado", "enchente", "inundação", "inundacao", "seca ", "onda de calor",
            "frente fria", "chuvas intensas", "tsunami", "vulcão", "vulcao", "queimada",
            "poluição", "poluicao", "sustentabilidade", "energia solar", "energia eólica",
            "el niño", "el nino", "la niña", "clima ", "previsão do tempo", "previsao do tempo",
            "temporal ", "deslizamento", "biodiversidade", "espécie ameaçada"],
        1: ["natureza", "ambiental", "temperatura", "graus", "floresta", "oceano"],
    },
    "ciencia_saude": {
        3: ["nasa", "spacex", "telescópio", "telescopio", "astronauta", "planeta ", "asteroide",
            "galáxia", "galaxia", "estação espacial", "estacao espacial", "foguete", "marte",
            "cientistas descobrem", "estudo revela", "pesquisa científica", "descoberta científica",
            "vacina", "anvisa", "câncer", "cancer", "diabetes", "dengue", "gripe", "covid",
            "sus ", "hospital", "cirurgia", "medicamento", "remédio", "remedio", "tratamento",
            "epidemia", "pandemia", "saúde mental", "saude mental", "ansiedade", "depressão",
            "obesidade", "alzheimer", "avc ", "infarto", "médicos", "medicos", "oms ", "dna"],
        1: ["ciência", "ciencia", "saúde", "saude", "doença", "doenca", "científico", "universo"],
    },
    "politica_mundo": {
        3: ["presidente", "lula", "bolsonaro", "congresso", "senado", "câmara dos deputados",
            "camara dos deputados", "stf", "supremo tribunal", "ministro", "governador",
            "prefeito", "eleição", "eleicao", "impeachment", "cpi ", "votação", "votacao",
            "projeto de lei", "reforma tributária", "reforma tributaria", "governo federal",
            "guerra", "israel", "palestina", "hamas", "ucrânia", "ucrania", "rússia", "russia",
            "otan", "onu ", "eua ", "estados unidos", "china ", "trump", "putin", "cessar-fogo",
            "diplomacia", "sanções", "sancoes", "parlamento", "primeiro-ministro", "ditadura",
            "democracia", "fronteira", "imigração", "imigracao", "refugiados"],
        1: ["política", "politica", "internacional", "país", "pais ", "nacional", "lei "],
    },
    "seguranca": {
        3: ["homicídio", "homicidio", "assassinato", "assassinado", "assassinada", "preso",
            "presa ", "prisão", "prisao", "delegacia", "polícia", "policia", "policial",
            "tráfico", "trafico", "traficante", "roubo", "assalto", "furto", "sequestro",
            "estupro", "feminicídio", "feminicidio", "latrocínio", "latrocinio", "facção",
            "faccao", "operação policial", "operacao policial", "mandado de prisão", "tiroteio",
            "baleado", "baleada", "esfaqueado", "esfaqueada", "corpo encontrado", "cadáver",
            "foragido", "investigação criminal", "suspeito", "criminoso", "quadrilha",
            "apreensão", "apreensao", "morto a tiros", "morta a tiros", "acidente grave",
            "atropelamento", "atropela", "atropelado", "atropelada", "vítima", "vitima",
            "morre após", "morre apos", "encontrado morto", "morre em", "morrem", "mortos",
            "morto em", "morta em", "mata ", "capota", "capotamento", "colisão", "colisao",
            "batida entre", "carro bate", "moto bate", "grave acidente", "acidente deixa",
            "acidente na", "acidente em", "acidente entre", "engavetamento"],
        1: ["crime", "violência", "violencia", "segurança pública", "delegado", "pm "],
    },
}

# Exclusões: se o texto contém estes termos, subtrai pontos da categoria
EXCLUSIONS = {
    "seguranca": ["guerra", "israel", "hamas", "ucrânia", "ucrania", "rússia", "russia", "gaza",
                  "bombardeio", "míssil", "missil", "exército", "tropas", "cessar-fogo"],
    "futebol": ["basquete", "vôlei", "volei", "fórmula 1", "formula 1", "tênis ", "ufc", "mma",
                "presidente da república", "presidente lula", "senado", "câmara dos deputados",
                "stf", "eleição", "eleicao", "ministro da"],
    "esportes": ["futebol", "brasileirão", "brasileirao", "flamengo", "corinthians", "palmeiras",
                 "libertadores", "gol ", "presidente da república", "senado", "stf",
                 "câmara dos deputados", "eleição", "eleicao"],
    "economia": ["homicídio", "homicidio", "preso", "delegacia", "terremoto", "furacão"],
    "celebridades": ["playstation", "xbox", "nintendo", "gameplay", "assassinato", "homicídio",
                     "delegacia", "preso por"],
    "automoveis": ["fórmula 1", "formula 1", "f1 ", "grande prêmio", "gp de",
                   "morre", "morrem", "morto", "morta", "mortos", "mata ", "atropela",
                   "capota", "colisão", "colisao", "acidente", "vítima", "vitima",
                   "baleado", "preso", "delegacia"],
    "ciencia_saude": ["lesão muscular", "desfalque", "jogador", "atleta"],
}

# Prioridade em caso de empate (primeiro vence)
PRIORITY = ["futebol", "seguranca", "games", "planeta", "musica", "automoveis", "gastronomia",
            "educacao", "ciencia_saude", "esportes", "economia", "tecnologia", "celebridades",
            "entretenimento", "politica_mundo"]

# Fontes com categoria PADRÃO (usada só quando a classificação não encontra sinal claro)
SOURCE_FORCED = {
    "Portal do Bitcoin": "economia",
    "Hugo Gloss": "celebridades",
    "Contigo!": "celebridades",
    "UOL Futebol": "futebol",
    "Folha Esportes": "esportes",
}

_WS_RE = re.compile(r"\s+")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

def clean_text(text: str) -> str:
    """Corrige encoding quebrado, entidades HTML e caracteres '?' de mojibake."""
    if not text:
        return ""
    # 1. Entidades HTML (&amp; &#8211; etc), aplicado 2x para casos duplamente escapados
    text = html_lib.unescape(html_lib.unescape(text))
    # 2. Remove caractere de substituição (aparece como '?' em muitos apps)
    text = text.replace("\ufffd", "")
    # 3. Mojibake comum (UTF-8 lido como Latin-1): "Ã©" -> "é"
    if any(m in text for m in ("Ã", "â€", "Â")):
        try:
            fixed = text.encode("latin-1").decode("utf-8")
            if fixed.count("\ufffd") == 0:
                text = fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    # 4. Normaliza aspas/traços tipográficos problemáticos
    for a, b in (("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
                 ("\u2013", "-"), ("\u2014", "-"), ("\u00a0", " ")):
        text = text.replace(a, b)
    # 5. Remove tags HTML residuais e caracteres de controle
    text = re.sub(r"<[^>]+>", " ", text)
    text = _CTRL_RE.sub("", text)
    return _WS_RE.sub(" ", text).strip()

def classify(title: str, summary: str = "", source_name: str = "", current: str = "") -> str:
    """Classifica a notícia em uma das 15 categorias analisando título (2x) e resumo (1x)."""
    t = f" {(title or '').lower()} "
    s = f" {(summary or '').lower()} "
    full = t + s

    scores = {}
    for cat, tiers in KW.items():
        score = 0
        for weight, words in tiers.items():
            for w in words:
                if w in t:
                    score += weight * 2  # título vale dobro
                elif w in s:
                    score += weight
        # Exclusões
        for w in EXCLUSIONS.get(cat, []):
            if w in full:
                score -= 4
        if score > 0:
            scores[cat] = score

    if not scores:
        # Sem sinal claro: usa categoria padrão da fonte, senão a atual mapeada
        if source_name in SOURCE_FORCED:
            return SOURCE_FORCED[source_name]
        mapped = OLD_TO_NEW.get((current or "").lower(), "")
        return mapped if mapped in VALID_IDS else "politica_mundo"

    best = max(scores.values())
    # Empate/quase-empate (diferença <= 1): usa ordem de prioridade
    candidates = [c for c, v in scores.items() if v >= best - 1]
    if len(candidates) > 1:
        for p in PRIORITY:
            if p in candidates:
                return p
    return max(scores, key=lambda c: scores[c])

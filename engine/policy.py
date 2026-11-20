"""
Tópico 3: Gestão de Estado, Robustez e Política de Decisão (NovaShop).

COMO LER ESTE FICHEIRO (de cima para baixo):
  1. LIMIARES        -> números que podes afinar
  2. LISTAS/PADRÕES  -> palavras e frases que o módulo procura no texto
  3. ConversationManager
       reset()             -> começa uma conversa nova (apaga a memória)
       update_and_decide() -> O CORAÇÃO: recebe os números dos tópicos 1/2,
                              atualiza a memória e escolhe UMA das 6 ações
       _generate_reply()   -> escreve a resposta (EN/PT) para a ação escolhida

IDEIA CENTRAL:
  Os tópicos 1 e 2 ESTIMAM (valência, atividade, confiança, flags).
  Este módulo DECIDE. Nunca reescreve a emoção estimada: quando há dúvida
  (sarcasmo, língua desconhecida, mensagem curta) fica mais CAUTELOSO
  (baixa a confiança e escolhe uma ação mais segura).
"""
import re

# ---------------------------------------------------------------------------
# Limites (thresholds)
# ---------------------------------------------------------------------------
# 1. Valência mede se o User está triste (-1) ou contente (1)
# 2. Activação mede se o User está calmo (-1) ou agitado (1)
# 3. "Estado Emocional" mede ao longo das interações o estado do User
# Aqui vamos definir os limites destas matrizes:

# VALÊNCIA LIMITES
# Queremos manter isto em valores altos (feliz)
# valência da mensagem, abaixo disto = mensagem negativa
VALENCE_NEG_THRESHOLD = -0.20
VALENCE_ESCALATE_THRESHOLD = -0.60          # limite negativo para escalar
# acima disto a mensagem é neutra ou positiva
NEUTRAL_RESET_THRESHOLD = -0.10

# ACTIVAÇÃO LIMITES
# Queremos manter isto em valores baixos (calmo)
ACTIVITY_HIGH_THRESHOLD = 0.45              # atividade alta
ACTIVITY_VERY_HIGH_THRESHOLD = 0.70         # atividade muito alta

# ESTADO EMOCIONAL ACUMULADO LIMITES
# estado emocional acumulado  abaixo disto = User "em baixo"
STATE_NEG_THRESHOLD = -0.25
EMA_NEW_WEIGHT = 0.45                        # peso da mensagem nova no estado

# LIMITES GERAIS
# N mensagens negativas seguidas -> oferecer humano
NEG_STREAK_OFFER = 2
# N mensagens negativas seguidas -> escalar
NEG_STREAK_ESCALATE = 3
# pedimos máximos de clarificação, para evitar ciclos
MAX_CLARIFICATIONS = 1
# limite para fecho de conversa amigável - por exemplo resolver o problema com sucesso
CLOSE_VALENCE_THRESHOLD = 0.0

# SARCASMO E CONFIANÇA
# o nível de confiança que o motor tem na emoção do User - abaixo disto -> pedir clarificação
CONFIDENCE_LOW_THRESHOLD = 0.45
# Com sarcasmo, a nossa valência  é entendida como negativa
SARCASM_VALENCE = -0.40
# Caso seja detectado sarcasmo, o nosso nível de confiança tem um limite N
SARCASM_CONFIDENCE_CAP = 0.60
# caso o sistema não detecte a língua, deve ter uma confiança máxima de N
UNKNOWN_LANG_CONFIDENCE_CAP = 0.40

# O seguinte "WORD_RE" serve para individualizar palavras numa frase, de forma a se poder analisar palavra-a-palavra.
# Neste caso, números não seriam observados
WORD_RE = r"[a-zà-ÿ']+"

# ---------------------------------------------------------------------------
# PROCURA POR KEYWORDS
# ---------------------------------------------------------------------------

# Entendemos que existem keywords que devem levar a ações automaticamente, quer para chamar uma pessoa, como para escalar

# 1 - Ameaça legal -> escalar logo
# Aqui procuramos palavras em EN ou PT, que pareçam de alguma forma mostrar que o User quer de imediato escalar a situação.
ESCALATION_PATTERNS = [
    r"\blawyers?\b", r"\bsue\b", r"\bsuing\b", r"\bcourt\b",
    r"\blegal (action|team|steps|complaint)\b",
    r"\bconsumer protection\b", r"\btrading standards\b", r"\bdeco\b", r"\bprocon\b",
    r"\badvogado\b", r"\btribunal\b", r"\bqueixa formal\b",
    r"\blivro de reclama[çc][õo]es\b", r"\bproteção do consumidor\b",
    r"\bação judicial\b", r"\bacao judicial\b",
]

# 2 - Falar com pessoa -> oferecer uma humano
# Aqui procuramos palavras que mostrem que o User pretende falar diretamente com uma pessoa
HUMAN_REQUEST_PATTERNS = [
    r"\b(speak|talk|chat) (to|with) (a |an |the )?(human|person|agent|someone|somebody|representative|manager)\b",
    r"\b(want|need|get me|give me) (a |an )?(human|person|agent|representative)\b",
    r"\breal (person|human)\b", r"\bhuman (agent|support)\b", r"\b(a|an) human\b",
    r"\bfalar com (um |uma |o |a )?(humano|pessoa|agente|atendente|responsável|responsavel|alguém|alguem)\b",
    r"\b(quero|preciso de) (um |uma )?(humano|pessoa|agente|atendente)\b",
    r"\bhumano\b", r"\batendente\b",
]

# 3 - Fecho -> terminar a conversa
# Aqui procuramos palavras que mostrem que o User viu a sua situação resolvida - fechar em bem
CLOSING_PATTERNS = [
    r"\bthank", r"\bperfect\b", r"\ball i needed\b", r"\bsolved\b", r"\bthat's all\b",
    r"\bobrigad[oa]\b", r"\bresolvido\b", r"\btudo certo\b", r"\bbye\b", r"\badeus\b",
]

# No entanto, se tivermos alguma destas palavras, entendemos que o User não pretende fechar, e apenas está chateado com a situação
CLOSING_BLOCKERS = {
    "still", "but", "however", "delay", "delayed", "late", "broken",
    "mas", "ainda", "atraso", "atrasada", "atrasado", "avariado", "avariada",
}

# 4 - Sarcasmo
# Se houver combinação destas palavras, podemos entender que há sarcasmo
# Apenas confirmamos caso a primeira análise não tenha levantado o label de "Sarcasmo
# 4.1 - Palavras sarcásticas positivas
SARCASM_POSITIVE_WORDS = {
    "great", "awesome", "wonderful", "fantastic", "amazing", "brilliant", "lovely", "perfect",
    "excelente", "ótimo", "otimo", "optimo", "maravilha", "maravilhoso", "fantástico",
    "fantastico", "perfeito", "lindo", "thanks",
}

# 4.2 - Palavras sarcásticas negativas
SARCASM_PROBLEM_WORDS = {
    "delay", "delayed", "late", "broken", "error", "issue", "problem", "wait", "waiting",
    "another", "again", "atraso", "atrasada", "atrasado", "avariado", "avariada", "erro",
    "problema", "espera", "esperar", "outro", "outra", "novamente", "nothing", "nada"
}

# 4.3 - Acrescentou-se palavras excluídas para evitar situações como "Great, problem solved"
SARCASM_EXCLUDE_WORDS = {"solved", "resolvido",
                         "thanks", "thank", "obrigado", "obrigada"}

# 5 - Palavras que podem obrigar a clarificação
# Caso se encontre problemas de clarificação -> pedir esclarecimento
AMBIGUOUS_PHRASES = {
    "ok", "okay", "k", "fine", "whatever", "hm", "hmm", "idk", "?", "...",
    "sim", "não", "nao", "talvez", "tanto faz",
}

# 6 - Palavras de Resposta
# Respostas após uma pergunta
YES_WORDS = {"yes", "yeah", "yep", "sure", "please",
             "ok", "okay", "sim", "claro", "pode", "quero"}
NO_WORDS = {"no", "nope", "nao", "não"}

# ---------------------------------------------------------------------------
# Língua
# Determinamos algumas palavras que conseguem determinar se o User está a falar em PT ou em EN
# Outras palavras, que poderiam ser noutro idioma, levam a confirmações e esclarecimentos
# ---------------------------------------------------------------------------

PT_MARKERS = {
    "obrigado", "obrigada", "não", "nao", "encomenda", "atraso", "atrasada", "resolvido",
    "ficou", "tudo", "olá", "ola", "bom", "dia", "produto", "devolução", "devolucao", "devolver",
    "ajuda", "favor", "excelente", "ótimo", "otimo", "optimo", "quero", "preciso", "minha", "meu",
    "onde", "quando", "quanto", "demora", "entrega", "morada", "falar", "com", "sim", "está",
    "estou", "já", "ainda", "porque", "pessoa", "humano", "chegou",
}
EN_MARKERS = {
    "the", "is", "my", "order", "where", "when", "how", "i", "it", "to", "and", "not", "what",
    "can", "delivery", "return", "refund", "late", "have", "was", "you", "this", "please",
    "thanks", "thank", "hello", "hi", "help", "want", "need", "still", "again", "are", "of",
    "for", "with", "been", "did", "does", "long", "address", "human", "agent", "speak", "talk",
    "someone", "arrived", "delay", "yes", "problem",
}

# ---------------------------------------------------------------------------
# Respostas por língua
# ---------------------------------------------------------------------------
REPLIES = {
    "en": {
        "ESCALATE": "I understand how serious this is. I am escalating your case immediately to a senior NovaShop specialist.",
        "OFFER_HUMAN": "I understand your frustration and would be glad to connect you with a human support agent right away. Would you like that?",
        "ASK_CLARIFICATION": "I want to make sure I help you properly. Could you please clarify what you need assistance with regarding your NovaShop order?",
        "CLOSE_POSITIVE": "You're very welcome! I'm glad everything is sorted. Thank you for shopping with NovaShop!",
        "HANDOFF": "Of course. I'm connecting you with a human NovaShop agent now.",
        "DECLINED": "No problem, I'll keep helping you myself. What do you need?",
        "EMPATHY_PREFIX": "I'm really sorry for the frustration this has caused. ",
    },
    "pt": {
        "ESCALATE": "Compreendo a gravidade da situação. Vou escalar o seu caso com prioridade máxima para um supervisor da NovaShop.",
        "OFFER_HUMAN": "Lamento o transtorno. Gostaria que o transferisse agora para um assistente humano da NovaShop?",
        "ASK_CLARIFICATION": "Quero ter a certeza de que o ajudo bem. Pode dar-me mais detalhes sobre o seu pedido ou dúvida na NovaShop?",
        "CLOSE_POSITIVE": "Fico muito contente por ter ajudado! Obrigado por escolher a NovaShop e até à próxima.",
        "HANDOFF": "Com certeza. Vou transferi-lo agora para um assistente humano da NovaShop.",
        "DECLINED": "Sem problema, continuo a ajudá-lo eu. Do que precisa?",
        "EMPATHY_PREFIX": "Lamento imenso o incómodo. ",
    },
}
# Caso se entenda que o User está a usar outra língua, pedir esclarecimento em PT ou EN
BILINGUAL_CLARIFICATION = (
    "I'm not sure I understood. Could you rephrase it in English or Portuguese? / "
    "Não tenho a certeza de ter percebido. Pode reformular em português ou inglês?"
)


# ---------------------------------------------------------------------------
# POLÍTICA
# ---------------------------------------------------------------------------
# Gere o estado emocional ao longo do tempo e decide a acção a tomar pelo assistente.

class ConversationManager:
    def __init__(self):
        self.reset()

    # Nova conversa = memória limpa.
    # Estas são as informações com que o sistema começa.
    def reset(self):
        # histórico (para o log e o relatório)
        self.turns = []
        self.state_valence = 0.0            # valência acumulada (EMA)
        self.state_activity = 0.0           # atividade acumulada (EMA)
        self.state_ready = False            # já houve alguma mensagem informativa?
        self.neg_streak = 0                 # nº de mensagens negativas seguidas
        self.clarify_streak = 0             # nº de pedidos de clarificação seguidos
        self.offered_human = False          # já oferecemos um humano nesta conversa?
        # acabámos de oferecer -> à espera de "sim"/"não"
        self.pending_offer = False
        self.last_lang = None               # última língua que reconhecemos

    # ------------------------------------------------------------------
    # Ferramentas de apoio
    # ------------------------------------------------------------------

    # Função para detectar a língua (entre PT e EN) - conforme os marcadores definidos antes
    def detect_language(self, words_set):
        pt = len(words_set & PT_MARKERS)
        en = len(words_set & EN_MARKERS)
        if pt > en:
            return "pt"
        if en > pt:
            return "en"
        return "unknown"                    # empate (ou zero evidência)

    # Função para detectar sarcasmo
    def detect_sarcasm(self, words_set):
        if words_set & SARCASM_EXCLUDE_WORDS:
            return False
        return bool(words_set & SARCASM_POSITIVE_WORDS) and bool(words_set & SARCASM_PROBLEM_WORDS)

    # Função que procura por palavras colocadas nos padrões definidos antes
    def _matches_any(self, text_lower, patterns):
        return any(re.search(p, text_lower) for p in patterns)

    # Função para perceber resposta a ofertas de um assistente humano
    def _yes_no(self, words_set, n_words):
        if n_words > 6:          # resposta longa = já não é um simples sim/não
            return None
        if words_set & NO_WORDS:
            return "no"
        if words_set & YES_WORDS:
            return "yes"
        return None

    # ------------------------------------------------------------------
    # Processo de Decisão
    # ------------------------------------------------------------------

    # 0 - Começamos por ver aquilo que recebemos do sistema, para decidir o que responder.
    def update_and_decide(self, text, valence, activity, confidence, label, input_flags=None):
        """
        Entrada: os números estimados (valence, activity, confidence, label) e,
                 opcionalmente, input_flags (ex.: {"sarcasm"}) vindas dos tópicos 1/2.
        Saída:   (action, reply, confidence_ajustada, flags, details)
        """
        clean_text = text.strip()
        text_lower = clean_text.lower()
        words = re.findall(WORD_RE, text_lower)
        words_set = set(words)
        input_flags = set(input_flags or [])
        flags = []

        # ------------------------------------------------------------------
        # 1 - Perceber a língua
        # Começamos por presumir que é em EN
        lang = self.detect_language(words_set)
        if lang == "unknown" and self.last_lang:
            # Se não percebermos a língua desta mensagem mas já a percebemos antes
            lang = self.last_lang
        elif lang == "unknown":
            flags.append("lang_unknown")
            confidence = min(confidence, UNKNOWN_LANG_CONFIDENCE_CAP)
        else:
            self.last_lang = lang
        if lang == "pt":
            flags.append("lang_pt")

        # ------------------------------------------------------------------
        # 2 - Confirmamos se há sarcasmo sarcasmo
        # Pode ser esta função a perceber isso, ou essa função vir de antes
        sarcastic = ("sarcasm" in input_flags) or self.detect_sarcasm(
            words_set)
        eff_valence = valence
        if sarcastic:
            flags.append("sarcasm_suspected")
            confidence = min(confidence, SARCASM_CONFIDENCE_CAP)
            eff_valence = min(valence, SARCASM_VALENCE)

        # ------------------------------------------------------------------
        # 3 - Incerteza, quando o sistema não percebeu o que é preciso
        is_too_short = len(words) <= 1 and len(clean_text) < 5
        stripped = text_lower.strip(" .!,")
        is_ambiguous = (text_lower in AMBIGUOUS_PHRASES or stripped in AMBIGUOUS_PHRASES
                        or (stripped == "" and text_lower != "") or "whatever" in words_set)
        low_confidence = confidence < CONFIDENCE_LOW_THRESHOLD
        uncertain = low_confidence or is_too_short or is_ambiguous

        # Assume uma label de "pouca confiança" ou de "ambiguidade"
        if is_too_short or is_ambiguous:
            flags.append("ambiguous_or_short")
            confidence = min(confidence, 0.30)
        if low_confidence:
            flags.append("low_confidence")

        # ------------------------------------------------------------------
        # 4 - Actualizar a informação
        # Mensagens incertas não dizem nada de fiável sobre a emoção
        if not uncertain:
            if not self.state_ready:
                self.state_valence = eff_valence
                self.state_activity = activity
                self.state_ready = True
            else:
                w = EMA_NEW_WEIGHT
                self.state_valence = w * eff_valence + \
                    (1 - w) * self.state_valence
                self.state_activity = w * activity + \
                    (1 - w) * self.state_activity

            if eff_valence <= VALENCE_NEG_THRESHOLD:
                self.neg_streak += 1
            elif eff_valence > NEUTRAL_RESET_THRESHOLD:
                self.neg_streak = 0     # neutra ou positiva quebra a sequência

        # ------------------------------------------------------------------
        # 5 - Padrões no texto
        # Procuramos na mensagem as palavras padrão
        has_threat = self._matches_any(text_lower, ESCALATION_PATTERNS)
        has_human_request = self._matches_any(
            text_lower, HUMAN_REQUEST_PATTERNS)
        has_closing_cue = self._matches_any(text_lower, CLOSING_PATTERNS)
        has_closing_blocker = bool(words_set & CLOSING_BLOCKERS)
        if has_threat:
            flags.append("legal_or_escalation_threat")
        if has_human_request:
            flags.append("human_request")

        # A parte a seguir serve para quando o chat pergunta se quer ajuda humana
        # Isto faz com que o chat fique à espera de uma resposta (positiva ou negativa) à pergunta, e conforme a resposta, re-adapta (ou não) o assunto
        was_pending = self.pending_offer
        self.pending_offer = False
        answer_to_offer = None
        if was_pending and not (has_threat or has_human_request):
            answer_to_offer = self._yes_no(words_set, len(words))

        # ------------------------------------------------------------------
        # 6 - Árvore de decisão
        # Procuramos que regra a aplicar e seguimos uma ordem onde aplicamos a plimeira que funcionar

        # Caso o User tenha aceite ou negado uma proposta, há uma frase anterior à resposta automática - um handoff ou um decline
        note = None

        # Caso responda que "Sim" a uma oferta, escalamos para uma pessoa
        # Caso para o "Não", colocamos como rejeitada a oferta
        if answer_to_offer == "yes":
            action, rule, note = "ESCALATE", "accepted_human_offer", "HANDOFF"
        elif answer_to_offer == "no":
            action, rule, note = "ANSWER", "declined_human_offer", "DECLINED"

        # Caso a mensagem tenha uma threat legal, escalar de imediato, independentemente do estado emocional
        elif has_threat:
            action, rule = "ESCALATE", "legal_threat"

        # Caso a mensagem seja a pedir contacto, se está mal, ou se já tivermos apresentado a oferta, segue logo
        # Senão, fazer a pergunta e esperar pelo sim ou não
        elif has_human_request:
            if (self.state_valence <= VALENCE_ESCALATE_THRESHOLD
                    or activity >= ACTIVITY_VERY_HIGH_THRESHOLD
                    or self.offered_human):
                action, rule = "ESCALATE", "human_request_bad_state"
            else:
                action, rule = "OFFER_HUMAN", "human_request"

        # Caso a mensagem seja clara (não incerta) e o User estiver com valores de valência baixos + de atividade muito alta, ou tiver atingido o nosso limite de mensagens negativas -> Escalar
        elif (not uncertain) and (
                (self.state_valence <= VALENCE_ESCALATE_THRESHOLD
                 and self.state_activity >= ACTIVITY_HIGH_THRESHOLD)
                or self.neg_streak >= NEG_STREAK_ESCALATE):
            # Frustração acumulada.
            action, rule = "ESCALATE", "accumulated_frustration"
            flags.append("accumulated_frustration")

        # Caso existam mensagens ambiguas e já tivermos várias mensagens negativas -> Escalar
        elif uncertain and (self.neg_streak >= NEG_STREAK_ESCALATE
                            or (self.state_ready and self.state_valence <= VALENCE_ESCALATE_THRESHOLD
                                and self.state_activity >= ACTIVITY_HIGH_THRESHOLD)):
            # Cliente já estava no limite e mandou um "ok"/"...": a frustração
            # ganha à ambiguidade (não faz sentido perguntar "o que quer dizer?").
            action, rule = "ESCALATE", "accumulated_frustration_uncertain"
            flags.append("accumulated_frustration")

        # Caso a mensagem seja incerta pedimos esclarecimento
        # Caso se atinja o limite de esclarecimentos -> Oferecer uma pessoa
        # Caso também já se tenha perguntado isso -> Escalar
        elif uncertain:
            if (self.clarify_streak >= MAX_CLARIFICATIONS
                    or (self.state_ready and self.state_valence <= STATE_NEG_THRESHOLD)):
                if self.offered_human:
                    action, rule = "ESCALATE", "uncertain_after_offer"
                else:
                    action, rule = "OFFER_HUMAN", "uncertain_offer"
            else:
                action, rule = "ASK_CLARIFICATION", "uncertain_ask"

        # Caso a valência esteja negativa -> Oferecer uma pessoa
        # Caso já se tenha oferecido ou esteja no limite de mensagens negativas -> Escalar
        # Senão responder de forma empática
        elif eff_valence <= VALENCE_NEG_THRESHOLD or self.state_valence <= STATE_NEG_THRESHOLD:
            if self.neg_streak >= NEG_STREAK_OFFER and not self.offered_human:
                action, rule = "OFFER_HUMAN", "negative_streak_offer"
            elif self.neg_streak >= NEG_STREAK_OFFER and self.offered_human:
                action, rule = "ESCALATE", "negative_streak_after_offer"
            else:
                action, rule = "ANSWER_EMPATHIC", "negative"

        # Caso tenha usado termos para fechar a conversa e esteja tudo bem -> Fechar positivo
        elif (has_closing_cue and eff_valence >= CLOSE_VALENCE_THRESHOLD
              and "?" not in text_lower and not has_closing_blocker
              and self.state_valence > STATE_NEG_THRESHOLD):
            action, rule = "CLOSE_POSITIVE", "closing"

        # Qualquer outra mensagem que não se adeque às regras anteriores -> Answer
        # É a acção Default
        else:
            action, rule = "ANSWER", "default"

        # ------------------------------------------------------------------
        # 7 - Actualizar estados e flags, e gerar resposta

        # Actualizar estado caso tenha sido oferecido um agente
        if action == "OFFER_HUMAN":
            self.offered_human = True
            self.pending_offer = True

        # Actualizar pedidos de esclarecimento
        if action == "ASK_CLARIFICATION":
            self.clarify_streak += 1
        else:
            self.clarify_streak = 0

        # Chama a função de resposta, conforme as características definidas anteriormente
        reply = self._generate_reply(action, text_lower, lang, note)

        # Adiciona informação ao histórico da conversa
        self.turns.append({
            "valence": valence,
            "eff_valence": round(eff_valence, 3),
            "activity": activity,
            "state_valence": round(self.state_valence, 3),
            "action": action,
            "rule": rule,
        })

        # Cria um dicionário para informar como e porquê a decisão deste turno foi tomada
        details = {
            "lang": lang,
            "sarcasm": sarcastic,
            "valence_adjusted": round(eff_valence, 3),
            "state_valence": round(self.state_valence, 3),
            "state_activity": round(self.state_activity, 3),
            "neg_streak": self.neg_streak,
            "clarify_streak": self.clarify_streak,
            "offered_human": self.offered_human,
            "rule": rule,
            "turn": len(self.turns),
        }
        return action, reply, round(confidence, 3), flags, details

    # ------------------------------------------------------------------
    # Processo de Resposta
    # ------------------------------------------------------------------
    # A fase anterior é o processo de decisão - agora que temos os valores definidos, já podemos activamente responder

    # Função da resposta
    def _generate_reply(self, action, text_lower, lang, note=None):

        # Define-se que caso não seja esclarecido em termos de línguas, seguimos em EN
        if lang == "unknown":
            if action == "ASK_CLARIFICATION":
                return BILINGUAL_CLARIFICATION
            lang = "en"

        # Responde conforme o nosso dicionário de respostas já definido
        r = REPLIES[lang]

        # Responde conforme o User tenha respondido a "Ofertas de Humanos"
        if note in ("HANDOFF", "DECLINED"):
            return r[note]
        if action in ("ESCALATE", "OFFER_HUMAN", "ASK_CLARIFICATION", "CLOSE_POSITIVE"):
            return r[action]

        # Responde "Answer" ou "Answer Empathic" conforme o nível de frustração + a resposta à pergunta do User
        faq = self._faq(text_lower, lang)
        if action == "ANSWER_EMPATHIC":
            return r["EMPATHY_PREFIX"] + faq
        return faq

    # Função de resposta À PERGUNTA DO USER
    def _faq(self, text_lower, lang):

        # Procura por sequências numéricas para procurar - por exemplo - números de encomendas
        order_match = re.search(r"\b(\d{3,})\b", text_lower)

        # Procura palavras-chave, e conforma aquilo que encontra, responde algo pré definido
        # Caso seja PT:
        if lang == "pt":
            if "entrega" in text_lower and "morada" in text_lower:
                return "Pode atualizar a morada de entrega na sua conta NovaShop antes de a encomenda ser expedida."
            if "entrega" in text_lower or "demora" in text_lower or "quanto tempo" in text_lower:
                return "A entrega standard da NovaShop demora 2 a 4 dias úteis."
            if "devol" in text_lower:
                return "Pode devolver qualquer artigo no prazo de 30 dias na secção 'As Minhas Encomendas' da NovaShop."
            if order_match:
                return f"Estou já a verificar o estado da sua encomenda n.º {order_match.group(1)}."
            if any(k in text_lower for k in ("encomenda", "pedido", "atraso", "atrasad", "chegou")):
                return "Indique-me o número da encomenda para eu verificar o estado do envio."
            return "Estou aqui para ajudar com a sua dúvida na NovaShop. Pode dar-me mais alguns detalhes?"

        # Caso seja EN:
        if "delivery" in text_lower and "address" in text_lower:
            return "You can update your delivery address in your NovaShop account before the order is dispatched."
        if "delivery" in text_lower or "long" in text_lower:
            return "Standard NovaShop delivery takes 2 to 4 business days."
        if "return" in text_lower:
            return "You can return any item within 30 days through the 'My Orders' section on NovaShop."
        if order_match:
            return f"I am checking the status of your order #{order_match.group(1)} right away."
        if any(k in text_lower for k in ("order", "late", "delay", "arrived")):
            return "Please share your order number so I can check the shipment status right away."
        return "I'm here to help with your NovaShop inquiry. Could you share a few more details?"
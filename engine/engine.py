import json
import os
import re
import math

from .vocabulary import (
    EMOTION_PROTOTYPES,
    HIGH_DOMINANCE_WORDS,
    INTENSIFIERS,
    LOW_DOMINANCE_WORDS,
    NEGATIONS,
    NEUTRAL_RADIUS,
)
from .policy import ConversationManager


class Engine:
    def __init__(self):
        self._load_lexicon()
        self.reset()

     #Carrega o dataset
    def _load_lexicon(self):
        data_path = os.path.join(os.path.dirname(__file__), "lexicon_dataset.json")
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                self.lexicon = json.load(f)
        except FileNotFoundError:
            self.lexicon = {}
    #Chamado no início de cada nova conversa, para limpar o histórico
    def reset(self):
        
        if not hasattr(self, "lexicon"):
            self._load_lexicon()
        self.history = []
        # Tópico 3: memória da conversa (estado acumulado, streaks, ofertas de humano)
        self.policy = ConversationManager()

    def process(self, text, audio_path=None, image_path=None):
        # Extrair palavras do texto, convertendo para minúsculas e removendo pontuação
        words = re.findall(r"[a-z'-]+", text.lower())
        
        total_valence = 0.0
        total_activity = 0.0
        ##para verifircar quantas palavras do texto estão no dataset, para calcular a confiança
        matched_words = 0
        ## para o caso de negação e intensificador
        negated = False
        multiplier = 1.0
        
        for word in words:
            # 1. Verificar se é negação(caso for atraves do continue, ele vai pular para a próxima palavra)
            if word in NEGATIONS:
                negated = True
                continue
            
            # 2. Verificar se é intensificador(caso for atraves do continue, ele vai pular para a próxima palavra)
            if word in INTENSIFIERS:
                multiplier = INTENSIFIERS[word]
                continue
            
            # 3. Verificar se a palavra está no dataset
            if word in self.lexicon:
                entry = self.lexicon[word]
                v = entry["valence"]
                a = entry["activity"]
                lbl = entry["label"]
                
                # Aplicar negação (inverte a valência e atenua ligeiramente)
                if negated:
                    v = -v * 0.8
                    negated = False
                
                # Aplicar intensificador(maximiza a valência e atividade, mas não ultrapassa os limites de -1 a 1)
                v = max(-1.0, min(1.0, v * multiplier)) 
                if multiplier > 1.0:
                    a = max(-1.0, min(1.0, a * 1.2))
                multiplier = 1.0
                
                total_valence += v
                total_activity += a
                matched_words += 1

        # Calcular Valência e Atividade médias
        if matched_words > 0:
            valence = max(-1.0, min(1.0, total_valence / matched_words))
            activity = max(-1.0, min(1.0, total_activity / matched_words))
        else:
            valence = 0.0
            activity = 0.0

        #pontos de exclamação(se houver pontos de exclamação, aumenta a atividade) 
        exclamations = text.count("!")
        if exclamations > 0:
            activity = min(1.0, activity + min(0.4, exclamations * 0.15))

        # letras maiúsculas (se mais de 60% das letras forem maiúsculas e houver pelo menos 4 letras, aumenta a atividade)    
        alpha_chars = [c for c in text if c.isalpha()]
        if len(alpha_chars) >= 4:
            caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if caps_ratio > 0.6:
                activity = min(1.0, activity + 0.3)

        # Calcular Confiança (0 a 1) com base nas palavras iguais a do dataset e tamanho da frase
        if len(words) == 0:
            confidence = 0.1
        elif matched_words == 0:
            confidence = 0.25
        else:
            coverage = matched_words / len(words)
            confidence = min(0.95, 0.45 + (coverage * 0.4) + min(0.15, matched_words * 0.05))

        # Calcular Dominância (-1 a 1) para ativar o mapa 3D e melhorar a distinção de rótulos
        dominance = self._estimate_dominance(text, words, valence, activity)
        # Escolher o label dominante usando a distância euclidiana
        label = self._euclidean_distance(valence, activity,dominance)

        self.history.append(valence)

        # Tópico 3: a política decide a acção e escreve a resposta, com base no estado da conversa
        action, reply, confidence, flags, policy_details = self.policy.update_and_decide(
            text, valence, activity, confidence, label
        )

        details = {
            "words_count": len(words),
            "matched_words": matched_words,
            "negation_used": "yes" if any(w in NEGATIONS for w in words) else "no",
        }
        details.update(policy_details)

        return {
            "valence": round(valence, 3),
            "activity": round(activity, 3),
            "dominance": round(dominance, 3),
            "confidence": round(confidence, 3),
            "label": label,
            "action": action,
            "reply": reply,
            "flags": flags,
            "details": details,
        }

# vamos usar a distancia euclidiana, onde qualquer ponto fora da zona neutra, calcula-se a distância euclidiana do ponto atual a cada protótipo e escolhe-se o mais próximo
    
    def _euclidean_distance(self, valence, activity, dominance=None):
        # 1. Verifica se está dentro da zona neutra (distância à origem)
        if math.hypot(valence, activity) < NEUTRAL_RADIUS:
            return "neutral"

        # 2. Encontra o protótipo emocional mais próximo
        best_label = "neutral"
        best_dist = float("inf")

        for label, (pv, pa, pd) in EMOTION_PROTOTYPES.items():
            if dominance is None:
                dist = math.hypot(valence - pv, activity - pa)
            else:
                dist = math.sqrt((valence - pv) ** 2 + (activity - pa) ** 2 + (dominance - pd) ** 2)

            if dist < best_dist:
                best_dist = dist
                best_label = label

        return best_label

    def _estimate_dominance(self, text, words, valence, activity):
        score = 0.0

        # 1. Pistas lexicais de controlo vs. submissão/incerteza
        for word in words:
            if word in HIGH_DOMINANCE_WORDS:
                score += 0.35
            elif word in LOW_DOMINANCE_WORDS:
                score -= 0.30

        # 2. Pistas de pontuação e maiúsculas
        if text.count("!") > 0:
            score += min(0.3, text.count("!") * 0.15)
        if text.count("?") > 0:
            score -= min(0.25, text.count("?") * 0.12)

        alpha_chars = [c for c in text if c.isalpha()]
        if len(alpha_chars) >= 4:
            caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if caps_ratio > 0.6:
                score += 0.35

        # 3. Se não houver pistas fortes, usa uma base suave a partir da valência
        if abs(score) < 0.05:
            score = valence * 0.25

        return max(-1.0, min(1.0, score))
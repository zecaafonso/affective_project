
import json
import os
import re
import math

# Protótipos de emoções com base em valência, atividade e dominância
EMOTION_PROTOTYPES = {
    "joy":         ( 0.75,  0.55,  0.40),
    "calm":        ( 0.55, -0.45,  0.20),
    "anger":       (-0.75,  0.75,  0.65),  # Alta dominância (exigente/agressivo)
    "fear":        (-0.70,  0.70, -0.65),  # Baixa dominância (inseguro/sem controlo)
    "frustration": (-0.55,  0.35, -0.10),
    "sadness":     (-0.65, -0.50, -0.50),
}
# Raio para considerar uma emoção como neutra
NEUTRAL_RADIUS = 0.22


NEGATIONS = {
    "not", "no", "never", "dont", "don't", "cant", "can't", 
    "wont", "won't", "isnt", "isn't", "wasnt", "wasn't", 
    "didnt", "didn't", "doesnt", "doesn't", "neither", "nor", "nothing"
}

INTENSIFIERS = {
    "very": 1.4,
    "extremely": 1.8,
    "super": 1.6,
    "really": 1.4,
    "so": 1.3,
    "incredibly": 1.7,
    "totally": 1.5,
    "completely": 1.5,
    "absolutely": 1.6,
    "slightly": 0.5,
    "somewhat": 0.6,
    "barely": 0.4,
    "hardly": 0.4,
    "little": 0.6,
    "bit": 0.6
}


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

    def process(self, text, audio_path=None, image_path=None):
        # Extrair palavras do texto, convertendo para minúsculas e removendo pontuação
        words = re.findall(r"[a-z'-]+", text.lower())
        
        total_valence = 0.0
        total_activity = 0.0
        ##para verifircar quantas palavras do texto estão no dataset, para calcular a confiança
        matched_words = 0
        ##para contar (labels) para escolher a dominante
       ## label_votes = {}  // tenho que apagar para a parte 2 funcionar
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
                if negated: # tive q alterar
                    v = -v * 0.8
                    # inverte a etiqueta se foi negada
                 #   if lbl in ("joy", "calm") and v < 0:
                 #       lbl = "frustration"
                 #   elif lbl in ("anger", "frustration", "sadness") and v > 0:
                 #       lbl = "calm"
                    negated = False
                
                # Aplicar intensificador(maximiza a valência e atividade, mas não ultrapassa os limites de -1 a 1)
                v = max(-1.0, min(1.0, v * multiplier)) 
                if multiplier > 1.0:
                    a = max(-1.0, min(1.0, a * 1.2))
                multiplier = 1.0
                
                total_valence += v
                total_activity += a
                matched_words += 1
                #tive q tirar igualmente e passar diretamente ao if de baixo
             #   label_votes[lbl] = label_votes.get(lbl, 0) + abs(v) + 0.1

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

        # Escolher o label dominante
    #    if matched_words == 0 or (abs(valence) < 0.15 and abs(activity) < 0.2):
    #        label = "neutral"
    #    elif label_votes:
    #        label = max(label_votes, key=label_votes.get)
    #    else:
    #        label = "neutral"
        # Escolher o label dominante usando a distância euclidiana
        label = self._euclidean_distance(valence, activity)

        self.history.append(valence)

        # Acredito que esta parte seja do topico 3 
        action = "ANSWER"
        if valence <= -0.6 and activity >= 0.5:
            action = "ESCALATE"
        elif valence <= -0.3:
            action = "ANSWER_EMPATHIC"
        elif confidence < 0.3:
            action = "ASK_CLARIFICATION"
        elif valence >= 0.5:
            action = "CLOSE_POSITIVE"

        return {
            "valence": round(valence, 3),
            "activity": round(activity, 3),
            "confidence": round(confidence, 3),
            "label": label,
            "action": action,
            "reply": "Thank you for contacting NovaShop support. How can I assist you further?",
            "flags": [],
            "details": {
                "words_count": len(words),
                "matched_words": matched_words,
                "negation_used": "yes" if any(w in NEGATIONS for w in words) else "no"
            }
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
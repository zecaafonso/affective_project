##############################################################################################################################################
# """STARTER ENGINE - this is the only place your group edits (you may add more files in engine/).

# It is intentionally weak: a tiny lexicon, no negation, no rules, no memory of the conversation, no
# language handling, and it always answers the same way. Your job is to turn it into a real affective
# engine. Keep the contract: process() must return a dict with these keys:

#     valence    float in [-1, 1]   negative <-> positive
#     activity   float in [-1, 1]   deactivated <-> activated   (also called arousal)
#     confidence float in [0, 1]    how much you trust this estimate
#     label      str                e.g. neutral, anger, fear, frustration, sadness, joy, calm
#     action     str                one of: ANSWER, ANSWER_EMPATHIC, ASK_CLARIFICATION, OFFER_HUMAN,
#                                   ESCALATE, CLOSE_POSITIVE
#     reply      str                what the assistant says
#   optional:
#     dominance  float in [-1, 1]   (enables the 3D view of the map)
#     flags      list of str        e.g. ["human_request"]
#     details    dict               anything useful for the log (it is written to the .txt log)
# """
# import re

# NEGATIVE = {"bad": -0.5, "terrible": -0.8, "angry": -0.8, "late": -0.4, "unacceptable": -0.8}
# POSITIVE = {"thanks": 0.6, "thank": 0.6, "great": 0.7, "good": 0.5, "perfect": 0.8}


# class Engine:
#     def reset(self):
#         """Called at the start of every new conversation."""
#         self.history = []

#     def process(self, text, audio_path=None, image_path=None):
#         words = re.findall(r"[a-z']+", text.lower())
#         score = sum(NEGATIVE.get(w, 0) + POSITIVE.get(w, 0) for w in words)
#         valence = max(-1.0, min(1.0, score))
#         activity = 0.3 if "!" in text else 0.0
#         label = "neutral" if abs(valence) < 0.2 else ("joy" if valence > 0 else "frustration")
#         self.history.append(valence)
#         return {"valence": valence, "activity": activity, "confidence": 0.3, "label": label,
#                 "action": "ANSWER", "reply": "Thanks for your message. How can I help?",
#                 "flags": [], "details": {"words": len(words)}}

######################################################################################################################################

# import json
# import os
# import re

# NEGATIONS = {
#     "not", "no", "never", "dont", "don't", "cant", "can't", 
#     "wont", "won't", "isnt", "isn't", "wasnt", "wasn't", 
#     "didnt", "didn't", "doesnt", "doesn't", "neither", "nor", "nothing"
# }

# INTENSIFIERS = {
#     "very": 1.4,
#     "extremely": 1.8,
#     "super": 1.6,
#     "really": 1.4,
#     "so": 1.3,
#     "incredibly": 1.7,
#     "totally": 1.5,
#     "completely": 1.5,
#     "absolutely": 1.6,
#     "slightly": 0.5,
#     "somewhat": 0.6,
#     "barely": 0.4,
#     "hardly": 0.4,
#     "little": 0.6,
#     "bit": 0.6
# }


# class Engine:
#     def __init__(self):
#         self._load_lexicon()
#         self.reset()

#      #Carrega o dataset
#     def _load_lexicon(self):
#         data_path = os.path.join(os.path.dirname(__file__), "lexicon_dataset.json")
#         try:
#             with open(data_path, "r", encoding="utf-8") as f:
#                 self.lexicon = json.load(f)
#         except FileNotFoundError:
#             self.lexicon = {}
#     #Chamado no início de cada nova conversa, para limpar o histórico
#     def reset(self):
        
#         if not hasattr(self, "lexicon"):
#             self._load_lexicon()
#         self.history = []

#     def process(self, text, audio_path=None, image_path=None):
#         # Extrair palavras do texto, convertendo para minúsculas e removendo pontuação
#         words = re.findall(r"[a-z'-]+", text.lower())
        
#         total_valence = 0.0
#         total_activity = 0.0
#         ##para verifircar quantas palavras do texto estão no dataset, para calcular a confiança
#         matched_words = 0
#         ##para contar (labels) para escolher a dominante
#         label_votes = {}
#         ## para o caso de negação e intensificador
#         negated = False
#         multiplier = 1.0
        
#         for word in words:
#             # 1. Verificar se é negação(caso for atraves do continue, ele vai pular para a próxima palavra)
#             if word in NEGATIONS:
#                 negated = True
#                 continue
            
#             # 2. Verificar se é intensificador(caso for atraves do continue, ele vai pular para a próxima palavra)
#             if word in INTENSIFIERS:
#                 multiplier = INTENSIFIERS[word]
#                 continue
            
#             # 3. Verificar se a palavra está no dataset
#             if word in self.lexicon:
#                 entry = self.lexicon[word]
#                 v = entry["valence"]
#                 a = entry["activity"]
#                 lbl = entry["label"]
                
#                 # Aplicar negação (inverte a valência e atenua ligeiramente,
#                 # atenua-se porque a negação não é tão forte quanto a palavra original, e não ultrapassa os limites de -1 a 1
#                 if negated:
#                     v = -v * 0.8
#                     # inverte a etiqueta se foi negada
#                     if lbl in ("joy", "calm") and v < 0:
#                         lbl = "frustration"
#                     elif lbl in ("anger", "frustration", "sadness") and v > 0:
#                         lbl = "calm"
#                     negated = False
                
#                 # Aplicar intensificador
#                 # maximiza a valência e atividade,porque o intensificador aumenta a intensidade da palavra, e não ultrapassa os limites de -1 a 1
#                 v = max(-1.0, min(1.0, v * multiplier)) 
#                 if multiplier > 1.0:
#                     a = max(-1.0, min(1.0, a * 1.2))
#                 multiplier = 1.0
                
#                 total_valence += v
#                 total_activity += a
#                 matched_words += 1
#                 label_votes[lbl] = label_votes.get(lbl, 0) + abs(v) + 0.1

#         # Calcular Valência e Atividade médias
#         # dividir pelo número de palavras correspondentes,porque se não tiver palavras correspondentes, valência e atividade serão 0
#         if matched_words > 0:
#             valence = max(-1.0, min(1.0, total_valence / matched_words))
#             activity = max(-1.0, min(1.0, total_activity / matched_words))
#         else:
#             valence = 0.0
#             activity = 0.0

#         # pontos de exclamação
#         # se houver pontos de exclamação, aumenta a atividade,em 0.15 por ponto de exclamação até um máximo de 0.4, e não ultrapassa 1.0)
#         exclamations = text.count("!")
#         if exclamations > 0:
#             activity = min(1.0, activity + min(0.4, exclamations * 0.15))

#         # letras maiúsculas 
#         # se mais de 60% das letras forem maiúsculas e houver pelo menos 4 letras, aumenta a atividade em 0.3, e não ultrapassa 1.0
#         alpha_chars = [c for c in text if c.isalpha()]
#         if len(alpha_chars) >= 4:
#             caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
#             if caps_ratio > 0.6:
#                 activity = min(1.0, activity + 0.3)

#         # Calcular Confiança (0 a 1) com base nas palavras iguais a do dataset e tamanho da frase
#         if len(words) == 0:
#             confidence = 0.1
#         elif matched_words == 0:
#             confidence = 0.25
#         else:
#             coverage = matched_words / len(words)
#             confidence = min(0.95, 0.45 + (coverage * 0.4) + min(0.15, matched_words * 0.05))

#         # Escolher o label dominante
#         # Se não houver palavras correspondentes ou se a valência e atividade forem muito próximas de zero, o label será "neutral". Caso contrário, o label será o que tiver mais votos
#         if matched_words == 0 or (abs(valence) < 0.15 and abs(activity) < 0.2):
#             label = "neutral"
#         elif label_votes:
#             label = max(label_votes, key=label_votes.get)
#         else:
#             label = "neutral"

#         self.history.append(valence)

#         # Acredito que esta parte seja do topico 3 
#         action = "ANSWER"
#         if valence <= -0.6 and activity >= 0.5:
#             action = "ESCALATE"
#         elif valence <= -0.3:
#             action = "ANSWER_EMPATHIC"
#         elif confidence < 0.3:
#             action = "ASK_CLARIFICATION"
#         elif valence >= 0.5:
#             action = "CLOSE_POSITIVE"

#         return {
#             "valence": round(valence, 3),
#             "activity": round(activity, 3),
#             "confidence": round(confidence, 3),
#             "label": label,
#             "action": action,
#             "reply": "Thank you for contacting NovaShop support. How can I assist you further?",
#             "flags": [],
#             "details": {
#                 "words_count": len(words),
#                 "matched_words": matched_words,
#                 "negation_used": "yes" if any(w in NEGATIONS for w in words) else "no"
#             }
#         }




    #____________________________________________________________________________________________________________________________________________#

import json
import os
import re

Negations = {
    "not", "no", "never", "dont", "don't", "cant", "can't", 
    "wont", "won't", "isnt", "isn't", "wasnt", "wasn't", 
    "didnt", "didn't", "doesnt", "doesn't", "neither", "nor", "nothing"
}

Intesifiers = {
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

    def _load_lexicon(self):
        data_path=os.path.join(os.path.dirname(__file__),"lexicon_dataset.json")
        try:
            with open(data_path,"r",encoding="utf-8") as f:
                self.lexicon = json.load(f)
        except:
            self.lexicon = {}

    def reset(self):
        if not hasattr(self,"lexicon"):
            self._load_lexicon()
        self.history=[]

    def process(self, text, audio_path=None, image_path=None):

        words = re.findall(r"[a-z'-]+", text.lower())

        total_valance=0.0
        total_activity=0.0
        matched_words=0
        label_votes={}

        negated=False
        multiplier=1.0

        for word in words:

            if word in Negations:
                negated=True
                continue

            if word in Intesifiers:
                multiplier=Intesifiers[word]
                continue
            if word in self.lexicon:
                entry = self.lexicon[word]
                v = entry["valence"]
                a = entry["activity"]
                lbl = entry["label"]

                if negated:
                    v=-v*0.8
                    


                



    

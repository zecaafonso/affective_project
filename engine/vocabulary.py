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

#dominancia
HIGH_DOMINANCE_WORDS = {
    "demand", "immediately", "now", "refund", "cancel", "manager",
    "unacceptable", "must", "need", "want", "insist", "fix", "lawsuit",
    "ridiculous", "stop", "guarantee", "compensate"
}

LOW_DOMINANCE_WORDS = {
    "help", "please", "sorry", "confused", "lost", "worried", "afraid",
    "scared", "unsure", "maybe", "might", "hope", "could", "would",
    "unable", "problem", "broken", "stuck"
}


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
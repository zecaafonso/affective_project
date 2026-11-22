"""Exploratory SAM evaluation of the NovaShop engine (topic 5).

Needs the packages in requirements.txt (pandas, openpyxl, scipy, scikit-learn, matplotlib).
They are only used here; the app and the tests use the standard library only.

    pip install -r requirements.txt
    python evaluation/calcular_metricas_sam_5_avaliadores.py [ratings.xlsx]

Reads the 5 rater sheets (Avaliador_1..Avaliador_5) and the system predictions (Sistema)
and writes into evaluation/Resultados_NovaShop/:

    resumo_metricas.txt          summary: label metrics, confusion matrix, SAM correlations
    resultados_avaliacao.xlsx    sheets Resultados_Detalhados, Matriz_Confusao and Erros (label errors)
    matriz_confusao.png          confusion matrix (rows: human majority label, columns: system label)
    f1_por_emocao.png            F1-score per emotion
    comparacao_vad.png           mean human SAM vs mean system value per dimension
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')  # write PNG files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,
                             confusion_matrix, f1_score, mean_absolute_error)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_XLSX = os.path.join(HERE, 'NovaShop_SAM_5_Avaliadores.xlsx')
OUT_DIR = os.path.join(HERE, 'Resultados_NovaShop')

CLASSES = ['neutral', 'joy', 'calm', 'sadness', 'fear', 'anger', 'frustration']
COLS = ['SAM Valence (1-9)', 'SAM Arousal (1-9)', 'SAM Dominance (1-9)', 'Rótulo humano']
# (name, rater column, system column). SAM Arousal is compared with the engine's Activity.
DIMENSIONS = [('valence', 'SAM Valence (1-9)', 'Valence'),
              ('arousal', 'SAM Arousal (1-9)', 'Activity'),
              ('dominance', 'SAM Dominance (1-9)', 'Dominance')]


def load(filename):
    """Read and validate the workbook. Returns (system sheet, list of the 5 rater sheets)."""
    system = pd.read_excel(filename, sheet_name='Sistema')
    ratings = []
    for participant in range(1, 6):
        d = pd.read_excel(filename, sheet_name=f'Avaliador_{participant}')
        incomplete = d[COLS].isna().any(axis=1)
        if incomplete.any():
            raise SystemExit(f'Avaliador_{participant}: falta preencher {int(incomplete.sum())} mensagens '
                             f'(linhas Excel {(d.index[incomplete] + 2).tolist()}).')
        if not d['ID'].equals(system['ID']):
            raise SystemExit(f'Avaliador_{participant}: IDs não coincidem com o separador Sistema.')
        for col in COLS[:3]:
            d[col] = pd.to_numeric(d[col], errors='coerce')
            if d[col].isna().any() or (~d[col].between(1, 9)).any() or (d[col] % 1 != 0).any():
                raise SystemExit(f'Avaliador_{participant}: valor inválido em {col}. Usa inteiros 1 a 9.')
        ratings.append(d)
    return system, ratings


def build_results(system, ratings):
    """One row per message: majority human label, mean SAM (mapped to -1..1) and system values."""
    rows = []
    for i, s in system.iterrows():
        labels = [str(r.loc[i, 'Rótulo humano']).strip().lower() for r in ratings]
        if any(label not in CLASSES for label in labels):
            raise SystemExit(f'ID {s["ID"]}: rótulo inválido {labels}')
        votes = pd.Series(labels).value_counts()
        winner = votes.index[0] if votes.iloc[0] >= 3 else None  # majority: >= 3 of 5
        row = {'ID': s['ID'], 'Cenário': s['Cenário'], 'Mensagem': s['Mensagem'],
               'human_label': winner, 'system_label': str(s['Emotion label']).lower(),
               'acordo_5_avaliadores': len(set(labels)) == 1, 'votos_rotulo': votes.iloc[0],
               'system_confidence': s['Confidence'], 'system_action': s['Action']}
        for name, col, pred in DIMENSIONS:
            vals = np.array([float(r.loc[i, col]) for r in ratings])
            row[f'human_{name}'] = (vals.mean() - 5) / 4          # SAM 1..9 -> -1..1
            row[f'system_{name}'] = s[pred]
            row[f'absolute_error_{name}'] = abs(row[f'human_{name}'] - row[f'system_{name}'])
            row[f'rater_std_{name}'] = vals.std(ddof=1)            # spread between raters, SAM 1..9
        rows.append(row)
    return pd.DataFrame(rows)


def save_charts(valid, res):
    cm = confusion_matrix(valid.human_label, valid.system_label, labels=CLASSES)
    fig, ax = plt.subplots(figsize=(8, 7))
    ConfusionMatrixDisplay(cm, display_labels=CLASSES).plot(ax=ax, cmap='Blues', colorbar=True)
    ax.set_title('NovaShop - Emotion Confusion Matrix')
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'matriz_confusao.png'), dpi=300)
    plt.close(fig)

    f1 = f1_score(valid.human_label, valid.system_label, labels=CLASSES, average=None, zero_division=0)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(CLASSES, f1)
    ax.set_ylim(0, 1)
    ax.set_ylabel('F1-score')
    ax.set_title('F1-score by Emotion')
    plt.setp(ax.get_xticklabels(), rotation=35)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'f1_por_emocao.png'), dpi=300)
    plt.close(fig)

    names = [n for n, _, _ in DIMENSIONS]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - 0.175, [res[f'human_{n}'].mean() for n in names], 0.35, label='SAM reference')
    ax.bar(x + 0.175, [res[f'system_{n}'].astype(float).mean() for n in names], 0.35, label='NovaShop')
    ax.set_xticks(x)
    ax.set_xticklabels([n.capitalize() for n in names])
    ax.set_ylim(-1, 1)
    ax.set_ylabel('Mean normalized value')
    ax.set_title('Human-Reference vs System VAD')
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, 'comparacao_vad.png'), dpi=300)
    plt.close(fig)


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    system, ratings = load(filename)
    res = build_results(system, ratings)
    valid = res.dropna(subset=['human_label'])
    os.makedirs(OUT_DIR, exist_ok=True)

    lines = ['NOVASHOP | AVALIAÇÃO SAM (exploratória)', f'Mensagens: {len(res)} | Avaliadores: 5',
             f'Concordância total de rótulos (5/5): {res["acordo_5_avaliadores"].mean():.1%}',
             f'Rótulos por maioria (>=3/5): {len(valid)}/{len(res)}']
    sheets = {'Resultados_Detalhados': res}
    if len(valid) > 0:
        cm = pd.DataFrame(confusion_matrix(valid.human_label, valid.system_label, labels=CLASSES),
                          index=CLASSES, columns=CLASSES)
        lines += [f'Accuracy: {accuracy_score(valid.human_label, valid.system_label):.4f}',
                  f'Macro F1 (todas as 7 classes): '
                  f'{f1_score(valid.human_label, valid.system_label, labels=CLASSES, average="macro", zero_division=0):.4f}',
                  '', 'Relatório por classe:',
                  classification_report(valid.human_label, valid.system_label, labels=CLASSES, zero_division=0),
                  'Matriz de confusão (linhas humanas, colunas sistema):', str(cm)]
        sheets['Matriz_Confusao'] = cm
        # Error analysis: messages where the human majority label differs from the system label.
        sheets['Erros'] = valid[valid.human_label != valid.system_label]
        save_charts(valid, res)
    else:
        lines += ['Não foi possível obter rótulos humanos por maioria.']
    for name, _, _ in DIMENSIONS:
        h = res[f'human_{name}'].astype(float)
        s = res[f'system_{name}'].astype(float)
        corr, p = spearmanr(h, s)
        lines += [f'\n{name.upper()}: Spearman rho={corr:.4f}, p={p:.4g}, MAE={mean_absolute_error(h, s):.4f}, '
                  f'desvio padrão médio entre avaliadores (SAM 1-9)={res[f"rater_std_{name}"].mean():.3f}']
    lines += ['\nNota: as 28 mensagens provêm exclusivamente dos 8 cenários originais; '
              'mensagens no mesmo cenário podem estar correlacionadas.',
              'As métricas descrevem este pequeno conjunto, não demonstram generalização. '
              'Correlação não é concordância exata.',
              'SAM Arousal foi comparado com o campo Activity do sistema.']
    report = '\n'.join(lines)

    with open(os.path.join(OUT_DIR, 'resumo_metricas.txt'), 'w', encoding='utf-8') as f:
        f.write(report + '\n')
    with pd.ExcelWriter(os.path.join(OUT_DIR, 'resultados_avaliacao.xlsx')) as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name, index=(name == 'Matriz_Confusao'))
    print(report)
    print(f'\nResultados escritos em {OUT_DIR}')


if __name__ == '__main__':
    main()

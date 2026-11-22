"""Avaliação exploratória do NovaShop: python calcular_metricas_sam.py NovaShop_SAM_5_Avaliadores.xlsx"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix, mean_absolute_error

filename=sys.argv[1] if len(sys.argv)>1 else 'NovaShop_SAM_5_Avaliadores.xlsx'
system=pd.read_excel(filename,sheet_name='Sistema')
ratings=[]
for participant in range(1,6):
    d=pd.read_excel(filename,sheet_name=f'Avaliador_{participant}')
    cols=['SAM Valence (1-9)','SAM Arousal (1-9)','SAM Dominance (1-9)','Rótulo humano']
    incomplete=d[cols].isna().any(axis=1)
    if incomplete.any():
        raise SystemExit(f'Avaliador_{participant}: falta preencher {int(incomplete.sum())} mensagens (linhas Excel {(d.index[incomplete]+2).tolist()}).')
    if not d['ID'].equals(system['ID']):
        raise SystemExit(f'Avaliador_{participant}: IDs não coincidem com o separador Sistema.')
    for col in cols[:3]:
        d[col]=pd.to_numeric(d[col],errors='coerce')
        if d[col].isna().any() or (~d[col].between(1,9)).any() or (d[col]%1 != 0).any():
            raise SystemExit(f'Avaliador_{participant}: valor inválido em {col}. Usa inteiros 1 a 9.')
    ratings.append(d)

classes=['neutral','joy','calm','sadness','fear','anger','frustration']
rows=[]
for i,s in system.iterrows():
    labels=[str(r.loc[i,'Rótulo humano']).strip().lower() for r in ratings]
    if any(label not in classes for label in labels):
        raise SystemExit(f'ID {s["ID"]}: rótulo inválido {labels}')
    votes=pd.Series(labels).value_counts()
    winner=votes.index[0] if votes.iloc[0]>=3 else None
    row={'ID':s['ID'],'Cenário':s['Cenário'],'Mensagem':s['Mensagem'],
         'human_label':winner,'system_label':str(s['Emotion label']).lower(),
         'acordo_5_avaliadores':len(set(labels))==1,'votos_rotulo':votes.iloc[0],
         'system_confidence':s['Confidence'],'system_action':s['Action']}
    for name,col,pred in [('valence','SAM Valence (1-9)','Valence'),('arousal','SAM Arousal (1-9)','Activity'),('dominance','SAM Dominance (1-9)','Dominance')]:
        vals=np.array([float(r.loc[i,col]) for r in ratings]);row[f'human_{name}']=(vals.mean()-5)/4
        row[f'system_{name}']=s[pred]
        row[f'absolute_error_{name}']=abs(row[f'human_{name}']-row[f'system_{name}'])
        row[f'rater_std_{name}']=vals.std(ddof=1)
    rows.append(row)
res=pd.DataFrame(rows)
res.to_csv('resultados_sam_detalhados.csv',index=False,encoding='utf-8-sig')
valid=res.dropna(subset=['human_label'])
lines=['NOVASHOP | AVALIAÇÃO SAM (exploratória)', f'Mensagens: {len(res)} | Avaliadores: 5',
       f'Concordância total de rótulos (5/5): {res["acordo_5_avaliadores"].mean():.1%}',
       f'Rótulos por maioria (>=3/5): {len(valid)}/{len(res)}']
if len(valid)>0:
    lines += [f'Accuracy: {accuracy_score(valid.human_label,valid.system_label):.4f}',
              f'Macro F1 (todas as 7 classes): {f1_score(valid.human_label,valid.system_label,labels=classes,average="macro",zero_division=0):.4f}',
              '', 'Relatório por classe:',classification_report(valid.human_label,valid.system_label,labels=classes,zero_division=0),
              'Matriz de confusão (linhas humanas, colunas sistema):',
              str(pd.DataFrame(confusion_matrix(valid.human_label,valid.system_label,labels=classes),index=classes,columns=classes))]
else:
    lines += ['Não foi possível obter rótulos humanos por maioria.']
for name in ['valence','arousal','dominance']:
    h=res[f'human_{name}'].astype(float);s=res[f'system_{name}'].astype(float)
    corr,p=spearmanr(h,s)
    lines += [f'\n{name.upper()}: Spearman rho={corr:.4f}, p={p:.4g}, MAE={mean_absolute_error(h,s):.4f}, desvio padrão médio entre avaliadores (SAM 1-9)={res[f"rater_std_{name}"].mean():.3f}']
lines += ['\nNota: as 28 mensagens provêm exclusivamente dos 8 cenários originais; mensagens no mesmo cenário podem estar correlacionadas.',
          'As métricas descrevem este pequeno conjunto, não demonstram generalização. Correlação não é concordância exata.',
          'SAM Arousal foi comparado com o campo Activity do sistema.']
report='\n'.join(lines)
print(report)
with open('resultados_sam_resumo.txt','w',encoding='utf-8') as f:f.write(report)
print('\nFicheiros criados: resultados_sam_detalhados.csv e resultados_sam_resumo.txt')

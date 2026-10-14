"""Render saved development experiments as standalone PNG and SVG plots."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from rag.cache import file_hash

RESULTS = Path(__file__).resolve().parents[1] / 'data/results'
OUTPUT = RESULTS / 'plots'
COLORS = ['#2458A6', '#00856A', '#B36A00', '#A54878', '#6E6E6E', '#7351A3']
LABELS = {
    'e5_small_v2': 'E5-small-v2', 'e5_base_v2': 'E5-base-v2', 'bge_small_en_v1_5': 'BGE-small-en-v1.5',
    'baseline_512_overlap_title': '512 / overlap / titles',
    '256_overlap_title': '256 / overlap / titles', '512_no_overlap_title': '512 / no overlap / titles',
    '512_overlap_no_title': '512 / overlap / no titles',
    'bge_512_overlap_title': '512 / overlap / titles', 'bge_256_overlap_title': '256 / overlap / titles',
    'bge_512_no_overlap_title': '512 / no overlap / titles', 'bge_512_overlap_no_title': '512 / overlap / no titles',
    'original_fixed_chunks_reference': 'Original fixed chunks (reference)',
    'fixed_k10': 'Fixed k=10', 'fixed_k5_control': 'Fixed k=5',
    'paper_style_document_adaptive': 'Gap rule + buffer 5',
    'bounded_adaptive_cap5': 'Bounded / buffer 1', 'bounded_cap5_buffer2': 'Bounded / buffer 2',
    'bounded_cap5_buffer3': 'Bounded / buffer 3',
}
SOURCES = ['scifact_development/summary.csv', 'scifact_models/summary.csv',
           'scifact_bge_chunking/summary.csv', 'scifact_adaptive/summary.csv',
           'scifact_adaptive/per_query_metrics.csv']


def read_csv(relative):
    with (RESULTS / relative).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def save(fig, name):
    for suffix in ['png', 'svg']:
        fig.savefig(OUTPUT / f'{name}.{suffix}', dpi=180, facecolor='white', bbox_inches='tight')
    plt.close(fig)


def style_axis(ax, ylabel, maximum):
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, maximum)
    ax.grid(axis='y', color='#E4E7EB', linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)


def metric_curves(rows, variants, title, filename):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout='constrained')
    fig.suptitle(title + '\n809 development queries · exact document retrieval', fontsize=15, fontweight='bold')
    for ax, metric, label, scale, maximum in zip(axes, ['precision','recall','mrr'],
            ['Precision (%)','Recall (%)','MRR'], [100,100,1], [100,100,1]):
        for index, variant in enumerate(variants):
            group = sorted([r for r in rows if r['variant']==variant], key=lambda r:int(r['k']))
            if [int(r['k']) for r in group] != [1,3,5,10,20]: raise ValueError('Incomplete k sweep')
            ax.plot([int(r['k']) for r in group], [float(r[metric])*scale for r in group],
                    marker='o', markersize=4, color=COLORS[index], label=LABELS[variant],
                    linestyle='--' if 'reference' in variant else '-')
        style_axis(ax,label,maximum)
        ax.set_xlabel('Retrieved unique documents (k)')
        ax.set_xticks([1,3,5,10,20])
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=2,frameon=False,fontsize=9)
    save(fig,filename)


def bars(ax, labels, values, ylabel, maximum, colors=None):
    bars = ax.barh(np.arange(len(labels)),values,color=colors or COLORS[:len(labels)],height=.65)
    ax.set_yticks(np.arange(len(labels)),labels)
    ax.invert_yaxis()
    ax.set_xlim(0,maximum)
    ax.set_xlabel(ylabel)
    ax.grid(axis='x',color='#E4E7EB',linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[['top','right']].set_visible(False)
    for bar,value in zip(bars,values):
        ax.text(value+.7 if maximum==100 else value+.006,bar.get_y()+bar.get_height()/2,
                f'{value:.2f}' if maximum==100 else f'{value:.3f}',va='center',fontsize=9)


def adaptive_plots(rows, details):
    order=['fixed_k10','paper_style_document_adaptive','bounded_adaptive_cap5',
           'bounded_cap5_buffer2','bounded_cap5_buffer3','fixed_k5_control']
    ordered=[next(r for r in rows if r['method']==name) for name in order]
    labels=[LABELS[name] for name in order]
    fig,axes=plt.subplots(1,3,figsize=(17,5),layout='constrained')
    fig.suptitle('Fixed vs adaptive document selection\n809 development queries · precision uses actual selected count',fontsize=15,fontweight='bold')
    for ax,metric,label,scale,maximum in zip(axes,['precision','recall','mrr'],
                                            ['Precision (%)','Recall (%)','MRR'],[100,100,1],[100,100,1]):
        bars(ax,labels,[float(r[metric])*scale for r in ordered],label,maximum)
    save(fig,'04_adaptive_metrics')
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    fig.suptitle('Evidence retained vs retrieval recall',fontsize=15,fontweight='bold')
    for ax,xfield,xlabel in zip(axes,['mean_selected','mean_estimated_context_tokens'],
                               ['Mean selected documents','Mean estimated passage tokens (BGE tokenizer)']):
        for i,r in enumerate(ordered):
            x=float(r[xfield]); y=float(r['recall'])*100
            ax.scatter(x,y,color=COLORS[i],s=65,label=labels[i])
        style_axis(ax,'Recall (%)',100)
        ax.set_xlabel(xlabel)
        ax.set_xlim(left=0)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='outside lower center',ncol=3,frameon=False,fontsize=9)
    save(fig,'05_adaptive_context_tradeoff')
    fig,axes=plt.subplots(1,2,figsize=(15,6),layout='constrained')
    fig.suptitle('Adaptive selection varies across queries\nBoxes show quartiles, dots show outliers, triangles show means',fontsize=15,fontweight='bold')
    for ax,field,label in zip(axes,['selected_count','estimated_context_tokens'],
                             ['Selected documents','Estimated passage tokens (BGE tokenizer)']):
        data=[[float(r[field]) for r in details if r['method']==name] for name in order]
        if any(len(group)!=809 for group in data): raise ValueError('Missing per-query data')
        boxes=ax.boxplot(data,showmeans=True,patch_artist=True,widths=.5,
                         flierprops={'markersize':3,'alpha':.35})
        for patch,color in zip(boxes['boxes'],COLORS): patch.set_facecolor(color); patch.set_alpha(.4)
        ax.set_xticks(range(1,7),[label.replace(' / ','\n') for label in labels],rotation=20,ha='right',fontsize=9)
        ax.set_ylabel(label); ax.set_ylim(bottom=0); ax.grid(axis='y',alpha=.2)
        ax.spines[['top','right']].set_visible(False)
    save(fig,'06_adaptive_distributions')



def chunk_cost_plot(e5,bge):
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    fig.suptitle('Chunking changes storage and embedding work',fontsize=15,fontweight='bold')
    for ax,rows,variants,title in [
        (axes[0],e5,['baseline_512_overlap_title','256_overlap_title','512_no_overlap_title','512_overlap_no_title'],'E5-small'),
        (axes[1],bge,['bge_512_overlap_title','bge_256_overlap_title','bge_512_no_overlap_title','bge_512_overlap_no_title'],'BGE-small')]:
        group=[next(r for r in rows if r['variant']==v and int(r['k'])==5) for v in variants]
        values=[int(r['chunk_count']) for r in group]
        rects=ax.bar(range(4),values,color=COLORS[:4])
        ax.set_xticks(range(4),['512\noverlap + titles','256\noverlap + titles','512\nno overlap + titles','512\noverlap, no titles'],fontsize=9)
        ax.set_ylim(0,max(values)*1.16)
        ax.set_ylabel('Searchable chunks')
        ax.set_title(title,fontweight='bold')
        ax.grid(axis='y',alpha=.2); ax.set_axisbelow(True)
        ax.spines[['top','right']].set_visible(False)
        for rect,value in zip(rects,values):
            ax.text(rect.get_x()+rect.get_width()/2,value+100,f'{value:,}',ha='center',fontsize=10)
    save(fig,'07_chunk_counts')


def overview(models,e5,bge,adaptive):
    fig,axes=plt.subplots(2,2,figsize=(16,10),layout='constrained')
    fig.suptitle('SciFact retrieval experiments — development results\n809 queries · held-out test results are not included',fontsize=18,fontweight='bold')
    panels=[(models,['e5_small_v2','e5_base_v2','bge_small_en_v1_5'],'Embedding models — Recall@5'),
            (e5,['baseline_512_overlap_title','256_overlap_title','512_no_overlap_title','512_overlap_no_title'],'E5-small chunking — Recall@5'),
            (bge,['bge_512_overlap_title','bge_256_overlap_title','bge_512_no_overlap_title','bge_512_overlap_no_title'],'BGE-small chunking — Recall@5')]
    for ax,(rows,variants,title) in zip(axes.flat,panels):
        group=[next(r for r in rows if r['variant']==v and int(r['k'])==5) for v in variants]
        bars(ax,[LABELS[v] for v in variants],[float(r['recall'])*100 for r in group],'Recall (%)',100)
        ax.set_title(title,fontsize=12,fontweight='bold')
    names=['fixed_k10','paper_style_document_adaptive','bounded_adaptive_cap5',
           'bounded_cap5_buffer2','bounded_cap5_buffer3','fixed_k5_control']
    group=[next(r for r in adaptive if r['method']==v) for v in names]
    ax=axes[1,1]
    bars(ax,[LABELS[v] for v in names],[float(r['recall'])*100 for r in group],'Recall (%)',100)
    ax.set_title('Adaptive selection — Recall at selected count',fontsize=12,fontweight='bold')
    save(fig,'00_overview')


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
    e5,models,bge,adaptive,details=[read_csv(path) for path in SOURCES]
    for rows in [e5,models,bge,adaptive]:
        if any(int(r['query_count'])!=809 for r in rows): raise ValueError('Unexpected evaluation scope')
        for row in rows:
            if any(not 0<=float(row[m])<=1 for m in ['precision','recall','mrr']): raise ValueError('Invalid metric')
    overview(models,e5,bge,adaptive)
    metric_curves(models,['e5_small_v2','e5_base_v2','bge_small_en_v1_5'],'Embedding model comparison','01_embedding_models_vs_k')
    metric_curves(e5,['baseline_512_overlap_title','256_overlap_title','512_no_overlap_title','512_overlap_no_title'],
                  'E5-small chunking comparison','02_e5_chunking_vs_k')
    metric_curves(bge,['bge_512_overlap_title','bge_256_overlap_title','bge_512_no_overlap_title',
                     'bge_512_overlap_no_title','original_fixed_chunks_reference'],'BGE-small chunking comparison','03_bge_chunking_vs_k')
    adaptive_plots(adaptive,details)
    chunk_cost_plot(e5,bge)
    manifest={'sources':{path:file_hash(RESULTS/path) for path in SOURCES},
              'plot_script_sha256':file_hash(Path(__file__)),
              'query_count':809,'split':'development (train labels)',
              'artifacts':[path.name for path in sorted(OUTPUT.iterdir()) if path.suffix in ['.png','.svg']]}
    (OUTPUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
    names=['00_overview','01_embedding_models_vs_k','02_e5_chunking_vs_k','03_bge_chunking_vs_k',
           '04_adaptive_metrics','05_adaptive_context_tradeoff','06_adaptive_distributions','07_chunk_counts']
    text=['# Retrieval experiment plots','','All plots use saved measurements from the same 809 development queries. No new evaluation or model calls were made. PNG is for viewing; SVG is scalable and editable.','']
    for name in names: text += [f'## {name.replace("_"," ")}', '',f'![{name}]({name}.png)','']
    text += ['Precision and recall are percentages; MRR is a score from 0 to 1. Metric axes start at zero. The three k-sweep plots include all five k values. Adaptive precision uses actual selected count, unlike fixed Precision@k. The adaptive token plots use BGE-token estimates including special tokens, not actual generation-model token counts. The distribution plot retains outliers, including the paper-style maximum of 37 documents. BGE native chunking and original fixed-chunk reference are distinguished. Titles/overlap and k can change retrieval evidence volume; none of these plots establishes generated-draft factuality or held-out performance.','', 'Rebuild: `python -m rag.examples.plot_retrieval_results`. Source CSV hashes are recorded in manifest.json.']
    (OUTPUT/'README.md').write_text('\n'.join(text)+'\n')
    print(f'Saved {len(names)} plots as PNG and SVG to {OUTPUT}')

if __name__=='__main__': main()

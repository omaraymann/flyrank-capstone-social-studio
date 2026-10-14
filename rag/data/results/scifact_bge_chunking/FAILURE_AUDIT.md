# Development retrieval failure audit

Configuration: BGE-small-en-v1.5, native 512-token chunks, titles, no overlap, k=10. All 809 query rankings were screened mechanically; the first five no-hit queries in dataset order were manually compared against full corpus abstracts. This is not a representative sample or an expert adjudication of every retrieved document.

## Label-based counts

- 696 queries retrieved all their positive labels in the top 10.
- 14 retrieved only some positive labels.
- 99 retrieved no positive label.
- For 24 of those 99, at least one positive-labelled document appears at ranks 11–20; the remaining 75 have none in the top 20.
- Full data, including top-ten abstracts and positive-labelled documents for all 99 misses, are saved in failure_audit.json. Complete corpus ranks were additionally calculated for the five inspected examples.

## Inspected examples

| Query ID | Request | Labelled document rank | Observation from the abstracts |
|---|---|---:|---|
| 0 | 0-dimensional biomaterials lack inductive properties | 27 | Retrieved papers discuss material properties and cellular effects. The labelled abstract discusses nanotechnologies and stem cells, but does not use the query's exact dimensional wording. Broad-topic retrieval and terminology differences are plausible contributors. |
| 14 | 5'-nucleotidase metabolizes 6MP | 13 | Rank 1 discusses nucleotidase enzyme kinetics but not the named drug. Rank 2 (6421792) discusses NT5C2, chemotherapy-drug inactivation, and resistance to 6-mercaptopurine. It is plausible alternative evidence, although it is unlabelled for this query and not expert-adjudicated here. |
| 15 | 50% of radiation-exposed patients have activated mesenchymal stem-cell markers | 1006 | Retrieved abstracts mention stem-cell/mesenchymal markers but do not establish the requested percentage and radiation condition. The labelled abstract concerns smooth-muscle-cell phenotypes in atherosclerosis and also does not clearly address those particulars. The abstract-level gold match warrants checking against the original annotations; this does not establish a label error. |
| 17 | 53% of perinatal mortality is due to low birth weight | 43 | Rank 1 discusses neonatal mortality and low birth weight but does not establish 53%. The labelled abstract discusses childhood underweight prevalence, with no explicit matching statement. Both specificity and abstract-level label alignment warrant review. |
| 63 | ATM and Rad3-related protein are critical for sensing DNA damage | 53 | Rank 2 (30122260) discusses ATM/ATR and sensing/signalling DNA damage directly. This is a plausible useful unlabelled result. The positive-labelled abstract instead focuses on ATR deletion, ageing and stem-cell loss. |

## Interpreting precision

The downloaded train qrels contain positive score-1 pairs only. A retrieved document absent from these labels is unjudged for this benchmark view; its absence is not a verified negative judgment. A document that refutes a claim can still be relevant evidence. Topical relatedness, evidence usefulness, and support/contradiction are separate judgments.

With 919 positive labels across 809 queries, the maximum average labelled Precision@10 is 919/(809*10), about 11.36%, assuming all positives are retrieved. Our measured 9.89% means approximately one labelled positive per top-ten list, not proof that the remaining nine are useless. Similarity scores are not calibrated relevance probabilities.

For a supplementary graded audit, use: 0 unrelated; 1 same broad topic without useful evidence; 2 partly useful evidence but missing an important entity/condition/number; 3 evidence addressing the exact claim, whether supporting or refuting it. Have humans adjudicate a sampled set, with an optional model proposing judgments and excerpts for review. Record uncertainty and disagreement. Keep official qrels unchanged, and report graded judgments separately. Graded relevance permits nDCG; a four-level score is an ordinal rating, not a percentage of relevance.

Next development actions: inspect query-specific missing entities/numbers and gold matches, then compare hybrid retrieval or reranking only if those failure patterns justify them. A k=20 increase rescues 24 label-based no-hit cases, but adds retrieval/context volume and does not fix the remaining failures. No held-out labels were read or changed.

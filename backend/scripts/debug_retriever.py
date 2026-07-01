from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent
sys.path.insert(0, str(BACKEND))
from app.config import get_settings
from app.catalog.loader import load_catalog
from app.retrieval.hybrid import HybridRetriever

settings = get_settings()
cat = load_catalog(settings.catalog_file)
print('catalog size', len(cat))
ret = HybridRetriever(cat, settings, enable_reranker=False)
print('faiss present:', ret.faiss is not None)
if ret.faiss is not None:
    try:
        print('faiss.ntotal', ret.faiss.index.ntotal)
    except Exception as e:
        print('cannot read ntotal', e)

q = 'java backend 40 min remote'
items, diag = ret.search(type('S', (), {'role':None,'experience':None,'industry':None,'programming_language':[],'technical_skills':[],'assessment_types':[],'leadership':False,'communication':False,'personality':False,'constraints':type('C',(),{'job_levels':[],'duration_max':None,'remote':None,'adaptive':None,'languages':[]})})(), return_diagnostics=True, raw_query=q)
print('returned items count', len(items))

# Inspect dense indices
from app.retrieval.embeddings import encode
qvec = encode([q], settings.embedding_model)[0]
d_scores, d_idx = ret.faiss.search(qvec, 150)
print('max d_idx', max(d_idx.tolist()))
print('min d_idx', min(d_idx.tolist()))
print('some d_idx', d_idx[:20].tolist())

# Check fused ranks
from app.retrieval.bm25 import BM25
bm = BM25(ret.corpus)
bm25_scores = bm.scores(q)
import numpy as np
sparse_ranked = np.argsort(-bm25_scores)[:150].tolist()
print('max sparse', max(sparse_ranked), 'len', len(sparse_ranked))

from app.retrieval.rrf import reciprocal_rank_fusion
fused = reciprocal_rank_fusion([ [int(i) for i in d_idx if i>=0], sparse_ranked ], k=60)
print('max fused key', max(fused.keys()))
print('sample fused keys', list(fused.keys())[:30])

# Verify any fused keys out of range
n = len(cat)
bad = [k for k in fused.keys() if k<0 or k>=n]
print('bad fused keys count', len(bad), bad[:10])

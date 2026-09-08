"""
Hybrid search engine: BM25 (keyword recall) + multilingual sentence embeddings
(semantic/cross-lingual recall for Hinglish paraphrase), fused by weighted
reciprocal rank fusion.

IMPORTANT: The embedding model (paraphrase-multilingual-MiniLM-L12-v2) is
downloaded from Hugging Face on first run and needs internet access. This is
what gives the system the ability to match "vacation spot" -> "Manali fix hai"
with zero shared words -- BM25 alone cannot do this by design, which is why
the eval set exists. If sentence-transformers / the model can't be loaded
(e.g. no internet), the engine falls back to BM25-only and reports degraded
mode explicitly rather than silently pretending to be semantic.
"""
import json
import re
import numpy as np
from datetime import datetime
from rank_bm25 import BM25Okapi

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

from query_classifier import classify

EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def tokenize(text):
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


class SearchEngine:
    def __init__(self, corpus_path):
        with open(corpus_path, encoding="utf-8") as f:
            self.corpus = json.load(f)
        self.by_id = {m["id"]: m for m in self.corpus}
        self.id_list = [m["id"] for m in self.corpus]
        self.timestamps = [datetime.fromisoformat(m["timestamp"]) for m in self.corpus]
        self.reference_date = self.timestamps[-1] + __import__("datetime").timedelta(days=3)

        self._build_bm25()
        self._build_embeddings()
        self._build_thread_map()

    # ------------------------------------------------------------------
    def _build_bm25(self):
        tokenized = [tokenize(m["text"]) for m in self.corpus]
        self.bm25 = BM25Okapi(tokenized)

    def _build_embeddings(self):
        self.embed_mode = "none"
        self.embeddings = None
        if not _ST_AVAILABLE:
            return
        try:
            self.model = SentenceTransformer(EMBED_MODEL_NAME)
            texts = [m["text"] for m in self.corpus]
            self.embeddings = self.model.encode(
                texts, batch_size=64, show_progress_bar=False,
                convert_to_numpy=True, normalize_embeddings=True,
            )
            self.embed_mode = "multilingual-minilm"
        except Exception as e:
            print(f"[engine] Embedding model unavailable ({e}); falling back to BM25-only mode.")
            self.embed_mode = "none"

    def _build_thread_map(self):
        """
        Group messages that belong to a known decision thread using the explicit
        thread_tag set at generation time (reliable), rather than inferring
        connectivity from the sparse/random reply_to links (unreliable: a real
        chat's reply-to graph is not guaranteed to connect a whole conversation).
        """
        self.thread_of = {}
        for m in self.corpus:
            tag = m.get("thread_tag")
            if tag:
                self.thread_of[m["id"]] = tag

    # ------------------------------------------------------------------
    def _bm25_scores(self, query):
        return self.bm25.get_scores(tokenize(query))

    def _embed_scores(self, query):
        if self.embed_mode == "none":
            return None
        q_emb = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)[0]
        return self.embeddings @ q_emb

    def _apply_filters(self, indices, sender, date_range):
        out = []
        for i in indices:
            m = self.corpus[i]
            if sender and m["sender"] != sender:
                continue
            if date_range:
                ts = self.timestamps[i]
                if not (date_range[0] <= ts < date_range[1]):
                    continue
            out.append(i)
        return out

    # ------------------------------------------------------------------
    def search(self, query, top_k=5, context_window=2):
        info = classify(query, self.reference_date)
        sender, date_range = info["sender"], info["date_range"]

        n = len(self.corpus)
        candidate_idx = list(range(n))
        candidate_idx = self._apply_filters(candidate_idx, sender, date_range)
        if not candidate_idx:
            # filters wiped out everything (bad date parse etc.) -- fall back to unfiltered
            candidate_idx = list(range(n))

        bm25_all = self._bm25_scores(query)
        embed_all = self._embed_scores(query)

        # rank within candidates
        bm25_ranked = sorted(candidate_idx, key=lambda i: -bm25_all[i])
        bm25_rank_of = {idx: r for r, idx in enumerate(bm25_ranked)}

        if embed_all is not None:
            embed_ranked = sorted(candidate_idx, key=lambda i: -embed_all[i])
            embed_rank_of = {idx: r for r, idx in enumerate(embed_ranked)}
            # weighted reciprocal rank fusion, favoring semantic for meaning queries
            k = 60
            w_embed, w_bm25 = 0.7, 0.3
            fused = {}
            for idx in candidate_idx:
                s = 0.0
                s += w_embed * (1.0 / (k + embed_rank_of[idx]))
                s += w_bm25 * (1.0 / (k + bm25_rank_of[idx]))
                fused[idx] = s
        else:
            fused = {idx: 1.0 / (60 + bm25_rank_of[idx]) for idx in candidate_idx}

        ranked = sorted(fused.items(), key=lambda x: -x[1])[:top_k]

        results = []
        max_score = ranked[0][1] if ranked else 1.0
        for idx, score in ranked:
            mid = self.id_list[idx]
            results.append({
                "message": self.corpus[idx],
                "score": round(score / max_score, 4),  # normalize to 0-1 for display
                "context": self._get_context(idx, context_window, mid),
            })

        return {
            "query": query,
            "detected_type": info["type"],
            "detected_sender": sender,
            "detected_date_range": [d.isoformat() for d in date_range] if date_range else None,
            "embed_mode": self.embed_mode,
            "results": results,
        }

    def _get_context(self, idx, window, mid):
        # If part of a decision thread, return the whole thread.
        if mid in self.thread_of:
            tid = self.thread_of[mid]
            members = [i for i, m in enumerate(self.corpus) if self.thread_of.get(m["id"]) == tid]
            members.sort()
            return {
                "type": "thread",
                "messages": [self.corpus[i] for i in members],
            }
        # Otherwise, N messages before/after in raw timeline order.
        lo = max(0, idx - window)
        hi = min(len(self.corpus), idx + window + 1)
        return {
            "type": "window",
            "messages": self.corpus[lo:hi],
        }


if __name__ == "__main__":
    eng = SearchEngine("../data/corpus.json")
    print("embed_mode:", eng.embed_mode)
    out = eng.search("when did we decide on Manali", top_k=3)
    print(json.dumps(out, indent=2, ensure_ascii=False)[:1500])

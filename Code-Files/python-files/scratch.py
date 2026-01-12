# *** 1 ***

import re

CJK_RE = re.compile(r'[\u4e00-\u9fff]')
BRACKETS = re.compile(r'\[.*?\]|\(.*?\)')
POS = re.compile(r'^[a-z]+\.', re.IGNORECASE)
DELIMS = re.compile(r'[；;,，/]+')
FULLWIDTH_SPACE = '\u3000'

def gen_candidates(raw):
    s = BRACKETS.sub('', raw)
    s = s.replace(FULLWIDTH_SPACE, ' ')
    s = POS.sub('', s).strip()
    s = DELIMS.sub(',', s)
    out = []
    for part in s.split(','):
        tok = part.strip()
        if not tok:
            continue
        if not CJK_RE.search(tok):
            continue
        punct_ratio = sum(ch in '.,;；，/()[]' for ch in tok) / len(tok)
        if punct_ratio > 0.3 or len(tok) > 30:
            continue
        out.append(tok)
    return out

# *** 2 ***

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

MODEL = "uer/roberta-base-chinese-cluecorpussmall"  # small-ish Chinese encoder
tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL, num_labels=2)

# Fine-tune on a small labeled set of candidates
# train_texts, train_labels = [...]
# ... standard HF Trainer / simple loop ...

def score_tokens(tokens):
    if not tokens: return []
    enc = tokenizer(tokens, padding=True, truncation=True, return_tensors="pt")
    with torch.no_grad():
        logits = model(**enc).logits
    probs = logits.softmax(dim=-1)[:, 1].tolist()  # prob keep
    return list(zip(tokens, probs))


# *** 3 ***

def clean_translation_field(raw):
    cands = gen_candidates(raw)
    scored = score_tokens(cands)  # or skip if you didn’t fine-tune
    kept = [t for t, p in scored if p >= 0.5] if scored else cands
    return kept

"""Pattern per detection runtime della "dichiarazione di limite corpus"
nella risposta del modello.

Copre 4 famiglie lessicali osservate nelle risposte reali (F.2 + subset
dev su Q9, Q35, Q43, Q49):

    1. canonico gold — "non incluso nel corpus (normativo di riferimento)"
    2. naturale modello — "il contesto (normativo/fornito) non contiene/include/riguarda"
    3. negazione assoluta — "assenti/non presenti nel contesto"
    4. meta-richiesta — "sarebbe necessario disporre/fare riferimento/consultare"

Il qualificatore "normativo" o "fornito" nella famiglia 2 è opzionale ma
deve seguire direttamente "contesto" (no parole intermedie): evita falsi
positivi come "il contesto storico non riguarda...".
"""

import re

CORPUS_LIMIT_RE = re.compile(
    r"(?:"
    # Famiglia 1: canonico "non incluso nel corpus"
    r"non\s+(?:è\s+|sono\s+|sia\s+|siano\s+)?(?:inclus[oaie]|present[eai])"
    r".{0,40}corpus(?:\s+normativo)?(?:\s+di\s+riferimento)?"
    r"|"
    # Famiglia 2: "contesto (normativo|fornito)? non contiene/include/riguarda"
    r"contesto\s+(?:normativo\s+)?(?:fornito\s+)?"
    r"non\s+(?:contiene|include|riguarda)"
    r"|"
    # Famiglia 3: "assenti/non presenti nel contesto"
    r"(?:assent[ei]|non\s+present[ei])\s+nel\s+contesto"
    r"|"
    # Famiglia 4: meta-richiesta di norme mancanti
    r"sarebbe\s+necessario\s+(?:disporre|fare\s+riferimento|consultare)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

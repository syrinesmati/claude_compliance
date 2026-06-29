# Prompt v1 → v2 : Changements et Résultats Détaillés

**Date :** 2026-06-29  
**Fichiers :** `compliance_scorer.py` (v1) · `compliance_scorer_v2.py` (v2)  
**Benchmark :** `benchmark.py` (v1) · `benchmark_v2.py` (v2)  

---

## 1. Contexte — Pourquoi un v2 ?

L'analyse du benchmark v1 a révélé que plusieurs modèles (Gemma3-12B, Qwen3-32B) scoraient les documents de **failure** trop haut parce qu'ils ne respectaient pas les plafonds `TYPE_MISMATCH` définis dans le prompt. Ils appliquaient Step 2A (équivalences fonctionnelles) de façon trop large — n'importe quel document avec une approbation RCC et des rôles mentionnés était upgradé en PARTIAL_MATCH ou DIRECT_MATCH.

**Objectif du v2 :** ajouter une section de règles strictes *avant* les équivalences Step 2, pour forcer les modèles à appliquer les plafonds durs avant de chercher des équivalences.

---

## 2. Différence exacte entre v1 et v2

### 2.1 Ce qui n'a PAS changé

Toutes les sections suivantes sont identiques entre v1 et v2 :

- CORE PRINCIPLE
- KEY CONCEPT DISAMBIGUATIONS (Risk Acceptance / Appetite, Charter / Strategy, Policy / Standard, Procedure, Register, Cybersecurity ≠ IT)
- STEP 1 — Translate Requirement & Evidence *(voir note typo ci-dessous)*
- STEP 2 — Functional Equivalence (2A à 2F) : toutes les règles d'équivalence, y compris la règle de pertinence domaine (2E), le KPI = monitoring report (2A), l'audit schedule = PARTIAL_MATCH (2A)
- STEP 3 — Intent Alignment + classification + hard caps
- STEP 4 — Self-Check
- STEP 5, 6, 7 — Micro-requirements, scoring MR, reliability
- Structure JSON de sortie

> **Note typo dans v2 ligne 54 :** suite à une édition dans l'IDE, la ligne contient `"TSAMA-3.1.3-2-L3-1he auditor is asking"` au lieu de `"The auditor is asking"`. Ce texte n'est pas lu par le modèle comme une instruction critique mais peut induire une confusion mineure — à corriger avant usage en production.

---

### 2.2 Ce qui A changé : la nouvelle section STRICT TYPE-MISMATCH RULES

**Position dans le prompt :** ajoutée entre KEY CONCEPT DISAMBIGUATIONS et STEP 1.  
**Instruction d'application :** *"apply these BEFORE any equivalence check"*

**Texte ajouté (v2 uniquement) :**

```
# STRICT TYPE-MISMATCH RULES (apply these BEFORE any equivalence check)

These document types are NEVER functionally equivalent,
regardless of governance language or approvals present:

- An operational process document (e.g. Vulnerability Management Process,
  Incident Response Procedure, Change Management Process) is NOT a Charter,
  NOT an Org Chart, and NOT a Risk Appetite document — even if it is
  RCC-approved and mentions roles. Score as TYPE_MISMATCH, evidence_strength ≤ 35.

- A technical security standard or policy (e.g. Cloud Computing Standard,
  Password Policy, Encryption Standard) is NOT an Org Chart and NOT a Charter
  — even if it names a VP or approving authority.
  Score as TYPE_MISMATCH, evidence_strength ≤ 35.

- A Static Application Security Testing (SAST) tool or architecture is NOT a
  Penetration Test report. SAST = automated code analysis during development.
  Pentest = active external attack simulation.
  Score as TYPE_MISMATCH, evidence_strength ≤ 25.

- An organizational chart is NOT a Risk Appetite document, NOT a Policy, and
  NOT a Risk Register — even if signed by the CEO.
  Score as DOMAIN_MISMATCH or TYPE_MISMATCH, evidence_strength ≤ 15.
```

**Modification de Step 2 (header) :**

| | v1 | v2 |
|---|---|---|
| Header Step 2 | *"apply BEFORE classifying — do NOT over-audit"* | *"apply AFTER confirming no Strict Type-Mismatch rule fires"* |

**Modification de Step 4 (self-check) :**

Ajout d'une étape 0 explicite dans la self-check :

| | v1 | v2 |
|---|---|---|
| Point 1 de Step 4 | "If TYPE_MISMATCH: re-read Step 2A-2F..." | **"Did a Strict Type-Mismatch rule (at the top) fire? If yes, do NOT upgrade to PARTIAL_MATCH because the document has governance language. Apply the hard cap."** puis: "If TYPE_MISMATCH: re-read Step 2A-2F..." |

**Modification de Step 6 (MR scoring) :**

Ajout d'une règle : *"If a Strict Type-Mismatch rule fired for this document, all MRs that require the correct deliverable type must score 0."*

---

## 3. Résultats par modèle

### Légende
- ✅ = PASS (success present=YES **ET** failure present=NO)
- ❌ = FAIL
- ◄ = cas qui a changé entre v1 et v2
- S = success score · F = failure score

---

### 3.1 Qwen3.6-27B-AWQ — v1: 4/6 → v2: 4/6 (─ stable)

| TC | v1 | v2 | Δ S | Δ F |
|----|----|----|-----|-----|
| TC1 Cyber Charter | ✅ 95%/20% | ✅ 90%/10% | −5% | −10% |
| TC2 Org Structure | ✅ 90%/20% | ✅ 95%/0% | +5% | −20% |
| TC3 Policy Review | ✅ 65%/0% | ✅ 75%/0% | +10% | 0% |
| TC4 Risk Appetite | ❌ 55%/0% | ❌ 20%/15% ◄ | −35% | +15% |
| TC5 Pentest | ✅ 92%/0% | ✅ 95%/0% | +3% | 0% |
| TC6 Phys Security | ❌ 55%/60% | ❌ 65%/65% | +10% | +5% |

**Analyse :**
- TC1, TC2, TC5 : amélioration de la discrimination (failure scores plus bas)
- **TC4 régression majeure** : le succès passe de 55% à 20%. Le modèle applique maintenant la règle stricte ("process doc ≠ Risk Appetite") mais **oublie l'EXCEPTION SAMA 3.2.1.x** qui doit upgrader le Jira workflow en PARTIAL_MATCH 50–70%. La règle stricte écrase l'exception.
- TC6 : les deux scores montent légèrement, aucune amélioration nette.

---

### 3.2 Qwen3-30B-MoE-FP8 — v1: 4/6 → v2: 4/6 (─ stable)

| TC | v1 | v2 | Δ S | Δ F |
|----|----|----|-----|-----|
| TC1 Cyber Charter | ✅ 85%/40% | ✅ 75%/35% | −10% | −5% |
| TC2 Org Structure | ✅ 85%/30% | ✅ 85%/15% | 0% | −15% |
| TC3 Policy Review | ❌ 55%/20% | ❌ 35%/15% ◄ | −20% | −5% |
| TC4 Risk Appetite | ✅ 85%/25% | ✅ 65%/15% | −20% | −10% |
| TC5 Pentest | ✅ 75%/35% | ✅ 75%/25% | 0% | −10% |
| TC6 Phys Security | ❌ 50%/50% | ❌ 35%/35% | −15% | −15% |

**Analyse :**
- Failure discrimination globalement améliorée (avg failure 33.3% → 23.3%)
- **TC3 régression** : le succès tombe de 55% à 35% (déjà borderline en v1, maintenant clairement sous le seuil). La règle stricte sur les process docs semble interférer avec l'évaluation des policy documents qui *ont* une version history.
- TC4 : reste PASS mais score success tombe (85%→65%) — la règle stricte rend le modèle plus conservateur sur tout.
- Malgré une meilleure discrimination des failures, les succès sont aussi pénalisés.

---

### 3.3 Gemma4-26B-MoE-AWQ — v1: 5/6 → v2: 4/6 (▼ −1)

| TC | v1 | v2 | Δ S | Δ F |
|----|----|----|-----|-----|
| TC1 Cyber Charter | ✅ 85%/15% | ✅ 85%/15% | 0% | 0% |
| TC2 Org Structure | ✅ 95%/0% | ✅ 90%/0% | −5% | 0% |
| TC3 Policy Review | ✅ 85%/0% | ✅ 90%/0% | +5% | 0% |
| TC4 Risk Appetite | ❌ 45%/0% | ❌ 45%/15% | 0% | +15% |
| TC5 Pentest | ✅ 95%/0% | ✅ 100%/25% | +5% | +25% |
| TC6 Phys Security | ✅ 85%/15% | ❌ 35%/15% ◄ | **−50%** | 0% |

**Analyse :**
- **TC6 régression catastrophique** : le succès chute de 85% à 35%. En v1, Gemma4-26B était le seul modèle à passer TC6 grâce à une application correcte de la règle Step 2A (audit schedule + KPI = monitoring report). En v2, la nouvelle règle stricte s'applique en premier et bloque tout : le Vulnerability Management Process dans le package succès est classifié comme "operational process document → TYPE_MISMATCH", ce qui tire le score du package global vers le bas.
- **Root cause** : la règle stricte est trop large — elle s'applique à n'importe quel document du package, pas seulement au document principal. Un package multi-fichiers doit être évalué collectivement (Step 2E), pas document par document avec blocage strict.
- TC5 : failure monte à 25% (le SAST diagram, qui était à 0%, remonte légèrement — Gemma4-26B applique malgré tout une légère équivalence).

---

### 3.4 Qwen3.5-9B-BF16 — v1: 5/6 → v2: 5/6 (─ stable)

| TC | v1 | v2 | Δ S | Δ F |
|----|----|----|-----|-----|
| TC1 Cyber Charter | ✅ 60%/0% | ✅ 90%/35% ◄ | +30% | +35% |
| TC2 Org Structure | ✅ 95%/0% | ✅ 95%/15% | 0% | +15% |
| TC3 Policy Review | ✅ 95%/0% | ✅ 85%/15% | −10% | +15% |
| TC4 Risk Appetite | ✅ 60%/0% | ✅ 70%/15% | +10% | +15% |
| TC5 Pentest | ✅ 95%/0% | ✅ 100%/25% | +5% | +25% |
| TC6 Phys Security | ❌ 20%/25% | ❌ 45%/30% ◄ | +25% | +5% |

**Analyse :**
- Pass count stable mais **les failure scores montent presque partout** (+15 à +35%). Le modèle répond aux nouvelles règles de façon contre-intuitive : il est plus confiant sur les succès (+30% sur TC1) mais aussi plus généreux sur les failures (+35% sur TC1).
- TC1 succès : v1 scorait la Strategy trop bas (60%) par excès de prudence. V2 corrige cela (+30%), mais l'effet "strict rules" hausse aussi le failure.
- TC4 : exception SAMA 3.2.1.x bien appliquée (70%, PARTIAL_MATCH, dans la bonne fourchette 50–70%).
- TC6 : succès de 20%→45%, progrès mais toujours en dessous du seuil 60%.
- **Effet net** : le v2 améliore les scores de succès mais dégrade légèrement la discrimination des failures pour ce modèle — l'avg failure passe de 4.2% à 22.5%.

---

### 3.5 Qwen3-32B-AWQ — v1: 4/6 → v2: **6/6** (▲ +2) ⭐

| TC | v1 | v2 | Δ S | Δ F |
|----|----|----|-----|-----|
| TC1 Cyber Charter | ❌ 95%/70% | ✅ 90%/35% ◄ | −5% | **−35%** |
| TC2 Org Structure | ✅ 95%/0% | ✅ 95%/35% | 0% | +35% |
| TC3 Policy Review | ✅ 85%/0% | ✅ 85%/15% | 0% | +15% |
| TC4 Risk Appetite | ✅ 80%/0% | ✅ 70%/15% | −10% | +15% |
| TC5 Pentest | ✅ 90%/15% | ✅ 95%/25% | +5% | +10% |
| TC6 Phys Security | ❌ 85%/70% | ✅ 85%/50% ◄ | 0% | **−20%** |

**Analyse :**
- **Grand gagnant du v2.** C'est le modèle qui bénéficiait le plus de règles strictes car il était systématiquement trop généreux sur les failures.
- **TC1** : la failure (Vulnerability Management Process) passe de 70% → 35%. La règle "operational process doc ≠ Charter" est appliquée correctement, cap à 35%.
- **TC6** : la failure (audit schedule + org chart) passe de 70% → 50%, juste sous le seuil de 60%. Le modèle applique correctement "audit schedule seul sans metrics = PARTIAL_MATCH plafonné", ce qui ne suffit pas pour dépasser le seuil.
- **TC2, TC3 : failures remontent** (+35%, +15%) — effet secondaire, le modèle reste généreux sur les non-matches évidents. Le Cloud Computing Standard monte à 35% (au lieu de 0%) mais reste sous le seuil.
- **TC4** : exception appliquée (70%, PARTIAL_MATCH), correct.

---

### 3.6 Gemma3-12B-BF16 — v1: 1/6 → v2: 2/6 (▲ +1)

| TC | v1 | v2 | Δ S | Δ F |
|----|----|----|-----|-----|
| TC1 Cyber Charter | ❌ 85%/95% | ❌ 85%/85% | 0% | −10% |
| TC2 Org Structure | ❌ 95%/85% | ❌ 95%/75% | 0% | −10% |
| TC3 Policy Review | ✅ 85%/40% | ✅ 75%/35% | −10% | −5% |
| TC4 Risk Appetite | ❌ 85%/60% | ✅ 90%/15% ◄ | +5% | **−45%** |
| TC5 Pentest | ❌ 85%/85% | ❌ 85%/65% | 0% | −20% |
| TC6 Phys Security | ❌ 95%/85% | ❌ 85%/85% | −10% | 0% |

**Analyse :**
- **TC4** : la seule vraie correction. La failure (org chart pour Risk Appetite) chute de 60% → 15%. La règle "org chart ≠ Risk Appetite" est bien appliquée, et l'exception SAMA 3.2.1.x fait monter le succès à 90%.
- **TC1, TC2, TC5** : failures encore trop hautes (75–85%). Le Vulnerability Management Process est encore scoré 85% comme Charter (TC1), et le SAST diagram 65% comme pentest (TC5). Pour ce modèle 12B, les règles strictes ne suffisent pas — il les lit mais les ignore en faveur de sa heuristique "tout document avec gouvernance RCC = score haut".
- **TC6** : aucune amélioration — les deux scores restent à 85%.
- **Conclusion** : le v2 aide marginalement Gemma3-12B mais le problème fondamental (capacité insuffisante à suivre les instructions conditionnelles) reste entier.

---

## 4. Tableau récapitulatif global

### 4.1 Pass count v1 → v2

| Modèle | v1 | v2 | Δ |
|--------|:--:|:--:|:-:|
| Qwen3-32B-AWQ | 4/6 | **6/6** | ▲ +2 |
| Gemma3-12B-BF16 | 1/6 | 2/6 | ▲ +1 |
| Qwen3.6-27B-AWQ | 4/6 | 4/6 | ─ |
| Qwen3-30B-MoE-FP8 | 4/6 | 4/6 | ─ |
| Qwen3.5-9B-BF16 | 5/6 | 5/6 | ─ |
| Gemma4-26B-MoE-AWQ | 5/6 | 4/6 | ▼ −1 |
| **TOTAL** | **23/36** | **25/36** | **+2** |

### 4.2 Average failure score v1 → v2 (plus bas = meilleur)

| Modèle | v1 Avg F | v2 Avg F | Δ |
|--------|:--------:|:--------:|:-:|
| Gemma4-26B-MoE-AWQ | 5.0% | 11.7% | +6.7% ↑ pire |
| Qwen3.5-9B-BF16 | 4.2% | 22.5% | +18.3% ↑ pire |
| Qwen3.6-27B-AWQ | 16.7% | 15.0% | −1.7% ↓ mieux |
| Qwen3-30B-MoE-FP8 | 33.3% | 23.3% | −10.0% ↓ mieux |
| Qwen3-32B-AWQ | 25.8% | 29.2% | +3.4% ↑ légèrement pire |
| Gemma3-12B-BF16 | 75.0% | 60.0% | −15.0% ↓ mieux |

### 4.3 Scores par test case (toutes v2)

| TC | 27B-AWQ | 30B-MoE | 26B-MoE | 9B-BF16 | 32B-AWQ | 12B-BF16 |
|----|:-------:|:-------:|:-------:|:-------:|:-------:|:--------:|
| TC1 Charter | ✅ 90/10 | ✅ 75/35 | ✅ 85/15 | ✅ 90/35 | ✅ 90/35 | ❌ 85/85 |
| TC2 Org | ✅ 95/0 | ✅ 85/15 | ✅ 90/0 | ✅ 95/15 | ✅ 95/35 | ❌ 95/75 |
| TC3 Policy | ✅ 75/0 | ❌ 35/15 | ✅ 90/0 | ✅ 85/15 | ✅ 85/15 | ✅ 75/35 |
| TC4 Risk | ❌ 20/15 | ✅ 65/15 | ❌ 45/15 | ✅ 70/15 | ✅ 70/15 | ✅ 90/15 |
| TC5 Pentest | ✅ 95/0 | ✅ 75/25 | ✅ 100/25 | ✅ 100/25 | ✅ 95/25 | ❌ 85/65 |
| TC6 Phys | ❌ 65/65 | ❌ 35/35 | ❌ 35/15 | ❌ 45/30 | ✅ 85/50 | ❌ 85/85 |
| **PASS** | **4/6** | **4/6** | **4/6** | **5/6** | **6/6** | **2/6** |

---

## 5. Analyse des effets par règle ajoutée

### Règle 1 : Process doc ≠ Charter / Org Chart / Risk Appetite (cap ≤ 35%)

| Cas ciblé | Modèle | Effet |
|-----------|--------|-------|
| TC1 failure : VMP scoré comme Charter | Qwen3-32B | ✅ 70% → 35% (−35%) |
| TC1 failure : VMP scoré comme Charter | Qwen3.6-27B | ✅ 20% → 10% (−10%) |
| TC1 failure : VMP scoré comme Charter | Gemma3-12B | ❌ 95% → 85% (−10%, toujours trop haut) |
| TC4 success : Jira workflow scoré trop bas | Qwen3.6-27B | ❌ 55% → **20%** (régression — exception ignorée) |

**Verdict :** efficace sur les grands modèles (32B, 27B), insuffisant sur Gemma3-12B, contre-productif sur le TC4 succès quand l'exception SAMA 3.2.1.x n'est pas appliquée.

### Règle 2 : Technical standard ≠ Org Chart (cap ≤ 35%)

| Cas ciblé | Modèle | Effet |
|-----------|--------|-------|
| TC2 failure : Cloud Standard scoré comme Org | Qwen3-30B | ✅ 30% → 15% |
| TC2 failure : Cloud Standard scoré comme Org | Gemma3-12B | ❌ 85% → 75% (toujours trop haut) |
| TC2 failure : Cloud Standard scoré comme Org | Qwen3-32B | ❌ 0% → **35%** (régression légère) |

**Verdict :** aide modérément les modèles moyens, régression mineure sur Qwen3-32B (qui scorait déjà 0%).

### Règle 3 : SAST ≠ Pentest (cap ≤ 25%)

| Cas ciblé | Modèle | Effet |
|-----------|--------|-------|
| TC5 failure : SAST diagram | Gemma3-12B | ❌ 85% → 65% (progrès, toujours au-dessus du seuil) |
| TC5 failure : SAST diagram | Qwen3.5-9B | + (déjà à 0% en v1, monte à 25% en v2 — régression) |

**Verdict :** effet limité. Les modèles qui scoraient déjà correctement (27B, 30B, 9B à 0%) ont tendance à monter légèrement.

### Règle 4 : Org chart ≠ Risk Appetite (cap ≤ 15%)

| Cas ciblé | Modèle | Effet |
|-----------|--------|-------|
| TC4 failure : org chart pour Risk Appetite | Gemma3-12B | ✅ 60% → **15%** (−45%, correction majeure) |
| TC4 failure | Tous les autres | Déjà à 0–25% en v1, légère hausse en v2 (0→15%) |

**Verdict :** très efficace pour Gemma3-12B (le seul à avoir fait cette erreur), sans impact notable sur les autres.

---

## 6. Problèmes identifiés dans v2

### Problème 1 — La règle stricte interfère avec les packages multi-fichiers (TC6)

**Modèle affecté :** Gemma4-26B-MoE-AWQ (régression 85%→35%)

En v1, Gemma4-26B évaluait le package succès TC6 collectivement (Step 2E) : audit schedule + KPI = monitoring report → DIRECT_MATCH. En v2, la règle stricte s'applique au Vulnerability Management Process (3ème doc du package) et tire le score global vers le bas. Le modèle ne distingue pas "cette règle s'applique à un doc isolé" vs "ce package contient un doc de type process mais les autres compensent".

**Fix suggéré :** Ajouter dans les règles strictes : *"Ces règles s'appliquent à un document isolé évalué seul. Dans un package multi-fichiers (Step 2E), un seul document de type mismatch ne disqualifie pas le package — évaluez la contribution nette des documents pertinents."*

### Problème 2 — La règle stricte écrase l'exception SAMA 3.2.1.x (TC4)

**Modèle affecté :** Qwen3.6-27B-AWQ (55%→20%)

La règle "process doc ≠ Risk Appetite" est appliquée avant que l'exception `EXCEPTION for SAMA risk-acceptance controls (domain 3.2.1.x)` soit lue. Le modèle bloque en haut et ne continue pas la lecture.

**Fix suggéré :** Déplacer l'exception SAMA 3.2.1.x *dans* les règles strictes comme cas d'exemption explicite, ou ajouter une note : *"Exception : voir KEY CONCEPT DISAMBIGUATIONS section Risk Acceptance pour les contrôles SAMA 3.2.1.x."*

### Problème 3 — Typo ligne 54

`"TSAMA-3.1.3-2-L3-1he auditor is asking: ______?"` → corriger en `"The auditor is asking: ______?"`.

### Problème 4 — Effet pervers sur Qwen3.5-9B (failure scores montent)

Pour Qwen3.5-9B, le v2 améliore les success scores mais hausse aussi les failure scores (+15 à +35%). Les nouvelles règles semblent "autoriser" des scores plus hauts en général. L'avg failure passe de 4.2% à 22.5%, ce qui dégrade la discrimination même si le pass count reste stable.

---

## 7. Recommandations pour v3

Sur la base des résultats v1 et v2 :

1. **Conserver les règles strictes** — elles sont utiles pour Qwen3-32B et Gemma3-12B.

2. **Ajouter une exemption explicite multi-fichiers** dans les règles strictes pour ne pas pénaliser les packages TC6.

3. **Remonter l'exception SAMA 3.2.1.x dans les règles strictes** comme note d'exception sur la règle "process doc ≠ Risk Appetite".

4. **Ajouter un exemple concret pour TC6** dans Step 2E : *"Exemple : un package contenant [audit schedule Physical Security + KPI physical access reviews] = DIRECT_MATCH pour évaluation d'efficacité physique, même si un troisième doc (Vuln Mgmt Process) est hors domaine et ne compte pas."*

5. **Corriger le typo ligne 54** avant de passer en production.

6. **Modèles recommandés pour production :**
   - `Qwen3-32B-AWQ` avec v2 → **6/6** (meilleur résultat observé)
   - `Qwen3.5-9B-BF16` avec v1 → **5/6** + avg failure 4.2% (meilleure discrimination)
   - `Gemma4-26B-MoE-AWQ` avec v1 → **5/6** + avg failure 5.0% (meilleure discrimination sur TC6)

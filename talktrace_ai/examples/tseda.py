"""Built-in T-SEDA codebook template.

Based on the **T-SEDA** dialogue coding scheme (T-SEDA Collective 2023,
*Toolkit for Systematic Educational Dialogue Analysis*, v.9, University of
Cambridge, https://camtree.learnworlds.com/t-seda — released under a Creative
Commons Attribution licence, CC BY). Definitions and keyword lists follow the
official German edition's detailed coding frame ("Detaillierter
Kodierungsrahmen", pack slides 33–38), deliberately kept SHORT: definition +
official keywords + a one-sentence distinction per code. LLM coders latch
onto concise, contrastive entries better than onto prose — and the human
reviewer stays the judge.

Two documented deviations from the detail slides (both resolved this way in
the project's methodological reference, matching the main coding sheet and
the English original):
- Abbreviation ``EN`` (not ``NE``) for "Ermutigen zum Nachdenken und
  Erklären" — consistent with the sibling prefix ``EI``.
- ``R`` covers ONLY the metacognitive reflection of dialogue/activity; the
  "make the learning trajectory explicit via outside references" clause
  belongs to ``V`` (as in the English original: RD vs. C).

Two project-specific sharpenings beyond the official slides:

1. **Speaker typicality** (the slides are speaker-neutral): ``EI/EN/ZK/L``
   (EN: ``IB/IR/CA/G``) carry a note that they are TEACHER moves in
   whole-class talk, assignable to student turns only in teacher-less
   peer/group settings. Finding from trial run 5: models assigned
   invite/guide codes to plain student turns in a teacher-led discussion.
2. **``EN``/``IR`` narrowed to eliciting a JUSTIFICATION**, and its keyword
   "Kannst du das genauer erklären?" / "Can you explain that in more
   detail?" replaced by justification-seeking wording. Rationale (trial run
   7): that keyword is functionally a request for *clarification*, which the
   scheme already covers under ``EI``/``IB`` ("ausbauen, umformulieren,
   klären"); it pulled student comprehension questions into ``EN``. Such
   questions are now coded by their dialogic function (``I``/``H``/``N``),
   and organisational questions about the task stay uncoded. This follows
   the English original's own contrast: *invite reasoning* vs. *invite to
   build on ideas*.

Language handling differs from ``DEMO_CODEBOOK``: the demo keeps the German
abbreviations in both languages (they label the same demo data), while this
template uses the **official abbreviations of each language version** —
German pack v9: ``I, EI, H, N, EN, ZK, R, V, L, ÄN``; English original:
``B, IB, CH, R, IR, CA, RD, C, G, E``. ⚠️ The letters collide across
languages: German ``R`` = Reflexion (engl. ``RD``), while English ``R`` =
make reasoning explicit (dt. ``N``). Codes are per-language identifiers here,
never translated UI strings.

Entry order follows the official detail slides and doubles as the
single-coding fallback hierarchy (codebook position = priority, see
``utils/codebook_hierarchy``): the catch-all (``ÄN``/``E``) is deliberately
last.

The dict shape (``Code``/``Bezeichnung``/``Beschreibung`` resp.
``Code``/``Label``/``Description``) matches exactly what a DOCX-table
codebook import produces, so the template flows through the entire pipeline
(preview, prompt, enum schema, hierarchy) like an uploaded codebook.
"""


TSEDA_ATTRIBUTION = (
    "T-SEDA Collective (2023). Toolkit for Systematic Educational Dialogue "
    "Analysis (T-SEDA). v.9. University of Cambridge. CC BY."
)

# Pre-sets applied when the template is loaded. T-SEDA codes dialogic moves
# of ALL participants — dialogue quality is co-constructed, and a teacher
# move (e.g. an invitation to reason) is only interpretable against the
# student turns around it. Both speaker groups are therefore ON by default
# (changed 2026-07: was teacher-only in the first template revision).
# T-SEDA is a multi-code scheme (up to two codes per turn).
TSEDA_PRESETS = {
    "llm_switch": True,
    "analyse_teacher_switch": True,
    "analyse_students_switch": True,
    "multi_coding_switch": True,
}


TSEDA_CODEBOOK = {
    "de": [
        {"Code": "I", "Bezeichnung": "Auf Ideen aufbauen",
         "Beschreibung": (
             "Eigene oder fremde Ideen aus vorangegangenen Beiträgen "
             "ausbauen, erläutern, klären oder kommentieren. "
             "Schlüsselwörter: „es ist auch“, „das gibt mir zu denken“, "
             "„ich meine“, „sie meinte“, „anknüpfend an“. "
             "Abgrenzung: explizite Begründung → N; mehrere Beiträge "
             "zusammenführen → ZK."
         )},
        {"Code": "EI", "Bezeichnung": "Ermutigen, auf Ideen aufzubauen",
         "Beschreibung": (
             "Andere auffordern, auf eigenen oder fremden Ideen aufzubauen, "
             "sie auszuarbeiten, umzuformulieren, zu klären oder zu "
             "kommentieren. "
             "Schlüsselwörter: „Was?“, „Sag mir“, „Kannst du das "
             "umformulieren?“, „Meinst du, dass …?“, „Stimmst du zu?“, "
             "„Kannst du ergänzen …?“. "
             "Abgrenzung: lädt zum Begründen ein → EN. Organisatorische "
             "Fragen zum Arbeitsauftrag sind keine dialogischen Züge und "
             "bleiben uncodiert. "
             "Im Klassengespräch ein Zug der LEHRKRAFT — bei Schüler:innen "
             "nur plausibel, wenn keine Lehrkraft am Gespräch beteiligt ist "
             "(z. B. Gruppenarbeit)."
         )},
        {"Code": "H", "Bezeichnung": "Herausfordern",
         "Beschreibung": (
             "Eine Idee in Frage stellen, anzweifeln, prüfen, ihr nicht "
             "zustimmen oder sie herausfordern. "
             "Schlüsselwörter: „Ich bin nicht einverstanden“, „Nein“, "
             "„Aber“, „Bist du sicher …?“, „… andere Idee“. "
             "Abgrenzung: neutrale Rückfrage zum Ausbauen → EI."
         )},
        {"Code": "N", "Bezeichnung": "Nachdenken und Erklären",
         "Beschreibung": (
             "Erklären, begründen und/oder nach Alternativen suchen — in "
             "Bezug auf eigene oder fremde Ideen. "
             "Schlüsselwörter: „ich denke“, „weil“, „deshalb“, „daher“, "
             "„wenn … dann“, „es ist wie …“, „stell dir vor“, „könnte“. "
             "Abgrenzung: bloßes Erweitern ohne Begründung → I."
         )},
        {"Code": "EN", "Bezeichnung": "Ermutigen zum Nachdenken und Erklären",
         "Beschreibung": (
             "Das Gegenüber auffordern, eine BEGRÜNDUNG zu liefern — eigene "
             "oder fremde Ideen zu erklären, zu begründen und/oder "
             "Alternativen zu suchen. "
             "Schlüsselwörter: „Warum?“, „Wieso?“, „Wie kommst du darauf?“, "
             "„Kannst du das begründen?“. "
             "Abgrenzung: lädt nur zum Ausbauen oder Klären ein → EI. Eine "
             "inhaltliche Verständnis- oder Rückfrage ist KEIN EN — sie wird "
             "nach ihrer dialogischen Funktion codiert: greift sie eine Idee "
             "auf → I; steckt Zweifel oder Ablehnung darin → H; liefert sie "
             "selbst eine Begründung oder Alternative → N. Organisatorische "
             "Fragen zum Arbeitsauftrag („Sollen wir das aufschreiben?“, „Wo "
             "tragen wir das ein?“) sind keine dialogischen Züge und bleiben "
             "uncodiert. "
             "Im Klassengespräch ein Zug der LEHRKRAFT — bei Schüler:innen "
             "nur plausibel, wenn keine Lehrkraft am Gespräch beteiligt ist "
             "(z. B. Gruppenarbeit)."
         )},
        {"Code": "ZK", "Bezeichnung": "Ideen zusammenführen und Konsens finden",
         "Beschreibung": (
             "Ideen bewerten, kontrastieren oder zusammenfassen, Argumente "
             "miteinander verknüpfen, Zustimmung/Konsens ausdrücken oder "
             "andere dazu auffordern. "
             "Schlüsselwörter: „ich stimme zu“, „um es zusammenzufassen“, "
             "„also sind wir alle der Meinung, dass …“, „ähnlich und "
             "unterschiedlich“. "
             "Abgrenzung: greift nur einen einzelnen Beitrag auf → I. "
             "Im Klassengespräch ein Zug der LEHRKRAFT — bei Schüler:innen "
             "nur plausibel, wenn keine Lehrkraft am Gespräch beteiligt ist "
             "(z. B. Gruppenarbeit)."
         )},
        {"Code": "R", "Bezeichnung": "Reflexion",
         "Beschreibung": (
             "Den Dialog oder die Lernaktivität bewerten oder metakognitiv "
             "reflektieren; andere dazu auffordern. "
             "Schlüsselwörter: „der Dialog“, „das Sprechen“, „die Aufgabe“, "
             "„was du gelernt hast“, „ich habe meine Meinung geändert“, "
             "„Gesprächsregeln“. "
             "Abgrenzung: bezieht sich auf den Prozess, nicht die Sachfrage "
             "(→ N); Bezüge nach außen → V."
         )},
        {"Code": "V", "Bezeichnung": "Verknüpfen",
         "Beschreibung": (
             "Verknüpfung mit Beiträgen, Wissen oder Erfahrungen über den "
             "unmittelbaren Dialog hinaus (frühere/kommende Stunden, "
             "Vorwissen, Alltag, Quellen). "
             "Schlüsselwörter: „letzte Stunde“, „vorher“, „erinnert mich "
             "an“, „nächste Stunde“, „im Zusammenhang mit“, „bei dir zu "
             "Hause“. "
             "Abgrenzung: Bezüge innerhalb des Gesprächs → I."
         )},
        {"Code": "L", "Bezeichnung": "Das Gespräch oder die Lernsituation leiten",
         "Beschreibung": (
             "Verantwortung übernehmen, die Aktivität zu gestalten oder das "
             "Gespräch in eine gewünschte Richtung zu lenken; unterstützende "
             "Strategien für Dialog und Lernen (Denkzeit geben, "
             "Partnerarbeit anregen). "
             "Schlüsselwörter: „Was ist mit …“, „konzentriere dich auf …“, "
             "„versuche einmal“, „keine Eile“, „lass uns …“. "
             "Abgrenzung: ohne eigenen Inhaltsbeitrag (→ N/ÄN). Das bloße "
             "Drannehmen einer Person — der Turn besteht nur aus einem "
             "Namen oder Sprecherlabel (z. B. „S2“) — ist KEIN Code; solche "
             "Turns bleiben uncodiert. "
             "Im Klassengespräch ein Zug der LEHRKRAFT — bei Schüler:innen "
             "nur plausibel, wenn keine Lehrkraft am Gespräch beteiligt ist "
             "(z. B. Gruppenarbeit)."
         )},
        {"Code": "ÄN", "Bezeichnung": "Äußerungen und Nachfragen",
         "Beschreibung": (
             "Auffang-Kategorie: relevante Beiträge anbieten oder erfragen, "
             "um eine Diskussion zu eröffnen oder die Beteiligung zu "
             "erhöhen — nur wenn kein spezifischerer Code passt. Auch kurze "
             "Antworten auf geschlossene Fragen und Plenums-Berichte. "
             "Schlüsselwörter: „Was denkst du über …?“, „Sag mal“, „deine "
             "Gedanken“, „meine Meinung ist …“. "
             "Abgrenzung: nur wenn I, EI, H, N, EN, ZK oder V nicht "
             "zutreffen. Das bloße Drannehmen (Turn nur Name/Sprecherlabel, "
             "z. B. „S2“) bleibt auch hier uncodiert."
         )},
    ],
    "en": [
        {"Code": "B", "Label": "Build on ideas",
         "Description": (
             "Build on, elaborate, clarify or comment on one's own or "
             "others' ideas expressed in earlier turns. "
             "Keywords: 'is also', 'that makes me think', 'I mean', "
             "'she meant', 'building on'. "
             "Distinction: explicit reasoning → R; bringing several "
             "contributions together → CA."
         )},
        {"Code": "IB", "Label": "Invite to build on ideas",
         "Description": (
             "Invite others to build on, elaborate, rephrase, clarify or "
             "comment on their own or others' ideas. "
             "Keywords: 'What?', 'Tell me', 'Can you rephrase that?', "
             "'Do you mean that …?', 'Do you agree?', 'Can you add …?'. "
             "Distinction: invites justification → IR. Organisational "
             "questions about the task are not dialogic moves and stay "
             "uncoded. "
             "In whole-class talk a TEACHER move — plausible for student "
             "turns only when no teacher takes part in the conversation "
             "(e.g. group work)."
         )},
        {"Code": "CH", "Label": "Challenge",
         "Description": (
             "Question, doubt, probe, disagree with or challenge an idea. "
             "Keywords: 'I disagree', 'No', 'But', 'Are you sure …?', "
             "'… different idea'. "
             "Distinction: a neutral follow-up inviting elaboration → IB."
         )},
        {"Code": "R", "Label": "Make reasoning explicit",
         "Description": (
             "Explain, justify and/or explore alternatives — relating to "
             "one's own or others' ideas. "
             "Keywords: 'I think', 'because', 'so', 'therefore', "
             "'if … then', 'it's like …', 'imagine if', 'could'. "
             "Distinction: mere extension without justification → B."
         )},
        {"Code": "IR", "Label": "Invite reasoning",
         "Description": (
             "Invite the other party to supply a JUSTIFICATION — to explain, "
             "justify and/or explore alternatives regarding their own or "
             "others' ideas. "
             "Keywords: 'Why?', 'How come?', 'What makes you say that?', "
             "'Can you justify that?'. "
             "Distinction: invites mere elaboration or clarification → IB. A "
             "content or comprehension question is NOT IR — code it by its "
             "dialogic function: taking up an idea → B; carrying doubt or "
             "rejection → CH; supplying reasoning or an alternative itself → "
             "R. Organisational questions about the task ('Should we write "
             "this down?', 'Where do we put this?') are not dialogic moves "
             "and stay uncoded. "
             "In whole-class talk a TEACHER move — plausible for student "
             "turns only when no teacher takes part in the conversation "
             "(e.g. group work)."
         )},
        {"Code": "CA", "Label": "Coordination of ideas and agreement",
         "Description": (
             "Evaluate, contrast or summarise ideas, connect arguments, "
             "express agreement/consensus or invite others to do so. "
             "Keywords: 'I agree', 'to sum up', 'so we all think that …', "
             "'similar and different'. "
             "Distinction: takes up only a single contribution → B. "
             "In whole-class talk a TEACHER move — plausible for student "
             "turns only when no teacher takes part in the conversation "
             "(e.g. group work)."
         )},
        {"Code": "RD", "Label": "Reflect on dialogue or activity",
         "Description": (
             "Evaluate or reflect metacognitively on the dialogue or the "
             "learning activity; invite others to do so. "
             "Keywords: 'the dialogue', 'the talk', 'the task', 'what you "
             "learned', 'I changed my mind', 'ground rules'. "
             "Distinction: concerns the process, not the subject question "
             "(→ R); references outside the talk → C."
         )},
        {"Code": "C", "Label": "Connect",
         "Description": (
             "Connect to contributions, knowledge or experiences beyond the "
             "immediate dialogue (earlier/upcoming lessons, prior "
             "knowledge, everyday life, sources). "
             "Keywords: 'last lesson', 'before', 'reminds me of', 'next "
             "lesson', 'connected to', 'at your home'. "
             "Distinction: references within the conversation → B."
         )},
        {"Code": "G", "Label": "Guide direction of dialogue or activity",
         "Description": (
             "Take responsibility for shaping the activity or steering the "
             "talk in a desired direction; supportive strategies for "
             "dialogue and learning (offering thinking time, prompting pair "
             "talk). "
             "Keywords: 'What about …', 'focus on …', 'have a go', "
             "'no rush', 'let's …'. "
             "Distinction: without contributing content itself (→ R/E). "
             "Merely nominating a person — the turn consists only of a name "
             "or speaker label (e.g. 'S2') — is NOT a code; such turns stay "
             "uncoded. "
             "In whole-class talk a TEACHER move — plausible for student "
             "turns only when no teacher takes part in the conversation "
             "(e.g. group work)."
         )},
        {"Code": "E", "Label": "Express or invite ideas",
         "Description": (
             "Catch-all category: offer or invite relevant contributions to "
             "open a discussion or increase participation — only when no "
             "more specific code applies. Also short answers to closed "
             "questions and plenary reports. "
             "Keywords: 'What do you think about …?', 'Tell me', 'your "
             "thoughts', 'my opinion is …'. "
             "Distinction: only when B, IB, CH, R, IR, CA or C do not "
             "apply. Merely nominating someone (turn is only a name/speaker "
             "label, e.g. 'S2') stays uncoded here too."
         )},
    ],
}

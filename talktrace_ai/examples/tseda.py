"""Built-in T-SEDA codebook template.

Based on the **T-SEDA** dialogue coding scheme (T-SEDA Collective 2023,
*Toolkit for Systematic Educational Dialogue Analysis*, v.9, University of
Cambridge, https://camtree.learnworlds.com/t-seda — released under a Creative
Commons Attribution licence, CC BY). T-SEDA explicitly allows local
adaptation; this template keeps the official code logic, shortens the
definitions for prompt use and replaces the original examples with
subject-neutral classroom anchors.

Language handling differs from ``DEMO_CODEBOOK``: the demo keeps the German
abbreviations in both languages (they label the same demo data), while this
template uses the **official abbreviations of each language version** —
German pack v9: ``EI, I, H, EN, N, ZK, V, R, L, ÄN``; English original:
``IB, B, CH, IR, R, CA, C, RD, G, E``. ⚠️ The letters collide across
languages: German ``R`` = Reflexion (engl. ``RD``), while English ``R`` =
make reasoning explicit (dt. ``N``). Codes are per-language identifiers here,
never translated UI strings.

Entry order doubles as the single-coding fallback hierarchy (codebook
position = priority, see ``utils/codebook_hierarchy``): the specific codes
come first, the catch-all (``ÄN``/``E``) is deliberately last.

The dict shape (``Code``/``Bezeichnung``/``Beschreibung`` resp.
``Code``/``Label``/``Description``) matches exactly what a DOCX-table
codebook import produces, so the template flows through the entire pipeline
(preview, prompt, enum schema, hierarchy) like an uploaded codebook.
"""


TSEDA_ATTRIBUTION = (
    "T-SEDA Collective (2023). Toolkit for Systematic Educational Dialogue "
    "Analysis (T-SEDA). v.9. University of Cambridge. CC BY."
)

# Pre-sets applied when the template is loaded: T-SEDA's most common use in
# this app is formative feedback on the *teacher's* dialogic moves, and
# T-SEDA is a multi-code scheme (several dialogic functions per turn).
TSEDA_PRESETS = {
    "llm_switch": True,
    "analyse_teacher_switch": True,
    "analyse_students_switch": False,
    "multi_coding_switch": True,
}


TSEDA_CODEBOOK = {
    "de": [
        {"Code": "EI", "Bezeichnung": "Ermutigen, auf Ideen aufzubauen",
         "Beschreibung": (
             "Lädt andere ein, eigene oder fremde Ideen/Beiträge aufzugreifen, "
             "auszuführen, zu klären, zu kommentieren oder zu verbessern. "
             "Indikatoren: „Was meinst du damit?“, „Kannst du das umformulieren?“, "
             "„Stimmst du zu?“, „Kannst du ergänzen?“. "
             "Beispiel — L: „Lena hat einen wichtigen Begriff genannt — wer kann "
             "das aufgreifen und weiterdenken?“ "
             "Abgrenzung: lädt zum Ausbauen ein, nicht zum Begründen (→ EN); "
             "lädt keine neuen, bezuglosen Ideen ein (→ ÄN)."
         )},
        {"Code": "I", "Bezeichnung": "Auf Ideen aufbauen",
         "Beschreibung": (
             "Greift eigene oder fremde Ideen aus vorhergehenden Beiträgen auf, "
             "führt sie aus, klärt oder kommentiert sie. "
             "Indikatoren: „anknüpfend an …“, „wie X gesagt hat …“, "
             "„das bringt mich auf …“, „auch …“. "
             "Beispiel — S: „Anknüpfend an Lena — das heißt auch, dass alle "
             "mitentscheiden dürfen.“ "
             "Abgrenzung: erweitert, ohne explizit zu begründen (Begründung → N); "
             "greift einen Beitrag auf, synthetisiert nicht mehrere (→ ZK)."
         )},
        {"Code": "H", "Bezeichnung": "Herausfordern",
         "Beschreibung": (
             "Stellt eine Idee in Frage, zweifelt an, widerspricht oder fordert "
             "sie heraus. "
             "Indikatoren: „Ich sehe das anders“, „Aber …“, „Bist du sicher?“, "
             "Gegenposition. "
             "Beispiel — S: „Aber gilt das wirklich in jedem Fall? Mir fällt ein "
             "Gegenbeispiel ein.“ "
             "Abgrenzung: keine neutrale Rückfrage zum Ausbauen (→ EI)."
         )},
        {"Code": "EN", "Bezeichnung": "Ermutigen zum Nachdenken und Erklären",
         "Beschreibung": (
             "Lädt andere ein zu erklären, zu begründen und/oder "
             "Möglichkeitsdenken zu nutzen — bezogen auf eigene oder fremde Ideen. "
             "Indikatoren: „Warum?“, „Wie kommst du darauf?“, „Begründe das“, "
             "„Was wäre, wenn …?“. "
             "Beispiel — L: „Warum sollte das so sein? Begründe das mal.“ "
             "Abgrenzung: lädt zum Begründen ein, nicht nur zum Ausbauen (→ EI)."
         )},
        {"Code": "N", "Bezeichnung": "Nachdenken und Erklären",
         "Beschreibung": (
             "Erklärt, begründet und/oder nutzt Möglichkeitsdenken — bezogen auf "
             "eigene oder fremde Ideen. "
             "Indikatoren: „weil …“, „also …“, „deshalb …“, „wenn … dann …“, "
             "„stell dir vor …“, „könnte …“. "
             "Beispiel — S: „Ich finde das richtig, weil alle davon betroffen "
             "sind.“ "
             "Abgrenzung: verlangt eine explizite Begründungs- oder "
             "Möglichkeitsstruktur; bloßes Erweitern ohne Begründung → I."
         )},
        {"Code": "ZK", "Bezeichnung": "Ideen zusammenführen und Konsens finden",
         "Beschreibung": (
             "Kontrastiert und synthetisiert mehrere Beiträge, bewertet sie, "
             "drückt Übereinstimmung/Konsens aus oder lädt zur Synthese ein. "
             "Indikatoren: „zusammengefasst …“, „wir denken also alle, dass …“, "
             "„einerseits … andererseits …“, „stimme zu“. "
             "Beispiel — L: „Fassen wir zusammen: Ein Argument war X, das "
             "Gegenargument Y — beide zielen auf Z.“ "
             "Abgrenzung: integriert/kontrastiert mehrere Beiträge; das Aufgreifen "
             "eines einzelnen Beitrags → I."
         )},
        {"Code": "V", "Bezeichnung": "Verknüpfen",
         "Beschreibung": (
             "Macht den Lernpfad explizit durch Bezüge außerhalb des unmittelbaren "
             "Gesprächs: frühere/spätere Stunden, Vorwissen, Alltag, Quellen. "
             "Indikatoren: „letzte Stunde“, „erinnert mich an“, "
             "„hängt zusammen mit“, „in den Nachrichten“. "
             "Beispiel — L: „Das knüpft an unser Thema aus der letzten Stunde an.“ "
             "Abgrenzung: verweist nach außen; Bezüge innerhalb des Gesprächs → I."
         )},
        {"Code": "R", "Bezeichnung": "Reflexion",
         "Beschreibung": (
             "Bewertet oder reflektiert metakognitiv den Prozess des Dialogs oder "
             "die Lernaktivität; lädt andere dazu ein. "
             "Indikatoren: „Was habt ihr gelernt?“, „Hat uns das Gespräch "
             "geholfen?“, „Ich habe meine Meinung geändert“, Gesprächsregeln. "
             "Beispiel — S: „Durch Miras Argument habe ich meine Meinung "
             "geändert.“ "
             "Abgrenzung: bezieht sich auf den Prozess des Redens/Lernens, nicht "
             "auf die Sachfrage (inhaltliche Begründung → N)."
         )},
        {"Code": "L", "Bezeichnung": "Das Gespräch oder die Lernsituation leiten",
         "Beschreibung": (
             "Übernimmt Verantwortung, die Aktivität zu gestalten oder das "
             "Gespräch zu fokussieren; Scaffolding-Strategien zur Stützung von "
             "Dialog und Lernen. "
             "Indikatoren: „Konzentriert euch auf …“, „Lass uns …“, "
             "„Besprecht das kurz zu zweit“, Denkzeit anbieten. "
             "Beispiel — L: „Konzentrieren wir uns zuerst auf das stärkste "
             "Argument.“ "
             "Abgrenzung: strukturiert/steuert, ohne selbst Inhalt beizutragen "
             "oder zu begründen. Das bloße Drannehmen einer Person — der Turn "
             "besteht nur aus einem Namen oder Sprecherlabel (z. B. „S2“, "
             "„Lena?“) — ist KEIN Code; solche Turns bleiben uncodiert."
         )},
        {"Code": "ÄN", "Bezeichnung": "Äußerungen und Nachfragen",
         "Beschreibung": (
             "Auffang-Kategorie: bietet relevante Beiträge an oder lädt sie ein, "
             "um ein Gespräch zu eröffnen oder fortzuführen — sofern kein "
             "spezifischerer Code zutrifft. Auch kurze Antworten auf geschlossene "
             "Fragen. "
             "Indikatoren: „Was denkst du über …?“, „Meine Meinung ist …“, "
             "offene Eröffnungsfragen. "
             "Beispiel — L: „Was fällt euch zu diesem Begriff spontan ein?“ "
             "Abgrenzung: nur vergeben, wenn EI, EN, I, N, ZK oder V nicht "
             "zutreffen. Auch als Auffang-Kategorie NICHT für das bloße "
             "Drannehmen (Turn besteht nur aus Name/Sprecherlabel, z. B. „S2“) "
             "— das bleibt uncodiert."
         )},
    ],
    "en": [
        {"Code": "IB", "Label": "Invite to build on ideas",
         "Description": (
             "Invites others to take up, elaborate, clarify, comment on or "
             "improve their own or others' ideas/contributions. "
             "Indicators: 'What do you mean by that?', 'Can you rephrase that?', "
             "'Do you agree?', 'Can you add to that?'. "
             "Example — T: 'Lena mentioned an important concept — who can take "
             "that up and think it further?' "
             "Distinction: invites elaboration, not justification (→ IR); does "
             "not invite new, unconnected ideas (→ E)."
         )},
        {"Code": "B", "Label": "Build on ideas",
         "Description": (
             "Takes up one's own or others' ideas from previous turns and "
             "elaborates, clarifies or comments on them. "
             "Indicators: 'building on …', 'as X said …', 'that makes me "
             "think of …', 'also …'. "
             "Example — S: 'Building on Lena — that also means everyone gets a "
             "say.' "
             "Distinction: extends without explicit justification "
             "(justification → R); takes up one contribution, does not "
             "synthesise several (→ CA)."
         )},
        {"Code": "CH", "Label": "Challenge",
         "Description": (
             "Questions, doubts, disagrees with or challenges an idea. "
             "Indicators: 'I see that differently', 'But …', 'Are you sure?', "
             "counter-position. "
             "Example — S: 'But is that really true in every case? I can think "
             "of a counter-example.' "
             "Distinction: not a neutral follow-up question inviting "
             "elaboration (→ IB)."
         )},
        {"Code": "IR", "Label": "Invite reasoning",
         "Description": (
             "Invites others to explain, justify and/or use possibility "
             "thinking — relating to their own or others' ideas. "
             "Indicators: 'Why?', 'How did you get there?', 'Justify that', "
             "'What if …?'. "
             "Example — T: 'Why should that be the case? Give a reason.' "
             "Distinction: invites justification, not mere elaboration (→ IB)."
         )},
        {"Code": "R", "Label": "Make reasoning explicit",
         "Description": (
             "Explains, justifies and/or uses possibility thinking — relating "
             "to one's own or others' ideas. "
             "Indicators: 'because …', 'so …', 'therefore …', 'if … then …', "
             "'imagine …', 'could …'. "
             "Example — S: 'I think that is right because everyone is affected "
             "by it.' "
             "Distinction: requires an explicit reasoning or possibility "
             "structure; mere extension without justification → B."
         )},
        {"Code": "CA", "Label": "Coordination of ideas and agreement",
         "Description": (
             "Contrasts and synthesises several contributions, evaluates them, "
             "expresses agreement/consensus or invites synthesis. "
             "Indicators: 'to sum up …', 'so we all think that …', 'on the one "
             "hand … on the other …', 'I agree'. "
             "Example — T: 'Let's summarise: one argument was X, the "
             "counter-argument Y — both aim at Z.' "
             "Distinction: integrates/contrasts several contributions; taking "
             "up a single contribution → B."
         )},
        {"Code": "C", "Label": "Connect",
         "Description": (
             "Makes the learning trajectory explicit through references "
             "outside the immediate conversation: earlier/later lessons, prior "
             "knowledge, everyday life, sources. "
             "Indicators: 'last lesson', 'reminds me of', 'is connected to', "
             "'in the news'. "
             "Example — T: 'That links back to our topic from the last lesson.' "
             "Distinction: points outside the talk; references within the "
             "conversation → B."
         )},
        {"Code": "RD", "Label": "Reflect on dialogue or activity",
         "Description": (
             "Evaluates or reflects metacognitively on the process of the "
             "dialogue or the learning activity; invites others to do so. "
             "Indicators: 'What have you learned?', 'Did the discussion help "
             "us?', 'I changed my mind', ground rules for talk. "
             "Example — S: 'Mira's argument made me change my mind.' "
             "Distinction: concerns the process of talking/learning, not the "
             "subject question itself (content reasoning → R)."
         )},
        {"Code": "G", "Label": "Guide direction of dialogue or activity",
         "Description": (
             "Takes responsibility for shaping the activity or focusing the "
             "talk in a desired direction; scaffolding strategies supporting "
             "dialogue and learning. "
             "Indicators: 'Focus on …', 'Let's …', 'Discuss this briefly in "
             "pairs', offering thinking time. "
             "Example — T: 'Let's concentrate on the strongest argument first.' "
             "Distinction: structures/steers without contributing or "
             "justifying content itself. Merely nominating a person — the turn "
             "consists only of a name or speaker label (e.g. 'S2', 'Lena?') — "
             "is NOT a code; such turns stay uncoded."
         )},
        {"Code": "E", "Label": "Express or invite ideas",
         "Description": (
             "Catch-all category: offers or invites relevant contributions to "
             "open or sustain a conversation — as long as no more specific "
             "code applies. Also short answers to closed questions. "
             "Indicators: 'What do you think about …?', 'My opinion is …', "
             "open opening questions. "
             "Example — T: 'What comes to mind spontaneously for this concept?' "
             "Distinction: only assigned when IB, IR, B, R, CA or C do not "
             "apply. Even as the catch-all, NOT for merely nominating someone "
             "(the turn consists only of a name/speaker label, e.g. 'S2') — "
             "that stays uncoded."
         )},
    ],
}

"""Synthetic demo data so new users can preview the app without API keys.

Scenario: a civics ("Politik") lesson discussing
"Soll das Wahlalter der Bundestagswahl auf 16 Jahre abgesenkt werden?"
(Should the voting age for the federal election be lowered to 16?).

The codebook follows **T-SEDA** (Teacher Scheme for Educational Dialogue
Analysis; T-SEDA Collective 2023, University of Cambridge) — code IDs are the
official German T-SEDA abbreviations (I, EI, H, N, EN, ZK, R, V, L, ÄN) and are
kept identical across languages because they are code identifiers, not UI
strings. Only the dialogue text and the codebook labels/descriptions are
translated.

T-SEDA codes the **teacher's** dialogic moves: only LEHRER/TEACHER turns carry
codes here; every student turn stays uncoded (it still appears in the
transcript and in the quantitative stats, just not in the qualitative coding
table). A teacher turn carries 0–2 codes — two turns here carry two codes,
represented (per the analysis schema) as one row per code with the same Impuls
text. The teacher utterances deliberately span a broad range of moves
(launching, inviting, challenging, connecting, consolidating, reflecting) so
the demo showcases most of the scheme.

The transcript, the teacher tag and the analysis rows are language-aware:
look up the matching language with `[lang]` (or pass `lang="en"`/`"de"` to
`build_demo_llm_analysis_df`). The DataFrame *column* names ("Sprecher",
"Shortcode", "Impuls") are internal keys used across the analysis pipeline
and stay German on purpose.
"""

import pandas as pd


DEMO_NUM_PUPILS = 22

DEMO_TEACHER_NAME = {
    "de": "LEHRER",
    "en": "TEACHER",
}

DEMO_GROUP_ID = {
    "de": "Demo-Kurs Politik",
    "en": "Demo Civics Class",
}


DEMO_TRANSCRIPT = {
    "de": """LEHRER: Heute diskutieren wir eine Frage, über die gerade im Bundestag gestritten wird: Soll das Wahlalter für die Bundestagswahl auf 16 Jahre abgesenkt werden? Was meint ihr?
S01: Ich finde, das sollte man machen.
LEHRER: Kannst du das genauer begründen, warum du dafür bist?
S01: Weil Jugendliche von vielen Entscheidungen lange betroffen sind, zum Beispiel beim Klimaschutz. Wenn wir die Folgen tragen, sollten wir auch mitbestimmen dürfen.
S02: Da würde ich anschließen: Bei der Europawahl durften 16-Jährige schon wählen, und das hat gut funktioniert.
LEHRER: Sieht das jemand anders?
S03: Ich bin skeptisch. Mit 16 hat man oft noch nicht genug politisches Wissen, um so eine Entscheidung zu treffen.
S04: Aber das könnte man genauso über viele Erwachsene sagen. Wissen hängt nicht am Alter.
S03: Stimmt schon, aber Erwachsene haben im Schnitt mehr Lebenserfahrung.
LEHRER: Mira, du hattest vorhin etwas zur Schülervertretung gesagt - magst du das einbringen?
S05: Ja. In unserer SV entscheiden auch 15- und 16-Jährige über wichtige Sachen, und das klappt gut. Das zeigt, dass man in dem Alter Verantwortung übernehmen kann.
S02: Genau das meine ich auch.
LEHRER: Aber stimmt das wirklich? In einigen Bundesländern dürfen 16-Jährige längst bei Kommunal- und Landtagswahlen wählen - spricht das nicht gegen deinen Einwand, Jonas?
S06: Man könnte politische Bildung in der Schule ausbauen, dann wären 16-Jährige besser vorbereitet.
S01: Das finde ich einen guten Kompromiss: absenken, aber gleichzeitig mehr Politikunterricht.
LEHRER: Ihr haltet also fest, dass Wahlrecht und politische Bildung zusammengehören?
S04: Ja, sonst wählt man vielleicht nur nach Gefühl.
S03: Okay, dem würde ich zustimmen, wenn die Bildung wirklich kommt.
LEHRER: Spannend - vorhin warst du noch dagegen. Was hat dich umgestimmt?
S03: Das Argument mit der politischen Bildung. Wenn man uns besser vorbereitet, traue ich es 16-Jährigen zu.
LEHRER: Gut. Lasst uns am Ende sammeln: Welche Argumente sprechen dafür, welche dagegen?
S05: Dafür sprechen Betroffenheit und Verantwortung.
S06: Dagegen vielleicht zu wenig Erfahrung - aber das lässt sich durch Bildung ausgleichen.
LEHRER: Genau, die Betroffenheit Jugendlicher ist ein starkes Argument - gerade weil ihr die Folgen am längsten tragt.
""",
    "en": """TEACHER: Today we're discussing a question that's currently being debated in the Bundestag: Should the voting age for the federal election be lowered to 16? What do you think?
S01: I think we should do that.
TEACHER: Can you explain in more detail why you're in favour?
S01: Because young people are affected by many decisions for a long time, for example on climate protection. If we bear the consequences, we should be allowed to have a say too.
S02: I'd build on that: in the European election 16-year-olds were already allowed to vote, and that worked well.
TEACHER: Does anyone see it differently?
S03: I'm sceptical. At 16 you often don't have enough political knowledge to make such a decision.
S04: But you could say the same about many adults. Knowledge doesn't depend on age.
S03: That's true, but on average adults have more life experience.
TEACHER: Mira, earlier you said something about the student council - would you like to bring that in?
S05: Yes. In our student council 15- and 16-year-olds also decide on important things, and it works well. That shows you can take on responsibility at that age.
S02: That's exactly what I mean too.
TEACHER: But is that really true? In several German states 16-year-olds have long been allowed to vote in local and state elections - doesn't that speak against your objection, Jonas?
S06: We could expand political education in school, then 16-year-olds would be better prepared.
S01: I think that's a good compromise: lower it, but at the same time more civics lessons.
TEACHER: So you're concluding that the right to vote and political education belong together?
S04: Yes, otherwise people might vote on gut feeling alone.
S03: Okay, I'd agree with that if the education really happens.
TEACHER: Interesting - earlier you were against it. What changed your mind?
S03: The argument about political education. If we're better prepared, I'd trust 16-year-olds with it.
TEACHER: Good. Let's gather at the end: which arguments speak for it, which against?
S05: In favour: being affected and taking responsibility.
S06: Against: maybe too little experience - but that can be offset through education.
TEACHER: Exactly, young people being affected is a strong argument - precisely because you bear the consequences the longest.
""",
}


DEMO_CODE_LEGEND = {
    "de": (
        "I=Auf Ideen aufbauen, EI=Ermutigen aufzubauen, H=Herausfordern, "
        "N=Nachdenken/Erklären, EN=Ermutigen zum Nachdenken, "
        "ZK=Zusammenführen/Konsens, R=Reflexion über den Dialog, "
        "V=Verknüpfen (außerhalb), L=Gespräch leiten, ÄN=Äußerungen/Nachfragen"
    ),
    "en": (
        "I=Build on ideas, EI=Invite build-on, H=Challenge, N=Reason/explain, "
        "EN=Invite reasoning, ZK=Coordinate/consensus, R=Reflect on dialogue, "
        "V=Connect (outside), L=Guide the talk, ÄN=Utterances/queries"
    ),
}


# Strukturiertes Demo-Codebuch — list[dict] genau wie ein per docx-Tabelle
# importiertes Codebuch. Wird in der Vorschau als Tabelle gerendert
# (`show_codebook_preview` in handlers/analysis.py). Die Code-IDs sind die
# offiziellen deutschen T-SEDA-Kürzel und bleiben in beiden Sprachen gleich.
DEMO_CODEBOOK = {
    "de": [
        {"Code": "I", "Bezeichnung": "Auf Ideen aufbauen",
         "Beschreibung": "Greift einen Vorbeitrag auf und führt ihn weiter aus."},
        {"Code": "EI", "Bezeichnung": "Ermutigen, auf Ideen aufzubauen",
         "Beschreibung": "Lädt ein, einen Beitrag aufzugreifen oder auszuführen."},
        {"Code": "H", "Bezeichnung": "Herausfordern",
         "Beschreibung": "Zweifelt an, widerspricht oder fordert einen Beitrag heraus."},
        {"Code": "N", "Bezeichnung": "Nachdenken und Erklären",
         "Beschreibung": "Erklärt oder begründet (z. B. mit 'weil', 'also', 'wenn … dann')."},
        {"Code": "EN", "Bezeichnung": "Ermutigen zum Nachdenken und Erklären",
         "Beschreibung": "Fordert eine Erklärung, Begründung oder Möglichkeitsdenken ein."},
        {"Code": "ZK", "Bezeichnung": "Ideen zusammenführen und Konsens finden",
         "Beschreibung": "Kontrastiert oder synthetisiert mehrere Beiträge, sucht Konsens."},
        {"Code": "R", "Bezeichnung": "Reflexion",
         "Beschreibung": "Denkt metakognitiv über den Dialog, den Prozess oder das Lernen nach."},
        {"Code": "V", "Bezeichnung": "Verknüpfen",
         "Beschreibung": "Stellt einen Bezug außerhalb des aktuellen Gesprächs her (Vorstunde, Alltag, Quelle)."},
        {"Code": "L", "Bezeichnung": "Das Gespräch leiten",
         "Beschreibung": "Steuert oder fokussiert das Gespräch (Scaffolding), ohne inhaltlichen Beitrag."},
        {"Code": "ÄN", "Bezeichnung": "Äußerungen und Nachfragen",
         "Beschreibung": "Auffang-Kategorie: eröffnet oder äußert, wenn kein spezifischerer Code passt."},
    ],
    "en": [
        {"Code": "I", "Label": "Build on ideas",
         "Description": "Takes up a previous contribution and extends it."},
        {"Code": "EI", "Label": "Invite building on ideas",
         "Description": "Invites someone to take up or extend a contribution."},
        {"Code": "H", "Label": "Challenge",
         "Description": "Doubts, disagrees with, or challenges a contribution."},
        {"Code": "N", "Label": "Reason and explain",
         "Description": "Explains or justifies (e.g. 'because', 'so', 'if … then')."},
        {"Code": "EN", "Label": "Invite reasoning",
         "Description": "Asks for an explanation, justification, or possibility thinking."},
        {"Code": "ZK", "Label": "Coordinate ideas / reach consensus",
         "Description": "Contrasts or synthesises several contributions, seeks consensus."},
        {"Code": "R", "Label": "Reflect on the dialogue",
         "Description": "Thinks metacognitively about the dialogue, the process, or learning."},
        {"Code": "V", "Label": "Connect",
         "Description": "Makes a link outside the current conversation (prior lesson, everyday life, a source)."},
        {"Code": "L", "Label": "Guide the conversation",
         "Description": "Steers or focuses the talk (scaffolding) without a content contribution."},
        {"Code": "ÄN", "Label": "Utterances and queries",
         "Description": "Catch-all: opens or states something when no more specific code fits."},
    ],
}


# T-SEDA coding of the demo transcript — TEACHER TURNS ONLY (student turns stay
# uncoded and are therefore absent here). One tuple per (turn, code): a teacher
# turn with two codes appears as two consecutive rows with the same Impuls text.
# This mirrors the real analysis schema ("one item per code"). The Impuls text
# matches the transcript line verbatim so the over-time mapping can locate each
# turn. Codes covered: L, EN, EI, H, V, ZK, R, I, N (ÄN — the residual catch-all
# — does not fit the teacher's facilitation moves and is left out).
_DEMO_ROWS = {
    "de": [
        ("LEHRER", "L",  "Heute diskutieren wir eine Frage, über die gerade im Bundestag gestritten wird: Soll das Wahlalter für die Bundestagswahl auf 16 Jahre abgesenkt werden? Was meint ihr?"),
        ("LEHRER", "EN", "Kannst du das genauer begründen, warum du dafür bist?"),
        ("LEHRER", "EI", "Sieht das jemand anders?"),
        ("LEHRER", "EI", "Mira, du hattest vorhin etwas zur Schülervertretung gesagt - magst du das einbringen?"),
        ("LEHRER", "H",  "Aber stimmt das wirklich? In einigen Bundesländern dürfen 16-Jährige längst bei Kommunal- und Landtagswahlen wählen - spricht das nicht gegen deinen Einwand, Jonas?"),
        ("LEHRER", "V",  "Aber stimmt das wirklich? In einigen Bundesländern dürfen 16-Jährige längst bei Kommunal- und Landtagswahlen wählen - spricht das nicht gegen deinen Einwand, Jonas?"),
        ("LEHRER", "ZK", "Ihr haltet also fest, dass Wahlrecht und politische Bildung zusammengehören?"),
        ("LEHRER", "R",  "Spannend - vorhin warst du noch dagegen. Was hat dich umgestimmt?"),
        ("LEHRER", "L",  "Gut. Lasst uns am Ende sammeln: Welche Argumente sprechen dafür, welche dagegen?"),
        ("LEHRER", "I",  "Genau, die Betroffenheit Jugendlicher ist ein starkes Argument - gerade weil ihr die Folgen am längsten tragt."),
        ("LEHRER", "N",  "Genau, die Betroffenheit Jugendlicher ist ein starkes Argument - gerade weil ihr die Folgen am längsten tragt."),
    ],
    "en": [
        ("TEACHER", "L",  "Today we're discussing a question that's currently being debated in the Bundestag: Should the voting age for the federal election be lowered to 16? What do you think?"),
        ("TEACHER", "EN", "Can you explain in more detail why you're in favour?"),
        ("TEACHER", "EI", "Does anyone see it differently?"),
        ("TEACHER", "EI", "Mira, earlier you said something about the student council - would you like to bring that in?"),
        ("TEACHER", "H",  "But is that really true? In several German states 16-year-olds have long been allowed to vote in local and state elections - doesn't that speak against your objection, Jonas?"),
        ("TEACHER", "V",  "But is that really true? In several German states 16-year-olds have long been allowed to vote in local and state elections - doesn't that speak against your objection, Jonas?"),
        ("TEACHER", "ZK", "So you're concluding that the right to vote and political education belong together?"),
        ("TEACHER", "R",  "Interesting - earlier you were against it. What changed your mind?"),
        ("TEACHER", "L",  "Good. Let's gather at the end: which arguments speak for it, which against?"),
        ("TEACHER", "I",  "Exactly, young people being affected is a strong argument - precisely because you bear the consequences the longest."),
        ("TEACHER", "N",  "Exactly, young people being affected is a strong argument - precisely because you bear the consequences the longest."),
    ],
}


def build_demo_llm_analysis_df(lang: str = "de"):
    """Build the synthetic LLM analysis DataFrame for the demo transcript.

    Columns match what run_analysis() produces. The column *names* stay
    German on purpose because they are internal keys used across the
    analysis pipeline; only the values are language-dependent.
    """
    rows = _DEMO_ROWS.get(lang, _DEMO_ROWS["de"])
    df_rows = [
        {"#": i, "Sprecher": spk, "Shortcode": code, "Impuls": text}
        for i, (spk, code, text) in enumerate(rows, start=1)
    ]
    return pd.DataFrame(df_rows, columns=["#", "Sprecher", "Shortcode", "Impuls"])

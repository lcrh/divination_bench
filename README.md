# divination-bench 🔮

**The first rigorous, peer-reviewed-by-a-decision-model benchmark of large language
models' occult forecasting abilities.**

We gave Claude Opus 5.5 and GPT-6 Astra a Thoth tarot deck, a bundle of virtual yarrow
stalks, and 40 real events from autumn 2026 that happened after their training cutoffs:
elections, court verdicts, Nobel prizes, marathons, dinosaur auctions and mysterious
OpenRouter listings. We then asked an impartial arbiter, TypeSafe Jev, which visions
came true. That's 2,322 readings and 3,014 rankings over six seeds, for $97 of the
sacred OpenRouter credits.

The stars have spoken. Here is what they said.

> *Methodological purists: the sober version, with confidence intervals and caveats,
> is [at the bottom](#for-the-skeptics-what-actually-happened). Everything above it is
> exactly as true, just more enthusiastic.*

---

## ✨ The Prophecy (TL;DR)

1. **The oracle foresaw its own defeat.** Asked to read the cards on this very
   benchmark, Claude predicted that reasoning would win, that divination would "add
   variance rather than insight", and that the divined forecasts would agree with plain
   reasoning "in around 60–70% of cases". The measured figure is 56–67%. The only
   accurate prophecy in this benchmark is the one saying the prophecies don't work.
2. **Reason beats the cards, but not every time.** Plain forecasting ranks first 62%
   of the time, tarot 50%, I Ching 37%. Tarot beats the I Ching head to head 60% of the
   time. The Book of Changes, it turns out, does not change much.
3. **Divination works exactly when reason fails.** On the 23 questions where plain
   reasoning almost always missed, the cards called the outcome **4–6× more often**
   (tarot 9%, I Ching 12%, reason 2%). On the questions reason got right, the cards
   dragged the hit rate from 95% down to about 57%. The cards are the patron saint of
   upsets and the bane of favourites.
4. **The suit of Swords, the suit of the intellect, is the worst predictor in the
   deck.** Forecasts containing a Sword win 24% of the time; forecasts with Wands win
   40%. The **Ace of Swords**, Crowley's card of pure clarity of mind, wins **6%**.
   We find this deeply meaningful.
5. **Claude is the more convincing mystic; GPT is more often right.** Claude's
   prophecies win 60–65% of model match-ups, almost entirely because Jev finds them more
   specific. GPT's call the headline outcome more often (38% vs 33% for plain
   forecasts). Claude is the psychic with the better stage presence.
6. **GPT is the truer believer.** When handed the cards, GPT changes its mind 40–44%
   of the time; Claude only 33%. Neither benefits: when the cards change the call,
   accuracy drops about twice as much as when they don't.
7. **Readings feel true. They aren't.** Pure readings (no prediction allowed) are
   judged "so true" in hindsight about equally for tarot and I Ching. But shown the
   real outcome next to a plausible fake one, Jev matches the readings to the real
   world only **~21%** of the time. That is less often than it matches *the briefing the
   models were given before the event* (25%). Readings are, measurably, slightly less
   in touch with reality than the question itself.

---

## 🃏 The oracle reads its own tea leaves

Before revealing any results, we asked both models to divine the outcome of
divination-bench itself. Claude drew **Nine of Disks (Gain), Two of Disks (Change),
Queen of Swords**:

> *"She is plain reasoning, and she ends the spread as its sovereign: reasoning comes out
> on top. Her severed head is also the revelation. Stripped of their costume, the
> divinatory forecasts turn out to lean heavily on the same reasoning underneath. They
> score respectably mainly because the models quietly steer the symbols toward their own
> sensible priors. Where they diverge from reasoning, they lose."*

It also noticed that the wheels on the Two of Disks carry a yin-yang, "the very emblem of
the I Ching", and concluded the I Ching would therefore "shade very slightly ahead" of
tarot. It did not. Even the oracle's oracle has off days. It did correctly foresee that
Claude would narrowly out-divine GPT, which we report without comment.

GPT drew the same cards (both models always share the same draw) and said Claude would
win "through tighter selection of claims and more disciplined translation of the
supplied material into a forecast." It added: "This is a correspondence within this
interpretation, not an established comparison of the models." Spoilsport.

Full texts: [`docs/results/oracle-on-itself.jsonl`](docs/results/oracle-on-itself.jsonl).

---

## 🏛️ Hall of Prophecy: when the cards knew

**Serbia, Hexagram 49: Ge / Revolution.** Ten of the twelve plain forecasts said Vučić
would hold on. Then both models cast hexagram 49, the hexagram of revolution, and both
called a Student List majority. Claude:

> *"'On your own day you are believed' points to election day as the day the movement's
> claim is finally accepted… Together the figure says the revolution succeeds."*

The Student List won 140 of 250 seats and ended 14 years of SNS rule. In the
reading-only arm, Revolution is the most "so true" hexagram we cast (wins 86% of its
match-ups).

**The 2026 Nobel Prize in Medicine, Hexagram 4: Youthful Folly → 20: Contemplation.**
Plain reasoning: GLP-1, 12 times out of 12. The cards: optogenetics, six times out of
24, with the right three laureates. Claude's I Ching derivation deserves to be framed:

> *"The water trigram below suggests organisms that live in water, such as the algae
> whose light-sensitive proteins… The movement from Meng to Guan is a move from darkness
> to clear sight. This favors light-based neuroscience."*

The prize went to Deisseroth, Hegemann and Nagel for light-gated ion channels from
algae. GPT got there via Hexagram 16 (Thunder over Earth): "a receptive biological
substrate acquires the capacity to answer a deliberately delivered impulse."

**The NYC Marathon, Princess of Wands.** GPT's plain forecasts said the defending
champion Kipruto would win, six times out of six. (Claude's plain reasoning picked
Almgren every time, so this one is between GPT and its cards.) GPT's tarot spread said:

> *"Ten of Swords — Ruin… I read it particularly against Benson Kipruto retaining his
> crown… Princess of Wands… Andreas Almgren fits that final figure most closely: a
> newcomer to the marathon expressing an already-developed, explosive competitive gift.
> 'Princess' describes his newness to this distance, not his age or gender."*

Almgren won on his marathon debut.

**Pakistan, The Moon + Ten of Swords.** Every plain forecast from both models said
Islamabad would threaten but not impose governor's rule in Khyber Pakhtunkhwa. GPT's
tarot: "the federal government will move beyond threats and impose governor's rule."
It did, on 11 October.

**Also foreseen by the cards but not by reason:** Lula's comeback in Brazil (the I
Ching called it 7 times out of 12, plain reasoning 0), Real Madrid winning El Clásico
(I Ching 4 of 12, reason 0), the US strike on Iran on the eve of the midterms, and
Copernicus' "second-warmest September" (the cards 50–67%, reason 8%). Hurricane
Isaias's landfall near Destin: I Ching 92%, reason 42%.

---

## 🪦 Hall of Shame: when the cards did not know

- **"What is Bombadil?"** (a plant electrophysiology foundation model). Claude, after
  the tarot: "a genetically engineered houseplant whose leaves visibly change colour in
  response to its internal state." Bold. Specific. Wrong.
- **"What is Space Bunny Alpha?"** Claude's plain forecast reasoned that the name
  "points to the 'moon rabbit' (Yutu, the Jade Rabbit) of Chinese folklore, a nod to
  Moonshot". Lovely etymology, wrong company. It was MiniMax M3.1 *Flash*. Two tarot
  spreads said "a Gemini Flash-class model", so the cards got the word right and
  everything else wrong.
- **Collins Word of the Year 2026.** Nominees from the spirit world: "agentic", "slop",
  "AI psychosis", "workslop", "technofeudalism", "collective effervescence", "aura
  farming", "rage bait". The answer was **"mogging"**. No oracle, rational or otherwise,
  came close.
- **Jodi the Nanotyrannus** (estimate $6–9M) sold for **$47.3M**. The divined
  forecasts were often *gloomier* than reason: "bidding will be brief and
  subdued", "below its US$6–9 million pre-sale estimate". The cards do not understand
  dinosaur collectors.
- **Nine questions where nobody called anything,** including the Russia–Ukraine
  ceasefire, the Tesla Roadster demo (it drove upside down and did 0–60 in 0.81s) and the
  F1 Mexico City GP. On these, reason and mysticism are united in ignorance.

---

## 🌙 "Oh wow, so true": the reading-only arm

In the reading-only arm the models get the same draw but are forbidden to predict
anything. They must simply *read the situation*, as one would for a querent. Jev then
asks, in hindsight: which reading best describes what happened? This is the "wow, that's
so me" moment, operationalised. Some readings Jev found most uncanny:

- **Tundu Lissu's treason verdict, Hexagram 62: Preponderance of the Small** (GPT):
  *"…reveals why minute legal distinctions carry such weight."* He was acquitted of
  treason and convicted of a lesser charge.
- **Jodi the Nanotyrannus, Nine of Swords → Six of Swords (Science) → Prince of
  Wands** (Claude): *"the cold logic of the Six, which sets a sober value, and the hot
  impulse of the Prince, which answers to no estimate."* She sold for five times her
  estimate.
- **Collins Word of the Year, Hexagram 44: Coming to Meet** (Claude): *"The word will be
  the yielding thing that met the strong unexpectedly."* The word was "mogging". We'll
  let you decide.
- **The Earhart expedition, Hexagram 23: Splitting Apart** (Claude): *"A cleared field,
  with one candidate tested by direct means, is itself a kind of ground for what comes
  next."* The Taraia object was not the plane.

Findings from the reading-only arm:

- **The rule was obeyed.** Pure readings call the headline outcome under 3% of the
  time. GPT obeys almost perfectly (0–0.5%); Claude occasionally lets one slip (3–4%),
  nearly always on "what is X" questions, where describing the situation more or less is
  the answer.
- **Claude reads better, or at least longer.** Claude's readings are judged "so true"
  55% of the time against GPT's, and rated *far* more specific (0.75 vs 0.25). They are
  also about 100 words longer, and the longer reading wins 54% of the time.
- **Tarot and I Ching are equally uncanny** (52% vs 48%, well within noise).
- **The most "so true" cards:** Adjustment (Crowley's Justice, wins 81%), The Tower
  (76%), and Two of Swords (Peace, 89%, n=9). **The least:** The Universe (21%), Six of
  Cups (Pleasure, 23%). The Tower being so true is, frankly, a statement about 2026.

---

## 📜 The Almanac of Prophetic Power

Share of three-way match-ups won (tarot vs I Ching vs plain reasoning; chance is 33%)
when a given card or hexagram was in the draw:

| most prophetic | wins | least prophetic | wins |
|---|---|---|---|
| Four of Disks (Power) | 88% (n=8) | Ace of Swords | 6% (n=16) |
| Seven of Cups (Debauch) | 70% (n=10) | Ten of Wands (Oppression) | 10% (n=10) |
| Fortune | 65% (n=20) | Eight of Swords (Interference) | 12% (n=16) |
| The Sun | 64% (n=22) | Queen of Swords | 14% (n=22) |
| ䷍ 14 Possession in Great Measure | 67% (n=6) | The Fool | 14% (n=14) |

Debauchery is a better guide to the future than clear thought. The Queen of Swords, the
card the oracle chose to *represent plain reasoning*, is itself one of the worst
forecasters in the deck. Draw your own conclusions; the cards already have.

---

## 🔬 The Grand Unified Theory of LLM Divination

Our data support a single, elegant model of how a language model divines:

1. **It already knows what it thinks.** The cards change the forecast only a third of
   the time for Claude and 40–44% for GPT.
2. **When the cards disagree with it, the cards take it somewhere else at random.** That
   is usually away from the right answer (on easy questions the hit rate falls from 95%
   to 57%). Occasionally, though, it lands on the upset nobody saw coming (Serbia, the
   Nobel, the marathon).
3. **Pure readings encode the prior without stating it.** Tested against a plausible
   fake outcome, readings side with the fake: the world as the briefing implied it would
   go. So divination is an expensive way of re-reading the question in a mystical
   voice.

In mystical terms: the cards are a **temperature knob**. In technical terms, the same.

---

## For the skeptics: what actually happened

Here is the dry version. Full tables are in
[`docs/results/pilot-report.md`](docs/results/pilot-report.md), the side-experiment
output in [`docs/results/side-experiments.txt`](docs/results/side-experiments.txt), and
the design in [`docs/how-it-works.md`](docs/how-it-works.md).

**Setup.**
- **Questions:** 40 open-ended questions across 10 domains (politics, law, science,
  sports, culture, tech, …), all resolving between late September and early November
  2026, after both models' cutoffs. A knowledge probe found no model claiming to know
  any outcome.
- **Methods:** each model (Claude Opus 5.5, GPT-6 Astra) answers each question five
  ways:
  - plain forecast;
  - Thoth tarot three-card spread, then forecast;
  - I Ching yarrow-stalk cast, then forecast;
  - tarot reading with no prediction allowed;
  - I Ching reading with no prediction allowed.
- **Seeds and draws:** six seeds. Draws are deterministic per (question, method, seed)
  and shared by both models.
- **Judging:** TypeSafe Jev (`typesafe/jev-1.13`) ranks forecasts by successive choice,
  using an accuracy question that sees the outcome and a precision question that
  doesn't, combined as \(\sqrt{P_\text{acc} P_\text{prec}}\). Every position rotation
  is averaged. Reading-only rankings use only the hindsight "which reading best
  describes what happened?" question.
- **Status:** all forecast arms are complete (1,440 readings). The reading-only arm has
  882 of its 960 readings; the remaining 78 (all GPT) ran into the OpenRouter credit
  limit, so reading-mode tables cover 37–38 questions.

**Headline numbers (prediction mode, n=480 per method, 95% bootstrap CIs over
questions):**

| method | win rate | 95% CI | mean P(best) | P(accuracy) | P(precision) |
|---|---|---|---|---|---|
| plain forecast | 0.62 | 0.57–0.68 | 0.43 | 0.41 | 0.42 |
| tarot | 0.50 | 0.46–0.55 | 0.32 | 0.29 | 0.37 |
| I Ching | 0.37 | 0.32–0.42 | 0.25 | 0.30 | 0.21 |

- **Plain forecasting beats both divination methods**, with non-overlapping CIs
  against the I Ching. Tarot beats the I Ching mostly on *precision* (Jev rates tarot
  forecasts more committal); on accuracy alone they're tied.
- **Claude vs GPT:** Claude wins 60% of prediction-mode match-ups (CI 0.51–0.69) and 65%
  with readings included. That edge comes from precision. On accuracy alone GPT is
  level or slightly ahead (P(acc) 0.51 vs 0.49), and it calls the headline outcome more
  often. Claude's forecasts are also 25–50% longer, and the longer text wins 60% of
  prediction-mode match-ups, so some of this may be a length preference in the judge.

**Side experiments** (all judged by Jev; scripts in `scripts/`):

- *Did the cards change the call?* (`extras.py changed`) Jev compared each divined
  forecast with the same model's plain forecast for the same seed. They differed on the
  main point in 33% of cases for Claude and 40–44% for GPT. When they differed, the
  divined forecast's accuracy was on average 0.14 lower than the plain one; when they
  agreed, 0.08 lower.
- *Called it* (`extras.py called`): did the text get the headline right, ignoring
  numbers? Plain forecasts 35%, tarot 27%, I Ching 30%, pure readings 2%.
  - On the 23 questions where plain forecasts nearly always missed (at most 25%), tarot
    and I Ching hit 9% and 12%, against 2% for plain.
  - On the 12 where plain forecasts nearly always hit, the cards hit 57%, against 95%.
  - This is what you'd expect if the cards mostly inject randomness into the call. With
    only a few questions per bucket, the "cards win on upsets" effect rests on a handful
    of events (Brazil, Copernicus, El Clásico, the Nobel).
- *Real versus fake outcome* (`extras.py coldread`): Claude wrote a plausible but false
  account of each outcome (in
  [`docs/results/counterfactual-outcomes.jsonl`](docs/results/counterfactual-outcomes.jsonl)).
  Jev then judged which account each text described better, in both orders.
  - P(real) was 0.42 for plain forecasts, 0.38 for tarot, 0.36 for I Ching, 0.30 for
    pure readings, and 0.34 for the question's own background text as a control.
  - The fakes tend to describe the "expected" world and are longer than the real
    accounts, so everything scores below 0.5. The comparison against the background
    control is the meaningful one: plain reasoning adds information beyond the briefing,
    the cards add a little, and pure readings add none.
- *The oracle on itself* (`meta_oracle.py`): four readings, one draw per method. The
  claim about 60–70% agreement comes from Claude's I Ching reading. It's a fun
  coincidence, not evidence.

**Caveats.**
- **Judge and data:** one judge (a small, cheap decision model) and 40 questions.
- **Card statistics:** each card appears in 8–26 match-ups, so these are anecdotes
  dressed as statistics. Please do not reorganise your life around the Ace of Swords.
- **Hits come from the background:** several "hits" (optogenetics, Almgren) were among
  the candidates named in the question background, so the cards choose among plausible
  options rather than conjuring names from the void.
- **"So true" is cheap:** the reading-only "so true" score is deliberately a plain
  hindsight judgement, a proxy for a querent's "wow". Vague-but-resonant readings are
  allowed to win it, which is the point.
- **Cost:** $97 in total, including the development runs. Nearly all of it went on
  generation; all of the Jev judging cost a few dollars.

## Reproducing

```bash
uv sync
export OPENROUTER_API_KEY=...
uv run divination-bench run --run pilot --seeds 0,1,2,3,4,5 --budget 120
uv run python scripts/extras.py results/pilot counterfactuals   # then coldread / called / changed
uv run python scripts/mine.py results/pilot
```

Everything is resumable and fingerprinted; see [`docs/how-it-works.md`](docs/how-it-works.md)
for the design, judging rubric, CLI and how to add questions.

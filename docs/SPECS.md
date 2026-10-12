# MCP for Health — "The Patient Advocate"

> Original brainstorm notes have been reorganized into a structured spec.
> Nothing removed — only grouped and clarified. Raw notes preserved in the Appendix.

## 1. Vision

**MCP for Health** is the glue that stitches a patient's healthcare journey
together. It is an **agentic advocate that stays with the patient**, carries
their story across visits, and delivers the missing context to clinicians at
the exact point of decision.

> "Everything that happens *outside* of the traditional clinical context is
> solved by this." — the **middle zones** between visits.

Anthropic is positioned to standardize this: a **unified language (MCP) for
entry into EHRs**, interoperable across model providers (Anthropic, OpenAI).

## 2. The Problem

- A patient's real story lives in fragments: phone calls with care teams,
  chatbot conversations, imaging, transcripts, sentiment — most of it lost
  between visits ("the middle zones").
- Clinicians (especially cardiologists & neurologists) start their reasoning
  from **imaging**; notes only augment their mental model of that imaging.
- Context that isn't digestible by an agent never reaches the clinician,
  so the right questions get asked too late.

## 3. The Value ("MCP for Health")

1. Brings **missing patient context** to the point of clinical decision.
2. Uses AI to help clinicians **ask the right questions sooner**.
3. **Carries conversations / encounters infinitely** across time.
4. Adds a **learning layer** that dynamically offers feedback based on:
   - what is being learned about the patient,
   - what best-in-class clinicians do,
   - where a clinician should prioritize (biggest opportunity to improve a
     patient's degree of engagement).

## 4. Core Capabilities (the Advocate agent)

- [ ] Pre-packaged and post-packaged context around each visit
- [ ] Organizes context for the physician visit (e.g. Abridge + physician)
- [ ] Stores and organizes longitudinal context
- [ ] Contextualizes, summarizes, and **"compresses" the patient's story
      between visits**
- [ ] Brings in (a) imaging and (b) tool calls to established systems
- [ ] Pre-packages context for the *next* specialist; co-registered imaging
      helps "clarify"

### Structured signals to extract from a call transcript
- Intent of the conversation
- Outcome of the conversation
- Degree the patient is **engaged** with their care
- Patient needs (social, medical, behavioral)
- Whether they trust their PCP
- Sentiment / affect
- **Journeys**: how these evolve over time

## 5. Demo Flow

```
Claude Conversation  ->  Package Context  ->  Clinician
```

Source data pulled into the package:
- Audio from calls with the care team
- Transcripts from those calls
- Imaging used for diagnoses (co-registered)

Plus an **authorization screen** before anything is shared.

**Demo storytelling:** show a synthetic patient story
**without** middle-zone context vs. **with** it — the delta is the pitch.

## 6. App Specification (v1 target)

A simple app that works on **both computer and phone (Android)**.

1. **Auth screen** → sign in with Google (with Claude Connector).
2. **Two-pane home screen:**

   **Conversations Pane** — focused on conversations (physicians, chatbots, etc.)
   - A box with a list of collapsible items, one per source:
     - **Phone conversations** → subitems: `transcript`, `affect`
     - **Chats** → pulls from Claude / ChatGPT

   **Anatomy Pane** — focused on anatomy
   - Starts from a template: **heart** or **brain**
   - Build on top of it with **patient-specific** overlays (imaging,
     literature maps, annotations)

3. **20 synthetic patient stories.** Start from a seed/zip → generate the
   synthetic stories ("patient stories in 4k / 8k" = high-fidelity detail).

## 7. Topics to Explore (roadmap / research)

- Federated learning
- Homomorphic cryptography
- Continual learning with a core model
- Data retention, data privacy & security (Apple-grade)
- Foundation models on imaging (JEPA / co-registration)
- DSPy.ai for the advocate's prompting/optimization

## 8. Non-negotiables

- **Private, safe data handling.** Safety is very important — this is real.
- Prototype must be solid enough to anchor on, because the work matters.

## 9. References

- Build Day hackathon winners:
  https://claude.com/blog/meet-the-winners-of-our-claude-opus-4-8-build-day-hackathon

---

## Appendix — Raw notes (verbatim, for provenance)

- patient stories in 4k / 8k
- Advocates. Anthropic is in a position to standardize.
- MCP for Health: Repo. This is the glue / Agentic advocate for the patient.
  "Dance" stitches things all together.
- Unified language for entry into EHRs (between Anthropic and OpenAI).
- Build a synthetic data set with known stories. WITHOUT middle zones vs WITH.
- During visit: compressed images + note.
- Utility for clinicians: Cardiologists and Neuro = heavy imaging centered;
  imaging is where their thought process starts.
- Private data, safety very important. Prototyper -> need to solidify/anchor.

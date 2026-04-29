# Loom Video Script: Agentic Music Recommender

**Target length:** 5 to 6 minutes
**Tool:** [loom.com](https://loom.com) (free tier is fine)

---

## What the rubric requires you to show

The rubric specifically calls out these four required demo beats:

1. ✅ End-to-end system run with 2 to 3 inputs
2. ✅ AI feature behavior (the agent doing its plan, act, check loop)
3. ✅ Reliability or guardrail or evaluation behavior
4. ✅ Clear outputs for each case

You don't need to show code setup, file structure, or installation. Skip those.

---

## Pre-recording checklist

Before you hit record, make sure:

- [ ] Your terminal is in the project directory
- [ ] `.env` has your real `ANTHROPIC_API_KEY`
- [ ] You have `python -m src.main` ready in your terminal history (just up-arrow)
- [ ] Architecture PNG is open in another window or tab so you can show it briefly
- [ ] Close Slack, email, anything that might pop a notification
- [ ] Increase your terminal font size so it's readable on video

---

## Script (with timing)

### 0:00 to 0:30 — Intro (30 seconds)

> "Hey, I'm Tesfa. This is my AI 110 final project. I took my Module 3 music recommender and extended it with an agentic workflow so you can talk to it in plain English instead of filling out a structured profile. Let me show you how it works."

**Show on screen:** README title or just your terminal.

### 0:30 to 1:30 — Demo case 1: clear request (60 seconds)

> "First case: a clear, energetic request."

**Run in terminal:**
```
python -m src.main "I'm running and need something upbeat"
```

> "What you're seeing happen here is the agent doing three things. First it sends my sentence to Claude Haiku to parse it into a structured profile, in this case probably high energy, pop or dance genre, happy mood. Then it hands that profile to my original Module 3 recommender, which scores all 18 songs and returns the top 5. Finally it sends those picks back to Claude and asks: how confident are you these match the request, on a scale of 0 to 1?"

**Point at the output:**
> "Confidence came back at [whatever it shows], the reasoning sentence explains why. And the top 5 songs are all in the high-energy pop range, which lines up."

### 1:30 to 2:30 — Demo case 2: different request (60 seconds)

> "Second case: a totally different vibe."

**Run in terminal:**
```
python -m src.main "chill lofi beats for studying"
```

> "Same agent, same pipeline, but the parsed profile this time is low energy, lofi, focused. The recommender scores against that profile and returns a completely different top 5. This is the same code path as before, just driven by a different request, which is the point: the agent gives the deterministic recommender a structured input, and the recommender does its thing."

**Point at the output:**
> "Confidence here is around [whatever], and the picks are all low-energy ambient or lofi tracks. That's the agent working as designed."

### 2:30 to 3:30 — Demo case 3: the guardrail demo (60 seconds)

> "Third case: this is the one I'm most proud of. I want to show what happens when the request is deliberately vague."

**Run in terminal:**
```
python -m src.main "I just want something good"
```

> "Watch the confidence score on this one. It's intentionally low, around 0.4 in my eval runs."

**Point at the output:**
> "Notice the agent doesn't pretend it understood. The reasoning sentence literally says the request is too vague to reliably match. This is a calibrated uncertainty signal. A lot of LLM-powered systems would just confidently spit out recommendations and act like they nailed it. I designed this one so the check step can push back and say no, I'm not sure. That feels like the more responsible default, even if it makes the demo less flashy."

### 3:30 to 4:30 — Reliability: eval harness (60 seconds)

> "Now for the reliability piece. I have a test harness that runs 8 fixed cases through the agent against the live API and prints a summary."

**Run in terminal:**
```
python -m tests.eval_harness
```

> "While this runs, you can see the structured logs scrolling: plan step, act step, check step for each case."

**When it finishes, point at the summary:**
> "7 out of 8 cases passed, average confidence 0.81. The one that failed was the sad late-night case. The agent's average song energy was 0.46 against a threshold of 0.45, so it missed by 0.01. The picks were defensible. I left the threshold tight on purpose because honestly, that's the kind of edge case worth thinking about, not papering over."

> "There's also a logs file written each run with the full trace, and the harness saves a results summary so I can compare runs over time."

### 4:30 to 5:30 — Architecture walkthrough (60 seconds)

**Switch to the architecture diagram.**

> "Quick architecture tour. The user request comes in, the agent runs three steps. Plan calls the LLM to parse to a profile. Act calls the original Module 3 recommender, which I didn't modify at all. Check calls the LLM again to rate confidence. If confidence is below 0.6, the agent re-plans once with extra context and retries."

> "The dotted lines are the eval harness and the logger. The harness sits outside the main flow and exercises the whole agent. The logger writes to console and to a log file so I can audit any run after the fact."

> "The big design decision here was wrap, don't rewrite. The original recommender is treated as a black-box tool the agent calls. That means all the original tests still pass, and the deterministic scoring logic stays independently testable."

### 5:30 to 6:00 — Reflection close (30 seconds)

> "What this project taught me is that the hard part of building AI systems isn't the AI part. It's deciding where to be strict, where to be lenient, where to retry, and where to fail loud. Mocked tests caught my control flow bugs in milliseconds. The live eval harness caught two real bugs the mocks couldn't have, including JSON markdown fences and a Windows encoding issue. Both layers earn their keep."

> "Code is on GitHub, full reflection is in the model card. Thanks for watching."

**End recording.**

---

## After recording

1. Trim the start and end if there's silence.
2. Get the share link from Loom.
3. Paste it into the README.md at the top, replacing the `[paste link here after recording]` placeholder.
4. Push the README change to GitHub.

## If your run differs from the script

The actual numbers (confidence values, which songs come back) will vary from run to run because the model is non-deterministic. Don't try to match the script word for word. Read your actual output and narrate what you see. The script is a structure, not a teleprompter.

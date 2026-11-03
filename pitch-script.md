# Fresh Eyes pitch script

One line per slide of `Fresh Eyes pitch deck.html`. Under four minutes, no em dashes. Say once, on slide 7 or 8,
that these are **simulated** neurons.

1. **Fresh Eyes:** "Fresh Eyes is a split brain for food: two hemispheres and a callosum that spot spoiling food
   without a single photo of rotten food."
2. **The problem:** "A third of food is wasted, and camera checks need thousands of rotten-food photos for every new
   product."
3. **A split brain for food:** "Like early vision, one hemisphere is silicon and sees sharp edges but no colour; the
   other is living neurons that see only colour and notice when it changes; a callosum joins their alarms."
4. **Neurons get used to the normal:** "Neurons naturally get used to what they see often and react to anything new,
   with no training."
5. **Colour picks the electrodes:** "Colour decides which electrodes we stimulate, always with exactly 12 pulses, so a
   bigger response can only mean change."
6. **What we built tonight:** "We built it on the organisers' simulator and added neuron adaptation, so the same code
   runs on a real CL1."
7. **The dish spots browning before any mould:** "A check is one look at the fruit, every two seconds, and spoiling
   takes 60 checks. The dish raised the alarm 12 checks into browning, when the fruit had only just started to turn;
   silicon needed 26, because it can only see the mould."
8. **Cut the callosum:** "Cut the link to the living hemisphere and the alarm waits for the mould: 26 checks, not 12.
   Lower is earlier."
9. **Why we trust it:** "A new fruit gets about twice the adapted response, every image gets the same 12 pulses, and
   with adaptation off the dish never fires, so this is change detection, not tiredness."
10. **What the dish taught us:** "Timing matters, the signal lives on the electrodes we stimulate, and this is one
    seed of simulated neurons with 4 false alarms in 40 on banana."
11. **New food, no new data:** "Switching to strawberry took 30 fresh checks and zero photos of rotten strawberries."
12. **The ask:** "The same script runs on a CL1 in about 9 minutes; give us one day to see if real neurons do what our
    simulated ones did, then teach the callosum how far to trust each hemisphere."

**If asked what "12 checks" means:** a check is one look at the fruit (one test image every 2 s). Spoiling runs 60
checks from the first hint of browning to full mould. The dish's first alarm came on check 12, about a fifth of the
way in; silicon's on check 26, when the mould spots appear. On strawberry the dish fired at 11. Lower is earlier.

Numbers come from `results.md` (scored run 1, seed 42, simulated culture).

---
marp: true
paginate: true
math: katex
footer: "A visual search advantage for illusory faces in objects (Keys et al., 2021)"
---

# Paper Reproduction: A Visual Search Advantage for Illusory Faces
## A visual search advantage for illusory faces in objects

**Presenter:** [Your Name]
**Date:** [Date]

---

## 1. Background & Core Question

- **The Visual Advantage of Real Faces**: The human visual system prioritizes face detection, allowing us to rapidly locate human faces in cluttered, complex scenes.
- **Face Pareidolia**: The phenomenon of mistakenly perceiving faces in inanimate objects (e.g., an electrical socket or a sliced bell pepper). Crucially, this occurs in the absence of typical low-level facial features (like skin color or specific face shapes).
- **The Core Research Question**:
  > Does this "illusory face" phenomenon in inanimate objects also confer a **visual search speed advantage** similar to that of real human faces?

---

## 2. Experiment 1: Search Among Homogeneous Distractors

**Objective**: To test whether illusory faces share a search advantage when placed among highly similar distractors.

- **Experimental Design**:
  - **Layout**: An invisible $8 \times 8$ grid, with Set Sizes of 16, 32, or 64.
  - **Targets**: Objects containing illusory faces vs. visually matched non-face objects.
  - **Distractors**: Non-face objects of the *same* category as the target (highly homogeneous).
- **Key Findings**:
  - Even though participants were simply instructed to find everyday objects (not "faces"), they located **objects containing illusory faces significantly faster** than their matched non-face counterparts.

<!-- Note: You can insert a screenshot of the Experiment 1 array from the paper here -->
<!-- ![bg right:40% fit](path/to/your/exp1_image.png) -->

---

## 3. Experiment 2: Direct Comparison with Real Faces

**Objective**: To lower the task difficulty and directly compare search efficiency between illusory faces and real human faces.

- **Experimental Design**:
  - **Layout**: Circular arrays with reduced Set Sizes of 4, 8, or 16.
  - **Targets**: Illusory face objects vs. matched non-face objects vs. **real human faces**.
  - **Distractors**: Heterogeneous (category-diverse) objects that did not match the target category.
- **Key Findings**:
  - Search speed and efficiency ranking: **Real Faces > Illusory Faces > Non-face Objects**.
  - The search advantage for illusory faces persisted, although it was less pronounced than the advantage for real human faces.

---

## 4. Reproduction Methodology & Tech Stack

This reproduction adheres to the experimental environment described in the original methodology.

- **Core Tools**: `MATLAB` + `Psychtoolbox-3` (PTB-3)
- **Experimental Parameters**:
  - **Fixation Cross**: 400~600 ms random jitter (using `WaitSecs` combined with `rand`).
  - **Target Presentation**: Maximum timeout set to 15,000 ms (via continuous `KbCheck` polling).
  - **Spatial Layout**: Based on a viewing distance of 40 cm, pixel dimensions were precisely calculated via trigonometry to ensure each stimulus subtended approximately $2^\circ \times 2^\circ$ of visual angle.
- **Trial Generation**: A pre-generated Condition Matrix was used to ensure the strict rule: "targets of the same object type never occur on consecutive trials."

---

## 5. Core Code Demonstration (PTB Layout Algorithm)

Below is the core MATLAB snippet used in Experiment 2 to generate the equidistant circular visual search array:
```matlab
function drawCircularArray(window, xCenter, yCenter, setSize)
    radius = 300; % Array radius (converted to pixels based on viewing distance)
    itemSize = 80; % Size of the individual stimulus
    
    % Calculate evenly distributed polar angles and convert to Cartesian coordinates
    angles = linspace(0, 2*pi, setSize + 1);
    angles(end) = []; 
    xCoords = xCenter + radius * cos(angles);
    yCoords = yCenter + radius * sin(angles);
    
    for i = 1:setSize
        rect = CenterRectOnPointd([0 0 itemSize itemSize], xCoords(i), yCoords(i));
        % In the actual experiment, Screen('DrawTexture', ...) is used here
        Screen('FillOval', window, [128 128 128], rect); 
    end
end
```

---

## 6. Conclusions & Takeaways

1. **A Broadly-Tuned Detection Mechanism**:
   The human brain's face-detection mechanism is highly tuned not only to real faces but to any diverse visual features that form a "face-like" geometric configuration.
2. **An Evolutionary Trade-off**:
   While this extreme sensitivity leads to "false positives" (face pareidolia), it is a highly beneficial trade-off. The cost of occasionally mistaking an object for a face is low, but the cost of missing a real face (a social partner or a threat) in a cluttered environment is high.
3. **Reproduction Insights**:
   - High temporal precision is critical, relying heavily on PTB's `Screen('Flip')` mechanisms.
   - The strict **yoked stimulus design** (matching targets directly to specific distractors) is the crucial element that makes this experimental paradigm successful.

---

<!-- _class: lead -->
# Thank You!
## Q & A 

Questions and discussions are welcome.
---
title: "Deep Learning Fundamentals: Neural Networks Before Transformers"
---

# Deep Learning Fundamentals: Neural Networks Before Transformers

[How LLMs Actually Work](../ai-llm/how-llms-actually-work.md) covers the
transformer architecture directly — but transformers are themselves
built from ideas (layers, weights, backpropagation, activation
functions) that originate in much simpler, older neural networks. This
page covers those fundamentals, plus the two architectures (CNNs,
RNNs) that solved image and sequence problems before transformers took
over both.

## 1. "What is a neural network, mechanically, at the smallest scale?"

**Answer:**

- The smallest unit, a **neuron** (or perceptron), does one simple
  thing: take several numeric inputs, multiply each by its own learned
  weight, sum them plus a bias term, and pass the result through an
  **activation function** — a single number out.
- A **layer** is many neurons doing this in parallel, each with its
  own weights, all looking at the same input. A network is multiple
  layers stacked: each layer's output becomes the next layer's input.
- Without an activation function, stacking layers would be
  mathematically pointless — a chain of purely linear operations
  collapses into a single equivalent linear operation, no matter how
  many layers deep. The activation function (historically sigmoid/tanh;
  almost universally **ReLU** — `max(0, x)` — in modern networks,
  since it's cheap to compute and avoids a problem covered in
  [§3](#3-backpropagation-and-the-vanishing-gradient-problem)) is what
  lets a deep network represent genuinely non-linear, complex
  relationships instead of just a fancier linear regression.
- "Deep" learning just means a network with enough stacked layers that
  each one can build on increasingly abstract features extracted by
  the ones before it — early layers in an image model learn edges,
  later layers learn shapes, the latest layers learn whole objects, all
  without anyone hand-specifying any of those intermediate concepts.

## 2. "How does a network actually learn its weights?"

**Answer:**

- Start with random weights, run a batch of training examples through
  the network (the **forward pass**), and compare the output to the
  correct answer using a **loss function** — a single number
  measuring how wrong the prediction was.
- **Backpropagation** then computes, for every single weight in the
  network, exactly how much that weight contributed to the final
  error — using the chain rule from calculus, working backward from
  the output layer to the input layer, one layer at a time (hence
  "back"-propagation).
- **Gradient descent** uses that per-weight error contribution (the
  **gradient**) to nudge every weight slightly in the direction that
  reduces the loss, by a step size called the **learning rate**.
  Repeat across many batches, many passes over the full dataset
  (**epochs**), and the weights gradually converge toward values that
  make the whole network's predictions accurate.
- **Interview point:** a learning rate that's too high overshoots past
  good weight values and can make training diverge entirely (loss gets
  *worse*, not better); too low converges so slowly that training
  takes impractically long, or gets stuck in a mediocre local
  solution. This is the single most commonly mistuned hyperparameter
  in deep learning, and "what happens if the learning rate is too
  high/low" is a near-guaranteed question.

## 3. Backpropagation and the Vanishing Gradient Problem

**Answer:**

- Because backpropagation multiplies gradients together layer by
  layer on the way backward, a *very* deep network can run into the
  **vanishing gradient problem**: if each layer's gradient contribution
  is a fraction less than 1 (which sigmoid/tanh activations tend to
  produce), multiplying many such fractions together across many
  layers shrinks the gradient toward zero by the time it reaches the
  earliest layers — those layers' weights barely update at all, and
  the network effectively stops learning from its earliest layers.
- **ReLU helps directly** — for positive inputs its gradient is a flat
  1, not a shrinking fraction, so it doesn't compound the same way
  sigmoid/tanh do across many layers. This is the real, practical
  reason ReLU (and its variants) became the default activation function
  once networks got deep.
- **Residual connections** (skip connections that let a layer's input
  bypass straight to a later layer, added to that layer's own output)
  are the other major fix — they give the gradient a direct, short path
  backward that doesn't have to pass through every intervening layer's
  multiplication, which is exactly what made training genuinely very
  deep networks (and, later, transformers — see
  [How LLMs Actually Work](../ai-llm/how-llms-actually-work.md)) practical at
  all.

## 4. Overfitting Controls: Dropout and Batch Normalization

**Answer:**

- **Dropout** randomly zeroes out a fraction of neurons' outputs on
  each training step (commonly 20–50%), forcing the rest of the
  network to not become overly reliant on any single neuron or small
  co-adapted group — a regularization technique in the same family as
  [L1/L2 regularization](regularization-and-hyperparameter-tuning.md#1-l1-vs-l2-regularization),
  just mechanically different. Dropout is turned off at inference time
  — the full network runs, just scaled to account for the neurons that
  were randomly dropped during training.
- **Batch normalization** normalizes a layer's outputs (zero mean,
  unit variance) across each training batch before passing them to the
  next layer — primarily a training-stability and training-speed
  technique (it keeps the scale of values flowing through the network
  consistent as weights change during training), with a regularizing
  side effect from the slight noise each batch's own statistics
  introduce.
- **Interview point:** these solve different problems despite both
  being near-universal in modern architectures — dropout fights
  overfitting directly; batch norm primarily fights *unstable/slow
  training*, and only secondarily helps generalization. Conflating them
  as "both just prevent overfitting" misses the actual reason each
  exists.

## 5. CNNs: Why Images Need a Different Architecture

**Answer:**

- A plain fully-connected layer treats every pixel as an independent
  input with its own weight — for even a modest image, that's millions
  of weights, and critically, it throws away the fact that nearby
  pixels are spatially related (an edge is a pattern across
  *neighboring* pixels, not an arbitrary combination of distant ones).
- A **convolutional layer** instead slides a small learned filter (a
  **kernel**, e.g. 3×3 pixels) across the whole image, applying the
  same small set of weights at every position — this directly encodes
  two assumptions that are true for images and false for arbitrary
  tabular data: **local patterns matter** (a filter only looks at a
  small neighborhood at a time) and **the same pattern can appear
  anywhere** (one filter, reused across the whole image, instead of a
  separate weight set per pixel position).
- Stacking convolutional layers builds the same increasing-abstraction
  hierarchy from [§1](#1-what-is-a-neural-network-mechanically-at-the-smallest-scale)
  — early layers detect edges and simple textures, later layers
  combine those into shapes, the latest layers combine shapes into
  whole recognizable objects.
- **Pooling layers** (commonly max-pooling) downsample between
  convolutional layers, keeping the strongest signal in each small
  region while reducing the spatial size — fewer parameters downstream,
  and a degree of tolerance to a pattern shifting slightly in position.

## 6. RNNs and LSTMs: Why Sequences Need a Different Architecture

**Answer:**

- A plain feedforward network has no concept of "order" or "what came
  before" — every input is processed independently. Text, audio, and
  time series are fundamentally sequential: the meaning of a word
  depends on the words before it.
- A **recurrent neural network (RNN)** processes a sequence one step
  at a time, carrying forward a **hidden state** — a running summary
  of everything seen so far — that gets updated at each new input and
  fed into the next step, letting earlier context influence how later
  inputs are interpreted.
- **The core weakness: long-range memory fades.** Because the hidden
  state is repeatedly overwritten and run back through the same
  vanishing-gradient-prone recurrence from [§3](#3-backpropagation-and-the-vanishing-gradient-problem),
  a plain RNN struggles to retain information from many steps earlier
  — the start of a long sentence effectively stops influencing the end
  of it.
- **LSTM (Long Short-Term Memory)** networks fix this with an explicit
  **memory cell** and learned **gates** (forget, input, output) that
  control exactly what information gets kept, overwritten, or passed
  through at each step — a far more deliberate, learnable mechanism for
  long-range memory than a plain RNN's hidden state alone.
- **Why transformers eventually displaced both:** RNNs/LSTMs process a
  sequence strictly step by step, which is inherently slow to train
  (can't parallelize across time steps) and still struggles with very
  long-range dependencies despite LSTM's gating. The transformer's
  **self-attention** mechanism (see
  [How LLMs Actually Work §3](../ai-llm/how-llms-actually-work.md#3-what-is-self-attention-and-why-is-it-the-mechanism-that-made-transformers-work))
  lets every position look directly at every other position in one
  parallelizable step, regardless of distance — solving both problems
  at once, which is the real reason it replaced RNNs/LSTMs as the
  default for sequence modeling.

| Architecture | Built for | Key idea | Still used today for |
|---|---|---|---|
| CNN | Images, spatial grids | Local filters, reused across position | Image classification, some audio/signal tasks, often as a feature extractor ahead of a transformer |
| RNN / LSTM | Sequences | A carried-forward hidden state / memory cell | Low-latency, strictly-online streaming tasks where a transformer's full-sequence attention isn't available |
| Transformer | Sequences (and now images, audio) | Self-attention — every position sees every other position directly | The default for nearly all large-scale language, and increasingly multimodal, tasks |

---

## Code Samples

No dedicated code samples for this page — it's architectural
background behind the transformer mechanics in
[How LLMs Actually Work](../ai-llm/how-llms-actually-work.md).

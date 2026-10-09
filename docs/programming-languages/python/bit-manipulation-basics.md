---
title: Bit Manipulation Basics
---

# Bit Manipulation Basics

Shifts and bitwise operators from first principles — not a common
day-to-day tool in application code, but a recurring interview topic
(flags, masks, classic "no extra space" problems) and the mechanism
behind why `n >> 1` shows up in binary search midpoints and
performance-sensitive code.

## 1. "Explain right shift (`>>`) and left shift (`<<`) — what are they actually doing?"

**Answer:**

- Every integer is stored as a sequence of bits. `2` in binary is
  `10`, `8` is `1000`, `5` is `101` — each position is a power of 2
  (rightmost = 2⁰, next = 2¹, next = 2², ...).
- `>>` and `<<` move every bit in that sequence right or left by N
  positions, filling the newly-empty spot(s) with `0`.
- `x >> n` is the same as `x // (2 ** n)` — integer (floor) division by
  a power of 2. `x << n` is the same as `x * (2 ** n)` — multiplication
  by a power of 2. Shifting is just a very fast way to multiply/divide
  by powers of two at the hardware level.
- **Both operators return a new value — they don't mutate the
  variable.** `a >> 1` leaves `a` completely unchanged unless
  reassigned (`a = a >> 1`, or the shorthand `a >>= 1`). This trips up
  almost everyone the first time:

```python
>>> a = 2        # binary: 10
>>> a >> 1       # shift every bit right, drop what falls off the edge: 10 -> 1
1
>>> a            # a was never reassigned
2
```

**A few more worked examples:**

```
8  >> 1   =  4      1000 -> 100
8  >> 2   =  2      1000 -> 10
8  >> 3   =  1      1000 -> 1
5  >> 1   =  2      101  -> 10     (the dropped "1" bit is just discarded)

1  << 1   =  2      1   -> 10
1  << 3   =  8      1   -> 1000
3  << 2   =  12     11  -> 1100
```

!!! example "Real-world analogy: sliding a row of lights"
    Picture a row of light bulbs, each either on or off, representing
    a number in binary. A right shift slides every bulb one socket to
    the right — whatever falls off the end is gone, and a fresh bulb
    (always off, `0`) appears at the start. Slide a lit bulb at
    position 4 one socket right, and it's now at position 3 — exactly
    like dividing its "value" (a power of 2) in half.

## 2. The other bitwise operators: `&`, `|`, `^`, `~`

**Answer:**

- **`&` (AND)** — each output bit is `1` only if *both* input bits are
  `1`. Used to check or clear specific bits.
- **`|` (OR)** — each output bit is `1` if *either* input bit is `1`.
  Used to set specific bits.
- **`^` (XOR)** — each output bit is `1` if the input bits *differ*.
  Used to toggle bits, and for its one famous property: `x ^ x == 0`
  and `x ^ 0 == x` for any `x`.
- **`~` (NOT)** — flips every bit. In Python, integers are
  conceptually infinite-precision with an infinite string of sign bits,
  so `~x` equals `-x - 1`, not a simple "flip the 8 bits" the way it
  would in a fixed-width language like C.

```python
>>> 0b1100 & 0b1010   # AND
8                      # 0b1000
>>> 0b1100 | 0b1010   # OR
14                     # 0b1110
>>> 0b1100 ^ 0b1010   # XOR
6                      # 0b0110
>>> ~5                # NOT
-6                     # Python ints: ~x == -x - 1
```

## 3. Bit flags: packing several on/off settings into one integer

**Answer:**

- Instead of four separate boolean fields, pack four independent
  settings into one integer, one bit each — the classic use case for
  shifts and bitwise operators together.

```python
READ    = 1 << 0   # 0b0001
WRITE   = 1 << 1   # 0b0010
EXECUTE = 1 << 2   # 0b0100
DELETE  = 1 << 3   # 0b1000

permissions = READ | WRITE          # set: combine flags with OR -> 0b0011

has_write = bool(permissions & WRITE)     # check: AND with the flag, non-zero means set
permissions |= EXECUTE                     # add a flag: OR it in
permissions &= ~WRITE                      # remove a flag: AND with its complement
permissions ^= READ                        # toggle a flag: XOR flips just that bit
```

!!! example "Real-world analogy: a panel of light switches"
    A permissions integer is one switch panel where each switch
    controls one independent feature — `READ`, `WRITE`, `EXECUTE`,
    `DELETE` are just labeled switches at fixed positions. `|` flips a
    switch on without touching the others; `&` with a flag checks one
    switch's position without needing to look at the rest; `^` toggles
    exactly one switch, whatever its current state; `& ~flag` flips
    exactly one off.

| Pros | Cons / Trade-offs |
|---|---|
| One integer instead of N boolean fields — compact, cheap to store/compare | Unreadable without named constants — `0b1011` means nothing without the flag definitions nearby |
| Checking/combining flags is a single fast bitwise op | Capped at the integer's bit width in fixed-width languages (not a practical limit in Python) |
| Common, recognizable pattern (Unix file permissions, HTTP header flags) | Easy to typo a shift amount and silently collide two flags on the same bit |

## 4. Classic interview problems this shows up in

**Answer:**

- **"Is `n` a power of two?"** — a power of two has exactly one bit
  set (`0b1000`, `0b0100`, ...). `n & (n - 1)` clears the lowest set
  bit; if `n` had only one bit set, the result is `0`.

```python
def is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0
```

- **"Find the single number that doesn't repeat"** — given an array
  where every number appears twice except one, find it without extra
  space. `x ^ x == 0` and XOR is commutative/associative, so XOR-ing
  every element cancels all the pairs, leaving only the unpaired one.

```python
def single_number(nums: list[int]) -> int:
    result = 0
    for n in nums:
        result ^= n
    return result
```

- **"Count the number of set bits (`1`s) in an integer"** — the
  classic "population count" problem.

```python
def count_set_bits(n: int) -> int:
    count = 0
    while n:
        n &= n - 1   # clears the lowest set bit each iteration
        count += 1
    return count
```

- **"Swap two variables without a temporary variable"** — a historical
  interview trick using XOR's self-canceling property (Python doesn't
  need this — tuple unpacking `a, b = b, a` already does it cleanly —
  but it's still asked to test whether XOR's properties are
  understood):

```python
a ^= b
b ^= a   # b is now original a
a ^= b   # a is now original b
```

- **Binary search midpoint**: `(l + r) >> 1` instead of `(l + r) // 2`
  — identical result for non-negative integers, occasionally asked to
  check whether a candidate recognizes `>>` as integer division by a
  power of 2 rather than something exotic.

**Interview point:** none of these need to be memorized as tricks in
isolation — each one falls out directly from the two properties above
(`x ^ x == 0`, and `n & (n - 1)` clears the lowest set bit). Knowing
*why* they work is what separates "recognizes the pattern" from
"recites a trick seen somewhere once."

---

## Code Samples

No dedicated code samples yet for this section — each snippet above is
short enough to run directly in a REPL.

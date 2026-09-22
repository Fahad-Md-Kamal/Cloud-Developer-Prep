---
title: "Sliding Window"
---

### 2.3 Sliding Window
-   **Pattern:** A technique for efficiently processing a contiguous subarray or substring. A "window" of a certain size slides over the data, and we reuse calculations from the previous step to optimize performance, typically from O(n^2) to O(n).

**Sliding Window Intuition:**

**The Core Idea:** Avoid recalculating from scratch for overlapping subarrays.

**Types:**
1. **Fixed size:** Window always same length (e.g., "max sum of k elements")
2. **Variable size:** Window grows/shrinks based on condition

**When to use:**
- Contiguous subarray/substring problems
- "Maximum/minimum in window"
- Need O(n) instead of O(n²)

#### 2.3.1 Best Time to Buy and Sell Stock
**Problem:** You are given an array `prices` where `prices[i]` is the price of a given stock on the `i`-th day. You want to maximize your profit by choosing a single day to buy one stock and choosing a different day in the future to sell that stock.

**Building Intuition:**

**Key Insight:** Track minimum price seen so far (best buy point) and calculate profit at each step.

**Not Sliding Window, but Related:** This is actually a **running minimum** problem.

**Example:** `prices = [7, 1, 5, 3, 6, 4]`
```
Day 0: price=7, min=7, profit=0
Day 1: price=1, min=1 (better!), profit=0
Day 2: price=5, min=1, profit=5-1=4 ✓
Day 3: price=3, min=1, profit=3-1=2
Day 4: price=6, min=1, profit=6-1=5 ✓
Day 5: price=4, min=1, profit=4-1=3

Max profit: 5
```

**Why This Approach?**
- Maintain running minimum (best buy so far)
- Calculate profit at each potential sell point
- One pass: O(n) time, O(1) space

**Solution:** This is a simple sliding window problem. We use two pointers, `left` (buy) and `right` (sell). We iterate the `right` pointer through the prices. If we find a price lower than our current `left` price, we move our `left` pointer to this new low. Otherwise, we calculate the potential profit and update our maximum profit.

**Pseudocode:**
```
INITIALIZE left = 0, right = 1  // left=buy, right=sell
INITIALIZE max_profit = 0
WHILE right < length of prices:
    IF prices[left] < prices[right]:
        profit = prices[right] - prices[left]
        max_profit = MAX(max_profit, profit)
    ELSE:
        left = right  // Found a lower buying price
    INCREMENT right
RETURN max_profit
```

**Implementation:**
```python
def max_profit(prices: list[int]) -> int:
    """
    Time: O(n) - A single pass through the array.
    Space: O(1) - Only two pointers are used.
    """
    l, r = 0, 1  # l=buy, r=sell
    max_p = 0
    while r < len(prices):
        if prices[l] < prices[r]:
            profit = prices[r] - prices[l]
            max_p = max(max_p, profit)
        else:
            l = r
        r += 1
    return max_p
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [7,1,5,3,6,4] | 5 | Buy at 1, sell at 6: profit = 5 |
| Decreasing | [7,6,4,3,1] | 0 | No profitable transaction possible |
| Single day | [5] | 0 | Cannot sell on same day |
| Multiple peaks | [2,4,1,7,5,11] | 10 | Buy at 1, sell at 11: profit = 10 |

#### 2.3.2 Longest Substring Without Repeating Characters
**Problem:** Given a string `s`, find the length of the longest substring without repeating characters.

**Solution:** We use a sliding window approach with a hash set to keep track of characters currently in our window. We expand the window by moving the `right` pointer. If we encounter a character that's already in our set, we shrink the window from the `left` until the duplicate is removed.

**Pseudocode:**
```
INITIALIZE empty set char_set
INITIALIZE left = 0, result = 0
FOR right from 0 to length of s:
    WHILE s[right] is in char_set:
        REMOVE s[left] from char_set
        INCREMENT left
    ADD s[right] to char_set
    result = MAX(result, right - left + 1)
RETURN result
```

**Implementation:**
```python
def length_of_longest_substring(s: str) -> int:
    """
    Time: O(n) - Each character is visited by the left and right pointers at most once.
    Space: O(min(n, m)) - Where n is the length of the string and m is the size of the character set.
    """
    char_set = set()
    l = 0
    res = 0
    for r in range(len(s)):
        while s[r] in char_set:
            char_set.remove(s[l])
            l += 1
        char_set.add(s[r])
        res = max(res, r - l + 1)
    return res
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | "abcabcbb" | 3 | Longest substring is "abc" with length 3 |
| All same | "bbbbb" | 1 | Longest substring is "b" with length 1 |
| No repeats | "pwwkew" | 3 | Longest substring is "wke" with length 3 |
| Empty string | "" | 0 | No characters, length is 0 |

#### 2.3.3 Longest Repeating Character Replacement
**Problem:** You are given a string `s` and an integer `k`. You can choose any character of the string and change it to any other uppercase English character. You can perform this operation at most `k` times. Return the length of the longest substring containing the same letter you can get after performing the operations.

**Solution:** The window is valid if `window_length - count(most_frequent_char) <= k`. We use a hash map to count character frequencies within the window. We expand the window with the `right` pointer. If the window becomes invalid, we shrink it from the `left`. We don't need to decrease the `max_freq` when shrinking, as we're only interested in finding a window larger than the current max.

**Pseudocode:**
```
INITIALIZE empty frequency map counts
INITIALIZE left = 0, max_freq = 0, result = 0
FOR right from 0 to length of s:
    INCREMENT counts[s[right]]
    max_freq = MAX(max_freq, counts[s[right]])
    
    // Check if current window is valid
    IF (right - left + 1) - max_freq > k:
        DECREMENT counts[s[left]]
        INCREMENT left
    
    result = MAX(result, right - left + 1)
RETURN result
```

**Implementation:**
```python
def character_replacement(s: str, k: int) -> int:
    """
    Time: O(n) - The pointers traverse the string once.
    Space: O(26) -> O(1) - The frequency map will hold at most 26 keys.
    """
    counts: dict[str, int] = {}
    l = 0
    max_freq = 0
    res = 0
    for r in range(len(s)):
        counts[s[r]] = counts.get(s[r], 0) + 1
        max_freq = max(max_freq, counts[s[r]])
        
        # Check if the current window is valid
        if (r - l + 1) - max_freq > k:
            counts[s[l]] -= 1
            l += 1
            
        res = max(res, r - l + 1)
    return res
```

**Trace Table:**
| Test Case | Input (s) | k | Output | Explanation |
|-----------|-----------|---|--------|-------------|
| Basic | "ABAB" | 2 | 4 | Replace both B's with A (or vice versa) |
| Longer | "AABABBA" | 1 | 4 | Replace one B in "AABA" or "ABBA" |
| All same | "AAAA" | 0 | 4 | No replacements needed |
| No replacements | "ABCD" | 0 | 1 | Can only take single character windows |

#### 2.3.4 Minimum Window Substring
**Problem:** Given two strings `s` and `t`, return the minimum window in `s` which will contain all the characters in `t`.

**Solution:** This is a more advanced sliding window problem.
1.  Use a hash map (`need`) to store the character counts of `t`.
2.  Use another map (`window`) to count characters in the current window of `s`.
3.  Expand the window with a `right` pointer. When a character from `t` is added, update `window`.
4.  Keep track of how many characters from `t` we have (`have`) and how many we need (`need_count`).
5.  Once `have == need_count`, the window is valid. Now, try to shrink it from the `left` to find the smallest possible valid window.
6.  When shrinking, if we remove a character that causes the window to become invalid, we stop shrinking and go back to expanding.

**Pseudocode:**
```
IF s is empty OR t is empty:
    RETURN empty string

INITIALIZE need = character count map of t
INITIALIZE window = empty map
INITIALIZE left = 0, have = 0, required = number of unique chars in t
INITIALIZE result = [-1, -1], result_length = infinity

FOR right from 0 to length of s:
    c = s[right]
    INCREMENT window[c]
    
    IF c in need AND window[c] == need[c]:
        INCREMENT have
    
    WHILE have == required:
        // Update result if current window is smaller
        IF (right - left + 1) < result_length:
            result = [left, right]
            result_length = right - left + 1
        
        // Shrink window from left
        c_left = s[left]
        DECREMENT window[c_left]
        IF c_left in need AND window[c_left] < need[c_left]:
            DECREMENT have
        INCREMENT left

RETURN substring from result[0] to result[1] if valid, else empty string
```

**Implementation:**
```python
def min_window(s: str, t: str) -> str:
    """
    Time: O(n + m) - Where n is len(s) and m is len(t).
    Space: O(m) - For the frequency maps.
    """
    if not t or not s:
        return ""

    need: dict[str, int] = {}
    for c in t:
        need[c] = need.get(c, 0) + 1

    window: dict[str, int] = {}
    l = 0
    have, required = 0, len(need)
    res, res_len = [-1, -1], float("infinity")

    for r in range(len(s)):
        c = s[r]
        window[c] = 1 + window.get(c, 0)

        if c in need and window[c] == need[c]:
            have += 1

        while have == required:
            if (r - l + 1) < res_len:
                res = [l, r]
                res_len = r - l + 1
            
            c_left = s[l]
            window[c_left] -= 1
            if c_left in need and window[c_left] < need[c_left]:
                have -= 1
            l += 1
            
    l, r = res
    return s[l : r + 1] if res_len != float("infinity") else ""
```

**Trace Table:**
| Test Case | Input (s) | Input (t) | Output | Explanation |
|-----------|-----------|-----------|--------|-------------|
| Basic | "ADOBECODEBANC" | "ABC" | "BANC" | Minimum window containing A, B, C |
| Single char | "a" | "a" | "a" | Entire string is the answer |
| Not found | "a" | "aa" | "" | Cannot find two 'a's in s |
| All chars | "ab" | "b" | "b" | Single character is sufficient |
        c = s[r]
        window[c] = 1 + window.get(c, 0)

        if c in need and window[c] == need[c]:
            have += 1

        while have == required:
            # Update our result
            if (r - l + 1) < res_len:
                res = [l, r]
                res_len = r - l + 1
            
            # Pop from the left of our window
            c_left = s[l]
            window[c_left] -= 1
            if c_left in need and window[c_left] < need[c_left]:
                have -= 1
            l += 1
            
    l, r = res
    return s[l : r + 1] if res_len != float("infinity") else ""
```

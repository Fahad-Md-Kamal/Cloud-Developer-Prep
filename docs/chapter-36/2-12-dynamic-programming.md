---
title: "Dynamic Programming"
---

### 2.12 Dynamic Programming
-   **Pattern:** Breaking down a problem into overlapping subproblems and storing their solutions to avoid redundant calculations. Key indicators: optimal substructure, overlapping subproblems.

**Dynamic Programming Intuition:**

**The Core Idea:** Solve each subproblem once, remember the answer.

**When to use DP:**
1. **Optimal substructure:** Solution to problem uses solutions to subproblems
2. **Overlapping subproblems:** Same subproblems solved multiple times
3. **Asking for:** "Maximum/minimum", "count ways", "is it possible"

**Two Approaches:**
1. **Top-down (Memoization):** Recursion + cache
2. **Bottom-up (Tabulation):** Build table from base cases

**DP Template:**
```python
# Define dp array/dict
dp = [base_case] * n

# Fill dp using recurrence relation
for i in range(n):
    dp[i] = function(dp[i-1], dp[i-2], ...)

return dp[n-1]  # or max(dp), etc.
```

**Common Patterns:**
- Fibonacci-like: `dp[i] = dp[i-1] + dp[i-2]`
- Min/max path: `dp[i][j] = arr[i][j] + min(dp[i-1][j], dp[i][j-1])`
- Knapsack: `dp[i][w] = max(don't take, take + dp[i-1][w-weight])`

#### 2.12.1 Climbing Stairs
**Problem:** You are climbing a staircase with `n` steps. You can climb 1 or 2 steps at a time. How many distinct ways can you climb to the top?

**Building Intuition:**

**Key Insight:** To reach step `n`, you must come from:
- Step `n-1` (take 1 step) OR
- Step `n-2` (take 2 steps)

**Therefore:** `ways(n) = ways(n-1) + ways(n-2)` ← Fibonacci!

**Example:** `n = 4`
```
Step 1: 1 way  [1]
Step 2: 2 ways [1+1, 2]
Step 3: 3 ways [1+1+1, 1+2, 2+1]
Step 4: 5 ways [1+1+1+1, 1+1+2, 1+2+1, 2+1+1, 2+2]
         ↑
      3 + 2 (from steps 3 and 2)
```

**Why DP?**
- Recursion alone: O(2ⁿ) exponential
- With memoization: O(n) linear
- Bottom-up: O(n) time, O(1) space

**Solution:** This is essentially the Fibonacci sequence! To reach step `n`, you must come from step `n-1` (1 step) or `n-2` (2 steps).

**Algorithm:**
- Base cases: `dp[1] = 1`, `dp[2] = 2`
- Recurrence: `dp[i] = dp[i-1] + dp[i-2]`
- Optimized to O(1) space using two variables

**Pseudocode:**
```
IF n <= 2:
    RETURN n

INITIALIZE prev2 = 1, prev1 = 2
FOR i from 3 to n:
    curr = prev1 + prev2
    prev2 = prev1
    prev1 = curr

RETURN prev1
```

**Implementation:**
```python
def climb_stairs(n: int) -> int:
    """
    Time: O(n) - Single pass
    Space: O(1) - Only store last two values
    """
    if n <= 2:
        return n
    
    prev2, prev1 = 1, 2
    for i in range(3, n + 1):
        curr = prev1 + prev2
        prev2, prev1 = prev1, curr
    
    return prev1
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Small n | 2 | 2 | Two ways: (1+1) or (2) |
| Medium n | 3 | 3 | Three ways: (1+1+1), (1+2), (2+1) |
| Larger n | 5 | 8 | Follows Fibonacci: 1,2,3,5,8 |
| Base case | 1 | 1 | Only one way: single step |

#### 2.12.2 Coin Change
**Problem:** Given an array of coin denominations and an amount, return the fewest number of coins needed to make up that amount. If impossible, return -1.

**Solution:** Build up solutions for all amounts from 0 to target.

**Algorithm:**
- `dp[i]` = minimum coins needed for amount `i`
- Base case: `dp[0] = 0` (0 coins for amount 0)
- For each amount, try each coin:
  - `dp[amount] = min(dp[amount], 1 + dp[amount - coin])`

**Why DP?** We reuse solutions for smaller amounts.

**Pseudocode:**
```
INITIALIZE dp = [infinity] * (amount + 1)
dp[0] = 0

FOR amt from 1 to amount:
    FOR each coin in coins:
        IF amt - coin >= 0:
            dp[amt] = MIN(dp[amt], 1 + dp[amt - coin])

IF dp[amount] != infinity:
    RETURN dp[amount]
ELSE:
    RETURN -1
```

**Implementation:**
```python
def coin_change(coins: list[int], amount: int) -> int:
    """
    Time: O(amount * len(coins))
    Space: O(amount) - For the DP array
    """
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0
    
    for amt in range(1, amount + 1):
        for coin in coins:
            if amt - coin >= 0:
                dp[amt] = min(dp[amt], 1 + dp[amt - coin])
    
    return dp[amount] if dp[amount] != float('inf') else -1
```

**Trace Table:**

| Test Case | Coins | Amount | Output | Explanation |
|-----------|-------|--------|--------|-------------|
| Basic | [1,2,5] | 11 | 3 | 5+5+1 = 11 (3 coins) |
| Not possible | [2] | 3 | -1 | Cannot make odd amount with coin of 2 |
| Zero amount | [1] | 0 | 0 | Zero coins for zero amount |
| Single coin | [1] | 2 | 2 | Two coins of value 1 |

#### 2.12.3 Longest Increasing Subsequence
**Problem:** Given an integer array `nums`, return the length of the longest strictly increasing subsequence.

**Solution:** For each position, track the length of the longest increasing subsequence ending at that position.

**Algorithm:**
- `dp[i]` = length of LIS ending at index `i`
- Base case: all `dp[i] = 1` (each element is a subsequence of length 1)
- For each `i`, check all previous `j < i`:
  - If `nums[j] < nums[i]`: `dp[i] = max(dp[i], dp[j] + 1)`

**Optimized solution:** Use binary search with patience sorting for O(n log n).

**Pseudocode:**
```
IF nums is empty:
    RETURN 0

INITIALIZE dp = [1] * length of nums

FOR i from 1 to length of nums:
    FOR j from 0 to i:
        IF nums[j] < nums[i]:
            dp[i] = MAX(dp[i], dp[j] + 1)

RETURN MAX(dp)
```

**Implementation:**
```python
def length_of_lis(nums: list[int]) -> int:
    """
    Time: O(n^2) - Nested loops
    Space: O(n) - For DP array
    """
    if not nums:
        return 0
    
    dp = [1] * len(nums)
    
    for i in range(1, len(nums)):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)
    
    return max(dp)

# Optimized O(n log n) solution using binary search
def length_of_lis_optimized(nums: list[int]) -> int:
    """
    Time: O(n log n) - Binary search for each element
    Space: O(n) - For the tails array
    """
    import bisect
    tails = []  # tails[i] = smallest tail of increasing subseq of length i+1
    
    for num in nums:
        pos = bisect.bisect_left(tails, num)
        if pos == len(tails):
            tails.append(num)
        else:
            tails[pos] = num
    
    return len(tails)
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [10,9,2,5,3,7,101,18] | 4 | LIS is [2,3,7,101] or [2,5,7,101] |
| All increasing | [1,2,3,4,5] | 5 | Entire array is LIS |
| All decreasing | [5,4,3,2,1] | 1 | No increasing subsequence > 1 |
| With duplicates | [1,3,6,7,9,4,10,5,6] | 6 | LIS is [1,3,4,5,6] or similar |

#### 2.12.4 Longest Common Subsequence
**Problem:** Given two strings `text1` and `text2`, return the length of their longest common subsequence.

**Solution:** 2D DP where `dp[i][j]` represents the LCS length for `text1[0:i]` and `text2[0:j]`.

**Algorithm:**
- If `text1[i-1] == text2[j-1]`: `dp[i][j] = 1 + dp[i-1][j-1]`
- Otherwise: `dp[i][j] = max(dp[i-1][j], dp[i][j-1])`

**Interpretation:** If characters match, extend the LCS. Otherwise, take the better of excluding one character from either string.

**Pseudocode:**
```
INITIALIZE m = length of text1, n = length of text2
INITIALIZE dp = 2D array of size (m+1) x (n+1) filled with 0

FOR i from 1 to m:
    FOR j from 1 to n:
        IF text1[i-1] == text2[j-1]:
            dp[i][j] = 1 + dp[i-1][j-1]
        ELSE:
            dp[i][j] = MAX(dp[i-1][j], dp[i][j-1])

RETURN dp[m][n]
```

**Implementation:**
```python
def longest_common_subsequence(text1: str, text2: str) -> int:
    """
    Time: O(m * n) - Fill the entire DP table
    Space: O(m * n) - For the DP table (can be optimized to O(min(m,n)))
    """
    m, n = len(text1), len(text2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                dp[i][j] = 1 + dp[i - 1][j - 1]
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    
    return dp[m][n]
```

**Trace Table:**

| Test Case | text1 | text2 | Output | Explanation |
|-----------|-------|-------|--------|-------------|
| Basic | "abcde" | "ace" | 3 | LCS is "ace" with length 3 |
| No common | "abc" | "def" | 0 | No common subsequence |
| Same strings | "abc" | "abc" | 3 | Entire string is LCS |
| Partial overlap | "abc" | "abc" | 3 | LCS includes all common chars |

#### 2.12.5 Word Break
**Problem:** Given a string `s` and a dictionary of words `wordDict`, return `true` if `s` can be segmented into a space-separated sequence of dictionary words.

**Solution:** Use DP where `dp[i]` represents whether `s[0:i]` can be segmented.

**Algorithm:**
- `dp[0] = True` (empty string can be segmented)
- For each position `i`, check all previous positions `j`:
  - If `dp[j]` is True and `s[j:i]` is in wordDict:
    - `dp[i] = True`

**Pseudocode:**
```
INITIALIZE word_set = set(wordDict)
INITIALIZE dp = [False] * (length of s + 1)
dp[0] = True

FOR i from 1 to length of s + 1:
    FOR j from 0 to i:
        IF dp[j] AND s[j:i] in word_set:
            dp[i] = True
            BREAK

RETURN dp[length of s]
```

**Implementation:**
```python
def word_break(s: str, wordDict: list[str]) -> bool:
    """
    Time: O(n^2 * m) where m is average word length (for substring comparison)
    Space: O(n) - For DP array
    """
    word_set = set(wordDict)
    dp = [False] * (len(s) + 1)
    dp[0] = True
    
    for i in range(1, len(s) + 1):
        for j in range(i):
            if dp[j] and s[j:i] in word_set:
                dp[i] = True
                break
    
    return dp[len(s)]
```

**Trace Table:**

| Test Case | s | wordDict | Output | Explanation |
|-----------|---|----------|--------|-------------|
| Basic | "leetcode" | ["leet","code"] | True | Can be segmented as "leet" + "code" |
| Reuse words | "applepenapple" | ["apple","pen"] | True | "apple" + "pen" + "apple" |
| Cannot segment | "catsandog" | ["cats","dog","sand","and","cat"] | False | Cannot form "catsandog" |
| Single word | "cars" | ["car","ca","rs"] | True | "ca" + "rs" = "cars" |

---

## 3. NeetCode 150: Additional Problems Beyond Blind 75

This section covers the additional 75 problems included in NeetCode 150, organized by the same pattern-based approach. These problems provide more practice with the core patterns and introduce some advanced variations.

### 3.1 Arrays & Hashing (Additional Problems)

#### 3.1.1 Encode and Decode Strings
**Problem:** Design an algorithm to encode a list of strings to a single string and decode it back to the original list.

**Solution:** Use a delimiter approach where we store the length of each string followed by a delimiter, then the string itself. This handles strings with special characters.

**Pseudocode:**
```
ENCODE:
    INITIALIZE result = ""
    FOR each string in strs:
        result += string_length + "#" + string
    RETURN result

DECODE:
    INITIALIZE result = []
    i = 0
    WHILE i < length of string:
        Find next "#" after position i
        length = substring from i to "#"
        string = substring of 'length' characters after "#"
        ADD string to result
        i = position after string
    RETURN result
```

**Implementation:**
```python
class Codec:
    def encode(self, strs: list[str]) -> str:
        """
        Encodes a list of strings to a single string.
        Time: O(n) where n is total length of all strings
        Space: O(n) for the result
        """
        result = ""
        for s in strs:
            result += str(len(s)) + "#" + s
        return result
    
    def decode(self, s: str) -> list[str]:
        """
        Decodes a single string to a list of strings.
        Time: O(n)
        Space: O(n)
        """
        result = []
        i = 0
        while i < len(s):
            # Find the delimiter
            j = i
            while s[j] != '#':
                j += 1
            length = int(s[i:j])
            # Extract the string of given length
            result.append(s[j + 1: j + 1 + length])
            i = j + 1 + length
        return result
```

**Trace Table:**

| Test Case | Input | Encoded | Decoded | Explanation |
|-----------|-------|---------|---------|-------------|
| Basic | ["hello","world"] | "5#hello5#world" | ["hello","world"] | Length prefix handles decoding |
| With delimiter | ["ab#cd","ef"] | "5#ab#cd2#ef" | ["ab#cd","ef"] | Handles strings containing "#" |
| Empty strings | ["","abc",""] | "0#3#abc0#" | ["","abc",""] | Empty strings encoded as 0# |

#### 3.1.2 Valid Sudoku
**Problem:** Determine if a 9x9 Sudoku board is valid. Only filled cells need to be validated.

**Solution:** Use three sets to track seen numbers: one for rows, one for columns, and one for 3x3 sub-boxes.

**Pseudocode:**
```
INITIALIZE sets for rows (9), columns (9), and boxes (9)
FOR each cell (r, c) in board:
    IF cell is not empty:
        num = cell value
        box_index = (r // 3) * 3 + (c // 3)
        IF num in rows[r] OR num in cols[c] OR num in boxes[box_index]:
            RETURN False
        ADD num to rows[r], cols[c], boxes[box_index]
RETURN True
```

**Implementation:**
```python
def is_valid_sudoku(board: list[list[str]]) -> bool:
    """
    Time: O(1) - Always 9x9 board = 81 cells
    Space: O(1) - Fixed size sets (max 9 numbers each)
    """
    rows = [set() for _ in range(9)]
    cols = [set() for _ in range(9)]
    boxes = [set() for _ in range(9)]  # index = (r//3) * 3 + (c//3)
    
    for r in range(9):
        for c in range(9):
            if board[r][c] == '.':
                continue
                
            num = board[r][c]
            box_key = (r // 3) * 3 + (c // 3)
            
            if (num in rows[r] or 
                num in cols[c] or 
                num in boxes[box_key]):
                return False
                
            rows[r].add(num)
            cols[c].add(num)
            boxes[box_key].add(num)
    
    return True
```

**Trace Table:**

| Test Case | Input Description | Output | Explanation |
|-----------|------------------|--------|-------------|
| Valid board | Standard partially filled valid board | True | No duplicates in rows/cols/boxes |
| Duplicate in row | Same number appears twice in one row | False | Violates row constraint |
| Duplicate in box | Same number in 3x3 sub-box | False | Violates box constraint |

### 3.2 Two Pointers (Additional Problems)

#### 3.2.1 Two Sum II - Input Array Is Sorted
**Problem:** Given a sorted array, find two numbers that add up to a target. Return their 1-indexed positions.

**Solution:** Use two pointers from both ends. Since array is sorted, we can eliminate half the search space each iteration.

**Pseudocode:**
```
INITIALIZE left = 0, right = length - 1
WHILE left < right:
    current_sum = numbers[left] + numbers[right]
    IF current_sum == target:
        RETURN [left + 1, right + 1]  // 1-indexed
    ELSE IF current_sum < target:
        left += 1
    ELSE:
        right -= 1
```

**Implementation:**
```python
def two_sum_sorted(numbers: list[int], target: int) -> list[int]:
    """
    Time: O(n) - Single pass with two pointers
    Space: O(1) - Only two pointers
    """
    l, r = 0, len(numbers) - 1
    
    while l < r:
        current_sum = numbers[l] + numbers[r]
        
        if current_sum == target:
            return [l + 1, r + 1]  # 1-indexed
        elif current_sum < target:
            l += 1
        else:
            r -= 1
    
    return []
```

**Trace Table:**

| Test Case | Input | Target | Output | Explanation |
|-----------|-------|--------|--------|-------------|
| Basic | [2,7,11,15] | 9 | [1,2] | 2 + 7 = 9 |
| Negative | [-1,0] | -1 | [1,2] | -1 + 0 = -1 |
| Large array | [2,3,4] | 6 | [1,3] | 2 + 4 = 6 |

#### 3.2.2 Trapping Rain Water
**Problem:** Given n non-negative integers representing elevation map where width of each bar is 1, compute how much water it can trap after raining.

**Solution:** Use two pointers. Water trapped at any position depends on the minimum of max heights to its left and right.

**Pseudocode:**
```
INITIALIZE left = 0, right = length - 1
INITIALIZE left_max = 0, right_max = 0, water = 0

WHILE left < right:
    IF height[left] < height[right]:
        IF height[left] >= left_max:
            left_max = height[left]
        ELSE:
            water += left_max - height[left]
        left += 1
    ELSE:
        IF height[right] >= right_max:
            right_max = height[right]
        ELSE:
            water += right_max - height[right]
        right -= 1

RETURN water
```

**Implementation:**
```python
def trap(height: list[int]) -> int:
    """
    Time: O(n) - Single pass with two pointers
    Space: O(1) - Only variables
    """
    if not height:
        return 0
    
    l, r = 0, len(height) - 1
    left_max, right_max = height[l], height[r]
    water = 0
    
    while l < r:
        if left_max < right_max:
            l += 1
            left_max = max(left_max, height[l])
            water += left_max - height[l]
        else:
            r -= 1
            right_max = max(right_max, height[r])
            water += right_max - height[r]
    
    return water
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [0,1,0,2,1,0,1,3,2,1,2,1] | 6 | Water trapped in valleys |
| No water | [3,2,1] | 0 | Descending, no water trapped |
| Valley | [3,0,2,0,4] | 7 | 2 + 3 + 1 + 1 = 7 units |

### 3.3 Sliding Window (Additional Problems)

#### 3.3.1 Permutation in String
**Problem:** Given two strings s1 and s2, return true if s2 contains a permutation of s1.

**Solution:** Use sliding window with character frequency matching.

**Pseudocode:**
```
INITIALIZE frequency map for s1
INITIALIZE window frequency map
INITIALIZE left = 0, matches = 0

FOR right from 0 to length of s2:
    Add s2[right] to window
    IF window[s2[right]] == s1_freq[s2[right]]:
        matches += 1
    
    IF window size == length of s1:
        IF matches == number of unique chars in s1:
            RETURN True
        
        Remove s2[left] from window
        IF needed, decrement matches
        left += 1

RETURN False
```

**Implementation:**
```python
def check_inclusion(s1: str, s2: str) -> bool:
    """
    Time: O(n) where n is length of s2
    Space: O(1) - At most 26 characters
    """
    if len(s1) > len(s2):
        return False

    s1_count: dict[str, int] = {}
    for ch in s1:
        s1_count[ch] = s1_count.get(ch, 0) + 1

    window_count: dict[str, int] = {}
    l = 0
    for r in range(len(s2)):
        window_count[s2[r]] = window_count.get(s2[r], 0) + 1

        if r - l + 1 > len(s1):
            left_char = s2[l]
            window_count[left_char] -= 1
            if window_count[left_char] == 0:
                del window_count[left_char]
            l += 1

        if window_count == s1_count:
            return True

    return False
```

**Trace Table:**

| Test Case | s1 | s2 | Output | Explanation |
|-----------|----|----|--------|-------------|
| Basic | "ab" | "eidbaooo" | True | "ba" is permutation of "ab" |
| No match | "ab" | "eidboaoo" | False | No permutation found |
| Same string | "abc" | "abc" | True | Entire string is permutation |

#### 3.3.2 Sliding Window Maximum
**Problem:** Given an array and an integer k, return max element in each sliding window of size k.

**Solution:** Use a deque to maintain indices of potentially maximum elements in decreasing order.

**Pseudocode:**
```
INITIALIZE deque for storing indices
INITIALIZE result array

FOR i from 0 to length of nums:
    // Remove indices outside window
    WHILE deque not empty AND deque[0] <= i - k:
        Remove from front
    
    // Remove smaller elements from back
    WHILE deque not empty AND nums[deque[-1]] < nums[i]:
        Remove from back
    
    ADD i to deque
    
    IF i >= k - 1:
        ADD nums[deque[0]] to result

RETURN result
```

**Implementation:**
```python
def max_sliding_window(nums: list[int], k: int) -> list[int]:
    """
    Time: O(n) - Each element added/removed once
    Space: O(k) - Monotonic queue stores at most k indices
    """
    result: list[int] = []
    q: list[int] = []  # stores indices in decreasing order of values
    head = 0  # logical front of the queue

    for i in range(len(nums)):
        if head < len(q) and q[head] <= i - k:
            head += 1

        while len(q) > head and nums[q[-1]] < nums[i]:
            q.pop()

        q.append(i)

        if i >= k - 1:
            result.append(nums[q[head]])

    return result
```

**Trace Table:**

| Test Case | nums | k | Output | Explanation |
|-----------|------|---|--------|-------------|
| Basic | [1,3,-1,-3,5,3,6,7] | 3 | [3,3,5,5,6,7] | Max in each window of 3 |
| Single element | [1] | 1 | [1] | Window size 1 |
| Descending | [9,8,7,6,5] | 3 | [9,8,7] | First element always max |

### 3.4 Stack (Additional Problems)

#### 3.4.1 Min Stack
**Problem:** Design a stack that supports push, pop, top, and retrieving the minimum element in constant time.

**Solution:** Use two stacks - one for values and one for tracking minimums.

**Pseudocode:**
```
CLASS MinStack:
    INITIALIZE main_stack = []
    INITIALIZE min_stack = []
    
    PUSH(val):
        ADD val to main_stack
        IF min_stack empty OR val <= min_stack[-1]:
            ADD val to min_stack
    
    POP():
        val = REMOVE from main_stack
        IF val == min_stack[-1]:
            REMOVE from min_stack
        RETURN val
    
    TOP():
        RETURN main_stack[-1]
    
    GET_MIN():
        RETURN min_stack[-1]
```

**Implementation:**
```python
class MinStack:
    def __init__(self):
        """
        All operations: O(1) time
        Space: O(n) - Two stacks
        """
        self.stack = []
        self.min_stack = []

    def push(self, val: int) -> None:
        self.stack.append(val)
        if not self.min_stack or val <= self.min_stack[-1]:
            self.min_stack.append(val)

    def pop(self) -> None:
        if self.stack:
            val = self.stack.pop()
            if val == self.min_stack[-1]:
                self.min_stack.pop()

    def top(self) -> int:
        return self.stack[-1] if self.stack else None

    def getMin(self) -> int:
        return self.min_stack[-1] if self.min_stack else None
```

**Trace Table:**

| Operations | Result | Explanation |
|------------|--------|-------------|
| push(-2), push(0), push(-3), getMin() | -3 | Minimum is -3 |
| pop(), top() | 0 | After pop, top is 0 |
| getMin() | -2 | Minimum is now -2 |

#### 3.4.2 Evaluate Reverse Polish Notation
**Problem:** Evaluate the value of an arithmetic expression in Reverse Polish Notation.

**Solution:** Use a stack. Push numbers, pop two operands for operators.

**Pseudocode:**
```
INITIALIZE stack = []

FOR each token in tokens:
    IF token is operator:
        b = POP from stack
        a = POP from stack
        result = APPLY operator to a and b
        PUSH result to stack
    ELSE:
        PUSH number to stack

RETURN stack[0]
```

**Implementation:**
```python
def eval_rpn(tokens: list[str]) -> int:
    """
    Time: O(n) - Process each token once
    Space: O(n) - Stack size
    """
    stack = []
    operators = {'+', '-', '*', '/'}
    
    for token in tokens:
        if token in operators:
            b = stack.pop()
            a = stack.pop()
            if token == '+':
                stack.append(a + b)
            elif token == '-':
                stack.append(a - b)
            elif token == '*':
                stack.append(a * b)
            else:  # division
                # Truncate toward zero
                stack.append(int(a / b))
        else:
            stack.append(int(token))
    
    return stack[0]
```

**Trace Table:**

| Test Case | tokens | Output | Explanation |
|-----------|--------|--------|-------------|
| Basic | ["2","1","+","3","*"] | 9 | ((2 + 1) * 3) = 9 |
| Division | ["4","13","5","/","+"] | 6 | (4 + (13 / 5)) = 6 |
| Negative | ["10","6","9","3","+","-11","*","/","*","17","+","5","+"] | 22 | Complex expression |

#### 3.4.3 Generate Parentheses
**Problem:** Given n pairs of parentheses, generate all combinations of well-formed parentheses.

**Solution:** Use backtracking, tracking count of open and close parentheses.

**Pseudocode:**
```
FUNCTION backtrack(current, open_count, close_count):
    IF length of current == 2 * n:
        ADD current to result
        RETURN
    
    IF open_count < n:
        backtrack(current + "(", open_count + 1, close_count)
    
    IF close_count < open_count:
        backtrack(current + ")", open_count, close_count + 1)

INITIALIZE result = []
backtrack("", 0, 0)
RETURN result
```

**Implementation:**
```python
def generate_parenthesis(n: int) -> list[str]:
    """
    Time: O(4^n / sqrt(n)) - Catalan number
    Space: O(n) - Recursion depth
    """
    result = []
    
    def backtrack(current, open_count, close_count):
        if len(current) == 2 * n:
            result.append(current)
            return
        
        if open_count < n:
            backtrack(current + "(", open_count + 1, close_count)
        
        if close_count < open_count:
            backtrack(current + ")", open_count, close_count + 1)
    
    backtrack("", 0, 0)
    return result
```

**Trace Table:**

| Test Case | n | Output | Explanation |
|-----------|---|--------|-------------|
| n=1 | 1 | ["()"] | Only one valid combination |
| n=2 | 2 | ["(())","()()"] | Two valid combinations |
| n=3 | 3 | ["((()))","(()())","(())()","()(())","()()()"] | Five valid combinations |

#### 3.4.4 Daily Temperatures
**Problem:** Given daily temperatures, return array where answer[i] is days until warmer temperature. If no warmer day, use 0.

**Solution:** Use monotonic decreasing stack storing indices.

**Pseudocode:**
```
INITIALIZE result = [0] * length
INITIALIZE stack = []

FOR i from 0 to length - 1:
    WHILE stack not empty AND temperatures[i] > temperatures[stack[-1]]:
        prev_index = POP from stack
        result[prev_index] = i - prev_index
    
    PUSH i to stack

RETURN result
```

**Implementation:**
```python
def daily_temperatures(temperatures: list[int]) -> list[int]:
    """
    Time: O(n) - Each index pushed/popped once
    Space: O(n) - Stack size
    """
    result = [0] * len(temperatures)
    stack = []  # stores indices
    
    for i, temp in enumerate(temperatures):
        while stack and temp > temperatures[stack[-1]]:
            prev_index = stack.pop()
            result[prev_index] = i - prev_index
        stack.append(i)
    
    return result
```

**Trace Table:**

| Test Case | temperatures | Output | Explanation |
|-----------|-------------|--------|-------------|
| Basic | [73,74,75,71,69,72,76,73] | [1,1,4,2,1,1,0,0] | Days until warmer |
| Decreasing | [90,80,70,60] | [0,0,0,0] | No warmer days |
| Increasing | [30,40,50,60] | [1,1,1,0] | Next day always warmer |

### 3.5 Binary Search (Additional Problems)

#### 3.5.1 Binary Search
**Problem:** Given a sorted array and a target value, return the index if target exists, otherwise return -1.

**Solution:** Classic binary search algorithm.

**Pseudocode:**
```
INITIALIZE left = 0, right = length - 1

WHILE left <= right:
    mid = (left + right) // 2
    IF nums[mid] == target:
        RETURN mid
    ELSE IF nums[mid] < target:
        left = mid + 1
    ELSE:
        right = mid - 1

RETURN -1
```

**Implementation:**
```python
def binary_search(nums: list[int], target: int) -> int:
    """
    Time: O(log n) - Binary search
    Space: O(1) - Only pointers
    """
    l, r = 0, len(nums) - 1
    
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            l = mid + 1
        else:
            r = mid - 1
    
    return -1
```

**Trace Table:**

| Test Case | nums | target | Output | Explanation |
|-----------|------|--------|--------|-------------|
| Found | [-1,0,3,5,9,12] | 9 | 4 | Element at index 4 |
| Not found | [-1,0,3,5,9,12] | 2 | -1 | Element doesn't exist |
| Single element | [5] | 5 | 0 | Found at index 0 |

#### 3.5.2 Search a 2D Matrix
**Problem:** Search for a target value in an m x n matrix. Integers in each row are sorted left to right, and the first integer of each row is greater than the last integer of the previous row.

**Solution:** Treat as 1D sorted array and use binary search.

**Pseudocode:**
```
IF matrix is empty:
    RETURN False

rows = number of rows
cols = number of columns
left = 0
right = rows * cols - 1

WHILE left <= right:
    mid = (left + right) // 2
    mid_value = matrix[mid // cols][mid % cols]
    
    IF mid_value == target:
        RETURN True
    ELSE IF mid_value < target:
        left = mid + 1
    ELSE:
        right = mid - 1

RETURN False
```

**Implementation:**
```python
def search_matrix(matrix: list[list[int]], target: int) -> bool:
    """
    Time: O(log(m*n)) - Binary search on m*n elements
    Space: O(1) - Only pointers
    """
    if not matrix or not matrix[0]:
        return False
    
    rows, cols = len(matrix), len(matrix[0])
    l, r = 0, rows * cols - 1
    
    while l <= r:
        mid = (l + r) // 2
        mid_val = matrix[mid // cols][mid % cols]
        
        if mid_val == target:
            return True
        elif mid_val < target:
            l = mid + 1
        else:
            r = mid - 1
    
    return False
```

**Trace Table:**

| Test Case | matrix | target | Output | Explanation |
|-----------|--------|--------|--------|-------------|
| Found | [[1,3,5,7],[10,11,16,20],[23,30,34,60]] | 3 | True | Element exists in first row |
| Not found | [[1,3,5,7],[10,11,16,20],[23,30,34,60]] | 13 | False | Element doesn't exist |

#### 3.5.3 Koko Eating Bananas
**Problem:** Koko loves bananas. There are n piles of bananas, each pile has a number of bananas. Koko can decide her eating speed k (bananas per hour). Return minimum k such that she can eat all bananas within h hours.

**Solution:** Binary search on eating speed. For each speed, check if it's possible to finish within h hours.

**Pseudocode:**
```
FUNCTION can_finish(piles, k, h):
    hours = 0
    FOR each pile in piles:
        hours += CEILING(pile / k)
    RETURN hours <= h

left = 1
right = MAX(piles)

WHILE left < right:
    mid = (left + right) // 2
    IF can_finish(piles, mid, h):
        right = mid
    ELSE:
        left = mid + 1

RETURN left
```

**Implementation:**
```python
import math

def min_eating_speed(piles: list[int], h: int) -> int:
    """
    Time: O(n log m) where n = len(piles), m = max(piles)
    Space: O(1)
    """
    def can_finish(k):
        hours = 0
        for pile in piles:
            hours += math.ceil(pile / k)
        return hours <= h
    
    l, r = 1, max(piles)
    
    while l < r:
        mid = (l + r) // 2
        if can_finish(mid):
            r = mid
        else:
            l = mid + 1
    
    return l
```

**Trace Table:**

| Test Case | piles | h | Output | Explanation |
|-----------|-------|---|--------|-------------|
| Basic | [3,6,7,11] | 8 | 4 | Eating at speed 4: 1+2+2+3=8 hours |
| Same as piles | [30,11,23,4,20] | 5 | 30 | One pile per hour |
| More time | [30,11,23,4,20] | 6 | 23 | Can eat slower |

### 3.6 Greedy Algorithms

Greedy algorithms make locally optimal choices at each step, hoping to find a global optimum. This pattern is useful for optimization problems.

#### 3.6.1 Maximum Subarray
**Problem:** Given an integer array nums, find the subarray with the largest sum and return its sum.

**Solution:** Kadane's Algorithm - at each position, decide whether to extend the current subarray or start a new one.

**Pseudocode:**
```
INITIALIZE max_sum = nums[0]
INITIALIZE current_sum = nums[0]

FOR i from 1 to length - 1:
    current_sum = MAX(nums[i], current_sum + nums[i])
    max_sum = MAX(max_sum, current_sum)

RETURN max_sum
```

**Implementation:**
```python
def max_sub_array(nums: list[int]) -> int:
    """
    Time: O(n) - Single pass
    Space: O(1) - Only variables
    """
    max_sum = nums[0]
    current_sum = nums[0]
    
    for i in range(1, len(nums)):
        current_sum = max(nums[i], current_sum + nums[i])
        max_sum = max(max_sum, current_sum)
    
    return max_sum
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [-2,1,-3,4,-1,2,1,-5,4] | 6 | Subarray [4,-1,2,1] has sum 6 |
| All negative | [-2,-1] | -1 | Best is single element -1 |
| All positive | [1,2,3,4] | 10 | Sum of all elements |

#### 3.6.2 Jump Game
**Problem:** Given an array where each element represents max jump length from that position, determine if you can reach the last index.

**Solution:** Greedy - track the farthest reachable position.

**Pseudocode:**
```
INITIALIZE max_reach = 0

FOR i from 0 to length - 1:
    IF i > max_reach:
        RETURN False
    max_reach = MAX(max_reach, i + nums[i])
    IF max_reach >= length - 1:
        RETURN True

RETURN True
```

**Implementation:**
```python
def can_jump(nums: list[int]) -> bool:
    """
    Time: O(n) - Single pass
    Space: O(1) - Only variables
    """
    max_reach = 0
    
    for i in range(len(nums)):
        if i > max_reach:
            return False
        max_reach = max(max_reach, i + nums[i])
        if max_reach >= len(nums) - 1:
            return True
    
    return True
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| Can reach | [2,3,1,1,4] | True | Jump path: 0->1->4 |
| Cannot reach | [3,2,1,0,4] | False | Stuck at index 3 (value 0) |
| Single element | [0] | True | Already at last index |

#### 3.6.3 Jump Game II
**Problem:** Given an array of non-negative integers nums, you are initially positioned at the first index. Each element represents maximum jump length. Return minimum number of jumps to reach the last index.

**Solution:** Greedy BFS approach - track the farthest we can reach with current number of jumps.

**Pseudocode:**
```
IF length <= 1:
    RETURN 0

INITIALIZE jumps = 0
INITIALIZE current_end = 0
INITIALIZE farthest = 0

FOR i from 0 to length - 2:
    farthest = MAX(farthest, i + nums[i])
    
    IF i == current_end:
        jumps += 1
        current_end = farthest
        
        IF current_end >= length - 1:
            BREAK

RETURN jumps
```

**Implementation:**
```python
def jump(nums: list[int]) -> int:
    """
    Time: O(n) - Single pass
    Space: O(1) - Only variables
    """
    if len(nums) <= 1:
        return 0
    
    jumps = 0
    current_end = 0
    farthest = 0
    
    for i in range(len(nums) - 1):
        farthest = max(farthest, i + nums[i])
        
        if i == current_end:
            jumps += 1
            current_end = farthest
            
            if current_end >= len(nums) - 1:
                break
    
    return jumps
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [2,3,1,1,4] | 2 | Jump 1->3->4 (2 jumps) |
| Single jump | [2,3,0,1,4] | 2 | Jump 0->1->4 |
| Multiple options | [1,2,1,1,1] | 3 | Minimum 3 jumps needed |

### 3.7 Intervals

Working with intervals requires sorting and tracking overlaps or gaps.

#### 3.7.1 Merge Intervals
**Problem:** Given array of intervals, merge all overlapping intervals.

**Solution:** Sort by start time, then merge if current overlaps with previous.

**Pseudocode:**
```
IF intervals empty:
    RETURN []

SORT intervals by start time
INITIALIZE result = [first interval]

FOR each interval in intervals[1:]:
    last_in_result = result[-1]
    
    IF interval.start <= last_in_result.end:
        last_in_result.end = MAX(last_in_result.end, interval.end)
    ELSE:
        ADD interval to result

RETURN result
```

**Implementation:**
```python
def merge(intervals: list[list[int]]) -> list[list[int]]:
    """
    Time: O(n log n) - Sorting dominates
    Space: O(n) - Result array
    """
    if not intervals:
        return []
    
    intervals.sort(key=lambda x: x[0])
    result = [intervals[0]]
    
    for interval in intervals[1:]:
        if interval[0] <= result[-1][1]:
            result[-1][1] = max(result[-1][1], interval[1])
        else:
            result.append(interval)
    
    return result
```

**Trace Table:**

| Test Case | intervals | Output | Explanation |
|-----------|-----------|--------|-------------|
| Basic | [[1,3],[2,6],[8,10],[15,18]] | [[1,6],[8,10],[15,18]] | [1,3] and [2,6] overlap |
| All overlap | [[1,4],[4,5]] | [[1,5]] | Merge all into one |
| No overlap | [[1,2],[3,4]] | [[1,2],[3,4]] | No overlaps |

#### 3.7.2 Insert Interval
**Problem:** Insert a new interval into sorted, non-overlapping intervals list.

**Solution:** Add intervals before, merge with overlapping, add intervals after.

**Pseudocode:**
```
INITIALIZE result = []
i = 0

// Add all intervals before newInterval
WHILE i < length AND intervals[i].end < newInterval.start:
    ADD intervals[i] to result
    i += 1

// Merge overlapping intervals
WHILE i < length AND intervals[i].start <= newInterval.end:
    newInterval.start = MIN(newInterval.start, intervals[i].start)
    newInterval.end = MAX(newInterval.end, intervals[i].end)
    i += 1
ADD newInterval to result

// Add remaining intervals
WHILE i < length:
    ADD intervals[i] to result
    i += 1

RETURN result
```

**Implementation:**
```python
def insert(intervals: list[list[int]], newInterval: list[int]) -> list[list[int]]:
    """
    Time: O(n) - Single pass through intervals
    Space: O(n) - Result array
    """
    result = []
    i = 0
    n = len(intervals)
    
    # Add all intervals before newInterval
    while i < n and intervals[i][1] < newInterval[0]:
        result.append(intervals[i])
        i += 1
    
    # Merge overlapping intervals
    while i < n and intervals[i][0] <= newInterval[1]:
        newInterval[0] = min(newInterval[0], intervals[i][0])
        newInterval[1] = max(newInterval[1], intervals[i][1])
        i += 1
    result.append(newInterval)
    
    # Add remaining intervals
    while i < n:
        result.append(intervals[i])
        i += 1
    
    return result
```

**Trace Table:**

| Test Case | intervals | newInterval | Output | Explanation |
|-----------|-----------|-------------|--------|-------------|
| Middle insert | [[1,3],[6,9]] | [2,5] | [[1,5],[6,9]] | Merges with [1,3] |
| No overlap | [[1,2],[3,5],[6,7],[8,10],[12,16]] | [4,8] | [[1,2],[3,10],[12,16]] | Merges [3,5],[6,7],[8,10] |
| Before all | [[3,5],[12,15]] | [1,2] | [[1,2],[3,5],[12,15]] | Inserted at start |

#### 3.7.3 Non-overlapping Intervals
**Problem:** Given array of intervals, find minimum number of intervals to remove to make the rest non-overlapping.

**Solution:** Sort by end time, greedily keep intervals that end earliest.

**Pseudocode:**
```
IF intervals length <= 1:
    RETURN 0

SORT intervals by end time
INITIALIZE count = 0
INITIALIZE prev_end = intervals[0].end

FOR i from 1 to length - 1:
    IF intervals[i].start < prev_end:
        count += 1  // Remove current interval
    ELSE:
        prev_end = intervals[i].end

RETURN count
```

**Implementation:**
```python
def erase_overlap_intervals(intervals: list[list[int]]) -> int:
    """
    Time: O(n log n) - Sorting
    Space: O(1) - Only variables
    """
    if len(intervals) <= 1:
        return 0
    
    intervals.sort(key=lambda x: x[1])
    count = 0
    prev_end = intervals[0][1]
    
    for i in range(1, len(intervals)):
        if intervals[i][0] < prev_end:
            count += 1
        else:
            prev_end = intervals[i][1]
    
    return count
```

**Trace Table:**

| Test Case | intervals | Output | Explanation |
|-----------|-----------|--------|-------------|
| Basic | [[1,2],[2,3],[3,4],[1,3]] | 1 | Remove [1,3] |
| All overlap | [[1,2],[1,2],[1,2]] | 2 | Remove 2 intervals |
| No overlap | [[1,2],[2,3]] | 0 | No removals needed |

### 3.8 Bit Manipulation

Bit manipulation uses bitwise operations for efficient solutions.

#### 3.8.1 Single Number
**Problem:** Given a non-empty array where every element appears twice except one, find that single element.

**Solution:** XOR all elements. Duplicates cancel out (x ^ x = 0), leaving the single element.

**Pseudocode:**
```
INITIALIZE result = 0

FOR each num in nums:
    result = result XOR num

RETURN result
```

**Implementation:**
```python
def single_number(nums: list[int]) -> int:
    """
    Time: O(n) - Single pass
    Space: O(1) - Only one variable
    """
    result = 0
    for num in nums:
        result ^= num
    return result
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [2,2,1] | 1 | 1 appears once |
| Longer | [4,1,2,1,2] | 4 | 4 is the single number |
| Negative | [-1,-1,2] | 2 | Works with negatives |

#### 3.8.2 Number of 1 Bits
**Problem:** Write a function that takes unsigned integer and returns number of '1' bits (Hamming weight).

**Solution:** Use Brian Kernighan's algorithm or check each bit.

**Pseudocode:**
```
INITIALIZE count = 0

WHILE n > 0:
    count += 1
    n = n AND (n - 1)  // Removes rightmost 1 bit

RETURN count
```

**Implementation:**
```python
def hamming_weight(n: int) -> int:
    """
    Time: O(k) where k is number of 1 bits
    Space: O(1)
    """
    count = 0
    while n:
        count += 1
        n &= (n - 1)  # Removes rightmost 1 bit
    return count
```

**Trace Table:**

| Test Case | n (binary) | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic | 11 (1011) | 3 | Three 1 bits |
| Power of 2 | 8 (1000) | 1 | One 1 bit |
| All ones | 15 (1111) | 4 | Four 1 bits |

#### 3.8.3 Counting Bits
**Problem:** Given integer n, return array ans of length n + 1 such that for each i (0 <= i <= n), ans[i] is the number of 1's in binary representation of i.

**Solution:** Use DP. ans[i] = ans[i >> 1] + (i & 1)

**Pseudocode:**
```
INITIALIZE result = [0] * (n + 1)

FOR i from 1 to n:
    result[i] = result[i >> 1] + (i AND 1)

RETURN result
```

**Implementation:**
```python
def count_bits(n: int) -> list[int]:
    """
    Time: O(n) - Single pass
    Space: O(n) - Result array
    """
    result = [0] * (n + 1)
    for i in range(1, n + 1):
        result[i] = result[i >> 1] + (i & 1)
    return result
```

**Trace Table:**

| Test Case | n | Output | Explanation |
|-----------|---|--------|-------------|
| Small | 2 | [0,1,1] | 0:0 bits, 1:1 bit, 2:1 bit |
| Medium | 5 | [0,1,1,2,1,2] | Binary counts for 0-5 |
| Power of 2 | 4 | [0,1,1,2,1] | Pattern visible |

#### 3.8.4 Missing Number
**Problem:** Given array nums containing n distinct numbers in range [0, n], return the only number in the range that is missing.

**Solution:** XOR all numbers and indices, or use sum formula.

**Pseudocode:**
```
INITIALIZE result = length of nums

FOR i from 0 to length - 1:
    result = result XOR i XOR nums[i]

RETURN result
```

**Implementation:**
```python
def missing_number(nums: list[int]) -> int:
    """
    Time: O(n) - Single pass
    Space: O(1) - Only variables
    """
    result = len(nums)
    for i in range(len(nums)):
        result ^= i ^ nums[i]
    return result

# Alternative: Using sum formula
def missing_number_sum(nums: list[int]) -> int:
    """
    Time: O(n)
    Space: O(1)
    """
    n = len(nums)
    expected_sum = n * (n + 1) // 2
    actual_sum = sum(nums)
    return expected_sum - actual_sum
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [3,0,1] | 2 | Missing 2 from [0,1,2,3] |
| Missing last | [0,1] | 2 | Missing last element |
| Missing first | [1,2] | 0 | Missing first element |

### 3.9 Linked List Additional

Additional linked list problems requiring advanced pointer manipulation.

#### 3.9.1 Copy List with Random Pointer
**Problem:** Deep copy a linked list where each node has a next and random pointer.

**Solution:** Three-pass approach: interweave nodes, copy random pointers, separate lists.

**Pseudocode:**
```
// Pass 1: Create interweaved list
current = head
WHILE current:
    copy = NEW Node(current.val)
    copy.next = current.next
    current.next = copy
    current = copy.next

// Pass 2: Copy random pointers
current = head
WHILE current:
    IF current.random:
        current.next.random = current.random.next
    current = current.next.next

// Pass 3: Separate lists
dummy = NEW Node(0)
current = head
copy_current = dummy
WHILE current:
    copy_current.next = current.next
    current.next = current.next.next
    current = current.next
    copy_current = copy_current.next

RETURN dummy.next
```

**Implementation:**
```python
class Node:
    def __init__(self, val: int, next: 'Node' = None, random: 'Node' = None):
        self.val = val
        self.next = next
        self.random = random

def copy_random_list(head: 'Node') -> 'Node':
    """
    Time: O(n) - Three passes
    Space: O(1) - In-place modifications
    """
    if not head:
        return None
    
    # Pass 1: Interweave original and copied nodes
    current = head
    while current:
        copy = Node(current.val, current.next)
        current.next = copy
        current = copy.next
    
    # Pass 2: Copy random pointers
    current = head
    while current:
        if current.random:
            current.next.random = current.random.next
        current = current.next.next
    
    # Pass 3: Separate lists
    dummy = Node(0)
    current = head
    copy_current = dummy
    while current:
        copy_current.next = current.next
        current.next = current.next.next
        current = current.next
        copy_current = copy_current.next
    
    return dummy.next
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| With random | [[7,null],[13,0],[11,4],[10,2],[1,0]] | Deep copy with all pointers | Each node copied with random links |
| No random | [[1,null],[2,null]] | [[1,null],[2,null]] | Linear list without random |
| Empty | null | null | Handle empty list |

#### 3.9.2 Add Two Numbers
**Problem:** Add two numbers represented by linked lists (digits in reverse order).

**Solution:** Traverse both lists simultaneously, tracking carry.

**Pseudocode:**
```
dummy = NEW Node(0)
current = dummy
carry = 0

WHILE l1 OR l2 OR carry:
    val1 = l1.val IF l1 ELSE 0
    val2 = l2.val IF l2 ELSE 0
    
    total = val1 + val2 + carry
    carry = total // 10
    current.next = NEW Node(total % 10)
    
    current = current.next
    l1 = l1.next IF l1 ELSE None
    l2 = l2.next IF l2 ELSE None

RETURN dummy.next
```

**Implementation:**
```python
def add_two_numbers(l1: ListNode, l2: ListNode) -> ListNode:
    """
    Time: O(max(n, m)) - Traverse both lists
    Space: O(max(n, m)) - Result list
    """
    dummy = ListNode(0)
    current = dummy
    carry = 0
    
    while l1 or l2 or carry:
        val1 = l1.val if l1 else 0
        val2 = l2.val if l2 else 0
        
        total = val1 + val2 + carry
        carry = total // 10
        current.next = ListNode(total % 10)
        
        current = current.next
        l1 = l1.next if l1 else None
        l2 = l2.next if l2 else None
    
    return dummy.next
```

**Trace Table:**

| Test Case | l1 | l2 | Output | Explanation |
|-----------|----|----|--------|-------------|
| Basic | [2,4,3] | [5,6,4] | [7,0,8] | 342 + 465 = 807 |
| Carry | [9,9,9] | [1] | [0,0,0,1] | 999 + 1 = 1000 |
| Different lengths | [9,9] | [1] | [0,0,1] | 99 + 1 = 100 |

#### 3.9.3 LRU Cache
**Problem:** Design a data structure that supports get and put operations in O(1) time with a capacity limit.

**Solution:** HashMap + Doubly Linked List for O(1) access and removal.

**Pseudocode:**
```
CLASS LRUCache:
    INITIALIZE capacity, cache (dict), head, tail (dummy nodes)
    
    METHOD get(key):
        IF key NOT in cache:
            RETURN -1
        node = cache[key]
        REMOVE node from list
        ADD node to head
        RETURN node.value
    
    METHOD put(key, value):
        IF key in cache:
            REMOVE cache[key] from list
        
        node = NEW Node(key, value)
        cache[key] = node
        ADD node to head
        
        IF cache size > capacity:
            lru = REMOVE tail.prev
            DELETE cache[lru.key]
```

**Implementation:**
```python
class Node:
    def __init__(self, key: int = 0, val: int = 0):
        self.key = key
        self.val = val
        self.prev = None
        self.next = None

class LRUCache:
    """
    Time: O(1) for both get and put
    Space: O(capacity)
    """
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}
        self.head = Node()
        self.tail = Node()
        self.head.next = self.tail
        self.tail.prev = self.head
    
    def _remove(self, node: Node):
        node.prev.next = node.next
        node.next.prev = node.prev
    
    def _add_to_head(self, node: Node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node
    
    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        node = self.cache[key]
        self._remove(node)
        self._add_to_head(node)
        return node.val
    
    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self._remove(self.cache[key])
        
        node = Node(key, value)
        self.cache[key] = node
        self._add_to_head(node)
        
        if len(self.cache) > self.capacity:
            lru = self.tail.prev
            self._remove(lru)
            del self.cache[lru.key]
```

**Trace Table:**

| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic | put(1,1), put(2,2), get(1), put(3,3), get(2) | [null,null,1,null,-1] | Key 2 evicted |
| Full capacity | put(1,1), put(2,2), put(3,3), get(1), put(4,4), get(2) | [null,null,null,1,null,-1] | LRU eviction |
| Update | put(1,1), put(1,2), get(1) | [null,null,2] | Update value |

### 3.10 Trees Additional

Advanced tree problems requiring complex traversal and manipulation.

#### 3.10.1 Binary Tree Right Side View
**Problem:** Return the values of the nodes you can see ordered from top to bottom when looking from the right side.

**Solution:** Level-order traversal (BFS), capturing last node at each level.

**Pseudocode:**
```
IF root is None:
    RETURN []

result = []
queue = [root]

WHILE queue not empty:
    level_size = length of queue
    
    FOR i from 0 to level_size - 1:
        node = DEQUEUE
        
        IF i == level_size - 1:
            ADD node.val to result
        
        IF node.left:
            ENQUEUE node.left
        IF node.right:
            ENQUEUE node.right

RETURN result
```

**Implementation:**
```python
def right_side_view(root: TreeNode) -> list[int]:
    """
    Time: O(n) - Visit each node once
    Space: O(w) - Queue width (max level width)
    """
    if not root:
        return []

    result: list[int] = []
    queue: list[TreeNode] = [root]
    head = 0

    while head < len(queue):
        level_size = len(queue) - head
        for i in range(level_size):
            node = queue[head]
            head += 1

            if i == level_size - 1:
                result.append(node.val)

            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)

    return result
```

**Trace Table:**

| Test Case | Tree | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [1,2,3,null,5,null,4] | [1,3,4] | Right side view |
| Left only | [1,2] | [1,2] | Go to left when no right |
| Single | [1] | [1] | Single node |

#### 3.10.2 Count Good Nodes in Binary Tree
**Problem:** Count nodes where no node in path from root has greater value.

**Solution:** DFS with maximum value tracker.

**Pseudocode:**
```
FUNCTION count_good_nodes(root):
    RETURN dfs(root, root.val)

FUNCTION dfs(node, max_so_far):
    IF node is None:
        RETURN 0
    
    count = 1 IF node.val >= max_so_far ELSE 0
    new_max = MAX(max_so_far, node.val)
    
    count += dfs(node.left, new_max)
    count += dfs(node.right, new_max)
    
    RETURN count
```

**Implementation:**
```python
def good_nodes(root: TreeNode) -> int:
    """
    Time: O(n) - Visit each node once
    Space: O(h) - Recursion stack height
    """
    def dfs(node: TreeNode, max_val: int) -> int:
        if not node:
            return 0
        
        count = 1 if node.val >= max_val else 0
        max_val = max(max_val, node.val)
        
        count += dfs(node.left, max_val)
        count += dfs(node.right, max_val)
        
        return count
    
    return dfs(root, root.val)
```

**Trace Table:**

| Test Case | Tree | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [3,1,4,3,null,1,5] | 4 | Nodes 3,4,3,5 are good |
| All good | [3,3,null,4,2] | 3 | All on left path are good |
| Root only | [1] | 1 | Single node is good |

#### 3.10.3 Lowest Common Ancestor of Binary Tree
**Problem:** Find the lowest common ancestor of two given nodes.

**Solution:** Recursive DFS - LCA is where both nodes are found in different subtrees.

**Pseudocode:**
```
FUNCTION lca(root, p, q):
    IF root is None OR root == p OR root == q:
        RETURN root
    
    left = lca(root.left, p, q)
    right = lca(root.right, p, q)
    
    IF left AND right:
        RETURN root
    
    RETURN left IF left ELSE right
```

**Implementation:**
```python
def lowest_common_ancestor(root: TreeNode, p: TreeNode, q: TreeNode) -> TreeNode:
    """
    Time: O(n) - Visit each node once
    Space: O(h) - Recursion stack
    """
    if not root or root == p or root == q:
        return root
    
    left = lowest_common_ancestor(root.left, p, q)
    right = lowest_common_ancestor(root.right, p, q)
    
    if left and right:
        return root
    
    return left if left else right
```

**Trace Table:**

| Test Case | Tree | p | q | Output | Explanation |
|-----------|------|---|---|--------|-------------|
| Siblings | [3,5,1,6,2,0,8] | 5 | 1 | 3 | Root is LCA |
| Parent-child | [3,5,1,6,2,0,8] | 5 | 2 | 5 | Parent is LCA |
| Deep | [3,5,1,6,2,0,8] | 6 | 2 | 5 | Common parent |

#### 3.10.4 Serialize and Deserialize Binary Tree
**Problem:** Design algorithm to serialize and deserialize a binary tree.

**Solution:** Pre-order traversal with null markers.

**Pseudocode:**
```
FUNCTION serialize(root):
    IF root is None:
        RETURN "null"
    
    result = [root.val]
    result.append(serialize(root.left))
    result.append(serialize(root.right))
    RETURN JOIN result with ","

FUNCTION deserialize(data):
    values = SPLIT data by ","
    index = [0]
    
    FUNCTION build():
        IF values[index[0]] == "null":
            index[0] += 1
            RETURN None
        
        node = NEW TreeNode(values[index[0]])
        index[0] += 1
        node.left = build()
        node.right = build()
        RETURN node
    
    RETURN build()
```

**Implementation:**
```python
def serialize(root: TreeNode) -> str:
    """
    Time: O(n) - Visit each node
    Space: O(n) - Result string
    """
    if not root:
        return "null"
    
    return f"{root.val},{serialize(root.left)},{serialize(root.right)}"

def deserialize(data: str) -> TreeNode:
    """
    Time: O(n) - Visit each value
    Space: O(n) - Recursion stack
    """
    values = data.split(',')
    index = [0]
    
    def build():
        if values[index[0]] == "null":
            index[0] += 1
            return None
        
        node = TreeNode(int(values[index[0]]))
        index[0] += 1
        node.left = build()
        node.right = build()
        return node
    
    return build()
```

**Trace Table:**

| Test Case | Tree | Serialized | Explanation |
|-----------|------|------------|-------------|
| Basic | [1,2,3,null,null,4,5] | "1,2,null,null,3,4,null,null,5,null,null" | Pre-order with nulls |
| Linear | [1,2,null,3] | "1,2,3,null,null,null" | Left-only tree |
| Empty | null | "null" | Empty tree |

#### 3.10.5 Binary Tree Maximum Path Sum
**Problem:** Find the maximum path sum where path can start and end at any node.

**Solution:** Post-order DFS tracking max path through each node.

**Pseudocode:**
```
max_sum = -INFINITY

FUNCTION max_path_sum(root):
    
    FUNCTION dfs(node):
        IF node is None:
            RETURN 0
        
        left = MAX(0, dfs(node.left))
        right = MAX(0, dfs(node.right))
        
        max_sum = MAX(max_sum, node.val + left + right)
        
        RETURN node.val + MAX(left, right)
    
    dfs(root)
    RETURN max_sum
```

**Implementation:**
```python
def max_path_sum(root: TreeNode) -> int:
    """
    Time: O(n) - Visit each node once
    Space: O(h) - Recursion stack
    """
    max_sum = float('-inf')
    
    def dfs(node):
        nonlocal max_sum
        
        if not node:
            return 0
        
        left = max(0, dfs(node.left))
        right = max(0, dfs(node.right))
        
        max_sum = max(max_sum, node.val + left + right)
        
        return node.val + max(left, right)
    
    dfs(root)
    return max_sum
```

**Trace Table:**

| Test Case | Tree | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [1,2,3] | 6 | Path 2->1->3 |
| Negative | [-10,9,20,null,null,15,7] | 42 | Path 15->20->7 |
| Single | [1] | 1 | Single node |

### 3.11 Heap / Priority Queue Additional

Heap problems for finding kth elements and managing ordered data streams.

#### 3.11.1 Kth Largest Element in a Stream
**Problem:** Design class to find kth largest element in a stream.

**Solution:** Min-heap of size k, maintaining k largest elements.

**Pseudocode:**
```
CLASS KthLargest:
    INITIALIZE k, min_heap
    
    METHOD __init__(k, nums):
        self.k = k
        self.heap = nums
        HEAPIFY self.heap
        
        WHILE size of heap > k:
            HEAPPOP from heap
    
    METHOD add(val):
        HEAPPUSH val to heap
        
        IF size of heap > k:
            HEAPPOP from heap
        
        RETURN heap[0]
```

**Implementation:**
```python
class KthLargest:
    """
    Time: O(k) per add operation with manual sorted insertion
    Space: O(k) - Store only the k largest elements
    """
    def __init__(self, k: int, nums: list[int]):
        self.k = k
        self.data = sorted(nums)
        while len(self.data) > k:
            self.data.pop(0)

    def _insert_sorted(self, val: int) -> None:
        i = 0
        while i < len(self.data) and self.data[i] < val:
            i += 1
        self.data.insert(i, val)

    def add(self, val: int) -> int:
        self._insert_sorted(val)
        if len(self.data) > self.k:
            self.data.pop(0)
        return self.data[0]
```

**Trace Table:**

| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic | init(3,[4,5,8,2]), add(3), add(5), add(10) | [4,5,5] | Track 3rd largest |
| Small k | init(1,[]), add(3), add(5) | [3,5] | Single element heap |
| Duplicates | init(2,[0]), add(-1), add(1), add(-2) | [0,-1,0] | Handle duplicates |

#### 3.11.2 K Closest Points to Origin
**Problem:** Find k closest points to origin (0,0).

**Solution:** Max-heap of size k, maintaining k closest points.

**Pseudocode:**
```
max_heap = []

FOR each point in points:
    distance = -(point[0]^2 + point[1]^2)
    
    IF size of heap < k:
        HEAPPUSH (distance, point) to heap
    ELSE IF distance > heap[0][0]:
        HEAPREPLACE heap with (distance, point)

result = [point for (_, point) in heap]
RETURN result
```

**Implementation:**
```python
def k_closest(points: list[list[int]], k: int) -> list[list[int]]:
    """
    Time: O(n * k) worst-case with manual ordered list
    Space: O(k)
    """
    farthest_first: list[tuple[int, list[int]]] = []  # (distance, point) sorted descending by distance

    for x, y in points:
        dist = x * x + y * y

        i = 0
        while i < len(farthest_first) and farthest_first[i][0] > dist:
            i += 1
        farthest_first.insert(i, (dist, [x, y]))

        if len(farthest_first) > k:
            farthest_first.pop(0)

    return [point for _, point in farthest_first]
```

**Trace Table:**

| Test Case | points | k | Output | Explanation |
|-----------|--------|---|--------|-------------|
| Basic | [[1,3],[-2,2]] | 1 | [[-2,2]] | Closest to origin |
| Multiple | [[3,3],[5,-1],[-2,4]] | 2 | [[3,3],[-2,4]] | Two closest |
| All | [[1,1],[2,2]] | 2 | [[1,1],[2,2]] | Return all |

#### 3.11.3 Find Median from Data Stream
**Problem:** Design data structure that supports adding numbers and finding median.

**Solution:** Two heaps - max heap for lower half, min heap for upper half.

**Pseudocode:**
```
CLASS MedianFinder:
    INITIALIZE max_heap (lower half), min_heap (upper half)
    
    METHOD add_num(num):
        HEAPPUSH -num to max_heap
        
        HEAPPUSH -HEAPPOP(max_heap) to min_heap
        
        IF size of min_heap > size of max_heap:
            HEAPPUSH -HEAPPOP(min_heap) to max_heap
    
    METHOD find_median():
        IF size of max_heap > size of min_heap:
            RETURN -max_heap[0]
        RETURN (-max_heap[0] + min_heap[0]) / 2.0
```

**Implementation:**
```python
class MedianFinder:
    """
    Time: O(n) for add, O(1) for find median using manual ordered lists.
    Space: O(n) - Store all numbers
    """
    def __init__(self):
        self.lower: list[int] = []  # descending order
        self.upper: list[int] = []  # ascending order

    def _insert_desc(self, arr: list[int], val: int) -> None:
        i = 0
        while i < len(arr) and arr[i] > val:
            i += 1
        arr.insert(i, val)

    def _insert_asc(self, arr: list[int], val: int) -> None:
        i = 0
        while i < len(arr) and arr[i] < val:
            i += 1
        arr.insert(i, val)

    def addNum(self, num: int) -> None:
        self._insert_desc(self.lower, num)
        if self.upper and self.lower and self.lower[0] > self.upper[0]:
            moved = self.lower.pop(0)
            self._insert_asc(self.upper, moved)

        if len(self.lower) > len(self.upper) + 1:
            moved = self.lower.pop(0)
            self._insert_asc(self.upper, moved)
        if len(self.upper) > len(self.lower):
            moved = self.upper.pop(0)
            self._insert_desc(self.lower, moved)

    def findMedian(self) -> float:
        if len(self.lower) > len(self.upper):
            return float(self.lower[0])
        return (self.lower[0] + self.upper[0]) / 2.0
```

**Trace Table:**

| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic | add(1), add(2), find(), add(3), find() | [null,null,1.5,null,2.0] | Median updates |
| Odd count | add(1), add(2), add(3), find() | [null,null,null,2.0] | Middle element |
| Even count | add(1), add(2), find() | [null,null,1.5] | Average of middle |

#### 3.11.4 Task Scheduler
**Problem:** Given tasks and cooldown period n, find minimum intervals needed to complete all tasks.

**Solution:** Use the scheduling formula instead of a heap. Let `max_freq` be the highest task frequency and `max_count` the number of tasks with that frequency. The minimum time is `max((max_freq - 1) * (n + 1) + max_count, len(tasks))`.

**Pseudocode:**
```
COUNT frequency of each task
max_freq = maximum count
max_count = number of tasks with max_freq

intervals = (max_freq - 1) * (n + 1) + max_count
RETURN max(intervals, len(tasks))
```

**Implementation:**
```python
def least_interval(tasks: list[str], n: int) -> int:
    """
    Time: O(m) where m = total tasks
    Space: O(k) where k = unique tasks
    """
    freq: dict[str, int] = {}
    max_freq = 0
    max_count = 0

    for task in tasks:
        freq[task] = freq.get(task, 0) + 1
        if freq[task] > max_freq:
            max_freq = freq[task]
            max_count = 1
        elif freq[task] == max_freq:
            max_count += 1

    intervals = (max_freq - 1) * (n + 1) + max_count
    return max(intervals, len(tasks))
```

**Trace Table:**

| Test Case | tasks | n | Output | Explanation |
|-----------|-------|---|--------|-------------|
| Basic | ["A","A","A","B","B","B"] | 2 | 8 | A->B->idle->A->B->idle->A->B |
| No idle | ["A","A","A","B","B","B"] | 0 | 6 | No cooldown needed |
| Different counts | ["A","A","A","A","A","A","B","C","D"] | 2 | 16 | Many idle slots |

### 3.12 Backtracking Additional

More complex backtracking problems requiring pruning and state management.

#### 3.12.1 Subsets II
**Problem:** Given array that may contain duplicates, return all possible subsets without duplicate subsets.

**Solution:** Backtracking with sorting and duplicate skipping.

**Pseudocode:**
```
SORT nums
result = []

FUNCTION backtrack(start, path):
    ADD copy of path to result
    
    FOR i from start to length - 1:
        IF i > start AND nums[i] == nums[i-1]:
            CONTINUE
        
        ADD nums[i] to path
        backtrack(i + 1, path)
        REMOVE last from path

backtrack(0, [])
RETURN result
```

**Implementation:**
```python
def subsets_with_dup(nums: list[int]) -> list[list[int]]:
    """
    Time: O(n * 2^n) - Generate all subsets
    Space: O(n) - Recursion depth
    """
    nums.sort()
    result = []
    
    def backtrack(start: int, path: list[int]):
        result.append(path[:])
        
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i-1]:
                continue
            
            path.append(nums[i])
            backtrack(i + 1, path)
            path.pop()
    
    backtrack(0, [])
    return result
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| With dups | [1,2,2] | [[],[1],[1,2],[1,2,2],[2],[2,2]] | Skip duplicate subsets |
| No dups | [1,2,3] | [[],[1],[1,2],[1,2,3],[1,3],[2],[2,3],[3]] | All subsets |
| All same | [1,1,1] | [[],[1],[1,1],[1,1,1]] | Handle all duplicates |

#### 3.12.2 Combination Sum II
**Problem:** Find all unique combinations that sum to target, each number used once.

**Solution:** Backtracking with sorting and duplicate skipping.

**Pseudocode:**
```
SORT candidates
result = []

FUNCTION backtrack(start, target, path):
    IF target == 0:
        ADD copy of path to result
        RETURN
    
    FOR i from start to length - 1:
        IF i > start AND candidates[i] == candidates[i-1]:
            CONTINUE
        IF candidates[i] > target:
            BREAK
        
        ADD candidates[i] to path
        backtrack(i + 1, target - candidates[i], path)
        REMOVE last from path

backtrack(0, target, [])
RETURN result
```

**Implementation:**
```python
def combination_sum2(candidates: list[int], target: int) -> list[list[int]]:
    """
    Time: O(2^n) - Explore all combinations
    Space: O(n) - Recursion depth
    """
    candidates.sort()
    result = []
    
    def backtrack(start: int, target: int, path: list[int]):
        if target == 0:
            result.append(path[:])
            return
        
        for i in range(start, len(candidates)):
            if i > start and candidates[i] == candidates[i-1]:
                continue
            if candidates[i] > target:
                break
            
            path.append(candidates[i])
            backtrack(i + 1, target - candidates[i], path)
            path.pop()
    
    backtrack(0, target, [])
    return result
```

**Trace Table:**

| Test Case | candidates | target | Output | Explanation |
|-----------|------------|--------|--------|-------------|
| Basic | [10,1,2,7,6,1,5] | 8 | [[1,1,6],[1,2,5],[1,7],[2,6]] | Unique combinations |
| With dups | [2,5,2,1,2] | 5 | [[1,2,2],[5]] | Skip duplicate paths |
| No solution | [1] | 2 | [] | No valid combination |

#### 3.12.3 Permutations
**Problem:** Given distinct integers, return all possible permutations.

**Solution:** Backtracking with used marker.

**Pseudocode:**
```
result = []
used = [False] * length

FUNCTION backtrack(path):
    IF length of path == length of nums:
        ADD copy of path to result
        RETURN
    
    FOR i from 0 to length - 1:
        IF used[i]:
            CONTINUE
        
        used[i] = True
        ADD nums[i] to path
        backtrack(path)
        REMOVE last from path
        used[i] = False

backtrack([])
RETURN result
```

**Implementation:**
```python
def permute(nums: list[int]) -> list[list[int]]:
    """
    Time: O(n * n!) - Generate all permutations
    Space: O(n) - Recursion depth
    """
    result = []
    used = [False] * len(nums)
    
    def backtrack(path: list[int]):
        if len(path) == len(nums):
            result.append(path[:])
            return
        
        for i in range(len(nums)):
            if used[i]:
                continue
            
            used[i] = True
            path.append(nums[i])
            backtrack(path)
            path.pop()
            used[i] = False
    
    backtrack([])
    return result
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [1,2,3] | [[1,2,3],[1,3,2],[2,1,3],[2,3,1],[3,1,2],[3,2,1]] | All permutations |
| Two elements | [0,1] | [[0,1],[1,0]] | 2! = 2 permutations |
| Single | [1] | [[1]] | One permutation |

#### 3.12.4 Palindrome Partitioning
**Problem:** Partition string such that every substring is a palindrome. Return all possible partitions.

**Solution:** Backtracking with palindrome checking.

**Pseudocode:**
```
result = []

FUNCTION is_palindrome(s, left, right):
    WHILE left < right:
        IF s[left] != s[right]:
            RETURN False
        left += 1
        right -= 1
    RETURN True

FUNCTION backtrack(start, path):
    IF start == length of s:
        ADD copy of path to result
        RETURN
    
    FOR end from start to length - 1:
        IF is_palindrome(s, start, end):
            ADD s[start:end+1] to path
            backtrack(end + 1, path)
            REMOVE last from path

backtrack(0, [])
RETURN result
```

**Implementation:**
```python
def partition(s: str) -> list[list[str]]:
    """
    Time: O(n * 2^n) - Explore all partitions
    Space: O(n) - Recursion depth
    """
    result = []
    
    def is_palindrome(left: int, right: int) -> bool:
        while left < right:
            if s[left] != s[right]:
                return False
            left += 1
            right -= 1
        return True
    
    def backtrack(start: int, path: list[str]):
        if start == len(s):
            result.append(path[:])
            return
        
        for end in range(start, len(s)):
            if is_palindrome(start, end):
                path.append(s[start:end+1])
                backtrack(end + 1, path)
                path.pop()
    
    backtrack(0, [])
    return result
```

**Trace Table:**

| Test Case | s | Output | Explanation |
|-----------|---|--------|-------------|
| Basic | "aab" | [["a","a","b"],["aa","b"]] | Two valid partitions |
| Single char | "a" | [["a"]] | Single partition |
| All palindrome | "aba" | [["a","b","a"],["aba"]] | Multiple options |

#### 3.12.5 Word Search
**Problem:** Given a 2D board and a word, find if the word exists in the grid (adjacent cells).

**Solution:** DFS backtracking with visited tracking.

**Pseudocode:**
```
FUNCTION exist(board, word):
    rows = number of rows
    cols = number of cols
    
    FUNCTION dfs(r, c, index):
        IF index == length of word:
            RETURN True
        
        IF r < 0 OR r >= rows OR c < 0 OR c >= cols:
            RETURN False
        IF board[r][c] != word[index]:
            RETURN False
        
        temp = board[r][c]
        board[r][c] = '#'
        
        found = dfs(r+1,c,index+1) OR dfs(r-1,c,index+1) OR
                dfs(r,c+1,index+1) OR dfs(r,c-1,index+1)
        
        board[r][c] = temp
        RETURN found
    
    FOR r from 0 to rows - 1:
        FOR c from 0 to cols - 1:
            IF dfs(r, c, 0):
                RETURN True
    
    RETURN False
```

**Implementation:**
```python
def exist(board: list[list[str]], word: str) -> bool:
    """
    Time: O(m * n * 4^L) where L is word length
    Space: O(L) - Recursion depth
    """
    rows, cols = len(board), len(board[0])
    
    def dfs(r: int, c: int, index: int) -> bool:
        if index == len(word):
            return True
        
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return False
        if board[r][c] != word[index]:
            return False
        
        temp = board[r][c]
        board[r][c] = '#'
        
        found = (dfs(r+1, c, index+1) or dfs(r-1, c, index+1) or
                 dfs(r, c+1, index+1) or dfs(r, c-1, index+1))
        
        board[r][c] = temp
        return found
    
    for r in range(rows):
        for c in range(cols):
            if dfs(r, c, 0):
                return True
    
    return False
```

**Trace Table:**

| Test Case | board | word | Output | Explanation |
|-----------|-------|------|--------|-------------|
| Exists | [["A","B","C"],["S","F","C"],["A","D","E"]] | "ABCCED" | True | Path exists |
| Not exists | [["A","B","C"],["S","F","C"],["A","D","E"]] | "ABCB" | False | Can't reuse cells |
| Single cell | [["a"]] | "a" | True | Match single cell |

### 3.13 Graphs Additional

Advanced graph problems requiring complex traversal strategies.

#### 3.13.1 Surrounded Regions
**Problem:** Capture all regions surrounded by 'X' by flipping 'O' to 'X'.

**Solution:** DFS from border 'O's, mark them safe, flip remaining 'O's.

**Pseudocode:**
```
FUNCTION solve(board):
    IF board is empty:
        RETURN
    
    rows, cols = dimensions
    
    FUNCTION dfs(r, c):
        IF out of bounds OR board[r][c] != 'O':
            RETURN
        board[r][c] = 'S'  // Mark as safe
        dfs(r+1, c)
        dfs(r-1, c)
        dfs(r, c+1)
        dfs(r, c-1)
    
    // Mark border-connected O's as safe
    FOR r in [0, rows-1]:
        FOR c from 0 to cols - 1:
            IF board[r][c] == 'O':
                dfs(r, c)
    
    FOR c in [0, cols-1]:
        FOR r from 0 to rows - 1:
            IF board[r][c] == 'O':
                dfs(r, c)
    
    // Flip remaining O's to X, restore S to O
    FOR r from 0 to rows - 1:
        FOR c from 0 to cols - 1:
            IF board[r][c] == 'O':
                board[r][c] = 'X'
            ELSE IF board[r][c] == 'S':
                board[r][c] = 'O'
```

**Implementation:**
```python
def solve(board: list[list[str]]) -> None:
    """
    Time: O(m * n) - Visit each cell
    Space: O(m * n) - Recursion stack worst case
    """
    if not board:
        return
    
    rows, cols = len(board), len(board[0])
    
    def dfs(r: int, c: int):
        if r < 0 or r >= rows or c < 0 or c >= cols or board[r][c] != 'O':
            return
        board[r][c] = 'S'
        dfs(r+1, c)
        dfs(r-1, c)
        dfs(r, c+1)
        dfs(r, c-1)
    
    # Mark border-connected O's
    for r in [0, rows-1]:
        for c in range(cols):
            if board[r][c] == 'O':
                dfs(r, c)
    
    for c in [0, cols-1]:
        for r in range(rows):
            if board[r][c] == 'O':
                dfs(r, c)
    
    # Flip and restore
    for r in range(rows):
        for c in range(cols):
            if board[r][c] == 'O':
                board[r][c] = 'X'
            elif board[r][c] == 'S':
                board[r][c] = 'O'
```

**Trace Table:**

| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Surrounded | [["X","X","X"],["X","O","X"],["X","X","X"]] | [["X","X","X"],["X","X","X"],["X","X","X"]] | Center O surrounded |
| Border | [["X","O","X"],["O","X","O"],["X","O","X"]] | [["X","O","X"],["O","X","O"],["X","O","X"]] | Border O's not flipped |
| Connected | [["O","O"],["O","O"]] | [["O","O"],["O","O"]] | All connected to border |

#### 3.13.2 Rotting Oranges
**Problem:** Find minimum minutes until no fresh oranges remain (rotten oranges spread every minute).

**Solution:** Multi-source BFS from all rotten oranges.

**Pseudocode:**
```
queue = []
fresh_count = 0

FOR r from 0 to rows - 1:
    FOR c from 0 to cols - 1:
        IF grid[r][c] == 2:
            ADD (r, c, 0) to queue
        ELSE IF grid[r][c] == 1:
            fresh_count += 1

minutes = 0
directions = [(0,1), (1,0), (0,-1), (-1,0)]

WHILE queue not empty:
    r, c, min = DEQUEUE
    minutes = MAX(minutes, min)
    
    FOR dr, dc in directions:
        nr, nc = r + dr, c + dc
        IF in bounds AND grid[nr][nc] == 1:
            grid[nr][nc] = 2
            fresh_count -= 1
            ENQUEUE (nr, nc, min + 1)

RETURN minutes IF fresh_count == 0 ELSE -1
```

**Implementation:**
```python
def oranges_rotting(grid: list[list[int]]) -> int:
    """
    Time: O(m * n) - Visit each cell once
    Space: O(m * n) - Queue size
    """
    rows, cols = len(grid), len(grid[0])
    queue: list[tuple[int, int, int]] = []
    head = 0
    fresh_count = 0

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 2:
                queue.append((r, c, 0))
            elif grid[r][c] == 1:
                fresh_count += 1

    minutes = 0
    directions = [(0,1), (1,0), (0,-1), (-1,0)]

    while head < len(queue):
        r, c, min_elapsed = queue[head]
        head += 1
        minutes = max(minutes, min_elapsed)
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                grid[nr][nc] = 2
                fresh_count -= 1
                queue.append((nr, nc, min_elapsed + 1))

    return minutes if fresh_count == 0 else -1
```

**Trace Table:**

| Test Case | grid | Output | Explanation |
|-----------|------|--------|-------------|
| All rot | [[2,1,1],[1,1,0],[0,1,1]] | 4 | Takes 4 minutes |
| Impossible | [[2,1,1],[0,1,1],[1,0,1]] | -1 | Bottom right unreachable |
| No fresh | [[0,2]] | 0 | No fresh oranges |

#### 3.13.3 Course Schedule II
**Problem:** Return ordering of courses to finish all courses (or empty if impossible).

**Solution:** Topological sort using DFS with cycle detection.

**Pseudocode:**
```
graph = BUILD adjacency list from prerequisites
visiting = SET()
visited = SET()
result = []

FUNCTION dfs(course):
    IF course in visiting:
        RETURN False  // Cycle detected
    IF course in visited:
        RETURN True
    
    ADD course to visiting
    
    FOR prereq in graph[course]:
        IF NOT dfs(prereq):
            RETURN False
    
    REMOVE course from visiting
    ADD course to visited
    ADD course to result
    RETURN True

FOR course from 0 to numCourses - 1:
    IF NOT dfs(course):
        RETURN []

RETURN result
```

**Implementation:**
```python
def find_order(numCourses: int, prerequisites: list[list[int]]) -> list[int]:
    """
    Time: O(V + E) - Visit all vertices and edges
    Space: O(V + E) - Graph and sets
    """
    graph = {i: [] for i in range(numCourses)}
    for course, prereq in prerequisites:
        graph[course].append(prereq)
    
    visiting = set()
    visited = set()
    result = []
    
    def dfs(course: int) -> bool:
        if course in visiting:
            return False
        if course in visited:
            return True
        
        visiting.add(course)
        
        for prereq in graph[course]:
            if not dfs(prereq):
                return False
        
        visiting.remove(course)
        visited.add(course)
        result.append(course)
        return True
    
    for course in range(numCourses):
        if not dfs(course):
            return []
    
    return result
```

**Trace Table:**

| Test Case | numCourses | prerequisites | Output | Explanation |
|-----------|------------|---------------|--------|-------------|
| Valid | 2 | [[1,0]] | [0,1] | Take 0 then 1 |
| Multiple paths | 4 | [[1,0],[2,0],[3,1],[3,2]] | [0,1,2,3] or [0,2,1,3] | Multiple valid orders |
| Cycle | 2 | [[1,0],[0,1]] | [] | Cycle detected |

#### 3.13.4 Graph Valid Tree
**Problem:** Check if n nodes and edges form a valid tree.

**Solution:** Tree has n-1 edges, no cycles, all nodes connected (Union-Find or DFS).

**Pseudocode:**
```
IF edges count != n - 1:
    RETURN False

graph = BUILD adjacency list
visited = SET()

FUNCTION dfs(node, parent):
    ADD node to visited
    
    FOR neighbor in graph[node]:
        IF neighbor == parent:
            CONTINUE
        IF neighbor in visited:
            RETURN False  // Cycle
        IF NOT dfs(neighbor, node):
            RETURN False
    
    RETURN True

IF NOT dfs(0, -1):
    RETURN False

RETURN length of visited == n
```

**Implementation:**
```python
def valid_tree(n: int, edges: list[list[int]]) -> bool:
    """
    Time: O(V + E) - DFS traversal
    Space: O(V + E) - Graph and visited set
    """
    if len(edges) != n - 1:
        return False
    
    graph = {i: [] for i in range(n)}
    for u, v in edges:
        graph[u].append(v)
        graph[v].append(u)
    
    visited = set()
    
    def dfs(node: int, parent: int) -> bool:
        visited.add(node)
        
        for neighbor in graph[node]:
            if neighbor == parent:
                continue
            if neighbor in visited:
                return False
            if not dfs(neighbor, node):
                return False
        
        return True
    
    if not dfs(0, -1):
        return False
    
    return len(visited) == n
```

**Trace Table:**

| Test Case | n | edges | Output | Explanation |
|-----------|---|-------|--------|-------------|
| Valid tree | 5 | [[0,1],[0,2],[0,3],[1,4]] | True | Tree structure |
| Cycle | 5 | [[0,1],[1,2],[2,3],[1,3],[1,4]] | False | Contains cycle |
| Disconnected | 4 | [[0,1],[2,3]] | False | Two components |

### 3.14 Dynamic Programming Additional

Advanced DP problems with multiple dimensions and complex state transitions.

#### 3.14.1 House Robber II
**Problem:** Houses arranged in circle. Rob houses to maximize money without robbing adjacent houses.

**Solution:** Run House Robber on [0:n-1] and [1:n], take maximum.

**Pseudocode:**
```
IF length == 1:
    RETURN nums[0]

FUNCTION rob_linear(houses):
    IF empty:
        RETURN 0
    
    prev2 = 0
    prev1 = 0
    
    FOR amount in houses:
        current = MAX(prev1, prev2 + amount)
        prev2 = prev1
        prev1 = current
    
    RETURN prev1

RETURN MAX(rob_linear(nums[:-1]), rob_linear(nums[1:]))
```

**Implementation:**
```python
def rob(nums: list[int]) -> int:
    """
    Time: O(n) - Two linear passes
    Space: O(1) - Only variables
    """
    if len(nums) == 1:
        return nums[0]
    
    def rob_linear(houses: list[int]) -> int:
        if not houses:
            return 0
        
        prev2, prev1 = 0, 0
        
        for amount in houses:
            current = max(prev1, prev2 + amount)
            prev2 = prev1
            prev1 = current
        
        return prev1
    
    return max(rob_linear(nums[:-1]), rob_linear(nums[1:]))
```

**Trace Table:**

| Test Case | nums | Output | Explanation |
|-----------|------|--------|-------------|
| Basic | [2,3,2] | 3 | Rob house 2 (can't rob 1 and 3) |
| Longer | [1,2,3,1] | 4 | Rob houses 2 and 4 |
| Single | [1] | 1 | Only one house |

#### 3.14.2 Decode Ways
**Problem:** Count ways to decode a string where 'A'=1, 'B'=2, ..., 'Z'=26.

**Solution:** DP - count ways by considering 1-digit and 2-digit decodings.

**Pseudocode:**
```
IF s is empty OR s[0] == '0':
    RETURN 0

n = length of s
dp = [0] * (n + 1)
dp[0] = 1
dp[1] = 1

FOR i from 2 to n:
    one_digit = INT(s[i-1])
    two_digits = INT(s[i-2:i])
    
    IF one_digit >= 1:
        dp[i] += dp[i-1]
    
    IF 10 <= two_digits <= 26:
        dp[i] += dp[i-2]

RETURN dp[n]
```

**Implementation:**
```python
def num_decodings(s: str) -> int:
    """
    Time: O(n) - Single pass
    Space: O(1) - Only two variables needed
    """
    if not s or s[0] == '0':
        return 0
    
    n = len(s)
    prev2, prev1 = 1, 1
    
    for i in range(1, n):
        current = 0
        
        if s[i] != '0':
            current += prev1
        
        two_digit = int(s[i-1:i+1])
        if 10 <= two_digit <= 26:
            current += prev2
        
        prev2 = prev1
        prev1 = current
    
    return prev1
```

**Trace Table:**

| Test Case | s | Output | Explanation |
|-----------|---|--------|-------------|
| Basic | "12" | 2 | "AB" (1,2) or "L" (12) |
| Multiple ways | "226" | 3 | "BZ", "VF", "BBF" |
| Invalid | "06" | 0 | Leading zero invalid |

#### 3.14.3 Unique Paths II
**Problem:** Find unique paths in grid with obstacles.

**Solution:** DP with obstacle checking.

**Pseudocode:**
```
IF obstacleGrid[0][0] == 1:
    RETURN 0

rows, cols = dimensions
dp = [[0] * cols FOR _ IN range(rows)]
dp[0][0] = 1

FOR r from 0 to rows - 1:
    FOR c from 0 to cols - 1:
        IF obstacleGrid[r][c] == 1:
            dp[r][c] = 0
        ELSE:
            IF r > 0:
                dp[r][c] += dp[r-1][c]
            IF c > 0:
                dp[r][c] += dp[r][c-1]

RETURN dp[rows-1][cols-1]
```

**Implementation:**
```python
def unique_paths_with_obstacles(obstacleGrid: list[list[int]]) -> int:
    """
    Time: O(m * n) - Fill DP table
    Space: O(n) - Can optimize to single row
    """
    if obstacleGrid[0][0] == 1:
        return 0
    
    rows, cols = len(obstacleGrid), len(obstacleGrid[0])
    dp = [0] * cols
    dp[0] = 1
    
    for r in range(rows):
        for c in range(cols):
            if obstacleGrid[r][c] == 1:
                dp[c] = 0
            elif c > 0:
                dp[c] += dp[c-1]
    
    return dp[-1]
```

**Trace Table:**

| Test Case | obstacleGrid | Output | Explanation |
|-----------|--------------|--------|-------------|
| With obstacle | [[0,0,0],[0,1,0],[0,0,0]] | 2 | Two paths around obstacle |
| Start blocked | [[1,0]] | 0 | Start blocked |
| No obstacle | [[0,0],[0,0]] | 2 | Two paths |

---

## 4. Interview Strategy: The UMPIRE Framework

When solving problems in interviews, follow this systematic approach:

**U - Understand:** Clarify the problem, ask about edge cases, input constraints
**M - Match:** Identify the pattern (Two Pointers? DP? DFS?)
**P - Plan:** Outline your approach before coding
**I - Implement:** Write clean, well-structured code
**R - Review:** Test with examples, check edge cases
**E - Evaluate:** Discuss time/space complexity, potential optimizations

---

## 5. Practice Schedule & Final Tips

**6-Week Comprehensive Plan (Blind 75 + NeetCode 150):**
- **Week 1-2:** Arrays, Strings, Hash Maps, Two Pointers (30 problems)
- **Week 3:** Sliding Window, Stack, Binary Search (25 problems)
- **Week 4:** Trees, Graphs, DFS/BFS (30 problems)
- **Week 5:** Dynamic Programming, Backtracking, Greedy (35 problems)
- **Week 6:** Review all patterns, Mock Interviews, Hard problems (30 problems)

**Final Tips:**
1. **Master patterns, not problems** - Focus on understanding why a solution works
2. **Code without looking** - Practice implementing from memory
3. **Explain out loud** - Simulate interview communication
4. **Time yourself** - Aim for 20-30 minutes per medium problem
5. **Review mistakes** - Understand why you got stuck
6. **Mock interviews** - Practice with peers or platforms like Pramp

**Red Flags to Avoid:**
- Jumping into code without planning
- Not testing your solution
- Poor variable naming
- Ignoring edge cases
- Not discussing trade-offs

---

## Summary

The Blind 75 represents the core patterns needed for technical interviews. By mastering these patterns—not memorizing solutions—you build a robust problem-solving toolkit applicable to hundreds of variations. Focus on understanding the underlying algorithms, practice explaining your thought process, and you'll be well-prepared for interviews at Lawstronaut, Optimizely, and beyond.

---
title: "Two Pointers"
---

### 2.2 Two Pointers
-   **Pattern:** Using two pointers to iterate through a data structure, often from opposite ends or at different speeds. This is highly effective for problems involving sorted arrays or searching for pairs.

**Two Pointers Intuition:**

Instead of nested loops (O(n²)), use two pointers working together:
1. **Opposite ends:** Start from both sides, move toward center
2. **Same direction:** Fast/slow pointers for cycle detection
3. **Sorted array:** Adjust pointers based on comparison

**When to use:**
- Sorted array (can make decisions based on values)
- Need to find pairs/triplets
- Palindrome checks
- Removing duplicates in-place

#### 2.2.1 Valid Palindrome
**Problem:** Given a string `s`, return `true` if it is a palindrome, or `false` otherwise. A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.

**Building Intuition:**

**Core Idea:** A palindrome reads the same forward and backward.

**Instead of:**
- Creating a reversed string (O(n) space)
- Comparing character by character

**Do this:**
- Compare first with last
- Second with second-to-last
- Work toward the middle

**Example:** "racecar"
```
l=0, r=6: 'r' == 'r' ✓
l=1, r=5: 'a' == 'a' ✓
l=2, r=4: 'c' == 'c' ✓
l=3, r=3: Middle reached ✓ Palindrome!
```

**Why Two Pointers?**
- O(1) space (no string reversal needed)
- One pass through string
- Can skip non-alphanumeric on the fly

**Solution:** Use two pointers, one at the beginning (`left`) and one at the end (`right`) of the string. Move them towards the center, skipping non-alphanumeric characters. If at any point the characters at `left` and `right` (in lowercase) don't match, it's not a palindrome.

**Pseudocode:**
```
INITIALIZE left = 0, right = length of s - 1
WHILE left < right:
    WHILE left < right AND s[left] is not alphanumeric:
        INCREMENT left
    WHILE left < right AND s[right] is not alphanumeric:
        DECREMENT right
    IF lowercase(s[left]) != lowercase(s[right]):
        RETURN False
    INCREMENT left
    DECREMENT right
RETURN True
```

**Implementation:**
```python
def is_palindrome(s: str) -> bool:
    """
    Time: O(n) - Each pointer traverses at most n/2 steps.
    Space: O(1) - No extra space is used besides the pointers.
    """
    l, r = 0, len(s) - 1
    while l < r:
        while l < r and not s[l].isalnum():
            l += 1
        while l < r and not s[r].isalnum():
            r -= 1
        if s[l].lower() != s[r].lower():
            return False
        l, r = l + 1, r - 1
    return True
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic palindrome | "A man, a plan, a canal: Panama" | True | Ignoring spaces and punctuation, reads same both ways |
| Not a palindrome | "race a car" | False | "raceacar" != "racaecar" |
| Single character | "a" | True | Single character is always a palindrome |
| Empty string | "" | True | Empty string is considered a palindrome |

#### 2.2.2 3Sum
**Problem:** Given an integer array `nums`, return all the triplets `[nums[i], nums[j], nums[k]]` such that `i != j`, `i != k`, and `j != k`, and `nums[i] + nums[j] + nums[k] == 0`.

**Building Intuition:**

**Key Insight:** Fix one number, use Two Sum on the rest!

**Strategy:**
1. Sort array first (enables two pointers)
2. For each number, find two others that sum to `-num`
3. Skip duplicates to avoid duplicate triplets

**Example:** `[-1, 0, 1, 2, -1, -4]` → sorted: `[-4, -1, -1, 0, 1, 2]`
```
i=0, num=-4: Find two that sum to 4
  left=1(-1), right=5(2) → -1+2=1 < 4 → move left
  left=2(-1), right=5(2) → -1+2=1 < 4 → move left
  No solution for -4

i=1, num=-1: Find two that sum to 1
  left=2(-1), right=5(2) → -1+2=1 = 1 ✓
  Found: [-1, -1, 2]
  
i=2, num=-1: Skip (duplicate)

i=3, num=0: Find two that sum to 0
  left=4(1), right=5(2) → 1+2=3 > 0 → move right
  left=4(1), right=5(2) → Can't find
  Actually: left=4(1), right... wait, let me recalculate
  Found: [-1, 0, 1]
```

**Why Sort First?**
- Enables two pointers technique
- Easy to skip duplicates
- Can break early if number > 0

**Solution:** This is a classic extension of "Two Sum". First, sort the array. Then, iterate through the array with a main pointer `i`. For each `nums[i]`, use two additional pointers, `left` and `right`, to find a pair that sums to `-nums[i]`. Crucially, you must handle duplicates by skipping over identical elements to avoid duplicate triplets in the result.

**Pseudocode:**
```
SORT nums
INITIALIZE empty result list
FOR i from 0 to length of nums:
    IF nums[i] > 0:
        BREAK (no more solutions possible)
    IF i > 0 AND nums[i] == nums[i-1]:
        CONTINUE (skip duplicates)
    
    left = i + 1, right = length - 1
    WHILE left < right:
        sum = nums[i] + nums[left] + nums[right]
        IF sum > 0:
            DECREMENT right
        ELSE IF sum < 0:
            INCREMENT left
        ELSE:
            ADD [nums[i], nums[left], nums[right]] to result
            INCREMENT left, DECREMENT right
            WHILE left < right AND nums[left] == nums[left-1]:
                INCREMENT left (skip duplicates)
RETURN result
```

**Implementation:**
```python
def three_sum(nums: list[int]) -> list[list[int]]:
    """
    Time: O(n^2) - O(n log n) for the sort, then O(n^2) for the nested loops.
    Space: O(1) or O(n) depending on the space complexity of the sorting algorithm.
    """
    res = []
    nums.sort()
    for i, a in enumerate(nums):
        # Skip positive integers for the first element
        if a > 0:
            break
        # Skip duplicates for the first element
        if i > 0 and a == nums[i - 1]:
            continue
            
        l, r = i + 1, len(nums) - 1
        while l < r:
            threeSum = a + nums[l] + nums[r]
            if threeSum > 0:
                r -= 1
            elif threeSum < 0:
                l += 1
            else:
                res.append([a, nums[l], nums[r]])
                l += 1
                r -= 1
                # Skip duplicates for the second and third elements
                while nums[l] == nums[l - 1] and l < r:
                    l += 1
    return res
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|  
| Basic | [-1,0,1,2,-1,-4] | [[-1,-1,2],[-1,0,1]] | Two triplets sum to 0 |
| All zeros | [0,0,0] | [[0,0,0]] | Only one valid triplet |
| No solution | [1,2,3] | [] | No three numbers sum to 0 |
| Duplicates | [-2,0,0,2,2] | [[-2,0,2]] | Duplicates handled correctly |

#### 2.2.3 Container With Most Water
**Problem:** You are given an integer array `height` of length `n`. There are `n` vertical lines drawn such that the two endpoints of the `i`-th line are `(i, 0)` and `(i, height[i])`. Find two lines that together with the x-axis form a container, such that the container contains the most water.

**Building Intuition:**

**Key Insight:** Area = width × min(height_left, height_right). Start wide, move inward intelligently.

**Greedy Strategy:**
- Start with widest container (left=0, right=end)
- Area limited by shorter line
- Move the shorter line inward (might find taller line)
- Never move taller line (can only decrease area)

**Example:** `[1, 8, 6, 2, 5, 4, 8, 3, 7]`
```
Step 1: left=0(1), right=8(7)
        width=8, height=min(1,7)=1
        area=8×1=8

Step 2: Move left (1 < 7)
        left=1(8), right=8(7)
        width=7, height=min(8,7)=7
        area=7×7=49 ✓

Step 3: Move right (8 > 7)
        left=1(8), right=7(3)
        width=6, height=min(8,3)=3
        area=6×3=18

... Continue moving shorter side ...

Max area: 49
```

**Why Move Shorter Line?**
- Moving taller line: Width decreases, height can't increase → area decreases
- Moving shorter line: Width decreases, but height might increase → possible larger area

**Solution:** Start with two pointers at the widest possible container, `left = 0` and `right = len(height) - 1`. The area is determined by the shorter of the two lines. To potentially find a larger area, you must move the pointer of the shorter line inward, as moving the taller line's pointer can only decrease the width without increasing the height.

**Pseudocode:**
```
INITIALIZE left = 0, right = length - 1
INITIALIZE max_water = 0
WHILE left < right:
    area = (right - left) * MIN(height[left], height[right])
    max_water = MAX(max_water, area)
    IF height[left] < height[right]:
        INCREMENT left
    ELSE:
        DECREMENT right
RETURN max_water
```

**Implementation:**
```python
def max_area(height: list[int]) -> int:
    """
    Time: O(n) - The pointers traverse the array once.
    Space: O(1) - Only pointers are used.
    """
    l, r = 0, len(height) - 1
    max_water = 0
    while l < r:
        area = (r - l) * min(height[l], height[r])
        max_water = max(max_water, area)
        if height[l] < height[r]:
            l += 1
        else:
            r -= 1
    return max_water
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [1,8,6,2,5,4,8,3,7] | 49 | Max area between index 1 (height 8) and index 8 (height 7): 7*7=49 |
| Same heights | [1,1] | 1 | Only one container possible: 1*1=1 |
| Increasing | [1,2,3,4,5] | 6 | Max area between index 0 and 4: (4-0)*1=4 or (3-1)*2=4 or (4-2)*2=4, best is (4-1)*2=6 |
| Single peak | [1,2,1] | 2 | Container between indices 0 and 2: 2*1=2 |

#### 2.2.4 Merge Strings Alternately
**Problem:** Given two strings `word1` and `word2`, merge them by adding letters in alternating order, starting with `word1`. If a string is longer, append the remaining characters to the end.

**Building Intuition:**

- Think of walking down both strings at the same time.
- At each step, grab the next letter from each string in turn.
- When one string finishes, simply pour the rest of the other string into the output.

**Key Insight:** Treat each string like its own queue with a pointer. Move the pointer forward every time you consume a character so you never revisit work.

**Why Two Pointers?**
- Each pointer tracks where you are within its respective string.
- You avoid slicing or repeatedly popping the first element (which would be expensive).
- The combined walk takes O(n + m) time with only O(1) extra tracking state.

**Solution:** Maintain two indices (`i`, `j`) that walk down `word1` and `word2`. Append the current character from each string if that pointer is still in bounds, and advance the pointer. Repeat until both strings are exhausted; any leftover characters are naturally appended because their pointer still passes the bounds check.

**Pseudocode:**
```
INITIALIZE i = 0, j = 0
INITIALIZE merged_chars = empty list
WHILE i < len(word1) OR j < len(word2):
    IF i < len(word1):
        APPEND word1[i] to merged_chars
        INCREMENT i
    IF j < len(word2):
        APPEND word2[j] to merged_chars
        INCREMENT j
RETURN JOIN(merged_chars)
```

**Implementation:**
```python
def merge_alternately(word1: str, word2: str) -> str:
    """
    Time: O(n + m) where n=len(word1) and m=len(word2).
    Space: O(n + m) for the output builder.
    """
    i = j = 0
    merged = []

    while i < len(word1) or j < len(word2):
        if i < len(word1):
            merged.append(word1[i])
            i += 1
        if j < len(word2):
            merged.append(word2[j])
            j += 1

    return "".join(merged)
```

**Trace Table:**
| Test Case | word1 | word2 | Output | Explanation |
|-----------|-------|-------|--------|-------------|
| Same length | "abc" | "pqr" | "apbqcr" | Alternates every character evenly |
| word2 longer | "ab" | "pqrs" | "apbqrs" | Remaining "rs" from `word2` appended at end |
| word1 longer | "abcd" | "pq" | "apbqcd" | After `word2` runs out, append leftover `word1` |
| Empty second | "xyz" | "" | "xyz" | Only characters from `word1` |

```python
# Pattern Example: Valid Palindrome
def is_palindrome(s: str) -> bool:
    l, r = 0, len(s) - 1
    while l < r:
        while l < r and not s[l].isalnum():
            l += 1
        while l < r and not s[r].isalnum():
            r -= 1
        if s[l].lower() != s[r].lower():
            return False
        l, r = l + 1, r - 1
    return True
```

---
title: "Arrays & Hashing"
---

### 2.1 Arrays & Hashing
-   **Pattern:** Using hash maps (dictionaries in Python) and sets to store and retrieve data in O(1) average time complexity. This is incredibly useful for checking for existence, counting occurrences, or grouping items.

#### 2.1.1 Majority Element (Grind 75)
**Problem:** Given an array `nums` of size `n`, return the majority element. The majority element is the element that appears more than `floor(n / 2)` times.

**Building Intuition:**

**Key Insight:** Boyer-Moore Voting Algorithm - The majority element will "survive" cancellation!

**The Voting Analogy:**
Imagine a room where the majority person tries to stay. Each time:
- Same person? They gain support (count++)
- Different person? They lose support (count--)
- Support reaches 0? Pick new candidate

**Example:** `[2, 2, 1, 1, 1, 2, 2]`
```
Step 1: candidate=2, count=1   [2]
Step 2: candidate=2, count=2   [2,2]
Step 3: candidate=2, count=1   [2,2,1]  (2 vs 1: cancel one)
Step 4: candidate=2, count=0   [2,2,1,1] (all cancel)
Step 5: candidate=1, count=1   [2,2,1,1,1] (new candidate)
Step 6: candidate=1, count=0   [2,2,1,1,1,2] (1 vs 2: cancel)
Step 7: candidate=2, count=1   [2,2,1,1,1,2,2] (new candidate)

Final: candidate=2 (majority!)
```

**Why It Works:**
- Majority > n/2, so even after cancellations it survives
- O(n) time, O(1) space
- Elegant mathematical proof!

**Alternative:** Hash map to count (O(n) space)

**Solution:** Use Boyer-Moore Voting Algorithm for O(1) space, or use a hash map to count occurrences.

**Pseudocode:**
```
INITIALIZE candidate = None, count = 0
FOR each num in nums:
    IF count == 0:
        candidate = num
    IF num == candidate:
        INCREMENT count
    ELSE:
        DECREMENT count
RETURN candidate
```

**Implementation:**
```python
def majority_element(nums: list[int]) -> int:
    """
    Time: O(n) - Single pass through array.
    Space: O(1) - Only two variables used.
    """
    count = 0
    candidate = None
    
    for num in nums:
        if count == 0:
            candidate = num
        count += 1 if num == candidate else -1
    
    return candidate
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [3,2,3] | 3 | 3 appears twice (majority) |
| Longer | [2,2,1,1,1,2,2] | 2 | 2 appears 4 times out of 7 |
| All same | [1,1,1,1] | 1 | All elements are majority |
| Barely majority | [1,2,1] | 1 | 1 appears twice out of 3 |

**Pattern Recognition: Boyer-Moore Voting**

**When to use this pattern:**
1. Find majority element (> n/2)
2. Need O(1) space
3. Guaranteed majority exists

**How It Works:**
- Pair up elements that differ → cancel out
- Majority survives because it's > 50%
- Two-pass version can verify if majority exists

**Related Problems:**
- **Majority Element II** (find all elements > n/3)
- **Single Number** (XOR cancellation)
- **Find the Celebrity** (similar elimination logic)

#### 2.1.2 Reverse Number and Add Two
**Problem:** Given a number $n$, reverse the number, add $2$, and return the result.

**Solution:** Convert the number to a string to reverse it, then convert back to integer, add 2, and return.

**Pseudocode:**
```
FUNCTION reverse_and_add_two(n):
    // Handle negative numbers
    is_negative = n < 0
    n = ABS(n)
    
    // Reverse the number
    reversed_str = REVERSE(STR(n))
    reversed_num = INT(reversed_str)
    
    // Add 2
    result = reversed_num + 2
    
    // Restore sign if negative
    IF is_negative:
        result = -result
    
    RETURN result
```

**Implementation:**
```python
def reverse_and_add_two(n: int) -> int:
    """
    Time: O(d) where d is the number of digits.
    Space: O(d) for string conversion.
    """
    # Handle negative numbers
    is_negative = n < 0
    n = abs(n)
    
    # Reverse the number by converting to string
    reversed_str = str(n)[::-1]
    reversed_num = int(reversed_str)
    
    # Add 2
    result = reversed_num + 2
    
    # Restore sign if original was negative
    if is_negative:
        result = -result
    
    return result

# Alternative: Mathematical approach without string conversion
def reverse_and_add_two_math(n: int) -> int:
    """
    Time: O(d) where d is the number of digits.
    Space: O(1) - No extra space.
    """
    is_negative = n < 0
    n = abs(n)
    
    reversed_num = 0
    while n > 0:
        digit = n % 10
        reversed_num = reversed_num * 10 + digit
        n //= 10
    
    result = reversed_num + 2
    
    if is_negative:
        result = -result
    
    return result
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | 123 | 323 | 123 → 321 + 2 = 323 |
| Single digit | 5 | 7 | 5 → 5 + 2 = 7 |
| With zeros | 1200 | 23 | 1200 → 21 + 2 = 23 |
| Negative | -456 | -656 | -456 → -(654 + 2) = -656 |
| Zero | 0 | 2 | 0 → 0 + 2 = 2 |

#### 2.1.3 Two Sum
**Problem:** Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.

**Building Intuition:**

The brute force approach would check every pair (O(n²)), but we can do better!

**Key Insight:** Instead of looking for two numbers that sum to target, look for *one number and its complement*.

For each number `x`, ask: "Have I already seen `target - x`?"

**Example:** `nums = [2, 7, 11, 15]`, `target = 9`
```
Step 1: See 2 → Need 7 → Haven't seen it yet → Remember {2: index 0}
Step 2: See 7 → Need 2 → Found it! {2: 0} → Return [0, 1]
```

**Why Hash Map?** 
- O(1) lookup vs O(n) array search
- Remember both value AND index
- One pass through array

**Solution:** We can iterate through the array while using a hash map to store the numbers we've seen and their indices. For each number, we calculate its `complement` (i.e., `target - num`). If the complement is already in our hash map, we've found our pair.

**Pseudocode:**
```
INITIALIZE empty hash map 'seen'
FOR each index i and number num in nums:
    complement = target - num
    IF complement exists in seen:
        RETURN [seen[complement], i]
    seen[num] = i
RETURN empty (no solution found)
```

**Implementation:**
```python
def two_sum(nums: list[int], target: int) -> list[int]:
    """
    Time: O(n) - We iterate through the list once.
    Space: O(n) - In the worst case, we store all n elements in the hash map.
    """
    seen = {}  # val -> index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
```

**Trace Table (nums = [2, 7, 11, 15], target = 9):**
| Step | i | num | complement | seen before step | action/result |
|------|---|-----|------------|------------------|---------------|
| 1 | 0 | 2 | 7 | {} | add seen[2] = 0 |
| 2 | 1 | 7 | 2 | {2: 0} | complement found → return [0, 1] |

**Pattern Recognition: Complement Lookup**

**When to use this pattern:**
1. Finding pairs/tuples that satisfy a condition
2. Need O(n) instead of O(n²)
3. Can compute what you're looking for: `target - current`

**Related Problems:**
- **3Sum** (extend to three numbers, use two pointers after sorting)
- **4Sum** (extend to four numbers)
- **Two Sum II** (sorted array → use two pointers instead of hash map)
- **Subarray Sum Equals K** (prefix sum + hash map)

**Key Questions:**
1. Can I compute the complement? (target - current)
2. Do I need to remember what I've seen? (hash map)
3. Do I need to track positions/indices? (store as value)

**Topic Problems to Practice:**
- [Two Sum II – Input Array Is Sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/)
- [Two Sum IV – Input Is a BST](https://leetcode.com/problems/two-sum-iv-input-is-a-bst/)
- [4Sum](https://leetcode.com/problems/4sum/)

#### 2.1.2 Contains Duplicate
**Problem:** Given an integer array `nums`, return `true` if any value appears at least twice in the array, and `false` if every element is distinct.

**Building Intuition:**

**The Question:** Have I seen this number before?

**Three Approaches:**
1. **Nested loops:** Check each pair → O(n²) time, O(1) space => Too slow
2. **Sort first:** Check adjacent → O(n log n) time, O(1) space ✓ Good
3. **Hash set:** Track seen → O(n) time, O(n) space ✓✓ Best for most cases

**Why Hash Set?**
- Set membership: O(1) vs O(n) array search
- Automatic duplicate detection
- One pass through array

**Example:** `[1, 2, 3, 1]`
```
Seen: {} → See 1 → Add {1}
Seen: {1} → See 2 → Add {1, 2}
Seen: {1, 2} → See 3 → Add {1, 2, 3}
Seen: {1, 2, 3} → See 1 → Already in set! Return True
```

**Solution:** A hash set is perfect for this. We iterate through the array, adding each number to the set. If we encounter a number that's already in the set, we've found a duplicate. A simpler one-liner is to compare the length of the original list to the length of a set created from it.

**Pseudocode:**
```
INITIALIZE empty set 'hashset'
FOR each number n in nums:
    IF n is in hashset:
        RETURN True
    ADD n to hashset
RETURN False
```

**Implementation:**
```python
def contains_duplicate(nums: list[int]) -> bool:
    """
    Time: O(n) - We iterate through the list once.
    Space: O(n) - To store the hash set.
    """
    hashset = set()
    for n in nums:
        if n in hashset:
            return True
        hashset.add(n)
    return False

# Alternative one-liner
def contains_duplicate_oneliner(nums: list[int]) -> bool:
    return len(nums) != len(set(nums))
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Has duplicate | [1, 2, 3, 1] | True | Element 1 appears twice |
| No duplicate | [1, 2, 3, 4] | False | All elements are distinct |
| Multiple duplicates | [1, 1, 1, 3, 3, 4, 3, 2, 4, 2] | True | Multiple elements appear more than once |
| Single element | [1] | False | Only one element, no duplicates possible |

**Pattern Recognition: Hash Set for Uniqueness**

**When to use this pattern:**
1. Detecting duplicates/repetitions
2. Checking if element was seen before
3. Need O(n) time, O(n) space acceptable

**Related Problems:**
- **Happy Number** (cycle detection in number sequence)
- **Linked List Cycle** (can use set, but Floyd's is O(1) space)
- **Longest Consecutive Sequence** (set for O(1) lookup)
- **Intersection of Two Arrays** (set for unique elements)

**Trade-offs:**
- **Hash Set:** Fast O(n), uses O(n) space
- **Sort First:** O(n log n), uses O(1) space
- **Choose:** Based on space vs time constraints

**Topic Problems to Practice:**
- [Contains Duplicate II](https://leetcode.com/problems/contains-duplicate-ii/)
- [Contains Duplicate III](https://leetcode.com/problems/contains-duplicate-iii/)
- [Happy Number](https://leetcode.com/problems/happy-number/)

#### 2.1.3 Group Anagrams
**Problem:** Given an array of strings `strs`, group the anagrams together.

**Building Intuition:**

**Key Insight:** Anagrams have the same characters, just rearranged. Need a "signature" that's identical for anagrams.

**Two Approaches:**
1. **Sort each string:** "eat" → "aet", "tea" → "aet" (same!)
2. **Character count:** "eat" → {e:1, a:1, t:1}

**Example:** `["eat", "tea", "tan", "ate", "nat", "bat"]`
```
"eat" → sorted: "aet" → group 1
"tea" → sorted: "aet" → group 1 (same!)
"tan" → sorted: "ant" → group 2
"ate" → sorted: "aet" → group 1 (same!)
"nat" → sorted: "ant" → group 2 (same!)
"bat" → sorted: "abt" → group 3

Result: [["eat","tea","ate"], ["tan","nat"], ["bat"]]
```

**Why Hash Map?**
- Use sorted string as key
- Group all strings with same key
- O(1) lookup and grouping

**Solution:** The core idea is to find a canonical representation for anagrams. If we sort the characters of a string, all its anagrams will produce the same sorted string. We can use this sorted string as a key in a hash map. A more performant approach is to use a character count array (e.g., a 26-element array for lowercase English letters) as the key.

**Pseudocode:**
```
INITIALIZE empty hash map 'anagram_map'
FOR each string s in strs:
    sorted_s = SORT characters of s
    APPEND s to anagram_map[sorted_s]
RETURN all values from anagram_map
```

**Implementation:**
```python
def group_anagrams(strs: list[str]) -> list[list[str]]:
    """
    Time: O(m * n log n) where m is the number of strings and n is the average length.
    Space: O(m * n) to store the results.
    """
    anagram_map: dict[str, list[str]] = {}
    for s in strs:
        sorted_s = "".join(sorted(s))
        if sorted_s not in anagram_map:
            anagram_map[sorted_s] = []
        anagram_map[sorted_s].append(s)
    return list(anagram_map.values())
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Mixed anagrams | ["eat","tea","tan","ate","nat","bat"] | [["bat"],["nat","tan"],["ate","eat","tea"]] | Groups anagrams together |
| Empty string | [""] | [[""]] | Single empty string forms one group |
| Single char | ["a"] | [["a"]] | Single character in its own group |
| No anagrams | ["abc", "def", "ghi"] | [["abc"], ["def"], ["ghi"]] | Each string in separate group |

**Pattern Recognition: Canonical Form Grouping**

**When to use this pattern:**
1. Group items by some property (anagrams, patterns)
2. Need a consistent "signature" for equivalent items
3. Hash map for O(1) grouping

**Canonical Forms:**
- Sorted string: "eat" → "aet"
- Character count: [1,0,0,0,1,0...1] (26 positions)
- Hash of properties

**Related Problems:**
- **Valid Anagram** (compare two strings)
- **Find All Anagrams in String** (sliding window + anagram check)
- **Group Shifted Strings** (shift pattern as signature)

**Topic Problems to Practice:**
- [Valid Anagram](https://leetcode.com/problems/valid-anagram/)
- [Find All Anagrams in a String](https://leetcode.com/problems/find-all-anagrams-in-a-string/)
- [Group Shifted Strings](https://leetcode.com/problems/group-shifted-strings/) *(Premium)*

#### 2.1.4 Top K Frequent Elements
**Problem:** Given an integer array `nums` and an integer `k`, return the `k` most frequent elements.

**Building Intuition:**

**Key Insight:** Instead of sorting (O(n log n)), use bucket sort with frequency as index!

**Three Approaches:**
1. **Sort by frequency:** O(n log n) => Too slow
2. **Heap:** O(n log k) ✓ Good
3. **Bucket sort:** O(n) ✓✓ Optimal!

**Bucket Sort Idea:**
```
Array: [1,1,1,2,2,3], k=2

Step 1: Count frequencies
{1: 3, 2: 2, 3: 1}

Step 2: Create buckets (index = frequency)
Bucket[0]: []
Bucket[1]: [3]        ← appears 1 time
Bucket[2]: [2]        ← appears 2 times
Bucket[3]: [1]        ← appears 3 times
Bucket[4]: []
...

Step 3: Walk from high to low frequency
Freq 3: [1] → Add 1 to result
Freq 2: [2] → Add 2 to result
k=2 elements found!

Result: [1, 2]
```

**Why Bucket Sort?**
- Frequency range: 1 to n (bounded!)
- Can use frequency as array index
- O(n) time instead of O(n log n)

**Solution:** First, count the frequency of each number using a plain dictionary. Then use bucket sort: create buckets where the index represents the frequency and place each number into its bucket. Walk the buckets from highest frequency to lowest to collect the top `k` elements.

**Pseudocode:**
```
INITIALIZE empty frequency map counts
FOR each num in nums:
    INCREMENT counts[num]

INITIALIZE buckets as a list of empty lists of length len(nums) + 1
FOR each (num, freq) in counts:
    APPEND num to buckets[freq]

INITIALIZE result list
FOR freq from len(buckets) - 1 down to 1:
    FOR each num in buckets[freq]:
        APPEND num to result
        IF length of result == k:
            RETURN result
RETURN result
```

**Implementation:**
```python
def top_k_frequent(nums: list[int], k: int) -> list[int]:
    """
    Time: O(n) - Counting plus linear bucket scan.
    Space: O(n) - For the frequency map and buckets.
    """
    counts: dict[int, int] = {}
    for num in nums:
        counts[num] = counts.get(num, 0) + 1

    buckets: list[list[int]] = [[] for _ in range(len(nums) + 1)]
    for num, freq in counts.items():
        buckets[freq].append(num)

    res: list[int] = []
    for freq in range(len(buckets) - 1, 0, -1):
        for num in buckets[freq]:
            res.append(num)
            if len(res) == k:
                return res
    return res
```

**Trace Table:**
| Test Case | Input | k | Output | Explanation |
|-----------|-------|---|--------|-------------|
| Basic | [1,1,1,2,2,3] | 2 | [1,2] | 1 appears 3 times, 2 appears 2 times |
| Single element | [1] | 1 | [1] | Only one element |
| All same frequency | [1,2] | 2 | [1,2] | Both appear once |

**Pattern Recognition: Bucket Sort for Bounded Range**

**When to use this pattern:**
1. Need top/bottom k elements
2. Values in bounded range (frequency: 1 to n)
3. Want O(n) instead of O(n log n)

**Bucket Sort vs Heap:**
- **Bucket sort:** O(n) time, O(n) space, only works for bounded ranges
- **Heap:** O(n log k) time, O(k) space, works for any range
- **Choose:** Bucket sort when possible, heap otherwise

**Related Problems:**
- **Top K Frequent Words** (heap, must handle ties)
- **Sort Characters by Frequency** (bucket sort works!)
- **K Closest Points to Origin** (heap or quickselect)

**Topic Problems to Practice:**
- [Top K Frequent Words](https://leetcode.com/problems/top-k-frequent-words/)
- [Kth Largest Element in an Array](https://leetcode.com/problems/kth-largest-element-in-an-array/)
- [K Closest Points to Origin](https://leetcode.com/problems/k-closest-points-to-origin/)

#### 2.1.5 Product of Array Except Self
**Problem:** Given an integer array `nums`, return an array `answer` such that `answer[i]` is equal to the product of all the elements of `nums` except `nums[i]`. You must do this in O(n) time and without using division.

**Building Intuition:**

**The Core Insight:** For each position, you need:
- Product of everything to the LEFT ×
- Product of everything to the RIGHT

**Visual Example:** `nums = [1, 2, 3, 4]`
```
Index:     0    1    2    3
Value:     1    2    3    4

Left:      1    1    2    6   (product of all elements before i)
Right:     24   12   4    1   (product of all elements after i)

Result:    24   12   8    6   (left[i] × right[i])
           ↑    ↑    ↑    ↑
         2*3*4  1*3*4  1*2*4  1*2*3
```

**Why Not Division?**
- Division by zero breaks it
- Problem explicitly forbids it
- Teaches prefix/postfix pattern

**General Solution (Using Three Arrays):**

First, let's understand the intuition: for each index `i`, we need the product of all elements to its left multiplied by the product of all elements to its right.

**Approach:**
1. Create `left_products[i]` = product of all elements before index `i`
2. Create `right_products[i]` = product of all elements after index `i`
3. Result at `i` = `left_products[i] * right_products[i]`

**Pseudocode:**
```
INITIALIZE left_products, right_products, result arrays with all 1s

FOR i from 1 to n-1:
    left_products[i] = left_products[i-1] * nums[i-1]
    
FOR i from n-2 down to 0:
    right_products[i] = right_products[i+1] * nums[i+1]
    
FOR i from 0 to n-1:
    result[i] = left_products[i] * right_products[i]
    
RETURN result
```

**Implementation:**
```python
def product_except_self_general(nums: list[int]) -> list[int]:
    """
    Time: O(n) - Three passes through the array.
    Space: O(n) - We use three additional arrays.
    """
    n = len(nums)
    
    # Initialize three arrays of size n
    left_products = [1] * n
    right_products = [1] * n
    result = [1] * n
    
    # Fill left_products: each index contains product of all elements to its left
    for i in range(1, n):
        left_products[i] = left_products[i - 1] * nums[i - 1]
        
    # Fill right_products: each index contains product of all elements to its right
    for i in range(n - 2, -1, -1):
        right_products[i] = right_products[i + 1] * nums[i + 1]
        
    # The result for index i is left_products[i] * right_products[i]
    for i in range(n):
        result[i] = left_products[i] * right_products[i]
        
    return result
```

**Optimized Solution (O(1) Extra Space):**

We can optimize the space by computing prefix and postfix products on the fly, storing them directly in the result array.

**Key Insight:** We don't need separate arrays for left and right products. We can:
1. First pass: store left products in the result array
2. Second pass: multiply each position by the right product as we go

**Pseudocode:**
```
INITIALIZE result array with all 1s
INITIALIZE prefix = 1
FOR i from 0 to n-1:
    res[i] = prefix
    prefix *= nums[i]
    
INITIALIZE postfix = 1
FOR i from n-1 down to 0:
    res[i] *= postfix
    postfix *= nums[i]
RETURN res
```

**Implementation:**
```python
def product_except_self(nums: list[int]) -> list[int]:
    """
    Time: O(n) - Two passes through the array.
    Space: O(1) - The output array doesn't count as extra space.
    """
    res = [1] * len(nums)
    prefix = 1
    for i in range(len(nums)):
        res[i] = prefix
        prefix *= nums[i]
    
    postfix = 1
    for i in range(len(nums) - 1, -1, -1):
        res[i] *= postfix
        postfix *= nums[i]
    return res
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [1,2,3,4] | [24,12,8,6] | [2*3*4, 1*3*4, 1*2*4, 1*2*3] |
| With zero | [0,1,2,3] | [6,0,0,0] | Zero multiplied with others gives 0 |
| Negative | [-1,1,0,-3,3] | [0,0,9,0,0] | Product includes zero |

**Pattern Recognition: Prefix/Postfix Sweep**

**When to use this pattern:**
1. Need information from both directions (left and right)
2. For each position, need aggregate data from before AND after
3. Can't use division to get "product of all others"

**The Pattern:**
1. Left pass: Accumulate information going forward
2. Right pass: Accumulate information going backward
3. Combine: Merge both at each position

**Related Problems:**
- **Trapping Rain Water** (max height from left, max height from right)
- **Max Subarray** (Kadane's - running sum with resets)
- **Candy** (distribute candies based on ratings from both sides)
- **Gas Station** (circular array with prefix sums)

**Key Questions:**
1. Do I need info from both directions?
2. Can I compute it in two passes?
3. Can I optimize space by reusing output array?

**Topic Problems to Practice:**
- [Trapping Rain Water](https://leetcode.com/problems/trapping-rain-water/) — another prefix/postfix style sweep.
- [Minimum Size Subarray Sum](https://leetcode.com/problems/minimum-size-subarray-sum/)
- [Array of Doubled Pairs](https://leetcode.com/problems/array-of-doubled-pairs/)

#### 2.1.6 Longest Consecutive Sequence
**Problem:** Given an unsorted array of integers `nums`, return the length of the longest consecutive elements sequence. You must write an algorithm that runs in O(n) time.

**Building Intuition:**

**Key Insight:** Only start counting from the beginning of a sequence!

**Naive Approach:** Sort first → O(n log n) =>

**Smart Approach:** Use set for O(1) lookup

**Example:** `[100, 4, 200, 1, 3, 2]`
```
Set: {100, 4, 200, 1, 3, 2}

Check 100: Is 99 in set? No → Start of sequence!
  100 → 101? No
  Length: 1

Check 4: Is 3 in set? Yes → NOT start, skip

Check 200: Is 199 in set? No → Start of sequence!
  200 → 201? No
  Length: 1

Check 1: Is 0 in set? No → Start of sequence!
  1 → 2? Yes → 3? Yes → 4? Yes → 5? No
  Length: 4 ✓

Check 3: Is 2 in set? Yes → NOT start, skip
Check 2: Is 1 in set? Yes → NOT start, skip

Longest: 4 (sequence: 1,2,3,4)
```

**Why This Works:**
- Only count each sequence once (from its start)
- O(1) lookups with set
- Each number visited at most twice (once as potential start, once when counting)

**Solution:** Use a set for O(1) lookups. For each number, we only start counting a sequence if it's the beginning of one (i.e., `num - 1` is not in the set). This ensures we only check each sequence once.

**Pseudocode:**
```
INITIALIZE num_set from nums
INITIALIZE longest_streak = 0
FOR each num in num_set:
    IF (num - 1) NOT in num_set:  // num is start of sequence
        current_num = num
        current_streak = 1
        WHILE (current_num + 1) in num_set:
            current_num += 1
            current_streak += 1
        longest_streak = MAX(longest_streak, current_streak)
RETURN longest_streak
```

**Implementation:**
```python
def longest_consecutive(nums: list[int]) -> int:
    """
    Time: O(n) - Each number is checked once as the start of a sequence.
    Space: O(n) - To store the set.
    """
    num_set = set(nums)
    longest_streak = 0
    for num in num_set:
        if (num - 1) not in num_set:
            current_num = num
            current_streak = 1
            while (current_num + 1) in num_set:
                current_num += 1
                current_streak += 1
            longest_streak = max(longest_streak, current_streak)
    return longest_streak
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Basic | [100,4,200,1,3,2] | 4 | Sequence: 1,2,3,4 |
| Single element | [0] | 1 | Single element sequence |
| No consecutive | [9,1,4,7,3] | 1 | No consecutive numbers |
| Duplicates | [1,2,0,1] | 3 | Sequence: 0,1,2 (duplicates ignored) |

**Pattern Recognition: Smart Iteration with Set**

**When to use this pattern:**
1. Find sequences/chains in unsorted array
2. Need O(n) time (can't sort)
3. Use set for O(1) membership check

**The Trick:** Only start work from "anchor points"
- Longest Consecutive: Start only if `num-1` not in set
- Union-Find: Start from root representatives
- Connected Components: Start from unvisited nodes

**Related Problems:**
- **Longest Increasing Subsequence** (different: use DP or binary search)
- **Binary Tree Longest Consecutive Sequence** (DFS on tree)
- **Max Consecutive Ones** (different: sliding window)

**Topic Problems to Practice:**
- [Longest Increasing Subsequence](https://leetcode.com/problems/longest-increasing-subsequence/)
- [Set Mismatch](https://leetcode.com/problems/set-mismatch/)
- [Relative Sort Array](https://leetcode.com/problems/relative-sort-array/)

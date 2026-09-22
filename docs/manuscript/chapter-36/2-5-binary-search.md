---
title: "Binary Search"
---

### 2.5 Binary Search
-   **Pattern:** An efficient algorithm for finding an item from a **sorted** list of items. It works by repeatedly dividing in half the portion of the list that could contain the item, until you've narrowed down the possible locations to just one.

**Binary Search Intuition:**

**The Core Idea:** Eliminate half the search space each step.

**Requirements:**
1. **Sorted data** (or partially sorted, like rotated)
2. **Decision criteria:** Can determine which half to search

**Why O(log n)?**
```
n elements → n/2 → n/4 → n/8 → ... → 1
Steps: log₂(n)
```

**Template:**
```python
left, right = 0, len(arr) - 1
while left <= right:
    mid = (left + right) // 2
    if found_target(mid):
        return mid
    elif go_right(mid):
        left = mid + 1
    else:
        right = mid - 1
return -1
```

**When to use:**
- Sorted array search
- "Find first/last occurrence"
- Rotated sorted array
- Peak element
- Square root, search in 2D matrix

#### 2.5.1 Find Minimum in Rotated Sorted Array
**Problem:** Suppose an array of length `n` sorted in ascending order is rotated between `1` and `n` times. Given the sorted rotated array `nums`, return the minimum element of this array. You must write an algorithm that runs in `O(log n)` time.

**Building Intuition:**

**Key Insight:** The minimum is at the "rotation point" where a larger number is followed by a smaller one.

**Example:** `[3, 4, 5, 1, 2]`
```
Original: [1, 2, 3, 4, 5]
Rotated:  [3, 4, 5, 1, 2]
                    ↑ min at rotation point
```

**Strategy:**
- If `nums[mid] >= nums[left]` → Left side is sorted → Min must be on right
- If `nums[mid] < nums[left]` → Right side is sorted → Min is mid or on left

**Why Binary Search?**
- Don't need to check every element
- Can determine which half contains minimum
- O(log n) vs O(n) linear scan

**Solution:** The key is to determine which part of the array is sorted. We use two pointers, `left` and `right`. If `nums[mid]` is greater than or equal to `nums[left]`, it means the left part is sorted, so the minimum must be in the right part. Otherwise, the right part is sorted, and the minimum could be `nums[mid]` or in the left part.

**Pseudocode:**
```
INITIALIZE result = nums[0]
INITIALIZE left = 0, right = length - 1
WHILE left <= right:
    // If subarray is already sorted
    IF nums[left] < nums[right]:
        result = MIN(result, nums[left])
        BREAK
    
    mid = (left + right) // 2
    result = MIN(result, nums[mid])
    
    IF nums[mid] >= nums[left]:  // Left part is sorted
        left = mid + 1
    ELSE:  // Right part is sorted
        right = mid - 1
RETURN result
```

**Implementation:**
```python
def find_min(nums: list[int]) -> int:
    """
    Time: O(log n) - Standard binary search.
    Space: O(1) - Only pointers are used.
    """
    res = nums[0]
    l, r = 0, len(nums) - 1
    while l <= r:
        # If the subarray is already sorted
        if nums[l] < nums[r]:
            res = min(res, nums[l])
            break
        
        m = (l + r) // 2
        res = min(res, nums[m])
        
        if nums[m] >= nums[l]: # Left part is sorted
            l = m + 1
        else: # Right part is sorted
            r = m - 1
    return res
```

**Trace Table:**
| Test Case | Input | Output | Explanation |
|-----------|-------|--------|-------------|
| Rotated once | [3,4,5,1,2] | 1 | Array was rotated, minimum is 1 |
| Not rotated | [1,2,3,4,5] | 1 | Array not rotated, first element is minimum |
| Rotated heavily | [4,5,6,7,0,1,2] | 0 | Minimum is at the rotation point |
| Two elements | [2,1] | 1 | Simple two-element rotation |

#### 2.5.2 Search in Rotated Sorted Array
**Problem:** Given the array `nums` after the possible rotation and an integer `target`, return the index of `target` if it is in `nums`, or `-1` if it is not in `nums`. You must write an algorithm with `O(log n)` runtime complexity.

**Solution:** This is a more complex binary search. At each step, we determine which half of the array is sorted. Then, we check if the `target` lies within the sorted half. If it does, we search in that half. Otherwise, we search in the other, unsorted (but still partitioned) half.

**Pseudocode:**
```
INITIALIZE left = 0, right = length - 1
WHILE left <= right:
    mid = (left + right) // 2
    IF nums[mid] == target:
        RETURN mid
    
    // Check if left half is sorted
    IF nums[left] <= nums[mid]:
        IF target > nums[mid] OR target < nums[left]:
            left = mid + 1  // Search right half
        ELSE:
            right = mid - 1  // Search left half
    ELSE:  // Right half is sorted
        IF target < nums[mid] OR target > nums[right]:
            right = mid - 1  // Search left half
        ELSE:
            left = mid + 1  // Search right half
RETURN -1  // Not found
```

**Implementation:**
```python
def search(nums: list[int], target: int) -> int:
    """
    Time: O(log n) - Standard binary search.
    Space: O(1) - Only pointers are used.
    """
    l, r = 0, len(nums) - 1
    while l <= r:
        m = (l + r) // 2
        if nums[m] == target:
            return m
            
        # Check if the left half is sorted
        if nums[l] <= nums[m]:
            if target > nums[m] or target < nums[l]:
                l = m + 1
            else:
                r = m - 1
        # Otherwise, the right half is sorted
        else:
            if target < nums[m] or target > nums[r]:
                r = m - 1
            else:
                l = m + 1
    return -1
```

**Trace Table:**
| Test Case | Input (nums) | Target | Output | Explanation |
|-----------|--------------|--------|--------|-------------|
| Found in rotated | [4,5,6,7,0,1,2] | 0 | 4 | Target found at index 4 |
| Found at start | [4,5,6,7,0,1,2] | 4 | 0 | Target found at index 0 |
| Not found | [4,5,6,7,0,1,2] | 3 | -1 | Target not in array |
| Single element | [1] | 1 | 0 | Single element match |

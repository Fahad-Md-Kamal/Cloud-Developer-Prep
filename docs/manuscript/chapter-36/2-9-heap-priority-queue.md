---
title: "Heap / Priority Queue"
---

### 2.9 Heap / Priority Queue
-   **Pattern:** A heap is a specialized tree-based structure that satisfies the heap property (parent ≥ children in max-heap, parent ≤ children in min-heap). Perfect for finding the k-th largest/smallest elements, merging sorted sequences, or getting min/max in O(1).

```python
# Implementation uses only lists with manual ordering (no heapq import)
```

#### 2.9.1 Find Median from Data Stream
**Problem:** Design a data structure that supports adding integers and finding the median.

**Solution:** Maintain two manually sorted lists to mirror the two-heap approach: a descending list (`small`) for the smaller half and an ascending list (`large`) for the larger half. Insert numbers in order and rebalance so their sizes differ by at most one and every element in `small` is ≤ every element in `large`.

**Algorithm:**
- **Max-heap** (left): stores smaller half of numbers
- **Min-heap** (right): stores larger half
- Maintain: `len(max_heap) >= len(min_heap)` and `len(max_heap) - len(min_heap) <= 1`
- **Add number:**
  1. Add to max-heap first
  2. Move max-heap's top to min-heap
  3. If min-heap becomes larger, move its top back to max-heap
- **Find median:**
  - If heaps are same size: average of both tops
  - Otherwise: top of max-heap

**Why two heaps?** Direct access to the "middle" elements in O(1).

**Pseudocode:**
```
CLASS MedianFinder:
    FUNCTION __init__():
        small = []  // max heap (negate values)
        large = []  // min heap
    
    FUNCTION addNum(num):
        // Add to max heap (small)
        PUSH -num to small
        
        // Ensure every element in small <= every element in large
        IF small AND large AND (-small[0] > large[0]):
            val = -POP from small
            PUSH val to large
        
        // Balance the heaps
        IF length of small > length of large + 1:
            val = -POP from small
            PUSH val to large
        IF length of large > length of small:
            val = POP from large
            PUSH -val to small
    
    FUNCTION findMedian():
        IF length of small > length of large:
            RETURN -small[0]
        RETURN (-small[0] + large[0]) / 2.0
```

**Implementation:**
```python
class MedianFinder:
    def __init__(self):
        """
        Maintain two ordered lists: small (desc) for lower half, large (asc) for upper half.
        """
        self.small: list[int] = []  # descending order
        self.large: list[int] = []  # ascending order

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
        """
        Time: O(n) - Manual sorted insertions.
        """
        self._insert_desc(self.small, num)

        if self.large and self.small and self.small[0] > self.large[0]:
            val = self.small.pop(0)
            self._insert_asc(self.large, val)

        if len(self.small) > len(self.large) + 1:
            val = self.small.pop(0)
            self._insert_asc(self.large, val)
        if len(self.large) > len(self.small):
            val = self.large.pop(0)
            self._insert_desc(self.small, val)

    def findMedian(self) -> float:
        """
        Time: O(1) - Access list fronts.
        """
        if len(self.small) > len(self.large):
            return float(self.small[0])
        return (self.small[0] + self.large[0]) / 2.0
```

**Trace Table:**
| Test Case | Operations | Output | Explanation |
|-----------|------------|--------|-------------|
| Basic | addNum(1), addNum(2), findMedian() | [null, null, 1.5] | Median of [1,2] is 1.5 |
| Odd count | addNum(1), addNum(2), addNum(3), findMedian() | [null, null, null, 2.0] | Median of [1,2,3] is 2 |
| Duplicates | addNum(1), addNum(1), findMedian() | [null, null, 1.0] | Median of [1,1] is 1 |
| Negative | addNum(-1), addNum(-2), findMedian() | [null, null, -1.5] | Works with negative numbers |

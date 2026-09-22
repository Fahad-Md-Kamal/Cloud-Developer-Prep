"""
Blind 75
https://leetcode.com/problems/top-k-frequent-elements/

Pattern: Arrays & Hashing, Heap
"""
from typing import List
from collections import Counter
import heapq

def top_k_frequent(nums: List[int], k: int) -> List[int]:
    """
    Given an integer array nums and an integer k, return the k most frequent elements.
    You may return the answer in any order.

    This solution uses a hash map to count frequencies, then a min-heap to keep
    track of the top k elements.

    Complexity:
    Time: O(n log k) - O(n) to build the frequency map. Then, for each of the n unique
          elements, we push to a heap of size k, which is O(log k).
    Space: O(n + k) - O(n) for the frequency map and O(k) for the heap.
    """
    if k == len(nums):
        return nums

    # 1. Build hash map: element -> frequency
    count = Counter(nums)

    # 2. Build min-heap of size k
    # Python's heapq is a min-heap, so we store (frequency, num)
    min_heap = []
    for num, freq in count.items():
        heapq.heappush(min_heap, (freq, num))
        if len(min_heap) > k:
            heapq.heappop(min_heap)

    # 3. Extract numbers from the heap
    return [num for freq, num in min_heap]


def top_k_frequent_bucket_sort(nums: List[int], k: int) -> List[int]:
    """
    A more optimized solution using a variation of Bucket Sort. This avoids the
    log k factor from the heap.

    Complexity:
    Time: O(n) - O(n) to count, O(n) to populate buckets, O(n) in worst case to get results.
    Space: O(n) - For the frequency map and the bucket list.
    """
    count = Counter(nums)
    # The index of the list represents the frequency.
    # The size is len(nums) + 1 because an element can appear at most n times.
    freq_buckets = [[] for i in range(len(nums) + 1)]

    for num, freq in count.items():
        freq_buckets[freq].append(num)

    res = []
    # Iterate backwards from the highest possible frequency
    for i in range(len(freq_buckets) - 1, 0, -1):
        for num in freq_buckets[i]:
            res.append(num)
            if len(res) == k:
                return res
    return res

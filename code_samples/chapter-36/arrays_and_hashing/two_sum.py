"""
Blind 75
https://leetcode.com/problems/two-sum/

Pattern: Arrays & Hashing
"""
from typing import List

def two_sum(nums: List[int], target: int) -> List[int]:
    """
    Given an array of integers nums and an integer target, return indices of the two numbers
    such that they add up to target.

    You may assume that each input would have exactly one solution, and you may not use
    the same element twice.

    You can return the answer in any order.

    Complexity:
    Time: O(n) - We iterate through the list once. Hash map lookups are O(1) on average.
    Space: O(n) - In the worst case, we store all n elements in the hash map.
    """
    seen = {}  # Dictionary to store value -> index
    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i
    return [] # Should not be reached based on problem description

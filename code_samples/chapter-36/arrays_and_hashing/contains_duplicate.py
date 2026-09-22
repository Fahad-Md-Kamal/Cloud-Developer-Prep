"""
Blind 75
https://leetcode.com/problems/contains-duplicate/

Pattern: Arrays & Hashing
"""
from typing import List

def contains_duplicate(nums: List[int]) -> bool:
    """
    Given an integer array nums, return true if any value appears at least twice
    in the array, and return false if every element is distinct.

    Complexity:
    Time: O(n) - We iterate through the list once. Set lookups are O(1) on average.
    Space: O(n) - In the worst case, we store all n elements in the hash set.
    """
    hashset = set()
    for n in nums:
        if n in hashset:
            return True
        hashset.add(n)
    return False

def contains_duplicate_oneliner(nums: List[int]) -> bool:
    """
    A more concise way to check for duplicates by comparing the length of the list
    to the length of a set created from it.

    Complexity:
    Time: O(n) - To build the set.
    Space: O(n) - To store the set.
    """
    return len(nums) != len(set(nums))

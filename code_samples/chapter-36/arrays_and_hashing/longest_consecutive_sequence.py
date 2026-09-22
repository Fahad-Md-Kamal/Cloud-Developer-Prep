"""
Blind 75
https://leetcode.com/problems/longest-consecutive-sequence/

Pattern: Arrays & Hashing
"""
from typing import List

def longest_consecutive(nums: List[int]) -> int:
    """
    Given an unsorted array of integers nums, return the length of the longest
    consecutive elements sequence.

    You must write an algorithm that runs in O(n) time.

    The key insight is to use a set for O(1) lookups. For each number, we check if it's
    the start of a sequence (i.e., if num - 1 is NOT in the set). If it is, we start
    counting the length of the sequence from there. This ensures we only build each
    sequence once, from its starting point.

    Complexity:
    Time: O(n) - Although there is a nested loop, the inner while loop only runs for
          each number that is the start of a sequence. In total, the inner loop
          runs n times across all outer loop iterations.
    Space: O(n) - To store the set of numbers.
    """
    num_set = set(nums)
    longest_streak = 0

    for num in num_set:
        # Check if it's the start of a sequence
        if (num - 1) not in num_set:
            current_num = num
            current_streak = 1

            # Count the length of the sequence
            while (current_num + 1) in num_set:
                current_num += 1
                current_streak += 1
            
            longest_streak = max(longest_streak, current_streak)

    return longest_streak

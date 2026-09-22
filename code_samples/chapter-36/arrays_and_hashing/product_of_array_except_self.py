"""
Blind 75
https://leetcode.com/problems/product-of-array-except-self/

Pattern: Arrays & Hashing
"""
from typing import List

def product_except_self(nums: List[int]) -> List[int]:
    """
    Given an integer array nums, return an array answer such that answer[i] is equal
    to the product of all the elements of nums except nums[i].

    The product of any prefix or suffix of nums is guaranteed to fit in a 32-bit integer.

    You must write an algorithm that runs in O(n) time and without using the division operator.

    The key is to make two passes. First, calculate the product of all elements to the
    left of each index (prefix products). Then, make a second pass backwards to multiply
    by the product of all elements to the right (postfix products).

    Complexity:
    Time: O(n) - We make two passes through the array.
    Space: O(1) - The output array does not count as extra space for this problem's constraints.
    """
    res = [1] * len(nums)

    # Pass 1: Calculate prefix products
    # res[i] will contain the product of all numbers to the left of i
    prefix = 1
    for i in range(len(nums)):
        res[i] = prefix
        prefix *= nums[i]

    # Pass 2: Calculate postfix products and multiply with prefixes
    # res[i] will be multiplied by the product of all numbers to the right of i
    postfix = 1
    for i in range(len(nums) - 1, -1, -1):
        res[i] *= postfix
        postfix *= nums[i]

    return res

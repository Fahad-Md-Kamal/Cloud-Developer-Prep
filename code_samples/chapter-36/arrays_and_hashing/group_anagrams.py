"""
Blind 75
https://leetcode.com/problems/group-anagrams/

Pattern: Arrays & Hashing
"""
from typing import List
from collections import defaultdict

def group_anagrams(strs: List[str]) -> List[List[str]]:
    """
    Given an array of strings strs, group the anagrams together. You can return the
    answer in any order.

    An Anagram is a word or phrase formed by rearranging the letters of a different
    word or phrase, typically using all the original letters exactly once.

    The key insight is that anagrams will be identical when their characters are sorted.
    We can use a sorted version of a string as a key in a hash map.

    Complexity:
    Time: O(m * n log n) where m is the number of strings and n is the average length
          of a string. The n log n comes from sorting each string.
    Space: O(m * n) - In the worst case, we store all characters from all strings
           in the hash map.
    """
    anagram_map = defaultdict(list)  # map charCount to list of anagrams

    for s in strs:
        # Sorting the string provides a canonical representation for anagrams
        sorted_s = "".join(sorted(s))
        anagram_map[sorted_s].append(s)

    return list(anagram_map.values())

def group_anagrams_char_count(strs: List[str]) -> List[List[str]]:
    """
    An alternative approach that avoids the n log n sorting cost. Instead, we create
    a character count array (or tuple) to use as the key. This is more efficient.

    Complexity:
    Time: O(m * n) where m is the number of strings and n is the average length.
          We iterate through each character of each string once.
    Space: O(m * n) - Same as before, to store the resulting groups.
    """
    anagram_map = defaultdict(list)

    for s in strs:
        count = [0] * 26  # for a-z
        for char in s:
            count[ord(char) - ord("a")] += 1
        
        # Tuples are immutable and can be used as dictionary keys
        anagram_map[tuple(count)].append(s)
        
    return list(anagram_map.values())

class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        charSet = set()
        lp = 0
        longest = 0
        for i in range(len(s)):
            while s[i] in charSet:
                charSet.remove(s[lp])
                lp += 1
            charSet.add(s[i])
            longest = max(i - lp + 1, longest)
        return longest
    
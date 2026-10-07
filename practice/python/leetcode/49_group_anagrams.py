class Solution:
    def groupAnagrams(self, strs: list[str]) -> list[list[str]]:
        groups = {}

        for wrd in strs:
            s_wrd = "".join(sorted(wrd))
            if s_wrd not in groups:
                groups[s_wrd] = [wrd]
            else:
                groups[s_wrd].append(wrd)
        return list(groups.values())


if __name__ == "__main__":
    test_cases = [
        (["eat", "tea", "tan", "ate", "nat", "bat"],
         [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]),
        ([""], [[""]]),
        (["a"], [["a"]]),
        ([], []),
        (["abc", "bca", "cab", "xyz"], [["abc", "bca", "cab"], ["xyz"]]),
        (["abc", "def", "ghi"], [["abc"], ["def"], ["ghi"]]),
        (["ab", "ba", "ab"], [["ab", "ba", "ab"]]),
        (["listen", "silent", "enlist"], [["listen", "silent", "enlist"]]),
        (["abcd", "dcba", "abdc"], [["abcd", "dcba", "abdc"]]),
        (["a", "b", "c"], [["a"], ["b"], ["c"]]),
        (["aa", "aa"], [["aa", "aa"]]),
        (["", ""], [["", ""]]),
        (["tan", "nat", "bat"], [["tan", "nat"], ["bat"]]),
        (["cab", "tin", "pat", "bac", "rat", "cats"],
         [["cab", "bac"], ["tin"], ["pat"], ["rat"], ["cats"]]),
        (["eat", "tea", "tea", "eat"], [["eat", "tea", "tea", "eat"]]),
        (["z", "y", "x", "zy"], [["z"], ["y"], ["x"], ["zy"]]),
        (["abab", "baba", "aabb"], [["abab", "baba", "aabb"]]),
        (["abc", "cba", "bac", "foo", "oof", "bar"],
         [["abc", "cba", "bac"], ["foo", "oof"], ["bar"]]),
        (["abcde", "edcba", "eabcd"], [["abcde", "edcba", "eabcd"]]),
        (["a", "aa", "aaa"], [["a"], ["aa"], ["aaa"]]),
    ]

    solution = Solution()
    for i, (strs, expected) in enumerate(test_cases, start=1):
        actual = solution.groupAnagrams(strs)
        assert actual == expected, (
            f"Test {i} failed: groupAnagrams({strs!r}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: groupAnagrams({strs!r}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")

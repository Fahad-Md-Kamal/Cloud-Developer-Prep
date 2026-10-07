class Solution:
    def lengthOfLastWord(self, s: str) -> int:
        wl = 0
        for i in range(len(s)-1, -1, -1):
            if wl == 0 and s[i] == " ":
                continue
            elif s[i] == " ":
                return wl
            else:
                wl += 1
        return wl


if __name__ == "__main__":
    test_cases = [
        ("Hello World", 5),
        ("   fly me   to   the moon  ", 4),
        ("luffy is still joyboy", 6),
        ("a", 1),
        ("a ", 1),
        ("   a", 1),
        ("Hello", 5),
        ("   a   b   c  ", 1),
        ("day", 3),
        ("This is a test sentence", 8),
        ("x", 1),
        ("Hello World   ", 5),
        ("   Hello", 5),
        ("python java c golang", 6),
        ("I love Python", 6),
        ("word", 4),
        ("a b", 1),
        ("    single", 6),
        ("The quick brown fox jumps over the lazy dog", 3),
        ("racecar", 7),
    ]

    solution = Solution()
    for i, (s, expected) in enumerate(test_cases, start=1):
        actual = solution.lengthOfLastWord(s)
        assert actual == expected, (
            f"Test {i} failed: lengthOfLastWord({s!r}) = {actual}, expected {expected}"
        )
        print(f"Test {i:2d} passed: lengthOfLastWord({s!r}) = {actual}")

    print(f"\nAll {len(test_cases)} test cases passed!")
